from dataclasses import replace

from pipeline.catalog import CatalogEntry, read_catalog, validate


def entry(**overrides) -> CatalogEntry:
    base = CatalogEntry(
        doc_id="ito_2001@2026-06-30",
        work_id="ito_2001",
        title="Income Tax Ordinance, 2001",
        doc_type="act",
        domain="income_tax",
        authority="FBR",
        language="en",
        amended_upto="2026-06-30",
        tax_years="TY2027",
        status="active",
        superseded_by="",
        source_url="https://download1.fbr.gov.pk/Docs/ito.pdf",
        local_file="",
        sha256="",
        notes="",
    )
    return replace(base, **overrides)


def test_shipped_catalog_is_valid():
    entries = read_catalog()
    assert validate(entries) == []
    assert any(e.status == "active" for e in entries)


def test_every_core_law_has_one_version_per_tax_year():
    active = [e for e in read_catalog() if e.status == "active"]
    for work_id in ["ito_2001", "sta_1990", "fea_2005", "customs_act_1969", "itr_2002"]:
        for year in ["TY2026", "TY2027"]:
            versions = [e for e in active if e.work_id == work_id and year in e.tax_year_list]
            assert len(versions) == 1, (work_id, year)


def test_rejects_duplicate_ids_and_unknown_status():
    problems = validate([entry(), entry(status="draft", tax_years="")])
    assert any("duplicate doc_id" in p for p in problems)
    assert any("unknown status" in p for p in problems)


def test_superseded_must_point_at_an_active_row():
    old = entry(doc_id="ito_2001@2025", tax_years="", status="superseded", superseded_by="nope")
    assert any("not in the catalog" in p for p in validate([entry(), old]))
    old.superseded_by = "ito_2001@2026-06-30"
    assert validate([entry(), old]) == []


def test_two_active_versions_for_the_same_year_are_rejected():
    twin = entry(doc_id="ito_2001@2026-07-15")
    assert any("more than one active version" in p for p in validate([entry(), twin]))


def test_superseded_rows_carry_no_tax_years():
    old = entry(doc_id="old", status="superseded", superseded_by="ito_2001@2026-06-30")
    assert any("only active or pending" in p for p in validate([entry(), old]))


def test_rejects_plain_http_and_bad_hashes():
    problems = validate([entry(source_url="http://x/y.pdf", sha256="ABC")])
    assert any("must be https" in p for p in problems)
    assert any("64 lowercase hex" in p for p in problems)
