# Progress log

Built, broke, learned. Newest entry first. A new session should read this file, then `docs/PLAN.md` section 13 (roadmap).

## Status

| Phase | State |
|---|---|
| 0 Setup | Skeleton completed on disk (health, compose, CI, config placeholders). Git join / tag / history scan skipped for now |
| 1 Data and retrieval | Catalog and download done. 32 active docs chunked and indexed. Qdrant `documents` has 18,600 points, 0 failures. Other scans not OCR'd. |
| 2 Agentic RAG and API | In progress. The backend image was rebuilt with `langgraph` and `psycopg`. `/health` reports corpus `9a59fef60e481ac3`. Parent sections are in Postgres (6,080 rows). `web_pages` has a 24-point seed. Token streaming, server PII redaction, and `POST /api/v1/feedback` are in. Confidence fitting, reranker comparison, and eval set v1 are still open. |
| 3 Chat UI | In progress. Browser PII redaction, onboarding profile, and the chat page are in. Feedback can be saved. Not deployed. |
| 4 Tax tools | Built. TY2026 and TY2027 rules, the calculator, the filer comparison, the labeling guidelines, and the four-key LLM fallback are in. Slab-boundary tests passed. |
| 5 Notice and checklists | Built. Notice uploads are read in memory, personal numbers are redacted before any model call, and the five checklists save progress for the session. |
| 6 Expert finder | Built. Word TF-IDF logistic regression is served as int8 ONNX. Human-written macro-F1 is 0.986. The Find an Expert page, city filter, and retrieval domain boost are in. SetFit and zero-shot mDeBERTa were not trained: the image has no torch. |
| 7 Updates agent | Built. Saved replay and a live fetch option, the updates feed, crawl change detection, and the privacy page are in. A scrape or crawl that returns nothing leaves the previous rows in place. |
| 8-9 | Not started |

Deferred on purpose:
- Railway deploy and RAM measurement (PLAN Phase 0 step 9): measure RAM locally with `docker stats` at the end of Phase 1, when the embedding and reranker models are loaded; deploy to Railway in Phase 3 (M1).
- User survey (Google Form): skipped for now. Until it runs, the eval set uses written and synthetic questions only, and the test split is frozen only after the survey questions are added.
- Full-corpus PDF extraction and chunking (Phase 1 step 3): stopped on 2026-10-13. Tesseract sat at 100% CPU on one scanned page for over an hour. Digital Acts already extracted (Income Tax Ordinance, Sales Tax Act, Federal Excise Act, Customs Act, Income Tax Rules) stay in `data/extracted/`. Resume later with OCR off, or OCR only the few scanned pages.

### Next
1. Collection `documents` still has 18,600 points. Do not delete it. Do not resume the documents indexer unless the chunks change.
2. Still open: confidence fitted on the dev set, reranker comparison, and eval set v1. `web_pages` is 30 points: the original seed, saved SECP, SRB, and BRA pages, and the three replay notices. `documents` is still 18,600. Do not delete it.
3. Phase 3 deploy is still open: backend on Railway, frontend on Vercel. The chat page on the host is `http://localhost:5174/`.
4. Every LLM role tries Groq, then `GEMINI_API_KEY` (3.8 then 2.5), then the same Gemini models on `GEMINI_API_KEY_2`, then OpenRouter. If every judge is down after draft tokens, the stream ends with `verified: false`, confidence low, `final`, and `done`.
5. The served classifier is the word TF-IDF model in `backend/ml/reports/classifier_metrics.json`. The ONNX file is gitignored. A checkout without that file uses the keyword rules. The same model tags each new FBR update.

## 2026-10-14: Updates agent

### Built
The FBR scraper reads a saved listing by default and can fetch a live page with a timeout. If that parse returns zero items, it exits with an alarm and does not delete stored updates. `POST /internal/notifications/ingest` (shared token) writes the `notifications` table, tags a domain with the ONNX classifier, and stores an English and Roman Urdu summary that does not invent a tax rate. New chunks are upserted into `web_pages` only. An empty crawl is an alarm, and a page is removed only when the crawl names it.

