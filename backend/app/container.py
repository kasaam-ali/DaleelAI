from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.adapters.fakes import FakeLLM
from app.adapters.llm_litellm import LiteLLMGateway
from app.core.cache import MemoryCache
from app.core.ports import LLMPort
from app.settings import Settings, load_models_config, load_settings
from app.version import CORPUS_DATE, INDEXED_CORPUS_VERSION

QaRunner = Callable[..., Awaitable[Any]]


@dataclass
class Container:
    settings: Settings
    llm: LLMPort
    qa: QaRunner | None = None
    answer_cache: MemoryCache | None = None
    feedback: Any = None
    corpus_version: str = "unindexed"
    corpus_date: str = "unindexed"
    today: Callable[[], date] = date.today


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or load_settings()
    if settings.adapters.llm == "fake":
        llm: LLMPort = FakeLLM()
    else:
        llm = LiteLLMGateway(load_models_config())
    qa = None
    if settings.adapters.vector_store == "qdrant":
        from app.adapters.live_qa import LiveQa

        qa = LiveQa(settings, llm)
    feedback = None
    if settings.database_url:
        from app.adapters.postgres_store import PostgresStore

        feedback = PostgresStore(settings.database_url)
    return Container(
        settings=settings,
        llm=llm,
        qa=qa,
        answer_cache=MemoryCache(),
        feedback=feedback,
        corpus_version=INDEXED_CORPUS_VERSION,
        corpus_date=CORPUS_DATE,
    )
