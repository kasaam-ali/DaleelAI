"""Hybrid retrieve: original query plus synonym expansion, then RRF. The searcher is injected."""

import re
from collections.abc import Awaitable, Callable

from app.core.retrieval.fusion import RankedHit, fuse_hits
from app.core.retrieval.synonyms import expand_search_query

Searcher = Callable[..., Awaitable[list[RankedHit]]]
_STATUTORY = re.compile(r"\bsection\s+\d{1,3}[A-Z]{0,4}\b", re.I)


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
    if _STATUTORY.search(query):
        return fuse_hits(lists, domain=domain, domain_boost=domain_boost)
    expanded = expand_search_query(query)
    if expanded != query:
        lists.append(await search(collection=collection, query=expanded, tax_year=tax_year, k=k))
    return fuse_hits(lists, domain=domain, domain_boost=domain_boost)
