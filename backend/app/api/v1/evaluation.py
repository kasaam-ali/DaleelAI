"""Read the reports written by the training and eval scripts."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
_REPORT = Path(__file__).resolve().parents[3] / "ml" / "reports" / "classifier_metrics.json"
_ABLATION = Path(__file__).resolve().parents[3] / "eval" / "reports" / "ablation.json"
_ANSWERS = Path(__file__).resolve().parents[3] / "eval" / "reports" / "answers.json"


def _missing(message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": "not_found", "message": message}},
        status_code=404,
    )


@router.get("/evaluation/classifier", response_model=None)
def classifier_report() -> dict | JSONResponse:
    if not _REPORT.is_file():
        return _missing("The classifier report has not been written.")
    return json.loads(_REPORT.read_text(encoding="utf-8"))


@router.get("/evaluation/ablation", response_model=None)
def ablation_report() -> dict | JSONResponse:
    if not _ABLATION.is_file():
        return _missing("The ablation report has not been written.")
    return json.loads(_ABLATION.read_text(encoding="utf-8"))


@router.get("/evaluation/answers", response_model=None)
def answers_report() -> dict | JSONResponse:
    if not _ANSWERS.is_file():
        return _missing("The answer-quality report has not been written.")
    return json.loads(_ANSWERS.read_text(encoding="utf-8"))
