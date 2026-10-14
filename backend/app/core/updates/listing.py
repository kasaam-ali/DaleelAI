"""Parse an FBR listing page. Replay and live fetch share this parser."""

import hashlib
import re
from html import unescape
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "listing.html"
_BASE = "https://www.fbr.gov.pk/"
_TYPE = {"sros": "sro", "circulars": "circular", "notifications": "notification"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ZeroItems(Exception):
    """A scrape parsed nothing. Callers must leave stored items alone."""

    def __init__(self) -> None:
        super().__init__("The scrape returned 0 items. Previous items were left in place.")


def parse_listing(html: str) -> list[dict]:
    items = []
    seen: set[str] = set()
    for match in re.finditer(r"<a\b([^>]*)>", html, flags=re.I):
        tag = match.group(1)
        href_match = re.search(r'href="([^"]+)"', tag, flags=re.I)
        if href_match is None:
            continue
        href = unescape(href_match.group(1))
        kind_match = re.search(r"Type=(SROs|Circulars|Notifications)\b", href, flags=re.I)
        if kind_match is None:
            continue
        title = unescape(html[match.end() :].split("<", 1)[0]).strip()
        if not title:
            continue
        url = _absolute(href)
        if url in seen:
            continue
        seen.add(url)
        text = unescape(_attr(tag, "data-text") or title)
        published = _attr(tag, "data-published")
        if published and _DATE.fullmatch(published) is None:
            published = None
        items.append(
            {
                "source_url": url,
                "listing_title": title,
                "title": title,
                "doc_type": _TYPE[kind_match.group(1).lower()],
                "published_at": published,
                "text": text,
                "sha256": hashlib.sha256(f"{url}\n{title}".encode()).hexdigest(),
            }
        )
    return items


def collect_listing(html: str) -> list[dict]:
    items = parse_listing(html)
    if not items:
        raise ZeroItems
    return items


def load_replay(path: Path | None = None) -> list[dict]:
    return collect_listing((path or FIXTURE).read_text(encoding="utf-8"))


def fetch_html(url: str, timeout: float = 15.0) -> str:
    """Playwright when that package is installed, otherwise a timed HTTP GET."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _fetch_http(url, timeout)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=_USER_AGENT)
            page.goto(url, timeout=int(timeout * 1000), wait_until="domcontentloaded")
            return page.content()
        finally:
            browser.close()


_USER_AGENT = "DaleelAI-crawler/1.0 (+https://github.com/kasaam-ali/DaleelAI)"


def _fetch_http(url: str, timeout: float) -> str:
    import httpx

    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def _absolute(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return _BASE + href.lstrip("/")


def _attr(tag: str, name: str) -> str | None:
    match = re.search(rf'{name}="([^"]*)"', tag, flags=re.I)
    if match is None:
        return None
    return match.group(1)
