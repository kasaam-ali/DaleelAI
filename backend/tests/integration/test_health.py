"""Checks that /health returns the app version and the stored corpus hash."""

from fastapi.testclient import TestClient

from app.container import build_container
from app.main import create_app
from app.settings import Adapters, Settings
from app.version import APP_VERSION, INDEXED_CORPUS_VERSION


def make_client() -> TestClient:
    settings = Settings(cors_origins=["http://localhost:5173"], adapters=Adapters(llm="fake"))
    return TestClient(create_app(build_container(settings)))


def test_health_reports_ok_and_version():
    response = make_client().get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == APP_VERSION
    assert body["env"] == "development"
    assert body["corpus_version"] == INDEXED_CORPUS_VERSION
    assert body["supported_tax_years"] == ["TY2026", "TY2027"]
    assert "dense" in body["models"]


def test_cors_allows_local_frontend():
    response = make_client().get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
