import asyncio

from app.agents.rag import _ranked_many
from app.core.plain_answer import plain_answer
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rewrite import COMPANY_FILING_QUERY, rewrite_queries

INDIV = RankedHit(
    chunk_id="336c72e3",
    payload={
        "section": "118",
        "text": "in the case of a person other than a company, the thirtieth day of September",
    },
)
COMPANY = RankedHit(
    chunk_id="7a45bf3e",
    payload={
        "section": "118",
        "text": "in the case of a company, the thirty-first day of December",
    },
)
S114 = RankedHit(
    chunk_id="s114", payload={"section": "114", "text": "every company shall furnish a return"}
)


def test_company_ask_gets_company_query():
    queries = rewrite_queries("Companies when is return due?", "company return filing deadline")
    assert COMPANY_FILING_QUERY in queries


def test_company_118_chunk_survives_selection():
    async def search(*, collection, query, tax_year, k):
        # Broad query surfaces only the individuals clause; the company query finds the other.
        return [COMPANY] if "thirty-first" in query else [INDIV, S114]

    ranked = asyncio.run(
        _ranked_many(
            search,
            None,
            rewrite_queries("When must companies file their income tax return?"),
            collection="documents",
            tax_year="2026",
            domain=None,
            k=30,
            keep=6,
            domain_boost=1.2,
            prefer={"114", "118"},
        )
    )
    ids = [hit.chunk_id for hit, _ in ranked]
    assert "7a45bf3e" in ids and "336c72e3" in ids and "s114" in ids


def test_context_meta_talk_stripped():
    out = plain_answer(
        "Individuals file by 30 September 2026 [1]. The context does not provide the company date."
    )
    assert "context" not in out.lower() and "30 September 2026" in out
    ru = plain_answer(
        "Individuals ki date 30 September hai [1]. Company ki date context mein nahi hai.",
        "roman_urdu",
    )
    assert "context" not in ru.lower() and "30 September" in ru
