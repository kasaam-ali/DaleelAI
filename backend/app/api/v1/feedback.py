"""Thumbs and wrong-answer reports. Stored in Postgres."""

import uuid

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.api.v1.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
def feedback(
    body: FeedbackRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> FeedbackResponse | JSONResponse:
    store = request.app.state.container.feedback
    if store is None:
        return _error(503, "repository_unavailable", "Feedback storage is not configured.")
    try:
        uuid.UUID(body.message_id)
        session_id = str(uuid.UUID(x_session_id)) if x_session_id else None
    except (ValueError, TypeError):
        return _error(400, "invalid_request", "message_id and X-Session-Id must be UUIDs.")
    if session_id is None:
        return _error(400, "invalid_request", "X-Session-Id is required.")
    try:
        saved = store.save_feedback(
            session_id=session_id,
            message_id=body.message_id,
            rating=body.rating,
            reason=body.reason,
            comment=body.comment,
            share_conversation=body.share_conversation,
        )
    except Exception:
        return _error(503, "repository_unavailable", "Feedback could not be saved.")
    return FeedbackResponse(id=saved)
