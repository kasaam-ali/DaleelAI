"""Postgres writes for chat turns, feedback, and schema setup. Reads stay in other adapters."""

import json
import threading
import uuid
from typing import Any

from app.adapters.postgres_schema import SCHEMA
from app.core.privacy.pii import redact_pii


class ChatAccessDenied(Exception):
    """The chat id belongs to a different session."""


# One lock so two workers cannot CREATE the same table at the same time.
_SCHEMA_LOCK = 726_001_307


class PostgresStore:
    def __init__(self, database_url: str, connect=None) -> None:
        self.database_url = database_url
        self._connect = connect
        self._ready = False
        self._lock = threading.Lock()

    def ensure(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            with self._open() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_lock(%s)", (_SCHEMA_LOCK,))
                    try:
                        for statement in SCHEMA:
                            cur.execute(statement)
                        conn.commit()
                    finally:
                        cur.execute("SELECT pg_advisory_unlock(%s)", (_SCHEMA_LOCK,))
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
                # A resent client_request_id maps to the same message id: save it once.
                cur.execute("SELECT 1 FROM messages WHERE id = %s", (_uuid(message_id),))
                if cur.fetchone() is not None:
                    conn.commit()
                    return
                cur.execute(
                    """
                    INSERT INTO messages (id, chat_id, role, content, intent, language, tax_year)
                    VALUES (%s, %s, 'user', %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        uuid.uuid5(uuid.NAMESPACE_URL, f"user:{message_id}"),
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

    def insert_notification(self, row: dict[str, Any]) -> bool:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications (
                      id, sha256, title, doc_type, domain, source_url, published_at,
                      effective_from, summary, who_is_affected, key_changes, indexed
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sha256) DO NOTHING
                    """,
                    (
                        _uuid(row["id"]),
                        row["sha256"],
                        row["title"],
                        row["doc_type"],
                        row.get("domain"),
                        row["source_url"],
                        row.get("published_at"),
                        row.get("effective_from"),
                        row["summary"],
                        row.get("who_is_affected"),
                        list(row.get("key_changes") or []),
                        bool(row.get("indexed")),
                    ),
                )
                inserted = cur.rowcount == 1
                if not inserted and row.get("domain"):
                    cur.execute(
                        """
                        UPDATE notifications
                        SET domain = %s
                        WHERE sha256 = %s AND domain IS NULL
                        """,
                        (row["domain"], row["sha256"]),
                    )
            conn.commit()
        return inserted

    def mark_notification_indexed(self, sha256: str) -> None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE notifications SET indexed = true WHERE sha256 = %s",
                    (sha256,),
                )
            conn.commit()

    def list_notifications(
        self, *, doc_type: str, domain: str, page: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        self.ensure()
        offset = (page - 1) * limit
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) FROM notifications
                    WHERE (%s = 'all' OR doc_type = %s)
                      AND (%s = 'all' OR domain = %s)
                    """,
                    (doc_type, doc_type, domain, domain),
                )
                total = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT id, title, doc_type, domain, source_url, published_at,
                           effective_from, summary, who_is_affected, key_changes
                    FROM notifications
                    WHERE (%s = 'all' OR doc_type = %s)
                      AND (%s = 'all' OR domain = %s)
                    ORDER BY published_at DESC NULLS LAST, title
                    LIMIT %s OFFSET %s
                    """,
                    (doc_type, doc_type, domain, domain, limit, offset),
                )
                rows = [_notification_row(row) for row in cur.fetchall()]
        return rows, total

    def get_notification(self, item_id: str) -> dict[str, Any] | None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, doc_type, domain, source_url, published_at,
                           effective_from, summary, who_is_affected, key_changes
                    FROM notifications WHERE id = %s
                    """,
                    (_uuid(item_id),),
                )
                found = cur.fetchone()
        if found is None:
            return None
        return _notification_row(found)

    def notification_sha256s(self) -> list[str]:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT sha256 FROM notifications")
                return [row[0] for row in cur.fetchall()]

    def upsert_web(self, row: dict[str, Any]) -> None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO web_pages (
                      id, url, site, title, content_type, sha256, removed
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, false)
                    ON CONFLICT (url) DO UPDATE SET
                      title = EXCLUDED.title,
                      sha256 = EXCLUDED.sha256,
                      fetched_at = now(),
                      changed_at = now(),
                      removed = false
                    """,
                    (
                        _uuid(str(uuid.uuid5(uuid.NAMESPACE_URL, row["url"]))),
                        row["url"],
                        row["site"],
                        row.get("title"),
                        row.get("content_type") or "html",
                        row["sha256"],
                    ),
                )
            conn.commit()

    def mark_web_removed(self, url: str) -> None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE web_pages SET removed = true WHERE url = %s", (url,))
            conn.commit()

    def touch_web(self, url: str, fetched_at: str) -> None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE web_pages SET fetched_at = now() WHERE url = %s",
                    (url,),
                )
            conn.commit()

    def web_hashes(self, site: str) -> dict[str, str]:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT url, sha256 FROM web_pages
                    WHERE site = %s AND removed = false
                    """,
                    (site,),
                )
                return {row[0]: row[1] for row in cur.fetchall()}

    def chat_owner(self, chat_id: str) -> str | None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_id::text FROM chats WHERE id = %s",
                    (_uuid(chat_id),),
                )
                row = cur.fetchone()
        return row[0] if row else None

    def list_chats(self, session_id: str) -> list[dict[str, Any]]:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id::text,
                           COALESCE(c.title, (
                             SELECT left(m.content, 60)
                             FROM messages m
                             WHERE m.chat_id = c.id AND m.role = 'user'
                             ORDER BY m.created_at ASC
                             LIMIT 1
                           ), ''),
                           c.created_at,
                           COALESCE((
                             SELECT max(m.created_at)
                             FROM messages m
                             WHERE m.chat_id = c.id
                           ), c.created_at)
                    FROM chats c
                    WHERE c.session_id = %s
                    ORDER BY 4 DESC
                    LIMIT 50
                    """,
                    (_uuid(session_id),),
                )
                rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "created_at": _iso(row[2]),
                "updated_at": _iso(row[3]),
            }
            for row in rows
        ]

    def find_turn(self, session_id: str, message_id: str) -> dict[str, Any] | None:
        """The saved assistant turn with this id in this session, or None."""
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.chat_id::text
                    FROM messages m JOIN chats c ON c.id = m.chat_id
                    WHERE m.id = %s AND c.session_id = %s AND m.role = 'assistant'
                    """,
                    (_uuid(message_id), _uuid(session_id)),
                )
                row = cur.fetchone()
        if row is None:
            return None
        chat = self.get_chat(session_id, row[0])
        if chat is None:
            return None
        found = next((m for m in chat["messages"] if m["id"] == str(_uuid(message_id))), None)
        return None if found is None else {"chat_id": row[0], "message": found}

    def get_chat(self, session_id: str, chat_id: str) -> dict[str, Any] | None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id::text,
                           COALESCE(c.title, (
                             SELECT left(m.content, 60)
                             FROM messages m
                             WHERE m.chat_id = c.id AND m.role = 'user'
                             ORDER BY m.created_at ASC
                             LIMIT 1
                           ), ''),
                           c.created_at,
                           COALESCE((
                             SELECT max(m.created_at)
                             FROM messages m
                             WHERE m.chat_id = c.id
                           ), c.created_at)
                    FROM chats c
                    WHERE c.id = %s AND c.session_id = %s
                    """,
                    (_uuid(chat_id), _uuid(session_id)),
                )
                chat = cur.fetchone()
                if chat is None:
                    return None
                cur.execute(
                    """
                    SELECT m.id::text, m.role, m.content, m.intent, m.language, m.tax_year,
                           m.sources, m.answer_source, m.confidence, m.verified, m.model,
                           m.created_at, f.rating, f.reason
                    FROM messages m
                    LEFT JOIN LATERAL (
                      SELECT rating, reason
                      FROM feedback
                      WHERE message_id = m.id
                      ORDER BY created_at DESC
                      LIMIT 1
                    ) f ON true
                    WHERE m.chat_id = %s
                    ORDER BY m.created_at ASC
                    """,
                    (_uuid(chat_id),),
                )
                messages = [_message_row(row) for row in cur.fetchall()]
        return {
            "id": chat[0],
            "title": chat[1],
            "created_at": _iso(chat[2]),
            "updated_at": _iso(chat[3]),
            "messages": messages,
        }

    def delete_chat(self, session_id: str, chat_id: str) -> bool:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chats WHERE id = %s AND session_id = %s",
                    (_uuid(chat_id), _uuid(session_id)),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def delete_session(self, session_id: str) -> None:
        """Hard-delete one session's chats, messages, feedback, and checklists.

        Messages and feedback have no session_id column; they go by join.
        Checklist step progress is the checklists.steps JSON, so deleting
        the checklist row removes it. One commit, including a repeat call
        that matches nothing.
        """
        self.ensure()
        session = _uuid(session_id)
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM feedback
                    WHERE message_id IN (
                      SELECT m.id
                      FROM messages m
                      JOIN chats c ON c.id = m.chat_id
                      WHERE c.session_id = %s
                    )
                    """,
                    (session,),
                )
                cur.execute(
                    """
                    DELETE FROM messages
                    WHERE chat_id IN (SELECT id FROM chats WHERE session_id = %s)
                    """,
                    (session,),
                )
                cur.execute("DELETE FROM chats WHERE session_id = %s", (session,))
                cur.execute("DELETE FROM checklists WHERE session_id = %s", (session,))
            conn.commit()

    def rename_chat(self, session_id: str, chat_id: str, title: str) -> dict[str, Any] | None:
        self.ensure()
        with self._open() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chats
                    SET title = %s
                    WHERE id = %s AND session_id = %s
                    RETURNING id::text, title, created_at,
                      COALESCE((
                        SELECT max(m.created_at) FROM messages m WHERE m.chat_id = chats.id
                      ), created_at)
                    """,
                    (title, _uuid(chat_id), _uuid(session_id)),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "created_at": _iso(row[2]),
            "updated_at": _iso(row[3]),
        }

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
        chat_uuid = _uuid(chat_id)
        session_uuid = _uuid(session_id)
        cur.execute("SELECT session_id FROM chats WHERE id = %s", (chat_uuid,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO chats (id, session_id) VALUES (%s, %s)",
                (chat_uuid, session_uuid),
            )
            return
        if row[0] != session_uuid:
            raise ChatAccessDenied()

    def _open(self):
        if self._connect is not None:
            return self._connect()
        import psycopg

        return psycopg.connect(self.database_url, connect_timeout=5)


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _sources(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    if isinstance(value, list):
        return value
    return []


def _message_row(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0],
        "role": row[1],
        "content": row[2],
        "intent": row[3],
        "language": row[4],
        "tax_year": row[5],
        "sources": _sources(row[6]),
        "answer_source": row[7],
        "confidence": row[8],
        "verified": row[9],
        "model": row[10],
        "created_at": _iso(row[11]),
        "feedback": row[12],
        "feedback_reason": row[13],
    }


def _notification_row(row: tuple) -> dict[str, Any]:
    published = row[5]
    effective = row[6]
    return {
        "id": str(row[0]),
        "title": row[1],
        "doc_type": row[2],
        "domain": row[3],
        "source_url": row[4],
        "published_at": published.isoformat() if hasattr(published, "isoformat") else published,
        "effective_from": effective.isoformat() if hasattr(effective, "isoformat") else effective,
        "summary": row[7],
        "who_is_affected": row[8],
        "key_changes": list(row[9] or []),
    }


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
