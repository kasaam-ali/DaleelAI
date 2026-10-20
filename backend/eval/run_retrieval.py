"""Retrieval eval over the 160-question test split.

The full run searches the Qdrant `documents` collection, reranks with the
cross-encoder, and verifies with the judge model. That needs Qdrant and
provider keys, and it does not download a missing cross-encoder.

Without those, the default is a lexical stand-in index in this file. It
scores every test question and reranks locally. Verification is recorded as
not run.

  # Stand-in. No keys, no Qdrant. Writes eval/reports/retrieval.json.
  python -m eval.run_retrieval

  # Full index. Needs QDRANT_URL, the documents collection, and (for
  # verification) a provider key. A missing cross-encoder stays not_rerun.
  python -m eval.run_retrieval --index qdrant

From the backend directory, or with PYTHONPATH=backend from the repo root.
"""

import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "datasets" / "answers.jsonl"
OUT = Path(__file__).resolve().parent / "reports" / "retrieval.json"

_STOP = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "and",
    "or",
    "is",
    "are",
    "does",
    "do",
    "what",
    "which",
    "when",
    "if",
    "still",
    "apply",
    "applies",
    "covers",
    "cover",
    "section",
    "kis",
    "se",
    "hai",
    "ka",
    "ki",
    "ke",
    "mein",
    "par",
    "kya",
    "ko",
    "aur",
    "yeh",
    "this",
    "that",
    "with",
    "from",
    "under",
    "not",
    "how",
    "can",
    "you",
    "your",
    "was",
    "were",
    "will",
    "its",
    "per",
}
_CITIES = {
    "karachi",
    "lahore",
    "islamabad",
    "rawalpindi",
    "faisalabad",
    "multan",
    "peshawar",
    "quetta",
    "hyderabad",
    "sialkot",
}

# Short passages, not the ordinance text. Distractors keep top-5 from being trivial.
PASSAGES = [
    {
        "section": "149",
        "text": (
            "Section 149 salary withholding annual income saalana employee. "
            "Section 149 of the Income Tax Ordinance, 2001 is the salary withholding section."
        ),
    },
    {
        "section": "4AB",
        "text": (
            "Section 4AB surcharge on salary in TY2026. "
            "Section 4AB is the TY2026 surcharge section. 4AB surcharge lagta."
        ),
    },
    {
        "section": "154A",
        "text": (
            "Section 154A freelancer IT services export withholding. "
            "Section 154A covers withholding on export of certain services, including IT."
        ),
    },
    {
        "section": "236C",
        "text": (
            "Section 236C property sale immovable withholding. "
            "Section 236C is the withholding section on sale of immovable property."
        ),
    },
    {
        "section": "236K",
        "text": (
            "Section 236K property purchase immovable withholding. "
            "Section 236K is the withholding section on purchase of immovable property."
        ),
    },
    {
        "section": "150",
        "text": (
            "Section 150 dividend withholding. Section 150 is the dividend withholding section."
        ),
    },
    {
        "section": "151",
        "text": (
            "Section 151 profit on debt withholding. "
            "Section 151 is the profit on debt withholding section."
        ),
    },
    {
        "section": "14",
        "text": (
            "Section 14 sales tax registration Sales Tax Act business. "
            "Section 14 of the Sales Tax Act, 1990 covers registration."
        ),
    },
    {
        "section": "80",
        "text": (
            "Section 80 customs declaration assessment Customs Act. "
            "Section 80 of the Customs Act, 1969 covers assessment."
        ),
    },
    {
        "section": "16",
        "text": (
            "Section 16 forming a company incorporation Companies Act banane. "
            "Section 16 of the Companies Act, 2017 covers incorporation."
        ),
    },
    {"section": "12", "text": "Section 12 defines salary. It is the definition, not withholding."},
    {
        "section": "114",
        "text": "Section 114 is the return of income. Filing a return is not withholding.",
    },
    {"section": "122", "text": "Section 122 is an amended assessment order by the commissioner."},
    {
        "section": "4",
        "text": "Section 4 is the charge of income tax, not a surcharge and not withholding.",
    },
    {"section": "148", "text": "Section 148 is withholding on imports, not on IT service exports."},
    {
        "section": "153",
        "text": "Section 153 is withholding on payments for goods, services, and contracts.",
    },
    {
        "section": "155",
        "text": "Section 155 is withholding on rent of property, not on a sale or purchase.",
    },
    {
        "section": "3",
        "text": "Section 3 of the Sales Tax Act is the charge of sales tax, not registration.",
    },
    {"section": "23", "text": "Section 23 of the Sales Tax Act covers the tax invoice."},
    {
        "section": "79",
        "text": "Section 79 of the Customs Act covers filing a goods declaration, not assessment.",
    },
    {
        "section": "42",
        "text": "Section 42 of the Companies Act covers associations, not forming a company.",
    },
    {
        "section": "236",
        "text": "Section 236 is a general advance tax. It is not the sale or purchase section.",
    },
]


