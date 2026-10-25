"""SSE chat. Retrieval is injected. With no QA runner the answer abstains."""

import asyncio
import inspect
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.agents.answer import sanitize_answer
from app.agents.rag import RagResult
from app.agents.router import is_prompt_injection, lexicon_route, resolve_reply_language
from app.api.v1.schemas import (
    AgentTrace,
    ChatRequest,
    FinalData,
    MetaData,
    Source,
)
from app.core.budget import CallBudget
from app.core.cache import MemoryCache, answer_cache_key
from app.core.demo import demo_in_language, match_demo
from app.core.plain_answer import plain_answer, plain_delta
from app.core.ports import LLMPort
from app.core.privacy.pii import outbound_pii, redact_pii
from app.core.retrieval.action_links import ActionLinkRule, load_action_links, match_action_links
from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.rewrite import rewrite_search_query
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE
from app.settings import CONFIG_DIR

QaRunner = Callable[[ChatRequest, str, str], Awaitable[RagResult]]

_REFUSAL = (
    "I can't help with hiding income, evading tax, or fake documents. "
    "For legal filing, use IRIS or call FBR at 051-111-772-772."
)
_INJECTION_REFUSAL = (
    "I can't ignore the rules or reveal a hidden prompt. "
    "Ask a tax question and I will answer from the ordinance."
)
_INJECTION_REFUSAL_RU = (
    "Main qawaid nahi chhod sakta aur chhupa hua prompt nahi dikha sakta. "
    "Tax ka sawal poochain, main ordinance se jawab doonga."
)
_REFUSAL_RU = (
    "Main income chhupane, tax se bachne, ya fake documents mein madad nahi kar sakta. "
    "Qanooni filing ke liye IRIS istemal karein ya FBR ko 051-111-772-772 par call karein."
)
_NOT_READY = "That tool is not available yet."
_NOT_READY_RU = "Yeh tool abhi dastiyab nahi."
_CHITCHAT = "Salam. Ask a tax question and I will answer from official FBR and SECP sources."
_CHITCHAT_RU = "Salam. Tax ka sawal poochain. Main FBR aur SECP ke sarkari sources se jawab doonga."
_OUT_OF_SCOPE = "That is outside tax and compliance. Ask about FBR or SECP and I can help."
_OUT_OF_SCOPE_RU = (
    "Yeh tax aur compliance se bahar hai. "
    "FBR ya SECP ke bare mein poochain, main madad kar sakta hoon."
)
_STATUTE = re.compile(r"^\d{1,3}[A-Z]{0,4}$")
_HEADER_STATUTE = re.compile(r"\b(?:Section|Rule|Regulation)\s+(\d{1,3}[A-Z]{0,4})\b", re.I)
log = logging.getLogger(__name__)


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
    session_id: str | None = None,
    store=None,
    classifier=None,
) -> AsyncIterator[dict[str, Any]]:
    body = body.model_copy(update={"message": redact_pii(body.message)})
    rules_path = CONFIG_DIR / "action_links.yaml"
    rules = link_rules if link_rules is not None else load_action_links(rules_path)
    tax_year = body.tax_year or current_tax_year(today)
    profile = body.profile.model_dump() if body.profile else None
    session = _uuid_or_none(session_id)
    message_id = _message_id(session, body.client_request_id)
    chat_id = _uuid_or_none(body.chat_id) or (
        str(uuid5(NAMESPACE_URL, f"chat:{message_id}")) if body.client_request_id else str(uuid4())
    )
    saved = await _saved_turn(store, session, message_id, body.client_request_id)
    if saved is not None:
        for event in _saved_events(saved, tax_year, corpus_date):
            yield event
        return
    demo = match_demo(body.message)
    if demo is not None:
        if body.language in {"en", "roman_urdu", "urdu"}:
            asked = "roman_urdu" if body.language == "urdu" else body.language
            demo = demo_in_language(demo, asked)
        async for event in _yield_demo(
            store, session, chat_id, message_id, body.message, demo, tax_year, corpus_date
        ):
            yield event
        return
    language_key = resolve_reply_language(body.message, body.language, "en")
    key = answer_cache_key(body.message, profile, tax_year, corpus_version, language_key)
    hide_cache = outbound_pii(body.message) is not None
    cached = None if hide_cache else _cached(cache, key)
    if cached is not None:
        async for event in _yield_cached(
            store, session, chat_id, message_id, body.message, cached, tax_year
        ):
            yield event
        return

    budget = CallBudget(cap=calls_cap)
    deadline = time.monotonic() + _request_limit_s(llm)
    routed = lexicon_route(body.message)
    log.info("route=lexicon intent=%s", routed.intent)

    if time.monotonic() >= deadline:
        yield {
            "event": "error",
            "data": {"code": "qa_failed", "message": "The answer took too long."},
        }
        yield {"event": "done", "data": {}}
        return

    language = resolve_reply_language(body.message, body.language, routed.language)
    routed = routed.model_copy(update={"language": language})
    if routed.intent == "notice" and _explanatory_notice(body.message):
        routed = routed.model_copy(
            update={
                "intent": "qa",
                "search_query": routed.search_query
                or "FBR notice income tax return discrepancy section 122 section 114 IRIS reply",
            }
        )
    if routed.intent == "qa":
        routed = routed.model_copy(
            update={
                "search_query": _enrich_search_query(
                    body.message, routed.search_query or body.message
                )
            }
        )
    if body.tax_year is None and routed.tax_year:
        tax_year = routed.tax_year
        key = answer_cache_key(body.message, profile, tax_year, corpus_version, language)
        cached = None if hide_cache else _cached(cache, key)
        if cached is not None:
            async for event in _yield_cached(
                store, session, chat_id, message_id, body.message, cached, tax_year
            ):
                yield event
            return

    yield _meta(routed.intent, language, tax_year, chat_id, message_id)
    stored_sources: list[dict[str, Any]] = []
    if routed.intent == "qa":
        started = time.perf_counter()
        result = None
        failure: Exception | None = None
        emitted = 0
        streamed: list[str] = []
        collected_sources: list[dict[str, Any]] = []
        sources_sent = False

        async def on_sources(hits, library) -> None:
            nonlocal sources_sent
            collected_sources[:] = [_source(hit, library) for hit in hits[:6]]
            if _accepts_on_delta(qa) and not sources_sent:
                sources_sent = True
                await pieces.put(("sources", list(collected_sources)))

        if _accepts_on_delta(qa):
            pieces: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()

            async def on_delta(text: str) -> None:
                if text:
                    await pieces.put(("token", text))

            async def on_status(node: str) -> None:
                await pieces.put(("step", {"node": node, "status": "start"}))

            async def produce() -> None:
                nonlocal result, failure
                try:
                    result = await _qa_result(
                        body,
                        qa,
                        routed,
                        tax_year,
                        corpus_date,
                        budget,
                        on_delta=on_delta,
                        on_sources=on_sources,
                        on_status=on_status,
                    )
                except Exception as exc:
                    failure = exc
                finally:
                    await pieces.put(None)

            task = asyncio.create_task(produce())
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = TimeoutError()
                    break
                try:
                    item = await asyncio.wait_for(pieces.get(), remaining)
                except TimeoutError:
                    failure = TimeoutError()
                    break
                if item is None:
                    break
                kind, data = item
                if kind == "step":
                    yield {"event": "step", "data": data}
                    continue
                if kind == "sources":
                    stored_sources = data
                    yield {"event": "sources", "data": {"sources": data}}
                    continue
                emitted += 1
                streamed.append(data)
                yield {"event": "token", "data": {"text": plain_delta(data, language)}}
            if not task.done():
                task.cancel()
            try:
                await asyncio.wait_for(task, 1)
            except (TimeoutError, asyncio.CancelledError):
                pass
        else:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = TimeoutError()
            else:
                try:
                    result = await asyncio.wait_for(
                        _qa_result(
                            body,
                            qa,
                            routed,
                            tax_year,
                            corpus_date,
                            budget,
                            on_sources=on_sources,
                        ),
                        remaining,
                    )
                except TimeoutError:
                    failure = TimeoutError()
                except Exception as exc:
                    failure = exc
        if failure is not None or result is None:
            if streamed:
                draft = plain_answer(sanitize_answer("".join(streamed), language), language)
                stored_sources = collected_sources
                final = _final(
                    draft,
                    "verified" if stored_sources else "none",
                    False,
                    "none",
                    tax_year,
                    corpus_date,
                    [],
                    confidence="medium" if stored_sources else "low",
                )
                await _save_turn(
                    store,
                    session_id=session,
                    chat_id=chat_id,
                    message_id=message_id,
                    user_text=body.message,
                    intent=routed.intent,
                    language=language,
                    final=final,
                    sources=stored_sources,
                )
                if stored_sources and not sources_sent:
                    yield {"event": "sources", "data": {"sources": stored_sources}}
                yield {
                    "event": "verification",
                    "data": {"verified": False, "unsupported": [], "replaced": False},
                }
                yield {"event": "final", "data": final}
                yield {"event": "done", "data": {}}
                return
            yield {
                "event": "error",
                "data": {
                    "code": "qa_failed",
                    "message": (
                        "The answer took too long."
                        if isinstance(failure, TimeoutError)
                        else "Search failed before an answer could be written."
                    ),
                },
            }
            yield {"event": "done", "data": {}}
            return
        if emitted == 0:
            yield {"event": "token", "data": {"text": plain_answer(result.answer, language)}}
        library = "web" if result.answer_source == "web" else "verified"
        if result.answer_source == "none":
            library = "web"
        if not sources_sent:
            stored_sources = [_source(hit, library) for hit in result.sources]
            yield {"event": "sources", "data": {"sources": stored_sources}}
        elif result.sources:
            stored_sources = [_source(hit, library) for hit in result.sources]
        yield {
            "event": "verification",
            "data": {
                "verified": result.verified,
                "unsupported": [],
                "replaced": result.replaced,
            },
        }
        final = _final(
            plain_answer(result.answer, language),
            result.answer_source,
            result.verified,
            result.model,
            tax_year,
            corpus_date,
            result.action_links,
            confidence=result.confidence,
            trace=_trace(
                routed.intent,
                routed.search_query or body.message,
                started,
                retrieved=result.retrieved,
                rerank_top=result.rerank_top,
                verified=result.verified,
            ),
        )
    elif routed.intent in {"calculate", "compare_filer"}:
        from app.core.tax_engine import chat_tool

        card_type, card, answer = chat_tool(routed.intent, body.message, tax_year, routed.params)
        if card_type is not None and card is not None:
            yield {"event": "tool_result", "data": {"card": {"type": card_type, "data": card}}}
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, [])
    elif routed.intent in {"notice", "checklist"}:
        if routed.intent == "notice":
            from app.core.services.notice import notice_prompt

            card_type, card, answer = notice_prompt()
        else:
            from app.core.services.checklists import checklist_from_chat

            card_type, card, answer = checklist_from_chat(body.message, language, store, session)
        if card_type is not None and card is not None:
            yield {"event": "tool_result", "data": {"card": {"type": card_type, "data": card}}}
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, [])
    elif routed.intent == "find_expert":
        from app.core.services.experts import city_in_text, find_experts

        card = find_experts(
            body.message,
            city=routed.params.get("city") or city_in_text(body.message),
            category=routed.params.get("category"),
            classifier=classifier,
        )
        answer = card["advice_ru"] if language == "roman_urdu" else card["advice"]
        yield {"event": "tool_result", "data": {"card": {"type": "experts", "data": card}}}
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, [])
    elif routed.intent == "updates":
        from app.core.services.updates import list_updates, memory_updates

        updates_store = (
            store
            if store is not None and hasattr(store, "list_notifications")
            else memory_updates()
        )
        card = list_updates(
            updates_store,
            doc_type="all",
            domain=str(routed.params.get("domain") or "all"),
            page=1,
            limit=5,
        )
        if card["items"]:
            answer = "Recent FBR updates: " + "; ".join(item["title"] for item in card["items"])
        else:
            answer = "No FBR updates are stored yet. Open Updates and run the saved replay."
        yield {"event": "tool_result", "data": {"card": {"type": "updates", "data": card}}}
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, [])
    else:
        answer = _short_reply(routed.intent, routed.authority, language, body.message)
        links = match_action_links(body.message, rules, domains=set())
        yield {"event": "token", "data": {"text": answer}}
        final = _final(answer, "none", False, "none", tax_year, corpus_date, links)
    payload = {
        "intent": routed.intent,
        "language": language,
        "final": final,
        "sources": stored_sources,
    }
    if (
        cache is not None
        and not hide_cache
        and outbound_pii(str(final.get("answer") or "")) is None
    ):
        cache.put(key, payload)
    await _save_turn(
        store,
        session_id=session,
        chat_id=chat_id,
        message_id=message_id,
        user_text=body.message,
        intent=routed.intent,
        language=language,
        final=final,
        sources=stored_sources,
    )
    yield {"event": "final", "data": final}
    yield {"event": "done", "data": {}}


