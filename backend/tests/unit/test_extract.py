"""Checks PDF text extraction and the OCR fallback, including a timeout."""

import json
from pathlib import Path

import pymupdf
import pytest

from pipeline.extract import (
    EXTRACT_VERSION,
    Page,
    apply_ocr_failure,
    apply_ocr_success,
    extract_markdown,
    extract_pdf,
    extract_text_layer,
    is_current,
    ocr_lines,
    ocr_scanned_range,
    output_path,
    page_kind,
    page_ranges,
    partial_path,
    projected_over_budget,
    report_for,
    save,
    should_ocr,
)
from tests.unit.test_catalog import entry

DIGITAL = (
    "149. Salary. Any salary paid to an employee is taxable. "
    "The charge is computed on taxable income for the tax year under this Ordinance, "
    "after the allowances and deductions this section permits."
)


def write_text(page: pymupdf.Page, text: str) -> None:
    unused = page.insert_textbox(pymupdf.Rect(72, 72, 540, 700), text)
    assert unused >= 0


def digital_and_blank_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    write_text(page, DIGITAL)
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def test_page_kind_uses_150_characters_and_an_image():
    assert len(DIGITAL) >= 150
    assert page_kind(DIGITAL, False) == "digital"
    assert page_kind(DIGITAL, True) == "digital"
    assert page_kind("x" * 149, True) == "scanned"
    assert page_kind("x" * 149, False) == "blank"
    assert page_kind("", False) == "blank"
    assert page_ranges([]) == ""
    assert page_ranges([77, 78, 79, 81, 255]) == "77-79, 81, 255"


def test_ocr_only_when_text_is_short_and_page_has_an_image():
    assert should_ocr("", True)
    assert should_ocr("x" * 19, True)
    assert not should_ocr("", False)
    assert not should_ocr("   ", False)
    assert not should_ocr("x" * 20, True)


def test_digital_and_blank_page_with_ocr_off_and_on(tmp_path: Path, monkeypatch):
    path = digital_and_blank_pdf(tmp_path)

    def fail(*args, **kwargs):
        raise AssertionError("tesseract should not run")

    monkeypatch.setattr("pipeline.extract.ocr_page", fail)

    for ocr in (False, True):
        pages = extract_pdf(path, ocr=ocr, dpi=200, done={}, label="sample")
        assert pages[0].method == "text"
        assert "149. Salary" in pages[0].text
        assert pages[1].method == "empty"
        assert pages[1].text.strip() == ""
        report = report_for(pages)
        assert report["total_pages"] == 2
        assert report["text_layer_pages"] == 1
        assert report["ocr_pages"] == 0
        assert report["ocr_failed_pages"] == 0
        assert report["empty_pages"] == 1
        assert report["digital_pages"] == 1
        assert report["scanned_pages"] == 0
        assert report["blank_pages"] == 1
        assert report["scanned_ranges"] == ""


def test_ocr_timeout_marks_the_page_and_continues(tmp_path: Path, monkeypatch):
    path = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    doc.new_page()
    page = doc.new_page()
    write_text(page, DIGITAL)
    doc.save(path)
    doc.close()

    def explode(*args, **kwargs):
        raise RuntimeError("tesseract timed out")

    monkeypatch.setattr("pipeline.extract.ocr_page", explode)
    monkeypatch.setattr("pipeline.extract.page_has_image", lambda page: True)

    pages = extract_pdf(path, ocr=True, dpi=200, done={}, label="scan")
    assert pages[0].method == "ocr_failed"
    assert pages[1].method == "text"
    assert "149. Salary" in pages[1].text
    report = report_for(pages)
    assert report == {
        "total_pages": 2,
        "text_layer_pages": 1,
        "ocr_pages": 0,
        "ocr_failed_pages": 1,
        "empty_pages": 0,
        "digital_pages": 1,
        "scanned_pages": 1,
        "blank_pages": 0,
        "scanned_ranges": "1",
    }


def test_resume_skips_pages_already_saved(tmp_path: Path, monkeypatch):
    path = digital_and_blank_pdf(tmp_path)

    def fail(*args, **kwargs):
        raise AssertionError("saved page was sent to OCR")

    monkeypatch.setattr("pipeline.extract.ocr_page", fail)
    done = {1: Page(page=1, text="KEPT", method="text")}
    pages = extract_pdf(path, ocr=True, dpi=200, done=done, label="sample")
    assert pages[0].text == "KEPT"
    assert pages[0].method == "text"
    assert pages[1].method == "empty"


