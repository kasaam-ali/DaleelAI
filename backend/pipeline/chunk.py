"""Turn extracted pages into parent sections and search chunks: data/chunks/<doc_id>.json.

Run inside the backend container:
    docker compose run --rm --no-deps backend python -m pipeline.chunk [--doc DOC_ID]

Sections are found from the law's own headings ("149. Salary.-", "PART VIII", "SECOND
SCHEDULE"). Documents without such headings (circulars, rate cards) get one parent per page.
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from bisect import bisect_right
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from datasketch import MinHash, MinHashLSH

from pipeline.catalog import CATALOG_PATH, DATA_DIR, CatalogEntry, read_catalog

CHUNK_VERSION = 1
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150
MAX_PARENT_CHARS = 12000
MIN_OCR_CONFIDENCE = 40.0
MAX_FRONT_MATTER_CHARS = 3000
NEAR_DUPLICATE_JACCARD = 0.9

ORDINALS = (
    "FIRST SECOND THIRD FOURTH FIFTH SIXTH SEVENTH EIGHTH NINTH TENTH ELEVENTH TWELFTH "
    "THIRTEENTH FOURTEENTH FIFTEENTH SIXTEENTH SEVENTEENTH EIGHTEENTH NINETEENTH TWENTIETH"
).split()

SECTION_RE = re.compile(
    r"^[ \t]*(?:\d{1,3}\s*\[\s*)?(?P<num>\d{1,3}[A-Z]{0,4})[.,](?:[ \t]*\n[ \t]*|[ \t]+)"
    r"(?P<title>[A-Z\[(\"'][^\n]{1,250}?(?:\n[^\n]{1,200}?)?)"
    r"[ \t]*(?:\.[ \t]*[-\u2013\u2014]+|:[ \t]+[\u2013\u2014]+)",
    re.MULTILINE,
)
STRUCTURE_RE = re.compile(
    r"^[ \t]*(?P<kind>PART|CHAPTER)[ \t]*[-\u2013\u2014]?[ \t]*"
    r"(?P<num>[IVXLC]+(?:-[A-Z])?|\d{1,2}[A-Z]?)\b[ \t]*(?P<rest>[^\n]*)",
    re.MULTILINE,
)
SCHEDULE_RE = re.compile(
    rf"^[ \t]*(?:THE[ \t]+)?(?P<ord>{'|'.join(ORDINALS)})[ \t]+SCHEDULE\b[^\n]*", re.MULTILINE
)
LABEL_ONLY_RE = re.compile(r"^\s*(?:\d{0,3}\[)?\(?(?:[ivxlc]+|[a-z]{1,2}|\d{1,3}[A-Z]?)\)\s*$")
PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s*)?[-\u2013]?\s*\d{1,4}\s*[-\u2013]?\s*$", re.IGNORECASE)
FOOTNOTE_MARK_RE = re.compile(r"\d{1,3}\s*\[|\]")

UNIT_NAMES = {
    "act": "Section",
    "finance_act": "Section",
    "ordinance": "Section",
    "rules": "Rule",
    "sro": "Rule",
    "regulations": "Regulation",
}


@dataclass
class Section:
    parent_id: str
    section: str
    section_title: str
    path: list[str]
    page_start: int
    page_end: int
    text: str


FEDERAL_AUTHORITIES = {"FBR", "SECP", "Ministry of Finance"}


@dataclass
class Chunk:
    chunk_id: str
    parent_id: str
    section: str
    section_title: str
    header: str
    page_start: int
    page_end: int
    text: str
    ocr: bool = False
    doc_id: str = ""
    doc_title: str = ""
    amended_upto: str = ""
    tax_years: list[str] = field(default_factory=list)
    jurisdiction: str = ""


@dataclass
class Report:
    pages_used: int = 0
    pages_dropped: int = 0
    front_matter_dropped: int = 0
    exact_duplicates: int = 0
    near_duplicates: int = 0
    notes: list[str] = field(default_factory=list)


# ---------- page cleaning ----------


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\ufffd", "-")
    text = re.sub(r"_{3,}", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.rstrip() for line in text.splitlines())


def edge_key(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def edge_lines(lines: list[str], n: int = 2) -> list[int]:
    filled = [i for i, line in enumerate(lines) if line.strip()]
    return sorted(set(filled[:n] + filled[-n:]))


def strip_boilerplate(pages: list[list[str]]) -> list[list[str]]:
    """Remove running headers, footers and page numbers that repeat across pages."""
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update({edge_key(lines[i]) for i in edge_lines(lines)})
    threshold = max(3, int(0.02 * len(pages)))
    repeated = {
        key
        for key, c in counts.items()
        if c >= threshold and key.strip("# ") and len(key) <= 100 and not LABEL_ONLY_RE.match(key)
    }
    cleaned = []
    for lines in pages:
        drop = {
            i
            for i in edge_lines(lines)
            if edge_key(lines[i]) in repeated or PAGE_NUMBER_RE.match(lines[i])
        }
        cleaned.append([line for i, line in enumerate(lines) if i not in drop])
    return cleaned


GLUED_RULE_LINE = re.compile(r"^([ \t]*)(\d+[A-Z]{0,4})([.,].*)$")
GLUED_BRACKET_LINE = re.compile(r"^([ \t]*)(\d{1,3})\[([A-Z].*)$")
TITLE_DASH_RE = re.compile(r"[.:][ \t]*[-\u2013\u2014]{1,2}")
RULE_ID_RE = re.compile(r"\d{1,3}[A-Z]{0,4}")

# pymupdf4llm wraps these column names across cell borders. Each pair keeps the same cell count.
RATE_HEADER_REPAIRS = (
    (
        "**Non-ATL Rates**<br>**L**|**ate Filer**|**Rates**<br>**Reference for Rates**",
        "**Non-ATL Rates**|**Late Filer Rates**|**Reference for Rates**",
    ),
    (
        "**Late Filer Rate**|**s**<br>**Reference for Rates**",
        "**Late Filer Rates**|**Reference for Rates**",
    ),
    (
        "**Non-ATL Rates**<br>**Late Fi**|**ler Rates**<br>**Reference for Rates**",
        "**Non-ATL Rates**|**Late Filer Rates**<br>**Reference for Rates**",
    ),
    (
        "**Non-ATL Rates**<br>**Late F**|**iler Rates**<br>**Reference for Rates**",
        "**Non-ATL Rates**|**Late Filer Rates**<br>**Reference for Rates**",
    ),
    (
        "**Late Filer Rat**|**es**<br>**Reference for Rates**",
        "**Late Filer Rates**|**Reference for Rates**",
    ),
    (
        "**Late Filer Rates**|<br>**Reference for Rates**",
        "**Late Filer Rates**|**Reference for Rates**",
    ),
)


def footnote_ids(lines: list[str]) -> set[str]:
    return {line.strip() for line in lines if re.fullmatch(r"\d{1,3}", line.strip())}


def unglue_rule_token(token: str, notes: set[str]) -> str:
    """8612B is footnote 86 plus rule 12B. 150H is a real rule and stays whole."""
    if RULE_ID_RE.fullmatch(token):
        return token
    for size in (3, 2, 1):
        if len(token) <= size:
            continue
        prefix, rest = token[:size], token[size:]
        if prefix in notes and RULE_ID_RE.fullmatch(rest):
            return rest
    return token


def detach_footnote_prefixes(lines: list[str]) -> list[str]:
    """Pull a page footnote off a rule number or a bracketed heading."""
    notes = footnote_ids(lines)
    if not notes:
        return lines
    out: list[str] = []
    for line in lines:
        rule = GLUED_RULE_LINE.match(line)
        if rule:
            token = unglue_rule_token(rule.group(2), notes)
            if token != rule.group(2):
                out.append(f"{rule.group(1)}{token}{rule.group(3)}")
                continue
        bracket = GLUED_BRACKET_LINE.match(line)
        if bracket and bracket.group(2) in notes:
            rest = bracket.group(3)
            if re.match(r"(CHAPTER|PART)\b", rest):
                out.append(f"{bracket.group(1)}{rest}")
                continue
            if TITLE_DASH_RE.search(rest[:120]):
                out.append(f"{bracket.group(1)}[{rest}")
                continue
        out.append(line)
    return out


def repair_rate_header_line(line: str) -> str:
    for broken, fixed in RATE_HEADER_REPAIRS:
        if broken in line:
            line = line.replace(broken, fixed)
    return line


def repair_table_headers(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("|") and "Section" in line and "ATL" in line:
            line = repair_rate_header_line(line)
        lines.append(line)
    return "\n".join(lines)


def join_labels(lines: list[str]) -> list[str]:
    """Put clause labels like "(a)" back on the same line as their text."""
    out: list[str] = []
    pending = ""
    for line in lines:
        if LABEL_ONLY_RE.match(line):
            pending = f"{pending}{line.strip()} "
            continue
        if pending and line.strip():
            out.append(pending + line.strip())
            pending = ""
        elif not pending:
            out.append(line)
    if pending:
        out.append(pending.strip())
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip().splitlines()


# ---------- structure ----------


@dataclass
class Heading:
    start: int
    kind: str  # section | part | chapter | schedule
    num: str
    title: str


def clean_title(title: str) -> str:
    title = title.lstrip("[")
    title = FOOTNOTE_MARK_RE.sub("", title)
    return re.sub(r"\s+", " ", title).strip(" .-\u2013\u2014")


def find_headings(text: str) -> list[Heading]:
    headings = [
        Heading(m.start(), "section", m["num"], clean_title(m["title"]))
        for m in SECTION_RE.finditer(text)
    ]
    for m in STRUCTURE_RE.finditer(text):
        rest = m["rest"].strip(" .-\u2013\u2014")
        if rest and not rest.isupper():
            continue  # a sentence that starts with "Part", not a heading
        if not rest:
            following = text[m.end() :].lstrip("\n").split("\n", 1)[0].strip()
            rest = following if following.isupper() and len(following) < 120 else ""
        headings.append(Heading(m.start(), m["kind"].lower(), m["num"], clean_title(rest)))
    for m in SCHEDULE_RE.finditer(text):
        ordinal = ORDINALS.index(m["ord"]) + 1
        headings.append(Heading(m.start(), "schedule", str(ordinal), clean_title(m.group(0))))
    return sorted(headings, key=lambda h: h.start)


def page_at(offsets: list[int], pages: list[int], position: int) -> int:
    return pages[max(0, bisect_right(offsets, position) - 1)]


def unit_label(entry: CatalogEntry) -> str:
    return UNIT_NAMES.get(entry.doc_type, "Section")


def build_sections(
    entry: CatalogEntry, text: str, offsets: list[int], pages: list[int], report: Report
) -> list[Section]:
    headings = find_headings(text)
    first_section = next((h for h in headings if h.kind == "section"), None)
    if first_section is None:
        return page_sections(entry, text, offsets, pages)

    sections: list[Section] = []
    if first_section.start > MAX_FRONT_MATTER_CHARS:
        report.front_matter_dropped = first_section.start  # cover and table of contents
    elif text[: first_section.start].strip():
        sections.append(
            make_section(
                entry, "s0", "", "Preamble", [], text, 0, first_section.start, offsets, pages
            )
        )
    headings = [h for h in headings if h.start >= first_section.start]

    structure: dict[str, str] = {}
    schedule: str | None = None
    seen: Counter[str] = Counter()
    last_key: str | None = None
    last_start = 0
    for i, h in enumerate(headings):
        end = headings[i + 1].start if i + 1 < len(headings) else len(text)
        if h.kind == "schedule":
            schedule = f"sch{h.num}"
            structure = {"schedule": h.title.title()}
            key, section, title = schedule, "", h.title.title()
        elif h.kind in {"part", "chapter"}:
            if h.kind == "part":
                structure.pop("chapter", None)
            name = f"{h.kind.title()} {h.num}" + (f" {h.title.title()}" if h.title else "")
            structure[h.kind] = name
            if schedule is None:
                continue  # in the main text, parts and chapters only label later sections
            key, section, title = f"{schedule}:p{h.num}", "", name
        else:
            key = f"{schedule}:s{h.num}" if schedule else f"s{h.num}"
            section, title = h.num, h.title

        if key == last_key:  # a heading repeated at a page top: continue the same parent
            sections[-1].text = text[last_start:end].strip()
            sections[-1].page_end = page_at(offsets, pages, end - 1)
            continue
        last_start = h.start
        last_key = key
        seen[key] += 1
        unique = key if seen[key] == 1 else f"{key}~{seen[key]}"
        path = [structure[k] for k in ("schedule", "part", "chapter") if k in structure]
        if h.kind != "section":
            path = path[:-1] if path and path[-1] == title else path
        sections.append(
            make_section(entry, unique, section, title, path, text, h.start, end, offsets, pages)
        )
    return split_large([s for s in sections if s.text])


def make_section(entry, key, section, title, path, text, start, end, offsets, pages) -> Section:
    return Section(
        parent_id=f"{entry.doc_id}:{key}",
        section=section,
        section_title=title,
        path=list(path),
        page_start=page_at(offsets, pages, start),
        page_end=page_at(offsets, pages, max(start, end - 1)),
        text=text[start:end].strip(),
    )


def page_sections(entry, text, offsets, pages) -> list[Section]:
    out = []
    for i, start in enumerate(offsets):
        end = offsets[i + 1] if i + 1 < len(offsets) else len(text)
        body = text[start:end].strip()
        if body:
            out.append(
                Section(
                    f"{entry.doc_id}:p{pages[i]}",
                    "",
                    f"Page {pages[i]}",
                    [],
                    pages[i],
                    pages[i],
                    body,
                )
            )
    return out


def split_large(sections: list[Section]) -> list[Section]:
    """Very long parents (big schedules) are split so expansion stays within budget."""
    out: list[Section] = []
    for s in sections:
        if len(s.text) <= MAX_PARENT_CHARS:
            out.append(s)
            continue
        for k, part in enumerate(split_text(s.text, MAX_PARENT_CHARS * 2 // 3, 0), start=1):
            out.append(
                Section(
                    f"{s.parent_id}:{k}",
                    s.section,
                    s.section_title,
                    s.path,
                    s.page_start,
                    s.page_end,
                    part,
                )
            )
    return out


# ---------- chunking ----------


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split on paragraph, then line, then sentence, then word boundaries."""
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", "; ", " "):
                cut = window.rfind(sep)
                if cut > size // 2:
                    end = start + cut + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = max(end - overlap, start + 1)
        if overlap:
            boundary = text.find("\n", next_start, end)
            if boundary == -1:
                boundary = text.find(" ", next_start, end)
            next_start = boundary + 1 if boundary != -1 else next_start
        start = next_start
    return pieces