def load_rows() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]


def tokens(text: str) -> set[str]:
    found = set()
    for part in re.findall(r"[a-z0-9]+", text.casefold()):
        if part in _STOP or part in _CITIES or part.isdigit():
            continue
        if len(part) < 2:
            continue
        found.add(part)
    return found


def _idf(passages: list[dict]) -> dict[str, float]:
    docs = [set(passage["tokens"]) for passage in passages]
    total = len(docs)
    weights: dict[str, float] = {}
    vocabulary = set().union(*docs)
    for term in vocabulary:
        df = sum(1 for doc in docs if term in doc)
        weights[term] = math.log((1 + total) / (1 + df)) + 1
    return weights


def prepare(passages: list[dict] | None = None) -> list[dict]:
    built = []
    for passage in passages or PASSAGES:
        text = passage["text"]
        section = str(passage["section"])
        built.append(
            {
                "section": section,
                "text": text,
                "tokens": tokens(f"{text} {section}"),
            }
        )
    weights = _idf(built)
    for passage in built:
        passage["weights"] = weights
    return built


def _score(query: str, passage: dict, *, section_bonus: float) -> float:
    query_tokens = tokens(query)
    weights = passage["weights"]
    total = sum(weights.get(term, 0.0) for term in query_tokens if term in passage["tokens"])
    if passage["section"].casefold() in query.casefold():
        total += section_bonus
    return total


def search(
    query: str, passages: list[dict], k: int = 5, *, section_bonus: float = 0.0
) -> list[dict]:
    ranked = sorted(
        passages, key=lambda passage: -_score(query, passage, section_bonus=section_bonus)
    )
    return ranked[:k]


def lexical_rerank(query: str, hits: list[dict], keep: int = 5) -> list[dict]:
    ranked = sorted(hits, key=lambda passage: -_score(query, passage, section_bonus=3.0))
    return ranked[:keep]


def hit(hits: list[dict], section: str | None) -> bool:
    if not section:
        return False
    wanted = section.casefold()
    return any(str(item.get("section") or "").casefold() == wanted for item in hits[:5])


def dataset_counts(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "en": sum(1 for row in rows if row["language"] == "en"),
        "roman_urdu": sum(1 for row in rows if row["language"] == "roman_urdu"),
        "special": sum(1 for row in rows if row["kind"] != "answerable"),
        "dev": sum(1 for row in rows if row["split"] == "dev"),
        "test": sum(1 for row in rows if row["split"] == "test"),
        "kinds": dict(sorted(Counter(row["kind"] for row in rows).items())),
    }


def _stage(name, status, reason, recall=None, latency=None, rows=0) -> dict:
    return {
        "name": name,
        "status": status,
        "recall_at_5": recall,
        "coverage": None,
        "mean_latency_ms": latency,
        "rows": rows,
        "reason": reason,
    }