def format_sse(event: dict[str, Any]) -> str:
    data = json.dumps(event["data"], ensure_ascii=False)
    return f"event: {event['event']}\ndata: {data}\n\n"


def _request_limit_s(llm) -> float:
    """Wall clock for the whole reply. A single model call keeps its own timeout_s."""
    override = getattr(llm, "request_limit_s", None)
    if isinstance(override, (int, float)) and override > 0:
        return float(override)
    retry = getattr(getattr(llm, "_config", None), "retry", None)
    timeout = getattr(retry, "timeout_s", None)
    if isinstance(timeout, (int, float)) and timeout > 0:
        return max(150.0, float(timeout) + 75.0)
    return 150.0


def _cached(cache: MemoryCache | None, key: str) -> dict[str, Any] | None:
    if cache is None:
        return None
    return cache.get(key)


def _replay(
    cached: dict[str, Any], tax_year: str, chat_id: str, message_id: str
) -> list[dict[str, Any]]:
    final = FinalData.model_validate(cached["final"]).model_copy(update={"cached": True})
    events = [_meta(cached["intent"], cached["language"], tax_year, chat_id, message_id)]
    sources = cached.get("sources") or []
    if sources:
        events.append({"event": "sources", "data": {"sources": sources}})
    events.append({"event": "final", "data": final.model_dump()})
    events.append({"event": "done", "data": {}})
    return events


