"""Load parent sections into Postgres. Does not read or write Qdrant.

Run: docker compose exec -T backend python scripts/load_sections.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
backend = HERE.parents[1]
if not (backend / "pipeline").is_dir():
    backend = HERE.parents[1] / "backend"
sys.path.insert(0, str(backend))

from pipeline.sections import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
