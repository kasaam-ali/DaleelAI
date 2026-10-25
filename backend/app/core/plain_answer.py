"""Keep section numbers out of the main answer prose (SPEC §5.2).

Legal refs stay in sources, [n] chips, the law panel and Details.
"""

import re

_NUM = r"\d{1,3}[A-Z]{0,4}(?:\(\w{1,4}\))*"
_REF = (
    rf"(?:Sections?|Sec\.?|s\.|§§?)\s*{_NUM}"
    rf"(?:\s*(?:,|and|or|aur|ya|/)\s*(?:(?:Sections?|s\.|§)\s*)?{_NUM})*"
)
_LAW = r"(?:\s+of\s+the\s+[A-Z][\w\s,]*?(?:Ordinance|Act|Rules)(?:,?\s*\d{4})?)?"
_PATTERNS = [
    (re.compile(rf"\s*\(\s*{_REF}{_LAW}\s*\)", re.I), ""),
    (re.compile(rf",?\s*\b(?:under|in|per|as per|according to|see)\s+{_REF}{_LAW}", re.I), ""),
    (re.compile(rf"\b{_REF}{_LAW}\s+(?:ke tehat|ke mutabiq|ke under|mein)\s*", re.I), ""),
    (re.compile(rf"\b{_REF}{_LAW}\s+(?:ka|ki|ke)\s+", re.I), ""),
    (re.compile(rf"\b{_REF}{_LAW}", re.I), "the law"),
]


def plain_answer(text: str, language: str = "en") -> str:
    out = text or ""
    for pattern, repl in _PATTERNS:
        if repl == "the law" and language == "roman_urdu":
            repl = "qanoon"
        out = pattern.sub(repl, out)
    out = re.sub(r"[ \t]+([.,;:!?])", r"\1", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out.strip()


_ANY_REF = re.compile(rf"\b{_REF}", re.I)


def plain_delta(text: str, language: str = "en") -> str:
    """Streamed chunk: touch it only when it carries a ref; keep its spacing."""
    if not _ANY_REF.search(text or ""):
        return text
    lead = text[: len(text) - len(text.lstrip())]
    tail = text[len(text.rstrip()) :]
    return lead + plain_answer(text, language) + tail
