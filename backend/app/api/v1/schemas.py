"""API contract source (Pydantic)."""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


class StoredChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    intent: str | None = None
    language: str | None = None
    tax_year: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    answer_source: AnswerSource | None = None
    confidence: Confidence | None = None
    verified: bool | None = None
    model: str | None = None
    created_at: str
    feedback: Literal["up", "down"] | None = None
    feedback_reason: str | None = None


class ChatSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatListResponse(BaseModel):
    chats: list[ChatSummary]


class ChatDetail(ChatSummary):
    messages: list[StoredChatMessage]


class ChatTitleRequest(BaseModel):
    title: str | None = None


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


class AgentTrace(BaseModel):
    intent: str
    search_query: str
    retrieved: int | None = None
    rerank_top: float | None = None
    verified: bool | None = None
    latency_ms: int | None = None


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
    trace: AgentTrace | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal["up", "down"]
    reason: Literal["wrong", "incomplete", "outdated", "other"] | None = None
    comment: str | None = Field(default=None, max_length=1000)
    share_conversation: bool = False


class FeedbackResponse(BaseModel):
    id: str


class SalaryRequest(BaseModel):
    annual_income: int | None = None
    monthly_income: int | None = None
    tax_year: str = "TY2027"

    @model_validator(mode="after")
    def _one_income(self) -> "SalaryRequest":
        if (self.annual_income is None) == (self.monthly_income is None):
            raise ValueError("Send annual_income or monthly_income.")
        return self


class FreelancerRequest(BaseModel):
    annual_receipts: int
    regime: Literal["pseb_export", "export_services", "local_services"]
    filer_status: Literal["filer", "non_filer"] = "filer"
    tax_year: str = "TY2027"


class PropertyRequest(BaseModel):
    side: Literal["purchase", "sale"]
    value: int
    filer_status: Literal["filer", "late_filer", "non_filer"]
    holding_period_years: int | None = None
    tax_year: str = "TY2027"


class FilerTransaction(BaseModel):
    type: str
    amount: int
    engine_cc: int | None = None


class FilerCompareRequest(BaseModel):
    tax_year: str = "TY2027"
    transactions: list[FilerTransaction]


class TaxSource(BaseModel):
    law: str
    ref: str


class BreakdownLine(BaseModel):
    label: str
    base: int
    rate: float | None = None
    tax: int
    source: TaxSource


class YearDelta(BaseModel):
    tax_year: str
    total_tax: int
    difference: int


class CalculationResponse(BaseModel):
    tax_year: str
    inputs: dict[str, Any]
    total_tax: int
    effective_rate: float
    breakdown: list[BreakdownLine]
    notes: list[str]
    rules_version: str
    compared_to: YearDelta | None = None
    monthly_tax: int | None = None
    net_annual: int | None = None
    net_monthly: int | None = None


class FilerRow(BaseModel):
    type: str
    amount: int
    engine_cc: int | None = None
    filer_tax: int
    late_filer_tax: int | None = None
    non_filer_tax: int
    difference: int
    source: TaxSource


class FilerComparisonResponse(BaseModel):
    tax_year: str
    rows: list[FilerRow]
    filer_total: int
    non_filer_total: int
    savings: int
    notes: list[str]
    rules_version: str


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


class NoticeExplanation(BaseModel):
    summary: str
    why_received: str
    next_steps: list[str]
    severity: Literal["low", "medium", "high"]
    recommend_expert: bool
    days_left: int | None = None


class NoticeSource(BaseModel):
    title: str
    section: str | None = None
    snippet: str


class NoticeActionLink(BaseModel):
    topic: str
    label: str
    label_ru: str
    url: str
    authority: Authority


class NoticeResponse(BaseModel):
    notice_type: str
    law: str
    section: str | None = None
    tax_year: str | None = None
    amount: int | None = None
    deadline: str | None = None
    issuing_office: str | None = None
    explanation: NoticeExplanation
    sources: list[NoticeSource]
    redactions: dict[str, int]
    ocr_used: bool
    action_links: list[NoticeActionLink]
    classification: dict[str, Any] | None = None
    expert_category: str | None = None


class ChecklistQuestion(BaseModel):
    id: str
    prompt: str
    prompt_ru: str
    options: list[str]


class ChecklistTemplate(BaseModel):
    id: str
    title: str
    title_ru: str
    description: str
    questions: list[ChecklistQuestion]


class ChecklistStepLink(BaseModel):
    label: str
    url: str


class ChecklistStep(BaseModel):
    id: str
    title: str
    detail: str
    sources: list[str]
    done: bool
    link: ChecklistStepLink | None = None


class ChecklistRequest(BaseModel):
    template_id: str
    answers: dict[str, str] = Field(default_factory=dict)
    language: Literal["en", "roman_urdu", "urdu"] = "en"


class ChecklistStepPatch(BaseModel):
    done: bool


class ChecklistResponse(BaseModel):
    id: str
    template_id: str
    title: str
    steps: list[ChecklistStep]
    progress: float


class ExpertFindRequest(BaseModel):
    query: str
    city: str | None = None
    category: (
        Literal[
            "income_tax",
            "sales_tax",
            "customs",
            "corporate_secp",
            "audit_notice",
            "property",
        ]
        | None
    ) = None


class ExpertClassification(BaseModel):
    category: str | None
    complexity: Literal["simple", "complex"]
    confidence: float
    low_confidence: bool


class ExpertListing(BaseModel):
    id: str
    name: str
    firm: str | None = None
    city: str
    specialties: list[str]
    profile_url: str
    source: str
    last_updated: str
    match_score: float


class ExpertFindResponse(BaseModel):
    classification: ExpertClassification
    experts: list[ExpertListing]
    advice: str
    disclaimer: str
    removal_contact: str


class ExpertUpsert(BaseModel):
    id: str
    name: str
    firm: str | None = None
    city: str
    specialties: list[str]
    profile_url: str
    source: str
    last_updated: str


class UpdateItem(BaseModel):
    id: str
    title: str
    doc_type: str
    domain: str | None = None
    published_at: str | None = None
    effective_from: str | None = None
    summary: str
    summary_en: str = ""
    summary_ru: str = ""
    who_is_affected: str | None = None
    key_changes: list[str]
    source_url: str


class UpdateListResponse(BaseModel):
    items: list[UpdateItem]
    page: int
    pages: int
    total: int


class NotificationIngestItem(BaseModel):
    source_url: str
    listing_title: str
    doc_type: Literal["sro", "circular", "notification"]
    published_at: str | None = None
    sha256: str
    pdf_base64: str | None = None
    text: str | None = None


class NotificationIngestRequest(BaseModel):
    items: list[NotificationIngestItem]


class NotificationIngestResponse(BaseModel):
    ingested: int
    skipped: int
    indexed: int = 0
    corpus_version: str


class WebIngestPage(BaseModel):
    url: str
    status: Literal["new", "changed", "removed", "unchanged"]
    content_type: Literal["html", "pdf"] = "html"
    title: str | None = None
    sha256: str | None = None
    fetched_at: str | None = None
    html: str | None = None
    pdf_base64: str | None = None
    text: str | None = None


class WebIngestRequest(BaseModel):
    site: str
    crawl_id: str
    pages: list[WebIngestPage]


class WebIngestResponse(BaseModel):
    indexed: int
    removed: int
    unchanged: int
    corpus_version: str