The Updates page filters by domain and has a saved-replay button. Chat `updates` returns those cards. Privacy and sources is a page. `contracts/openapi.json` was exported again. Saved SECP, SRB, and BRA pages were added to `web_pages`.

### Broke
The FBR department listing is drawn by JavaScript, and this image has no Playwright browser, so a plain fetch of that page parses zero items. The homepage's static download links still parse. Replay does not need the live site.

### Learned
If a partial crawl treated every URL it did not send as removed, it would wipe the library. Removals are explicit. `documents` stayed at 18,600. `web_pages` went from 24 points to 30.

Checks: ruff clean, pytest 207 passed, frontend 37 passed, typecheck and lint clean. The backend container was not recreated.

## 2026-10-14: Expert finder and classifier

### Built
1,608 synthetic questions and 72 human-written questions, in English and Roman Urdu, across the six domains and both complexity levels. The synthetic test (336) and the human test are scored apart. Word n-grams and character n-grams both reach human macro-F1 0.986 and synthetic macro-F1 1.0. The word model is served. It is an int8 ONNX matrix, 62 KB with the vocabulary file, under the 300 MB cap. Accuracy, per-language F1, the confusion matrix, and latency are in the metrics file and on the Evaluation page.

The same model feeds the 1.2 retrieval boost when confidence is high enough, and a notice that should go to an expert carries that category. The directory is 13 public firm listings with city, specialties, source, last updated, a removal contact, and the not-an-endorsement line. `POST /api/v1/experts/find` and the chat `find_expert` card use it. A simple question returns no listing and points back to chat.

### Broke
The first ONNX export was a text pipeline. The slim image has no `en_US.UTF-8` locale, so the runtime refused to load it. TF-IDF now stays in Python and only the linear weights are quantized.

### Learned
SetFit and mDeBERTa need torch, which this image does not have, so they are listed as not trained rather than given a fake score. The two logistic models tied, and the word model is faster (0.23 ms vs 0.50 ms on the human set).

Checks: ruff clean, pytest 202 passed, frontend 37 passed, typecheck and lint clean. No image rebuild. Qdrant was not touched. The first live search created the experts table and stored the 13 listings.

## 2026-10-14: Notice explainer and checklists

### Built
A PDF or image notice is checked for type, size, and page count, read with PyMuPDF (Tesseract only if the page has almost no text), and the personal numbers are replaced before any model call. The page image is masked in memory and never written to disk. Eighteen synthetic notices are in `backend/tests/fixtures/notices.json`. The five checklists are NTN, AOP or company NTN, sales tax, SECP, and an income tax return. A freelance NTN answer adds a PSEB step with no invented URL. Progress is stored in Postgres when the database is configured, and the page also keeps it in localStorage.

### Broke
FastAPI file upload needs `python-multipart`. It was missing from the image, so the route could not load until it was installed in the running container and added to the lockfile.

### Learned
PyMuPDF's markdown export puts a whole notice on one line. The name redactor used to read up to 80 characters with no newline, which swallowed the demanded amount. It now stops before the next field label.

## 2026-10-14: Four API keys in the LLM fallback

### Built
Each role now tries Groq, then Gemini 3.8 and 2.5 on `GEMINI_API_KEY`, then those same models on `GEMINI_API_KEY_2`, then OpenRouter. A failed Gemini call cools down that key only, so the second key is still tried.

### Learned
Cooldown was stored by model id. Listing `gemini-3.8-flash` twice would have skipped the second key. The suffix on the config entry keeps the two attempts apart, and the call sends that entry's key.

## 2026-10-14: Tax rules and calculators

### Built
TY2026 and TY2027 rules in `backend/app/core/tax_rules/`. Salary slabs come from the Income Tax Ordinance schedule and the Finance Act 2026 substitution. Section 4AB is 9 percent of salary tax above Rs 10,000,000 for TY2026, and no salary surcharge for TY2027. Freelancer rates cover PSEB export, other export of services, and domestic IT services. Property uses sections 236C and 236K. Late filer rates are only on TY2026 property. Filer comparison also covers vehicle registration, the annual vehicle tax, dividends, and profit on a bank deposit.

