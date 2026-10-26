"""Deterministic filing-date binder.

Post-process (design A): after the model answer and plain_answer strip, if the
retrieved s.114/118 text carries a filing-date clause and the ask needs that
taxpayer kind, make sure the spoken answer states the date. Dates are only
added when the clause is literally present in retrieved text; never invented.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_FILING_ASK = re.compile(
    r"\b(deadline|due date|last date|file|filing|return|114|118|akhri|tareekh|tarikh)\b", re.I
)
_COMPANY_ASK = re.compile(
    r"\b(compan(y|ies)|pvt|private limited|\(?pvt\)? ltd|limited company|corporate|corporation)\b",
    re.I,
)
_INDIVIDUAL_ASK = re.compile(
    r"\b(individuals?|salar(y|ied)|aop|association of persons|person|persons|naukri|mulazim)\b",
    re.I,
)
_ALL_ASK = re.compile(r"\b(all|every|each|har|sab|kinds?|types?|categories)\b", re.I)
_DEC31 = re.compile(r"thirty-first day of december|31(st)?\s+december|december\s+31", re.I)
_SEP30 = re.compile(r"thirtieth day of september|30(th)?\s+september|september\s+30", re.I)
_FALLBACK = re.compile(
    r"[^\n.]*(not clear from the sources|sources se clear nahi)[^\n]*?(FBR website[^\n.]*\.?)?",
    re.I,
)
_DAYMONTH_YEAR = re.compile(
    r"\b((?:30(?:th)?|thirtieth day of)\s+september|(?:31(?:st)?|thirty-first day of)\s+december)"
    r"(,?\s+)(\d{4})\b",
    re.I,
)
_SECTION = re.compile(r"\b(114|118)\b|return of income", re.I)


def _year(tax_year: str | None) -> str:
    m = re.search(r"(\d{4})", tax_year or "")
    return f" {m.group(1)}" if m else ""


def bind_filing_dates(
    answer: str,
    question: str,
    source_texts: Iterable[str],
    tax_year: str | None,
    language: str = "en",
) -> str:
    answer = _fix_years(answer, tax_year)
    q = question or ""
    if not _FILING_ASK.search(q):
        return answer
    texts = [t or "" for t in source_texts]
    joined = "\n".join(texts)
    if not _SECTION.search(joined):
        return answer
    company = bool(_COMPANY_ASK.search(q))
    individual = bool(_INDIVIDUAL_ASK.search(q))
    general = bool(_ALL_ASK.search(q)) or not (company or individual)
    yr = _year(tax_year)
    roman = language not in ("en", "", None)
    out = (answer or "").rstrip()
    add: list[str] = []
    if (individual or general) and _SEP30.search(joined) and not _SEP30.search(out):
        add.append(
            f"Individuals aur AOPs ke liye return 30 September{yr} tak file karni hoti hai."
            if roman
            else f"For individuals and AOPs, the return is due on or before 30 September{yr}."
        )
    if (company or general) and _DEC31.search(joined) and not _DEC31.search(out):
        add.append(
            f"Companies ke liye return 31 December{yr} tak file karni hoti hai."
            if roman
            else f"For companies, the return is due on or before 31 December{yr}."
        )
    if not add:
        return answer
    out = _FALLBACK.sub("", out).strip()
    return (out + ("\n\n" if out else "") + " ".join(add)).strip()


def _fix_years(answer: str, tax_year: str | None) -> str:
    """Force deadline day-month years to the asked tax year (TY2026 -> 2026)."""
    m = re.search(r"(\d{4})", tax_year or "")
    if not answer or not m:
        return answer
    return _DAYMONTH_YEAR.sub(lambda x: f"{x.group(1)}{x.group(2)}{m.group(1)}", answer)
