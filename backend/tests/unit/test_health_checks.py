"""Dependency checks run together and each one gives up inside its budget."""

import time

from fastapi.testclient import TestClient

from app.api import health as health_module
from app.api.health import overall_status
from app.api.health_checks import CHECK_NAMES, check_embeddings, check_llm, collect_checks
from app.container import build_container
from app.main import create_app
from app.settings import Adapters, Settings
from app.version import CORPUS_DATE


def _settings(**adapters) -> Settings:
    return Settings(
        adapters=Adapters(llm="fake", embedder="fake", vector_store="memory", **adapters)
    )


async def test_checks_run_in_parallel_inside_the_budget():
    def slow() -> str:
        time.sleep(0.2)
        return "ok"

    probes = {name: slow for name in CHECK_NAMES}
    started = time.perf_counter()
    result = await collect_checks(_settings(), probes=probes, timeout_s=1.0, slow_ms=800)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.6
    assert set(result) == set(CHECK_NAMES)
    assert all(item["status"] == "ok" for item in result.values())
    assert all(item["latency_ms"] >= 150 for item in result.values())


async def test_a_check_that_exceeds_its_budget_is_down():
    def stuck() -> str:
        time.sleep(1.0)
        return "ok"

    probes = {name: (stuck if name == "qdrant" else lambda: "ok") for name in CHECK_NAMES}
    started = time.perf_counter()
    result = await collect_checks(_settings(), probes=probes, timeout_s=0.05, slow_ms=800)
    assert time.perf_counter() - started < 0.4
    assert result["qdrant"]["status"] == "down"
    assert result["api"]["status"] == "ok"
    assert result["llm"]["status"] == "ok"


def test_unconfigured_dependencies_are_down_without_a_network_call(monkeypatch):
    for name in (
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_2",
        "OPENROUTER_API_KEY",
        "ZAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        adapters=Adapters(llm="litellm", vector_store="qdrant", embedder="fastembed"),
        database_url="",
        qdrant={"url": ""},
    )
    assert check_llm(Settings(adapters=Adapters(llm="fake"))) == "ok"
    assert check_llm(settings) == "down"


def test_embeddings_follow_the_local_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    settings = Settings(adapters=Adapters(embedder="fastembed"))
    assert check_embeddings(settings) == "down"
    (tmp_path / "model").mkdir()
    assert check_embeddings(settings) == "ok"
    assert check_embeddings(Settings(adapters=Adapters(embedder="fake"))) == "ok"


def test_postgres_down_marks_the_service_degraded():
    down = {"status": "down", "latency_ms": 1}
    ok = {"status": "ok", "latency_ms": 1}
    assert overall_status({"postgres": down, "qdrant": ok}) == "degraded"
    assert overall_status({"postgres": ok, "qdrant": down, "llm": down}) == "ok"


def test_health_reports_checks_without_waiting_on_them():
    health_module._cached.clear()
    settings = Settings(
        cors_origins=["http://localhost:5173"],
        adapters=Adapters(llm="fake", embedder="fake", vector_store="memory"),
        database_url="",
    )
    started = time.perf_counter()
    response = TestClient(create_app(build_container(settings))).get("/health")
    assert time.perf_counter() - started < 1.0
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["corpus_date"] == CORPUS_DATE
    assert set(body["checks"]) == {"api", "qdrant", "postgres", "llm", "embeddings"}
    assert body["checks"]["api"]["status"] == "ok"
    assert body["checks"]["llm"]["status"] == "ok"
    assert body["checks"]["qdrant"]["status"] == "down"
    assert body["checks"]["postgres"]["status"] == "down"
    assert body["checks"]["embeddings"]["status"] == "ok"
    assert isinstance(body["checks"]["api"]["latency_ms"], int)