The engine, four API routes, chat cards for `calculate` and `compare_filer`, and the Calculator and Filer pages are in. `contracts/openapi.json` was exported again. Labeling rules are in `backend/ml/labeling_guidelines.md`.

### Learned
The TY2027 withholding card has no late-filer column, so a late-filer property request for that year returns 400. A rupee just above a salary boundary can round back to the same tax. The tests still check that step.

Checks: ruff clean, pytest 184 passed. No image rebuild. Qdrant and Postgres were not touched.

## 2026-10-14: Judge failure keeps the draft

### Built
`verify_answer` catches `AllProvidersUnavailable`. The draft stays, `verified` is false, and confidence is low. The chat stream still emits `verification`, `final`, and `done` when tokens were already sent. A failure before any token still emits `error` then `done`.

### Learned
A 503 on the judge means the check did not finish. The draft the user already saw should close as an unverified answer, not as a failed search.

## 2026-10-14: Gemini Flash 3.8 then 3.6

### Built
Replaced `gemini-3.5-flash` and `gemini-3.5-flash-lite` in `backend/config/models.yaml`. Each Gemini slot is now `gemini-3.8-flash`, then `gemini-3.6-flash`, then `gemini-2.5-flash` where a third fallback already existed. Groq and OpenRouter stay in the same places.

### Learned
Both 3.6 and 3.8 are offered by the Gemini API. A judge probe got HTTP 503 from 3.6, then `gemini-3.8-flash` replied `ok` with fallback true. 3.8 is first so a live call does not wait on that 503.

## 2026-10-14: Backend rebuild, sections, feedback, web seed

### Built
Rebuilt the backend image with `docker compose up -d --build backend`. Postgres and Qdrant were not recreated and no volume was wiped. `/health` now reports corpus version `9a59fef60e481ac3`. `scripts/load_sections.py` loaded 6,080 parent sections from the chunk files into Postgres in 3.8 seconds, 0 failures. It does not touch Qdrant.

`POST /api/v1/feedback` stores a rating in Postgres. The server redactor in `app/core/privacy/pii.py` matches `contracts/pii_cases.json`. Chat redacts the question before the model sees it, and a saved turn stores `CNIC [CNIC]`. `contracts/openapi.json` was exported again.

`scripts/index_web_pages.py` wrote 24 points into Qdrant `web_pages` only. FBR, KPRA, and PRA were fetched. IRIS used the short fallback paragraph. `documents` stayed at 18,600 before and after. Draft tokens stream on `POST /api/v1/chat`. A model that dies mid-stream is discarded and the next model is tried, so a partial draft is not mixed with the fallback.

### Broke
The first save of a live turn passed the final event object into `save_turn` and Postgres rejected it. The helper now writes the answer fields. A later live question streamed tokens and then ended on an `error` event after `gemini-3.5-flash` returned 503 for the judge. A direct judge probe still answered from `gemini-2.5-flash`.

### Learned
The file watcher reloads the API when tests change, which drops the in-memory answer cache and loads the embedding models again on the next question. `ruff format` also wanted `pipeline/index.py` on one line. That file had not been edited for behavior.

Checks: `ruff check`, `ruff format --check`, and pytest in the new container. 164 passed. Smoke: `/health` 200 with corpus `9a59fef60e481ac3`. One chat returned `meta`, token events, `sources`, `verification`, `final`, `done`. Feedback POST returned 201. Sections 6,080. `documents` 18,600. `web_pages` 24.

## 2026-10-14: Qdrant index finished

### Built
The resumed indexer finished. `data/index_qdrant.log` ends with `indexed 15247 points this run, failed 0, collection count 18600`. Companies Act 2017 and the remaining small documents were included. `sro_80_2023` was already stored, so it was skipped. The collection was not deleted.

### Learned
A long document can sit several minutes between log lines, because progress prints every 2,000 chunks. The process was still at full CPU during those gaps.

## 2026-10-14: Chat page, PII redaction, onboarding

