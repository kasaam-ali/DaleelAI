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
    (
        re.compile(
            r"\b(?:Name|Taxpayer)\s*:\s*"
            r"(?:(?!\b(?:CNIC|NTN|Phone|Email|Office|Amount|Deadline|Address)\b)[^,\n]){2,80}",
            re.IGNORECASE,
        ),
        "[NAME]",
    ),
    (
        re.compile(
            r"\bAddress\s*:\s*"
            r"(?:(?!\b(?:CNIC|NTN|Phone|Email|Name|Office|Amount|Deadline)\b)[^\n]){2,120}",
            re.IGNORECASE,
        ),
        "[ADDRESS]",
    ),
]


def redact_pii(text: str) -> str:
    """An unlabeled 7 or 8 digit run stays. It is a rupee amount, not an NTN."""
    return redact_report(text)[0]


_BUCKETS = {
    "[CNIC]": "cnic",
    "[NTN]": "ntn",
    "[PHONE]": "phone",
    "[EMAIL]": "email",
    "[NAME]": "name",
    "[ADDRESS]": "name",
}


def redact_report(text: str) -> tuple[str, dict[str, int]]:
    """Redact and count. Address hits are counted with names."""
    counts = {"cnic": 0, "ntn": 0, "phone": 0, "email": 0, "name": 0}
    out = text
    for pattern, placeholder in _PATTERNS:
        found = list(pattern.finditer(out))
        bucket = _BUCKETS.get(placeholder)
        if bucket is not None:
            counts[bucket] += len(found)
        out = pattern.sub(placeholder, out)
    return out, counts


def outbound_pii(text: str) -> str | None:
    """CNIC, hyphen or labeled NTN, phone, or email still present. Placeholders are clean."""
    for pattern, placeholder in _PATTERNS:
        if placeholder not in {"[CNIC]", "[NTN]", "[PHONE]", "[EMAIL]"}:
            continue
        match = pattern.search(text)
        if match is not None:
            return match.group(0)
    return None


def pii_secrets(text: str) -> list[str]:
    """Raw values to black out on a page. Placeholders are not secrets."""
    found: list[str] = []
    for pattern, placeholder in _PATTERNS:
        if placeholder not in {"[CNIC]", "[NTN]", "[PHONE]", "[EMAIL]"}:
            continue
        found.extend(match.group(0) for match in pattern.finditer(text))
    return found
