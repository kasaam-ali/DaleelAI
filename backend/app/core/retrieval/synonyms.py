"""Expand an English search query with TAX_SYNONYMS. No LLM call."""

import re

# Kept from v1 (src/retriever.py). Matching is whole-word, and at most 6 terms are added.
TAX_SYNONYMS: dict[str, list[str]] = {
    "petrol": ["petrol", "diesel", "fuel", "gasoline", "petroleum", "fuel levy", "petroleum levy"],
    "car": ["vehicle", "motor vehicle", "automobile", "transport", "car"],
    "bike": ["motorcycle", "motorbike", "two wheeler", "scooter"],
    "salary": ["wages", "remuneration", "pay", "salary", "earnings"],
    "business": ["company", "firm", "enterprise", "sole proprietorship", "aop", "business"],
    "freelancer": [
        "independent contractor",
        "self-employed",
        "export of services",
        "section 154A",
        "IT services",
        "PSEB",
    ],
    "property": ["real estate", "immovable property", "land", "building", "house", "plot"],
    "ntn": [
        "national tax number",
        "tax registration",
        "taxpayer identification",
        "section 181",
        "CNIC",
    ],
    "gst": ["sales tax", "value added tax", "vat", "general sales tax", "gst registration"],
    "return": ["tax return", "income tax return", "itr", "declaration", "filing"],
    "penalty": ["fine", "surcharge", "default", "late filing fee", "penalty"],
    "withholding": ["advance tax", "deduction at source", "wht", "withholding tax"],
    "exemption": ["tax free", "zero tax", "relief", "rebate", "exemption"],
    "deduction": ["allowance", "expense", "write-off", "adjustment", "deduction"],
    "registration": ["enrollment", "signup", "apply", "register", "registration"],
    "deadline": ["due date", "last date", "timeline", "time limit", "deadline"],
    "rate": ["percentage", "tax rate", "levy", "duty", "rate"],
    "import": ["customs duty", "import duty", "tariff", "customs", "import"],
    "export": ["export rebate", "drawback", "export incentive", "export"],
    "bank": ["financial institution", "banking", "bank", "financial"],
    "dividend": ["profit distribution", "shareholder payment", "dividend"],
    "capital gain": ["property sale profit", "shares profit", "capital gains", "cgt"],
    "jewelry": ["gold", "silver", "precious metal", "ornament", "jewelry"],
    "cash": ["currency", "banknote", "money", "cash", "liquid funds", "section 231AB"],
    "notice": ["show cause", "section 122", "amendment of assessment", "audit"],
    "foreign": ["overseas", "abroad", "international", "foreign", "offshore"],
    "agriculture": ["farming", "crop", "livestock", "agricultural", "farm"],
    "pension": ["retirement benefit", "superannuation", "pension", "retirement"],
    "medical": ["health", "hospital", "treatment", "medical expense", "healthcare"],
    "education": ["school", "university", "tuition", "educational", "education"],
    "donation": ["charity", "zakat", "sadqa", "philanthropy", "donation"],
    "loan": ["borrowing", "credit", "debt", "financing", "loan", "mortgage"],
    "rent": ["lease", "tenancy", "rental income", "rent", "leasing"],
    "insurance": ["policy", "premium", "coverage", "insurance", "assurance"],
    "stock": ["shares", "equity", "securities", "stock market", "stock"],
    "profit": ["gain", "earnings", "net income", "bottom line", "profit"],
    "loss": ["deficit", "negative income", "write-off", "loss", "carry forward"],
}

_MAX_ADDED = 6


def expand_search_query(query: str, *, limit: int = _MAX_ADDED) -> str:
    """Append up to `limit` synonym terms. The original query stays at the front."""
    added = added_terms(query, limit=limit)
    if not added:
        return query
    return f"{query} {' '.join(added)}"


def added_terms(query: str, *, limit: int = _MAX_ADDED) -> list[str]:
    lowered = query.lower()
    added: list[str] = []
    for key, synonyms in TAX_SYNONYMS.items():
        group = [key, *synonyms]
        if not any(_whole_term(lowered, term) for term in group):
            continue
        for term in group:
            if _whole_term(lowered, term) or term in added:
                continue
            added.append(term)
            if len(added) >= limit:
                return added
    return added


def _whole_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term.lower())}\b", text) is not None
