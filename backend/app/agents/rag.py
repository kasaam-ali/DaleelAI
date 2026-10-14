"""QA path in node order. LangGraph, when installed, wraps these same steps."""

import asyncio
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.answer import generate_answer, verify_answer
from app.agents.grade import broaden_query, grade_context
from app.core.budget import CallBudget
from app.core.ports import LLMPort
from app.core.retrieval.action_links import ActionLink, ActionLinkRule, match_action_links
from app.core.retrieval.expand import expand_parents
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rerank import Scorer, rerank
from app.core.retrieval.retrieve import Searcher, retrieve
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE, verified_band, web_is_sufficient

AnswerSource = Literal["verified", "web", "none"]
SectionLookup = dict[str, str] | Callable[[list[str]], dict[str, str]]


class RagRequest(BaseModel):
    question: str
    search_query: str
    language: str
    tax_year: str
    corpus_date: str
    domains: set[str] = Field(default_factory=set)


class RagResult(BaseModel):
    answer: str
    answer_source: AnswerSource
    verified: bool
    replaced: bool
    model: str
    confidence: Literal["high", "medium", "low"] | None = None
    action_links: list[ActionLink] = Field(default_factory=list)
    sources: list[RankedHit] = Field(default_factory=list)
    retrieved: int = 0
    rerank_top: float | None = None


