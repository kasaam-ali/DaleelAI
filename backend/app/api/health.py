from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.version import APP_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    env: str
    corpus_version: str
    supported_tax_years: list[str]
    models: dict[str, str]


@router.get("/health")
def health(request: Request) -> HealthResponse:
    settings = request.app.state.container.settings
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        env=settings.env,
        corpus_version="unindexed",
        supported_tax_years=["TY2026", "TY2027"],
        models={
            "dense": settings.models.dense,
            "sparse": settings.models.sparse,
            "reranker": settings.models.reranker,
            "llm": settings.adapters.llm,
        },
    )
