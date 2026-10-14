import json

import pytest

from app.agents.answer import generate_answer, verify_answer
from app.core.budget import CallBudget, CallBudgetExceeded
from app.core.cache import CachingLLM, MemoryCache, answer_cache_key
from app.core.ports import AllProvidersUnavailable, LLMResult
from app.core.retrieval.expand import ContextBlock
from app.core.retrieval.sufficiency import ABSTAIN_SENTENCE


class ScriptedLLM:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[str] = []
        self.messages = None

    async def complete(self, role, messages, **kwargs):
        self.calls.append(role)
        self.messages = messages
        return LLMResult(text=self.reply, model="fake/model", fallback=False, latency_ms=1)


def blocks() -> list[ContextBlock]:
    return [ContextBlock(parent_id="s149", text="Section 149 taxes salary.")]


async def test_generate_streams_deltas():
    class StreamingLLM:
        async def stream(self, role, messages, **kwargs):
            kwargs["info"]["model"] = "fake/stream"
            kwargs["info"]["fallback"] = False
            yield "Sal"
            yield "ary."

    seen: list[str] = []

    async def on_delta(text: str) -> None:
        seen.append(text)

    result = await generate_answer(
        StreamingLLM(),
        question="What is the salary tax?",
        language="en",
        tax_year="TY2027",
        corpus_date="2026-06-30",
        blocks=blocks(),
        mode="verified",
        on_delta=on_delta,
    )

    assert seen == ["Sal", "ary."]
    assert result.text == "Salary."
    assert result.model == "fake/stream"


async def test_generate_uses_reasoning_and_states_the_year():
    llm = ScriptedLLM("Salary is taxed under section 149. [1]")

    result = await generate_answer(
        llm,
        question="What is the salary tax?",
        language="en",
        tax_year="TY2027",
        corpus_date="2026-06-30",
        blocks=blocks(),
        mode="verified",
        budget=CallBudget(),
    )

    assert llm.calls == ["reasoning"]
    assert result.text.startswith("Salary is taxed")
    prompt = llm.messages[0].content + llm.messages[1].content
    assert "TY2027" in prompt
    assert "[1] Section 149 taxes salary." in prompt
    assert ABSTAIN_SENTENCE in prompt
    assert "official website" not in prompt


async def test_web_mode_adds_the_website_note_and_empty_context_skips_the_call():
    llm = ScriptedLLM("unused")
    budget = CallBudget()

    empty = await generate_answer(
        llm,
        question="?",
        language="en",
        tax_year="TY2027",
        corpus_date="2026-06-30",
        blocks=[],
        mode="web",
        budget=budget,
    )
    assert empty.text == ABSTAIN_SENTENCE
    assert budget.used == 0
    assert llm.calls == []

    await generate_answer(
        llm,
        question="How do I register?",
        language="roman_urdu",
        tax_year="TY2027",
        corpus_date="2026-10-10",
        blocks=blocks(),
        mode="web",
        budget=budget,
    )
    assert "official website" in llm.messages[0].content
    assert budget.used == 1


async def test_more_than_half_unsupported_is_replaced():
    draft = "Salary is taxed under section 149 [1]. The rate is 90 percent. File on Mars."
    labels = {
        "sentences": [
            {"sentence": "Salary is taxed under section 149 [1].", "supported": True},
            {"sentence": "The rate is 90 percent.", "supported": False},
            {"sentence": "File on Mars.", "supported": False},
        ]
    }
    budget = CallBudget(cap=5)

    checked = await verify_answer(
        ScriptedLLM(json.dumps(labels)),
        draft=draft,
        blocks=blocks(),
        mode="verified",
        budget=budget,
    )

    assert checked.replaced is True
    assert checked.verified is False
    assert checked.answer == ABSTAIN_SENTENCE
    assert budget.used == 1


async def test_one_unsupported_sentence_is_kept_and_web_is_never_verified():
    draft = "Salary is taxed under section 149 [1]. The rate is 90 percent."
    labels = {
        "sentences": [
            {"sentence": "Salary is taxed under section 149 [1].", "supported": True},
            {"sentence": "The rate is 90 percent.", "supported": False},
        ]
    }
    checked = await verify_answer(
        ScriptedLLM(json.dumps(labels)),
        draft=draft,
        blocks=blocks(),
        mode="web",
    )

    assert checked.replaced is False
    assert checked.verified is False
    assert checked.answer == draft
    assert checked.unsupported[0]["sentence"] == "The rate is 90 percent."


async def test_verify_keeps_the_draft_when_every_judge_is_down():
    class DownLLM:
        async def complete(self, role, messages, **kwargs):
            raise AllProvidersUnavailable("judge", ["all down"])

    checked = await verify_answer(
        DownLLM(),
        draft="Salary is taxed.",
        blocks=blocks(),
        mode="verified",
    )

    assert checked.verified is False
    assert checked.replaced is False
    assert checked.answer == "Salary is taxed."
    assert checked.confidence == "low"


def test_budget_cap_blocks_the_sixth_call():
    budget = CallBudget(cap=5)
    for _ in range(5):
        budget.charge()
    with pytest.raises(CallBudgetExceeded):
        budget.charge()


def test_answer_cache_key_ignores_case_and_extra_spaces():
    profile = {"filer_status": "filer"}
    left = answer_cache_key("  Kitna Tax? ", profile, "TY2027", "abc")
    right = answer_cache_key("kitna tax?", profile, "TY2027", "abc")
    other = answer_cache_key("kitna tax?", profile, "TY2026", "abc")

    assert left == right
    assert left != other


async def test_llm_cache_skips_the_second_call():
    from app.core.ports import ChatMessage

    inner = ScriptedLLM("cached body")
    caching = CachingLLM(inner, MemoryCache())
    messages = [ChatMessage(role="user", content="hello")]
    first = await caching.complete("fast", messages, temperature=0.0)
    second = await caching.complete("fast", messages, temperature=0.0)

    assert first.text == second.text == "cached body"
    assert inner.calls == ["fast"]
    assert caching.hits == 1


async def test_providers_down_is_not_caught_by_generate():
    class Down:
        async def complete(self, role, messages, **kwargs):
            raise AllProvidersUnavailable(role, ["down"])

    with pytest.raises(AllProvidersUnavailable):
        await generate_answer(
            Down(),
            question="tax?",
            language="en",
            tax_year="TY2027",
            corpus_date="2026-06-30",
            blocks=blocks(),
            mode="verified",
            budget=CallBudget(),
        )
