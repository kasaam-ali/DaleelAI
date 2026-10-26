"""Answer-quality scoring and the 160-question retrieval eval."""

import json

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.api.v1 import evaluation
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings
from eval.run_answers import correct, expects_refusal, load_rows, refused, score
from eval.run_retrieval import load_rows as retrieval_rows
from eval.run_retrieval import stand_in_report

_REPORT = evaluation._REPORT
_ABLATION = evaluation._ABLATION


def test_answer_dataset_has_the_160_test_rows_and_40_specials():
    rows = load_rows()
    assert sum(1 for row in rows if row["split"] == "test") == 160
    assert sum(1 for row in rows if row["kind"] != "answerable") == 40
    assert sum(1 for row in rows if expects_refusal(row)) == 32


def test_correctness_and_refusal_are_scored_against_the_reference():
    row = {
        "kind": "answerable",
        "gold_section": "149",
        "reference": (
            "Section 149 of the Income Tax Ordinance, 2001 is the salary withholding section."
        ),
    }
    assert correct(row, "Section 149 covers salary withholding.")
    assert not correct(row, "I am not sure about that.")
    assert refused("I can't help with hiding income.")
    assert refused("Abstain. Stamp duty is outside this library.")
    assert not refused("Section 149 applies to salary.")

    rows = load_rows()
    answers = {}
    for item in rows:
        if expects_refusal(item):
            answers[item["id"]] = {"id": item["id"], "answer": "Abstain. Refuse.", "latency_ms": 12}
        else:
            section = item.get("gold_section")
            answer = item["reference"] if not section else f"Section {section} applies."
            answers[item["id"]] = {
                "id": item["id"],
                "answer": answer,
                "latency_ms": 20,
            }
    report = score(rows, answers)
    assert report["test_rows"] == 160
    assert report["special_cases"] == 40
    assert report["refusal_cases"] == 32
    assert report["refusal_rate"] == 1.0
    assert report["correctness"] == 1.0
    assert report["mean_latency_ms"] == 18
    assert report["live"] is False


def test_stand_in_retrieval_covers_every_test_question():
    rows = retrieval_rows()
    report = stand_in_report(rows)
    assert report["index"] == "stand-in"
    assert report["rows"] == 160
    assert report["split"] == "test"
    assert report["dataset"]["test"] == 160
    assert report["dataset"]["kinds"]["answerable"] == 200
    stages = {stage["name"]: stage for stage in report["stages"]}
    assert stages["lexical"]["status"] == "stand_in"
    assert stages["lexical"]["rows"] == 160
    assert stages["lexical"]["recall_at_5"] >= 0.9
    assert stages["+rerank"]["status"] == "stand_in"
    assert stages["+rerank"]["recall_at_5"] >= 0.9
    assert stages["+verification"]["status"] == "not_rerun"
    assert stages["+verification"]["recall_at_5"] is None
    assert "verification" in report["not_run"]
    assert "qdrant" in report["not_run"]


def test_classifier_report_records_when_it_was_measured_and_the_label_kinds():
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert report["measured_at"] == "2026-10-14"
    assert report["dataset"]["kinds"]["income_tax|simple"] == 140
    assert report["dataset"]["train"] == 1272
    ablation = json.loads(_ABLATION.read_text(encoding="utf-8"))
    assert ablation["dataset"]["kinds"]["answerable"] == 200
    assert ablation["dataset"]["test"] == 160


def test_answers_endpoint_is_404_until_a_report_is_written(monkeypatch, tmp_path):
    monkeypatch.setattr(evaluation, "_ANSWERS", tmp_path / "missing.json")
    client = TestClient(
        create_app(Container(settings=Settings(adapters=Adapters(llm="fake")), llm=FakeLLM()))
    )
    missing = client.get("/api/v1/evaluation/answers")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    path = tmp_path / "answers.json"
    path.write_text(json.dumps({"correctness": 0.5, "refusal_rate": 1.0}), encoding="utf-8")
    monkeypatch.setattr(evaluation, "_ANSWERS", path)
    found = client.get("/api/v1/evaluation/answers")
    assert found.status_code == 200
    assert found.json()["refusal_rate"] == 1.0
