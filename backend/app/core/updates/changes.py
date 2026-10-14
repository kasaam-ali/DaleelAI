"""Decide which crawled pages are new, changed, unchanged, or removed."""

from urllib.parse import urlparse

import yaml


class ZeroPages(Exception):
    """A site returned no pages. Previous pages stay searchable."""

    def __init__(self) -> None:
        super().__init__("This crawl fetched 0 pages. Previous pages were left in place.")


class OffList(Exception):
    def __init__(self, url: str) -> None:
        super().__init__(f"That URL is not on the crawler allowlist: {url}")
        self.url = url


def detect_changes(fetched: list[dict], known: dict[str, str]) -> dict[str, list]:
    """`known` maps url to sha256. An empty fetch raises and does not list removals."""
    if not fetched:
        raise ZeroPages
    new, changed, unchanged = [], [], []
    seen: set[str] = set()
    for page in fetched:
        url = page["url"]
        seen.add(url)
        previous = known.get(url)
        if previous is None:
            new.append(page)
        elif previous != page["sha256"]:
            changed.append(page)
        else:
            unchanged.append(page)
    removed = [url for url in known if url not in seen]
    return {"new": new, "changed": changed, "unchanged": unchanged, "removed": removed}


def prefixes_for(path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    prefixes = []
    for site in data.get("sites") or []:
        prefixes.extend(site.get("allow_prefixes") or [])
    return prefixes


def url_allowed(url: str, prefixes: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return any(url.startswith(prefix) for prefix in prefixes)
