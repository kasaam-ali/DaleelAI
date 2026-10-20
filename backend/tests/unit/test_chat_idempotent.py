"""N10: resending a queued question with the same client_request_id saves it once."""

import json
import uuid

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.container import Container
from app.main import create_app
from app.settings import Adapters, Settings


class TurnStore:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    def chat_owner(self, chat_id: str) -> str | None:
        return next((t["session_id"] for t in self.saved if t["chat_id"] == chat_id), None)

    def save_turn(self, **turn) -> None:
        if any(t["message_id"] == turn["message_id"] for t in self.saved):
            return
        self.saved.append(turn)

    def find_turn(self, session_id: str, message_id: str) -> dict | None:
        for turn in self.saved:
            if turn["session_id"] == session_id and turn["message_id"] == message_id:
                return {
                    "chat_id": turn["chat_id"],
                    "message": {
                        "id": message_id,
                        "role": "assistant",
                        "content": turn["assistant_text"],
                        "intent": turn["intent"],
                        "language": turn["language"],
                        "tax_year": turn["tax_year"],
                        "sources": turn["sources"],
                        "answer_source": turn["answer_source"],
                        "confidence": turn["confidence"],
                        "verified": turn["verified"],
                        "model": turn["model"],
                    },
                }
        return None


def _events(text: str) -> list[dict]:
    out = []
    for block in text.split("\n\n"):
        lines = dict(line.split(":", 1) for line in block.splitlines() if ":" in line)
        if "event" in lines:
            out.append({"event": lines["event"].strip(), "data": json.loads(lines["data"])})
    return out


def test_same_client_request_id_is_saved_once_and_replayed():
    store = TurnStore()
    container = Container(
        settings=Settings(adapters=Adapters(llm="fake")), llm=FakeLLM(), feedback=store
    )
    client = TestClient(create_app(container))
    session = str(uuid.uuid4())
    body = {"chat_id": None, "message": "How is salary taxed?", "client_request_id": "q-1"}
    headers = {"X-Session-Id": session}

    first = _events(client.post("/api/v1/chat", json=body, headers=headers).text)
    second = _events(client.post("/api/v1/chat", json=body, headers=headers).text)

    assert len(store.saved) == 1
    meta1 = next(e for e in first if e["event"] == "meta")["data"]
    meta2 = next(e for e in second if e["event"] == "meta")["data"]
    assert meta1["chat_id"] == meta2["chat_id"] == store.saved[0]["chat_id"]
    assert meta1["message_id"] == meta2["message_id"]
    final1 = next(e for e in first if e["event"] == "final")["data"]
    final2 = next(e for e in second if e["event"] == "final")["data"]
    assert final2["answer"] == final1["answer"]
    assert second[-1]["event"] == "done"


def test_other_session_with_same_client_id_is_not_deduped():
    store = TurnStore()
    container = Container(
        settings=Settings(adapters=Adapters(llm="fake")), llm=FakeLLM(), feedback=store
    )
    client = TestClient(create_app(container))
    body = {"chat_id": None, "message": "How is salary taxed?", "client_request_id": "q-1"}
    for _ in range(2):
        client.post("/api/v1/chat", json=body, headers={"X-Session-Id": str(uuid.uuid4())})
    assert len(store.saved) == 2
