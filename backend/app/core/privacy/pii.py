"""Replace personal numbers with placeholders. Same cases as the browser redactor."""

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\bPK\d{2}[A-Z]{4}\d{16}\b", re.IGNORECASE), "[ACCOUNT]"),
    (re.compile(r"\b\d{5}-?\d{7}-?\d\b"), "[CNIC]"),
    (
        re.compile(r"(?<![A-Za-z0-9])(?:(?:\+92|0092)[\s-]?|0)3\d{2}[- ]?\d{7}\b"),
        "[PHONE]",
    ),
    (
        re.compile(
            r"\b(?:NTN(?:\s*No\.?)?|Registration\s*No\.?)\s*[:#-]?\s*(?:\d{7}-\d|\d{7,8})\b",
            re.IGNORECASE,
        ),
        "[NTN]",
    ),
    (re.compile(r"\b\d{7}-\d\b"), "[NTN]"),
    (
        re.compile(
            r"\b(?:account(?:\s*(?:no\.?|number))?|a/c)\s*[:#-]?\s*\d{10,18}\b",
            re.IGNORECASE,
        ),
        "[ACCOUNT]",
    ),
    (re.compile(r"\b(?:Name|Taxpayer)\s*:\s*[^,\n]{2,80}", re.IGNORECASE), "[NAME]"),
    (re.compile(r"\bAddress\s*:\s*[^\n]{2,120}", re.IGNORECASE), "[ADDRESS]"),
]


def redact_pii(text: str) -> str:
    """An unlabeled 7 or 8 digit run stays. It is a rupee amount, not an NTN."""
    out = text
    for pattern, placeholder in _PATTERNS:
        out = pattern.sub(placeholder, out)
    return out