### Built
Browser redaction in `frontend/src/lib/pii.ts` covers CNIC, labeled NTN, phone, email, IBAN, and labeled account numbers. `25000000` stays. Shared cases live in `contracts/pii_cases.json`. The three profile questions and an anonymous session id sit in localStorage and go out with each chat request (`X-Session-Id`). The chat page streams `POST /api/v1/chat` and shows the library stamp, confidence, verified state, citations, official links, and feedback. English and Roman Urdu strings are JSON. Rupee amounts from 1 lakh up get a lakh or crore hint.

### Broke
Nothing in the indexer. The feedback route does not exist yet, so a click there fails in the open.

### Learned
A grouped amount like `Rs 1,800,000 (18 lakh)` can be matched as a shorter prefix (`1,800,00`) if the hint check is only a lookahead. The annotator now keeps an existing parenthesis and skips a second hint. `+` is not a word character, so a phone pattern needs a lookbehind or it misses a number at the start of the text.

Host checks: 37 unit tests passed, oxlint clean, `tsc -b` clean, production build succeeded. Changing one profile field no longer clears the other two. A health check that does not answer within 5 seconds shows that the tax service is unreachable. No container was rebuilt or restarted.

## 2026-10-14: Borderline grade, live adapters, LangGraph wrapper

### Built
Borderline band uses `sufficiency.sufficient_at` 0.7 and `borderline_at` 0.4 from `settings.yaml`. Those numbers are config knobs. SPECS does not fit them on a dev set yet. In that band, one fast call grades the context. If it says no, one fast call writes a broader query and searches the verified library again. A second borderline result is not graded again. Then the web library is searched with those same queries. No web LLM rewrite.

`LiveQa` is attached when the vector store adapter is `qdrant`. It does not open Qdrant, load FastEmbed, or connect to Postgres until the first question. Search is hybrid dense plus BM25 with server-side RRF, filtered by tax year. It does not create or delete collections. A missing `web_pages` collection returns no hits. Postgres parent lookup is a SELECT. A missing driver or table returns no rows, and expansion keeps the chunk text.

`langgraph` and `psycopg[binary]` are in `backend/pyproject.toml`, and `uv.lock` was updated. The running image was not rebuilt. `run_qa_graph` uses a StateGraph with the nine QA nodes when the package imports, and calls `run_qa` when it does not. The graph test passed in a throwaway container after `uv sync`. The indexer container was not restarted.

### Broke
Nothing in the indexer. One-off tests do not include the packages until a rebuild, so the suite there skips the installed-graph test.

### Learned
The dev image used by `docker compose run` did not have FastEmbed or the Qdrant client. The indexing container does, because that process has been embedding. A rebuild is what puts the new lock into a fresh image. Loading those models a second time inside the indexing container is a memory risk.

Tests: `ruff check`, `ruff format --check`, and pytest in a one-off container. 127 passed, 1 skipped (langgraph absent). With langgraph installed in a separate throwaway container, the graph test passed.

## 2026-10-14: Backend started, indexing resumed

### Built
`daleelai-backend-1` was exited (code 1, file watcher out of memory). Started that same container again. Health returned ok. The indexer was started detached and appended to `data/index_qdrant.log`. It skipped 3,353 points already in `documents`, including the whole Income Tax Ordinance, then kept upserting. The collection was not deleted.

### Learned
The earlier log line of 2,059 was stale. Qdrant had 3,353 points when the container died. Resume reads Qdrant, not the log.

## 2026-10-14: Phase 2 router through SSE

### Built
Quoted `${QDRANT_URL}` and `${QDRANT_API_KEY}` in `backend/config/settings.yaml`. Inside `{...}` the bare `${...}` is invalid YAML, so the backend could not load settings.

Router (`backend/app/agents/router.py`): one `fast` call, temperature 0, JSON checked with `RouterOutput`. Urdu script forces `language: urdu`. If every provider fails, keyword lists pick the intent. Bad JSON is an error, not a silent keyword route.