async def _yield_cached(store, session, chat_id, message_id, user_text, cached, tax_year):
    events = _replay(cached, tax_year, chat_id, message_id)
    final_event = next(event for event in events if event["event"] == "final")
    for event in events:
        yield event
    await _save_turn(
        store,
        session_id=session,
        chat_id=chat_id,
        message_id=message_id,
        user_text=user_text,
        intent=cached["intent"],
        language=cached["language"],
        final=final_event["data"],
        sources=cached.get("sources") or [],
    )


def _meta(
    intent: str, language: str, tax_year: str, chat_id: str, message_id: str
) -> dict[str, Any]:
    data = MetaData(
        chat_id=chat_id,
        message_id=message_id,
        intent=intent,  # type: ignore[arg-type]
        language=language,  # type: ignore[arg-type]
        tax_year=tax_year,
    )
    return {"event": "meta", "data": data.model_dump()}


def _accepts_on_delta(qa) -> bool:
    return _accepts_param(qa, "on_delta")


def _accepts_param(fn, name: str) -> bool:
    if fn is None:
        return False
    try:
        return name in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _message_id(session: str | None, client_request_id: str | None) -> str:
    """Same client request id in the same session -> same message id, so a resend is a no-op."""
    if session and client_request_id:
        return str(uuid5(NAMESPACE_URL, f"daleelai:{session}:{client_request_id}"))
    return str(uuid4())


