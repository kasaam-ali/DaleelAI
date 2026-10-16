import pytest

from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rerank import rerank
from app.core.retrieval.retrieve import retrieve
from app.core.retrieval.synonyms import expand_search_query


def hit(chunk_id: str, *, domain: str = "income_tax", text: str = "") -> RankedHit:
    return RankedHit(chunk_id=chunk_id, domain=domain, payload={"text": text or chunk_id})


class RecordingSearch:
    def __init__(self, lists: dict[str, list[RankedHit]]):
        self.lists = lists
        self.calls: list[dict] = []

    async def __call__(self, *, collection: str, query: str, tax_year: str | None, k: int):
        self.calls.append({"collection": collection, "query": query, "tax_year": tax_year, "k": k})
        return self.lists.get(query, [])


async def test_synonyms_cause_a_second_search_and_the_shared_hit_wins():
    original = "salary tax"
    expanded = expand_search_query(original)
    search = RecordingSearch(
        {
            original: [hit("only-original"), hit("shared")],
            expanded: [hit("shared"), hit("only-expanded")],
        }
    )

    ranked = await retrieve(search, original, collection="documents", tax_year="TY2027", k=30)

    assert [call["query"] for call in search.calls] == [original, expanded]
    assert all(call["tax_year"] == "TY2027" for call in search.calls)
    assert all(call["collection"] == "documents" for call in search.calls)
    assert ranked[0][0].chunk_id == "shared"


async def test_query_without_synonyms_is_searched_once():
    search = RecordingSearch({"section 149": [hit("s149")]})

    ranked = await retrieve(search, "section 149", collection="documents", tax_year="TY2026")

    assert len(search.calls) == 1
    assert ranked[0][0].chunk_id == "s149"


async def test_statutory_query_skips_synonym_expansion():
    query = "immovable property sale seller advance tax Section 236C"
    search = RecordingSearch({query: [hit("s236c")]})

    ranked = await retrieve(search, query, collection="documents", tax_year="TY2027")

    assert [call["query"] for call in search.calls] == [query]
    assert ranked[0][0].chunk_id == "s236c"


def test_rerank_keeps_six_and_ignores_hits_past_the_pool():
    hits = [hit(f"c{i}", text=f"text-{i}") for i in range(40)]

    def score(_query: str, texts: list[str]) -> list[float]:
        assert len(texts) == 30
        return [float(index) for index in range(len(texts))]

    ranked = rerank("salary", hits, score, pool=30, keep=6)

    assert [item[0].chunk_id for item in ranked] == ["c29", "c28", "c27", "c26", "c25", "c24"]


def test_rerank_scores_the_opening_of_a_long_chunk():
    long = "HEAD " + ("x" * 2000)
    seen: list[str] = []

    def score(_query: str, texts: list[str]) -> list[float]:
        seen.extend(texts)
        return [0.5]

    rerank("salary", [hit("a", text=long)], score, pool=1, keep=1)

    assert seen[0].startswith("HEAD ")
    assert len(seen[0]) == 400


def test_rerank_rejects_a_short_score_list():
    with pytest.raises(ValueError, match="2"):
        rerank("salary", [hit("a"), hit("b")], lambda _query, _texts: [0.1])
