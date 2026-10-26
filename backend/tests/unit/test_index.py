"""Checks point ids, the header in front of the text, and resume."""

from pipeline.chunk import CHUNK_VERSION
from pipeline.index import (
    DENSE_MODEL,
    SPARSE_MODEL,
    chunks_to_index,
    corpus_version,
    crossed_progress,
    embed_input,
    payload_for,
    point_id,
)
from tests.unit.test_catalog import entry


def test_embed_input_puts_the_header_in_front_of_the_text():
    assert embed_input({"header": "Act > Section 4", "text": "Income tax shall be imposed."}) == (
        "Act > Section 4\n\nIncome tax shall be imposed."
    )


def test_point_id_is_stable():
    assert point_id("ito_2001@2026-06-30:s4:c0") == point_id("ito_2001@2026-06-30:s4:c0")
    assert point_id("a") != point_id("b")


def test_payload_uses_catalog_fields_and_keeps_the_raw_text():
    row = entry()
    version = corpus_version([row])
    payload = payload_for(
        {
            "chunk_id": "ito_2001@2026-06-30:s149:c2",
            "section": "149",
            "section_title": "Salary",
            "parent_id": "ito_2001@2026-06-30:s149",
            "page_start": 212,
            "page_end": 213,
            "header": "Income Tax Ordinance, 2001 > Section 149 Salary",
            "text": "deduct tax from the salary",
            "jurisdiction": "federal",
        },
        row,
        version,
    )
    assert payload["work_id"] == "ito_2001"
    assert payload["doc_type"] == "act"
    assert payload["domain"] == "income_tax"
    assert payload["tax_years"] == ["TY2027"]
    assert payload["text"] == "deduct tax from the salary"
    assert payload["source_url"].startswith("https://")
    assert len(payload["corpus_version"]) == 16
    assert version == corpus_version([row])
    assert DENSE_MODEL in f"{CHUNK_VERSION}|{DENSE_MODEL}|{SPARSE_MODEL}"


def test_resume_skips_points_already_stored():
    chunks = [
        {"chunk_id": "keep-me", "header": "h", "text": "a"},
        {"chunk_id": "have-me", "header": "h", "text": "b"},
    ]
    done = {point_id("have-me")}
    pending = chunks_to_index(chunks, done)
    assert [chunk["chunk_id"] for chunk in pending] == ["keep-me"]


def test_progress_prints_every_2000_chunks():
    assert not crossed_progress(0, 64)
    assert not crossed_progress(1984, 1999)
    assert crossed_progress(1984, 2048)
    assert crossed_progress(0, 4000)
