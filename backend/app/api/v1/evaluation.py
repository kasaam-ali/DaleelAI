"""Read the classifier comparison written by ml/train_classifier.py."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
_REPORT = Path(__file__).resolve().parents[3] / "ml" / "reports" / "classifier_metrics.json"
_ABLATION = Path(__file__).resolve().parents[3] / "eval" / "reports" / "ablation.json"


@router.get("/evaluation/classifier", response_model=None)
def classifier_report() -> dict | JSONResponse:
    if not _REPORT.is_file():
        return JSONResponse(
            {
                "error": {
                    "code": "not_found",
                    "message": "The classifier report has not been written.",
                }
            },
            status_code=404,
        )
    return json.loads(_REPORT.read_text(encoding="utf-8"))


@router.get("/evaluation/ablation", response_model=None)
def ablation_report() -> dict | JSONResponse:
    if not _ABLATION.is_file():
        return JSONResponse(
            {
                "error": {
                    "code": "not_found",
                    "message": "The ablation report has not been written.",
                }
            },
            status_code=404,
        )
    return json.loads(_ABLATION.read_text(encoding="utf-8"))
