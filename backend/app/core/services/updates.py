"""Store FBR updates and apply a web crawl without deleting unrelated pages."""

import hashlib
import uuid
from typing import Any

from app.core.classifier import KeywordClassifier
from app.core.updates.changes import OffList, ZeroPages, detect_changes, url_allowed
from app.core.updates.listing import ZeroItems, load_replay

_MEMORY: "MemoryUpdates | None" = None


class MemoryUpdates:
    def __init__(self) -> None:
        self.notifications: dict[str, dict[str, Any]] = {}
        self.web: dict[str, dict[str, Any]] = {}

    def insert_notification(self, row: dict[str, Any]) -> bool:
        if row["sha256"] in self.notifications:
            return False
        self.notifications[row["sha256"]] = dict(row)
        return True

    def mark_notification_indexed(self, sha256: str) -> None:
        if sha256 in self.notifications:
            self.notifications[sha256]["indexed"] = True

    def list_notifications(
        self, *, doc_type: str, domain: str, page: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows = [
            row
            for row in self.notifications.values()
            if (doc_type == "all" or row["doc_type"] == doc_type)
            and (domain == "all" or row["domain"] == domain)
        ]
        rows.sort(key=lambda row: (row.get("published_at") or "", row["title"]), reverse=True)
        total = len(rows)
        start = (page - 1) * limit
        return rows[start : start + limit], total

    def get_notification(self, item_id: str) -> dict[str, Any] | None:
        for row in self.notifications.values():
            if row["id"] == item_id:
                return row
        return None

    def notification_sha256s(self) -> list[str]:
        return [row["sha256"] for row in self.notifications.values()]

    def upsert_web(self, row: dict[str, Any]) -> None:
        self.web[row["url"]] = {**row, "removed": False}

    def mark_web_removed(self, url: str) -> None:
        if url in self.web:
            self.web[url]["removed"] = True

    def touch_web(self, url: str, fetched_at: str) -> None:
        if url in self.web:
            self.web[url]["fetched_at"] = fetched_at

    def web_hashes(self, site: str) -> dict[str, str]:
        return {
            url: row["sha256"]
            for url, row in self.web.items()
            if row["site"] == site and not row.get("removed")
        }


def memory_updates(reset: bool = False) -> MemoryUpdates:
    global _MEMORY
    if reset or _MEMORY is None:
        _MEMORY = MemoryUpdates()
    return _MEMORY


def ingest_notifications(
    items: list[dict[str, Any]],
    store: Any,
    classifier: Any | None = None,
    indexer: Any | None = None,
) -> dict[str, Any]:
    if not items:
        raise ZeroItems
    model = classifier or KeywordClassifier()
    ingested = 0
    skipped = 0
    indexed = 0
    for item in items:
        row = _row(item, model)
        if not store.insert_notification(row):
            skipped += 1
            continue
        ingested += 1
        if indexer is not None:
            try:
                indexer(row)
                store.mark_notification_indexed(row["sha256"])
                indexed += 1
            except Exception:
                pass
    return {
        "ingested": ingested,
        "skipped": skipped,
        "indexed": indexed,
        "corpus_version": _version(store.notification_sha256s()),
    }


def list_updates(store: Any, *, doc_type: str, domain: str, page: int, limit: int) -> dict:
    rows, total = store.list_notifications(doc_type=doc_type, domain=domain, page=page, limit=limit)
    pages = max(1, (total + limit - 1) // limit) if total else 1
    return {
        "items": [_public(row) for row in rows],
        "page": page,
        "pages": pages,
        "total": total,
    }


def replay_notifications(store: Any, classifier: Any | None = None, indexer: Any | None = None):
    return ingest_notifications(load_replay(), store, classifier, indexer)


def apply_web_crawl(
    site: str,
    pages: list[dict[str, Any]],
    store: Any,
    prefixes: list[str],
    indexer: Any | None = None,
) -> dict[str, Any]:
    """Apply an explicit crawl batch. An empty batch removes nothing."""
    if not pages:
        raise ZeroPages
    for page in pages:
        if not url_allowed(page["url"], prefixes):
            raise OffList(page["url"])
    known = store.web_hashes(site) if hasattr(store, "web_hashes") else {}
    fetched = [page for page in pages if page["status"] != "removed"]
    if fetched:
        plan = detect_changes(fetched, known)
    else:
        plan = {"new": [], "changed": [], "unchanged": [], "removed": []}
    explicit_removed = [page["url"] for page in pages if page["status"] == "removed"]
    indexed = 0
    for page in plan["new"] + plan["changed"]:
        store.upsert_web({**page, "site": site, "removed": False})
        if indexer is not None:
            indexer.upsert(page)
        indexed += 1
    removed = 0
    for url in explicit_removed:
        store.mark_web_removed(url)
        if indexer is not None:
            indexer.delete(url)
        removed += 1
    for page in plan["unchanged"]:
        store.touch_web(page["url"], page.get("fetched_at") or "")
    version = _version([page.get("sha256") or page["url"] for page in pages])
    return {
        "indexed": indexed,
        "removed": removed,
        "unchanged": len(plan["unchanged"]),
        "corpus_version": version,
    }


def _row(item: dict[str, Any], classifier: Any) -> dict[str, Any]:
    text = item.get("text") or item["title"]
    prediction = classifier.predict(f"{item['title']}\n{text}")
    domain = prediction.category
    title = item["title"]
    published = item.get("published_at")
    when = published or "an unknown date"
    kind = item["doc_type"].replace("_", " ")
    summary_en = (
        f"This {kind} ({title}) was listed on {when}. "
        "Read the official file before you rely on it. This summary does not add a tax rate."
    )
    summary_ru = (
        f"Yeh {kind} ({title}) {when} ko listing mein aya. "
        "Official file parh lain. Is khulasa mein koi tax rate nahi hai."
    )
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, item["sha256"])),
        "sha256": item["sha256"],
        "title": title,
        "doc_type": item["doc_type"],
        "domain": domain,
        "source_url": item["source_url"],
        "published_at": published,
        "effective_from": None,
        "summary": f"{summary_en}\n\n{summary_ru}",
        "summary_en": summary_en,
        "summary_ru": summary_ru,
        "who_is_affected": "Readers named in the official file. This summary does not decide that.",
        "key_changes": ["Open the official file. This line does not state a tax change."],
        "indexed": False,
    }


def split_summary(summary: str) -> tuple[str, str]:
    """English, then Roman Urdu, separated by the first blank line."""
    english, _break, roman = (summary or "").partition("\n\n")
    return english, roman


def _public(row: dict[str, Any]) -> dict[str, Any]:
    english = row.get("summary_en")
    roman = row.get("summary_ru")
    if not english and not roman:
        english, roman = split_summary(str(row.get("summary") or ""))
    elif english is None or roman is None:
        fallback_en, fallback_ru = split_summary(str(row.get("summary") or ""))
        english = fallback_en if english is None else english
        roman = fallback_ru if roman is None else roman
    return {
        "id": row["id"],
        "title": row["title"],
        "doc_type": row["doc_type"],
        "domain": row.get("domain"),
        "published_at": row.get("published_at"),
        "effective_from": row.get("effective_from"),
        "summary": row["summary"],
        "summary_en": english,
        "summary_ru": roman,
        "who_is_affected": row.get("who_is_affected"),
        "key_changes": list(row.get("key_changes") or []),
        "source_url": row["source_url"],
    }


def _version(values: list[str]) -> str:
    blob = "\n".join(sorted(values))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]
