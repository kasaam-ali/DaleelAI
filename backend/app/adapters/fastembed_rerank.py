"""Cross-encoder rerank. The model loads on the first call."""

from app.adapters.qdrant_search import coerce_scores


class FastEmbedReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def __call__(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(model_name=self.model_name)
        raw = list(self._model.rerank(query, texts))
        scores = coerce_scores(raw)
        if len(scores) != len(texts):
            raise ValueError(f"reranker returned {len(scores)} scores for {len(texts)} texts")
        return scores
