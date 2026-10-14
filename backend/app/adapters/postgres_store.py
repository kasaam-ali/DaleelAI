"""Postgres writes for chat turns, feedback, and schema setup. Reads stay in other adapters."""

import json
import uuid
from typing import Any

from app.adapters.postgres_schema import SCHEMA
from app.core.privacy.pii import redact_pii


class PostgresStore:
    def __init__(self, database_url: str, connect=None) -> None:
        self.database_url = database_url
        self._connect = connect
        self._ready = False

    def ensure(self) -> None:
        if self._ready:
            return
        with self._open() as conn:
            with conn.cursor() as cur:
                for statement in SCHEMA:
                    cur.execute(statement)
            conn.commit()
        self._ready = True

    def save_turn(
        self,
        *,
        session_id: str,
        chat_id: str,
        message_id: str,
        user_text: str,
        assistant_text: str,
        intent: str,
        language: str,
        tax_year: str,
        answer_source: str,
        confidence: str,
        verified: bool,
        model: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        self.ensure()
        user_text = redact_pii(user_text)
        sources_json = json.dumps(sources or [])
        with self._open() as conn:
            with conn.cursor() as cur:
                self._ensure_session(cur, session_id)
                self._ensure_chat(cur, chat_id, session_id)
                cur.execute(
                    """
                    INSERT INTO messages (id, chat_id, role, content, intent, language, tax_year)
                    VALUES (%s, %s, 'user', %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        uuid.uuid4(),
                        _uuid(chat_id),
                        user_text,
                        intent,
                        language,
                        tax_year,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO messages (
                      id, chat_id, role, content, intent, language, tax_year,
                      sources, answer_source, confidence, verified, model
                    )
                    VALUES (%s, %s, 'assistant', %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        _uuid(message_id),
                        _uuid(chat_id),
                        assistant_text,
                        intent,
                        language,
                        tax_year,
                        sources_json,
                        answer_source,
                        confidence,
                        verified,
                        model,
                    ),
                )
            conn.commit()

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
        self.ensure()
        feedback_id = uuid.uuid4()
        clean_comment = redact_pii(comment) if comment else None
        with self._open() as conn:
            with conn.cursor() as cur:
                self._ensure_message(cur, session_id, message_id)
                cur.execute(
                    """
                    INSERT INTO feedback (
                      id, message_id, rating, reason, comment, share_conversation
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        feedback_id,
                        _uuid(message_id),
                        rating,
                        reason,
                        clean_comment,
                        share_conversation,
                    ),
                )
            conn.commit()
        return str(feedback_id)

    def find_sections(self, section: str) -> list[dict[str, Any]]:
        self.ensure()
        root = section.split("(", 1)[0]
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT section, COALESCE(section_title, ''), left(text, 400)
                    FROM sections
                    WHERE section = %s OR section = %s
                    LIMIT 3
                    """,
                    (section, root),
                )
                rows = cur.fetchall()
        return [{"section": row[0] or section, "title": row[1], "text": row[2]} for row in rows]

    def save_checklist(
        self,
        *,
        session_id: str,
        template_id: str,
        answers: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> str:
        self.ensure()
        checklist_id = uuid.uuid4()
        with self._open() as conn:
            with conn.cursor() as cur:
                self._ensure_session(cur, session_id)
                cur.execute(
                    """
                    INSERT INTO checklists (id, session_id, template_id, answers, steps)
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    (
                        checklist_id,
                        _uuid(session_id),
                        template_id,
                        json.dumps(answers),
                        json.dumps(steps),
                    ),
                )
            conn.commit()
        return str(checklist_id)

    def update_checklist_step(
        self,
        *,
        session_id: str,
        checklist_id: str,
        step_id: str,
        done: bool,
    ) -> dict[str, Any] | None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT template_id, answers, steps
                    FROM checklists
                    WHERE id = %s AND session_id = %s
                    """,
                    (_uuid(checklist_id), _uuid(session_id)),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                steps = row[2]
                if isinstance(steps, str):
                    steps = json.loads(steps)
                answers = row[1]
                if isinstance(answers, str):
                    answers = json.loads(answers)
                found = False
                for step in steps:
                    if step.get("id") == step_id:
                        step["done"] = done
                        found = True
                if not found:
                    return None
                cur.execute(
                    """
                    UPDATE checklists
                    SET steps = %s::jsonb, updated_at = now()
                    WHERE id = %s
                    """,
                    (json.dumps(steps), _uuid(checklist_id)),
                )
            conn.commit()
        return {
            "id": checklist_id,
            "template_id": row[0],
            "answers": answers,
            "steps": steps,
        }

    def list_experts(self) -> list[dict[str, Any]]:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, firm, city, specialties, profile_url, source, last_updated
                    FROM experts
                    WHERE active
                    ORDER BY name, city
                    """
                )
                rows = cur.fetchall()
        return [_expert_row(row) for row in rows]

    def upsert_expert(self, row: dict[str, Any]) -> None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO experts (
                      id, name, firm, city, specialties, profile_url, source, last_updated, active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (source, profile_url) DO UPDATE SET
                      name = EXCLUDED.name,
                      firm = EXCLUDED.firm,
                      city = EXCLUDED.city,
                      specialties = EXCLUDED.specialties,
                      last_updated = EXCLUDED.last_updated,
                      active = true
                    """,
                    (
                        _uuid(str(row["id"])),
                        row["name"],
                        row.get("firm"),
                        row["city"],
                        list(row["specialties"]),
                        row["profile_url"],
                        row["source"],
                        row["last_updated"],
                    ),
                )
            conn.commit()

    def _ensure_message(self, cur, session_id: str, message_id: str) -> None:
        cur.execute("SELECT id FROM messages WHERE id = %s", (_uuid(message_id),))
        if cur.fetchone():
            return
        chat_id = uuid.uuid5(uuid.NAMESPACE_URL, f"daleelai-chat:{message_id}")
        self._ensure_session(cur, session_id)
        self._ensure_chat(cur, str(chat_id), session_id)
        cur.execute(
            """
            INSERT INTO messages (id, chat_id, role, content)
            VALUES (%s, %s, 'assistant', '')
            ON CONFLICT (id) DO NOTHING
            """,
            (_uuid(message_id), chat_id),
        )

    def _ensure_session(self, cur, session_id: str) -> None:
        cur.execute(
            """
            INSERT INTO sessions (id) VALUES (%s)
            ON CONFLICT (id) DO UPDATE SET last_seen_at = now()
            """,
            (_uuid(session_id),),
        )

    def _ensure_chat(self, cur, chat_id: str, session_id: str) -> None:
        cur.execute(
            """
            INSERT INTO chats (id, session_id) VALUES (%s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (_uuid(chat_id), _uuid(session_id)),
        )

    def _open(self):
        if self._connect is not None:
            return self._connect()
        import psycopg

        return psycopg.connect(self.database_url, connect_timeout=5)


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _expert_row(row: tuple) -> dict[str, Any]:
    updated = row[7]
    return {
        "id": str(row[0]),
        "name": row[1],
        "firm": row[2],
        "city": row[3],
        "specialties": list(row[4] or []),
        "profile_url": row[5],
        "source": row[6],
        "last_updated": updated.isoformat() if hasattr(updated, "isoformat") else str(updated),
    }
