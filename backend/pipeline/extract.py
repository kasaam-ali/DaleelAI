"""Extract page text from active catalog documents into data/extracted/<doc_id>.json.

Run inside the backend container:
    docker compose run --rm --no-deps backend python -m pipeline.extract
        [--doc DOC_ID] [--only-missing] [--ocr] [--dpi 200] [--force]

OCR is off unless --ocr is set. With --ocr, Tesseract runs only on pages whose text
layer has fewer than 20 characters and that contain an image. Blank pages are skipped.
Each OCR page has a 30 second timeout; a timeout or error marks that page ocr_failed
and the run continues. A partial file is written as each page finishes, so a rerun
skips pages already saved. Rate cards (doc_type "guide") still use pymupdf4llm.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from pipeline.catalog import CATALOG_PATH, DATA_DIR, CatalogEntry, read_catalog

OCR_MIN_CHARS = 20
CLASS_MIN_CHARS = 150
OCR_TIMEOUT_S = 30
DEFAULT_DPI = 200
EXTRACT_VERSION = 1

REPORT_KEYS = (
    "total_pages",
    "text_layer_pages",
    "ocr_pages",
    "ocr_failed_pages",
    "empty_pages",
)


@dataclass
class Page:
    page: int
    text: str
    method: str  # text | markdown | ocr | ocr_failed | empty
    ocr_confidence: float | None = None
    page_class: str = ""  # digital | scanned | blank, from the text layer before OCR


def page_kind(text: str, has_image: bool) -> str:
    """digital if the text is long enough, else scanned when the page has an image, else blank."""
    if len(text.strip()) >= CLASS_MIN_CHARS:
        return "digital"
    if has_image:
        return "scanned"
    return "blank"


def page_ranges(numbers: list[int]) -> str:
    if not numbers:
        return ""
    ranges: list[str] = []
    start = prev = numbers[0]
    for number in numbers[1:]:
        if number == prev + 1:
            prev = number
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = number
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(ranges)


def should_ocr(text: str, has_image: bool) -> bool:
    return len(text.strip()) < OCR_MIN_CHARS and has_image


def page_has_image(page: pymupdf.Page) -> bool:
    return bool(page.get_images())


def report_for(pages: list[Page]) -> dict:
    counts: dict = {key: 0 for key in REPORT_KEYS}
    counts["total_pages"] = len(pages)
    scanned: list[int] = []
    for page in pages:
        if page.method == "ocr_failed":
            counts["ocr_failed_pages"] += 1
        elif page.method == "ocr":
            counts["ocr_pages"] += 1
        elif len(page.text.strip()) < OCR_MIN_CHARS:
            counts["empty_pages"] += 1
        else:
            counts["text_layer_pages"] += 1
        kind = page.page_class or page_kind(page.text, False)
        counts[f"{kind}_pages"] = counts.get(f"{kind}_pages", 0) + 1
        if kind == "scanned":
            scanned.append(page.page)
    for kind in ("digital", "scanned", "blank"):
        counts.setdefault(f"{kind}_pages", 0)
    counts["scanned_ranges"] = page_ranges(scanned)
    return counts


def ocr_lines(data: dict) -> tuple[str, float | None]:
    """Rebuild text from Tesseract word boxes, keeping line and paragraph breaks."""
    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        conf = float(data["conf"][i])
        if conf >= 0:
            confidences.append(conf)
    out: list[str] = []
    previous: tuple[int, int] | None = None
    for (block, par, _), words in lines.items():
        if previous is not None and previous != (block, par):
            out.append("")
        out.append(" ".join(words))
        previous = (block, par)
    mean = round(sum(confidences) / len(confidences), 1) if confidences else None
    return "\n".join(out), mean


def ocr_page(path: Path, page_no: int, dpi: int) -> tuple[str, float | None]:
    with pymupdf.open(path) as doc:
        pix = doc[page_no - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    data = pytesseract.image_to_data(
        image,
        lang="eng",
        output_type=pytesseract.Output.DICT,
        timeout=OCR_TIMEOUT_S,
    )
    return ocr_lines(data)


def extract_markdown(path: Path) -> list[Page]:
    import pymupdf4llm

    chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True, show_progress=False)
    return [
        Page(page=i + 1, text=chunk["text"], method="markdown") for i, chunk in enumerate(chunks)
    ]


def extract_text_layer(path: Path) -> list[Page]:
    with pymupdf.open(path) as doc:
        return [
            Page(page=i + 1, text=page.get_text("text"), method="text")
            for i, page in enumerate(doc)
        ]


def _read_page(pdf_page: pymupdf.Page, page_no: int, markdown: dict[int, str]) -> Page:
    if page_no in markdown:
        text = markdown[page_no]
        method = "empty" if len(text.strip()) < OCR_MIN_CHARS else "markdown"
        return Page(page=page_no, text=text, method=method)
    text = pdf_page.get_text("text")
    method = "empty" if len(text.strip()) < OCR_MIN_CHARS else "text"
    return Page(page=page_no, text=text, method=method)


def extract_pdf(
    path: Path,
    *,
    ocr: bool,
    dpi: int,
    done: dict[int, Page],
    doc_type: str = "act",
    label: str = "",
    on_page: Callable[[list[Page]], None] | None = None,
) -> list[Page]:
    """Read one PDF. Pages present in done are kept as-is so a rerun can resume."""
    with pymupdf.open(path) as doc:
        total = doc.page_count
        missing = [i + 1 for i in range(total) if (i + 1) not in done]
    markdown: dict[int, str] = {}
    if doc_type == "guide" and missing:
        markdown = {page.page: page.text for page in extract_markdown(path)}

    pages: list[Page] = []
    with pymupdf.open(path) as doc:
        total = doc.page_count
        for index in range(total):
            page_no = index + 1
            if page_no in done:
                pages.append(done[page_no])
            else:
                try:
                    has_image = page_has_image(doc[index])
                    page = _read_page(doc[index], page_no, markdown)
                    kind = page_kind(page.text, has_image)
                    page.page_class = kind
                    if ocr and should_ocr(page.text, has_image):
                        try:
                            text, conf = ocr_page(path, page_no, dpi)
                            page = Page(
                                page=page_no,
                                text=text,
                                method="ocr",
                                ocr_confidence=conf,
                                page_class=kind,
                            )
                        except Exception as exc:
                            print(f"ocr_failed {label} page {page_no}: {exc}", flush=True)
                            page = Page(
                                page=page_no,
                                text=page.text,
                                method="ocr_failed",
                                page_class=kind,
                            )
                except Exception as exc:
                    print(f"page failed {label} page {page_no}: {exc}", flush=True)
                    page = Page(
                        page=page_no,
                        text="",
                        method="ocr_failed" if ocr else "empty",
                        page_class="blank",
                    )
                pages.append(page)
                if on_page is not None:
                    on_page(pages)
            if page_no % 25 == 0:
                print(f"{label} page {page_no}", flush=True)
    return pages


def output_path(entry: CatalogEntry, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / "extracted" / f"{entry.doc_id}.json"


def partial_path(out: Path) -> Path:
    return out.with_name(out.stem + ".partial.json")


def document_payload(entry: CatalogEntry, pages: list[Page], *, complete: bool) -> dict:
    payload = {
        "doc_id": entry.doc_id,
        "sha256": entry.sha256,
        "version": EXTRACT_VERSION,
        "pages": [asdict(page) for page in pages],
    }
    if complete:
        payload["report"] = report_for(pages)
    return payload


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def is_current(entry: CatalogEntry, out: Path) -> bool:
    if not out.exists():
        return False
    cached = json.loads(out.read_text(encoding="utf-8"))
    return cached.get("sha256") == entry.sha256 and cached.get("version") == EXTRACT_VERSION


def load_partial(entry: CatalogEntry, path: Path) -> dict[int, Page]:
    if not path.exists():
        return {}
    cached = json.loads(path.read_text(encoding="utf-8"))
    if cached.get("sha256") != entry.sha256 or cached.get("version") != EXTRACT_VERSION:
        return {}
    done: dict[int, Page] = {}
    for raw in cached.get("pages", []):
        done[raw["page"]] = Page(
            page=raw["page"],
            text=raw.get("text", ""),
            method=raw.get("method", "text"),
            ocr_confidence=raw.get("ocr_confidence"),
            page_class=raw.get("page_class", ""),
        )
    return done


def save(entry: CatalogEntry, pages: list[Page], out: Path) -> None:
    atomic_write(out, document_payload(entry, pages, complete=True))


def classify_saved(entry: CatalogEntry, data_dir: Path = DATA_DIR) -> dict:
    """Classify an already extracted PDF. Reads the PDF for images and does not write data/."""
    extracted = json.loads(output_path(entry, data_dir).read_text(encoding="utf-8"))
    texts = {raw["page"]: raw.get("text", "") for raw in extracted.get("pages", [])}
    scanned: list[int] = []
    counts = {"total": 0, "digital": 0, "scanned": 0, "blank": 0}
    with pymupdf.open(entry.path(data_dir)) as doc:
        for index, pdf_page in enumerate(doc):
            page_no = index + 1
            kind = page_kind(texts.get(page_no, ""), page_has_image(pdf_page))
            counts["total"] += 1
            counts[kind] += 1
            if kind == "scanned":
                scanned.append(page_no)
    total = counts["total"]
    counts["scanned_pct"] = round(100 * counts["scanned"] / total, 1) if total else 0.0
    counts["scanned_ranges"] = page_ranges(scanned)
    return counts


def report_from_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    stored = data.get("report")
    if isinstance(stored, dict) and all(key in stored for key in REPORT_KEYS):
        return {key: int(stored[key]) for key in REPORT_KEYS}
    pages = [
        Page(
            page=raw["page"],
            text=raw.get("text", ""),
            method=raw.get("method", "text"),
            ocr_confidence=raw.get("ocr_confidence"),
        )
        for raw in data.get("pages", [])
    ]
    return report_for(pages)


def print_summary(rows: list[dict]) -> None:
    print(
        f"{'document':<48} {'total':>5} {'text':>5} {'ocr':>5} "
        f"{'ocr_failed':>10} {'empty':>5}  status",
        flush=True,
    )
    for row in rows:
        print(
            f"{row['doc_id']:<48} {row['total_pages']:>5} {row['text_layer_pages']:>5} "
            f"{row['ocr_pages']:>5} {row['ocr_failed_pages']:>10} {row['empty_pages']:>5}  "
            f"{row['status']}",
            flush=True,
        )


def _zero_report() -> dict[str, int]:
    return {key: 0 for key in REPORT_KEYS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", action="append", help="only this doc_id (repeatable)")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="skip documents that already have data/extracted/<doc_id>.json",
    )
    parser.add_argument("--ocr", action="store_true", help="OCR short pages that contain an image")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="OCR render dpi (default 200)")
    parser.add_argument("--force", action="store_true", help="ignore finished output and partials")
    parser.add_argument(
        "--classify",
        action="store_true",
        help="classify saved text against PDF images; do not write or run OCR",
    )
    args = parser.parse_args(argv)

    entries = [entry for entry in read_catalog(CATALOG_PATH) if entry.searchable]
    if args.doc:
        wanted = set(args.doc)
        found = {entry.doc_id for entry in entries}
        for doc_id in args.doc:
            if doc_id not in found:
                print(f"not in active catalog: {doc_id}", flush=True)
        entries = [entry for entry in entries if entry.doc_id in wanted]
    print(f"{len(entries)} documents selected", flush=True)
    if args.classify:
        print(
            f"{'document':<48} {'total':>5} {'digital':>7} {'scanned':>7} "
            f"{'blank':>5} {'scan%':>6}  ranges",
            flush=True,
        )
        for entry in entries:
            try:
                counts = classify_saved(entry)
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                print(f"{entry.doc_id:<48} failed: {exc}", flush=True)
                continue
            print(
                f"{entry.doc_id:<48} {counts['total']:>5} {counts['digital']:>7} "
                f"{counts['scanned']:>7} {counts['blank']:>5} {counts['scanned_pct']:>5.1f}%  "
                f"{counts['scanned_ranges']}",
                flush=True,
            )
        return 0

    rows: list[dict] = []
    for entry in entries:
        out = output_path(entry)
        part = partial_path(out)
        if not args.force and ((args.only_missing and out.exists()) or is_current(entry, out)):
            try:
                report = report_from_file(out)
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                print(f"skipped {entry.doc_id}: unreadable output ({exc})", flush=True)
                report = _zero_report()
            rows.append({"doc_id": entry.doc_id, "status": "skipped", **report})
            continue

        if args.force:
            part.unlink(missing_ok=True)
            done: dict[int, Page] = {}
        else:
            done = load_partial(entry, part)
        print(f"extracting {entry.doc_id}: {len(done)} pages already saved", flush=True)
        started = time.monotonic()

        def on_page(
            pages: list[Page],
            entry: CatalogEntry = entry,
            part: Path = part,
        ) -> None:
            atomic_write(part, document_payload(entry, pages, complete=False))

        try:
            pages = extract_pdf(
                entry.path(),
                ocr=args.ocr,
                dpi=args.dpi,
                done=done,
                doc_type=entry.doc_type,
                label=entry.doc_id,
                on_page=on_page,
            )
        except Exception as exc:
            print(f"failed {entry.doc_id}: {exc}", flush=True)
            rows.append({"doc_id": entry.doc_id, "status": "failed", **_zero_report()})
            continue

        save(entry, pages, out)
        part.unlink(missing_ok=True)
        report = report_for(pages)
        rows.append({"doc_id": entry.doc_id, "status": "saved", **report})
        print(f"saved {entry.doc_id} in {time.monotonic() - started:.0f}s", flush=True)

    print_summary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
