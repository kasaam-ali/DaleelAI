import json

from pipeline.chunk import (
    CHUNK_CHARS,
    Chunk,
    Report,
    dedupe,
    detach_footnote_prefixes,
    find_headings,
    join_labels,
    process,
    split_text,
    strip_boilerplate,
)
from tests.unit.test_catalog import entry

DASH = "\u2014"
TOC = "TABLE OF CONTENTS\n" + "\n".join(f"{n}.\nHeading number {n}\n{n + 3}" for n in range(1, 120))
BODY_PAGES = [
    f"""Income Tax Ordinance, 2001
PART I
PRELIMINARY
1. Short title and commencement.{DASH}(1) This Ordinance may be called the Income Tax Ordinance.
(2) It extends to the whole of Pakistan.
12""",
    f"""Income Tax Ordinance, 2001
2. Definitions.{DASH}In this Ordinance,
(a)
"person" includes an individual;
PART II
CHARGE OF TAX
4. Tax on taxable income.{DASH}(1) Income tax shall be imposed for each tax year.
13""",
    f"""Income Tax Ordinance, 2001
Part of the income is exempt as described below.
FIRST SCHEDULE
1. Rates for individuals.{DASH}The rates are given in the table below.
14""",
]


def write_extracted(tmp_path, pages: list[str]):
    row = entry(sha256="a" * 64)
    payload = {
        "doc_id": row.doc_id,
        "sha256": row.sha256,
        "version": 1,
        "pages": [
            {"page": i + 1, "text": t, "method": "text", "ocr_confidence": None}
            for i, t in enumerate(pages)
        ],
    }
    (tmp_path / "extracted").mkdir()
    (tmp_path / "extracted" / f"{row.doc_id}.json").write_text(json.dumps(payload), "utf-8")
    return row


def test_strip_boilerplate_drops_running_headers_and_page_numbers():
    words = "alpha beta gamma delta epsilon zeta eta theta iota kappa".split()
    bodies = [[f"{w} clause {k}" for k in "abcdef"] for w in words]
    pages = [["Income Tax Ordinance, 2001", *body, str(i)] for i, body in enumerate(bodies)]
    assert strip_boilerplate(pages) == bodies


def test_join_labels_reattaches_clause_labels():
    assert join_labels(["(a)", '"person" includes;', "(ii)", "next"]) == [
        '(a) "person" includes;',
        "(ii) next",
    ]


def test_table_of_contents_entries_are_not_section_headings():
    headings = find_headings("149.\nSalary\n212\n149. Salary.\u2014(1) Any salary")
    assert [(h.kind, h.num, h.title) for h in headings] == [("section", "149", "Salary")]


def test_ocr_comma_after_number_still_counts_as_a_heading():
    assert find_headings("5, Appointment of members.\u2014 For the purposes")[0].num == "5"


def test_sentences_starting_with_part_are_not_headings():
    assert find_headings("Part of the income is exempt.\nPART II\nCHARGE OF TAX")[0].title == (
        "CHARGE OF TAX"
    )


def test_contents_list_does_not_put_the_body_inside_a_schedule(tmp_path):
    dash = "\u2014"
    text = f"""195A. Early contents heading.{dash} Kept so the contents are not front matter.
FIFTEENTH SCHEDULE
819
THRESHOLD FOR ECONOMIC TRANSACTIONS
819
4. Tax on taxable income.{dash}(1) Income tax shall be imposed for each tax year.
THE FIRST SCHEDULE
PART I
RATES OF TAX
(See Chapter II)
1. Rates for individuals.{dash}The rates are given in the table below.
"""
    row = write_extracted(tmp_path, [text])
    payload, _ = process(row, tmp_path)
    by_section = {c["section"]: c for c in payload["chunks"]}
    assert "Fifteenth" not in by_section["4"]["header"]
    assert by_section["4"]["header"].endswith("Section 4 Tax on taxable income")
    assert "The First Schedule" in by_section["1"]["header"]


def test_a_new_chapter_does_not_keep_the_previous_part(tmp_path):
    dash = "\u2014"
    text = f"""1. Opening.{dash}(1) This Ordinance starts here.
PART IV
AGREEMENTS
CHAPTER IX
MINIMUM TAX
113. Minimum tax on the income of certain persons.{dash}(1) This section shall apply.
"""
    row = write_extracted(tmp_path, [text])
    payload, _ = process(row, tmp_path)
    header = next(c["header"] for c in payload["chunks"] if c["section"] == "113")
    assert "Chapter Ix Minimum Tax" in header or "Chapter IX Minimum Tax" in header
    assert "Part IV" not in header


def test_process_builds_sections_with_paths_and_drops_the_toc(tmp_path):
    row = write_extracted(tmp_path, [TOC, *BODY_PAGES])
    payload, report = process(row, tmp_path)

    ids = [s["parent_id"].split(":", 1)[1] for s in payload["sections"]]
    assert ids == ["s1", "s2", "s4", "sch1", "sch1:s1"]
    assert report.front_matter_dropped > 0
    assert not any("TABLE OF CONTENTS" in c["text"] for c in payload["chunks"])

    by_parent = {c["parent_id"].split(":", 1)[1]: c for c in payload["chunks"]}
    assert by_parent["s4"]["header"] == (
        "Income Tax Ordinance, 2001 > Part II Charge Of Tax > Section 4 Tax on taxable income"
    )
    assert by_parent["s1"]["page_start"] == 2
    assert by_parent["s4"]["doc_id"] == row.doc_id
    assert by_parent["s4"]["doc_title"] == row.title
    assert by_parent["s4"]["amended_upto"] == "2026-06-30"
    assert by_parent["s4"]["tax_years"] == ["TY2027"]
    assert by_parent["s4"]["jurisdiction"] == "federal"
    assert by_parent["s4"]["section"] == "4"
    assert by_parent["s2"]["text"].count('(a) "person"') == 1
    assert "Income Tax Ordinance, 2001\n" not in by_parent["s2"]["text"]
    assert by_parent["sch1:s1"]["header"].startswith("Income Tax Ordinance, 2001 > First Schedule")


