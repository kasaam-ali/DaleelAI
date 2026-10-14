"""Index the official web seed into Qdrant `web_pages` only.

Run: docker compose run --rm --no-deps backend python scripts/index_web_pages.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
backend = HERE.parents[1]
if not (backend / "pipeline").is_dir():
    backend = HERE.parents[1] / "backend"
sys.path.insert(0, str(backend))

from pipeline.web_pages import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
