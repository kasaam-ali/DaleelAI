import json
from datetime import date

import pytest

from app.agents.router import (
    ChatTurn,
    RouterParseError,
    RouterRequest,
    keyword_route,
    route,
)
from app.core.ports import AllProvidersUnavailable, ChatMessage, LLMResult

TODAY = date(2026, 10, 14)


def request(message: str, **kwargs) -> RouterRequest:
    base = {"message": message, "today": TODAY, "current_tax_year": "TY2027"}
    base.update(kwargs)
    return RouterRequest(**base)


class ScriptedLLM:
    def __init__(self, reply: str):
        self.reply = reply
        self.role = None
        self.messages: list[ChatMessage] | None = None
        self.kwargs: dict | None = None

    async def complete(self, role, messages, **kwargs):
        self.role = role
        self.messages = messages
        self.kwargs = kwargs
        return LLMResult(text=self.reply, model="fake/fast", fallback=False, latency_ms=1)


class DownLLM:
    async def complete(self, role, messages, **kwargs):
        raise AllProvidersUnavailable(role, ["all providers down"])


def model_json(**overrides) -> str:
    payload = {
        "intent": "qa",
        "language": "en",
        "jurisdiction": "federal",
        "authority": "FBR",
        "tax_year": None,
        "params": {},
        "standalone_question": "What is the salary tax?",
        "search_query": "salary income tax rate Pakistan",
    }
    payload.update(overrides)
    return json.dumps(payload)


async def test_structured_call_uses_fast_role_at_temperature_zero():
    llm = ScriptedLLM(model_json())

    output = await route(llm, request("What is the salary tax?"))

    assert llm.role == "fast"
    assert llm.kwargs["temperature"] == 0.0
    assert output.intent == "qa"
    assert output.search_query == "salary income tax rate Pakistan"
    assert output.tax_year is None
    assert "What is the salary tax?" in llm.messages[1].content
    assert "current_tax_year: TY2027" in llm.messages[1].content


async def test_fenced_json_and_explicit_tax_year():
    llm = ScriptedLLM("```json\n" + model_json(tax_year="TY2026", language="roman_urdu") + "\n```")

    output = await route(llm, request("TY2026 mein salary tax?"))

    assert output.tax_year == "TY2026"
    assert output.language == "roman_urdu"


async def test_urdu_script_overrides_model_language():
    llm = ScriptedLLM(model_json(language="en"))

    output = await route(llm, request("تنخواہ پر ٹیکس کتنا ہے؟"))

    assert output.language == "urdu"
    assert llm.role == "fast"


async def test_only_the_last_four_turns_are_sent():
    history = [ChatTurn(role="user", content=f"turn-{i}") for i in range(6)]
    llm = ScriptedLLM(model_json())

    await route(llm, request("follow up", history=history, profile={"taxpayer_type": "freelancer"}))

    prompt = llm.messages[1].content
    assert "turn-0" not in prompt
    assert "turn-1" not in prompt
    assert "turn-2" in prompt
    assert "turn-5" in prompt
    assert "freelancer" in prompt


async def test_invalid_json_is_not_a_keyword_fallback():
    llm = ScriptedLLM("I cannot help with that.")

    with pytest.raises(RouterParseError):
        await route(llm, request("What is section 149?"))


async def test_qa_without_search_query_is_rejected():
    llm = ScriptedLLM(model_json(search_query="  "))

    with pytest.raises(RouterParseError):
        await route(llm, request("What is section 149?"))


async def test_providers_down_uses_keyword_router():
    output = await route(DownLLM(), request("Non-filer pe kitna tax hai?"))

    assert output.intent == "compare_filer"
    assert output.language == "roman_urdu"
    assert output.search_query == ""
    assert output.tax_year is None


@pytest.mark.parametrize(
    ("message", "intent", "language"),
    [
        ("How do I evade tax on cash sales?", "refuse", "en"),
        ("Show cause notice aya hai", "notice", "roman_urdu"),
        ("How much tax on a salary of 1800000?", "calculate", "en"),
        ("NTN checklist chahiye", "checklist", "roman_urdu"),
        ("Need a tax lawyer in Lahore", "find_expert", "en"),
        ("Any latest SRO this week?", "updates", "en"),
        ("SRB sales tax registration", "provincial", "en"),
        ("Salam", "chitchat", "en"),
        ("What does section 149 say?", "qa", "en"),
        ("Freelancer pe kitna tax hai?", "calculate", "roman_urdu"),
    ],
)
def test_keyword_intents(message, intent, language):
    output = keyword_route(message)

    assert output.intent == intent
    assert output.language == language
    assert output.standalone_question == message


def test_keyword_provincial_authority_and_explicit_year():
    output = keyword_route("PRA pe tax year 2026 ka sales tax")

    assert output.intent == "provincial"
    assert output.authority == "PRA"
    assert output.jurisdiction == "provincial"
    assert output.tax_year == "TY2026"


def test_keyword_qa_keeps_the_message_as_the_search_query():
    output = keyword_route("section 149 salary withholding TY2027")

    assert output.intent == "qa"
    assert output.jurisdiction == "federal"
    assert output.authority == "FBR"
    assert output.tax_year == "TY2027"
    assert output.search_query == "section 149 salary withholding TY2027"


def test_greeting_plus_a_real_question_is_not_chitchat():
    output = keyword_route("hi what does section 149 say about salary")

    assert output.intent == "qa"
