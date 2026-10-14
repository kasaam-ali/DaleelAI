"""LangGraph wrapper around the QA nodes. Falls back to run_qa when langgraph is absent."""

from typing import TypedDict

from app.agents.rag import (
    RagRequest,
    RagResult,
    _abstain,
    _blocks,
    _result,
    run_qa,
    settle_band,
)
from app.core.budget import CallBudget
from app.core.retrieval.sufficiency import web_is_sufficient


class _GraphState(TypedDict, total=False):
    next: str


QA_NODES = (
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


def langgraph_available() -> bool:
    try:
        import langgraph.graph  # noqa: F401
    except ImportError:
        return False
    return True


async def run_qa_graph(*args, runner: str = "langgraph", **kwargs) -> RagResult:
    """Use the StateGraph when langgraph is installed. Otherwise run the plain function."""
    if runner != "langgraph" or not langgraph_available():
        return await run_qa(*args, **kwargs)
    return await _invoke_graph(*args, **kwargs)


async def _invoke_graph(
    llm,
    search,
    score,
    request: RagRequest,
    *,
    sections=None,
    link_rules=None,
    budget: CallBudget | None = None,
    sufficient_at: float,
    borderline_at: float,
    web_minimum: float = 0.5,
    web_enabled: bool = True,
    domain: str | None = None,
    k: int = 30,
    keep: int = 6,
    web_keep: int = 5,
    domain_boost: float = 1.2,
    token_budget: int = 6000,
    on_delta=None,
) -> RagResult:
    from langgraph.graph import END, START, StateGraph

    from app.core.retrieval.synonyms import expand_search_query

    rules = link_rules or []
    budget = budget or CallBudget()
    box: dict = {
        "queries": [request.search_query],
        "ranked": [],
        "fused": [],
        "blocks": [],
        "web_ranked": [],
        "mode": "none",
        "draft": "",
        "model": "none",
        "verified": False,
        "replaced": False,
        "confidence": None,
        "result": None,
    }

    async def rewrite(_state):
        box["expanded"] = expand_search_query(request.search_query)
        return {}

    async def retrieve_node(_state):
        box["fused"] = await _fused(
            search,
            box["queries"],
            collection="documents",
            tax_year=request.tax_year,
            domain=domain,
            k=k,
            domain_boost=domain_boost,
        )
        return {}

    async def rerank_node(_state):
        box["ranked"] = await _rerank_hits(score, request.search_query, box["fused"], k, keep)
        return {}

    async def expand_node(_state):
        box["blocks"] = await _blocks(box["ranked"], sections, token_budget)
        return {}

    async def sufficiency(_state):
        band, ranked, queries = await settle_band(
            llm,
            search,
            score,
            request,
            box["ranked"],
            sections,
            budget,
            sufficient_at=sufficient_at,
            borderline_at=borderline_at,
            domain=domain,
            k=k,
            keep=keep,
            domain_boost=domain_boost,
            token_budget=token_budget,
        )
        box["ranked"] = ranked
        box["queries"] = queries
        if band == "sufficient":
            box["blocks"] = await _blocks(ranked, sections, token_budget)
            box["mode"] = "verified"
            return {"next": "generate"}
        return {"next": "web_fallback"}

    async def web_fallback(_state):
        if not web_enabled:
            box["mode"] = "none"
            return {"next": "links"}
        fused = await _fused(
            search,
            box["queries"],
            collection="web_pages",
            tax_year=None,
            domain=domain,
            k=k,
            domain_boost=domain_boost,
        )
        ranked = await _rerank_hits(score, box["queries"][0], fused, k, web_keep)
        box["web_ranked"] = ranked
        top = ranked[0][1] if ranked else None
        if web_is_sufficient(top, minimum=web_minimum):
            box["ranked"] = ranked
            box["blocks"] = await _blocks(ranked, sections, token_budget)
            box["mode"] = "web"
            return {"next": "generate"}
        box["mode"] = "none"
        return {"next": "links"}

    async def generate(_state):
        if box["mode"] == "none" or budget.remaining() < 2:
            box["mode"] = "none"
            box["draft"] = ""
            return {}
        from app.agents.answer import generate_answer

        generated = await generate_answer(
            llm,
            question=request.question,
            language=request.language,
            tax_year=request.tax_year,
            corpus_date=request.corpus_date,
            blocks=box["blocks"],
            mode=box["mode"],
            budget=budget,
            on_delta=on_delta,
        )
        box["draft"] = generated.text
        box["model"] = generated.model
        return {}

    async def verify(_state):
        if box["mode"] == "none":
            return {}
        from app.agents.answer import verify_answer

        checked = await verify_answer(
            llm,
            draft=box["draft"],
            blocks=box["blocks"],
            mode=box["mode"],
            budget=budget,
        )
        box["draft"] = checked.answer
        box["verified"] = checked.verified
        box["replaced"] = checked.replaced
        box["confidence"] = checked.confidence
        return {}

    async def links(_state):
        if box["mode"] == "none":
            box["result"] = _abstain(request, rules, box["web_ranked"])
            return {}
        box["result"] = _result(
            request,
            rules,
            box["mode"],
            box["draft"],
            box["verified"],
            box["replaced"],
            box["model"],
            box["ranked"],
            confidence=box.get("confidence"),
        )
        return {}

    graph = StateGraph(_GraphState)
    graph.add_node("rewrite", rewrite)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("expand", expand_node)
    graph.add_node("sufficiency", sufficiency)
    graph.add_node("web_fallback", web_fallback)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)
    graph.add_node("links", links)
    graph.add_edge(START, "rewrite")
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "expand")
    graph.add_edge("expand", "sufficiency")
    graph.add_conditional_edges(
        "sufficiency",
        lambda state: state["next"],
        {"generate": "generate", "web_fallback": "web_fallback"},
    )
    graph.add_conditional_edges(
        "web_fallback",
        lambda state: state["next"],
        {"generate": "generate", "links": "links"},
    )
    graph.add_edge("generate", "verify")
    graph.add_edge("verify", "links")
    graph.add_edge("links", END)
    await graph.compile().ainvoke({"next": "rewrite"})
    return box["result"]


async def _fused(search, queries, *, collection, tax_year, domain, k, domain_boost):
    from app.core.retrieval.retrieve import retrieve

    merged = []
    seen: set[str] = set()
    for query in queries:
        fused = await retrieve(
            search,
            query,
            collection=collection,
            tax_year=tax_year,
            domain=domain,
            k=k,
            domain_boost=domain_boost,
        )
        for hit, _score in fused:
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            merged.append(hit)
    return merged


async def _rerank_hits(score, query: str, hits, pool: int, keep: int):
    import asyncio

    from app.core.retrieval.rerank import rerank

    return await asyncio.to_thread(rerank, query, hits, score, pool=pool, keep=keep)
