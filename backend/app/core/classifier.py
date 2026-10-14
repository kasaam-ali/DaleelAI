"""Domain and complexity labels. The keyword model is the fallback when ONNX is absent."""

import re
from typing import Literal

from pydantic import BaseModel

Domain = Literal[
    "income_tax",
    "sales_tax",
    "customs",
    "corporate_secp",
    "audit_notice",
    "property",
]
Complexity = Literal["simple", "complex"]
LOW_CONFIDENCE = 0.55

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "audit_notice",
        (
            "audit",
            "show cause",
            "notice",
            "recovery notice",
            "section 122",
            "section 177",
            "section 182",
            "appeal",
            "deadline",
        ),
    ),
    (
        "property",
        ("plot", "immovable", "section 236c", "section 236k", "236c", "236k", "property"),
    ),
    ("customs", ("customs", "goods declaration", "import gd", "tariff")),
    (
        "sales_tax",
        ("sales tax", "further tax", "input tax", "output tax", "pra", "srb"),
    ),
    (
        "corporate_secp",
        ("secp", "incorporat", "shareholder", "registered office", "director"),
    ),
    (
        "income_tax",
        (
            "salary",
            "income tax",
            "ntn",
            "filer",
            "dividend",
            "freelancer",
            "freelance",
            "withholding",
            "return",
            "section 154a",
            "section 4ab",
        ),
    ),
)
_COMPLEX = (
    "appeal",
    "deadline",
    "both",
    "together",
    "and a",
    "aur",
    "alag",
    "compare",
    "farq",
    "4 days",
    "4 din",
    "which deadline",
    "pehli deadline",
    "holding period",
    "end use",
    "revise",
    "amend",
)


class Prediction(BaseModel):
    category: str | None
    complexity: Complexity
    confidence: float
    low_confidence: bool

    def public(self) -> dict[str, str | float | bool | None]:
        return self.model_dump()


def retrieval_domain(prediction: Prediction) -> str | None:
    """Only a confident category is allowed to boost retrieval."""
    if prediction.low_confidence or not prediction.category:
        return None
    return prediction.category


class KeywordClassifier:
    """Phrase rules from the labeling guidelines. Used when the ONNX file is absent."""

    def predict(self, text: str) -> Prediction:
        lowered = text.casefold()
        hits = [
            domain
            for domain, phrases in _RULES
            if any(_phrase(lowered, phrase) for phrase in phrases)
        ]
        if not hits:
            return Prediction(
                category=None,
                complexity="simple",
                confidence=0.3,
                low_confidence=True,
            )
        category = hits[0]
        confidence = 0.82 if len(hits) == 1 else 0.46
        complexity: Complexity = (
            "complex" if any(_phrase(lowered, phrase) for phrase in _COMPLEX) else "simple"
        )
        return Prediction(
            category=category,
            complexity=complexity,
            confidence=confidence,
            low_confidence=confidence < LOW_CONFIDENCE,
        )


def _phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
