"""Saved answers for the demo script. A match returns before any model call."""

import json
import re
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).with_name("demo_answers.json")
_SPACE = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _SPACE.sub(" ", text.lower().replace("?", "").strip())


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    payload = json.loads(_PATH.read_text(encoding="utf-8"))
    return tuple(payload["items"])


def match_demo(message: str) -> dict | None:
    key = _norm(message)
    for row in _rows():
        if key in {_norm(item) for item in row["match"]}:
            return row
    return None
