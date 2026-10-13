"""Fetch catalog documents into data/docs and check them against their pinned sha256.

Run inside the backend container:
    docker compose run --rm --no-deps backend python -m pipeline.download [--all] [--pin]

--all   also verify superseded/expired/excluded rows (local files only)
--pin   record the sha256 of rows that have none yet
"""

import argparse
import hashlib
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from pipeline.catalog import (
    CATALOG_PATH,
    DATA_DIR,
    CatalogEntry,
    read_catalog,
    validate,
    write_catalog,
)

USER_AGENT = "DaleelAI/0.1 (student research project; +https://github.com/kasaam-ali/DaleelAI)"
POLITE_DELAY_S = 2.0


class DownloadError(Exception):
    pass


@dataclass
class Outcome:
    doc_id: str
    state: str  # ok | pinned | fetched | copied | missing | mismatch | failed | pending
    detail: str = ""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, dest: Path, client: httpx.Client) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise DownloadError(f"HTTP {response.status_code}")
            with tmp.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        with tmp.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise DownloadError("response is not a PDF")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def sync_entry(
    entry: CatalogEntry, data_dir: Path, client: httpx.Client, pin: bool
) -> tuple[Outcome, bool]:
    """Make sure the entry's file exists and matches its hash. Returns (outcome, network_used)."""
    path = entry.path(data_dir)
    state = "ok"
    network_used = False

    if not path.exists():
        local = entry.local_copy(data_dir)
        if entry.source_url and local is not None and local.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local, path)
            state = "copied"
        elif entry.source_url:
            network_used = True
            try:
                fetch(entry.source_url, path, client)
            except (DownloadError, httpx.HTTPError) as exc:
                return Outcome(entry.doc_id, "failed", str(exc) or type(exc).__name__), True
            state = "fetched"
        elif entry.status == "pending":
            return Outcome(entry.doc_id, "pending", entry.notes), False
        else:
            return Outcome(entry.doc_id, "missing", str(path)), False

    actual = sha256_of(path)
    if not entry.sha256:
        if pin:
            entry.sha256 = actual
            return Outcome(entry.doc_id, "pinned", actual[:12]), network_used
        return Outcome(entry.doc_id, "missing", "no sha256 pinned; rerun with --pin"), network_used
    if actual != entry.sha256:
        detail = f"expected {entry.sha256[:12]}, got {actual[:12]}"
        return Outcome(entry.doc_id, "mismatch", detail), network_used
    return Outcome(entry.doc_id, state), network_used


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="also verify non-searchable rows")
    parser.add_argument("--pin", action="store_true", help="record missing sha256 values")
    args = parser.parse_args(argv)

    entries = read_catalog(CATALOG_PATH)
    problems = validate(entries)
    if problems:
        print("catalog is invalid:", *problems, sep="\n  ")
        return 1

    wanted = [e for e in entries if args.all or e.status in {"active", "pending"}]
    outcomes: list[Outcome] = []
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, timeout=120, follow_redirects=True) as client:
        for entry in wanted:
            outcome, network_used = sync_entry(entry, DATA_DIR, client, args.pin)
            outcomes.append(outcome)
            print(f"{outcome.state:9} {outcome.doc_id} {outcome.detail}".rstrip(), flush=True)
            if network_used:
                time.sleep(POLITE_DELAY_S)

    if args.pin:
        write_catalog(entries, CATALOG_PATH)

    bad = [o for o in outcomes if o.state in {"missing", "mismatch", "failed"}]
    pending = [o for o in outcomes if o.state == "pending"]
    ok = len(outcomes) - len(bad) - len(pending)
    print(f"\n{ok} ok, {len(pending)} pending, {len(bad)} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
