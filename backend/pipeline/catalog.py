"""Reads catalog.csv and checks that each document row is valid."""

import csv
import os
import re
from dataclasses import dataclass, fields
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("catalog.csv")
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))

STATUSES = {"active", "pending", "superseded", "incorporated", "expired", "excluded"}
TAX_YEARS = {"TY2026", "TY2027"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class CatalogEntry:
    doc_id: str
    work_id: str
    title: str
    doc_type: str
    domain: str
    authority: str
    language: str
    amended_upto: str
    tax_years: str
    status: str
    superseded_by: str
    source_url: str
    local_file: str
    sha256: str
    notes: str

    @property
    def tax_year_list(self) -> list[str]:
        return self.tax_years.split()

    @property
    def searchable(self) -> bool:
        return self.status == "active"

    def path(self, data_dir: Path = DATA_DIR) -> Path:
        """Downloaded copies live in data/docs; hand-collected files stay in data/raw."""
        if self.source_url:
            return data_dir / "docs" / f"{self.doc_id}.pdf"
        return data_dir / "raw" / self.local_file

    def local_copy(self, data_dir: Path = DATA_DIR) -> Path | None:
        return data_dir / "raw" / self.local_file if self.local_file else None


COLUMNS = [f.name for f in fields(CatalogEntry)]


def read_catalog(path: Path = CATALOG_PATH) -> list[CatalogEntry]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"catalog columns must be {COLUMNS}, got {reader.fieldnames}")
        return [CatalogEntry(**row) for row in reader]


def write_catalog(entries: list[CatalogEntry], path: Path = CATALOG_PATH) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            writer.writerow({c: getattr(entry, c) for c in COLUMNS})


def validate(entries: list[CatalogEntry]) -> list[str]:
    problems: list[str] = []
    ids = [e.doc_id for e in entries]
    by_id = {e.doc_id: e for e in entries}
    for doc_id in {i for i in ids if ids.count(i) > 1}:
        problems.append(f"{doc_id}: duplicate doc_id")

    for e in entries:
        where = e.doc_id or "<missing doc_id>"
        if not e.doc_id or not e.work_id or not e.title:
            problems.append(f"{where}: doc_id, work_id and title are required")
        if e.status not in STATUSES:
            problems.append(f"{where}: unknown status {e.status!r}")
        unknown_years = set(e.tax_year_list) - TAX_YEARS
        if unknown_years:
            problems.append(f"{where}: unknown tax years {sorted(unknown_years)}")
        if e.status in {"active", "pending"} and not e.tax_year_list:
            problems.append(f"{where}: {e.status} documents need tax_years")
        if e.status not in {"active", "pending"} and e.tax_year_list:
            problems.append(f"{where}: only active or pending documents carry tax_years")
        if not e.source_url and not e.local_file:
            problems.append(f"{where}: needs a source_url or a local_file")
        if e.source_url and not e.source_url.startswith("https://"):
            problems.append(f"{where}: source_url must be https")
        if e.sha256 and not SHA256_RE.match(e.sha256):
            problems.append(f"{where}: sha256 must be 64 lowercase hex characters")
        if e.status in {"superseded", "incorporated"}:
            target = by_id.get(e.superseded_by)
            if target is None:
                problems.append(f"{where}: superseded_by {e.superseded_by!r} is not in the catalog")
            elif target.status != "active":
                problems.append(f"{where}: superseded_by {e.superseded_by!r} is not active")
        elif e.superseded_by:
            problems.append(f"{where}: superseded_by is only for superseded or incorporated rows")

    works: dict[tuple[str, str], list[str]] = {}
    for e in entries:
        if e.status == "active":
            for year in e.tax_year_list:
                works.setdefault((e.work_id, year), []).append(e.doc_id)
    for (work_id, year), doc_ids in works.items():
        if len(doc_ids) > 1:
            problems.append(f"{work_id}: {year} has more than one active version {doc_ids}")
    return problems
