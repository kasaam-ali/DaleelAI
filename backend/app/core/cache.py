"""Request caches. Keys match SPECS section 4. Storage here is in memory, not Postgres."""

import hashlib
import json
from typing import Any

from app.core.ports import ChatMessage, LLMPort, LLMResult, Role


def answer_cache_key(
    question: str,
    profile: dict[str, Any] | None,
    tax_year: str,
    corpus_version: str,
) -> str:
    raw = json.dumps(
        {
            "question": " ".join(question.strip().lower().split()),
            "profile": profile or {},
            "tax_year": tax_year,
            "corpus_version": corpus_version,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def llm_cache_key(
    role: str,
    messages: list[ChatMessage],
    *,
    temperature: float,
    max_tokens: int | None,
) -> str:
    """SPECS names the model in the key. The gateway picks the model inside the call,
    so the key is the request: role, messages, and params."""
    raw = json.dumps(
        {
            "role": role,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class MemoryCache:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self.data.get(key)

    def put(self, key: str, payload: dict[str, Any]) -> None:
        self.data[key] = payload


class CachingLLM:
    """Wraps an LLM port. A hit returns the stored result and does not call the inner port."""

    def __init__(self, inner: LLMPort, cache: MemoryCache) -> None:
        self.inner = inner
        self.cache = cache
        self.hits = 0

    async def complete(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResult:
        key = llm_cache_key(role, messages, temperature=temperature, max_tokens=max_tokens)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return LLMResult.model_validate(cached)
        result = await self.inner.complete(
            role,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.cache.put(key, result.model_dump())
        return result
