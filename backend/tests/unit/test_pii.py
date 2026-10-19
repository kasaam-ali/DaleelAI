"""Checks the shared CNIC, NTN, phone, and email cases."""

import json
from pathlib import Path

import pytest

from app.core.privacy.pii import redact_pii


def _cases_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "contracts" / "pii_cases.json",
        Path("/contracts/pii_cases.json"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("contracts/pii_cases.json")


CASES = json.loads(_cases_path().read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_shared_pii_cases(case):
    assert redact_pii(case["input"]) == case["output"]


def test_redaction_is_stable():
    once = redact_pii("\n".join(case["input"] for case in CASES))
    assert redact_pii(once) == once
