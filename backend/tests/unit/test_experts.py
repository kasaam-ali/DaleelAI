"""Classifier data, keyword fallback, and the expert directory."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.adapters.onnx_classifier import OnnxClassifier
from app.container import Container
from app.core.classifier import KeywordClassifier, Prediction, retrieval_domain
from app.core.ports import LLMResult
from app.core.privacy.pii import outbound_pii
from app.core.retrieval.fusion import fuse_hits
from app.core.services.experts import find_experts
from app.main import create_app
from app.settings import Adapters, Settings
from ml.dataset import DOMAINS, human_rows, synthetic_rows
from tests.integration.test_chat import make_client, parse_sse, router_payload
from tests.unit.test_retrieve import hit


def test_datasets_are_separate_and_labeled():
    train, synthetic = synthetic_rows()
    human = human_rows()
    assert 1500 <= len(train) + len(synthetic) <= 2000
    assert len(human) >= 60
    human_text = {row["question"].casefold() for row in human}
    synthetic_text = {row["question"].casefold() for row in train + synthetic}
    assert human_text.isdisjoint(synthetic_text)
    for row in train + synthetic + human:
        assert row["domain"] in DOMAINS
        assert row["complexity"] in {"simple", "complex"}
        assert row["language"] in {"en", "roman_urdu"}
        assert outbound_pii(row["question"]) is None
    assert {row["provenance"] for row in human} == {"human"}
    assert {row["provenance"] for row in train} == {"synthetic"}


def test_exported_onnx_labels_a_held_out_question():
    path = Path(__file__).resolve().parents[2] / "models" / "classifier.onnx"
    if not path.is_file():
        return
    prediction = OnnxClassifier(path).predict(
        "An audit notice and a recovery notice arrived the same week. Which deadline comes first?"
    )
    assert prediction.category == "audit_notice"
    assert prediction.complexity == "complex"
    assert prediction.low_confidence is False


def test_keyword_classifier_and_domain_boost():
    model = KeywordClassifier()
    audit = model.predict("Audit notice aya hai, appeal karni hai")
    assert audit.category == "audit_notice"
    assert audit.complexity == "complex"
    assert retrieval_domain(audit) == "audit_notice"
    unsure = model.predict("hello there")
    assert unsure.low_confidence is True
    assert retrieval_domain(unsure) is None
    fused = fuse_hits(
        [[hit("tax", domain="income_tax"), hit("customs", domain="customs")]],
        domain="customs",
        domain_boost=1.2,
    )
    assert fused[0][0].chunk_id == "customs"


def test_low_confidence_asks_for_a_category_before_skipping_listings():
    class Unsure:
        def predict(self, text: str) -> Prediction:
            return Prediction(
                category="audit_notice",
                complexity="simple",
                confidence=0.4,
                low_confidence=True,
            )

    found = find_experts(
        "Audit notice aya hai, appeal karni hai",
        city="Karachi",
        category=None,
        classifier=Unsure(),
    )
    assert found["experts"] == []
    assert found["advice_code"] == "uncertain_category"
    assert "Pick one" in found["advice"]
    assert found["advice_ru"] != found["advice"]


def test_city_filter_and_simple_questions_skip_listings():
    found = find_experts(
        "Audit notice aya hai, appeal karni hai",
        city="karachi",
        category=None,
    )
    assert found["classification"]["category"] == "audit_notice"
    assert found["experts"]
    assert {row["city"] for row in found["experts"]} == {"Karachi"}
    assert found["disclaimer"]
    assert found["removal_contact"]
    simple = find_experts(
        "What salary tax applies to Rs 1200000 in TY2027?",
        city=None,
        category=None,
    )
    assert simple["experts"] == []
    assert simple["advice_code"] == "simple_question"
    assert "chat" in simple["advice"]
    assert simple["advice_ru"]
    none = find_experts(
        "Audit notice aya hai, appeal karni hai",
        city="Quetta",
        category="audit_notice",
    )
    assert none["experts"] == []
    assert none["advice_code"] == "no_listing"
    assert none["advice_ru"]


class Scripted:
    async def complete(self, role, messages, **kwargs):
        return LLMResult(
            text=json.dumps(router_payload(intent="find_expert", search_query="")),
            model="scripted",
            fallback=False,
            latency_ms=0,
        )


def test_find_endpoint_and_chat_card():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory", classifier="keyword"))
    client = TestClient(create_app(Container(settings=settings, llm=FakeLLM())))
    response = client.post(
        "/api/v1/experts/find",
        json={"query": "Audit notice aya hai, appeal karni hai", "city": "Lahore"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["experts"]
    assert body["advice_code"] == "ok"
    assert body["advice_ru"]
    assert all(row["city"] == "Lahore" for row in body["experts"])
    denied = client.post(
        "/internal/experts/upsert",
        json={
            "id": "b1c1a1d0-0001-4000-8000-0000000000e1",
            "name": "Example Firm",
            "city": "Karachi",
            "specialties": ["income_tax"],
            "profile_url": "https://example.com/firm",
            "source": "example",
            "last_updated": "2026-10-14",
        },
    )
    assert denied.status_code == 401

    chat = make_client(Scripted()).post(
        "/api/v1/chat",
        json={"message": "Audit notice aya hai in Karachi, appeal karni hai"},
    )
    events = parse_sse(chat.text)
    card = events[1][1]["card"]
    assert card["type"] == "experts"
    assert card["data"]["classification"]["category"] == "audit_notice"
