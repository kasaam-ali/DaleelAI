from typing import Literal, Protocol

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
