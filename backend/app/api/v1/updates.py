"""Updates feed, notification ingest, and web crawl ingest."""

from pathlib import Path

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from app.api.v1.schemas import (
    NotificationIngestRequest,
    NotificationIngestResponse,
    UpdateListResponse,
    WebIngestRequest,
    WebIngestResponse,
)
from app.core.services.updates import (
    _public,
    apply_web_crawl,
    ingest_notifications,
    list_updates,
    memory_updates,
    replay_notifications,
)
from app.core.updates.changes import OffList, ZeroPages, prefixes_for
from app.core.updates.listing import ZeroItems

router = APIRouter()
internal_router = APIRouter()
_ALLOWLIST = Path(__file__).resolve().parents[3] / "config" / "web_sources.yaml"


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _store(request: Request):
    store = request.app.state.container.feedback
    if store is not None and hasattr(store, "list_notifications"):
        return store
    return memory_updates()


def _indexer(request: Request):
    settings = request.app.state.container.settings
    if settings.adapters.vector_store != "qdrant":
        return None
    from app.core.updates.indexer import WebIndexer, index_notification

    return index_notification, WebIndexer()


def _authorized(request: Request, token: str | None, authorization: str | None) -> bool:
    expected = request.app.state.container.settings.internal_token
    if not expected:
        return False
    if token == expected:
        return True
    bearer = (authorization or "").removeprefix("Bearer ").strip()
    return bool(bearer) and bearer == expected


@router.get("/updates", response_model=UpdateListResponse)
def updates_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    doc_type: str = Query(default="all"),
    domain: str = Query(default="all"),
) -> UpdateListResponse | JSONResponse:
    if doc_type not in {"all", "sro", "circular", "notification"}:
        return _error(
            400,
            "invalid_request",
            "doc_type must be all, sro, circular, or notification.",
        )
    found = list_updates(_store(request), doc_type=doc_type, domain=domain, page=page, limit=limit)
    return UpdateListResponse.model_validate(found)


@router.post("/updates/replay", response_model=NotificationIngestResponse)
def updates_replay(request: Request) -> NotificationIngestResponse | JSONResponse:
    indexer, _web = _pair(request)
    try:
        result = replay_notifications(
            _store(request),
            classifier=getattr(request.app.state.container, "classifier", None),
            indexer=indexer,
        )
    except ZeroItems as exc:
        return _error(400, "zero_items", str(exc))
    return NotificationIngestResponse.model_validate(result)


@router.get("/updates/{item_id}", response_model=None)
def updates_one(item_id: str, request: Request) -> JSONResponse:
    row = _store(request).get_notification(item_id)
    if row is None:
        return _error(404, "not_found", "That update was not found.")
    return JSONResponse(_public(row))


@internal_router.post("/notifications/ingest", response_model=NotificationIngestResponse)
def notifications_ingest(
    body: NotificationIngestRequest,
    request: Request,
    x_internal_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> NotificationIngestResponse | JSONResponse:
    if not _authorized(request, x_internal_token, authorization):
        return _error(401, "unauthorized", "The internal token does not match.")
    indexer, _web = _pair(request)
    items = [item.model_dump() for item in body.items]
    for item in items:
        item["title"] = item.pop("listing_title")
    try:
        result = ingest_notifications(
            items,
            _store(request),
            classifier=getattr(request.app.state.container, "classifier", None),
            indexer=indexer,
        )
    except ZeroItems as exc:
        return _error(400, "zero_items", str(exc))
    return NotificationIngestResponse.model_validate(result)


@internal_router.post("/notifications/replay", response_model=NotificationIngestResponse)
def notifications_replay(
    request: Request,
    x_internal_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> NotificationIngestResponse | JSONResponse:
    if not _authorized(request, x_internal_token, authorization):
        return _error(401, "unauthorized", "The internal token does not match.")
    return updates_replay(request)


@internal_router.post("/web/ingest", response_model=WebIngestResponse)
def web_ingest(
    body: WebIngestRequest,
    request: Request,
    x_internal_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> WebIngestResponse | JSONResponse:
    if not _authorized(request, x_internal_token, authorization):
        return _error(401, "unauthorized", "The internal token does not match.")
    _notice, web = _pair(request)
    pages = [page.model_dump() for page in body.pages]
    try:
        result = apply_web_crawl(
            body.site,
            pages,
            _store(request),
            prefixes_for(_ALLOWLIST),
            indexer=web,
        )
    except ZeroPages as exc:
        return _error(400, "zero_pages", str(exc))
    except OffList as exc:
        return _error(400, "off_list", str(exc))
    return WebIngestResponse.model_validate(result)


def _pair(request: Request):
    built = _indexer(request)
    if built is None:
        return None, None
    return built
