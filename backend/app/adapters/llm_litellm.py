import logging
import os
import time
from collections.abc import Callable

import litellm

from app.core.ports import AllProvidersUnavailable, ChatMessage, LLMResult, Role
from app.settings import ModelsConfig

log = logging.getLogger(__name__)

PROVIDER_KEYS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "zai": "ZAI_API_KEY",
}


class LiteLLMGateway:
    """Tries the models of a role in order; a failing model is skipped for `cooldown_s`."""

    def __init__(self, config: ModelsConfig, clock: Callable[[], float] = time.monotonic):
        self._config = config
        self._clock = clock
        self._cooldown_until: dict[str, float] = {}

    async def complete(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResult:
        candidates = self._config.roles.get(role)
        if not candidates:
            raise ValueError(f"No models configured for role '{role}'")

        errors: list[str] = []
        for index, model in enumerate(candidates):
            if not _has_api_key(model):
                errors.append(f"{model}: no API key")
                continue
            if self._clock() < self._cooldown_until.get(model, 0.0):
                errors.append(f"{model}: cooling down")
                continue

            started = self._clock()
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[message.model_dump() for message in messages],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self._config.retry.timeout_s,
                    num_retries=self._config.retry.attempts,
                )
            except Exception as exc:
                self._cooldown_until[model] = self._clock() + self._config.retry.cooldown_s
                reason = _describe_error(exc)
                log.warning("LLM call failed for %s (%s): %s", model, role, reason)
                errors.append(f"{model}: {reason}")
                continue

            usage = getattr(response, "usage", None)
            return LLMResult(
                text=response.choices[0].message.content or "",
                model=model,
                fallback=index > 0,
                latency_ms=int((self._clock() - started) * 1000),
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )

        raise AllProvidersUnavailable(role, errors)

    async def stream(
        self,
        role: Role,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        info: dict | None = None,
    ):
        """Yield text pieces as the provider sends them. One failed model falls through."""
        candidates = self._config.roles.get(role)
        if not candidates:
            raise ValueError(f"No models configured for role '{role}'")

        errors: list[str] = []
        for index, model in enumerate(candidates):
            if not _has_api_key(model):
                errors.append(f"{model}: no API key")
                continue
            if self._clock() < self._cooldown_until.get(model, 0.0):
                errors.append(f"{model}: cooling down")
                continue

            collected: list[str] = []
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=[message.model_dump() for message in messages],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self._config.retry.timeout_s,
                    num_retries=self._config.retry.attempts,
                    stream=True,
                )
                async for chunk in response:
                    text = _delta_text(chunk)
                    if text:
                        collected.append(text)
            except Exception as exc:
                self._cooldown_until[model] = self._clock() + self._config.retry.cooldown_s
                reason = _describe_error(exc)
                log.warning("LLM stream failed for %s (%s): %s", model, role, reason)
                errors.append(f"{model}: {reason}")
                continue
            if info is not None:
                info["model"] = model
                info["fallback"] = index > 0
            self.last_model = model
            for text in collected:
                yield text
            return

        raise AllProvidersUnavailable(role, errors)


def _delta_text(chunk) -> str:
    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return ""
    delta = getattr(choices[0], "delta", None)
    content = getattr(delta, "content", None) if delta is not None else None
    return content if isinstance(content, str) else ""


def _describe_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    return f"{type(exc).__name__} (HTTP {status})" if status else type(exc).__name__


def _has_api_key(model: str) -> bool:
    env_var = PROVIDER_KEYS.get(model.split("/", 1)[0])
    return env_var is None or bool(os.environ.get(env_var))
