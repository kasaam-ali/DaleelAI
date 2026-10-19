"""In-memory chat feedback for a local run that has no Postgres URL."""

import uuid
from typing import Any


class MemorySessionStore:
    def __init__(self) -> None:
        self.feedback: list[dict[str, Any]] = []
        self.turns: list[dict[str, Any]] = []

    def save_feedback(
        self,
        *,
        session_id: str,
        message_id: str,
        rating: str,
        reason: str | None,
        comment: str | None,
        share_conversation: bool,
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

    def save_turn(self, **kwargs: Any) -> None:
        self.turns.append(kwargs)
