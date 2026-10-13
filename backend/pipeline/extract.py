"""Extract page text from active catalog documents into data/extracted/<doc_id>.json.

Run inside the backend container:
    docker compose run --rm --no-deps backend python -m pipeline.extract
        [--doc DOC_ID] [--only-missing] [--ocr] [--dpi 200] [--force]

OCR is off unless --ocr is set. With --ocr, Tesseract runs only on pages whose text
layer has fewer than 20 characters and that contain an image. --ocr-scanned instead
reads an existing extraction and OCRs pages in a range whose text is under 150
characters and that contain an image. Blank pages are skipped.
Each OCR page has a 30 second timeout; a timeout or error marks that page ocr_failed
and the run continues. A partial file is written as each page finishes, so a rerun
skips pages already saved. Rate cards (doc_type "guide") still use pymupdf4llm.
"""

import argparse
import json
import random
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
OCR_BUDGET_S = 45 * 60
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
    source: str = ""  # "ocr" when the stored text came from Tesseract


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
                                source="ocr",
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
        done[raw["page"]] = _page_from_raw(raw)
    return done


def apply_ocr_success(page: Page, text: str, confidence: float | None) -> Page:
    return Page(
        page=page.page,
        text=text,
        method="ocr",
        ocr_confidence=confidence,
        page_class=page.page_class or "scanned",
        source="ocr",
    )


def apply_ocr_failure(page: Page) -> Page:
    return Page(
        page=page.page,
        text=page.text,
        method="ocr_failed",
        ocr_confidence=None,
        page_class=page.page_class or "scanned",
        source="",
    )


def projected_over_budget(elapsed: float, finished: int, remaining: int, budget_s: float) -> bool:
    """True when the finished pages imply the rest would pass the time budget.

    The first four pages are too few to judge the rate. Elapsed time past the
    budget still stops the run immediately.
    """
    if remaining < 1:
        return False
    if elapsed > budget_s:
        return True
    if finished < 5:
        return False
    average = elapsed / finished
    return elapsed + average * remaining > budget_s


def _page_from_raw(raw: dict) -> Page:
    return Page(
        page=raw["page"],
        text=raw.get("text", ""),
        method=raw.get("method", "text"),
        ocr_confidence=raw.get("ocr_confidence"),
        page_class=raw.get("page_class", ""),
        source=raw.get("source", ""),
    )


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


def scanned_page_numbers(
    pages: list[Page], images: dict[int, bool], start: int, end: int
) -> list[int]:
    """Pages in the range that are scanned and do not already have an OCR result."""
    found: list[int] = []
    for page in pages:
        if page.page < start or page.page > end:
            continue
        if page.source == "ocr" or page.method in {"ocr", "ocr_failed"}:
            continue
        kind = page.page_class or page_kind(page.text, images.get(page.page, False))
        if kind == "scanned":
            found.append(page.page)
    return found


def _read_ocr_partial(entry: CatalogEntry, path: Path) -> tuple[dict[int, Page], dict[int, float]]:
    """Load an OCR resume file. A partial from a different job is refused."""
    if not path.exists():
        return {}, {}
    cached = json.loads(path.read_text(encoding="utf-8"))
    if cached.get("purpose") != "ocr-scanned":
        raise ValueError(f"{path.name} is not an OCR resume file")
    if cached.get("sha256") != entry.sha256 or cached.get("version") != EXTRACT_VERSION:
        return {}, {}
    done = {raw["page"]: _page_from_raw(raw) for raw in cached.get("pages", [])}
    seconds = {int(number): float(value) for number, value in cached.get("seconds", {}).items()}
    return done, seconds


def _write_ocr_partial(
    path: Path,
    entry: CatalogEntry,
    pages: dict[int, Page],
    seconds: dict[int, float],
) -> None:
    ordered = [pages[number] for number in sorted(pages)]
    atomic_write(
        path,
        {
            "doc_id": entry.doc_id,
            "sha256": entry.sha256,
            "version": EXTRACT_VERSION,
            "purpose": "ocr-scanned",
            "pages": [asdict(page) for page in ordered],
            "seconds": {str(number): seconds[number] for number in sorted(seconds)},
        },
    )