def measure(rows: list[dict], search_fn, rerank_fn=None) -> dict:
    first_hits = 0
    rerank_hits = 0
    scored = 0
    first_ms = 0
    rerank_ms = 0
    for row in rows:
        section = row.get("gold_section")
        started = time.perf_counter()
        hits = search_fn(row["question"])
        first_ms += int((time.perf_counter() - started) * 1000)
        if section:
            scored += 1
            if hit(hits, section):
                first_hits += 1
        if rerank_fn is None:
            continue
        started = time.perf_counter()
        reranked = rerank_fn(row["question"], hits)
        rerank_ms += int((time.perf_counter() - started) * 1000)
        if section and hit(reranked, section):
            rerank_hits += 1
    n = len(rows)
    return {
        "n": n,
        "scored": scored,
        "first_hits": first_hits,
        "rerank_hits": rerank_hits,
        "first_ms": round(first_ms / n) if n else None,
        "rerank_ms": round(rerank_ms / n) if n and rerank_fn else None,
    }


def stand_in_report(rows: list[dict], test_rows: list[dict] | None = None) -> dict:
    passages = prepare()
    chosen = test_rows if test_rows is not None else [row for row in rows if row["split"] == "test"]
    # Rerank sees a wider pool than the top 5 the first stage returns.
    pool = prepare()

    def first(query: str) -> list[dict]:
        return search(query, pool, k=30, section_bonus=0.0)

    def rerank(query: str, hits: list[dict]) -> list[dict]:
        return lexical_rerank(query, hits, keep=5)

    measured = measure(chosen, first, rerank)
    n = measured["n"]
    scored = measured["scored"]
    recall = round(measured["first_hits"] / scored, 3) if scored else None
    rerank_recall = round(measured["rerank_hits"] / scored, 3) if scored else None
    reason = (
        f"Lexical stand-in index ({len(passages)} passages). "
        f"{scored} of {n} test rows have a gold section; recall@5 uses those. "
        "This is not the Qdrant documents collection."
    )
    keys = [
        name
        for name in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY")
        if os.environ.get(name)
    ]
    verify_reason = "Verification calls an outside model. " + (
        "A provider key is set, but this stand-in pass does not spend those calls."
        if keys
        else "No provider key was set, so this pass did not call one."
    )
    return {
        "measured_at": time.strftime("%Y-%m-%d"),
        "index": "stand-in",
        "split": "test",
        "rows": n,
        "scored_rows": scored,
        "live_models": False,
        "not_run": ["qdrant", "cross-encoder rerank", "verification"],
        "dataset": dataset_counts(rows),
        "stages": [
            _stage(
                "lexical", "stand_in", reason, recall=recall, latency=measured["first_ms"], rows=n
            ),
            _stage(
                "+rerank",
                "stand_in",
                "Lexical rerank on the stand-in pool, with a bonus when the query "
                "names the section. The cross-encoder was not loaded.",
                recall=rerank_recall,
                latency=measured["rerank_ms"],
                rows=n,
            ),
            _stage("+verification", "not_rerun", verify_reason),
        ],
    }


