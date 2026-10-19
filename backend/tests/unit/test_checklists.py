"""Checklist templates, answers, and saved progress."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.adapters.memory_store import MemorySessionStore
from app.container import Container
from app.core.services.checklists import (
    MemoryChecklists,
    list_templates,
    mark_step,
    start_checklist,
)
from app.main import create_app
from app.settings import Adapters, Settings


def test_five_templates_have_at_most_three_questions():
    rows = list_templates()
    assert [row["id"] for row in rows] == [
        "income_tax_return",
        "ntn_aop_company",
        "ntn_individual",
        "sales_tax_registration",
        "secp_company_incorporation",
    ]
    for row in rows:
        assert len(row["questions"]) <= 3
        assert row["questions"]


def test_freelance_ntn_adds_a_pseb_step_and_progress_saves():
    repo = MemoryChecklists()
    session = str(uuid.uuid4())
    created = start_checklist(
        "ntn_individual",
        {"work": "freelance", "registered": "no"},
        "en",
        repo,
        session,
    )
    assert created["progress"] == 0
    assert any(step["id"] == "pseb" for step in created["steps"])
    assert any(
        (step.get("link") or {}).get("url") == "https://iris.fbr.gov.pk/"
        for step in created["steps"]
    )
    updated = mark_step(created["id"], "iris", True, "en", repo, session)
    assert updated["progress"] > 0
    assert next(step for step in updated["steps"] if step["id"] == "iris")["done"] is True


def test_secp_steps_do_not_invent_a_url():
    created = start_checklist("secp_company_incorporation", {"kind": "private"}, "en", None, None)
    assert all(step.get("link") is None for step in created["steps"])
    assert created["steps"][0]["sources"]


def test_tick_keeps_the_language_the_checklist_started_in():
    repo = MemoryChecklists()
    session = str(uuid.uuid4())
    created = start_checklist("ntn_individual", {}, "roman_urdu", repo, session)
    assert created["title"] == "NTN registration"
    step_id = created["steps"][0]["id"]
    updated = mark_step(created["id"], step_id, True, None, repo, session)
    assert updated["title"] == "NTN registration"
    assert updated["progress"] > 0
    english = mark_step(created["id"], step_id, False, "en", repo, session)
    assert english["title"] == "Register for an NTN"


def test_every_step_has_roman_urdu_text():
    created = start_checklist(
        "ntn_individual",
        {"work": "freelance", "registered": "no"},
        "en",
        None,
        None,
    )
    assert any(step["id"] == "pseb" for step in created["steps"])
    for step in created["steps"]:
        assert step["title_ru"]
        assert step["detail_ru"]
        assert step["title_ru"] != step["title"]
        assert step["detail_ru"] != step["detail"]


def test_list_and_get_stay_inside_the_session():
    store = MemorySessionStore()
    client = _client(store)
    mine = str(uuid.uuid4())
    theirs = str(uuid.uuid4())
    created = client.post(
        "/api/v1/checklists",
        headers={"X-Session-Id": mine},
        json={"template_id": "income_tax_return", "answers": {}, "language": "roman_urdu"},
    )
    assert created.status_code == 201
    checklist_id = created.json()["id"]
    assert created.json()["title"] == "Income tax return file karein"
    assert created.json()["steps"][0]["title_ru"]

    listed = client.get("/api/v1/checklists", headers={"X-Session-Id": mine})
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [checklist_id]

    empty = client.get("/api/v1/checklists", headers={"X-Session-Id": theirs})
    assert empty.status_code == 200
    assert empty.json() == []

    found = client.get(f"/api/v1/checklists/{checklist_id}", headers={"X-Session-Id": mine})
    assert found.status_code == 200
    assert found.json()["title"] == "Income tax return file karein"

    hidden = client.get(f"/api/v1/checklists/{checklist_id}", headers={"X-Session-Id": theirs})
    assert hidden.status_code == 404
    assert hidden.json() == {
        "error": {"code": "not_found", "message": "That checklist was not found."}
    }

    missing = client.get("/api/v1/checklists")
    assert missing.status_code == 400
    assert missing.json()["error"] == {
        "code": "invalid_request",
        "message": "X-Session-Id is required.",
    }
    bad_session = client.get("/api/v1/checklists", headers={"X-Session-Id": "not-a-uuid"})
    assert bad_session.status_code == 400
    assert bad_session.json()["error"]["message"] == "X-Session-Id must be a UUID."
    bad_id = client.get("/api/v1/checklists/not-a-uuid", headers={"X-Session-Id": mine})
    assert bad_id.status_code == 400
    assert bad_id.json()["error"]["message"] == "checklist id must be a UUID."
    absent = client.get(f"/api/v1/checklists/{uuid.uuid4()}", headers={"X-Session-Id": mine})
    assert absent.status_code == 404

    step_id = created.json()["steps"][0]["id"]
    patched = client.patch(
        f"/api/v1/checklists/{checklist_id}/steps/{step_id}",
        headers={"X-Session-Id": mine},
        json={"done": True},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Income tax return file karein"
    again = client.get(f"/api/v1/checklists/{checklist_id}", headers={"X-Session-Id": mine})
    assert again.json()["steps"][0]["done"] is True


def test_checklist_reads_report_missing_storage():
    client = _client(_SaveOnly())
    response = client.get("/api/v1/checklists", headers={"X-Session-Id": str(uuid.uuid4())})
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "repository_unavailable",
            "message": "Checklist storage is not configured.",
        }
    }
    detail = client.get(
        f"/api/v1/checklists/{uuid.uuid4()}",
        headers={"X-Session-Id": str(uuid.uuid4())},
    )
    assert detail.status_code == 503
    assert detail.json()["error"]["code"] == "repository_unavailable"


class _SaveOnly:
    def save_checklist(self, **_kwargs: object) -> str:
        return str(uuid.uuid4())


def _client(store: object) -> TestClient:
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))
    return TestClient(create_app(Container(settings=settings, llm=FakeLLM(), feedback=store)))
