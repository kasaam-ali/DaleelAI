"""DELETE /api/v1/session removes one session and leaves the other alone."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.adapters.memory_store import MemorySessionStore
from app.adapters.postgres_store import PostgresStore
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings


def client_for(store) -> TestClient:
    settings = Settings(adapters=Adapters(llm="fake"))
    container = Container(settings=settings, llm=FakeLLM(), feedback=store)
    return TestClient(create_app(container))


def _fill(store: MemorySessionStore, session_id: str, title: str) -> str:
    chat_id = store.add_chat(session_id, title)
    message_id = store.add_message(chat_id, "assistant", "An answer.")
    store.save_feedback(session_id=session_id, message_id=message_id, rating="up")
    store.save_checklist(
        session_id=session_id,
        template_id="ntn_individual",
        answers={},
        steps=[{"id": "cnic", "done": True}],
    )
    return chat_id


def test_delete_session_removes_only_that_sessions_history():
    store = MemorySessionStore()
    mine = str(uuid.uuid4())
    theirs = str(uuid.uuid4())
    _fill(store, mine, "Salary")
    their_chat = _fill(store, theirs, "Theirs")
    client = client_for(store)

    deleted = client.delete("/api/v1/session", headers={"X-Session-Id": mine})
    assert deleted.status_code == 204
    assert deleted.content == b""

    listed = client.get("/api/v1/chats", headers={"X-Session-Id": mine})
    assert listed.status_code == 200
    assert listed.json()["chats"] == []
    assert [row["session_id"] for row in store.feedback] == [theirs]
    assert len(store.checklists) == 1
    assert next(iter(store.checklists.values()))["session_id"] == theirs

    again = client.delete("/api/v1/session", headers={"X-Session-Id": mine})
    assert again.status_code == 204

    kept = client.get("/api/v1/chats", headers={"X-Session-Id": theirs})
    assert [item["id"] for item in kept.json()["chats"]] == [their_chat]
    assert store.get_chat(theirs, their_chat)["messages"][0]["content"] == "An answer."


def test_delete_session_is_204_when_nothing_is_stored():
    response = client_for(MemorySessionStore()).delete(
        "/api/v1/session",
        headers={"X-Session-Id": str(uuid.uuid4())},
    )
    assert response.status_code == 204


def test_delete_session_rejects_a_bad_or_missing_id():
    client = client_for(MemorySessionStore())
    missing = client.delete("/api/v1/session")
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "invalid_request"
    bad = client.delete("/api/v1/session", headers={"X-Session-Id": "not-a-uuid"})
    assert bad.status_code == 400
    assert bad.json()["error"]["message"] == "X-Session-Id must be a UUID."


def test_delete_session_is_503_without_storage():
    settings = Settings(adapters=Adapters(llm="fake"))
    container = Container(settings=settings, llm=FakeLLM(), feedback=None)
    response = TestClient(create_app(container)).delete(
        "/api/v1/session",
        headers={"X-Session-Id": str(uuid.uuid4())},
    )
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "repository_unavailable",
        "message": "Session storage is not configured.",
    }


def test_ensure_locks_the_schema_and_runs_once():
    class Cursor:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, sql, params=None):
            self.calls.append(sql)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self) -> None:
            self.cursor_obj = Cursor()

        def cursor(self):
            return self.cursor_obj

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    store = PostgresStore("postgresql://example", connect=lambda: conn)
    store.ensure()
    store.ensure()
    locks = [sql for sql in conn.cursor_obj.calls if "pg_advisory_lock" in sql]
    assert locks == ["SELECT pg_advisory_lock(%s)"]
    assert any("CREATE TABLE IF NOT EXISTS sessions" in sql for sql in conn.cursor_obj.calls)


def test_postgres_delete_session_is_one_transaction_scoped_to_the_session():
    class Cursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple | None]] = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self) -> None:
            self.cursor_obj = Cursor()
            self.commits = 0

        def cursor(self):
            return self.cursor_obj

        def commit(self):
            self.commits += 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    store = PostgresStore("postgresql://example", connect=lambda: conn)
    store._ready = True
    session_id = str(uuid.uuid4())
    store.delete_session(session_id)

    sqls = [sql for sql, _params in conn.cursor_obj.calls]
    assert conn.commits == 1
    assert any("DELETE FROM feedback" in sql and "session_id" in sql for sql in sqls)
    assert any("DELETE FROM messages" in sql and "session_id" in sql for sql in sqls)
    assert any(sql.startswith("DELETE FROM chats") and "session_id" in sql for sql in sqls)
    assert any(sql.startswith("DELETE FROM checklists") and "session_id" in sql for sql in sqls)
    assert {params[0] for _sql, params in conn.cursor_obj.calls} == {uuid.UUID(session_id)}


def test_postgres_delete_session_does_not_commit_when_a_delete_fails():
    class Cursor:
        def execute(self, sql, params=None):
            if "DELETE FROM checklists" in sql:
                raise RuntimeError("disk")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self) -> None:
            self.commits = 0

        def cursor(self):
            return Cursor()

        def commit(self):
            self.commits += 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    store = PostgresStore("postgresql://example", connect=lambda: conn)
    store._ready = True
    try:
        store.delete_session(str(uuid.uuid4()))
    except RuntimeError:
        failed = True
    else:
        failed = False
    assert failed is True
    assert conn.commits == 0