def test_ocr_lines_keeps_paragraph_breaks():
    data = {
        "text": ["(1)", "This", "Ordinance", "extends", "to", "Pakistan."],
        "block_num": [1, 1, 1, 2, 2, 2],
        "par_num": [1, 1, 1, 1, 1, 1],
        "line_num": [1, 1, 1, 1, 1, 1],
        "conf": [90.0, 88.0, 91.0, 80.0, 85.0, 92.0],
    }
    text, conf = ocr_lines(data)
    assert text == "(1) This Ordinance\n\nextends to Pakistan."
    assert conf == 87.7


def test_extract_text_layer_reads_a_digital_page(tmp_path: Path):
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "149. Salary.—(1) Any salary paid.")
    doc.save(path)
    doc.close()

    pages = extract_text_layer(path)
    assert len(pages) == 1
    assert pages[0].method == "text"
    assert "149. Salary" in pages[0].text


def test_extract_markdown_keeps_table_rows(tmp_path: Path):
    path = tmp_path / "rates.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_htmlbox(
        pymupdf.Rect(50, 50, 500, 200),
        "<table><tr><td>Section</td><td>ATL</td></tr><tr><td>151</td><td>15%</td></tr></table>",
    )
    doc.save(path)
    doc.close()

    pages = extract_markdown(path)
    assert pages[0].method == "markdown"
    assert "151" in pages[0].text
    assert "15%" in pages[0].text or "15" in pages[0].text


def test_ocr_success_marks_source_and_keeps_the_page_scanned():
    page = Page(page=77, text="REGISTERED No. M-302", method="text", page_class="scanned")
    done = apply_ocr_success(page, "1. First Schedule rate 20", 80.0)
    assert done.source == "ocr"
    assert done.method == "ocr"
    assert done.page_class == "scanned"
    assert done.ocr_confidence == 80.0
    failed = apply_ocr_failure(page)
    assert failed.source == ""
    assert failed.method == "ocr_failed"
    assert failed.text == page.text


def test_budget_waits_for_five_pages_then_stops_a_slow_run():
    assert not projected_over_budget(1000, 4, 100, 45 * 60)
    assert projected_over_budget(50, 5, 10, 60)
    assert not projected_over_budget(10, 5, 2, 100)
    assert projected_over_budget(61, 1, 3, 60)


def _banner_pdf(tmp_path: Path, scans: int) -> Path:
    path = tmp_path / "act.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    write_text(page, DIGITAL)
    banner = "REGISTERED No. M-302. The Gazette of Pakistan banner stays short."
    assert 20 <= len(banner) < 150
    assert not should_ocr(banner, True)
    assert page_kind(banner, True) == "scanned"
    for _ in range(scans):
        page = doc.new_page()
        write_text(page, banner)
    doc.save(path)
    doc.close()
    return path


def test_scanned_range_ocr_marks_source_and_skips_a_resumed_page(tmp_path: Path, monkeypatch):
    path = _banner_pdf(tmp_path, 2)
    row = entry(doc_id="finance_act_2026", sha256="b" * 64)
    data = tmp_path / "data"
    (data / "docs").mkdir(parents=True)
    path.replace(row.path(data))
    pages = extract_text_layer(row.path(data))
    save(row, pages, output_path(row, data))
    seen: list[int] = []

    def fake_ocr(pdf_path, page_no, dpi):
        seen.append(page_no)
        return ("PCT 3825.1010 rate 20. " * 8, 81.0)

    monkeypatch.setattr("pipeline.extract.ocr_page", fake_ocr)
    monkeypatch.setattr("pipeline.extract.page_has_image", lambda page: True)
    stats = ocr_scanned_range(row, start=1, end=3, data_dir=data, budget_s=45 * 60)
    assert seen == [2, 3]
    assert stats["status"] == "saved"
    assert stats["ocr_pages"] == 2
    assert stats["ocr_failed_pages"] == 0
    saved = json.loads(output_path(row, data).read_text(encoding="utf-8"))
    by_page = {raw["page"]: raw for raw in saved["pages"]}
    assert by_page[1]["source"] == ""
    assert by_page[1]["method"] == "text"
    assert by_page[2]["source"] == "ocr"
    assert by_page[2]["page_class"] == "scanned"
    assert "3825.1010" in by_page[2]["text"]
    assert not partial_path(output_path(row, data)).exists()

    seen.clear()
    banner = "REGISTERED No. M-302. The Gazette of Pakistan banner stays short."
    for number in (2, 3):
        by_page[number]["text"] = banner
        by_page[number]["method"] = "text"
        by_page[number]["source"] = ""
        by_page[number]["page_class"] = ""
        by_page[number]["ocr_confidence"] = None
    output_path(row, data).write_text(json.dumps(saved), encoding="utf-8")
    partial = partial_path(output_path(row, data))
    partial.write_text(
        json.dumps(
            {
                "doc_id": row.doc_id,
                "sha256": row.sha256,
                "version": EXTRACT_VERSION,
                "purpose": "ocr-scanned",
                "pages": [
                    {
                        "page": 2,
                        "text": "already read",
                        "method": "ocr",
                        "ocr_confidence": 90.0,
                        "page_class": "scanned",
                        "source": "ocr",
                    }
                ],
                "seconds": {"2": 1.5},
            }
        ),
        encoding="utf-8",
    )
    again = ocr_scanned_range(row, start=1, end=3, data_dir=data)
    assert seen == [3]
    assert again["ocr_pages"] == 2
    merged = json.loads(output_path(row, data).read_text(encoding="utf-8"))
    kept = {raw["page"]: raw for raw in merged["pages"]}
    assert kept[2]["text"] == "already read"
    assert kept[2]["source"] == "ocr"


