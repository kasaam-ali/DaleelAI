import pytest

from app.agents.rag import run_qa
from app.agents.rag_graph import QA_NODES, langgraph_available, run_qa_graph
from tests.unit.test_rag import RULES, LibrarySearch, ScriptedLLM, hit, request, score_library


def test_graph_lists_the_spec_nodes():
    assert QA_NODES == (
        "rewrite",
        "retrieve",
        "rerank",
        "expand",
        "sufficiency",
        "web_fallback",
        "generate",
        "verify",
        "links",
    )


async def test_graph_entrypoint_matches_the_plain_path(monkeypatch):
    import app.agents.rag_graph as graph

    monkeypatch.setattr(graph, "langgraph_available", lambda: False)
    search = LibrarySearch({"documents": [hit("s149", "verified law about NTN")]})
    llm = ScriptedLLM("You register for an NTN on IRIS [1].")

    result = await run_qa_graph(
        llm,
        search,
        score_library("verified"),
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )
    plain = await run_qa(
        llm,
        search,
        score_library("verified"),
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == plain.answer_source == "verified"
    assert result.answer == plain.answer


async def test_installed_graph_answers_when_the_package_is_present():
    if not langgraph_available():
        pytest.skip("langgraph is not installed in this image")
    search = LibrarySearch({"documents": [hit("s149", "verified law about NTN")]})
    llm = ScriptedLLM("You register for an NTN on IRIS [1].")

    result = await run_qa_graph(
        llm,
        search,
        score_library("verified"),
        request(),
        link_rules=RULES,
        sufficient_at=0.7,
        borderline_at=0.4,
    )

    assert result.answer_source == "verified"
    assert result.verified is True
