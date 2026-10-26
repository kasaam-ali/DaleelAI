"""Checks the eval set and that a demo question matches a saved answer."""

import json
from pathlib import Path

from app.agents.rag import RagRequest, _result
from app.core.demo import match_demo
from app.core.retrieval.fusion import RankedHit

DATA = Path(__file__).resolve().parents[2] / "eval" / "datasets" / "answers.jsonl"


def test_eval_set_covers_languages_and_special_cases():
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == 240
    answerable = [row for row in rows if row["kind"] == "answerable"]
    assert sum(row["language"] == "en" for row in answerable) == 100
    assert sum(row["language"] == "roman_urdu" for row in answerable) == 100
    special = [row for row in rows if row["kind"] != "answerable"]
    assert len(special) == 40
    assert {row["kind"] for row in special} == {
        "unanswerable",
        "provincial",
        "tax_year",
        "injection",
        "evasion",
    }
    assert sum(row["split"] == "dev" for row in rows) == 80
    assert sum(row["split"] == "test" for row in rows) == 160
    assert all(row["provenance"] == "synthetic" for row in rows)
    assert all(row["gold_page"] is None for row in rows)


def test_demo_match_is_exact_and_skips_ordinary_questions():
    assert match_demo("What is section 149?") is None
    found = match_demo("Demo: what does section 149 cover?")
    assert found is not None
    assert "Section 149" in found["answer"]


def test_result_records_retrieved_count_and_top_score():
    hit = RankedHit(chunk_id="c1", payload={"text": "section 149"})
    request = RagRequest(
        question="salary",
        search_query="section 149 salary",
        language="en",
        tax_year="TY2027",
        corpus_date="2026-10-14",
    )
    result = _result(request, [], "verified", "answer", True, False, "m", [(hit, 0.81)])
    assert result.retrieved == 1
    assert result.rerank_top == 0.81
    assert result.sources[0].chunk_id == "c1"
