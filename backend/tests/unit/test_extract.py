import json
from pathlib import Path

import pymupdf

from pipeline.extract import (
    EXTRACT_VERSION,
    Page,
    extract_markdown,
    extract_pdf,
    extract_text_layer,
    is_current,
    ocr_lines,
    page_kind,
    page_ranges,
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


def test_cache_is_current_only_for_same_hash_and_version(tmp_path: Path):
    row = entry(sha256="a" * 64)
    out = tmp_path / "doc.json"
    save(row, [Page(page=1, text="hello", method="text")], out)
    assert is_current(row, out)
    stale = json.loads(out.read_text(encoding="utf-8"))
    stale["version"] = EXTRACT_VERSION + 1
    out.write_text(json.dumps(stale), encoding="utf-8")
    assert not is_current(row, out)
