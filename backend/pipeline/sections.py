"""Load parent sections from chunk files into Postgres. Does not touch Qdrant."""

import json
import time
from pathlib import Path

from app.version import CORPUS_DATE, INDEXED_CORPUS_VERSION
from pipeline.catalog import DATA_DIR


def section_rows(payload: dict, version: str) -> list[tuple]:
    doc_id = str(payload.get("doc_id") or "")
    rows = []
    for section in payload.get("sections") or []:
        parent_id = str(section.get("parent_id") or "")
        text = str(section.get("text") or "").strip()
        if not doc_id or not parent_id or not text:
            continue
        rows.append(
            (
                parent_id,
                doc_id,
                section.get("section") or "",
                section.get("section_title") or "",
                section.get("page_start"),
                section.get("page_end"),
                text,
                version,
            )
        )
    return rows


def load_directory(
    cur,
    chunks_dir: Path,
    version: str,
) -> tuple[int, int, list[str]]:
    """Insert one file at a time. Returns files, rows, and failure messages."""
    files = 0
    rows = 0
    failures: list[str] = []
    paths = sorted(chunks_dir.glob("*.json"))
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            batch = section_rows(payload, version)
            if batch:
                cur.executemany(_UPSERT, batch)
            files += 1
            rows += len(batch)
            print(f"{path.name:45} sections={len(batch)}", flush=True)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            print(f"failed {path.name}: {exc}", flush=True)
    return files, rows, failures


_UPSERT = """
INSERT INTO sections (
  parent_id, doc_id, section, section_title, page_start, page_end, text, corpus_version
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (parent_id) DO UPDATE SET
  doc_id = EXCLUDED.doc_id,
  section = EXCLUDED.section,
  section_title = EXCLUDED.section_title,
  page_start = EXCLUDED.page_start,
  page_end = EXCLUDED.page_end,
  text = EXCLUDED.text,
  corpus_version = EXCLUDED.corpus_version
"""


def write_meta(cur, version: str, corpus_date: str) -> None:
    cur.executemany(
        """
        INSERT INTO meta (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        (("corpus_version", version), ("corpus_date", corpus_date)),
    )


def main() -> int:
    import os

    import psycopg

    from app.adapters.postgres_schema import SCHEMA

    started = time.monotonic()
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL is empty", flush=True)
        return 2
    chunks_dir = DATA_DIR / "chunks"
    with psycopg.connect(url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            for statement in SCHEMA:
                cur.execute(statement)
            files, rows, failures = load_directory(cur, chunks_dir, INDEXED_CORPUS_VERSION)
            write_meta(cur, INDEXED_CORPUS_VERSION, CORPUS_DATE)
            cur.execute("SELECT count(*) FROM sections")
            stored = cur.fetchone()[0]
        conn.commit()
    elapsed = round(time.monotonic() - started, 1)
    print("summary", flush=True)
    print(f"{'files':10} {files}", flush=True)
    print(f"{'rows':10} {rows}", flush=True)
    print(f"{'stored':10} {stored}", flush=True)
    print(f"{'failed':10} {len(failures)}", flush=True)
    print(f"{'seconds':10} {elapsed}", flush=True)
    print("qdrant was not used", flush=True)
    return 1 if failures else 0