def test_documents_without_headings_get_one_parent_per_page(tmp_path):
    row = write_extracted(tmp_path, ["Circular text one " * 10, "Circular text two " * 10])
    payload, _ = process(row, tmp_path)
    assert [s["section_title"] for s in payload["sections"]] == ["Page 1", "Page 2"]


def test_split_text_respects_size_and_overlaps():
    text = " ".join(f"word{i}." for i in range(800))
    pieces = split_text(text, CHUNK_CHARS, 150)
    assert all(len(p) <= CHUNK_CHARS for p in pieces)
    assert pieces[1].split()[0] in pieces[0]


def test_split_tables_repeat_their_header_row(tmp_path):
    rows = "\n".join(f"|151 Profit on debt case {n}|{n}.00%|{2 * n}.00%|" for n in range(60))
    table = f"|**Section**|**ATL Rates**|**Non-ATL Rates**|\n|---|---|---|\n{rows}"
    row = write_extracted(tmp_path, [table])
    payload, _ = process(row, tmp_path)
    assert len(payload["chunks"]) > 1
    assert all(c["text"].startswith("|**Section**|") for c in payload["chunks"])


def test_dedupe_removes_exact_and_near_duplicates():
    base = " ".join(f"token{i}" for i in range(200))
    chunks = [
        Chunk("a", "p", "1", "t", "h", 1, 1, base),
        Chunk("b", "p", "1", "t", "h", 1, 1, base.upper()),
        Chunk("c", "p", "1", "t", "h", 1, 1, base + " extra"),
        Chunk("d", "p", "1", "t", "h", 1, 1, "something else entirely " * 20),
    ]
    report = Report()
    assert [c.chunk_id for c in dedupe(chunks, report)] == ["a", "d"]
    assert (report.exact_duplicates, report.near_duplicates) == (1, 1)


def test_footnote_prefix_comes_off_the_rule_heading():
    lines = [
        "8612B. Restoration as an active taxpayer.--A non-active taxpayer may be restored.",
        "13.",
        "Application. \u2013The provisions of this Chapter shall apply.",
        "14.",
        "87[Filing of returns.\u2014 (1) Every person registered under the Act shall file.",
        "150H. Scrutiny of records. \u2014 An officer may examine the record.",
        "86",
        "Rule 12B inserted by Notification No. S.R.O. 494(I)/2015, dated 30th June, 2015.",
        "87",
        "Rule 14 substituted by Notification No. S.R.O. 530(I)/2008, dated 11th June, 2008.",
        "15",
        "A footnote that must not eat the real rule 150H.",
    ]
    headings = find_headings("\n".join(detach_footnote_prefixes(lines)))
    assert [(h.num, h.title) for h in headings if h.kind == "section"] == [
        ("12B", "Restoration as an active taxpayer"),
        ("13", "Application"),
        ("14", "Filing of returns"),
        ("150H", "Scrutiny of records"),
    ]
    assert find_headings("9.\nKnown properties of the defaulter:--") == []
    appeal = "150ZR.\nPrescribed form of appeal to the Commissioner (Appeals): \u2013 An appeal"
    assert find_headings(appeal)[0].num == "150ZR"


def test_broken_rate_card_header_is_repaired_and_repeated(tmp_path):
    header = (
        "|**Section**|**Ancillary Information-A**|**Ancillary Information-B**|"
        "**ATL Rates**|**Non-ATL Rates**<br>**L**|**ate Filer**|"
        "**Rates**<br>**Reference for Rates**|"
    )
    sep = "|---|---|---|---|---|---|---|"
    rows = [
        (
            f"|148 Imports|Goods falling in Part-{n} of the Twelfth Schedule|"
            f"|{rate}|{other}||Part-II of the First Schedule read with rule {n}|"
        )
        for n, rate, other in (
            (1, "1.00%", "2.00%"),
            (2, "2.00%", "4.00%"),
            (3, "3.50%", "7.00%"),
            (4, "5.50%", "11.00%"),
            (5, "6.00%", "12.00%"),
            (6, "4.00%", "8.00%"),
            (7, "1.00%", "2.00%"),
        )
    ]
    row = write_extracted(tmp_path, ["\n".join([header, sep, *rows])])
    payload, _ = process(row, tmp_path)
    assert len(payload["chunks"]) > 1
    fixed = (
        "|**Section**|**Ancillary Information-A**|**Ancillary Information-B**|"
        "**ATL Rates**|**Non-ATL Rates**|**Late Filer Rates**|**Reference for Rates**|"
    )
    assert all(c["text"].startswith(fixed) for c in payload["chunks"])
    joined = "\n".join(c["text"] for c in payload["chunks"])
    assert "1.00%" in joined and "2.00%" in joined