def qdrant_report(rows: list[dict]) -> dict:
    """Full-index path. Raises SystemExit when Qdrant or the collection is unreachable."""
    from app.adapters.qdrant_search import QdrantHybridSearch
    from app.settings import load_settings

    settings = load_settings()
    if not settings.qdrant.url.strip():
        raise SystemExit(
            "Not run: QDRANT_URL is empty. The full-index retrieval eval did not start."
        )
    searcher = QdrantHybridSearch(
        settings.qdrant.url,
        settings.qdrant.api_key,
        settings.models.dense,
        settings.models.sparse,
    )
    try:
        searcher._ensure()
        before = int(searcher._client.count(collection_name="documents", exact=True).count)
    except Exception as exc:
        raise SystemExit(
            f"Not run: Qdrant documents is unreachable ({type(exc).__name__})."
        ) from exc
    chosen = [row for row in rows if row["split"] == "test"]

    def first(query: str) -> list[dict]:
        points = searcher._search("documents", query, None, 30)
        return [_point(point) for point in points]

    rerank_fn = _cross_encoder(settings.models.reranker)
    measured = measure(chosen, first, rerank_fn)
    after = int(searcher._client.count(collection_name="documents", exact=True).count)
    if after != before:
        raise SystemExit(f"documents changed from {before} to {after}")
    scored = measured["scored"]
    n = measured["n"]
    stages = [
        _stage(
            "lexical",
            "measured",
            "Dense plus BM25 on the documents collection. "
            "Recall@5 is the gold section in the top 5.",
            recall=round(measured["first_hits"] / scored, 3) if scored else None,
            latency=measured["first_ms"],
            rows=n,
        )
    ]
    not_run = []
    if rerank_fn is None:
        not_run.append("cross-encoder rerank")
        stages.append(
            _stage(
                "+rerank",
                "not_rerun",
                "The cross-encoder is not on disk, so it was not downloaded for this run.",
            )
        )
    else:
        stages.append(
            _stage(
                "+rerank",
                "measured",
                "Cross-encoder rerank of the hybrid pool. Recall@5 uses the reranked top 5.",
                recall=round(measured["rerank_hits"] / scored, 3) if scored else None,
                latency=measured["rerank_ms"],
                rows=n,
            )
        )
    not_run.append("verification")
    stages.append(
        _stage(
            "+verification",
            "not_rerun",
            "Verification calls an outside model once per question. "
            "This retrieval pass does not spend those calls; "
            "run eval.run_answers --live for answer quality.",
        )
    )
    return {
        "measured_at": time.strftime("%Y-%m-%d"),
        "index": "qdrant",
        "split": "test",
        "rows": n,
        "scored_rows": scored,
        "documents_before": before,
        "documents_after": after,
        "documents_unchanged": True,
        "live_models": False,
        "not_run": not_run,
        "dataset": dataset_counts(rows),
        "stages": stages,
    }


def _point(point) -> dict:
    payload = dict(getattr(point, "payload", None) or {})
    return {
        "section": str(payload.get("section") or ""),
        "text": str(payload.get("text") or ""),
        "payload": payload,
    }


def _cross_encoder(model_name: str):
    cache = Path(os.environ.get("FASTEMBED_CACHE_PATH", Path.home() / ".cache" / "fastembed"))
    if not cache.is_dir() or not any(cache.iterdir()):
        return None
    try:
        from app.adapters.fastembed_rerank import FastEmbedReranker
        from app.core.retrieval.rerank import rerank as rerank_hits
    except ImportError:
        return None
    scorer = FastEmbedReranker(model_name)

    def rerank(query: str, hits: list[dict]) -> list[dict]:
        from app.core.retrieval.fusion import RankedHit

        ranked = [
            RankedHit(
                chunk_id=str(index),
                domain=None,
                payload={"text": hit["text"], "section": hit["section"]},
            )
            for index, hit in enumerate(hits)
        ]
        ordered = rerank_hits(query, ranked, scorer, pool=len(ranked), keep=5)
        return [
            {"section": hit.payload.get("section"), "text": hit.payload.get("text")}
            for hit, _score in ordered
        ]

    return rerank


def write_report(payload: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    index = "stand-in"
    if "--index" in argv:
        index = argv[argv.index("--index") + 1]
    rows = load_rows()
    if index == "qdrant":
        if not os.environ.get("QDRANT_URL", "").strip():
            print("Not run: QDRANT_URL is empty. The full-index retrieval eval did not start.")
            return 2
        payload = qdrant_report(rows)
    elif index == "stand-in":
        payload = stand_in_report(rows)
    else:
        print("index must be stand-in or qdrant")
        return 2
    write_report(payload)
    summary = {
        "index": payload["index"],
        "rows": payload["rows"],
        "not_run": payload["not_run"],
        "stages": {stage["name"]: stage["recall_at_5"] for stage in payload["stages"]},
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
