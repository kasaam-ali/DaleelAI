"""Five checklist templates. Progress is stored for the session."""

import json
import uuid
from pathlib import Path
from typing import Any

_TEMPLATES = Path(__file__).resolve().parent.parent / "checklists" / "templates"
_EXTRA = {
    ("ntn_individual", "work", "freelance"): {
        "id": "pseb",
        "title": "Ask PSEB about freelancer registration",
        "detail": (
            "Export of IT services is in section 154A. "
            "PSEB registration is separate from the NTN. "
            "Confirm the current form on the official PSEB site. No link is shown here."
        ),
        "sources": ["Income Tax Ordinance, 2001, section 154A"],
    },
    ("sales_tax_registration", "province", "punjab"): {
        "id": "pra",
        "title": "If the supply is services, open PRA",
        "detail": "Punjab sales tax on services is filed with the Punjab Revenue Authority.",
        "sources": ["Sales Tax Act, 1990, section 14"],
        "link": {"label": "Punjab Revenue Authority", "url": "http://e.pra.punjab.gov.pk/"},
    },
    ("sales_tax_registration", "province", "sindh"): {
        "id": "srb",
        "title": "If the supply is services, check SRB",
        "detail": (
            "Sindh sales tax on services is with the Sindh Revenue Board. "
            "This build does not show a URL because that address is not confirmed here."
        ),
        "sources": ["Sales Tax Act, 1990, section 14"],
    },
}


class ChecklistError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MemoryChecklists:
    """Process-local progress used when Postgres is not configured."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def save_checklist(
        self,
        *,
        session_id: str,
        template_id: str,
        answers: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> str:
        checklist_id = str(uuid.uuid4())
        self.rows[checklist_id] = {
            "session_id": session_id,
            "template_id": template_id,
            "answers": answers,
            "steps": steps,
        }
        return checklist_id

    def update_checklist_step(
        self,
        *,
        session_id: str,
        checklist_id: str,
        step_id: str,
        done: bool,
    ) -> dict[str, Any] | None:
        row = self.rows.get(checklist_id)
        if row is None or row["session_id"] != session_id:
            return None
        found = False
        for step in row["steps"]:
            if step["id"] == step_id:
                step["done"] = done
                found = True
        if not found:
            return None
        return row


memory_checklists = MemoryChecklists()


def list_templates() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(_TEMPLATES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if len(data["questions"]) > 3:
            raise ChecklistError("invalid_request", f"{data['id']} has more than 3 questions.")
        rows.append(
            {
                "id": data["id"],
                "title": data["title"],
                "title_ru": data["title_ru"],
                "description": data["description"],
                "questions": data["questions"],
            }
        )
    return rows


def start_checklist(
    template_id: str,
    answers: dict[str, str],
    language: str,
    repo: Any,
    session_id: str | None,
) -> dict[str, Any]:
    template = _load(template_id)
    clean = _answers(template, answers)
    steps = _steps(template, clean)
    checklist_id = str(uuid.uuid4())
    if repo is not None and session_id:
        checklist_id = repo.save_checklist(
            session_id=session_id,
            template_id=template_id,
            answers=clean,
            steps=steps,
        )
    return _public(checklist_id, template, language, steps)


def mark_step(
    checklist_id: str,
    step_id: str,
    done: bool,
    language: str,
    repo: Any,
    session_id: str,
) -> dict[str, Any]:
    if repo is None:
        raise ChecklistError("repository_unavailable", "Checklist storage is not configured.")
    saved = repo.update_checklist_step(
        session_id=session_id,
        checklist_id=checklist_id,
        step_id=step_id,
        done=done,
    )
    if saved is None:
        raise ChecklistError("not_found", "That checklist step was not found for this session.")
    template = _load(saved["template_id"])
    return _public(checklist_id, template, language, saved["steps"])


def checklist_from_chat(
    message: str,
    language: str,
    repo: Any,
    session_id: str | None,
) -> tuple[str | None, dict[str, Any] | None, str]:
    template_id = _match(message)
    if template_id is None:
        return (
            None,
            None,
            "Which checklist? NTN, AOP or company NTN, sales tax, SECP, or an income tax return.",
        )
    card = start_checklist(template_id, {}, language, repo, session_id)
    return "checklist", card, f"Checklist started: {card['title']}"


def _match(message: str) -> str | None:
    text = message.lower()
    if "sales tax" in text:
        return "sales_tax_registration"
    if "secp" in text or "incorporat" in text:
        return "secp_company_incorporation"
    if "aop" in text:
        return "ntn_aop_company"
    if "return" in text:
        return "income_tax_return"
    if "ntn" in text:
        return "ntn_individual"
    return None


def _load(template_id: str) -> dict[str, Any]:
    path = _TEMPLATES / f"{template_id}.json"
    if not path.is_file():
        raise ChecklistError("invalid_request", "Unknown checklist.")
    return json.loads(path.read_text(encoding="utf-8"))


def _answers(template: dict[str, Any], answers: dict[str, str]) -> dict[str, str]:
    allowed = {question["id"]: set(question["options"]) for question in template["questions"]}
    clean: dict[str, str] = {}
    for key, value in answers.items():
        if key not in allowed:
            raise ChecklistError("invalid_request", "Unknown question.")
        if value not in allowed[key]:
            raise ChecklistError("invalid_request", "Unknown answer.")
        clean[key] = value
    return clean


def _steps(template: dict[str, Any], answers: dict[str, str]) -> list[dict[str, Any]]:
    steps = [{**step, "done": False} for step in template["steps"]]
    for (template_id, question, value), extra in _EXTRA.items():
        if template["id"] == template_id and answers.get(question) == value:
            steps.append({**extra, "done": False})
    return steps


def _public(
    checklist_id: str,
    template: dict[str, Any],
    language: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    title = template["title_ru"] if language in {"roman_urdu", "urdu"} else template["title"]
    done = sum(1 for step in steps if step.get("done"))
    total = len(steps)
    return {
        "id": checklist_id,
        "template_id": template["id"],
        "title": title,
        "steps": steps,
        "progress": round(done / total, 2) if total else 0,
    }
