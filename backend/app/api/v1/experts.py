"""Find a public listing, and let the directory scraper upsert one."""

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.api.v1.schemas import ExpertFindRequest, ExpertFindResponse, ExpertUpsert
from app.core.classifier import KeywordClassifier
from app.core.services.experts import ExpertError, find_experts, load_directory

router = APIRouter()
internal_router = APIRouter()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _listings(request: Request) -> list[dict] | None:
    store = request.app.state.container.feedback
    if store is None or not hasattr(store, "list_experts"):
        return None
    try:
        rows = store.list_experts()
        if rows:
            return rows
        for row in load_directory()["experts"]:
            store.upsert_expert(row)
        return store.list_experts()
    except Exception:
        return None


@router.post("/experts/find", response_model=ExpertFindResponse)
def experts_find(body: ExpertFindRequest, request: Request) -> ExpertFindResponse | JSONResponse:
    classifier = getattr(request.app.state.container, "classifier", None) or KeywordClassifier()
    try:
        found = find_experts(
            body.query,
            city=body.city,
            category=body.category,
            classifier=classifier,
            listings=_listings(request),
        )
    except ExpertError as exc:
        return _error(400, exc.code, exc.message)
    return ExpertFindResponse.model_validate(found)


@internal_router.post("/experts/upsert", response_model=None)
def experts_upsert(
    body: ExpertUpsert,
    request: Request,
    x_internal_token: str | None = Header(default=None),
) -> JSONResponse:
    expected = request.app.state.container.settings.internal_token
    if not expected or x_internal_token != expected:
        return _error(401, "unauthorized", "The internal token does not match.")
    store = request.app.state.container.feedback
    if store is None or not hasattr(store, "upsert_expert"):
        return _error(503, "repository_unavailable", "Expert storage is not configured.")
    try:
        store.upsert_expert(body.model_dump())
    except Exception:
        return _error(400, "invalid_request", "The listing could not be saved.")
    return JSONResponse({"saved": True})
