"""Export OpenAPI and SSE event schemas. --check fails if the committed files differ."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CONTRACTS = ROOT / "contracts"
sys.path.insert(0, str(BACKEND))


def build_openapi() -> dict:
    from app.main import create_app

    return create_app().openapi()


def build_events() -> dict:
    from app.api.v1.schemas import SSE_EVENTS

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://daleelai.local/contracts/events.schema.json",
        "title": "DaleelAI SSE events",
        "oneOf": [model.model_json_schema() for model in SSE_EVENTS],
    }


def dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def generated() -> dict[str, str]:
    return {
        "openapi.json": dumps(build_openapi()),
        "events.schema.json": dumps(build_events()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or check API contracts")
    parser.add_argument("--check", action="store_true", help="Fail if committed JSON differs")
    args = parser.parse_args(argv)
    files = generated()
    drifted = []
    for name, text in files.items():
        path = CONTRACTS / name
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != text:
            drifted.append(name)
            if not args.check:
                path.write_text(text, encoding="utf-8")
    if args.check and drifted:
        print("contract drift: " + ", ".join(drifted), file=sys.stderr)
        return 1
    if args.check:
        print("contracts ok")
    else:
        print("wrote " + ", ".join(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
