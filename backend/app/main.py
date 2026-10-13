from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.container import Container, build_container
from app.version import APP_VERSION

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def create_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()
    app = FastAPI(title="DaleelAI API", version=APP_VERSION)
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
