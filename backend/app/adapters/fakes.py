"""In-memory LLM for tests. It records each call and makes no network request."""

from collections.abc import Sequence
from typing import Any

from app.core.ports import ChatMessage, LLMResult, Role


class FakeLLM:
    def __init__(self, reply: str = "fake answer"):
        self.reply = reply
        self.calls: list[tuple[Role, list[ChatMessage]]] = []

    async def complete(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResult:
        self.calls.append((role, messages))
        return LLMResult(text=self.reply, model="fake/fake", fallback=False, latency_ms=0)


class FakeVectorStore:
    async def search(self, collection: str, query: str, *, k: int = 30) -> list[Any]:
        return []


class FakeEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


class FakeReranker:
    def rerank(self, query: str, documents: Sequence[str], *, keep: int = 6) -> list[Any]:
        return list(documents[:keep])


class FakeClassifier:
    def predict(self, text: str) -> Any:
        return {"category": "income_tax", "complexity": "simple", "confidence": 0.0}


class FakeRepository:
    async def ping(self) -> bool:
        return True


class FakeDocumentParser:
    def parse(self, data: bytes, filename: str) -> str:
        return ""


class FakeAgentRunner:
    async def run(self, payload: dict[str, Any]) -> Any:
        return {"status": "stub", "payload": payload}
