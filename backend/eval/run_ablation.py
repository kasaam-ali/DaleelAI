"""Read-only retrieval sample. Never writes to Qdrant and never rebuilds documents."""

import json
import re
import time
from pathlib import Path

from app.adapters.postgres_sections import PostgresSections
from app.adapters.qdrant_search import QdrantHybridSearch
from app.settings import load_settings

DATA = Path(__file__).resolve().parent / "datasets" / "answers.jsonl"
OUT = Path(__file__).resolve().parent / "reports" / "ablation.json"
SAMPLE = 8


def load_rows() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]


def sample_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    chosen: list[dict] = []
    for row in rows:
        if row["split"] != "test" or row["kind"] != "answerable" or not row.get("gold_section"):
            continue
        section = str(row["gold_section"])
        if section in seen:
            continue
        seen.add(section)
        chosen.append(row)
        if len(chosen) == SAMPLE:
            break
    return chosen


def contains(text: str, section: str) -> bool:
    return re.search(rf"\b{re.escape(section)}\b", text or "", flags=re.I) is not None


def hit_points(points, section: str) -> bool:
    for point in points[:5]:
        payload = dict(getattr(point, "payload", None) or {})
        blob = " ".join(
            str(payload.get(key) or "")
            for key in ("section", "heading", "section_title", "text", "parent_section")
        )
        if contains(blob, section):
            return True
    return False


def dense_points(search: QdrantHybridSearch, query: str):
    search._ensure()
    dense_vec, _indices, _values = search._embed(query)
    found = search._client.query_points(
        collection_name="documents",
        query=dense_vec,
        using="dense",
        limit=5,
        with_payload=True,
    )
    return found.points


def count_documents(search: QdrantHybridSearch) -> int:
    search._ensure()
    counted = search._client.count(collection_name="documents", exact=True)
    return int(counted.count)


def stage(name, status, reason, recall=None, latency=None, rows=0, coverage=None) -> dict:
    return {
        "name": name,
        "status": status,
        "recall_at_5": recall,
        "coverage": coverage,
        "mean_latency_ms": latency,
        "rows": rows,
        "reason": reason,
    }


def measure(search, sections, rows: list[dict]) -> dict:
    dense_hits = 0
    hybrid_hits = 0
    parent_hits = 0
    web_hits = 0
    dense_ms = 0
    hybrid_ms = 0
    web_ms = 0
    for row in rows:
        question = row["question"]
        section = row["gold_section"]
        year = row["tax_year"]
        started = time.perf_counter()
        dense = dense_points(search, question)
        dense_ms += int((time.perf_counter() - started) * 1000)
        if hit_points(dense, section):
            dense_hits += 1

        started = time.perf_counter()
        hybrid = search._search("documents", question, year, 5)
        hybrid_ms += int((time.perf_counter() - started) * 1000)
        if hit_points(hybrid, section):
            hybrid_hits += 1
        parent_ids = []
        for hit in hybrid:
            parent = str(hit.payload.get("parent_id") or "")
            if parent:
                parent_ids.append(parent)
        parents = sections(parent_ids)
        parent_hit = hit_points(hybrid, section) or any(
            contains(text, section) for text in parents.values()
        )
        if parent_hit:
            parent_hits += 1

        started = time.perf_counter()
        web = search._search("web_pages", question, None, 5)
        web_ms += int((time.perf_counter() - started) * 1000)
        if web:
            web_hits += 1

    n = len(rows)
    return {
        "dense_hits": dense_hits,
        "hybrid_hits": hybrid_hits,
        "parent_hits": parent_hits,
        "web_hits": web_hits,
        "n": n,
        "dense_ms": round(dense_ms / n) if n else None,
        "hybrid_ms": round(hybrid_ms / n) if n else None,
        "web_ms": round(web_ms / n) if n else None,
    }


def report_for(rows, measured, error, before, after):
    counts = {
        "total": len(rows),
        "en": sum(1 for row in rows if row["language"] == "en"),
        "roman_urdu": sum(1 for row in rows if row["language"] == "roman_urdu"),
        "special": sum(1 for row in rows if row["kind"] != "answerable"),
        "dev": sum(1 for row in rows if row["split"] == "dev"),
        "test": sum(1 for row in rows if row["split"] == "test"),
    }
    untouched = "This pass only ran queries. The documents collection was not rebuilt."
    stages = [
        stage(
            "v1.0 baseline",
            "not_rerun",
            "Rebuilding the first index would replace the 18,600 document points. " + untouched,
        ),
        stage(
            "+headers",
            "not_rerun",
            "Headers are already in the live chunks. "
            "A header-free index would be a second collection. " + untouched,
        ),
    ]
    if measured is None:
        pending = (
            "dense",
            "+BM25 hybrid",
            "+rerank",
            "+parent expansion",
            "+verification",
            "+web fallback",
        )
        for name in pending:
            stages.append(stage(name, "not_rerun", error or "Not measured."))
    else:
        n = measured["n"]
        stages[1:1] = [
            stage(
                "dense",
                "measured",
                "Dense-only query. Top 5 checked for the gold section.",
                recall=round(measured["dense_hits"] / n, 3) if n else None,
                latency=measured["dense_ms"],
                rows=n,
            )
        ]
        # insert order: v1.0, dense, +headers, hybrid...
        # stages currently v1.0, dense, +headers after the insert at 1. Wait I inserted at 1
        # so order is v1.0, dense, +headers. Good.
        stages.append(
            stage(
                "+BM25 hybrid",
                "measured",
                "Dense plus BM25 with RRF and the tax-year filter. Same gold-section check.",
                recall=round(measured["hybrid_hits"] / n, 3) if n else None,
                latency=measured["hybrid_ms"],
                rows=n,
            )
        )
        stages.append(
            stage(
                "+rerank",
                "not_rerun",
                "The cross-encoder was not loaded, so a cold download would not start.",
            )
        )
        stages.append(
            stage(
                "+parent expansion",
                "measured",
                "Same hybrid hits, plus the parent section text already stored in Postgres.",
                recall=round(measured["parent_hits"] / n, 3) if n else None,
                latency=measured["hybrid_ms"],
                rows=n,
            )
        )
        stages.append(
            stage(
                "+verification",
                "not_rerun",
                "Verification calls an outside model. This pass did not spend those calls.",
            )
        )
        stages.append(
            stage(
                "+web fallback",
                "measured",
                "Share of the sample with any web_pages hit. Coverage, not ordinance recall.",
                coverage=round(measured["web_hits"] / n, 3) if n else None,
                latency=measured["web_ms"],
                rows=n,
            )
        )
    return {
        "measured_at": time.strftime("%Y-%m-%d"),
        "sample_size": measured["n"] if measured else 0,
        "documents_before": before,
        "documents_after": after,
        "documents_unchanged": before is not None and before == after,
        "error": error,
        "dataset": counts,
        "stages": stages,
    }


def main() -> None:
    rows = load_rows()
    chosen = sample_rows(rows)
    settings = load_settings()
    search = QdrantHybridSearch(
        settings.qdrant.url,
        settings.qdrant.api_key,
        settings.models.dense,
        settings.models.sparse,
    )
    before = count_documents(search)
    print(f"documents {before}")
    print(f"sample {len(chosen)}")
    measured = measure(search, PostgresSections(settings.database_url), chosen)
    after = count_documents(search)
    print(f"documents after {after}")
    if after != before:
        raise SystemExit(f"documents changed from {before} to {after}")
    payload = report_for(rows, measured, None, before, after)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = {item["name"]: item["recall_at_5"] or item["coverage"] for item in payload["stages"]}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
