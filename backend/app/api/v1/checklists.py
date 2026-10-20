"""Checklist templates and per-session progress."""

import uuid

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.api.v1.schemas import (
    ChecklistRequest,
    ChecklistResponse,
    ChecklistStepPatch,
    ChecklistTemplate,
)
from app.core.services.checklists import (
    ChecklistError,
    get_for_session,
    list_for_session,
    list_templates,
    mark_step,
    memory_checklists,
    start_checklist,
)

router = APIRouter()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _repo(request: Request):
    store = request.app.state.container.feedback
    if store is not None and hasattr(store, "save_checklist"):
        return store
    return memory_checklists


def _session(x_session_id: str | None) -> str | JSONResponse:
    if not x_session_id:
        return _error(400, "invalid_request", "X-Session-Id is required.")
    try:
        return str(uuid.UUID(x_session_id))
    except (ValueError, TypeError):
        return _error(400, "invalid_request", "X-Session-Id must be a UUID.")


@router.get("/checklists/templates", response_model=list[ChecklistTemplate])
def templates() -> list[ChecklistTemplate]:
    return [ChecklistTemplate.model_validate(row) for row in list_templates()]


@router.post("/checklists", response_model=ChecklistResponse, status_code=201)
def create_checklist(
    body: ChecklistRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> ChecklistResponse | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    try:
        saved = start_checklist(
            body.template_id,
            body.answers,
            body.language,
            _repo(request),
            session,
        )
    except ChecklistError as exc:
        status = 404 if exc.code == "not_found" else 400
        return _error(status, exc.code, exc.message)
    return ChecklistResponse.model_validate(saved)


@router.get("/checklists", response_model=list[ChecklistResponse])
def list_checklists(
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> list[ChecklistResponse] | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    try:
        rows = list_for_session(_repo(request), session)
    except ChecklistError as exc:
        return _checklist_error(exc)
    return [ChecklistResponse.model_validate(row) for row in rows]


@router.get("/checklists/{checklist_id}", response_model=ChecklistResponse)
def get_checklist(
    checklist_id: str,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> ChecklistResponse | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    denied = _checklist_id(checklist_id)
    if denied is not None:
        return denied
    try:
        saved = get_for_session(checklist_id, _repo(request), session)
    except ChecklistError as exc:
        return _checklist_error(exc)
    return ChecklistResponse.model_validate(saved)


@router.patch(
    "/checklists/{checklist_id}/steps/{step_id}",
    response_model=ChecklistResponse,
)
def patch_step(
    checklist_id: str,
    step_id: str,
    body: ChecklistStepPatch,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> ChecklistResponse | JSONResponse:
    session = _session(x_session_id)
    if isinstance(session, JSONResponse):
        return session
    denied = _checklist_id(checklist_id)
    if denied is not None:
        return denied
    try:
        saved = mark_step(
            checklist_id,
            step_id,
            body.done,
            body.language,
            _repo(request),
            session,
        )
    except ChecklistError as exc:
        return _checklist_error(exc)
    return ChecklistResponse.model_validate(saved)


def _checklist_id(checklist_id: str) -> JSONResponse | None:
    try:
        uuid.UUID(checklist_id)
    except (ValueError, TypeError):
        return _error(422, "invalid_request", "checklist id must be a UUID.")
    return None


def _checklist_error(exc: ChecklistError) -> JSONResponse:
    status = 400
    if exc.code == "not_found":
        status = 404
    elif exc.code == "repository_unavailable":
        status = 503
    return _error(status, exc.code, exc.message)
