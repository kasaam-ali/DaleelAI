"""Reciprocal rank fusion for the two hybrid result lists. No network calls."""

from pydantic import BaseModel, Field

# Cormack, Clarke, Buettcher. SPECS does not set k, so this is the usual constant.
RRF_K = 60


class RankedHit(BaseModel):
    chunk_id: str
    domain: str | None = None
    payload: dict = Field(default_factory=dict)


def rrf_fuse(ranked_lists: list[list[str]], *, k: int = RRF_K) -> list[tuple[str, float]]:
    """Fuse ranked id lists. Rank is 1-based. Earlier lists win a tie."""
    scores: dict[str, float] = {}
    first_seen: list[str] = []
    for ranked in ranked_lists:
        seen: set[str] = set()
        rank = 0
        for chunk_id in ranked:
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            rank += 1
            if chunk_id not in scores:
                first_seen.append(chunk_id)
                scores[chunk_id] = 0.0
            scores[chunk_id] += 1.0 / (k + rank)
    ordered = sorted(first_seen, key=lambda chunk_id: -scores[chunk_id])
    return [(chunk_id, scores[chunk_id]) for chunk_id in ordered]


def fuse_hits(
    ranked_lists: list[list[RankedHit]],
    *,
    k: int = RRF_K,
    domain: str | None = None,
    domain_boost: float = 1.2,
) -> list[tuple[RankedHit, float]]:
    """RRF across query lists, then multiply the predicted domain by domain_boost."""
    payloads: dict[str, RankedHit] = {}
    id_lists: list[list[str]] = []
    for ranked in ranked_lists:
        ids: list[str] = []
        for hit in ranked:
            ids.append(hit.chunk_id)
            payloads.setdefault(hit.chunk_id, hit)
        id_lists.append(ids)
    fused: list[tuple[RankedHit, float]] = []
    for chunk_id, score in rrf_fuse(id_lists, k=k):
        hit = payloads[chunk_id]
        if domain and hit.domain == domain:
            score *= domain_boost
        fused.append((hit, score))
    fused.sort(key=lambda item: -item[1])
    return fused
