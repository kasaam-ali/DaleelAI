from fastapi.testclient import TestClient

from app.container import build_container
from app.main import create_app
from app.settings import Adapters, Settings
from app.version import APP_VERSION


def make_client() -> TestClient:
    settings = Settings(cors_origins=["http://localhost:5173"], adapters=Adapters(llm="fake"))
    return TestClient(create_app(build_container(settings)))


def test_health_reports_ok_and_version():
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": APP_VERSION, "env": "development"}


def test_cors_allows_local_frontend():
    response = make_client().get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
