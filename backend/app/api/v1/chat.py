"""Chat stream plus session-scoped history. A wrong session is a 404."""

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.v1.schemas import ChatDetail, ChatListResponse, ChatRequest
from app.core.services.chat import format_sse, iter_chat_events

router = APIRouter()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _session(value: str | None) -> str | JSONResponse:
    if not value:
        return _error(400, "invalid_request", "X-Session-Id is required.")
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError):
        return _error(400, "invalid_request", "X-Session-Id must be a UUID.")


def _store(request: Request):
    store = request.app.state.container.feedback
    if store is None or not hasattr(store, "list_chats"):
        return None
    return store


def _guard_continue(body: ChatRequest, session_header: str | None, store) -> JSONResponse | None:
    if not body.chat_id:
        return None
    try:
        uuid.UUID(body.chat_id)
    except (ValueError, TypeError):
        return _error(400, "invalid_request", "chat_id must be a UUID.")
    session = _session(session_header)
    if isinstance(session, JSONResponse):
        return session
    if store is None or not hasattr(store, "chat_owner"):
        return None
    owner = store.chat_owner(body.chat_id)
    if owner is not None and owner != session:
        return _error(404, "not_found", "That chat was not found.")
    return None


@router.get("/chats", response_model=ChatListResponse)
def list_chats(
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> ChatListResponse | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    store = _store(request)
    if store is None:
        return _error(503, "repository_unavailable", "Chat storage is not configured.")
    return ChatListResponse(chats=store.list_chats(session))


@router.get("/chats/{chat_id}", response_model=ChatDetail)
def get_chat(
    chat_id: str,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> ChatDetail | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    try:
        uuid.UUID(chat_id)
    except (ValueError, TypeError):
        return _error(400, "invalid_request", "chat_id must be a UUID.")
    store = _store(request)
    if store is None:
        return _error(503, "repository_unavailable", "Chat storage is not configured.")
    found = store.get_chat(session, chat_id)
    if found is None:
        return _error(404, "not_found", "That chat was not found.")
    return ChatDetail.model_validate(found)


@router.post("/chat", response_model=None)
async def chat(
    body: ChatRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> StreamingResponse | JSONResponse:
    container = request.app.state.container
    denied = _guard_continue(body, x_session_id, container.feedback)
    if denied is not None:
        return denied

    async def body_stream() -> AsyncIterator[str]:
        async for event in iter_chat_events(
            body,
            container.llm,
            today=container.today(),
            corpus_version=container.corpus_version,
            corpus_date=container.corpus_date,
            qa=container.qa,
            cache=container.answer_cache,
            calls_cap=container.settings.budget.calls_cap,
            session_id=x_session_id,
            store=container.feedback,
            classifier=getattr(container, "classifier", None),
        ):
            yield format_sse(event)

    return StreamingResponse(body_stream(), media_type="text/event-stream")
