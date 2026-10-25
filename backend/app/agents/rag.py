"""QA path in node order. LangGraph, when installed, wraps these same steps."""

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.answer import (
    blocks_mention_statute,
    finalize_supported_answer,
    generate_answer,
    verify_answer,
)
from app.agents.grade import broaden_query, grade_context
from app.core.budget import CallBudget
from app.core.ports import LLMPort
from app.core.retrieval.action_links import ActionLink, ActionLinkRule, match_action_links
from app.core.retrieval.expand import ContextBlock, expand_parents
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rerank import Scorer, rerank
from app.core.retrieval.retrieve import Searcher, retrieve
from app.core.retrieval.rewrite import (
    cross_reference_note,
    detect_topics,
    hit_section,
    is_generic_web_hit,
    _is_raw_desi,
    is_statutory_hit,
    matching_topic_sections,
    maybe_llm_queries,
    retrieval_keep,
    rewrite_queries,
    topics_for_note,
    usable_web_hits,
)
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE, verified_band, web_is_sufficient

log = logging.getLogger(__name__)

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
    on_sources=None,
    on_status=None,
    live_search=None,
) -> RagResult:
    """Local library first. A miss falls through to rewrite, rerank, and the model."""
    rules = link_rules or []
    budget = budget or CallBudget()
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
    queries = await _search_queries(llm, request, budget)
    topic_keep = retrieval_keep(keep, len(queries))
    prefer = _wanted_sections(request)
    note = statute_note(request)
    ranked = await _ranked_many(
        search,
        score,
        queries,
        collection="documents",
        tax_year=request.tax_year,
        domain=domain,
        k=k,
        keep=topic_keep,
        domain_boost=domain_boost,
        prefer=prefer,
        note_covers=bool(note),
    )
    if note and ranked:
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
            on_sources=on_sources,
        )
    if _topic_statutes(ranked, request):
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
            on_sources=on_sources,
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
        keep=topic_keep,
        domain_boost=domain_boost,
        token_budget=token_budget,
        queries=queries,
    )
    if band == "sufficient" or _topic_statutes(ranked, request):
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
            on_sources=on_sources,
        )
    web_ranked: list[tuple[RankedHit, float]] = []
    if web_enabled:
        web_ranked = usable_web_hits(
            await _ranked_many(
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
                on_sources=on_sources,
            )
        live_ranked = await _live_hits(live_search, queries)
        if live_ranked:
            return await _answer(
                llm,
                request,
                live_ranked,
                "web",
                sections,
                rules,
                budget,
                token_budget=token_budget,
                on_delta=on_delta,
                on_sources=on_sources,
            )
    await _emit_sources(on_sources, web_ranked, "web")
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
    queries: list[str] | None = None,
) -> tuple[str, list[tuple[RankedHit, float]], list[str]]:
    """Grade only in the borderline band, then at most one broader search. No second grade."""
    queries = list(queries or rewrite_queries(request.question, request.search_query))
    band = _band_of(ranked, sufficient_at, borderline_at)
    if band != "borderline":
        return band, ranked, queries
    blocks = await _blocks(ranked, sections, token_budget)
    if await grade_context(llm, request.question, blocks, budget):
        return "sufficient", ranked, queries
    broader = await broaden_query(llm, request.search_query, budget)
    if not broader:
        return "insufficient", ranked, queries
    queries = [*queries, broader]
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
    prefer: set[str] | None = None,
    note_covers: bool = False,
) -> list[tuple[RankedHit, float]]:
    """Search until the wanted sections are in hand, then skip the cross-encoder."""
    if not queries:
        return []
    started = time.perf_counter()
    pool = min(k, 12)
    merged: list[RankedHit] = []
    seen: set[str] = set()
    searched = 0
    quota = 4 if len(queries) > 1 else pool
    for query in queries:
        fused = await retrieve(
            search,
            query,
            collection=collection,
            tax_year=tax_year,
            domain=domain,
            k=pool,
            domain_boost=domain_boost,
        )
        searched += 1
        fresh: list[RankedHit] = []
        for hit, _score in fused:
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            fresh.append(hit)
        kept: list[RankedHit] = []
        for hit in fresh:
            if prefer and hit_section(hit) in prefer:
                kept.append(hit)
                continue
            if len(kept) < quota:
                kept.append(hit)
        merged.extend(kept)
        if len(merged) > pool:
            merged = merged[:pool]
        if _sections_covered(merged, prefer) or len(merged) >= pool:
            break
        # The property note already states every missing section. Another embed
        # plus the cross-encoder is what sat in front of the first token.
        if note_covers and _has_preferred(merged, prefer):
            break
    if not merged:
        return []
    search_ms = int((time.perf_counter() - started) * 1000)
    limit = min(keep, pool)
    if _sections_covered(merged, prefer) or (note_covers and _has_preferred(merged, prefer)):
        ranked = [(hit, 1.0) for hit in _one_per_section(merged, prefer or set())][:limit]
        rerank_ms = 0
        chunks = len(ranked)
    else:
        inputs = _rerank_inputs(merged, prefer)
        rerank_started = time.perf_counter()
        ranked = await asyncio.to_thread(
            rerank,
            queries[0],
            inputs,
            score,
            pool=len(inputs),
            keep=min(limit, len(inputs)),
        )
        if prefer:
            preferred = [item for item in ranked if hit_section(item[0]) in prefer]
            other = [item for item in ranked if hit_section(item[0]) not in prefer]
            ranked = preferred + other
        rerank_ms = int((time.perf_counter() - rerank_started) * 1000)
        chunks = len(inputs)
    log.warning(
        "retrieval_ms=%d rerank_ms=%d queries=%d chunks=%d",
        search_ms,
        rerank_ms,
        searched,
        chunks,
    )
    return ranked[:limit]


