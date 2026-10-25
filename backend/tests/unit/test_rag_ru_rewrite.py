"""Roman Urdu the lexicon cannot read is rewritten to English before search."""

import asyncio

from app.adapters.fakes import FakeLLM
from app.agents.rag import RagRequest, _search_queries
from app.core.budget import CallBudget


def _request(question: str, language: str) -> RagRequest:
    return RagRequest(
        question=question,
        search_query=question,
        language=language,
        tax_year="TY2026",
        corpus_date="2026-10-14",
    )


def test_unknown_roman_urdu_gets_an_english_query():
    llm = FakeLLM('{"queries": ["minimum tax on turnover Section 113"]}')
    queries = asyncio.run(_search_queries(llm, _request("dukaan ka tax kitna hai?", "roman_urdu"), CallBudget()))

    assert queries == ["minimum tax on turnover Section 113"]


def test_english_question_makes_no_model_call():
    budget = CallBudget()
    asyncio.run(_search_queries(FakeLLM("{}"), _request("minimum tax on turnover", "en"), budget))

    assert budget.used == 0
