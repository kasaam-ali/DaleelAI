"""Hybrid retrieve: original query plus synonym expansion, then RRF. The searcher is injected."""

from collections.abc import Awaitable, Callable

from app.core.retrieval.fusion import RankedHit, fuse_hits
from app.core.retrieval.synonyms import expand_search_query

Searcher = Callable[..., Awaitable[list[RankedHit]]]


async def retrieve(
    search: Searcher,
    query: str,
    *,
    collection: str,
    tax_year: str | None,
    domain: str | None = None,
    k: int = 30,
    domain_boost: float = 1.2,
) -> list[tuple[RankedHit, float]]:
    """Search the original query and, when synonyms add terms, the expanded query."""
    lists = [await search(collection=collection, query=query, tax_year=tax_year, k=k)]
    expanded = expand_search_query(query)
    if expanded != query:
        lists.append(await search(collection=collection, query=expanded, tax_year=tax_year, k=k))
    return fuse_hits(lists, domain=domain, domain_boost=domain_boost)
