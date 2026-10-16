from fastapi.testclient import TestClient

from app.adapters.postgres_sections import PostgresSections
from app.adapters.qdrant_search import coerce_scores, hit_from_payload
from app.container import build_container
from app.main import create_app
from app.settings import Adapters, Settings


def test_qdrant_runner_does_not_connect_until_a_question():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="qdrant"))

    container = build_container(settings)

    assert container.qa is not None
    assert container.qa.search._client is None
    assert container.qa.rerank._model is None


def test_warm_loads_search_and_rerank_together():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="qdrant"))
    qa = build_container(settings).qa
    called: list[str] = []
    qa.search.warm = lambda: called.append("search")
    qa.rerank.warm = lambda: called.append("rerank")

    qa.warm()

    assert set(called) == {"search", "rerank"}


def test_fake_llm_app_does_not_warm_models():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="qdrant"))
    container = build_container(settings)

    def fail():
        raise AssertionError("warmed")

    container.qa.warm = fail
    with TestClient(create_app(container)):
        pass


def test_memory_adapter_keeps_the_fake_qa_runner_empty():
    settings = Settings(adapters=Adapters(llm="fake", vector_store="memory"))

    assert build_container(settings).qa is None


def test_payload_and_scores_are_normalized():
    hit = hit_from_payload({"chunk_id": "s149", "text": "salary", "domain": "income_tax"})

    assert hit.chunk_id == "s149"
    assert hit.domain == "income_tax"

    class Scored:
        score = 0.4

    assert coerce_scores([0.2, Scored(), (1, 0.5)]) == [0.2, 0.4, 0.5]


def test_postgres_lookup_uses_the_injected_connection():
    class Cursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return [("s149", "parent section")]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self):
            self.cursor_obj = Cursor()

        def cursor(self):
            return self.cursor_obj

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    found = PostgresSections("postgresql://example", connect=lambda: conn)(["s149"])

    assert found == {"s149": "parent section"}
    assert "sections" in conn.cursor_obj.sql
    assert conn.cursor_obj.params == (["s149"],)


def test_postgres_errors_return_no_rows():
    def boom():
        raise RuntimeError("no table")

    assert PostgresSections("postgresql://example", connect=boom)(["s149"]) == {}
    assert PostgresSections("")(["s149"]) == {}
