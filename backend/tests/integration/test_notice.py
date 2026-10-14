"""Notice and checklist HTTP routes, including the chat cards."""

import json
import uuid

import fitz
from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.container import Container
from app.core.privacy.pii import outbound_pii
from app.main import create_app
from app.settings import Adapters, Settings
from tests.integration.test_chat import make_client, parse_sse, router_payload

_SESSION = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(
        fitz.Rect(48, 48, 560, 800),
        "\n".join(
            [
                "Office: RTO Lahore",
                "Notice under section 114(4)",
                "Tax Year 2025",
                "This is a filing notice.",
                "Name: Test Person One",
                "CNIC: 11111-1111111-1",
                "NTN: 1111111-1",
                "Phone: 0300-1111111",
                "Email: person1@example.com",
                "Amount demanded: Rs 180000",
                "Deadline: 2026-11-20",
                "Please reply on IRIS.",
            ]
        ),
        fontsize=10,
    )
    data = doc.tobytes()
    doc.close()
    return data


def test_explain_endpoint_redacts_before_the_model():
    llm = FakeLLM()
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))
    client = TestClient(create_app(Container(settings=settings, llm=llm)))
    response = client.post(
        "/api/v1/notice/explain",
        files={"file": ("notice.pdf", _pdf(), "application/pdf")},
        data={"language": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["section"] == "114(4)"
    assert body["redactions"]["cnic"] >= 1
    joined = "\n".join(message.content for _role, messages in llm.calls for message in messages)
    assert "11111-1111111-1" not in joined
    assert outbound_pii(joined) is None


def test_checklist_round_trip():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))
    client = TestClient(create_app(Container(settings=settings, llm=FakeLLM())))
    templates = client.get("/api/v1/checklists/templates")
    assert templates.status_code == 200
    assert len(templates.json()) == 5
    created = client.post(
        "/api/v1/checklists",
        headers={"X-Session-Id": _SESSION},
        json={"template_id": "income_tax_return", "answers": {"work": "salary"}, "language": "en"},
    )
    assert created.status_code == 201
    checklist_id = created.json()["id"]
    step_id = created.json()["steps"][0]["id"]
    patched = client.patch(
        f"/api/v1/checklists/{checklist_id}/steps/{step_id}",
        headers={"X-Session-Id": _SESSION},
        json={"done": True},
    )
    assert patched.status_code == 200
    assert patched.json()["progress"] > 0
    missing = client.post("/api/v1/checklists", json={"template_id": "income_tax_return"})
    assert missing.status_code == 400


def test_chat_notice_and_checklist_cards():
    notice = make_client(Scripted()).post(
        "/api/v1/chat",
        json={"message": "Explain this notice", "language": "en"},
    )
    notice_events = parse_sse(notice.text)
    assert notice_events[1][1]["card"]["type"] == "notice"
    assert "not saved" in notice_events[2][1]["text"]
    checklist = make_client(Scripted(intent="checklist")).post(
        "/api/v1/chat",
        json={"message": "Help me register an NTN", "language": "en"},
    )
    events = parse_sse(checklist.text)
    card = events[1][1]["card"]
    assert card["type"] == "checklist"
    assert card["data"]["template_id"] == "ntn_individual"


class Scripted:
    def __init__(self, intent: str = "notice") -> None:
        self.intent = intent

    async def complete(self, role, messages, **kwargs):
        from app.core.ports import LLMResult

        return LLMResult(
            text=json.dumps(router_payload(intent=self.intent, search_query="")),
            model="scripted",
            fallback=False,
            latency_ms=0,
        )


def test_other_session_cannot_mark_the_step():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))
    client = TestClient(create_app(Container(settings=settings, llm=FakeLLM())))
    created = client.post(
        "/api/v1/checklists",
        headers={"X-Session-Id": str(uuid.uuid4())},
        json={"template_id": "ntn_individual", "answers": {}},
    )
    checklist_id = created.json()["id"]
    step_id = created.json()["steps"][0]["id"]
    denied = client.patch(
        f"/api/v1/checklists/{checklist_id}/steps/{step_id}",
        headers={"X-Session-Id": str(uuid.uuid4())},
        json={"done": True},
    )
    assert denied.status_code == 404
