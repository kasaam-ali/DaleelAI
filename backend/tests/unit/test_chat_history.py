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

    def delete_chat(self, session_id: str, chat_id: str) -> bool:
        if self.owner.get(chat_id) != session_id:
            return False
        self.owner.pop(chat_id, None)
        self.rows.pop(chat_id, None)
        return True

    def rename_chat(self, session_id: str, chat_id: str, title: str) -> dict | None:
        if self.owner.get(chat_id) != session_id:
            return None
        self.rows[chat_id]["title"] = title
        return self.rows[chat_id]


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


def test_delete_removes_only_the_owners_chat():
    store = MemoryChats()
    session_id = str(uuid.uuid4())
    other = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    foreign = str(uuid.uuid4())
    store.owner[chat_id] = session_id
    store.owner[foreign] = other
    store.rows[chat_id] = _summary(chat_id)
    store.rows[foreign] = _summary(foreign)
    client = client_for(store)

    missing = client.delete(f"/api/v1/chats/{chat_id}")
    denied = client.delete(
        f"/api/v1/chats/{foreign}",
        headers={"X-Session-Id": session_id},
    )
    gone = client.delete(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
    )
    again = client.delete(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
    )
    listed = client.get("/api/v1/chats", headers={"X-Session-Id": session_id})

    assert missing.status_code == 400
    assert denied.status_code == 404
    assert gone.status_code == 204
    assert again.status_code == 404
    assert listed.json()["chats"] == []
    assert foreign in store.rows


def test_rename_keeps_the_chat_in_this_session():
    store = MemoryChats()
    session_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    store.owner[chat_id] = session_id
    store.rows[chat_id] = _summary(chat_id)
    client = client_for(store)

    renamed = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
        json={"title": "  Salary   question  "},
    )
    listed = client.get("/api/v1/chats", headers={"X-Session-Id": session_id})
    blank = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
        json={"title": "   "},
    )
    hidden = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": str(uuid.uuid4())},
        json={"title": "Stolen"},
    )

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Salary question"
    assert listed.json()["chats"][0]["title"] == "Salary question"
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "invalid_request"
    assert "detail" not in blank.json()
    missing = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
        json={},
    )
    too_long = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
        json={"title": "x" * 81},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "invalid_request"
    assert "detail" not in missing.json()
    assert too_long.status_code == 422
    assert too_long.json()["error"] == {
        "code": "invalid_request",
        "message": "A title can be at most 80 characters.",
    }
    assert hidden.status_code == 404
    assert store.rows[chat_id]["title"] == "Salary question"


def test_rename_masks_a_cnic_in_the_title():
    store = MemoryChats()
    session_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    store.owner[chat_id] = session_id
    store.rows[chat_id] = _summary(chat_id)
    client = client_for(store)

    renamed = client.patch(
        f"/api/v1/chats/{chat_id}",
        headers={"X-Session-Id": session_id},
        json={"title": "Notice for 35202-1234567-1"},
    )
    listed = client.get("/api/v1/chats", headers={"X-Session-Id": session_id})

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Notice for [CNIC]"
    assert "35202-1234567-1" not in renamed.text
    assert listed.json()["chats"][0]["title"] == "Notice for [CNIC]"
    assert store.rows[chat_id]["title"] == "Notice for [CNIC]"


def test_postgres_delete_and_rename_are_scoped_to_the_session():
    class Cursor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple | None]] = []
            self.rowcount = 0
            self._row = None

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            if "DELETE" in sql:
                self.rowcount = 0
                self._row = None
            elif "UPDATE" in sql:
                self.rowcount = 0
                self._row = None

        def fetchone(self):
            return self._row

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
    store._ready = True
    session_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    assert store.delete_chat(session_id, chat_id) is False
    assert store.rename_chat(session_id, chat_id, "Salary") is None
    delete_sql, delete_params = conn.cursor_obj.calls[0]
    rename_sql, rename_params = conn.cursor_obj.calls[1]
    assert "DELETE FROM chats" in delete_sql
    assert "session_id" in delete_sql
    assert delete_params[1] == uuid.UUID(session_id)
    assert "UPDATE chats" in rename_sql
    assert "session_id" in rename_sql
    assert rename_params[0] == "Salary"
    assert rename_params[2] == uuid.UUID(session_id)


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
