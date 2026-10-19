"""Hybrid Qdrant search. The client and embedders are created on the first call."""

import asyncio
import threading
from typing import Any

from app.core.retrieval.fusion import RankedHit


def hit_from_payload(payload: dict[str, Any]) -> RankedHit:
    return RankedHit(
        chunk_id=str(payload.get("chunk_id") or ""),
        domain=payload.get("domain"),
        payload=payload,
    )


def coerce_scores(raw: list[Any]) -> list[float]:
    scores: list[float] = []
    for item in raw:
        if isinstance(item, (int, float)):
            scores.append(float(item))
        elif hasattr(item, "score"):
            scores.append(float(item.score))
        else:
            scores.append(float(item[1]))
    return scores


class QdrantHybridSearch:
    """Dense plus BM25 with server-side RRF. Does not create or delete collections."""

    def __init__(self, url: str, api_key: str, dense_model: str, sparse_model: str) -> None:
        self.url = url
        self.api_key = api_key
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self._client = None
        self._dense = None
        self._sparse = None
        self._lock = threading.Lock()

    async def __call__(self, *, collection: str, query: str, tax_year: str | None, k: int = 30):
        return await asyncio.to_thread(self._search, collection, query, tax_year, k)

    def _search(self, collection: str, query: str, tax_year: str | None, k: int) -> list[RankedHit]:
        with self._lock:
            self._ensure()
            dense_vec, indices, values = self._embed(query)
            try:
                points = self._query(collection, dense_vec, indices, values, tax_year, k)
            except Exception:
                if collection != "documents":
                    return []
                raise
        hits: list[RankedHit] = []
        for point in points:
            payload = dict(getattr(point, "payload", None) or {})
            if not payload.get("chunk_id"):
                payload["chunk_id"] = str(getattr(point, "id", ""))
            hits.append(hit_from_payload(payload))
        return hits

    def _ensure(self) -> None:
        if self._client is not None:
            return
        from fastembed import SparseTextEmbedding, TextEmbedding
        from qdrant_client import QdrantClient

        self._client = QdrantClient(
            url=self.url,
            api_key=self.api_key or None,
            timeout=20,
            check_compatibility=False,
        )
        self._dense = TextEmbedding(model_name=self.dense_model)
        self._sparse = SparseTextEmbedding(model_name=self.sparse_model)

    def warm(self) -> None:
        """Load the embedders and run one vector so the first question skips that cost."""
        self._ensure()
        self._embed("tax")

    def _embed(self, query: str) -> tuple[list[float], list[int], list[float]]:
        dense = next(iter(self._dense.embed([query])))
        sparse = next(iter(self._sparse.embed([query])))
        dense_list = dense.tolist() if hasattr(dense, "tolist") else list(dense)
        indices = sparse.indices.tolist()
        values = sparse.values.tolist()
        return dense_list, indices, values

    def _query(self, collection, dense_vec, indices, values, tax_year, k):
        from qdrant_client import models

        prefetch = [
            models.Prefetch(query=dense_vec, using="dense", limit=k),
            models.Prefetch(
                query=models.SparseVector(indices=indices, values=values),
                using="bm25",
                limit=k,
            ),
        ]
        query_filter = None
        if tax_year:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="tax_years",
                        match=models.MatchAny(any=[tax_year]),
                    )
                ]
            )
        result = self._client.query_points(
            collection_name=collection,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=query_filter,
            limit=k,
            with_payload=True,
        )
        return result.points
