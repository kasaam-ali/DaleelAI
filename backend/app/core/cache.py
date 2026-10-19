"""Request caches. Keys match SPECS section 4. Storage here is in memory, not Postgres."""

import hashlib
import json
import time
from typing import Any

from app.core.ports import ChatMessage, LLMPort, LLMResult, Role


def answer_cache_key(
    question: str,
    profile: dict[str, Any] | None,
    tax_year: str,
    corpus_version: str,
    language: str = "",
) -> str:
    """Normalized redacted question, language, and tax year. Profile stays out of the answer."""
    raw = json.dumps(
        {
            "question": " ".join(question.strip().lower().split()),
            "language": language or "",
            "tax_year": tax_year,
            "corpus_version": corpus_version,
            "profile": profile or {},
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
    """In-memory cache. Answer entries expire after 24 hours."""

    def __init__(self, ttl_s: float = 24 * 60 * 60) -> None:
        self.data: dict[str, dict[str, Any]] = {}
        self.expires: dict[str, float] = {}
        self.ttl_s = ttl_s

    def get(self, key: str) -> dict[str, Any] | None:
        exp = self.expires.get(key)
        if exp is not None and time.monotonic() >= exp:
            self.data.pop(key, None)
            self.expires.pop(key, None)
            return None
        return self.data.get(key)

    def put(self, key: str, payload: dict[str, Any]) -> None:
        self.data[key] = payload
        self.expires[key] = time.monotonic() + self.ttl_s


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
