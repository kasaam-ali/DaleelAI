"""Calculator and filer comparison over HTTP."""

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings
from tests.integration.test_chat import ScriptedLLM, make_client, parse_sse, router_payload


def client() -> TestClient:
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))
    return TestClient(create_app(Container(settings=settings, llm=FakeLLM())))


def test_salary_endpoint_uses_the_monthly_figure():
    response = client().post(
        "/api/v1/calculator/salary",
        json={"monthly_income": 100_000, "tax_year": "TY2027"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inputs"]["annual_income"] == 1_200_000
    assert body["total_tax"] == 6_000
    assert body["rules_version"] == "ty2027@2026-07-01"


def test_unknown_filer_type_is_400():
    response = client().post(
        "/api/v1/compare/filer",
        json={"tax_year": "TY2026", "transactions": [{"type": "gift", "amount": 10}]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_transaction_type"


def test_late_filer_property_is_rejected_for_ty2027():
    response = client().post(
        "/api/v1/calculator/property",
        json={
            "tax_year": "TY2027",
            "side": "sale",
            "value": 1_000_000,
            "filer_status": "late_filer",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_chat_calculate_returns_a_card_instead_of_not_ready():
    llm = ScriptedLLM(router_payload(intent="calculate", search_query=""))
    response = make_client(llm).post(
        "/api/v1/chat",
        json={"message": "Salary tax on 1200000", "tax_year": "TY2027"},
    )
    events = parse_sse(response.text)
    names = [name for name, _data in events]
    assert names == ["meta", "tool_result", "token", "final", "done"]
    card = events[1][1]["card"]
    assert card["type"] == "calculation"
    assert card["data"]["total_tax"] == 6_000
    assert "not available" not in events[2][1]["text"].lower()
