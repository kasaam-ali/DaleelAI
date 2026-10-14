from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.api.v1.schemas import ChatRequest
from app.core.services.chat import format_sse, iter_chat_events

router = APIRouter()


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> StreamingResponse:
    container = request.app.state.container

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
        ):
            yield format_sse(event)

    return StreamingResponse(body_stream(), media_type="text/event-stream")
