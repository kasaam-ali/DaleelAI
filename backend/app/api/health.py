from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.version import APP_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    env: str


@router.get("/health")
def health(request: Request) -> HealthResponse:
    settings = request.app.state.container.settings
    return HealthResponse(status="ok", version=APP_VERSION, env=settings.env)