def statute_note(request: RagRequest) -> str:
    """Property and freelancer law is already written. A model restatement waits out the timeout.

    The search query is not part of this choice. A cash-withdrawal rewrite names
    Section 37 and "plot", and that text must not select the property note.
    """
    question = request.question
    keys = {topic.key for topic in topics_for_note(question)}
    if "property" not in keys and "freelancer" not in keys:
        return ""
    return cross_reference_note(question, language=request.language)


async def local_fast_answer(
    search,
    request: RagRequest,
    *,
    rules,
    domain: str | None,
    k: int,
    domain_boost: float,
    on_delta=None,
    on_sources=None,
    on_status=None,
) -> RagResult | None:
    """Speak a curated note before any index call. Search only fills sources.

    `documents` first. `web_pages` only when the library has no hit. No rerank,
    no live web, and no model. A question with no curated note returns None so
    the heavier path can run.
    """
    note = statute_note(request)
    if not note:
        return None
    if on_status is not None:
        await on_status("retrieve")
    if on_delta is not None:
        await on_delta(note)
    queries = rewrite_queries(request.question, request.search_query)[:1]
    query = queries[0] if queries else request.search_query
    documents = await retrieve(
        search,
        query,
        collection="documents",
        tax_year=request.tax_year,
        domain=domain,
        k=min(k, 8),
        domain_boost=domain_boost,
    )
    mode: Literal["verified", "web"] = "verified"
    ranked = documents
    if not ranked:
        web = usable_web_hits(
            await retrieve(
                search,
                query,
                collection="web_pages",
                tax_year=None,
                domain=domain,
                k=min(k, 8),
                domain_boost=domain_boost,
            )
        )
        if web:
            mode = "web"
            ranked = web
    answer_source, verified, confidence = _citation_trust(ranked, mode)
    if answer_source == "none":
        ranked = []
    await _emit_sources(on_sources, ranked, answer_source)
    return _result(
        request,
        rules,
        answer_source,
        note,
        verified,
        False,
        "none",
        ranked,
        confidence=confidence,
    )


def _has_preferred(hits: list[RankedHit], prefer: set[str] | None) -> bool:
    if not prefer:
        return False
    return bool(prefer & {hit_section(hit) for hit in hits})


def _sections_covered(hits: list[RankedHit], prefer: set[str] | None) -> bool:
    if not prefer:
        return False
    return prefer <= {hit_section(hit) for hit in hits}


def _one_per_section(hits: list[RankedHit], prefer: set[str]) -> list[RankedHit]:
    chosen: list[RankedHit] = []
    seen: set[str] = set()
    for hit in hits:
        section = hit_section(hit)
        if section not in prefer or section in seen:
            continue
        seen.add(section)
        chosen.append(hit)
    return chosen


def _rerank_inputs(merged: list[RankedHit], prefer: set[str] | None) -> list[RankedHit]:
    """At most six chunks. Labeled sections go in first when the set is incomplete."""
    if not prefer:
        return merged[:6]
    labeled = _one_per_section(merged, prefer)
    if not labeled:
        return merged[:6]
    others = [hit for hit in merged if hit_section(hit) not in prefer]
    return (labeled + others)[:6]


