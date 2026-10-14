"""FBR notifications scraper.

Replay is the default, so a demo does not depend on fbr.gov.pk.
`--live` fetches one page. Zero parsed items is an alarm and this process
does not delete anything that was stored before.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.updates.listing import ZeroItems, collect_listing, fetch_html, load_replay  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect FBR SROs, circulars, and notifications")
    parser.add_argument("--live", action="store_true", help="Fetch a listing page instead of the fixture")
    parser.add_argument("--url", default="https://www.fbr.gov.pk/")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        if args.live:
            items = collect_listing(fetch_html(args.url, timeout=args.timeout))
        else:
            items = load_replay()
    except ZeroItems as exc:
        print(f"alarm: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"alarm: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"items": len(items), "mode": "live" if args.live else "replay"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
