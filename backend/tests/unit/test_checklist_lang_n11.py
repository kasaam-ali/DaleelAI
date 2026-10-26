"""N11/N12: checklist titles in both languages; bad id is 422; experts RU copy."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings


def _client() -> TestClient:
    return TestClient(
        create_app(Container(settings=Settings(adapters=Adapters(llm="fake")), llm=FakeLLM()))
    )


def test_checklist_returns_both_titles():
    client = _client()
    session = {"X-Session-Id": str(uuid.uuid4())}
    template = client.get("/api/v1/checklists/templates").json()[0]
    made = client.post(
        "/api/v1/checklists",
        json={"template_id": template["id"], "answers": {}, "language": "en"},
        headers=session,
    )
    assert made.status_code == 201, made.text
    body = made.json()
    assert body["title_en"] == template["title"]
    assert body["title_ru"] == template["title_ru"]
    assert body["title_ru"] and body["title_ru"] != body["title_en"]


def test_bad_checklist_id_is_422_in_app_format():
    response = _client().get(
        "/api/v1/checklists/not-a-uuid", headers={"X-Session-Id": str(uuid.uuid4())}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
