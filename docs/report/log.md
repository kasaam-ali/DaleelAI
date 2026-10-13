# Progress log

Built, broke, learned. Newest entry first. A new session should read this file, then `docs/PLAN.md` section 13 (roadmap).

## Status

| Phase | State |
|---|---|
| 0 Setup | Code done (merged in PR #1). Left: user survey (Kasaam), ADRs for this phase |
| 1 Data and retrieval | Next |
| 2-9 | Not started |

Deferred on purpose:
- Railway deploy and RAM measurement (PLAN Phase 0 step 9): measure RAM locally with `docker stats` at the end of Phase 1, when the embedding and reranker models are loaded; deploy to Railway in Phase 3 (M1).

## 2026-10-13: Phase 0

### Built
- Reviewed PLAN and SPECS and fixed:
  - NTN regex matched every 8-digit number, so rupee amounts like `25000000` would have been redacted. Bare numbers now count as NTN only after a label.
  - `bge-reranker-base` (about 1.1 GB) did not fit the 1.5 GB RAM target. The default is now `ms-marco-MiniLM-L-12-v2`; Phase 1 compares both.
  - Classifier must be int8 ONNX under 300 MB.
  - Router now also writes the English search query, so a normal question is 3 LLM calls (cap 5) instead of 4 (cap 6).
  - Parent sections moved from a vectorless Qdrant collection to a Postgres `sections` table.
  - Tax rules gained the section 4AB surcharge and an optional late-filer category (values still to be verified against the law).
- Git: folder joined to `github.com/kasaam-ali/DaleelAI`, baseline tagged `v1.0`, source PDFs untracked (still on disk in `data/`). No Groq key found in history.
- `.gitignore` rewritten; its `data/` line had been saved as UTF-16 and was ignored by git.
- Backend skeleton (`backend/`): FastAPI `/health`, YAML settings with `${ENV}` expansion, LLM gateway (`app/adapters/llm_litellm.py`) with ordered fallback per role, skip on missing key, 60 s cooldown per failed model, fake LLM adapter, 12 tests.
- Scripts: `python -m scripts.llm_smoke` (one real call per role), `python -m scripts.list_models` (flags configured models the provider no longer offers).
- Frontend skeleton (`frontend/`): Vite 8, React 19, TypeScript, Tailwind 4, TanStack Query, landing page showing API status.
- `docker-compose.yml`: backend, frontend, Postgres 16, Qdrant 1.15.4. CI in `.github/workflows/ci.yml` (ruff, pytest, oxlint, build), green on PR #1.

### Broke
- Windows Smart App Control blocks newly released native Python wheels (`pydantic_core`, `tiktoken`, `regex`, ...). Fix: the backend runs in Docker locally. Node tools on the host are not affected.
- Old Groq key returned 401; replaced. Groq no longer offers Llama 3.x (404); switched to `openai/gpt-oss-120b` and `gpt-oss-20b`.
- Gemini 3.5 Flash returned 503 (overloaded) on most calls today; Gemini 2.5 Flash added as a fallback for reasoning and judge.

### Learned
- Free-tier model ids change within months; `scripts/list_models` should be run when calls start failing.
- Phase 0 check passed: with `GROQ_API_KEY` removed, every role answered from Gemini.

### How to run
- Start everything: `docker compose up -d`, then open http://localhost:5173 (API at http://localhost:8000/health).
- Backend checks: `docker compose run --rm --no-deps backend sh -c "ruff check . && pytest -q"`.
- Keys live in `.env` (git-ignored): `GROQ_API_KEY`, `GEMINI_API_KEY`, `GEMINI_API_KEY_2` (unused), `OPENROUTER_API_KEY`. The current keys were pasted in chat; rotate them.

### Next (Phase 1)
1. `backend/pipeline/catalog.csv` and `download.py`.
2. Corpus cleanup: latest consolidated Acts and Rules only, add Finance Acts 2025 and 2026, Companies Act 2017, SECP guides.
3. Extraction (pymupdf4llm + v1 OCR path), section-aware chunking, contextual headers, dedupe.
4. Index into Qdrant (dense + BM25), reranker comparison.