async def _saved_turn(store, session, message_id, client_request_id):
    finder = getattr(store, "find_turn", None)
    if not (session and client_request_id and finder):
        return None
    try:
        return await asyncio.to_thread(finder, session, message_id)
    except Exception:
        log.warning("saved turn lookup failed", exc_info=True)
        return None


def _saved_events(saved: dict[str, Any], tax_year: str, corpus_date: str) -> list[dict[str, Any]]:
    message = saved["message"]
    final = FinalData(
        answer=message["content"],
        answer_source=message.get("answer_source") or "none",
        confidence=message.get("confidence") or "low",
        verified=bool(message.get("verified")),
        model=message.get("model") or "saved",
        tax_year=message.get("tax_year") or tax_year,
        corpus_date=message.get("corpus_date") or corpus_date,
        cached=True,
    )
    events = [
        _meta(
            message.get("intent") or "qa",
            message.get("language") or "en",
            final.tax_year,
            saved["chat_id"],
            message["id"],
        )
    ]
    if message.get("sources"):
        events.append({"event": "sources", "data": {"sources": message["sources"]}})
    events.append({"event": "final", "data": final.model_dump()})
    events.append({"event": "done", "data": {}})
    return events


def _uuid_or_none(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(value))
    except (ValueError, TypeError):
        return None


