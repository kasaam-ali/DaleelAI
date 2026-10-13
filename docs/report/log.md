# Progress log

Built, broke, learned. Newest entry first. A new session should read this file, then `docs/PLAN.md` section 13 (roadmap).

## Status

| Phase | State |
|---|---|
| 0 Setup | Code done (merged in PR #1). Left: ADRs for this phase |
| 1 Data and retrieval | In progress: catalog and download done (step 1 of 6) |
| 2-9 | Not started |

Deferred on purpose:
- Railway deploy and RAM measurement (PLAN Phase 0 step 9): measure RAM locally with `docker stats` at the end of Phase 1, when the embedding and reranker models are loaded; deploy to Railway in Phase 3 (M1).
- User survey (Google Form): skipped for now. Until it runs, the eval set uses written and synthetic questions only, and the test split is frozen only after the survey questions are added.

## 2026-10-13: Phase 1, catalog and download

### Built
- `backend/pipeline/catalog.csv`: 100 rows, one per document version. 31 active, 1 pending (Companies Act 2017), 45 superseded, 14 incorporated amendment ordinances, 5 expired amnesty schemes, 4 excluded (Urdu translations, a byte-identical duplicate, internal FBR service rules). Every row has a pinned sha256.
- `backend/pipeline/catalog.py`: loader and validator. Rules: unique ids, known statuses, https URLs, superseded rows point at an active row, and one active version per law per tax year.
- `backend/pipeline/download.py`: copies local files or downloads from FBR into `data/docs/<doc_id>.pdf`, rejects non-PDF responses, checks sha256 (`--pin` records new ones, `--all` also checks non-indexed rows). 2 s delay between requests.
- Downloaded 21 official PDFs (331 MB): the Income Tax Ordinance, Sales Tax Act, Federal Excise Act and Customs Act amended up to 30.06.2026; Income Tax Rules up to 15.09.2026; Sales Tax Rules up to 31.07.2026; Federal Excise Rules up to 16.09.2026; Finance Acts 2025 and 2026; withholding tax rate cards for TY2026 and TY2027; FBR circulars explaining Finance Act 2026; and the TY2026 versions.
- `data/` is mounted into the backend container at `/data` (`DATA_DIR`). `httpx` moved from dev to main dependencies. 26 tests.

### Learned
- A law needs one version per tax year, not just "latest": TY2026 answers must come from the law as it stood in TY2026. The catalog now has `work_id` (the law) and `tax_years` (which years a version answers), and retrieval filters on `tax_years` (SPECS section 5). Eval gold uses `work_id` + section so it survives new consolidations.
- File names lie: `sales tax 1.pdf` and FBR's "UpdatedUpto06-08-2025" file are the same document, and its cover says "updated up to 30 June 2025". Dates in the catalog come from cover pages.
- FBR's site blocks requests from cloud servers but works from the laptop. SECP returns 403 to scripts, so the Companies Act is a manual download.
- Sales Tax Special Procedures and Withholding Rules have no consolidation newer than 2015; later changes are only in SROs.

### Next
1. Save the Companies Act 2017 (updated 18.08.2022) from the SECP page in the catalog notes as `data/raw/companies_act_2017.pdf`, set its row to `active`, run `python -m pipeline.download --pin`.
2. Extraction (pymupdf4llm + v1 OCR path), section-aware chunking, contextual headers, dedupe.
3. Index into Qdrant (dense + BM25), reranker comparison.
4. Web library first crawl, action links, eval set v1, v1.0 baseline numbers.

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
