"""Roman-Urdu / desi tax talk -> English statutory sub-queries. No Qdrant calls."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.core.retrieval.fusion import RankedHit
from app.core.retrieval.synonyms import expand_search_query

_STATUTE = re.compile(r"^(\d{1,3}[A-Z]{0,4})", re.I)
_HOMEPAGE = re.compile(r"^https?://[^/]+/?$", re.I)
_GENERIC_TITLES = frozenset(
    {
        "federal board of revenue",
        "khyber pakhtunkhwa revenue authority",
        "punjab revenue authority",
        "sindh revenue board",
        "balochistan revenue authority",
        "fbr",
        "kpra",
        "pra",
        "srb",
        "bra",
    }
)
_DESI = (
    "kya",
    "hai",
    "hain",
    "hoon",
    "mein",
    "mujhe",
    "kaise",
    "kitna",
    "bhai",
    "gari",
    "paise",
    "kiraya",
    "tankhwah",
)


@dataclass(frozen=True)
class TaxTopic:
    key: str
    query: str
    sections: tuple[str, ...]
    triggers: tuple[str, ...]


# First-match-wins is how the old enrich leaked 231B onto plot/remittance chats.
# Every matching topic becomes its own English search.
TOPICS: tuple[TaxTopic, ...] = (
    TaxTopic(
        "property",
        (
            "immovable property sale seller advance tax Section 236C "
            "buyer purchase tax Section 236K capital gains tax Section 37 holding period"
        ),
        ("236C", "236K", "37"),
        (
            "plot",
            "zameen",
            "flat",
            "apartment",
            "immovable",
            "property sale",
            "property purchase",
            "bech raha",
            "bech rahi",
            "bechne",
            "becha",
            "bech",
            "khareed",
            "kharida",
            "kharid",
            "transfer ke waqt",
            "registry",
            "236c",
            "236k",
        ),
    ),
    TaxTopic(
        "late_filer",
        (
            "Section 100BA Tenth Schedule Active Taxpayers List persons not appearing on ATL "
            "higher withholding rates"
        ),
        ("100BA",),
        (
            "late filer",
            "late file",
            "late filing",
            "late jama",
            "late return",
            "return date",
            "date guzar",
            "atl",
            "active taxpayer",
            "non-filer",
            "non filer",
            "tenth schedule",
            "100ba",
            "filer",
        ),
    ),
    TaxTopic(
        "return_filing",
        (
            "Section 114 return of income who must file Section 118 due date "
            "for furnishing return of income filing deadline individual association of persons "
            "30th September company 31st December"
        ),
        ("114", "118"),
        (
            "file return",
            "file my return",
            "file my income tax return",
            "file the return",
            "filing return",
            "return filing",
            "income tax return",
            "return file",
            "return jama",
            "section 114",
            "section 118",
        ),
    ),
    TaxTopic(
        "pension",
        (
            "pension received by an employee salary Section 12 pension or annuity "
            "Second Schedule exemption of pension retirement benefit"
        ),
        ("12",),
        ("pension", "pensioner", "retired", "retirement", "buzurg"),
    ),
    TaxTopic(
        "senior_profit",
        (
            "profit on debt senior citizen Behbood Savings Certificates pensioner "
            "withholding exemption"
        ),
        ("7B", "236S"),
        (
            "senior citizen",
            "behbood",
            "pensioner",
            "profit on debt",
            "savings certificate",
            "savings certificates",
        ),
    ),
    TaxTopic(
        "capital_gain",
        (
            "capital gains tax on immovable property Section 37 "
            "holding period gain on disposal of plot"
        ),
        ("37",),
        (
            "capital gain",
            "capital gains",
            "munafa",
            "munafe",
            "bache hain",
            "section 37",
        ),
    ),
    TaxTopic(
        "remittance",
        (
            "foreign exchange remittance banking channel Proceeds Realization Certificate "
            "PRC encashment Section 111(4) unexplained income gift from relative Section 39(3)"
        ),
        ("111", "39"),
        (
            "dubai",
            "overseas",
            "abroad",
            "bahar se",
            "foreign remittance",
            "remittance",
            "hundi",
            "hawala",
            "paise bheje",
            "paisa bheja",
            "bheje hain",
            "bheja hai",
            "gift",
            "tohfa",
            "hadiya",
            "prc",
            "proceeds realization",
            "encashment",
            "111(4)",
            "section 111",
            "unexplained",
            "saga bhai",
            "bahar se aaye",
        ),
    ),
    TaxTopic(
        "rent",
        "income from property rent chargeable tax Section 15 withholding tax on rent Section 155",
        ("15", "155"),
        (
            "kiraya",
            "kiraye",
            "kiray",
            "rent",
            "rental",
            "tenant",
            "portion",
            "section 15",
            "section 155",
            "155",
        ),
    ),
    TaxTopic(
        "salary",
        "salary income Section 12 deduction of tax from salary Section 149",
        ("12", "149"),
        (
            "tankhwah",
            "tankhwa",
            "tanakhwa",
            "salary",
            "salaried",
            "wages",
            "naukri",
            "office wale",
            "section 149",
            "section 12",
            "149",
        ),
    ),
    TaxTopic(
        "utility",
        (
            "advance tax on electricity bill Section 235 telephone mobile internet "
            "prepaid card Section 236 credit for tax collected Section 168 tax refund Section 170"
        ),
        ("235", "236", "168", "170"),
        (
            "bijli",
            "electricity",
            "wapda",
            "mobile",
            "internet",
            "prepaid",
            "telephone",
            "load",
            "section 235",
            "section 236",
            "section 168",
            "section 170",
            "235",
            "wapas mil",
            "adjust",
        ),
    ),
    TaxTopic(
        "vehicle",
        "advance tax motor vehicle registration Section 231B Division VII",
        ("231B",),
        ("gari", "gaari", "car", "motor vehicle", "231b", "section 231b"),
    ),
    TaxTopic(
        "cash",
        "advance tax on cash withdrawal Section 231AB banking company",
        ("231AB",),
        ("cash withdrawal", "231ab", "section 231ab", "withdrawal"),
    ),
    TaxTopic(
        "freelancer",
        "section 154A export of IT services PSEB freelancer withholding section 114 return",
        ("154A", "114"),
        ("freelancer", "upwork", "fiverr", "154a", "pseb", "export of services"),
    ),
    TaxTopic(
        "ntn",
        "section 181 NTN registration e-commerce digitally ordered goods sales tax",
        ("181",),
        ("ntn", "easypaisa", "online seller", "online clothes", "section 181", "181"),
    ),
    TaxTopic(
        "notice",
        "section 122 amendment of assessment section 114 return discrepancy FBR notice",
        ("122", "114"),
        ("notice", "show cause", "section 122", "122"),
    ),
    TaxTopic(
        "business",
        "business income Section 18 association of persons sole proprietorship return",
        ("18",),
        ("karobar", "business income", "sole proprietor"),
    ),
)

_LLM_REWRITE = (
    "Turn this Pakistani tax question into short English statutory search queries. "
    "Name Income Tax Ordinance sections when they apply. At most 3 queries, under 15 words each. "
    'Reply with JSON only: {"queries": ["..."]}.'
)


def detect_topics(text: str) -> list[TaxTopic]:
    blob = _normalize(text)
    found = [
        topic for topic in TOPICS if any(_has_trigger(blob, trigger) for trigger in topic.triggers)
    ]
    keys = {topic.key for topic in found}
    # "profit" on a Behbood / senior-citizen question is not a plot capital gain.
    # The freelancer and notice templates already search Section 114.
    if keys & {"freelancer", "notice"}:
        found = [topic for topic in found if topic.key != "return_filing"]
    if "senior_profit" in keys:
        found = [topic for topic in found if topic.key != "capital_gain"]
    # Cash withdrawal is Section 231AB. A capital-gain aside is not a plot sale,
    # and the plot template must not be written into the search text.
    if "cash" in keys and not _immovable_cue(text):
        found = [topic for topic in found if topic.key not in {"property", "capital_gain"}]
    return found


def topics_for_note(text: str) -> list[TaxTopic]:
    """Topics for a curated note. Drop our own search templates first.

    A cash-withdrawal rewrite names Section 37 and "plot" inside the capital-gain
    template. That text must not select the property note.
    """
    cleaned = text
    for topic in sorted(TOPICS, key=lambda item: len(item.query), reverse=True):
        cleaned = cleaned.replace(topic.query, " ")
    found = detect_topics(cleaned)
    keys = {topic.key for topic in found}
    # Judge the user's words, not a search template that names "plot" or "immovable".
    if "cash" in keys and not _immovable_cue(cleaned):
        found = [topic for topic in found if topic.key != "property"]
    return found


_PROPERTY_NOTE = (
    "Authoritative cross-reference: Seller advance tax is Section 236C and buyer advance tax "
    "is Section 236K. Late or non-ATL filers face higher withholding under Section 100BA "
    "and the Tenth Schedule."
)
_GAIN_NOTE = (
    "Profit on selling the property is capital gain on immovable property under "
    "Section 37(1A), First Schedule Division VIII holding-period rates. A plot acquired before "
    "1 July 2024 still uses holding-period rates; a 2-year holding period is not automatically "
    "zero."
)
_CASH_NOTE = (
    "Authoritative cross-reference: Advance tax on cash withdrawal is Section 231AB. It applies "
    "to persons not on the Active Taxpayers List (ATL); a filer on the ATL does not pay it. "
    "Rates are in the First Schedule and the Tenth Schedule."
)
_REMITTANCE_NOTE = (
    "Authoritative cross-reference: Section 111(4) — foreign exchange through normal banking "
    "channels is immune from source inquiry up to Rs 5 million per year. Rs 50 lakh is above that "
    "ceiling, not inside it. Do not say Rs 50 lakh is within the limit. Keep the bank PRC "
    "(Proceeds Realization Certificate) and the encashment certificate. "
    "Section 39(3) — a gift from a direct relative (brother) must come via a banking channel or "
    "cross-cheque. Section 231B — advance tax on motor vehicle registration "
    "or purchase still applies."
)
_INCOME_NOTE = (
    "Authoritative cross-reference: Section 149 is salary withholding. Section 15 income from "
    "property must be reported. Rent of 35,000 times 12 is 420,000, which is above the 300,000 "
    "rent threshold, so Section 155 withholding can also apply. Whenever Section 235 "
    "or Section 236 applies, also use Section 168 and Section 170. "
    "Advance tax on mobile and internet (Section 236) "
    "and electricity (Section 235) is adjustable against annual liability in the IRIS return under "
    "Section 168. Excess is claimable as a refund under Section 170, not automatic cash back. "
    "Do not describe those withholdings as non-adjustable."
)
_PROPERTY_NOTE_RU = (
    "Seller ka advance tax Section 236C hai aur buyer ka advance tax Section 236K hai. "
    "Late filer ya jo ATL par nahi, un par Section 100BA aur Tenth Schedule ke mutabiq "
    "zyada withholding hoti hai."
)
_GAIN_NOTE_RU = (
    "Property bechne ka munafa immovable property par capital gain hai, Section 37(1A), "
    "First Schedule Division VIII ke holding-period rates. 1 July 2024 se pehle liya hua plot "
    "ab bhi holding-period rates par hai; 2 saal ka holding automatic zero nahi."
)
_CASH_NOTE_RU = (
    "Cash nikalne par advance tax Section 231AB hai. Yeh un logon par lagta hai jo Active "
    "Taxpayers List (ATL) par nahi; ATL wala filer yeh nahi deta. "
    "Rates First Schedule aur Tenth Schedule mein hain."
)
_REMITTANCE_NOTE_RU = (
    "Section 111(4): normal banking channel se aayi foreign exchange saal mein Rs 5 million "
    "tak source inquiry se immune hai. Rs 50 lakh us had se upar hai, limit ke andar nahi. "
    "Is liye bank se PRC (Proceeds Realization Certificate) aur encashment certificate rakhain. "
    "Section 39(3): seedhe rishtedar (bhai) ka gift banking channel ya "
    "cross-cheque se aana chahiye. "
    "Section 231B: gari ki registration ya kharid par advance tax phir bhi lagta hai."
)
_INCOME_NOTE_RU = (
    "Section 149 tankhwah ki withholding hai. "
    "Section 15 property ki income hai aur report karni hai. "
    "35 hazar mahana kiraya saal ka 4 lakh 20 hazar banta hai, jo 3 lakh ki had se upar hai, "
    "is liye Section 155 ki withholding bhi lag sakti hai. Jahan Section 235 ya Section 236 lage, "
    "wahan Section 168 aur Section 170 bhi dekhein. Mobile aur internet (Section 236) aur bijli "
    "(Section 235) ka advance tax IRIS return mein Section 168 ke tehat "
    "saalane tax se adjust hota hai. "
    "Zyada kata hua tax Section 170 ke tehat refund mang sakte hain. Yeh automatic cash back nahi, "
    "aur yeh withholding non-adjustable nahi hai."
)
_FREELANCER_NOTE = (
    "Authoritative cross-reference: Withholding on export of IT services is Section 154A. "
    "The income tax return is filed under Section 114."
)
_FREELANCER_NOTE_RU = (
    "IT services ke export par Section 154A ki withholding lagti hai. "
    "Income tax return Section 114 ke tehat file hoti hai."
)


def _immovable_cue(text: str) -> bool:
    """Plot, land, or a property sale. 'Capital gain' alone is not one."""
    blob = _normalize(text)
    cues = next(topic.triggers for topic in TOPICS if topic.key == "property")
    return any(
        _has_trigger(blob, trigger)
        for trigger in cues
        if trigger not in {"capital gain", "capital gains"}
    )


def cross_reference_note(text: str, *, language: str = "en") -> str:
    """Short statutory bridge for the topics this question already triggered."""
    keys = {topic.key for topic in topics_for_note(text)}
    if "cash" in keys and not _immovable_cue(text):
        keys.discard("property")
    roman = language == "roman_urdu"
    parts: list[str] = []
    if "cash" in keys:
        parts.append(_CASH_NOTE_RU if roman else _CASH_NOTE)
    if "property" in keys:
        parts.append(_PROPERTY_NOTE_RU if roman else _PROPERTY_NOTE)
        if "capital_gain" in keys:
            parts.append(_GAIN_NOTE_RU if roman else _GAIN_NOTE)
    if "remittance" in keys:
        parts.append(_REMITTANCE_NOTE_RU if roman else _REMITTANCE_NOTE)
    if "freelancer" in keys:
        parts.append(_FREELANCER_NOTE_RU if roman else _FREELANCER_NOTE)
    if "utility" in keys or {"salary", "rent"} <= keys:
        parts.append(_INCOME_NOTE_RU if roman else _INCOME_NOTE)
    return "\n\n".join(parts)


COMPANY_FILING_QUERY = (
    "Section 118 return of income in the case of a company due on or before the "
    "thirty-first day of December 31st December company filing deadline"
)
_COMPANY_DATE = re.compile(r"thirty[- ]first day of december|31(?:st)? december", re.I)


def is_company_date_hit(hit: RankedHit) -> bool:
    return hit_section(hit) == "118" and bool(
        _COMPANY_DATE.search(str(hit.payload.get("text") or ""))
    )


def rewrite_queries(message: str, search_query: str = "") -> list[str]:
    """One English statutory query per detected topic. Drops raw Roman Urdu."""
    blob = f"{message} {search_query}".strip()
    queries: list[str] = []
    for topic in detect_topics(blob):
        queries.append(topic.query)
        if topic.key == "return_filing":
            # The company clause of s118 loses to the individuals clause on one query.
            queries.append(COMPANY_FILING_QUERY)
    extra = (search_query or "").strip()
    if extra and extra not in queries and not _is_raw_desi(extra):
        queries.append(extra)
    if queries:
        return queries[:4]
    fallback = expand_search_query((search_query or message).strip())
    return [fallback] if fallback else [message]


def rewrite_search_query(message: str, search_query: str = "") -> str:
    return " ".join(rewrite_queries(message, search_query))


def section_key(value: str) -> str:
    match = _STATUTE.match(str(value).strip())
    return match.group(1).upper() if match else ""


def hit_section(hit: RankedHit) -> str:
    return section_key(str(hit.payload.get("section") or ""))


def is_statutory_hit(hit: RankedHit) -> bool:
    return bool(hit_section(hit))


def is_generic_web_hit(hit: RankedHit) -> bool:
    url = str(hit.payload.get("source_url") or hit.payload.get("url") or "").split("?", 1)[0]
    title = str(hit.payload.get("doc_title") or hit.payload.get("title") or "").strip().lower()
    if _HOMEPAGE.match(url):
        return True
    return title in _GENERIC_TITLES


def matching_topic_sections(hits: list[RankedHit], text: str) -> set[str]:
    wanted = {section.upper() for topic in detect_topics(text) for section in topic.sections}
    found = {hit_section(hit) for hit in hits}
    return {section for section in found if section and section in wanted}


def usable_web_hits(ranked: list[tuple[RankedHit, float]]) -> list[tuple[RankedHit, float]]:
    return [(hit, score) for hit, score in ranked if not is_generic_web_hit(hit)]


def retrieval_keep(base_keep: int, n_queries: int) -> int:
    return min(16, max(base_keep, 4 * max(1, n_queries)))


async def maybe_llm_queries(llm, text: str, budget) -> list[str]:
    """Extra English queries when the lexicon saw nothing. Fail-soft."""
    if detect_topics(text) or budget is None or budget.remaining() < 3:
        return []
    from app.core.ports import AllProvidersUnavailable, ChatMessage

    try:
        budget.charge()
        result = await llm.complete(
            "fast",
            [
                ChatMessage(role="system", content=_LLM_REWRITE),
                ChatMessage(role="user", content=text[:800]),
            ],
            temperature=0.0,
            max_tokens=200,
        )
    except AllProvidersUnavailable:
        return []
    return _parse_llm_queries(result.text)


def _parse_llm_queries(text: str) -> list[str]:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end <= start:
        # max_tokens cut the JSON off. Keep the queries that closed.
        return _closed_queries(text[start:])
    if start == -1 or end <= start:
        line = text.strip().strip('"').splitlines()[0].strip() if text.strip() else ""
        return [line[:300]] if line and not _is_raw_desi(line) else []
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return _closed_queries(text[start:])
    raw = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    queries: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip() and not _is_raw_desi(item):
            queries.append(item.strip()[:300])
        if len(queries) == 4:
            break
    return queries


def _closed_queries(text: str) -> list[str]:
    found = re.findall(r'"((?:[^"\\]|\\.){3,300})"\s*[,\]]', text)
    return [q.strip() for q in found if q.strip() and not _is_raw_desi(q)][:4]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9()]+", " ", text.lower()).strip()


# "bech raha" / "becha" / "bechne" are property sales. Prefix match made "bech"
# fire on "bechta" (I sell clothes) and pulled 236C into an NTN question.
_EXACT_WORD = frozenset({"bech"})


_SECTION_PHRASE = re.compile(r"section \d+[a-z]{0,4}\Z")


def _has_trigger(blob: str, trigger: str) -> bool:
    needle = trigger.lower()
    if " " in needle:
        # "section 236" is inside "section 236C", and "section 15" is inside "section 154A".
        # A following letter or digit means a different section.
        if _SECTION_PHRASE.fullmatch(needle):
            return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", blob) is not None
        return needle in blob
    # "236" must not fire inside "236C" or "236K".
    if any(char.isdigit() for char in needle):
        return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", blob) is not None
    if needle in _EXACT_WORD:
        return re.search(rf"\b{re.escape(needle)}\b", blob) is not None
    return re.search(rf"\b{re.escape(needle)}\w*\b", blob) is not None


def _is_raw_desi(text: str) -> bool:
    blob = _normalize(text)
    return any(_has_trigger(blob, word) for word in _DESI)