def jurisdiction_for(entry: CatalogEntry) -> str:
    if entry.authority in FEDERAL_AUTHORITIES:
        return "federal"
    return "provincial"


def section_label(entry: CatalogEntry, s: Section) -> str:
    if s.section:
        unit = unit_label(entry)
        label = f"{unit} {s.section}"
        return f"{label} {s.section_title}".strip()
    return s.section_title


def short_title(entry: CatalogEntry) -> str:
    return re.sub(r"\s*\(.*?\)\s*$", "", entry.title)


TABLE_HEADER_RE = re.compile(r"^(\|.*\|)\n(\|[-| :]+\|)$", re.MULTILINE)


def with_table_header(piece: str, section_text: str) -> str:
    """Rows of a split markdown table keep their column names."""
    match = TABLE_HEADER_RE.search(section_text)
    if match and piece.lstrip().startswith("|") and match.group(0) not in piece:
        return f"{match.group(0)}\n{piece}"
    return piece


def chunk_section(
    entry: CatalogEntry, s: Section, page_texts: dict[int, str], ocr_pages: set[int]
) -> list[Chunk]:
    header = " > ".join([short_title(entry), *s.path, section_label(entry, s)])
    chunks = []
    for i, raw_piece in enumerate(split_text(s.text, CHUNK_CHARS, CHUNK_OVERLAP)):
        first, last = locate(raw_piece, s, page_texts)
        piece = with_table_header(raw_piece, s.text)
        chunks.append(
            Chunk(
                chunk_id=f"{s.parent_id}:c{i}",
                parent_id=s.parent_id,
                section=s.section,
                section_title=s.section_title,
                header=header,
                page_start=first,
                page_end=last,
                text=piece,
                ocr=any(p in ocr_pages for p in range(first, last + 1)),
                doc_id=entry.doc_id,
                doc_title=entry.title,
                amended_upto=entry.amended_upto,
                tax_years=entry.tax_year_list,
                jurisdiction=jurisdiction_for(entry),
            )
        )
    return chunks


