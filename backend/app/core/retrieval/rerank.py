"""Keep the top rerank scores. The cross-encoder itself is injected."""

from collections.abc import Callable

from app.core.retrieval.fusion import RankedHit

Scorer = Callable[[str, list[str]], list[float]]

# The opening of a 1,000-character chunk is what the section heading says.
# Scoring the whole passage is what made the CPU cross-encoder take seconds.
RERANK_CHARS = 400


def rerank(
    query: str,
    hits: list[RankedHit],
    score: Scorer,
    *,
    pool: int = 30,
    keep: int = 6,
) -> list[tuple[RankedHit, float]]:
    """Score at most `pool` hits and return the best `keep`, highest score first."""
    chosen = hits[:pool]
    if not chosen:
        return []
    texts = [str(hit.payload.get("text", ""))[:RERANK_CHARS] for hit in chosen]
    scores = score(query, texts)
    if len(scores) != len(chosen):
        raise ValueError(f"reranker returned {len(scores)} scores for {len(chosen)} hits")
    ordered = sorted(zip(chosen, scores, strict=True), key=lambda item: -item[1])
    return ordered[:keep]