def test_scanned_ocr_failure_does_not_mark_source_and_budget_keeps_partial(
    tmp_path: Path, monkeypatch
):
    path = _banner_pdf(tmp_path, 6)
    row = entry(doc_id="finance_act_2026", sha256="c" * 64)
    data = tmp_path / "data"
    (data / "docs").mkdir(parents=True)
    path.replace(row.path(data))
    save(row, extract_text_layer(row.path(data)), output_path(row, data))

    def explode(pdf_path, page_no, dpi):
        if page_no == 2:
            raise RuntimeError("tesseract timed out")
        return ("rate 15", 70.0)

    monkeypatch.setattr("pipeline.extract.ocr_page", explode)
    monkeypatch.setattr("pipeline.extract.page_has_image", lambda page: True)
    stats = ocr_scanned_range(row, start=2, end=3, data_dir=data)
    assert stats["ocr_failed_pages"] == 1
    assert stats["ocr_pages"] == 1
    saved = json.loads(output_path(row, data).read_text(encoding="utf-8"))
    by_page = {raw["page"]: raw for raw in saved["pages"]}
    assert by_page[2]["method"] == "ocr_failed"
    assert by_page[2]["source"] == ""
    assert by_page[3]["source"] == "ocr"

    save(row, extract_text_layer(row.path(data)), output_path(row, data))
    clock = {"now": 0.0}

    def monotonic():
        return clock["now"]

    def slow(pdf_path, page_no, dpi):
        clock["now"] += 10
        return ("rate 15", 70.0)

    monkeypatch.setattr("pipeline.extract.time.monotonic", monotonic)
    monkeypatch.setattr("pipeline.extract.ocr_page", slow)
    stopped = ocr_scanned_range(row, start=2, end=7, data_dir=data, budget_s=55)
    assert stopped["status"] == "stopped"
    assert stopped["attempted"] == 5
    assert partial_path(output_path(row, data)).exists()


def test_a_text_layer_partial_is_not_an_ocr_resume_file(tmp_path: Path):
    row = entry(doc_id="finance_act_2026", sha256="d" * 64)
    data = tmp_path / "data"
    out = output_path(row, data)
    out.parent.mkdir(parents=True)
    save(row, [Page(page=1, text="x" * 40, method="text")], out)
    partial_path(out).write_text(json.dumps({"sha256": row.sha256, "pages": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="not an OCR resume"):
        ocr_scanned_range(row, start=1, end=1, data_dir=data)


def test_cache_is_current_only_for_same_hash_and_version(tmp_path: Path):
    row = entry(sha256="a" * 64)
    out = tmp_path / "doc.json"
    save(row, [Page(page=1, text="hello", method="text")], out)
    assert is_current(row, out)
    stale = json.loads(out.read_text(encoding="utf-8"))
    stale["version"] = EXTRACT_VERSION + 1
    out.write_text(json.dumps(stale), encoding="utf-8")
    assert not is_current(row, out)
