"""Checklist templates, answers, and saved progress."""

import uuid

from app.core.services.checklists import (
    MemoryChecklists,
    list_templates,
    mark_step,
    start_checklist,
)


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