async def _save_turn(
    store,
    *,
    session_id: str | None,
    chat_id: str,
    message_id: str,
    user_text: str,
    intent: str,
    language: str,
    final: dict[str, Any],
    sources: list[dict[str, Any]],
) -> None:
    if store is None or session_id is None:
        return

    def write() -> None:
        store.save_turn(
            session_id=session_id,
            chat_id=chat_id,
            message_id=message_id,
            user_text=user_text,
            assistant_text=final["answer"],
            intent=intent,
            language=language,
            tax_year=final["tax_year"],
            answer_source=final["answer_source"],
            confidence=final["confidence"],
            verified=bool(final["verified"]),
            model=final["model"],
            sources=sources,
        )

    try:
        await asyncio.to_thread(write)
    except Exception:
        log.warning("chat turn was not saved", exc_info=True)


async def _qa_result(
    body,
    qa,
    routed,
    tax_year: str,
    corpus_date: str,
    budget: CallBudget,
    on_delta=None,
    on_sources=None,
    on_status=None,
) -> RagResult:
    if qa is None:
        return RagResult(
            answer=ABSTAIN_SENTENCE,
            answer_source="none",
            verified=False,
            replaced=False,
            model="none",
        )
    kwargs: dict[str, Any] = {}
    if on_delta is not None:
        kwargs["on_delta"] = on_delta
    if on_sources is not None and _accepts_param(qa, "on_sources"):
        kwargs["on_sources"] = on_sources
    if on_status is not None and _accepts_param(qa, "on_status"):
        kwargs["on_status"] = on_status
    return await qa(body, routed, tax_year, corpus_date, budget, **kwargs)


def _final(
    answer,
    answer_source,
    verified,
    model,
    tax_year,
    corpus_date,
    links,
    confidence=None,
    trace=None,
) -> dict[str, Any]:
    level = confidence or stand_in_confidence(answer_source)
    return FinalData(
        answer=answer,
        answer_source=answer_source,
        confidence=level,  # type: ignore[arg-type]
        verified=verified,
        model=model,
        tax_year=tax_year,
        corpus_date=corpus_date,
        action_links=[link.model_dump() for link in links],
        follow_ups=[],
        cached=False,
        trace=trace,
    ).model_dump()


