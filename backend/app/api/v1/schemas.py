"""API contract source (Pydantic)."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Language = Literal["en", "roman_urdu", "urdu"]
AnswerSource = Literal["verified", "web", "none"]
Confidence = Literal["high", "medium", "low"]
Intent = Literal[
    "qa",
    "notice",
    "calculate",
    "compare_filer",
    "checklist",
    "find_expert",
    "updates",
    "provincial",
    "refuse",
    "chitchat",
    "out_of_scope",
]
Authority = Literal["FBR", "SECP", "SRB", "PRA", "KPRA", "BRA"]
_TAX_YEAR = re.compile(r"^TY20\d{2}$")


class Profile(BaseModel):
    taxpayer_type: Literal["salaried", "freelancer", "business", "company"] | None = None
    filer_status: Literal["filer", "non_filer", "unknown"] | None = None
    province: Literal["punjab", "sindh", "kpk", "balochistan", "islamabad", "gb", "ajk"] | None = (
        None
    )
    city: str | None = None


class ChatRequest(BaseModel):
    chat_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    language: Literal["auto", "en", "roman_urdu", "urdu"] = "auto"
    tax_year: str | None = None
    profile: Profile | None = None

    @field_validator("tax_year")
    @classmethod
    def _tax_year(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _TAX_YEAR.fullmatch(value):
            raise ValueError("tax_year must look like TY2026")
        return value


class Source(BaseModel):
    library: Literal["verified", "web"]
    doc_id: str
    title: str
    section: str | None = None
    page: int | None = None
    url: str
    mirror_url: str | None = None
    site: str | None = None
    fetched_at: str | None = None
    snippet: str
    rerank_score: float | None = None


class ActionLink(BaseModel):
    topic: str
    label: str
    label_ru: str
    url: str
    authority: Authority


class MetaData(BaseModel):
    chat_id: str
    message_id: str
    intent: Intent
    language: Language
    tax_year: str


class TokenData(BaseModel):
    text: str


class SourcesData(BaseModel):
    sources: list[Source]


class VerificationData(BaseModel):
    verified: bool
    unsupported: list[dict] = Field(default_factory=list)
    replaced: bool


class FinalData(BaseModel):
    answer: str
    answer_source: AnswerSource
    confidence: Confidence
    verified: bool
    model: str
    tax_year: str
    corpus_date: str
    action_links: list[ActionLink] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    cached: bool


class ErrorData(BaseModel):
    code: str
    message: str


class MetaEvent(BaseModel):
    event: Literal["meta"]
    data: MetaData


class TokenEvent(BaseModel):
    event: Literal["token"]
    data: TokenData


class SourcesEvent(BaseModel):
    event: Literal["sources"]
    data: SourcesData


class VerificationEvent(BaseModel):
    event: Literal["verification"]
    data: VerificationData


class FinalEvent(BaseModel):
    event: Literal["final"]
    data: FinalData


class ErrorEvent(BaseModel):
    event: Literal["error"]
    data: ErrorData


class DoneEvent(BaseModel):
    event: Literal["done"]
    data: dict = Field(default_factory=dict)


SSE_EVENTS = (
    MetaEvent,
    TokenEvent,
    SourcesEvent,
    VerificationEvent,
    FinalEvent,
    ErrorEvent,
    DoneEvent,
)
