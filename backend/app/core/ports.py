from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel

Role = Literal["reasoning", "fast", "vision", "judge"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResult(BaseModel):
    text: str
    model: str
    fallback: bool
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class AllProvidersUnavailable(Exception):
    def __init__(self, role: str, errors: list[str]):
        super().__init__(f"No model available for role '{role}': {'; '.join(errors)}")
        self.role = role
        self.errors = errors


class LLMPort(Protocol):
    async def complete(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResult: ...


class VectorStorePort(Protocol):
    async def search(self, collection: str, query: str, *, k: int = 30) -> list[Any]: ...


class EmbedderPort(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class RerankerPort(Protocol):
    def rerank(self, query: str, documents: Sequence[str], *, keep: int = 6) -> list[Any]: ...


class ClassifierPort(Protocol):
    def predict(self, text: str) -> Any: ...


class RepositoryPort(Protocol):
    async def ping(self) -> bool: ...


class DocumentParserPort(Protocol):
    def parse(self, data: bytes, filename: str) -> str: ...


class AgentRunnerPort(Protocol):
    async def run(self, payload: dict[str, Any]) -> Any: ...