def _trace(intent, search_query, started, *, retrieved=None, rerank_top=None, verified=None):
    return AgentTrace(
        intent=intent,
        search_query=search_query,
        retrieved=retrieved,
        rerank_top=rerank_top,
        verified=verified,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


async def _yield_demo(store, session, chat_id, message_id, question, demo, tax_year, corpus_date):
    intent = str(demo.get("intent") or "qa")
    language = str(demo.get("language") or "en")
    answer = str(demo["answer"])
    yield _meta(intent, language, tax_year, chat_id, message_id)
    yield {"event": "token", "data": {"text": answer}}
    trace = AgentTrace(
        intent=intent,
        search_query=question,
        retrieved=0,
        rerank_top=None,
        verified=False,
        latency_ms=0,
    )
    final = FinalData(
        answer=answer,
        answer_source="none",
        confidence="low",
        verified=False,
        model="demo-cache",
        tax_year=tax_year,
        corpus_date=corpus_date,
        action_links=[],
        follow_ups=[],
        cached=True,
        trace=trace,
    ).model_dump()
    await _save_turn(
        store,
        session_id=session,
        chat_id=chat_id,
        message_id=message_id,
        user_text=question,
        intent=intent,
        language=language,
        final=final,
        sources=[],
    )
    yield {"event": "final", "data": final}
    yield {"event": "done", "data": {}}


def _source(hit: RankedHit, library: str) -> dict[str, Any]:
    payload = hit.payload
    text = str(payload.get("text", ""))
    return Source(
        library=library,  # type: ignore[arg-type]
        doc_id=str(payload.get("doc_id") or hit.chunk_id),
        title=str(payload.get("doc_title") or payload.get("title") or ""),
        section=_statutory_section(payload),
        page=payload.get("page_start"),
        url=str(payload.get("source_url") or payload.get("url") or ""),
        mirror_url=payload.get("mirror_url"),
        site=payload.get("site"),
        fetched_at=payload.get("fetched_at"),
        snippet=text[:300],
        rerank_score=None,
    ).model_dump()


def _explanatory_notice(message: str) -> bool:
    """Long chat questions about a notice stay on QA so a section can be attached."""
    return len(message.split()) >= 12


def _enrich_search_query(message: str, query: str) -> str:
    return rewrite_search_query(message, query)


def _statutory_section(payload: dict[str, Any]) -> str | None:
    raw = str(payload.get("section") or "").strip()
    if _STATUTE.fullmatch(raw):
        return raw
    header = str(payload.get("header") or payload.get("heading") or "")
    found = _HEADER_STATUTE.search(header)
    return found.group(1) if found else None


def _short_reply(
    intent: str,
    authority: str | None,
    language: str = "en",
    message: str = "",
) -> str:
    roman = language == "roman_urdu"
    if intent == "refuse":
        if is_prompt_injection(message):
            return _INJECTION_REFUSAL_RU if roman else _INJECTION_REFUSAL
        return _REFUSAL_RU if roman else _REFUSAL
    if intent == "chitchat":
        return _CHITCHAT_RU if roman else _CHITCHAT
    if intent == "out_of_scope":
        return _OUT_OF_SCOPE_RU if roman else _OUT_OF_SCOPE
    if intent == "provincial":
        name = authority or (
            "subai revenue authority" if roman else "the provincial revenue authority"
        )
        if roman:
            return (
                f"Yeh {name} ka subai mamla lagta hai. "
                "DaleelAI wifaqi tax FBR aur SECP se batata hai. "
                "Qaaida us idare ki site par tasdeeq karein."
            )
        return (
            f"This looks like a provincial matter for {name}. "
            "DaleelAI answers federal tax from FBR and SECP. "
            "Confirm the rule on that authority's site."
        )
    if intent == "notice":
        if roman:
            return "Jab explainer dastiyab ho, notice upload karein. Abhi dastiyab nahi."
        return "Upload the notice when the explainer is available. It is not available yet."
    return _NOT_READY_RU if roman else _NOT_READY
