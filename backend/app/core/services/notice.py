"""Read a notice in memory, hide personal details, then explain the cited section."""

import json
import re
from collections.abc import Callable
from datetime import date
from typing import Any

import fitz

from app.core.classifier import KeywordClassifier
from app.core.ports import ChatMessage, LLMPort, Role
from app.core.privacy.pii import outbound_pii, redact_report
from app.core.retrieval.action_links import ActionLink, load_action_links, match_action_links
from app.settings import CONFIG_DIR

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
_MIN_TEXT = 40

_SECTION = re.compile(
    r"(?<![A-Za-z])(?:section|u\s*/\s*s\.?)\s*(\d+[A-Za-z]?(?:\(\d+[A-Za-z]?\))?)",
    re.IGNORECASE,
)
_TAX_YEAR = re.compile(r"Tax Year\s+(20\d{2})", re.IGNORECASE)
_DEADLINE_ISO = re.compile(r"Deadline:\s*(20\d{2}-\d{2}-\d{2})")
_DEADLINE_DMY = re.compile(
    r"\b(?:by|before|on or before)\s+(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b",
    re.IGNORECASE,
)
_AMOUNT_LABELED = re.compile(r"Amount demanded:\s*Rs\.?\s*([\d,]+)", re.IGNORECASE)
_AMOUNT_RS = re.compile(r"\bRs\.?\s*([\d,]+)", re.IGNORECASE)
_OFFICE_LABEL = re.compile(r"Office:\s*((?:RTO|LTU|CTO),?\s+[A-Za-z]+)", re.IGNORECASE)
_OFFICE_ABBR = re.compile(r"\b((?:RTO|LTU|CTO),?\s+[A-Za-z]+)\b", re.IGNORECASE)
_OFFICE_SPELLED = re.compile(
    r"((?:Regional Tax Office|Large Taxpayers'? Office|Corporate Tax Office),?\s+[A-Za-z]+)",
    re.IGNORECASE,
)
_NONFILING = ("non-filing", "non filing", "not filed", "failure to file", "failure to furnish")
_TYPES = (
    ("show cause", "show_cause"),
    ("penalty", "penalty"),
    ("audit", "audit"),
    ("refund", "refund"),
    ("information", "information"),
    ("recovery", "recovery"),
    ("unexplained", "assessment"),
    ("withholding", "assessment"),
    ("extension", "assessment"),
    ("statement", "assessment"),
    ("amendment", "assessment"),
    ("filing", "assessment"),
)
_COMPLEX = {"show_cause", "audit", "recovery", "penalty"}


class NoticeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def guard_user_text(text: str) -> None:
    """Stop before an external call if a personal number is still in user text."""
    if outbound_pii(text):
        raise NoticeError(
            "invalid_request",
            "Personal details were still in the text, so nothing was sent.",
        )


