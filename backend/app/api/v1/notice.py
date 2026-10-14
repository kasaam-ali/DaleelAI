"""Explain an uploaded notice. The file stays in memory."""

from datetime import date

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api.v1.schemas import NoticeResponse
from app.core.services.notice import NoticeError, explain_upload

router = APIRouter()


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@router.post("/notice/explain", response_model=NoticeResponse)
async def explain_notice(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    language: str = Form(default="en"),  # noqa: B008
) -> NoticeResponse | JSONResponse:
    if language not in {"en", "roman_urdu", "urdu"}:
        return _error(400, "invalid_request", "Language must be en, roman_urdu, or urdu.")
    data = await file.read()
    store = request.app.state.container.feedback

    def searcher(section: str) -> list[dict]:
        if store is None or not hasattr(store, "find_sections"):
            return []
        return store.find_sections(section)

    try:
        body = await explain_upload(
            data,
            language=language,
            llm=request.app.state.container.llm,
            searcher=searcher,
            today=date.today(),
        )
    except NoticeError as exc:
        return _error(400, exc.code, exc.message)
    return NoticeResponse.model_validate(body)
