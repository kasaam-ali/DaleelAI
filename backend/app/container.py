from dataclasses import dataclass

from app.adapters.fakes import FakeLLM
from app.adapters.llm_litellm import LiteLLMGateway
from app.core.ports import LLMPort
from app.settings import Settings, load_models_config, load_settings


@dataclass
class Container:
    settings: Settings
    llm: LLMPort


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or load_settings()
    if settings.adapters.llm == "fake":
        llm: LLMPort = FakeLLM()
    else:
        llm = LiteLLMGateway(load_models_config())
    return Container(settings=settings, llm=llm)
