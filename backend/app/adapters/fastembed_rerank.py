"""Cross-encoder rerank. The model loads on the first call."""

import threading

from app.adapters.qdrant_search import coerce_scores


class FastEmbedReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def __call__(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        with self._lock:
            return self._score(query, texts)

    def _score(self, query: str, texts: list[str]) -> list[float]:
        self._ensure()
        raw = list(self._model.rerank(query, texts))
        scores = coerce_scores(raw)
        if len(scores) != len(texts):
            raise ValueError(f"reranker returned {len(scores)} scores for {len(texts)} texts")
        return scores

    def warm(self) -> None:
        """Load the cross-encoder and score one pair so the first question skips that cost."""
        self._ensure()
        list(self._model.rerank("tax", ["section"]))

    def _ensure(self) -> None:
        if self._model is not None:
            return
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name=self.model_name)
