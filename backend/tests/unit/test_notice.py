"""Eighteen synthetic notices. Personal numbers must never reach the model."""

import json
import re
from datetime import date
from pathlib import Path

import fitz
import pytest

from app.core.ports import LLMResult
from app.core.privacy.pii import outbound_pii
from app.core.services.notice import (
    NoticeError,
    _pdf_text,
    explain_upload,
    extract_text,
    mask_secrets,
    parse_fields,
    validate_upload,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "notices.json"
_TODAY = date(2026, 10, 14)
_CNIC = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
_NTN = re.compile(r"\b\d{7}-\d\b")
_PHONE = re.compile(r"(?<![A-Za-z0-9])(?:(?:\+92|0092)[\s-]?|0)3\d{2}[- ]?\d{7}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


class SpyLLM:
    def __init__(self) -> None:
        self.payloads: list[str] = []

    async def complete(self, role, messages, **kwargs):
        blob = "\n".join(message.content for message in messages)
        self.payloads.append(blob)
        text = "{}"
        if role == "reasoning":
            text = json.dumps(
                {
                    "summary": "Explained from the redacted notice.",
                    "why_received": "The office asked for a reply.",
                    "next_steps": ["Reply on IRIS."],
                }
            )
        return LLMResult(text=text, model="spy", fallback=False, latency_ms=1)


def _load() -> list[dict]:
    return json.loads(_FIXTURES.read_text(encoding="utf-8"))


def _body(row: dict) -> str:
    receipts = "Declared receipts 25000000 are not an NTN.\n" if row["id"] == "n01" else ""
    return (
        "Federal Board of Revenue\n"
        f"Office: {row['office']}\n"
        f"Notice under section {row['section']}\n"
        f"Tax Year {row['year']}\n"
        f"This is a {row['phrase']} notice.\n"
        f"Name: {row['name']}\n"
        f"CNIC: {row['cnic']}\n"
        f"NTN: {row['ntn']}\n"
        f"Phone: {row['phone']}\n"
        f"Email: {row['email']}\n"
        f"Amount demanded: Rs {row['amount']}\n"
        f"Deadline: {row['deadline']}\n"
        f"{receipts}"
        "Please reply on IRIS.\n"
    )


def _pdf(text: str, pages: int = 1) -> bytes:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        if index == 0:
            page.insert_textbox(fitz.Rect(48, 48, 560, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(scope="module")
def notices() -> list[dict]:
    rows = _load()
    assert 15 <= len(rows) <= 20
    return rows


async def test_every_notice_processes_and_pii_stays_out_of_the_model(notices):
    spy = SpyLLM()
    for row in notices:
        result = await explain_upload(
            _pdf(_body(row)),
            llm=spy,
            today=_TODAY,
            searcher=lambda _section, section=row["section"]: [
                {"section": section, "text": "Ordinance text."}
            ],
        )
        assert result["section"] == row["section"]
        assert result["tax_year"] == f"TY{row['year']}"
        assert result["notice_type"] == row["notice_type"]
        assert result["deadline"] == row["deadline"]
        assert result["amount"] == row["amount"]
        assert result["issuing_office"] == row["office"]
        assert result["redactions"]["cnic"] >= 1
        assert result["redactions"]["ntn"] >= 1
        assert result["explanation"]["summary"]
        assert result["sources"][0]["title"] == "Income Tax Ordinance, 2001"
        assert result["action_links"]
    joined = "\n".join(spy.payloads)
    assert spy.payloads
    assert outbound_pii(joined) is None
    assert _CNIC.search(joined) is None
    assert _NTN.search(joined) is None
    assert _PHONE.search(joined) is None
    assert _EMAIL.search(joined) is None
    for row in notices:
        assert row["cnic"] not in joined
        assert row["ntn"] not in joined
        assert row["name"] not in joined
        assert row["email"] not in joined
    assert "25000000" in joined
    soon = next(row for row in notices if row["id"] == "n04")
    soon_result = await explain_upload(_pdf(_body(soon)), llm=spy, today=_TODAY)
    assert soon_result["explanation"]["days_left"] == 2
    assert soon_result["explanation"]["severity"] == "high"
    assert soon_result["explanation"]["recommend_expert"] is True
    assert soon_result["expert_category"] == "audit_notice"
    calm = next(row for row in notices if row["id"] == "n18")
    calm_result = await explain_upload(_pdf(_body(calm)), llm=spy, today=_TODAY)
    assert calm_result["explanation"]["severity"] == "low"
    assert calm_result["explanation"]["recommend_expert"] is False


async def test_unredacted_text_never_reaches_the_llm(monkeypatch, notices):
    monkeypatch.setattr(
        "app.core.services.notice.redact_report",
        lambda text: (text, {"cnic": 0, "ntn": 0, "phone": 0, "email": 0, "name": 0}),
    )
    spy = SpyLLM()
    with pytest.raises(NoticeError) as raised:
        await explain_upload(_pdf(_body(notices[0])), llm=spy, today=_TODAY)
    assert raised.value.code == "invalid_request"
    assert spy.payloads == []


def test_mask_removes_the_cnic_from_the_page():
    raw = _pdf("CNIC: 11111-1111111-1 and nothing else of note in this notice text.")
    masked = mask_secrets(raw, "pdf", ["11111-1111111-1"])
    text, _ocr = extract_text(masked, "pdf")
    assert "11111-1111111-1" not in text


async def test_notice_asks_the_model_once(notices):
    roles: list[str] = []

    class Once:
        async def complete(self, role, messages, **kwargs):
            roles.append(role)
            return LLMResult(
                text=json.dumps(
                    {
                        "summary": "Explained from the redacted notice.",
                        "why_received": "The office asked for a reply.",
                        "next_steps": ["Reply on IRIS."],
                    }
                ),
                model="spy",
                fallback=False,
                latency_ms=1,
            )

    await explain_upload(_pdf(_body(notices[0])), llm=Once(), today=_TODAY)
    assert roles == ["reasoning"]


def test_plain_section_skips_the_layout_pass(monkeypatch):
    import pymupdf4llm

    def fail(*_args, **_kwargs):
        raise AssertionError("layout pass")

    monkeypatch.setattr(pymupdf4llm, "to_markdown", fail)
    text = _pdf_text(_pdf("Notice under section 114(4)\n" + "word " * 20))
    assert "114" in text


def test_layout_pass_runs_when_plain_text_has_no_section(monkeypatch):
    import pymupdf4llm

    monkeypatch.setattr(
        pymupdf4llm,
        "to_markdown",
        lambda _doc: "Notice under section 122(1)\n" + "word " * 20,
    )
    text = _pdf_text(_pdf("Office notice with a deadline and an amount but no statute label.\n"))
    assert "122" in text


def test_upload_limits():
    with pytest.raises(NoticeError) as bad_type:
        validate_upload(b"not a notice")
    assert bad_type.value.code == "invalid_file_type"
    with pytest.raises(NoticeError) as too_big:
        validate_upload(b"%PDF" + b"x" * (10 * 1024 * 1024))
    assert too_big.value.code == "file_too_large"
    with pytest.raises(NoticeError) as too_many:
        validate_upload(_pdf("A short notice that still has enough words to be a page.", pages=11))
    assert too_many.value.code == "too_many_pages"


def test_dated_amount_and_office_are_read_from_plain_wording():
    filing = parse_fields(
        "\n".join(
            [
                "REGIONAL TAX OFFICE, LAHORE",
                "Notice u/s 114(4) of the Income Tax Ordinance, 2001",
                "This is a non-filing notice. Penalty under section 182 may apply.",
                "Tax Year 2025",
                "Reply by 31-10-2026.",
                "Tax demanded Rs. 1,250,000.",
            ]
        )
    )
    assert filing["section"] == "114(4)"
    assert filing["notice_type"] == "return_filing"
    assert filing["deadline"] == "2026-10-31"
    assert filing["amount"] == 1_250_000
    assert filing["issuing_office"] == "REGIONAL TAX OFFICE LAHORE"
    assert "114(4)" in filing["section"]

    info = parse_fields(
        "\n".join(
            [
                "Large Taxpayers' Office, Islamabad",
                "Call for information u/s 176.",
                "Please respond before 25/10/2026.",
                "Rs. 75,000",
            ]
        )
    )
    assert info["section"] == "176"
    assert info["notice_type"] == "information"
    assert info["deadline"] == "2026-10-25"
    assert info["amount"] == 75_000
    assert info["issuing_office"] == "Large Taxpayers' Office Islamabad"


async def test_upload_keeps_a_dmy_deadline_and_a_rupee_amount():
    text = "\n".join(
        [
            "Office: RTO Lahore",
            "Notice u/s 176",
            "Tax Year 2025",
            "This is an information notice with enough words to be read.",
            "Reply by 31-10-2026.",
            "Amount demanded: Rs. 1,250,000",
        ]
    )
    result = await explain_upload(_pdf(text), today=_TODAY)
    assert result["section"] == "176"
    assert result["deadline"] == "2026-10-31"
    assert result["amount"] == 1_250_000
    assert result["issuing_office"] == "RTO Lahore"
    assert result["explanation"]["days_left"] == 17
    assert result["explanation"]["next_steps"][0] == "Reply on IRIS by 2026-10-31."
    assert result["sources"][0]["section"] == "176"
    assert "176" in result["sources"][0]["snippet"]
