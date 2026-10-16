import asyncio
import logging
import os
import queue
import threading
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

        deadline = time.monotonic() + self._config.retry.timeout_s
        errors: list[str] = []
        for index, entry in enumerate(candidates):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            resolved = _resolve(entry)
            if resolved is None:
                errors.append(f"{entry}: no API key")
                continue
            model, api_key = resolved
            if self._clock() < self._cooldown_until.get(entry, 0.0):
                errors.append(f"{entry}: cooling down")
                continue

            started = self._clock()
            try:
                response = await _bounded(
                    asyncio.to_thread(
                        _completion_in_thread,
                        _call_kwargs(
                            self._config,
                            model,
                            messages,
                            temperature,
                            max_tokens,
                            api_key,
                            timeout_s=remaining,
                        ),
                    ),
                    remaining,
                )
            except Exception as exc:
                self._cooldown_until[entry] = self._clock() + self._config.retry.cooldown_s
                reason = _describe_error(exc)
                log.warning("LLM call failed for %s (%s): %s", entry, role, reason)
                errors.append(f"{entry}: {reason}")
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
        """Yield each text piece as the provider sends it.

        Attempts share one wall-clock budget (`timeout_s`). A model that fails
        before its first piece is skipped. A piece already yielded is kept, so
        the next model is not concatenated onto a partial answer.
        """
        candidates = self._config.roles.get(role)
        if not candidates:
            raise ValueError(f"No models configured for role '{role}'")

        deadline = time.monotonic() + self._config.retry.timeout_s
        errors: list[str] = []
        for index, entry in enumerate(candidates):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            resolved = _resolve(entry)
            if resolved is None:
                errors.append(f"{entry}: no API key")
                continue
            model, api_key = resolved
            if self._clock() < self._cooldown_until.get(entry, 0.0):
                errors.append(f"{entry}: cooling down")
                continue

            emitted = False
            chunks: queue.Queue = queue.Queue()
            threading.Thread(
                target=_pump_deltas,
                args=(
                    _call_kwargs(
                        self._config,
                        model,
                        messages,
                        temperature,
                        max_tokens,
                        api_key,
                        stream=True,
                        timeout_s=remaining,
                    ),
                    chunks,
                ),
                daemon=True,
            ).start()
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    item = await _next_pumped(chunks, remaining)
                    if item is _POLL:
                        continue
                    if item is _END:
                        return
                    if isinstance(item, Exception):
                        raise item
                    text = item
                    if info is not None:
                        info["model"] = model
                        info["fallback"] = index > 0
                    self.last_model = model
                    emitted = True
                    yield text
            except TimeoutError:
                if emitted:
                    raise
                self._cooldown_until[entry] = self._clock() + self._config.retry.cooldown_s
                log.warning("LLM stream timed out for %s (%s)", entry, role)
                errors.append(f"{entry}: timeout")
                continue
            except Exception as exc:
                if emitted:
                    raise
                self._cooldown_until[entry] = self._clock() + self._config.retry.cooldown_s
                reason = _describe_error(exc)
                log.warning("LLM stream failed for %s (%s): %s", entry, role, reason)
                errors.append(f"{entry}: {reason}")
                continue

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


def _resolve(entry: str) -> tuple[str, str | None] | None:
    """Return `(model, api_key)`. None means the named key is missing.

    `model|ENV_VAR` forces that variable. Cooldown stays on the whole entry,
    so the same Gemini model can be tried again with `GEMINI_API_KEY_2`.
    """
    model, sep, env_name = entry.partition("|")
    if not sep:
        env_name = PROVIDER_KEYS.get(model.split("/", 1)[0]) or ""
    if not env_name:
        return model, None
    api_key = os.environ.get(env_name)
    if not api_key:
        return None
    return model, api_key


def _call_kwargs(
    config,
    model,
    messages,
    temperature,
    max_tokens,
    api_key,
    stream=False,
    timeout_s: float | None = None,
) -> dict:
    timeout = config.retry.timeout_s if timeout_s is None else timeout_s
    kwargs = {
        "model": model,
        "messages": [message.model_dump() for message in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "num_retries": config.retry.attempts,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if "gpt-oss" in model:
        kwargs["reasoning_effort"] = "low"
    if stream:
        kwargs["stream"] = True
        kwargs["stream_timeout"] = timeout
    return kwargs


_END = object()
_POLL = object()


def _pump_deltas(kwargs: dict, out: queue.Queue) -> None:
    """Read the provider on a worker thread so a blocked socket cannot freeze the request loop."""

    async def run() -> None:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            text = _delta_text(chunk)
            if text:
                out.put(text)
        out.put(_END)

    try:
        asyncio.run(run())
    except Exception as exc:
        out.put(exc)


async def _next_pumped(out: queue.Queue, timeout_s: float):
    """Return the next piece. The wait itself returns when the budget is spent."""
    if timeout_s <= 0:
        raise TimeoutError

    def take():
        try:
            return out.get(timeout=min(timeout_s, 1.0))
        except queue.Empty:
            return _POLL

    item = await asyncio.to_thread(take)
    return item


def _completion_in_thread(kwargs: dict):
    """Run the provider off the request loop so a hung call cannot freeze the timeout."""
    return asyncio.run(litellm.acompletion(**kwargs))


async def _bounded(awaitable, timeout_s: float):
    """Wait until `timeout_s`. A provider that ignores cancellation does not extend the wait."""
    task = asyncio.create_task(awaitable)
    task.add_done_callback(_retrieve_exception)
    done, _pending = await asyncio.wait({task}, timeout=timeout_s)
    if not done:
        task.cancel()
        raise TimeoutError
    return task.result()


def _retrieve_exception(task: asyncio.Task) -> None:
    if not task.cancelled():
        task.exception()
