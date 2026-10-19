"""Checklist templates, answers, and saved progress."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
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


def test_patch_keeps_the_roman_urdu_title():
    settings = Settings(adapters=Adapters(llm="fake"))
    client = TestClient(create_app(Container(settings=settings, llm=FakeLLM())))
    session = str(uuid.uuid4())
    created = client.post(
        "/api/v1/checklists",
        headers={"X-Session-Id": session},
        json={"template_id": "ntn_individual", "answers": {}, "language": "roman_urdu"},
    )
    body = created.json()
    assert created.status_code == 201
    assert body["title"] == "NTN registration"

    patched = client.patch(
        f"/api/v1/checklists/{body['id']}/steps/{body['steps'][0]['id']}",
        headers={"X-Session-Id": session},
        json={"done": True, "language": "roman_urdu"},
    )

    assert patched.status_code == 200
    assert patched.json()["title"] == "NTN registration"
    assert patched.json()["progress"] > 0


def test_secp_steps_do_not_invent_a_url():
    created = start_checklist("secp_company_incorporation", {"kind": "private"}, "en", None, None)
    assert all(step.get("link") is None for step in created["steps"])
    assert created["steps"][0]["sources"]
