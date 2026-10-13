# Progress log

Built, broke, learned. Newest entry first. A new session should read this file, then `docs/PLAN.md` section 13 (roadmap).

## Status

| Phase | State |
|---|---|
| 0 Setup | Skeleton completed on disk (health, compose, CI, config placeholders). Git join / tag / history scan skipped for now |
| 1 Data and retrieval | Catalog and download done. 32 active docs extracted. Finance Act 2026 scanned pages OCR'd and rechunked (531 chunks). Other scans not OCR'd. Qdrant not started. |
| 2-9 | Not started |

Deferred on purpose:
- Railway deploy and RAM measurement (PLAN Phase 0 step 9): measure RAM locally with `docker stats` at the end of Phase 1, when the embedding and reranker models are loaded; deploy to Railway in Phase 3 (M1).
- User survey (Google Form): skipped for now. Until it runs, the eval set uses written and synthetic questions only, and the test split is frozen only after the survey questions are added.
- Full-corpus PDF extraction and chunking (Phase 1 step 3): stopped on 2026-10-13. Tesseract sat at 100% CPU on one scanned page for over an hour. Digital Acts already extracted (Income Tax Ordinance, Sales Tax Act, Federal Excise Act, Customs Act, Income Tax Rules) stay in `data/extracted/`. Resume later with OCR off, or OCR only the few scanned pages.

### Next
1. Done: Companies Act 2017 (updated 18.08.2022, 418 pages) saved by hand as `data/raw/The-Company-Act-2017-updated-18.8.2022.pdf`, now active and pinned. 32 active documents, none pending.
2. Sample chunks of the Income Tax Ordinance (30 June 2026) and Sales Tax Rules (31 July 2026) are saved. The Ordinance path is wrong: the contents list sets Fifteenth Schedule and later sections stay inside it. Next, when asked: fix that schedule scope, then the other documents. Qdrant is not started.
3. Index into Qdrant only after extraction is resumed.
4. Web library first crawl, action links, eval set v1, v1.0 baseline numbers.

## 2026-10-13: Sample chunks, two documents

### Built
Chunk files saved for the Income Tax Ordinance amended to 30 June 2026 (2,724 chunks, 665 sections) and the Sales Tax Rules updated to 31 July 2026 (707 chunks, 320 sections). No other document was chunked.

### Learned
The Ordinance contents page lists the Fifteenth Schedule before section 4. The chunker never leaves a schedule, so section 4, section 12, section 149 and section 113 are all labeled as inside the Fifteenth Schedule. Sales Tax Rules 12B and 14 are labeled correctly.

## 2026-10-13: Chunker headings and rate-card headers

### Built
A footnote glued to a rule is removed only when that number is a footnote on the same page. `8612B.` becomes rule 12B, and `87[Filing of returns` becomes rule 14. A real rule such as 150H is left as it is. A rule number on its own line is joined to the title on the next line.

The withholding rate card header is repaired where the column names were split across cells (`Non-ATL Rates` / `Late Filer` / `Reference`). Split table chunks repeat that header. Sales Tax Rules, 31 July 2026, now has 310 section headings (was 73) and every chunk carries a section number.

### Learned
The TY2026 rate card's late-filer cell is empty on the section 148 rows in the PDF itself. Later pages still merge some columns, so those rows were not relabeled.

## 2026-10-13: Finance Act 2026 scanned pages

### Built
Targeted OCR of Finance Act 2026 pages 77-255. The trial on pages 77-81 was not saved, so those five pages were included. 179 pages, 0 failures, 1.38 seconds per page, 251 seconds total. Each successful page is marked source "ocr". The old 20-character gate would have skipped these pages, because the gazette banner is about 60 characters. `--ocr-scanned` uses the 150-character scanned class instead.

Rechunk of this document only: 531 chunks (was 177). The extra 354 chunks are the OCR pages. 256 pages used, 0 dropped, 0 exact duplicates, 1 near duplicate. Section numbers are still empty: this Act is schedule and amendment text, not "149. Salary." headings, so each parent is still one page.

### Next
Chunker footnote and table-header fixes are not started. Other scanned documents (Finance Act 2025, both Income Tax Rules, Federal Excise Rules, SRO 1515) were not OCR'd. Qdrant indexing is not started.

## 2026-10-13: Page classification

### Learned
Audit threshold galat tha, scanned pages miss hue. A page with under 20 characters was counted empty, so a scanned gazette page that still had a 60-character banner looked fine. The report now classes each page before OCR: digital when the text layer has at least 150 characters, scanned when it is shorter and the page has an image, blank when it is shorter and has no image. `python -m pipeline.extract --classify` prints the counts and scanned ranges without writing `data/` or calling Tesseract.

### Next
Targeted OCR is not started. Finance Act 2026 pages 77-255 are scanned. Finance Act 2025, both Income Tax Rules versions, the latest Federal Excise Rules, and SRO 1515(I)/2021 are also above 5 percent scanned.

## 2026-10-13: Phase 0 skeleton fill-in

### Built
- Filled remaining v2 layout that was still missing: `backend/config/web_sources.yaml`, `action_links.yaml`, full `settings.yaml`, `app/api/v1/` placeholder, `core/services/`, `agents/`, `ml/`, `eval/`, Protocol stubs, fake adapters, scrapers stubs, `contracts/`, `scripts/export_contract.py`, `docs/adr/`.
- `/health` now returns liveness plus stub corpus/model versions. Frontend Chat page is a disabled placeholder.
- Official URLs only where confirmed this session (FBR, IRIS, KPRA, PRA IRIS). SECP / SRB / BRA left as TODO with empty URLs. No fake live links.
- Node: `frontend/package.json` `engines.node` is `>=20.19.0` (Vite 8). This machine currently has Node 24.20.0, so the frontend typechecks on the host. If a laptop is still on Node 20.11, use the compose `node:24-alpine` service.

### Skipped (do later)
- Git fetch/push/pull, reset/rebase/merge, `v1.0` tag, `git rm --cached` PDFs, history secret scan, filter/gc. Local git state left as-is.

### Next
- `docker compose up` (or backend checks inside Docker). Then continue Phase 1 extraction/index. Git join when it is no longer hanging.

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
See the deferred note above. Full extraction is skipped until OCR is limited to scanned pages only.

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
