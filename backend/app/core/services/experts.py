"""Match a question to the curated directory. Public listing fields only."""

import json
from pathlib import Path
from typing import Any

from app.core.classifier import KeywordClassifier, Prediction

_PATH = Path(__file__).resolve().parent.parent / "experts" / "directory.json"
_CITIES = {
    "karachi": "Karachi",
    "lahore": "Lahore",
    "islamabad": "Islamabad",
    "faisalabad": "Faisalabad",
    "peshawar": "Peshawar",
    "rawalpindi": "Rawalpindi",
    "multan": "Multan",
}


class ExpertError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_directory() -> dict[str, Any]:
    return json.loads(_PATH.read_text(encoding="utf-8"))


def city_in_text(text: str) -> str | None:
    lowered = text.casefold()
    for key, label in _CITIES.items():
        if key in lowered:
            return label
    return None


def find_experts(
    query: str,
    *,
    city: str | None,
    category: str | None,
    classifier: Any | None = None,
    listings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = load_directory()
    model = classifier or KeywordClassifier()
    prediction: Prediction = model.predict(query)
    if category:
        prediction = prediction.model_copy(
            update={"category": category, "low_confidence": False, "confidence": 1.0}
        )
    rows = listings if listings is not None else list(directory["experts"])
    chosen = prediction.category
    matched = []
    wanted_city = _canon_city(city) if city else None
    for row in rows:
        if chosen and chosen not in row["specialties"]:
            continue
        if wanted_city and row["city"].casefold() != wanted_city.casefold():
            continue
        score = 0.9 if wanted_city else 0.75
        matched.append({**row, "match_score": score})
    matched.sort(key=lambda row: (-row["match_score"], row["name"], row["city"]))
    if prediction.low_confidence and not category:
        advice = "The category is uncertain. Pick one and search again."
        shown = []
    elif prediction.complexity == "simple" and not category:
        advice = "This looks like a short question. Ask it in chat before you hire anyone."
        shown = []
    elif not matched:
        advice = "No listing in that city covers this category."
        shown = []
    else:
        advice = "These are public listings for that category. Contact them yourself."
        shown = matched[:5]
    return {
        "classification": prediction.public(),
        "experts": shown,
        "advice": advice,
        "disclaimer": directory["disclaimer"],
        "removal_contact": directory["removal_contact"],
    }


def _canon_city(city: str) -> str:
    return _CITIES.get(city.casefold(), city)
