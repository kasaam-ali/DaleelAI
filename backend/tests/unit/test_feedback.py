"""Checks that a thumbs rating is stored for this session."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.postgres_store import PostgresStore
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings


class MemoryStore:
    def __init__(self):
        self.rows = []

    def save_feedback(self, **kwargs):
        self.rows.append(kwargs)
        return "11111111-1111-1111-1111-111111111111"


def _client(store):
    container = Container(
        settings=Settings(adapters=Adapters(llm="fake")),
        llm=object(),
        feedback=store,
    )
    return TestClient(create_app(container))


def test_feedback_stores_the_rating():
    store = MemoryStore()
    message_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    response = _client(store).post(
        "/api/v1/feedback",
        headers={"X-Session-Id": session_id},
        json={"message_id": message_id, "rating": "down", "reason": "wrong", "comment": None},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "11111111-1111-1111-1111-111111111111"
    assert store.rows[0]["message_id"] == message_id
    assert store.rows[0]["rating"] == "down"
    assert store.rows[0]["session_id"] == session_id


def test_feedback_requires_a_session():
    response = _client(MemoryStore()).post(
        "/api/v1/feedback",
        json={"message_id": str(uuid.uuid4()), "rating": "up"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_postgres_feedback_inserts_a_row():
    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))

        def fetchone(self):
            return ("exists",)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self):
            self.cursor_obj = Cursor()
            self.committed = False

        def cursor(self):
            return self.cursor_obj

        def commit(self):
            self.committed = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    conn = Conn()
    store = PostgresStore("postgresql://example", connect=lambda: conn)
    store._ready = True
    saved = store.save_feedback(
        session_id=str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
        rating="up",
        reason=None,
        comment="CNIC 12345-1234567-1",
        share_conversation=False,
    )

    sql = " ".join(call[0] for call in conn.cursor_obj.calls)
    assert "INSERT INTO feedback" in sql
    assert conn.committed is True
    assert uuid.UUID(saved)
    comment = conn.cursor_obj.calls[-1][1][4]
    assert comment == "CNIC [CNIC]"
    assert "12345-1234567-1" not in comment
