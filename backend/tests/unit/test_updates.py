"""Replay listings, crawl change detection, and the updates feed."""

import json

from fastapi.testclient import TestClient

from app.adapters.fakes import FakeLLM
from app.container import Container
from app.core.ports import LLMResult
from app.core.services.updates import apply_web_crawl, memory_updates
from app.core.updates.changes import ZeroPages, detect_changes, prefixes_for, url_allowed
from app.core.updates.listing import ZeroItems, collect_listing, load_replay
from app.main import create_app
from app.settings import Adapters, Settings
from tests.integration.test_chat import make_client, parse_sse, router_payload

_LIVE_SNIPPET = (
    '<li><a href="Downloads/?id=17752&Type=SROs">'
    "S.R.O1751(I)/2026 - Production Monitoring of Leather Paper & Paperboard<a></li>"
)


def _client(token: str = "") -> TestClient:
    memory_updates(reset=True)
    settings = Settings(
        adapters=Adapters(llm="fake", vector_store="memory", classifier="keyword"),
        internal_token=token,
    )
    return TestClient(create_app(Container(settings=settings, llm=FakeLLM())))


def test_replay_fixture_and_zero_item_alarm():
    items = load_replay()
    assert len(items) == 3
    assert {item["doc_type"] for item in items} == {"sro", "circular", "notification"}
    assert all(item["sha256"] for item in items)
    parsed = collect_listing(_LIVE_SNIPPET)
    assert parsed[0]["doc_type"] == "sro"
    assert parsed[0]["source_url"].startswith("https://www.fbr.gov.pk/Downloads/")
    try:
        collect_listing("<html><p>no listing</p></html>")
    except ZeroItems as exc:
        assert "0 items" in str(exc)
        assert "left in place" in str(exc)
    else:
        raise AssertionError("empty listing should alarm")


def test_change_detection_keeps_pages_when_a_crawl_is_empty():
    known = {"https://www.fbr.gov.pk/": "abc"}
    try:
        detect_changes([], known)
    except ZeroPages as exc:
        assert "left in place" in str(exc)
    else:
        raise AssertionError("zero pages should alarm")
    assert known == {"https://www.fbr.gov.pk/": "abc"}
    plan = detect_changes(
        [
            {"url": "https://www.fbr.gov.pk/", "sha256": "abc"},
            {"url": "https://bra.gob.pk/", "sha256": "new"},
        ],
        known,
    )
    assert [page["url"] for page in plan["unchanged"]] == ["https://www.fbr.gov.pk/"]
    assert [page["url"] for page in plan["new"]] == ["https://bra.gob.pk/"]
    changed = detect_changes([{"url": "https://www.fbr.gov.pk/", "sha256": "def"}], known)
    assert changed["changed"][0]["url"] == "https://www.fbr.gov.pk/"
    gone = detect_changes([{"url": "https://bra.gob.pk/", "sha256": "new"}], known)
    assert gone["removed"] == ["https://www.fbr.gov.pk/"]


def test_off_list_url_is_rejected_and_empty_crawl_deletes_nothing():
    from pathlib import Path

    prefixes = prefixes_for(Path(__file__).resolve().parents[2] / "config" / "web_sources.yaml")
    assert url_allowed("https://www.secp.gov.pk/company", prefixes)
    assert url_allowed("http://www.srb.gos.pk/", prefixes)
    assert not url_allowed("https://example.com/tax", prefixes)
    store = memory_updates(reset=True)
    store.upsert_web(
        {
            "url": "https://www.fbr.gov.pk/",
            "site": "fbr.gov.pk",
            "title": "FBR",
            "sha256": "abc",
        }
    )
    try:
        apply_web_crawl("fbr.gov.pk", [], store, prefixes)
    except ZeroPages:
        pass
    else:
        raise AssertionError("empty crawl should alarm")
    assert store.web["https://www.fbr.gov.pk/"]["removed"] is False


def test_replay_feed_domain_filter_and_chat_card():
    client = _client(token="test-token")
    denied = client.post("/internal/notifications/ingest", json={"items": []})
    assert denied.status_code == 401
    replayed = client.post("/api/v1/updates/replay")
    assert replayed.status_code == 200
    body = replayed.json()
    assert body["ingested"] == 3
    again = client.post("/api/v1/updates/replay")
    assert again.json()["skipped"] == 3
    sales = client.get("/api/v1/updates", params={"domain": "sales_tax"})
    assert sales.status_code == 200
    assert sales.json()["total"] == 1
    assert sales.json()["items"][0]["doc_type"] == "circular"
    assert "Roman" not in sales.json()["items"][0]["summary"]
    assert "khulasa" in sales.json()["items"][0]["summary"]
    empty = client.post(
        "/internal/web/ingest",
        headers={"X-Internal-Token": "test-token"},
        json={"site": "fbr.gov.pk", "crawl_id": "c1", "pages": []},
    )
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "zero_pages"
    blocked = client.post(
        "/internal/web/ingest",
        headers={"Authorization": "Bearer test-token"},
        json={
            "site": "fbr.gov.pk",
            "crawl_id": "c2",
            "pages": [
                {
                    "url": "https://example.com/tax",
                    "status": "new",
                    "sha256": "abc",
                    "title": "Off list",
                }
            ],
        },
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "off_list"

    class Scripted:
        async def complete(self, role, messages, **kwargs):
            return LLMResult(
                text=json.dumps(router_payload(intent="updates", search_query="")),
                model="scripted",
                fallback=False,
                latency_ms=0,
            )

    chat = make_client(Scripted()).post("/api/v1/chat", json={"message": "latest sro"})
    events = parse_sse(chat.text)
    card = events[1][1]["card"]
    assert card["type"] == "updates"
    assert card["data"]["total"] == 3
