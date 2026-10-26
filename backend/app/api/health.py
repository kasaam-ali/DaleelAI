"""GET /health reports the version, corpus, tax years, and which models are configured."""

import time
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.health_checks import collect_checks
from app.version import APP_VERSION

router = APIRouter()
CACHE_TTL_S = 10
_cached: dict[str, tuple[float, dict]] = {}


class DependencyCheck(BaseModel):
    status: Literal["ok", "slow", "down", "off"]
    latency_ms: int


class DependencyChecks(BaseModel):
    api: DependencyCheck
    qdrant: DependencyCheck
    postgres: DependencyCheck
    llm: DependencyCheck
    embeddings: DependencyCheck


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    env: str
    corpus_version: str
    corpus_date: str = ""
    supported_tax_years: list[str]
    models: dict[str, str]
    checks: DependencyChecks


def _cache_key(settings) -> str:
    return "|".join(
        (
            settings.adapters.llm,
            settings.adapters.vector_store,
            settings.adapters.embedder,
            settings.database_url,
            settings.qdrant.url,
            settings.models.dense,
            settings.models.sparse,
        )
    )


def overall_status(checks: dict) -> Literal["ok", "degraded"]:
    """Postgres stores the chats. If it is configured and down, the service is degraded.

    "off" (no DATABASE_URL) runs on the in-memory store and is not degraded.
    """
    postgres = checks.get("postgres") or {}
    if postgres.get("status") == "down":
        return "degraded"
    return "ok"


async def checks_for(container) -> dict:
    settings = container.settings
    key = _cache_key(settings)
    now = time.monotonic()
    hit = _cached.get(key)
    if hit is not None and now - hit[0] < CACHE_TTL_S:
        return hit[1]
    payload = await collect_checks(settings)
    _cached[key] = (now, payload)
    return payload


@router.get("/health")
async def health(request: Request) -> HealthResponse:
    container = request.app.state.container
    settings = container.settings
    checks = await checks_for(container)
    return HealthResponse(
        status=overall_status(checks),
        version=APP_VERSION,
        env=settings.env,
        corpus_version=container.corpus_version,
        corpus_date=container.corpus_date,
        supported_tax_years=["TY2026", "TY2027"],
        models={
            "dense": settings.models.dense,
            "sparse": settings.models.sparse,
            "reranker": settings.models.reranker,
            "llm": settings.adapters.llm,
        },
        checks=DependencyChecks.model_validate(checks),
    )