def ocr_scanned_range(
    entry: CatalogEntry,
    *,
    start: int,
    end: int,
    dpi: int = DEFAULT_DPI,
    budget_s: float = OCR_BUDGET_S,
    data_dir: Path = DATA_DIR,
) -> dict:
    """OCR scanned pages in a page range and merge them into the saved extraction.

    A page is scanned when its stored text is under 150 characters and the PDF
    page has an image. The 20-character OCR gate is not used here. Successful
    text is marked source "ocr". A timeout marks ocr_failed and the run continues.
    """
    out = output_path(entry, data_dir)
    saved = json.loads(out.read_text(encoding="utf-8"))
    if saved.get("sha256") != entry.sha256:
        raise ValueError(f"{entry.doc_id}: extraction is stale")
    by_no = {raw["page"]: _page_from_raw(raw) for raw in saved.get("pages", [])}
    part = partial_path(out)
    resumed, seconds = _read_ocr_partial(entry, part)
    by_no.update(resumed)

    pdf_path = entry.path(data_dir)
    images: dict[int, bool] = {}
    with pymupdf.open(pdf_path) as doc:
        for number in range(start, end + 1):
            if 1 <= number <= doc.page_count:
                images[number] = page_has_image(doc[number - 1])
    ordered = [by_no[number] for number in sorted(by_no)]
    targets = scanned_page_numbers(ordered, images, start, end)
    print(
        f"{entry.doc_id}: {len(targets)} scanned pages to OCR in {start}-{end}, "
        f"{len(resumed)} already in the resume file",
        flush=True,
    )

    finished = 0
    failed = 0
    started = time.monotonic()
    stopped = False
    for index, number in enumerate(targets):
        elapsed = time.monotonic() - started
        remaining = len(targets) - index
        if projected_over_budget(elapsed, finished, remaining, budget_s):
            stopped = True
            print(
                f"stopping {entry.doc_id}: projected time exceeds {budget_s:.0f}s "
                f"after {finished} pages",
                flush=True,
            )
            break
        current = by_no[number]
        current = Page(
            page=current.page,
            text=current.text,
            method=current.method,
            ocr_confidence=current.ocr_confidence,
            page_class="scanned",
            source=current.source,
        )
        t0 = time.monotonic()
        try:
            text, confidence = ocr_page(pdf_path, number, dpi)
            updated = apply_ocr_success(current, text, confidence)
        except Exception as exc:
            print(f"ocr_failed {entry.doc_id} page {number}: {exc}", flush=True)
            updated = apply_ocr_failure(current)
            failed += 1
        by_no[number] = updated
        resumed[number] = updated
        seconds[number] = round(time.monotonic() - t0, 2)
        finished += 1
        _write_ocr_partial(part, entry, resumed, seconds)
        save(entry, [by_no[n] for n in sorted(by_no)], out)
        if finished % 25 == 0:
            elapsed = time.monotonic() - started
            average = elapsed / finished
            print(
                f"{entry.doc_id} page {number}  ocr={finished - failed} failed={failed} "
                f"elapsed={elapsed:.0f}s avg={average:.1f}s left={len(targets) - index - 1}",
                flush=True,
            )

    if finished or resumed:
        save(entry, [by_no[n] for n in sorted(by_no)], out)
    if not stopped:
        part.unlink(missing_ok=True)

    in_range = [page for page in by_no.values() if start <= page.page <= end]
    ocr_pages = [page for page in in_range if page.source == "ocr"]
    failed_pages = [page for page in in_range if page.method == "ocr_failed"]
    timed = [seconds[page.page] for page in in_range if page.page in seconds]
    average = round(sum(timed) / len(timed), 2) if timed else 0.0
    sample_pages = ocr_pages if len(ocr_pages) <= 5 else random.sample(ocr_pages, 5)
    samples = [
        {
            "page": page.page,
            "confidence": page.ocr_confidence,
            "text": page.text[:300],
        }
        for page in sorted(sample_pages, key=lambda page: page.page)
    ]
    return {
        "status": "stopped" if stopped else "saved",
        "ocr_pages": len(ocr_pages),
        "ocr_failed_pages": len(failed_pages),
        "attempted": finished,
        "average_seconds": average,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "samples": samples,
    }


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
    parser.add_argument(
        "--ocr-scanned",
        action="store_true",
        help="OCR saved pages whose text is under 150 characters and that contain an image",
    )
    parser.add_argument("--from-page", type=int, help="first page for --ocr-scanned")
    parser.add_argument("--to-page", type=int, help="last page for --ocr-scanned")
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

    if args.ocr_scanned:
        if len(entries) != 1 or args.from_page is None or args.to_page is None:
            print("need exactly one --doc plus --from-page and --to-page", flush=True)
            return 2
        if args.from_page < 1 or args.to_page < args.from_page:
            print("page range is invalid", flush=True)
            return 2
        try:
            stats = ocr_scanned_range(
                entries[0],
                start=args.from_page,
                end=args.to_page,
                dpi=args.dpi,
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            print(f"failed {entries[0].doc_id}: {exc}", flush=True)
            return 1
        print(
            f"{entries[0].doc_id} {stats['status']}: ocr={stats['ocr_pages']} "
            f"ocr_failed={stats['ocr_failed_pages']} avg={stats['average_seconds']}s "
            f"elapsed={stats['elapsed_seconds']}s",
            flush=True,
        )
        for sample in stats["samples"]:
            print(
                f"--- page {sample['page']} conf {sample['confidence']} ---\n{sample['text']}",
                flush=True,
            )
        return 2 if stats["status"] == "stopped" else 0

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