def locate(piece: str, s: Section, page_texts: dict[int, str]) -> tuple[int, int]:
    """Find the pages a chunk starts and ends on, within its section's page range."""
    head, tail = piece[:60], piece[-60:]
    first = last = None
    for p in range(s.page_start, s.page_end + 1):
        body = page_texts.get(p, "")
        if first is None and head in body:
            first = p
        if tail in body:
            last = p
    first = first or s.page_start
    return first, max(first, last or first)


# ---------- dedupe ----------


def fingerprint(text: str) -> str:
    return hashlib.sha256(re.sub(r"\W+", " ", text.lower()).strip().encode()).hexdigest()


def minhash(text: str) -> MinHash:
    words = re.findall(r"\w+", text.lower())
    m = MinHash(num_perm=64)
    for i in range(max(1, len(words) - 4)):
        m.update(" ".join(words[i : i + 5]).encode())
    return m


def dedupe(chunks: list[Chunk], report: Report) -> list[Chunk]:
    seen: set[str] = set()
    lsh = MinHashLSH(threshold=NEAR_DUPLICATE_JACCARD, num_perm=64)
    kept: list[Chunk] = []
    for c in chunks:
        fp = fingerprint(c.text)
        if fp in seen:
            report.exact_duplicates += 1
            continue
        seen.add(fp)
        if len(c.text) >= 300:
            m = minhash(c.text)
            if lsh.query(m):
                report.near_duplicates += 1
                continue
            lsh.insert(c.chunk_id, m)
        kept.append(c)
    return kept


