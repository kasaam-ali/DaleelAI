"""Official-site crawler with change detection.

Replay reads the saved official-page text. A live crawl that returns no real
pages exits non-zero and does not mark older pages removed.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.updates.changes import ZeroPages, detect_changes  # noqa: E402
from pipeline.web_pages import replay_pages  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crawl allowlisted official tax pages")
    parser.add_argument("--live", action="store_true", help="Fetch seed pages instead of the saved text")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        fetched = replay_pages() if not args.live else _live(args.timeout)
        plan = detect_changes(fetched, {})
    except ZeroPages as exc:
        print(f"alarm: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"alarm: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "new": len(plan["new"]),
                "changed": len(plan["changed"]),
                "unchanged": len(plan["unchanged"]),
                "removed": len(plan["removed"]),
            }
        )
    )
    return 0


def _live(timeout: float) -> list[dict]:
    from app.core.updates.listing import fetch_html
    from pipeline.web_pages import SEEDS, html_to_text, page_is_usable
    import hashlib

    fetched = []
    for page in SEEDS:
        if not page.get("seeds_live", True):
            continue
        try:
            text = html_to_text(fetch_html(page["url"], timeout=timeout))
        except Exception:
            continue
        if not page_is_usable(page["title"], text):
            continue
        fetched.append(
            {
                "url": page["url"],
                "title": page["title"],
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text": text[:8000],
            }
        )
    return fetched


if __name__ == "__main__":
    raise SystemExit(main())
