"""Session-scoped chat history. A foreign chat id is a 404, not a 403."""

import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.adapters.postgres_store import ChatAccessDenied, PostgresStore
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings


class MemoryChats:
    def __init__(self) -> None:
        self.owner: dict[str, str] = {}
        self.rows: dict[str, dict] = {}

    def chat_owner(self, chat_id: str) -> str | None:
        return self.owner.get(chat_id)

    def list_chats(self, session_id: str) -> list[dict]:
        return [self.rows[chat_id] for chat_id, owner in self.owner.items() if owner == session_id]

    def get_chat(self, session_id: str, chat_id: str) -> dict | None:
        if self.owner.get(chat_id) != session_id:
            return None
        detail = dict(self.rows[chat_id])
        detail["messages"] = []
        return detail


def client_for(store: MemoryChats) -> TestClient:
    settings = Settings(adapters=Adapters(llm="fake"))
    container = Container(settings=settings, llm=FakeLLM(), feedback=store)
    return TestClient(create_app(container))


def _summary(chat_id: str) -> dict:
    return {
        "id": chat_id,
        "title": "How is salary taxed?",
        "created_at": "2026-10-14T00:00:00+00:00",
        "updated_at": "2026-10-14T00:01:00+00:00",
    }


def test_list_is_empty_for_a_new_session():
    response = client_for(MemoryChats()).get(
        "/api/v1/chats",
        headers={"X-Session-Id": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    assert response.json() == {"chats": []}


def test_list_returns_only_this_session():
    store = MemoryChats()
    mine = str(uuid.uuid4())
    theirs = str(uuid.uuid4())
    own_chat = str(uuid.uuid4())
    other_chat = str(uuid.uuid4())
    store.owner[own_chat] = mine
    store.owner[other_chat] = theirs
    store.rows[own_chat] = _summary(own_chat)
    store.rows[other_chat] = _summary(other_chat)

    response = client_for(store).get("/api/v1/chats", headers={"X-Session-Id": mine})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["chats"]] == [own_chat]


def test_get_chat_returns_messages_for_the_owner():
    store = MemoryChats()
    session_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    store.owner[chat_id] = session_id
    store.rows[chat_id] = _summary(chat_id)

    response = client_for(store).get(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
    )

    assert response.status_code == 200
    assert response.json()["id"] == chat_id
    assert response.json()["messages"] == []


def test_get_chat_hides_another_session():
    store = MemoryChats()
    chat_id = str(uuid.uuid4())
    store.owner[chat_id] = str(uuid.uuid4())
    store.rows[chat_id] = _summary(chat_id)

    response = client_for(store).get(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_history_rejects_a_missing_or_malformed_session():
    store = MemoryChats()
    client = client_for(store)
    missing = client.get("/api/v1/chats")
    malformed = client.get("/api/v1/chats", headers={"X-Session-Id": "short"})
    assert missing.status_code == 400
    assert malformed.status_code == 400
    assert missing.json()["error"]["code"] == "invalid_request"


def test_continue_rejects_a_foreign_chat():
    store = MemoryChats()
    chat_id = str(uuid.uuid4())
    store.owner[chat_id] = str(uuid.uuid4())
    denied = client_for(store).post(
        "/api/v1/chat",
        headers={"X-Session-Id": str(uuid.uuid4())},
        json={"chat_id": chat_id, "message": "What is section 149?"},
    )
    assert denied.status_code == 404


def test_continue_requires_a_uuid_session_when_chat_id_is_sent():
    response = client_for(MemoryChats()).post(
        "/api/v1/chat",
        json={"chat_id": str(uuid.uuid4()), "message": "What is section 149?"},
    )
    assert response.status_code == 400


def test_save_turn_refuses_another_sessions_chat():
    class Cursor:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, sql, params=None):
            self.calls.append(sql)

        def fetchone(self):
            return (uuid.uuid4(),)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Conn:
        def __init__(self) -> None:
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
    try:
        store.save_turn(
            session_id=str(uuid.uuid4()),
            chat_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            user_text="question",
            assistant_text="answer",
            intent="qa",
            language="en",
            tax_year="TY2026",
            answer_source="verified",
            confidence="high",
            verified=True,
            model="fake",
            sources=[],
        )
    except ChatAccessDenied:
        denied = True
    else:
        denied = False
    assert denied is True
    assert conn.committed is False
