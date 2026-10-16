import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.experts import internal_router
from app.api.v1.router import router as v1_router
from app.api.v1.updates import internal_router as updates_internal_router
from app.container import Container, build_container
from app.version import APP_VERSION

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def create_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        qa = container.qa
        adapters = container.settings.adapters
        if (
            qa is not None
            and hasattr(qa, "warm")
            and adapters.llm != "fake"
            and adapters.embedder == "fastembed"
            and adapters.reranker == "fastembed"
        ):
            await asyncio.to_thread(qa.warm)
        yield

    app = FastAPI(title="DaleelAI API", version=APP_VERSION, lifespan=lifespan)
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/internal")
    app.include_router(updates_internal_router, prefix="/internal")
    return app


app = create_app()
