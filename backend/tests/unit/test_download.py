"""Checks that a catalog download keeps a file only when the hash matches."""

import hashlib

import httpx

from pipeline.download import sync_entry
from tests.unit.test_catalog import entry

PDF = b"%PDF-1.7 fake body"


def client_for(body: bytes, status: int = 200) -> httpx.Client:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, content=body))
    return httpx.Client(transport=transport)


def test_fetches_and_pins_a_new_document(tmp_path):
    row = entry()
    outcome, network_used = sync_entry(row, tmp_path, client_for(PDF), pin=True)
    assert outcome.state == "pinned" and network_used
    assert row.sha256 == hashlib.sha256(PDF).hexdigest()
    assert (tmp_path / "docs" / "ito_2001@2026-06-30.pdf").read_bytes() == PDF


def test_unpinned_document_is_a_problem_without_pin(tmp_path):
    outcome, _ = sync_entry(entry(), tmp_path, client_for(PDF), pin=False)
    assert outcome.state == "missing"


def test_hash_mismatch_is_reported(tmp_path):
    row = entry(sha256="0" * 64)
    outcome, _ = sync_entry(row, tmp_path, client_for(PDF), pin=True)
    assert outcome.state == "mismatch"


def test_html_error_pages_are_not_saved(tmp_path):
    outcome, _ = sync_entry(entry(), tmp_path, client_for(b"<html>blocked</html>"), pin=True)
    assert outcome.state == "failed" and "not a PDF" in outcome.detail
    assert not list((tmp_path / "docs").iterdir())


def test_http_errors_are_reported(tmp_path):
    outcome, _ = sync_entry(entry(), tmp_path, client_for(b"", status=403), pin=True)
    assert outcome.state == "failed" and "403" in outcome.detail


def test_local_copy_is_used_instead_of_downloading(tmp_path):
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "income tax 1.pdf").write_bytes(PDF)
    row = entry(local_file="income tax 1.pdf", sha256=hashlib.sha256(PDF).hexdigest())

    def refuse(_):
        raise AssertionError("should not hit the network")

    outcome, network_used = sync_entry(
        row, tmp_path, httpx.Client(transport=httpx.MockTransport(refuse)), pin=False
    )
    assert outcome.state == "copied" and not network_used


def test_pending_rows_without_a_file_are_not_errors(tmp_path):
    row = entry(source_url="", local_file="companies_act_2017.pdf", status="pending")
    outcome, _ = sync_entry(row, tmp_path, client_for(PDF), pin=True)
    assert outcome.state == "pending"
