from types import SimpleNamespace

import litellm
import pytest

from app.adapters import llm_litellm
from app.adapters.llm_litellm import LiteLLMGateway
from app.core.ports import AllProvidersUnavailable, ChatMessage
from app.settings import ModelsConfig, RetryConfig

MESSAGES = [ChatMessage(role="user", content="Salam")]


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_gateway(clock=None) -> LiteLLMGateway:
    config = ModelsConfig(
        roles={"reasoning": ["groq/big", "gemini/flash"]},
        retry=RetryConfig(attempts=0, cooldown_s=60, timeout_s=5),
    )
    return LiteLLMGateway(config, clock=clock or FakeClock())


def ok_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
    )


@pytest.fixture(autouse=True)
def api_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")


@pytest.fixture
def calls(monkeypatch):
    """Records called models; a provider raises its `*_error` when one is set."""
    record = SimpleNamespace(models=[], groq_error=None, gemini_error=None)

    async def fake_acompletion(model, **kwargs):
        record.models.append(model)
        if model.startswith("groq/") and record.groq_error:
            raise record.groq_error
        if model.startswith("gemini/") and record.gemini_error:
            raise record.gemini_error
        return ok_response(f"answer from {model}")

    monkeypatch.setattr(llm_litellm.litellm, "acompletion", fake_acompletion)
    return record


async def test_first_model_answers_without_fallback(calls):
    result = await make_gateway().complete("reasoning", MESSAGES)

    assert result.model == "groq/big"
    assert result.fallback is False
    assert result.prompt_tokens == 3
    assert calls.models == ["groq/big"]


async def test_rate_limit_falls_back_to_next_provider(calls):
    calls.groq_error = litellm.RateLimitError(message="429", llm_provider="groq", model="big")

    result = await make_gateway().complete("reasoning", MESSAGES)

    assert result.model == "gemini/flash"
    assert result.fallback is True
    assert calls.models == ["groq/big", "gemini/flash"]


async def test_timeout_falls_back_to_next_provider(calls):
    calls.groq_error = litellm.Timeout(message="timeout", model="big", llm_provider="groq")

    result = await make_gateway().complete("reasoning", MESSAGES)

    assert result.model == "gemini/flash"


async def test_missing_groq_key_skips_groq(calls, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")

    result = await make_gateway().complete("reasoning", MESSAGES)

    assert result.model == "gemini/flash"
    assert result.fallback is True
    assert calls.models == ["gemini/flash"]


async def test_failed_model_cools_down_then_returns(calls):
    clock = FakeClock()
    gateway = make_gateway(clock)
    calls.groq_error = litellm.RateLimitError(message="429", llm_provider="groq", model="big")
    await gateway.complete("reasoning", MESSAGES)

    calls.groq_error = None
    calls.models.clear()
    clock.now += 30
    during = await gateway.complete("reasoning", MESSAGES)
    clock.now += 31
    after = await gateway.complete("reasoning", MESSAGES)

    assert during.model == "gemini/flash"
    assert after.model == "groq/big"
    assert calls.models == ["gemini/flash", "groq/big"]


async def test_all_providers_failing_raises(calls):
    calls.groq_error = litellm.RateLimitError(message="429", llm_provider="groq", model="big")
    calls.gemini_error = litellm.Timeout(message="timeout", model="flash", llm_provider="gemini")

    with pytest.raises(AllProvidersUnavailable) as error:
        await make_gateway().complete("reasoning", MESSAGES)

    assert error.value.role == "reasoning"
    assert len(error.value.errors) == 2


async def test_unknown_role_raises(calls):
    with pytest.raises(ValueError):
        await make_gateway().complete("vision", MESSAGES)
