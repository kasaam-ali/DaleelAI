"""LangGraph wrapper around the QA nodes. Falls back to run_qa when langgraph is absent."""

from typing import TypedDict

from app.agents.rag import (
    RagRequest,
    RagResult,
    _abstain,
    _blocks,
    _live_hits,
    _ranked_many,
    _result,
    _search_queries,
    _topic_statutes,
    _wanted_sections,
    attach_cross_reference,
    local_fast_answer,
    run_qa,
    settle_band,
    statute_note,
)
from app.core.budget import CallBudget
from app.core.retrieval.rewrite import retrieval_keep, usable_web_hits
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
    on_sources=None,
    on_status=None,
    live_search=None,
) -> RagResult:
    from langgraph.graph import END, START, StateGraph

    rules = link_rules or []
    fast = await local_fast_answer(
        search,
        request,
        rules=rules,
        domain=domain,
        k=k,
        domain_boost=domain_boost,
        on_delta=on_delta,
        on_sources=on_sources,
        on_status=on_status,
    )
    if fast is not None:
        return fast
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
        box["queries"] = await _search_queries(llm, request, budget)
        return {}

    async def retrieve_node(_state):
        box["ranked"] = await _ranked_many(
            search,
            score,
            box["queries"],
            collection="documents",
            tax_year=request.tax_year,
            domain=domain,
            k=k,
            keep=retrieval_keep(keep, len(box["queries"])),
            domain_boost=domain_boost,
            prefer=_wanted_sections(request),
            note_covers=bool(statute_note(request)),
        )
        box["fused"] = [hit for hit, _score in box["ranked"]]
        # The property note is the answer. Emit it before expansion and the model.
        spoken = statute_note(request)
        if spoken and box["ranked"] and on_delta is not None:
            await on_delta(spoken)
            box["note_sent"] = True
        return {}

    async def rerank_node(_state):
        return {}

    async def expand_node(_state):
        box["blocks"] = await _blocks(box["ranked"], sections, token_budget)
        return {}

    async def sufficiency(_state):
        if statute_note(request) and box["ranked"]:
            box["blocks"] = await _blocks(box["ranked"], sections, token_budget)
            box["mode"] = "verified"
            return {"next": "generate"}
        if _topic_statutes(box["ranked"], request):
            box["blocks"] = await _blocks(box["ranked"], sections, token_budget)
            box["mode"] = "verified"
            return {"next": "generate"}
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
            keep=retrieval_keep(keep, len(box["queries"])),
            domain_boost=domain_boost,
            token_budget=token_budget,
            queries=box["queries"],
        )
        box["ranked"] = ranked
        box["queries"] = queries
        if band == "sufficient" or _topic_statutes(ranked, request):
            box["blocks"] = await _blocks(ranked, sections, token_budget)
            box["mode"] = "verified"
            return {"next": "generate"}
        return {"next": "web_fallback"}

    async def web_fallback(_state):
        if not web_enabled:
            box["mode"] = "none"
            return {"next": "links"}
        ranked = usable_web_hits(
            await _ranked_many(
                search,
                score,
                box["queries"],
                collection="web_pages",
                tax_year=None,
                domain=domain,
                k=k,
                keep=web_keep,
                domain_boost=domain_boost,
            )
        )
        box["web_ranked"] = ranked
        top = ranked[0][1] if ranked else None
        if web_is_sufficient(top, minimum=web_minimum):
            box["ranked"] = ranked
            box["blocks"] = await _blocks(ranked, sections, token_budget)
            box["mode"] = "web"
            return {"next": "generate"}
        live_ranked = await _live_hits(live_search, box["queries"])
        if live_ranked:
            box["ranked"] = live_ranked
            box["web_ranked"] = live_ranked
            box["blocks"] = await _blocks(live_ranked, sections, token_budget)
            box["mode"] = "web"
            return {"next": "generate"}
        box["mode"] = "none"
        return {"next": "links"}

    async def generate(_state):
        from app.agents.answer import generate_answer
        from app.agents.rag import _emit_sources

        spoken = statute_note(request)
        if spoken and box["mode"] != "none":
            await _emit_sources(on_sources, box["ranked"], box["mode"])
            box["blocks"] = attach_cross_reference(box["blocks"], request)
            if on_delta is not None and not box.get("note_sent"):
                await on_delta(spoken)
            box["draft"] = spoken
            box["model"] = "none"
            return {}

        if box["mode"] == "none" or budget.remaining() < 2:
            box["mode"] = "none"
            box["draft"] = ""
            return {}

        await _emit_sources(on_sources, box["ranked"], box["mode"])
        box["blocks"] = attach_cross_reference(box["blocks"], request)
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
        from app.agents.answer import (
            blocks_mention_statute,
            finalize_supported_answer,
            verify_answer,
        )

        if blocks_mention_statute(box["blocks"]):
            box["draft"] = finalize_supported_answer(
                box["draft"],
                box["blocks"],
                question=request.question,
                search_query=request.search_query,
                language=request.language,
            )
            box["verified"] = False
            box["replaced"] = False
            box["confidence"] = "medium"
            return {}
        checked = await verify_answer(
            llm,
            draft=box["draft"],
            blocks=box["blocks"],
            mode=box["mode"],
            budget=budget,
        )
        box["draft"] = finalize_supported_answer(
            checked.answer,
            box["blocks"],
            question=request.question,
            search_query=request.search_query,
            language=request.language,
        )
        box["verified"] = checked.verified
        box["replaced"] = checked.replaced
        box["confidence"] = checked.confidence
        return {}

    async def links(_state):
        if box["mode"] == "none":
            from app.agents.rag import _emit_sources

            await _emit_sources(on_sources, box["web_ranked"], "web")
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
