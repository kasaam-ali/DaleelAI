from types import SimpleNamespace

import litellm
import pytest

from app.adapters import llm_litellm
from app.adapters.llm_litellm import LiteLLMGateway
from app.core.ports import AllProvidersUnavailable, ChatMessage
from app.settings import ModelsConfig, RetryConfig, load_models_config

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


async def test_stream_yields_provider_deltas(monkeypatch):
    async def fake_acompletion(model, **kwargs):
        assert kwargs["stream"] is True

        async def chunks():
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"))])
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))])

        return chunks()

    monkeypatch.setattr(llm_litellm.litellm, "acompletion", fake_acompletion)
    info: dict = {}
    parts = [piece async for piece in make_gateway().stream("reasoning", MESSAGES, info=info)]

    assert parts == ["Hel", "lo"]
    assert info["model"] == "groq/big"


async def test_stream_drops_a_partial_model_and_uses_the_next(monkeypatch):
    async def fake_acompletion(model, **kwargs):
        async def chunks():
            if model.startswith("groq/"):
                piece = SimpleNamespace(delta=SimpleNamespace(content="Hel"))
                yield SimpleNamespace(choices=[piece])
                raise RuntimeError("dropped")
            piece = SimpleNamespace(delta=SimpleNamespace(content="lo"))
            yield SimpleNamespace(choices=[piece])

        return chunks()

    monkeypatch.setattr(llm_litellm.litellm, "acompletion", fake_acompletion)
    info: dict = {}
    parts = [piece async for piece in make_gateway().stream("reasoning", MESSAGES, info=info)]

    assert parts == ["lo"]
    assert info["model"] == "gemini/flash"
    assert info["fallback"] is True


def _key_name(entry: str) -> str:
    model, sep, env_name = entry.partition("|")
    if sep:
        return env_name
    provider = model.split("/", 1)[0]
    return {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }[provider]


def test_every_role_uses_the_four_keys_in_order():
    config = load_models_config()
    expected = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_2",
        "OPENROUTER_API_KEY",
    ]
    for role in ("reasoning", "fast", "judge", "vision"):
        names = []
        for entry in config.roles[role]:
            name = _key_name(entry)
            if not names or names[-1] != name:
                names.append(name)
        assert names == expected
        assert "gemini/gemini-3.8-flash|GEMINI_API_KEY_2" in config.roles[role]
        assert "gemini/gemini-2.5-flash|GEMINI_API_KEY_2" in config.roles[role]


async def test_keys_one_two_and_three_fall_through_to_openrouter(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "gemini-key-2")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    seen: list[tuple[str, str | None]] = []

    async def fake_acompletion(model, **kwargs):
        seen.append((model, kwargs.get("api_key")))
        if model.startswith("openrouter/"):
            return ok_response("from openrouter")
        raise litellm.RateLimitError(message="429", llm_provider="test", model=model)

    monkeypatch.setattr(llm_litellm.litellm, "acompletion", fake_acompletion)
    config = ModelsConfig(
        roles={
            "reasoning": [
                "groq/big",
                "gemini/gemini-3.8-flash",
                "gemini/gemini-2.5-flash",
                "gemini/gemini-3.8-flash|GEMINI_API_KEY_2",
                "gemini/gemini-2.5-flash|GEMINI_API_KEY_2",
                "openrouter/google/gemma-4-31b-it:free",
            ]
        },
        retry=RetryConfig(attempts=0, cooldown_s=60, timeout_s=5),
    )

    result = await LiteLLMGateway(config, clock=FakeClock()).complete("reasoning", MESSAGES)

    assert result.model == "openrouter/google/gemma-4-31b-it:free"
    assert result.fallback is True
    assert seen == [
        ("groq/big", "groq-key"),
        ("gemini/gemini-3.8-flash", "gemini-key-1"),
        ("gemini/gemini-2.5-flash", "gemini-key-1"),
        ("gemini/gemini-3.8-flash", "gemini-key-2"),
        ("gemini/gemini-2.5-flash", "gemini-key-2"),
        ("openrouter/google/gemma-4-31b-it:free", "openrouter-key"),
    ]
