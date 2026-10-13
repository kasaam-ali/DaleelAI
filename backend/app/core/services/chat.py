"""SSE chat. Retrieval is injected. With no QA runner the answer abstains."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date
from typing import Any
from uuid import uuid4

from app.agents.rag import RagResult
from app.agents.router import RouterParseError, RouterRequest, route
from app.api.v1.schemas import (
    ChatRequest,
    FinalData,
    MetaData,
    Source,
)
from app.core.budget import CallBudget
from app.core.cache import MemoryCache, answer_cache_key
from app.core.ports import LLMPort
from app.core.retrieval.action_links import ActionLinkRule, load_action_links, match_action_links
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE
from app.settings import CONFIG_DIR

QaRunner = Callable[[ChatRequest, str, str], Awaitable[RagResult]]

_REFUSAL = (
    "I can't help with hiding income, evading tax, or fake documents. "
    "For legal filing, use IRIS or call FBR at 051-111-772-772."
)
_NOT_READY = "That tool is not available yet."
_CHITCHAT = "Salam. Ask a tax question and I will answer from official FBR and SECP sources."
_OUT_OF_SCOPE = "That is outside tax and compliance. Ask about FBR or SECP and I can help."


def current_tax_year(today: date) -> str:
    """Tax year ends on 30 June and is named by the year it ends."""
    end_year = today.year if (today.month, today.day) <= (6, 30) else today.year + 1
    return f"TY{end_year}"


def stand_in_confidence(answer_source: str) -> str:
    """Not the dev-set logistic model. Web stays at medium. Abstain is low."""
    if answer_source == "none":
        return "low"
    return "medium"


async def iter_chat_events(
    body: ChatRequest,
    llm: LLMPort,
    *,
    today: date,
    corpus_version: str = "unindexed",
    corpus_date: str = "unindexed",
    qa: QaRunner | None = None,
    cache: MemoryCache | None = None,
    link_rules: list[ActionLinkRule] | None = None,
    calls_cap: int = 5,
) -> AsyncIterator[dict[str, Any]]:
    rules_path = CONFIG_DIR / "action_links.yaml"
    rules = link_rules if link_rules is not None else load_action_links(rules_path)
    tax_year = body.tax_year or current_tax_year(today)
    profile = body.profile.model_dump() if body.profile else None
    key = answer_cache_key(body.message, profile, tax_year, corpus_version)
    cached = _cached(cache, key)
    if cached is not None:
        for event in _replay(cached, tax_year):
            yield event
        return

    budget = CallBudget(cap=calls_cap)
    try:
        routed = await route(
            llm,
            RouterRequest(
                message=body.message,
                profile=profile,
                today=today,
                current_tax_year=current_tax_year(today),
            ),
            budget,
        )
    except RouterParseError as exc:
        yield {"event": "error", "data": {"code": "router_parse", "message": str(exc)}}
        yield {"event": "done", "data": {}}
        return

    language = routed.language
    if body.language != "auto" and language != "urdu":
        language = body.language
    if body.tax_year is None and routed.tax_year:
        tax_year = routed.tax_year
        key = answer_cache_key(body.message, profile, tax_year, corpus_version)
        cached = _cached(cache, key)
        if cached is not None:
            for event in _replay(cached, tax_year):
                yield event
            return

    yield _meta(routed.intent, language, tax_year)
    if routed.intent == "qa":
        try:
            result = await _qa_result(body, qa, routed, tax_year, corpus_date, budget)
        except Exception:
            yield {
                "event": "error",
                "data": {
                    "code": "qa_failed",
                    "message": "Search failed before an answer could be written.",
                },
            }
            yield {"event": "done", "data": {}}
            return
        library = "web" if result.answer_source == "web" else "verified"
        if result.answer_source == "none":
            library = "web"
        sources = [_source(hit, library) for hit in result.sources]
        yield {"event": "token", "data": {"text": result.answer}}
        yield {"event": "sources", "data": {"sources": sources}}
        yield {
            "event": "verification",
            "data": {
                "verified": result.verified,
                "unsupported": [],
                "replaced": result.replaced,
            },
        }
        final = _final(
            result.answer,
            result.answer_source,
            result.verified,
            result.model,
            tax_year,
            corpus_date,
            result.action_links,
        )
    else:
        answer = _short_reply(routed.intent, routed.authority)
        links = match_action_links(body.message, rules, domains=set())
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, links)
    payload = {"intent": routed.intent, "language": language, "final": final}
    if cache is not None:
        cache.put(key, payload)
    yield {"event": "final", "data": final}
    yield {"event": "done", "data": {}}


def format_sse(event: dict[str, Any]) -> str:
    data = json.dumps(event["data"], ensure_ascii=False)
    return f"event: {event['event']}\ndata: {data}\n\n"


def _cached(cache: MemoryCache | None, key: str) -> dict[str, Any] | None:
    if cache is None:
        return None
    return cache.get(key)


def _replay(cached: dict[str, Any], tax_year: str) -> list[dict[str, Any]]:
    final = FinalData.model_validate(cached["final"]).model_copy(update={"cached": True})
    return [
        _meta(cached["intent"], cached["language"], tax_year),
        {"event": "final", "data": final.model_dump()},
        {"event": "done", "data": {}},
    ]


def _meta(intent: str, language: str, tax_year: str) -> dict[str, Any]:
    data = MetaData(
        chat_id=str(uuid4()),
        message_id=str(uuid4()),
        intent=intent,  # type: ignore[arg-type]
        language=language,  # type: ignore[arg-type]
        tax_year=tax_year,
    )
    return {"event": "meta", "data": data.model_dump()}


async def _qa_result(
    body,
    qa,
    routed,
    tax_year: str,
    corpus_date: str,
    budget: CallBudget,
) -> RagResult:
    if qa is None:
        return RagResult(
            answer=ABSTAIN_SENTENCE,
            answer_source="none",
            verified=False,
            replaced=False,
            model="none",
        )
    return await qa(body, routed, tax_year, corpus_date, budget)


def _final(answer, answer_source, verified, model, tax_year, corpus_date, links) -> dict[str, Any]:
    return FinalData(
        answer=answer,
        answer_source=answer_source,
        confidence=stand_in_confidence(answer_source),  # type: ignore[arg-type]
        verified=verified,
        model=model,
        tax_year=tax_year,
        corpus_date=corpus_date,
        action_links=[link.model_dump() for link in links],
        follow_ups=[],
        cached=False,
    ).model_dump()


def _source(hit: RankedHit, library: str) -> dict[str, Any]:
    payload = hit.payload
    text = str(payload.get("text", ""))
    return Source(
        library=library,  # type: ignore[arg-type]
        doc_id=str(payload.get("doc_id") or hit.chunk_id),
        title=str(payload.get("doc_title") or payload.get("title") or ""),
        section=payload.get("section") or payload.get("heading"),
        page=payload.get("page_start"),
        url=str(payload.get("source_url") or payload.get("url") or ""),
        mirror_url=payload.get("mirror_url"),
        site=payload.get("site"),
        fetched_at=payload.get("fetched_at"),
        snippet=text[:300],
        rerank_score=None,
    ).model_dump()


def _short_reply(intent: str, authority: str | None) -> str:
    if intent == "refuse":
        return _REFUSAL
    if intent == "chitchat":
        return _CHITCHAT
    if intent == "out_of_scope":
        return _OUT_OF_SCOPE
    if intent == "provincial":
        name = authority or "the provincial revenue authority"
        return (
            f"This looks like a provincial matter for {name}. "
            "DaleelAI answers federal tax from FBR and SECP. "
            "Confirm the rule on that authority's site."
        )
    if intent == "notice":
        return "Upload the notice when the explainer is available. It is not available yet."
    return _NOT_READY