Retrieval helpers, no network: synonym expansion (whole word, max 6 terms), reciprocal rank fusion with k=60 (SPECS does not set k) plus a 1.2 domain boost, action links (max 3, empty URLs omitted), parent-section expansion on a 6,000-token budget (4 characters per token until a real tokenizer is wired), web sufficiency floor 0.5. Verified sufficiency takes its two thresholds as arguments.

`run_qa` runs the node order without LangGraph: verified library, else web library, else the v1 abstain sentence. Generate is one reasoning call. Verify is one judge call. More than half unsupported replaces the draft. Web answers are never `verified`. Call budget cap is 5. LLM cache and answer cache use sha256 keys from SPECS section 4. The LLM cache key is role + messages + params, because the gateway picks the model inside the call.

`POST /api/v1/chat` streams SSE. `meta` is first and `done` is last. With no QA runner the answer abstains and does not call Qdrant. Confidence is a stand-in: medium for an answer, low for abstain. It is not the dev-set logistic model. Contracts were exported. The contracts CI job now runs the check inside the backend env.

Tests in a one-off container (`docker compose run --rm --no-deps`). The exited backend service was not started. Unit tests: 102 passed. Chat stream tests passed after that.

### Broke
Indexing was already stopped before this session. `daleelai-backend-1` had exited with code 1. The last log line is a file-watcher out-of-memory error. The collection was not deleted and the container was not started.

### Learned
The keyword route only sees the current message. History rewrite needs the model. Chitchat is only a short greeting, so "hi what does section 149 say" stays `qa`. A cache hit can skip the router only when the request already names the tax year. LangGraph is not in `pyproject.toml`, and the serving image would need a rebuild before that import works.

## 2026-10-13: Index script and Phase 2 handoff

### Built
`scripts/index_qdrant.py` (the container copy is `backend/scripts/index_qdrant.py`) skips chunk ids already in Qdrant, upserts in batches of 64, and prints progress every 2,000 chunks. The run was started detached. It resumed from 1,867 points. Corpus version `9a59fef60e481ac3`. The collection was not deleted.

Command: `docker compose exec -T backend python scripts/index_qdrant.py`

Live log (gitignored): `data/index_qdrant.log`

### Next chat
Start Phase 2 (PLAN section 13): router with structured output and keyword fallback; LangGraph RAG (rewrite, retrieve, rerank, expand, sufficiency, web fallback, generate, verify, action links); SSE chat and contract export; call budget, LLM cache, answer cache. Retrieval quality depends on the index finishing. Check the log before calling Qdrant for answers.

## 2026-10-13: Qdrant index started

### Built
`pipeline/index.py` upserts active chunks into Qdrant collection `documents`: dense `BAAI/bge-small-en-v1.5` (384, cosine) and sparse `Qdrant/bm25`. The embedded string is the header plus the text. Payload matches the spec, including `work_id`, `tax_years` and `corpus_version`. A rerun uses the same point ids.

### Learned
Embedding on this machine is about 6 chunks a second at full CPU. The full 18,600 chunks would take about 45 minutes, so the run was stopped with 1,867 points saved. The collection was not deleted. The standalone script now skips those points instead of embedding them again.

## 2026-10-13: All active documents chunked

### Built
Chunked the other 30 active documents with the same chunker. 32 files in `data/chunks/`, 18,600 chunks in 43 seconds. Nothing failed. Qdrant was not started.

### Learned
Income Tax Rules updated to 15 September 2026 dropped 242 pages that had no usable text. Finance Act 2025, which is almost entirely scanned and was not OCR'd, produced 2 chunks.

## 2026-10-13: Contents headings no longer stick

### Built
A contents entry is a heading followed by a page number. Those schedule, part and chapter lines are ignored. A new chapter also clears the previous part. Section 4 of the Income Tax Ordinance is now "Chapter II Charge Of Tax", not the Fifteenth Schedule. The two sample chunk files were rewritten: Ordinance 2,638 chunks, Sales Tax Rules 747 chunks.

### Learned
The contents page lists every schedule before the Ordinance text. Leaving the last of those set made the whole Act look like the Fifteenth Schedule.

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
