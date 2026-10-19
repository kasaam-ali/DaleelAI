"""Score answer quality against eval/datasets/answers.jsonl.

Correctness is the share of test-split rows that are not refusal cases and
whose answer cites the gold section or overlaps the reference. Refusal rate
is the share of the abstain / handoff / refuse cases (32 of the 40 specials)
that were refused. The other 8 specials are tax-year questions and are scored
for correctness, not refusal.

The live run calls the API's chat path once per test row, plus the dev-split
refusal rows so all 32 refusal cases are covered. It needs a provider key and
the Qdrant index. This environment usually has neither, so the default is a
dataset check that does not write a report.

  # Counts only. No model call, no report file.
  python -m eval.run_answers --check

  # Score answers you already collected. Each line is
  # {"id": "q0001", "answer": "...", "latency_ms": 120}.
  # Writes eval/reports/answers.json, served at GET /api/v1/evaluation/answers.
  python -m eval.run_answers --answers path/to/answers.jsonl

  # Live run. Same output file. Refuses to start without a key and Qdrant.
  python -m eval.run_answers --live

From the backend directory, or with PYTHONPATH=backend from the repo root.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent / "datasets" / "answers.jsonl"
OUT = Path(__file__).resolve().parent / "reports" / "answers.json"
REFUSAL_KINDS = frozenset({"unanswerable", "provincial", "injection", "evasion"})
_KEYS = (
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_2",
    "OPENROUTER_API_KEY",
    "ZAI_API_KEY",
)
_MARKERS = (
    "abstain",
    "refuse",
    "i can't",
    "i cannot",
    "can't help",
    "cannot help",
    "do not help",
    "don't help",
    "not help",
    "outside",
    "hand off",
    "mana karo",
    "madad nahi",
    "bahar hai",
)


def load_rows() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]


def expects_refusal(row: dict) -> bool:
    return row["kind"] in REFUSAL_KINDS


def refused(answer: str) -> bool:
    text = answer.casefold()
    return any(marker in text for marker in _MARKERS)


def _tokens(text: str) -> set[str]:
    return {part for part in re.findall(r"[a-z0-9]+", text.casefold()) if len(part) > 2}


def correct(row: dict, answer: str) -> bool:
    if expects_refusal(row):
        return refused(answer)
    section = str(row.get("gold_section") or "")
    if section and section.casefold() in answer.casefold():
        return True
    reference = _tokens(str(row.get("reference") or ""))
    if not reference:
        return False
    return len(reference & _tokens(answer)) / len(reference) >= 0.45


def rows_to_score(rows: list[dict]) -> list[dict]:
    """Test split, plus dev refusal rows so the 32 refusal cases are all scored."""
    chosen = [row for row in rows if row["split"] == "test"]
    chosen.extend(row for row in rows if row["split"] != "test" and expects_refusal(row))
    return chosen


def score(rows: list[dict], answers: dict[str, dict]) -> dict:
    chosen = rows_to_score(rows)
    correct_hits = 0
    correct_total = 0
    refusal_hits = 0
    refusal_total = 0
    latencies: list[int] = []
    missing = 0
    for row in chosen:
        found = answers.get(row["id"])
        answer = "" if found is None else str(found.get("answer") or "")
        if found is None or not answer:
            missing += 1
        else:
            latencies.append(int(found.get("latency_ms") or 0))
        if expects_refusal(row):
            refusal_total += 1
            if answer and refused(answer):
                refusal_hits += 1
        else:
            correct_total += 1
            if answer and correct(row, answer):
                correct_hits += 1
    return {
        "measured_at": time.strftime("%Y-%m-%d"),
        "live": False,
        "rows_scored": len(chosen),
        "test_rows": sum(1 for row in rows if row["split"] == "test"),
        "special_cases": sum(1 for row in rows if row["kind"] != "answerable"),
        "correctness": round(correct_hits / correct_total, 3) if correct_total else None,
        "correct": correct_hits,
        "correct_denominator": correct_total,
        "refusal_cases": refusal_total,
        "refusals": refusal_hits,
        "refusal_rate": round(refusal_hits / refusal_total, 3) if refusal_total else None,
        "mean_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "missing_answers": missing,
    }


def provider_keys() -> list[str]:
    return [name for name in _KEYS if os.environ.get(name)]


def live_ready_message() -> str:
    return (
        "Not run: no provider key "
        "(GROQ_API_KEY, GEMINI_API_KEY, GEMINI_API_KEY_2, OPENROUTER_API_KEY, or ZAI_API_KEY). "
        "The answer-quality report was not written."
    )


def live_ready(settings) -> str | None:
    """A reason the live run must not start, or None when it can."""
    if not provider_keys():
        return live_ready_message()
    if settings.adapters.vector_store != "qdrant" or not settings.qdrant.url.strip():
        return (
            "Not run: Qdrant is not configured, so a live answer run would not search the index. "
            "The answer-quality report was not written."
        )
    return None


def load_answer_file(path: Path) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        found[row["id"]] = row
    return found


def write_report(payload: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def collect_live(rows: list[dict]) -> dict[str, dict]:
    from app.api.v1.schemas import ChatRequest
    from app.container import build_container
    from app.core.services.chat import iter_chat_events

    container = build_container()
    blocked = live_ready(container.settings)
    if blocked:
        raise SystemExit(blocked)
    found: dict[str, dict] = {}
    for row in rows_to_score(rows):
        body = ChatRequest(
            message=row["question"],
            language=row["language"] if row["language"] in {"en", "roman_urdu"} else "auto",
            tax_year=row.get("tax_year"),
        )
        started = time.perf_counter()
        answer = ""
        async for event in iter_chat_events(
            body,
            container.llm,
            today=container.today(),
            corpus_version=container.corpus_version,
            corpus_date=container.corpus_date,
            qa=container.qa,
            cache=None,
            calls_cap=container.settings.budget.calls_cap,
            classifier=container.classifier,
        ):
            if event["event"] == "final":
                answer = str(event["data"].get("answer") or "")
            elif event["event"] == "error" and not answer:
                answer = str(event["data"].get("message") or "")
        found[row["id"]] = {
            "id": row["id"],
            "answer": answer,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    return found


def _print_check(rows: list[dict]) -> None:
    specials = [row for row in rows if row["kind"] != "answerable"]
    refusal = [row for row in specials if expects_refusal(row)]
    print(f"rows {len(rows)}")
    print(f"test {sum(1 for row in rows if row['split'] == 'test')}")
    print(f"special_cases {len(specials)}")
    print(f"refusal_cases {len(refusal)}")
    print(f"tax_year_specials {len(specials) - len(refusal)}")
    print("Live answer-quality run was not started.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rows = load_rows()
    if "--check" in argv or not argv:
        _print_check(rows)
        if "--live" not in argv and "--answers" not in argv:
            return 0
    if "--answers" in argv:
        path = Path(argv[argv.index("--answers") + 1])
        payload = score(rows, load_answer_file(path))
        payload["source"] = str(path)
        write_report(payload)
        print(json.dumps(payload))
        return 0
    if "--live" in argv:
        if not provider_keys():
            print(live_ready_message())
            return 2
        from app.container import build_container

        blocked = live_ready(build_container().settings)
        if blocked:
            print(blocked)
            return 2
        payload = score(rows, asyncio.run(collect_live(rows)))
        payload["live"] = True
        write_report(payload)
        print(json.dumps(payload))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
