import json
from datetime import date

from fastapi.testclient import TestClient

from app.agents.rag import RagResult
from app.container import Container
from app.core.cache import MemoryCache
from app.core.ports import LLMResult
from app.main import create_app
from app.settings import Adapters, Settings


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        name = "message"
        data = "{}"
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = line.removeprefix("data: ")
        events.append((name, json.loads(data)))
    return events


class ScriptedLLM:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0

    async def complete(self, role, messages, **kwargs):
        self.calls += 1
        return LLMResult(
            text=json.dumps(self.payload),
            model="fake/fast",
            fallback=False,
            latency_ms=1,
        )


def router_payload(**overrides) -> dict:
    payload = {
        "intent": "qa",
        "language": "en",
        "jurisdiction": "federal",
        "authority": "FBR",
        "tax_year": None,
        "params": {},
        "standalone_question": "What is section 149?",
        "search_query": "section 149 salary",
    }
    payload.update(overrides)
    return payload


def make_client(llm, *, qa=None, today=None, cache=None) -> TestClient:
    settings = Settings(adapters=Adapters(llm="fake"))
    container = Container(
        settings=settings,
        llm=llm,
        qa=qa,
        answer_cache=cache if cache is not None else MemoryCache(),
        today=lambda: today or date(2026, 10, 14),
    )
    return TestClient(create_app(container))


def test_qa_stream_order_and_cache_hit():
    llm = ScriptedLLM(router_payload())
    qa_calls = {"n": 0}

    async def qa(body, routed, tax_year, corpus_date, budget):
        qa_calls["n"] += 1
        return RagResult(
            answer="Salary is taxed [1].",
            answer_source="verified",
            verified=True,
            replaced=False,
            model="fake/model",
        )

    client = make_client(llm, qa=qa, today=date(2026, 10, 14))
    first = client.post(
        "/api/v1/chat", json={"message": "What is section 149?", "tax_year": "TY2027"}
    )
    second = client.post(
        "/api/v1/chat", json={"message": "What is section 149?", "tax_year": "TY2027"}
    )

    assert first.status_code == 200
    events = parse_sse(first.text)
    names = [name for name, _data in events]
    assert names == ["meta", "token", "sources", "verification", "final", "done"]
    assert events[0][1]["intent"] == "qa"
    assert events[0][1]["tax_year"] == "TY2027"
    assert events[-2][1]["cached"] is False
    assert events[-2][1]["confidence"] == "medium"
    assert events[-2][1]["verified"] is True

    cached = parse_sse(second.text)
    assert [name for name, _data in cached] == ["meta", "final", "done"]
    assert cached[1][1]["cached"] is True
    assert llm.calls == 1
    assert qa_calls["n"] == 1


def test_bad_router_json_ends_with_done():
    llm = ScriptedLLM({})
    llm.complete = _bad_complete  # type: ignore[method-assign]

    response = make_client(llm).post("/api/v1/chat", json={"message": "What is section 149?"})

    events = parse_sse(response.text)
    assert [name for name, _data in events] == ["error", "done"]
    assert events[0][1]["code"] == "router_parse"


async def _bad_complete(role, messages, **kwargs):
    return LLMResult(text="not json", model="fake/fast", fallback=False, latency_ms=1)


def test_request_tax_year_overrides_the_calendar():
    llm = ScriptedLLM(router_payload(intent="chitchat", search_query=""))
    response = make_client(llm, today=date(2026, 10, 14)).post(
        "/api/v1/chat",
        json={"message": "Salam", "tax_year": "TY2026"},
    )

    meta = parse_sse(response.text)[0][1]
    assert meta["intent"] == "chitchat"
    assert meta["tax_year"] == "TY2026"


def test_june_date_defaults_to_ty2026():
    llm = ScriptedLLM(router_payload(intent="chitchat", search_query=""))
    response = make_client(llm, today=date(2026, 6, 30)).post(
        "/api/v1/chat",
        json={"message": "Salam"},
    )

    assert parse_sse(response.text)[0][1]["tax_year"] == "TY2026"


def test_qa_failure_emits_error_then_done():
    llm = ScriptedLLM(router_payload())

    async def qa(body, routed, tax_year, corpus_date, budget):
        raise RuntimeError("qdrant down")

    response = make_client(llm, qa=qa).post(
        "/api/v1/chat",
        json={"message": "What is section 149?", "tax_year": "TY2027"},
    )

    events = parse_sse(response.text)
    assert [name for name, _data in events] == ["meta", "error", "done"]
    assert events[1][1]["code"] == "qa_failed"


def test_empty_message_is_rejected():
    response = make_client(ScriptedLLM(router_payload())).post("/api/v1/chat", json={"message": ""})

    assert response.status_code == 422