async def run_qa(
    llm: LLMPort,
    search: Searcher,
    score: Scorer,
    request: RagRequest,
    *,
    sections: SectionLookup | None = None,
    link_rules: list[ActionLinkRule] | None = None,
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
    """Verified library first. A borderline score gets one grade and at most one broader rewrite."""
    rules = link_rules or []
    budget = budget or CallBudget()
    queries = [request.search_query]
    ranked = await _ranked_many(
        search,
        score,
        queries,
        collection="documents",
        tax_year=request.tax_year,
        domain=domain,
        k=k,
        keep=keep,
        domain_boost=domain_boost,
    )
    band, ranked, queries = await settle_band(
        llm,
        search,
        score,
        request,
        ranked,
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
    if band == "sufficient":
        return await _answer(
            llm,
            request,
            ranked,
            "verified",
            sections,
            rules,
            budget,
            token_budget=token_budget,
            on_delta=on_delta,
        )
    web_ranked: list[tuple[RankedHit, float]] = []
    if web_enabled:
        web_ranked = await _ranked_many(
            search,
            score,
            queries,
            collection="web_pages",
            tax_year=None,
            domain=domain,
            k=k,
            keep=web_keep,
            domain_boost=domain_boost,
        )
        top = web_ranked[0][1] if web_ranked else None
        if web_is_sufficient(top, minimum=web_minimum):
            return await _answer(
                llm,
                request,
                web_ranked,
                "web",
                sections,
                rules,
                budget,
                token_budget=token_budget,
                on_delta=on_delta,
            )
    return _abstain(request, rules, web_ranked)


async def settle_band(
    llm,
    search,
    score,
    request: RagRequest,
    ranked: list[tuple[RankedHit, float]],
    sections: SectionLookup | None,
    budget: CallBudget,
    *,
    sufficient_at: float,
    borderline_at: float,
    domain: str | None,
    k: int,
    keep: int,
    domain_boost: float,
    token_budget: int,
) -> tuple[str, list[tuple[RankedHit, float]], list[str]]:
    """Grade only in the borderline band, then at most one broader search. No second grade."""
    queries = [request.search_query]
    band = _band_of(ranked, sufficient_at, borderline_at)
    if band != "borderline":
        return band, ranked, queries
    blocks = await _blocks(ranked, sections, token_budget)
    if await grade_context(llm, request.question, blocks, budget):
        return "sufficient", ranked, queries
    broader = await broaden_query(llm, request.search_query, budget)
    if not broader:
        return "insufficient", ranked, queries
    queries = [request.search_query, broader]
    retried = await _ranked_many(
        search,
        score,
        [broader],
        collection="documents",
        tax_year=request.tax_year,
        domain=domain,
        k=k,
        keep=keep,
        domain_boost=domain_boost,
    )
    retry_band = _band_of(retried, sufficient_at, borderline_at)
    if retry_band == "borderline":
        retry_band = "insufficient"
    if retry_band == "sufficient":
        return "sufficient", retried, queries
    return "insufficient", retried, queries


async def _ranked_many(
    search,
    score,
    queries: list[str],
    *,
    collection: str,
    tax_year: str | None,
    domain: str | None,
    k: int,
    keep: int,
    domain_boost: float,
) -> list[tuple[RankedHit, float]]:
    merged: list[RankedHit] = []
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
    anchor = queries[0] if queries else ""
    return await asyncio.to_thread(rerank, anchor, merged, score, pool=k, keep=keep)


async def _blocks(ranked, sections: SectionLookup | None, token_budget: int):
    hits = [hit for hit, _score in ranked]
    mapping = await _section_map(sections, hits)
    return expand_parents(hits, mapping, token_budget=token_budget)


async def _section_map(sections: SectionLookup | None, hits: list[RankedHit]) -> dict[str, str]:
    if isinstance(sections, dict) or not sections:
        return sections or {}
    parent_ids: list[str] = []
    for hit in hits:
        parent_id = str(hit.payload.get("parent_id") or "")
        if parent_id and parent_id not in parent_ids:
            parent_ids.append(parent_id)
    if not parent_ids:
        return {}
    return await asyncio.to_thread(sections, parent_ids)


async def _answer(
    llm,
    request,
    ranked,
    mode,
    sections,
    rules,
    budget: CallBudget,
    *,
    token_budget: int,
    on_delta=None,
) -> RagResult:
    if budget.remaining() < 2:
        return _abstain(request, rules, ranked if mode == "web" else [])
    blocks = await _blocks(ranked, sections, token_budget)
    generated = await generate_answer(
        llm,
        question=request.question,
        language=request.language,
        tax_year=request.tax_year,
        corpus_date=request.corpus_date,
        blocks=blocks,
        mode=mode,
        budget=budget,
        on_delta=on_delta,
    )
    checked = await verify_answer(
        llm,
        draft=generated.text,
        blocks=blocks,
        mode=mode,
        budget=budget,
    )
    return _result(
        request,
        rules,
        mode,
        checked.answer,
        checked.verified,
        checked.replaced,
        generated.model,
        ranked,
        confidence=checked.confidence,
    )


def _result(
    request, rules, mode, answer, verified, replaced, model, ranked, confidence=None
) -> RagResult:
    hits = [hit for hit, _score in ranked]
    top = ranked[0][1] if ranked else None
    return RagResult(
        answer=answer,
        answer_source=mode,
        verified=verified,
        replaced=replaced,
        model=model,
        confidence=confidence,
        action_links=_links(request, rules),
        sources=hits[:6],
        retrieved=len(ranked),
        rerank_top=top,
    )


def _abstain(request, rules, web_ranked: list[tuple[RankedHit, float]]) -> RagResult:
    return RagResult(
        answer=ABSTAIN_SENTENCE,
        answer_source="none",
        verified=False,
        replaced=False,
        model="none",
        action_links=_links(request, rules),
        sources=[hit for hit, _score in web_ranked[:3]],
        retrieved=len(web_ranked),
        rerank_top=web_ranked[0][1] if web_ranked else None,
    )


def _band_of(ranked, sufficient_at: float, borderline_at: float) -> str:
    top = ranked[0][1] if ranked else None
    return verified_band(top, sufficient_at=sufficient_at, borderline_at=borderline_at)


def _links(request: RagRequest, rules: list[ActionLinkRule]) -> list[ActionLink]:
    return match_action_links(request.question, rules, domains=request.domains)