# ---------- driver ----------


def load_pages(entry: CatalogEntry, data_dir: Path, report: Report) -> list[tuple[int, str, bool]]:
    extracted = json.loads((data_dir / "extracted" / f"{entry.doc_id}.json").read_text("utf-8"))
    if extracted["sha256"] != entry.sha256:
        raise ValueError(f"{entry.doc_id}: extraction is stale, rerun pipeline.extract")
    kept = []
    for p in extracted["pages"]:
        conf = p.get("ocr_confidence")
        is_ocr = p["method"] == "ocr"
        if not p["text"].strip() or (is_ocr and (conf is None or conf < MIN_OCR_CONFIDENCE)):
            report.pages_dropped += 1
            continue
        kept.append((p["page"], normalize(p["text"]), is_ocr))
    report.pages_used = len(kept)
    return kept


def process(entry: CatalogEntry, data_dir: Path = DATA_DIR) -> tuple[dict, Report]:
    report = Report()
    raw = load_pages(entry, data_dir, report)
    cleaned = strip_boilerplate([text.splitlines() for _, text, _ in raw])
    cleaned = [detach_footnote_prefixes(lines) for lines in cleaned]
    page_numbers = [page for page, _, _ in raw]
    ocr_pages = {page for page, _, is_ocr in raw if is_ocr}

    texts = [repair_table_headers("\n".join(join_labels(lines))) for lines in cleaned]
    offsets, position = [], 0
    for t in texts:
        offsets.append(position)
        position += len(t) + 2
    full = "\n\n".join(texts)
    page_texts = dict(zip(page_numbers, texts, strict=True))

    sections = build_sections(entry, full, offsets, page_numbers, report)
    chunks = [c for s in sections for c in chunk_section(entry, s, page_texts, ocr_pages)]
    chunks = dedupe(chunks, report)
    live_parents = {c.parent_id for c in chunks}
    payload = {
        "doc_id": entry.doc_id,
        "sha256": entry.sha256,
        "version": CHUNK_VERSION,
        "sections": [asdict(s) for s in sections if s.parent_id in live_parents],
        "chunks": [asdict(c) for c in chunks],
    }
    return payload, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", action="append", help="only this doc_id (repeatable)")
    args = parser.parse_args(argv)

    entries = [e for e in read_catalog(CATALOG_PATH) if e.searchable]
    if args.doc:
        entries = [e for e in entries if e.doc_id in set(args.doc)]
    out_dir = DATA_DIR / "chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for entry in entries:
        payload, r = process(entry)
        (out_dir / f"{entry.doc_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        n = len(payload["chunks"])
        total += n
        print(
            f"{entry.doc_id:45} sections={len(payload['sections']):5} chunks={n:6} "
            f"pages={r.pages_used} dropped_pages={r.pages_dropped} "
            f"front_matter={r.front_matter_dropped} dup={r.exact_duplicates}+{r.near_duplicates}"
            + (f" {'; '.join(r.notes)}" if r.notes else ""),
            flush=True,
        )
    print(f"total chunks {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
