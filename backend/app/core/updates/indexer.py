"""Upsert official-page chunks into Qdrant collection web_pages only."""

import logging
import os
import threading
from typing import Any

from app.version import INDEXED_CORPUS_VERSION

log = logging.getLogger(__name__)
_model_lock = threading.Lock()
_dense = None
_sparse = None


def index_notification(row: dict[str, Any]) -> None:
    page = {
        "url": row["source_url"],
        "site": "fbr.gov.pk",
        "authority": "FBR",
        "title": row["title"],
        "domain": row.get("domain") or "unclassified",
    }
    text = row["summary"]
    _upsert_page(page, text)


class WebIndexer:
    def upsert(self, page: dict[str, Any]) -> None:
        _upsert_page(page, page.get("text") or page.get("title") or "")

    def delete(self, url: str) -> None:
        from qdrant_client.http import models

        from pipeline.web_pages import COLLECTION, assert_safe_collection

        client = _client()
        assert_safe_collection(COLLECTION)
        before = _documents(client)
        client.delete(
            collection_name=COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="url", match=models.MatchValue(value=url))]
                )
            ),
        )
        if _documents(client) != before:
            raise RuntimeError("documents count changed")


def warm_indexer() -> None:
    """Load the embedding models once, before the first replay request."""
    try:
        _models()
    except Exception:
        log.warning("indexer warm failed", exc_info=True)


def _models():
    global _dense, _sparse
    if _dense is not None and _sparse is not None:
        return _dense, _sparse
    with _model_lock:
        if _dense is None or _sparse is None:
            from fastembed import SparseTextEmbedding, TextEmbedding

            from pipeline.index import DENSE_MODEL, SPARSE_MODEL

            _dense = TextEmbedding(model_name=DENSE_MODEL)
            _sparse = SparseTextEmbedding(model_name=SPARSE_MODEL)
    return _dense, _sparse


def _upsert_page(page: dict[str, Any], text: str) -> None:
    from datetime import UTC, datetime

    from qdrant_client.http import models

    from pipeline.index import DENSE_SIZE
    from pipeline.web_pages import (
        COLLECTION,
        _count,
        _ensure_web,
        assert_safe_collection,
        point_id,
        records_for,
    )

    client = _client()
    assert_safe_collection(COLLECTION)
    before = _count(client, "documents")
    _ensure_web(client, DENSE_SIZE)
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = records_for(page, text, fetched_at, INDEXED_CORPUS_VERSION)
    if not records:
        return
    dense_model, sparse_model = _models()
    embed_text = [f"{row['header']}\n\n{row['text']}" for row in records]
    points = []
    for row, dense_vec, sparse_vec in zip(
        records,
        dense_model.embed(embed_text),
        sparse_model.embed(embed_text),
        strict=True,
    ):
        points.append(
            models.PointStruct(
                id=point_id(row["chunk_id"]),
                vector={
                    "dense": dense_vec.tolist(),
                    "bm25": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=row,
            )
        )
    assert_safe_collection(COLLECTION)
    client.upsert(collection_name=COLLECTION, points=points)
    if _count(client, "documents") != before:
        raise RuntimeError("documents count changed")


def _client():
    from qdrant_client import QdrantClient

    return QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
        timeout=30,
        check_compatibility=False,
    )


def _documents(client) -> int | None:
    from pipeline.web_pages import _count

    return _count(client, "documents")