async def _blocks(ranked, sections: SectionLookup | None, token_budget: int):
    hits = [hit for hit, _score in ranked]
    mapping = await _section_map(sections, hits)
    share = max(400, token_budget // max(1, len(hits)))
    return expand_parents(hits, mapping, token_budget=token_budget, max_block_tokens=share)


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
    on_sources=None,
) -> RagResult:
    spoken = statute_note(request)
    if spoken:
        answer_source, verified, confidence = _citation_trust(ranked, mode)
        if answer_source == "none":
            ranked = []
        await _emit_sources(on_sources, ranked, answer_source)
        if on_delta is not None:
            await on_delta(spoken)
        return _result(
            request,
            rules,
            answer_source,
            spoken,
            verified,
            False,
            "none",
            ranked,
            confidence=confidence,
        )
    if budget.remaining() < 2:
        return _abstain(request, rules, ranked if mode == "web" else [])
    await _emit_sources(on_sources, ranked, mode)
    blocks = attach_cross_reference(await _blocks(ranked, sections, token_budget), request)
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
    # Statutory context is enough. A judge call here only delays the stream (often a 429).
    if blocks_mention_statute(blocks):
        answer = finalize_supported_answer(
            generated.text,
            blocks,
            question=request.question,
            search_query=request.search_query,
            language=request.language,
        )
        return _result(
            request,
            rules,
            mode,
            answer,
            False,
            False,
            generated.model,
            ranked,
            confidence="medium",
        )
    checked = await verify_answer(
        llm,
        draft=generated.text,
        blocks=blocks,
        mode=mode,
        budget=budget,
    )
    answer = finalize_supported_answer(
        checked.answer,
        blocks,
        question=request.question,
        search_query=request.search_query,
        language=request.language,
    )
    return _result(
        request,
        rules,
        mode,
        answer,
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


async def _search_queries(llm, request: RagRequest, budget: CallBudget) -> list[str]:
    """Lexicon queries first. Roman Urdu the lexicon cannot read gets one English rewrite.

    The corpus is English, so a raw Roman Urdu query retrieves nothing.
    """
    queries = rewrite_queries(request.question, request.search_query)
    if request.language != "roman_urdu" or detect_topics(request.question):
        return queries
    english = await maybe_llm_queries(llm, request.question, budget)
    return (english + [q for q in queries if not _is_raw_desi(q)])[:4] or queries


def attach_cross_reference(blocks: list[ContextBlock], request: RagRequest) -> list[ContextBlock]:
    note = cross_reference_note(request.question)
    if not note:
        return blocks
    return [ContextBlock(parent_id="cross-reference", text=note), *blocks]


async def _live_hits(live_search, queries: list[str]) -> list[tuple[RankedHit, float]]:
    """Public web, capped at 2.5s. Homepages never enter the pool."""
    if live_search is None:
        return []
    query = " ".join(queries)[:300]
    try:
        snippets = await asyncio.wait_for(live_search(query), timeout=2.5)
    except Exception:
        log.info("live_web_unavailable")
        return []
    ranked: list[tuple[RankedHit, float]] = []
    for index, snippet in enumerate(snippets or []):
        if not isinstance(snippet, dict):
            continue
        hit = RankedHit(
            chunk_id=f"live-{index}",
            payload={
                "text": str(snippet.get("text") or "")[:500],
                "source_url": str(snippet.get("url") or ""),
                "url": str(snippet.get("url") or ""),
                "title": str(snippet.get("title") or ""),
                "doc_title": str(snippet.get("title") or ""),
            },
        )
        if is_generic_web_hit(hit) or not hit.payload["text"]:
            continue
        ranked.append((hit, 0.51))
        if len(ranked) == 3:
            break
    return ranked


def _wanted_sections(request: RagRequest) -> set[str]:
    blob = f"{request.question} {request.search_query}"
    return {section.upper() for topic in detect_topics(blob) for section in topic.sections}


def _topic_statutes(ranked: list[tuple[RankedHit, float]], request: RagRequest) -> bool:
    """A labeled ordinance section is enough to answer. Do not spend a grade call first."""
    hits = [hit for hit, _score in ranked]
    blob = f"{request.question} {request.search_query}"
    if matching_topic_sections(hits, blob):
        return True
    return bool(detect_topics(blob)) and any(is_statutory_hit(hit) for hit in hits)


def _band_of(ranked, sufficient_at: float, borderline_at: float) -> str:
    top = ranked[0][1] if ranked else None
    return verified_band(top, sufficient_at=sufficient_at, borderline_at=borderline_at)


def _citation_trust(
    ranked: list[tuple[RankedHit, float]], mode: str
) -> tuple[Literal["verified", "web", "none"], bool, Literal["high", "medium", "low"]]:
    """Verified and high confidence require a retrieved ordinance section."""
    statutes: list[RankedHit] = []
    pages: list[RankedHit] = []
    for hit, _score in ranked:
        if not str(hit.payload.get("text") or "").strip():
            continue
        if hit_section(hit):
            statutes.append(hit)
        elif str(hit.payload.get("source_url") or hit.payload.get("url") or "").strip():
            pages.append(hit)
    if mode == "web" and (statutes or pages):
        return "web", False, "medium"
    if statutes:
        return "verified", True, "high"
    if pages:
        return "web", False, "medium"
    return "none", False, "low"


def _links(request: RagRequest, rules: list[ActionLinkRule]) -> list[ActionLink]:
    return match_action_links(request.question, rules, domains=request.domains)


async def _emit_sources(on_sources, ranked, mode: str) -> None:
    if on_sources is None or not ranked:
        return
    hits = [hit for hit, _score in ranked]
    maybe = on_sources(hits, mode)
    if asyncio.iscoroutine(maybe) or inspect.isawaitable(maybe):
        await maybe
