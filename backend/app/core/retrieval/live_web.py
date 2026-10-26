"""Bounded public-web snippets. Not the stored web_pages collection."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

_TAG = re.compile(r"<[^>]+>")
_LINK = re.compile(
    r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S,
)
_LINK_HREF_FIRST = re.compile(
    r'<a[^>]*href="([^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>',
    re.I | re.S,
)
_SNIPPET = re.compile(r'class="result-snippet"[^>]*>(.*?)</td>', re.I | re.S)
_HOME = re.compile(r"^https?://[^/]+/?$", re.I)
_ALLOWED = ("fbr.gov.pk", "secp.gov.pk", "pakistancode.gov.pk", "iris.fbr.gov.pk")


def _unwrap(url: str) -> str:
    if "uddg=" in url:
        query = parse_qs(urlparse(url).query)
        raw = query.get("uddg", [""])[0]
        if raw:
            return unquote(raw)
    return url


def _clean(html: str) -> str:
    text = _TAG.sub(" ", unescape(html))
    return re.sub(r"\s+", " ", text).strip()


def parse_lite_results(html: str, *, limit: int = 3) -> list[dict[str, str]]:
    """Pull titled snippets. Generic homepages are dropped."""
    links = _LINK.findall(html) or _LINK_HREF_FIRST.findall(html)
    snippets = [_clean(item) for item in _SNIPPET.findall(html)]
    found: list[dict[str, str]] = []
    for index, (href, title_html) in enumerate(links):
        url = _unwrap(href).split("#", 1)[0]
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if not any(host == name or host.endswith("." + name) for name in _ALLOWED):
            continue
        if _HOME.match(url):
            continue
        title = _clean(title_html)
        snippet = snippets[index] if index < len(snippets) else title
        if not snippet:
            continue
        found.append({"url": url, "title": title or host, "text": snippet[:500]})
        if len(found) >= limit:
            break
    return found


async def fetch_official_snippets(query: str) -> list[dict[str, str]]:
    """At most ~2.3s. Empty when the public search does not answer in time."""
    import httpx

    question = " ".join(query.split())[:240]
    if not question:
        return []
    timeout = httpx.Timeout(2.3, connect=1.0)
    headers = {"User-Agent": "DaleelAI/0.1 (statutory research; +https://localhost)"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = await client.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": f"site:fbr.gov.pk {question}"},
        )
        response.raise_for_status()
    return parse_lite_results(response.text)
