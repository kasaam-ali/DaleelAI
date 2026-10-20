"""DELETE /api/v1/session removes one session's stored history."""

from fastapi import APIRouter, Header, Request, Response

from app.api.v1.chat import _error, _session, _store

router = APIRouter()


@router.delete("/session", status_code=204)
def delete_session(
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> Response:
    session = _session(x_session_id)
    if isinstance(session, Response):
        return session
    store = _store(request)
    if store is None or not hasattr(store, "delete_session"):
        return _error(503, "repository_unavailable", "Session storage is not configured.")
    store.delete_session(session)
    return Response(status_code=204)
