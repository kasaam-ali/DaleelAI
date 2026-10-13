"""Index chunk files into Qdrant. Resumes, upserts in batches, prints every 2000 chunks.

The backend container only mounts ./backend, so the copy that actually runs is
backend/scripts/index_qdrant.py. This file is the same script.

From the repo root:
    docker compose exec -T backend python scripts/index_qdrant.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
backend = HERE.parents[1]
if not (backend / "pipeline").is_dir():
    backend = HERE.parents[1] / "backend"
sys.path.insert(0, str(backend))

from pipeline.index import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
