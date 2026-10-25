"""SPEC §5.2: main answer prose carries no section numbers; sources still do."""

import re

import pytest

from app.agents.rag import RagRequest, run_qa
from app.core.plain_answer import plain_answer
from app.core.retrieval.fusion import RankedHit
from tests.integration.test_chat import ScriptedLLM as RouterLLM
from tests.integration.test_chat import make_client, parse_sse, router_payload
from tests.unit.test_rag import LibrarySearch, ScriptedLLM

SECTION = re.compile(r"§|\bs\.\s?\d|\bsections?\s+\d", re.I)

CASES = [
    (
        "When is the income tax return filing deadline?",
        "Section 114",
        "114",
        "You must file your return by 30 September under Section 114 of the "
        "Income Tax Ordinance, 2001 [1]. Late filing (Section 182) can bring a penalty [1].",
    ),
    (
        "How is tax on my salary deducted?",
        "Section 149",
        "149",
        "Your employer deducts tax from your salary every month as per Section 149 [1]. "
        "The rates come from Division I of the First Schedule (s.149) [1].",
    ),
]


@pytest.mark.parametrize(("question", "law", "number", "draft"), CASES)
def test_main_answer_hides_sections_but_sources_keep_them(question, law, number, draft):
    doc = RankedHit(
        chunk_id=f"ito-{number}",
        domain="income_tax",
        payload={
            "text": f"{law}. verified law text",
            "parent_id": f"ito-{number}",
            "doc_title": "Income Tax Ordinance, 2001",
            "section": number,
        },
    )

    async def qa(body, routed, tax_year, corpus_date, budget, **kwargs):
        del budget, kwargs
        request = RagRequest(
            question=body.message,
            search_query=body.message,
            language=routed.language,
            tax_year=tax_year,
            corpus_date=corpus_date,
        )
        return await run_qa(
            ScriptedLLM(draft),
            LibrarySearch({"documents": [doc]}),
            lambda _q, texts: [0.9 for _ in texts],
            request,
            sufficient_at=0.7,
            borderline_at=0.4,
        )

    client = make_client(RouterLLM(router_payload()), qa=qa)
    events = parse_sse(client.post("/api/v1/chat", json={"message": question}).text)
    final = next(data for name, data in events if name == "final")
    sources = next(data for name, data in events if name == "sources")["sources"]
    tokens = "".join(data["text"] for name, data in events if name == "token")
    print(
        "\nANSWER:",
        final["answer"],
        "\nSOURCES:",
        [(s["title"], s["section"], s["snippet"][:20]) for s in sources],
    )
    assert not SECTION.search(final["answer"])
    assert not SECTION.search(tokens)
    assert "[1]" in final["answer"]
    assert any(number in str(s["section"]) + s["snippet"] for s in sources)


def test_plain_answer_roman_urdu():
    text = (
        "Return Section 114 ke tehat 30 September tak file hoti hai [1]. "
        "Section 236K ka advance tax lagta hai."
    )
    out = plain_answer(text, "roman_urdu")
    assert out == "Return 30 September tak file hoti hai [1]. Advance tax lagta hai."
