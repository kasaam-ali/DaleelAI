"""In-memory chats, feedback, and checklists for one process."""

import uuid
from typing import Any


class MemorySessionStore:
    """Same session methods as PostgresStore, with nothing left after delete_session."""

    def __init__(self) -> None:
        self.chats: dict[str, dict[str, Any]] = {}
        self.feedback: list[dict[str, Any]] = []
        self.checklists: dict[str, dict[str, Any]] = {}

    def chat_owner(self, chat_id: str) -> str | None:
        row = self.chats.get(chat_id)
        return None if row is None else row["session_id"]

    def list_chats(self, session_id: str) -> list[dict[str, Any]]:
        rows = [
            self._summary(row) for row in self.chats.values() if row["session_id"] == session_id
        ]
        rows.sort(key=lambda item: item["updated_at"], reverse=True)
        return rows[:50]

    def get_chat(self, session_id: str, chat_id: str) -> dict[str, Any] | None:
        row = self.chats.get(chat_id)
        if row is None or row["session_id"] != session_id:
            return None
        detail = self._summary(row)
        detail["messages"] = [dict(message) for message in row["messages"]]
        return detail

    def find_turn(self, session_id: str, message_id: str) -> dict[str, Any] | None:
        for row in self.chats.values():
            if row["session_id"] != session_id:
                continue
            for message in row["messages"]:
                if message["id"] == message_id and message["role"] == "assistant":
                    return {"chat_id": row["id"], "message": dict(message)}
        return None

    def delete_chat(self, session_id: str, chat_id: str) -> bool:
        row = self.chats.get(chat_id)
        if row is None or row["session_id"] != session_id:
            return False
        self._drop_chat(chat_id)
        return True

    def rename_chat(self, session_id: str, chat_id: str, title: str) -> dict[str, Any] | None:
        row = self.chats.get(chat_id)
        if row is None or row["session_id"] != session_id:
            return None
        row["title"] = title
        return self._summary(row)

    def add_chat(self, session_id: str, title: str, chat_id: str | None = None) -> str:
        chat_id = chat_id or str(uuid.uuid4())
        self.chats[chat_id] = {
            "id": chat_id,
            "session_id": session_id,
            "title": title,
            "created_at": "2026-10-14T00:00:00+00:00",
            "updated_at": "2026-10-14T00:01:00+00:00",
            "messages": [],
        }
        return chat_id

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        message_id: str | None = None,
    ) -> str:
        message_id = message_id or str(uuid.uuid4())
        self.chats[chat_id]["messages"].append(
            {
                "id": message_id,
                "role": role,
                "content": content,
                "intent": None,
                "language": None,
                "tax_year": None,
                "sources": [],
                "answer_source": None,
                "confidence": None,
                "verified": None,
                "model": None,
                "created_at": "2026-10-14T00:01:00+00:00",
                "feedback": None,
                "feedback_reason": None,
            }
        )
        return message_id

    def save_feedback(
        self,
        *,
        session_id: str,
        message_id: str,
        rating: str,
        reason: str | None = None,
        comment: str | None = None,
        share_conversation: bool = False,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        self.feedback.append(
            {
                "id": feedback_id,
                "session_id": session_id,
                "message_id": message_id,
                "rating": rating,
                "reason": reason,
                "comment": comment,
                "share_conversation": share_conversation,
            }
        )
        return feedback_id

    def save_checklist(
        self,
        *,
        session_id: str,
        template_id: str,
        answers: dict[str, Any],
        steps: list[dict[str, Any]],
        language: str = "en",
    ) -> str:
        checklist_id = str(uuid.uuid4())
        self.checklists[checklist_id] = {
            "session_id": session_id,
            "template_id": template_id,
            "answers": answers,
            "steps": steps,
            "language": language,
        }
        return checklist_id

    def update_checklist_step(
        self,
        *,
        session_id: str,
        checklist_id: str,
        step_id: str,
        done: bool,
    ) -> dict[str, Any] | None:
        row = self.checklists.get(checklist_id)
        if row is None or row["session_id"] != session_id:
            return None
        found = False
        for step in row["steps"]:
            if step["id"] == step_id:
                step["done"] = done
                found = True
        if not found:
            return None
        return {
            "id": checklist_id,
            "template_id": row["template_id"],
            "answers": row["answers"],
            "steps": row["steps"],
            "language": row.get("language") or "en",
        }

    def list_checklists(self, *, session_id: str) -> list[dict[str, Any]]:
        rows = [
            self._checklist_row(checklist_id, row)
            for checklist_id, row in self.checklists.items()
            if row["session_id"] == session_id
        ]
        rows.reverse()
        return rows

    def get_checklist(self, *, session_id: str, checklist_id: str) -> dict[str, Any] | None:
        row = self.checklists.get(checklist_id)
        if row is None or row["session_id"] != session_id:
            return None
        return self._checklist_row(checklist_id, row)

    def _checklist_row(self, checklist_id: str, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": checklist_id,
            "template_id": row["template_id"],
            "answers": row["answers"],
            "steps": row["steps"],
            "language": row.get("language") or "en",
        }

    def delete_session(self, session_id: str) -> None:
        message_ids: set[str] = set()
        for chat_id, row in list(self.chats.items()):
            if row["session_id"] != session_id:
                continue
            message_ids.update(message["id"] for message in row["messages"])
            del self.chats[chat_id]
        self.feedback = [
            row
            for row in self.feedback
            if row.get("session_id") != session_id and row.get("message_id") not in message_ids
        ]
        self.checklists = {
            checklist_id: row
            for checklist_id, row in self.checklists.items()
            if row["session_id"] != session_id
        }

    def _drop_chat(self, chat_id: str) -> None:
        row = self.chats.pop(chat_id)
        message_ids = {message["id"] for message in row["messages"]}
        self.feedback = [
            item for item in self.feedback if item.get("message_id") not in message_ids
        ]

    def _summary(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
