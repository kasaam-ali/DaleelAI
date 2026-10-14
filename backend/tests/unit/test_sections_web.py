import pytest

from pipeline.sections import section_rows
from pipeline.web_pages import assert_safe_collection, chunk_text, html_to_text, records_for


def test_section_rows_keep_parent_text():
    rows = section_rows(
        {
            "doc_id": "finance_act_2025",
            "sections": [
                {
                    "parent_id": "finance_act_2025:p1",
                    "section": "",
                    "section_title": "Page 1",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "  parent text  ",
                },
                {"parent_id": "", "text": "skip"},
            ],
        },
        "9a59fef60e481ac3",
    )

    assert rows == [
        (
            "finance_act_2025:p1",
            "finance_act_2025",
            "",
            "Page 1",
            1,
            1,
            "parent text",
            "9a59fef60e481ac3",
        )
    ]


def test_web_chunks_overlap_and_keep_the_official_url():
    pieces = chunk_text("a" * 1200, size=1000, overlap=150)
    assert len(pieces) == 2
    assert pieces[0][-150:] == pieces[1][:150]
    page = {
        "url": "https://iris.fbr.gov.pk/",
        "site": "iris.fbr.gov.pk",
        "authority": "FBR",
        "title": "IRIS",
        "domain": "income_tax",
    }
    records = records_for(page, "Register for NTN on IRIS.", "2026-10-14T00:00:00Z", "abc")
    assert records[0]["url"] == "https://iris.fbr.gov.pk/"
    assert records[0]["chunk_id"].startswith("web:iris.fbr.gov.pk:")
    assert "script" not in html_to_text("<script>secret</script><p>NTN help</p>")


def test_web_indexer_refuses_the_documents_collection():
    with pytest.raises(RuntimeError):
        assert_safe_collection("documents")