def validate_upload(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise NoticeError("file_too_large", "The file is larger than 10 MB.")
    if data.startswith(b"%PDF"):
        kind = "pdf"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        kind = "png"
    elif data.startswith(b"\xff\xd8\xff"):
        kind = "jpeg"
    else:
        raise NoticeError("invalid_file_type", "Upload a PDF, PNG, or JPEG.")
    if _page_count(data, kind) > MAX_PAGES:
        raise NoticeError("too_many_pages", "The file has more than 10 pages.")
    return kind


def mask_secrets(data: bytes, kind: str, secrets: list[str]) -> bytes:
    """Black out personal values on the page. The result stays in memory."""
    doc = fitz.open(stream=data, filetype=_filetype(kind))
    try:
        for page in doc:
            for secret in secrets:
                if len(secret) < 4:
                    continue
                for rect in page.search_for(secret):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
            page.apply_redactions()
        return doc.tobytes()
    finally:
        doc.close()


def parse_fields(text: str) -> dict[str, Any]:
    section = _first(_SECTION, text)
    year = _first(_TAX_YEAR, text)
    return {
        "law": "Income Tax Ordinance, 2001",
        "section": section,
        "tax_year": f"TY{year}" if year else None,
        "notice_type": _notice_type(text, section),
        "deadline": _deadline(text),
        "amount": _amount(text),
        "issuing_office": _office(text),
    }


async def explain_upload(
    data: bytes,
    *,
    language: str = "en",
    llm: LLMPort | None = None,
    searcher: Callable[[str], list[dict[str, Any]]] | None = None,
    today: date | None = None,
    link_rules: list | None = None,
    classifier=None,
) -> dict[str, Any]:
    """Validate, extract, redact, then explain. The upload is never written to disk."""
    kind = validate_upload(data)
    raw_text, ocr_used = extract_text(data, kind)
    if len(raw_text.strip()) < _MIN_TEXT:
        raise NoticeError(
            "invalid_request",
            "The notice could not be read. The image was not sent anywhere.",
        )
    redacted, redactions = redact_report(raw_text)
    guard_user_text(redacted)
    fields = parse_fields(redacted)
    snippets = _snippets(searcher, fields.get("section"))
    explanation = _local_explanation(fields, language)
    if llm is not None:
        law = "\n".join(item["text"] for item in snippets)
        result = await _complete(
            llm,
            "reasoning",
            redacted,
            "Explain the notice in the requested language. Use only the notice and the law text.",
            law=law,
        )
        parsed = _json_object(result.text if result is not None else "")
        if parsed and isinstance(parsed.get("summary"), str):
            explanation["summary"] = parsed["summary"]
            if isinstance(parsed.get("why_received"), str):
                explanation["why_received"] = parsed["why_received"]
            if isinstance(parsed.get("next_steps"), list):
                explanation["next_steps"] = [str(step) for step in parsed["next_steps"]]
    clock = today or date.today()
    days_left = _days_left(fields.get("deadline"), clock)
    notice_type = fields["notice_type"]
    explanation["days_left"] = days_left
    explanation["recommend_expert"] = notice_type in _COMPLEX or (
        days_left is not None and days_left < 7
    )
    explanation["severity"] = _severity(notice_type, days_left)
    rules = (
        link_rules
        if link_rules is not None
        else load_action_links(CONFIG_DIR / "action_links.yaml")
    )
    links = match_action_links("return filing IRIS", rules)
    model = classifier or KeywordClassifier()
    prediction = model.predict(redacted)
    return {
        **fields,
        "explanation": explanation,
        "sources": _sources(fields, snippets),
        "redactions": redactions,
        "ocr_used": ocr_used,
        "action_links": [_link(item) for item in links],
        "classification": prediction.public(),
        "expert_category": prediction.category if explanation["recommend_expert"] else None,
    }


def extract_text(data: bytes, kind: str) -> tuple[str, bool]:
    if kind == "pdf":
        text = _pdf_text(data)
        if len(text.strip()) >= _MIN_TEXT:
            return text, False
        return _ocr_pdf(data) or text, True
    return _ocr_image(data), True


def notice_prompt() -> tuple[str, dict[str, Any], str]:
    message = (
        "Open the Notice page and upload the PDF or photo. It is read in memory and not saved."
    )
    return "notice", {"upload": True, "message": message}, message


def _pdf_text(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        plain = "\n".join(page.get_text() for page in doc)
        # Layout analysis is the slow part of a notice. Skip it when the page
        # text already names a section.
        if len(plain.strip()) >= _MIN_TEXT and _SECTION.search(plain):
            return plain
        markdown = ""
        try:
            import pymupdf4llm

            markdown = pymupdf4llm.to_markdown(doc) or ""
        except Exception:
            markdown = ""
        if _SECTION.search(markdown):
            return markdown
        return plain or markdown
    finally:
        doc.close()


def _ocr_pdf(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    try:
        for page in doc:
            pixmap = page.get_pixmap(dpi=120)
            parts.append(_ocr_bytes(pixmap.tobytes("png")))
    finally:
        doc.close()
    return "\n".join(part for part in parts if part)


def _ocr_image(data: bytes) -> str:
    return _ocr_bytes(data)


def _ocr_bytes(data: bytes) -> str:
    try:
        import io

        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image) or ""
    except Exception:
        return ""


def _page_count(data: bytes, kind: str) -> int:
    try:
        doc = fitz.open(stream=data, filetype=_filetype(kind))
    except Exception as exc:
        raise NoticeError("invalid_file_type", "The file could not be read.") from exc
    try:
        return doc.page_count
    finally:
        doc.close()


def _filetype(kind: str) -> str:
    if kind == "jpeg":
        return "jpeg"
    return kind


async def _complete(
    llm: LLMPort,
    role: Role,
    redacted: str,
    instruction: str,
    law: str = "",
):
    guard_user_text(redacted)
    messages = [
        ChatMessage(role="system", content=instruction),
        ChatMessage(role="user", content="NOTICE:\n" + redacted),
    ]
    if law:
        messages.append(ChatMessage(role="user", content="LAW:\n" + law))
    try:
        return await llm.complete(role, messages, temperature=0.0, max_tokens=600)
    except NoticeError:
        raise
    except Exception:
        return None


def _snippets(
    searcher: Callable[[str], list[dict[str, Any]]] | None,
    section: str | None,
) -> list[dict[str, Any]]:
    if searcher is None or not section:
        return []
    try:
        found = searcher(section) or []
    except Exception:
        return []
    return [item for item in found if item.get("text")]


def _sources(fields: dict[str, Any], snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not snippets:
        section = fields.get("section") or ""
        return [
            {
                "title": "Income Tax Ordinance, 2001",
                "section": section,
                "snippet": f"The notice cites section {section}.",
            }
        ]
    return [
        {
            "title": "Income Tax Ordinance, 2001",
            "section": item.get("section") or fields.get("section"),
            "snippet": item.get("text", "")[:400],
        }
        for item in snippets
    ]


def _local_explanation(fields: dict[str, Any], language: str) -> dict[str, Any]:
    section = fields.get("section") or "the cited section"
    office = fields.get("issuing_office") or "the issuing office"
    deadline = fields.get("deadline")
    if language == "roman_urdu":
        summary = f"Yeh notice section {section} ke tehat hai."
        why = f"{office} ne is section ke tehat jawab manga hai."
        first = (
            f"IRIS par {deadline} se pehle jawab dein."
            if deadline
            else "Notice par likhi deadline se pehle IRIS par jawab dein."
        )
        steps = [first, "Cited section ka text padhein."]
    else:
        summary = f"This notice is under section {section} of the Income Tax Ordinance, 2001."
        why = f"{office} asked for a reply under that section."
        first = (
            f"Reply on IRIS by {deadline}."
            if deadline
            else "Reply on IRIS before the deadline printed on the notice."
        )
        steps = [first, "Read the cited section before you reply."]
    return {"summary": summary, "why_received": why, "next_steps": steps}


def _days_left(deadline: str | None, today: date) -> int | None:
    if not deadline:
        return None
    year, month, day = (int(part) for part in deadline.split("-"))
    return (date(year, month, day) - today).days


def _severity(notice_type: str, days_left: int | None) -> str:
    if days_left is not None and days_left < 7:
        return "high"
    if notice_type in {"recovery", "audit"}:
        return "high"
    if notice_type in {"show_cause", "penalty"}:
        return "medium"
    return "low"


def _json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _notice_type(text: str, section: str | None) -> str:
    """114(4) asks for a return. A later penalty warning does not retype it."""
    if section and re.match(r"114\b", section):
        return "return_filing"
    lowered = text.lower()
    if any(phrase in lowered for phrase in _NONFILING):
        return "assessment"
    for phrase, name in _TYPES:
        if phrase in lowered:
            return name
    return "other"


def _deadline(text: str) -> str | None:
    iso = _DEADLINE_ISO.search(text)
    if iso:
        return iso.group(1)
    found = _DEADLINE_DMY.search(text)
    if found is None:
        return None
    day, month, year = (int(found.group(part)) for part in (1, 2, 3))
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _amount(text: str) -> int | None:
    found = _AMOUNT_LABELED.search(text) or _AMOUNT_RS.search(text)
    if found is None:
        return None
    digits = found.group(1).replace(",", "")
    if not digits.isdigit():
        return None
    return int(digits)


def _office(text: str) -> str | None:
    found = _OFFICE_LABEL.search(text) or _OFFICE_ABBR.search(text) or _OFFICE_SPELLED.search(text)
    if found is None:
        return None
    return re.sub(r"\s+", " ", found.group(1).replace(",", " ")).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1).strip()


def _link(item: ActionLink) -> dict[str, str]:
    return item.model_dump()
