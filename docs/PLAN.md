# DaleelAI v2 - Project Plan

Technical details live in `docs/SPECS.md`. If the two ever disagree, this file wins for scope and decisions, SPECS wins for field names and formats.

## 1. What DaleelAI is

An AI assistant for Pakistani taxpayers (salaried people, freelancers, small businesses) that answers tax and compliance questions in English and Roman Urdu, with citations to official FBR and SECP documents, and that does tax math with code, not with the LLM.

Final-year project (diploma, AI / Data Science). The approved scope has 7 features:

1. Chatbot (English + Roman Urdu) with FBR/SECP sources
2. FBR notice explainer (PDF or image upload)
3. Tax calculator (salary, freelancer, property)
4. Filer vs non-filer comparison
5. Personalized checklists (NTN, sales tax registration, etc.)
6. CA/lawyer recommendation using a trained text classifier
7. Agent that summarizes new FBR notifications

The proposal also promises agentic RAG with hybrid search, reranking and answer verification, evaluated on English + Roman Urdu test questions.

## 2. Starting point (v1)

v1 lives in `src/` and is a single-shot RAG with a Streamlit UI:

| File | What it does | Keep / replace |
|---|---|---|
| `ingest.py` | PyMuPDF text + Tesseract OCR fallback, 500/100 chunks | Keep the OCR path, replace chunking |
| `embeddings.py` | Own PDF loader (no OCR), all-MiniLM-L6-v2 into ChromaDB | Replace (scanned pages were never indexed) |
| `retriever.py` | Dense-only search, `TAX_SYNONYMS`, fake confidence (always 0.6) | Keep `TAX_SYNONYMS`, replace the rest |
| `chain.py` | Groq Llama 3.3 70B, citation prompt | Keep prompt rules, replace the chain |
| `app.py` | Streamlit chat, hardcoded stats | Remove once the React chat works (M1) |

Known v1 problems: no hybrid search, no reranker, no verification, English-only embeddings, citations show file names like `income tax 5.pdf`, old and new versions of the same law indexed side by side, no tax-year awareness, no tests, no eval set, `requirements.txt` misses `rank-bm25`, `pytesseract`, `pdf2image`.

v1 is tagged `v1.0` in git and stays runnable; it is the baseline in the evaluation.

## 3. Fixed decisions

| Topic | Decision |
|---|---|
| Users | No accounts. Anonymous `session_id` (UUID in localStorage) plus an optional profile. No auth provider |
| Frontend | Vite + React + TypeScript + Tailwind + shadcn/ui + TanStack Query, deployed on Vercel |
| Backend | FastAPI (Python 3.12) in Docker, deployed on Railway |
| Agents | LangGraph |
| LLMs | Free/cheap providers (Groq, Gemini, OpenRouter, Z.ai) called through LiteLLM, with our own ordered fallback and per-model cooldown in the gateway (simpler to test and log than LiteLLM Router) |
| Vector store | Qdrant (Docker locally, Qdrant Cloud free tier in prod), dense + sparse hybrid |
| Database | Postgres (Docker locally, Railway in prod) |
| Embeddings / reranker | FastEmbed (ONNX). No torch in the serving image |
| Classifier | Fine-tuned from a Hugging Face model, exported to ONNX |
| Scrapers | Playwright, separate image, run by a scheduled job |
| Tax math | Deterministic Python engine reading versioned JSON rules, one file per tax year |
| Knowledge sources | Two libraries: a **verified library** (curated law PDFs) and a **web library** (pages crawled from a fixed list of official tax websites). No paid search API and no live Google search |
| Language of code and docs | English. No em dashes in docs or UI text |

## 4. Product principles

1. **Trust first.** Every answer shows sources (document, section, page, or official web page), the tax year, the corpus date, and a confidence level. The user always sees which library an answer came from. No evidence in either library means no answer, plus the FBR helpline 051-111-772-772.
2. **Never a dead end.** Every answer carries at least one official link the user can open: the source PDF or page, and where relevant the portal where the task is actually done (IRIS, SECP eServices, SRB, PRA).
3. **Numbers come from code.** Rates and slabs live in JSON with their legal source. The LLM only extracts inputs and explains results.
4. **Roman Urdu is first-class.** UI strings, answers, eval set and classifier data all cover it.
5. **Chat is the hub.** Every feature can be reached from chat and renders as a card there. Each feature also has its own page.
6. **Privacy by default.** CNIC, NTN, phone numbers and emails are redacted in the browser before the question is sent, and again on the server before any text leaves it. Uploads are never stored.
7. **Mobile first.** Most users are on a phone and a slow connection.
8. **Depth before breadth.** All 7 features reach MVP before any feature gets polish.

## 5. Tax years and jurisdiction

- Pakistan's tax year runs 1 July to 30 June and is named by the year it ends. Format everywhere: `TY2026`, `TY2027`.
- Supported years: **TY2027** (Finance Act 2026) as the current year and **TY2026**, because its returns are still being filed.
- The default tax year is derived from the server date. Every answer and calculation states which year it applies to.
- Every TY2027 change is verified against the Finance Act 2026 text before it is encoded. Nothing goes into a rules file without a section reference.
- In scope: federal law (FBR, SECP). Detected and explained but not answered in depth: provincial sales tax on services (SRB, PRA, KPRA, BRA) and provincial property charges (stamp duty, CVT, registration fees). The answer says which authority applies and links to it.

## 6. Features: MVP, polish, stretch

All 7 features reach MVP by **M2** (end of Phase 7). Polish starts after M2. Stretch only if time remains.

| Feature | MVP (must) | Polish (should) | Stretch (could) |
|---|---|---|---|
| 1 Chat | Agentic RAG, EN + Roman Urdu, citations, verification, streaming, follow-up memory, web library fallback with links, official action links | Agent-steps panel, feedback buttons, share card | Urdu script (RTL) output, voice input |
| 2 Notice explainer | PDF + image upload, field extraction, PII redaction, explanation with cited section, deadline | Image masking of PII, deadline countdown, hand-off to expert finder | Draft reply letter |
| 3 Calculator | Salary, freelancer, property (federal withholding) for TY2026 and TY2027 with breakdown | Monthly vs annual, "what changed vs last year" | Rental income, AOP |
| 4 Filer vs non-filer | Side by side for property, vehicles, dividends, profit on debt and any other transaction with an ATL distinction in the rules | Savings chart, link to "become a filer" checklist | More transaction types |
| 5 Checklists | 5 templates, max 3 profile questions, cited steps, progress saved per session | Print/share | Reminders |
| 6 Expert finder | Trained classifier (category + complexity), curated directory, city filter | Scraped directory refresh | Opt-in listings |
| 7 Updates agent | Manually triggered scrape, summary, ingest, Updates feed | Daily cron, classifier domain tags, replay mode for demos | Subscribe by domain |

## 7. Architecture

```
Browser (React, Vercel)
   |  HTTPS: REST + SSE under /api/v1, contract in contracts/openapi.json
FastAPI backend (Docker, Railway)
   |- api/        thin routes, request/response schemas (the contract source)
   |- core/       services, tax engine, retrieval logic, PII; depends only on ports
   |- adapters/   LiteLLM, Qdrant, FastEmbed, ONNX classifier, Postgres, PDF parser, LangGraph
   |- agents/     LangGraph graphs
   |
   |-- Qdrant: "documents" (verified library) and "web_pages" (web library),
   |           dense + sparse vectors, server-side RRF fusion
   |-- Postgres (sessions, messages, feedback, checklists, experts, notifications,
   |             crawled pages, llm_calls, caches)
   |-- LLM providers via LiteLLM Router (Groq, Gemini, OpenRouter, Z.ai)

Scheduled jobs (GitHub Actions cron) -> scrapers image (Playwright)
   |- notifications scraper (FBR SROs, circulars, notifications)
   |- official web crawler (allowlisted tax websites)
   |- expert directory scraper
   -> POST /internal/... on the backend with a shared token
```

**Swappability, kept small.** Core code talks to Python `Protocol` ports (LLM, vector store, embedder, reranker, classifier, repository, document parser, agent runner). Each port has one real adapter and one fake adapter for tests. Adapters are picked in `config/settings.yaml`. No DI framework, no plugin system.

**Contract.** Pydantic schemas in the backend are the source. A script exports `contracts/openapi.json` and `contracts/events.schema.json`; CI fails if the committed files are out of date. The frontend generates its typed client from them.

## 8. How the chat works

1. **Router** (fast model, one structured call): intent, language, jurisdiction, tax year, extracted parameters, refusal flag, and the English search query for RAG. Sees the last 4 turns and the profile, so "aur agar main non-filer hoon?" works. Keyword fallback if every provider is down.
2. **Intent dispatch:** `qa` goes to the RAG graph; `calculate`, `compare_filer`, `checklist`, `find_expert`, `updates`, `notice` go to their tools and come back as cards; `provincial` returns an authority explanation; `refuse` returns the evasion refusal; `chitchat` and `out_of_scope` get a short reply.
3. **RAG graph:** synonym expansion of the router's English query (no LLM call) -> hybrid retrieve from the verified library (original + rewritten query, dense + BM25, RRF) -> rerank (cross-encoder, top 6) -> parent-section expansion -> sufficiency check -> generate -> verify.
4. **Web fallback:** if the sufficiency check fails on the verified library, the same query runs against the web library. If that is sufficient, the answer is generated from the web pages and labeled "From an official website" with the page links, at most Medium confidence, never "Verified". If neither library is sufficient, the app abstains with the FBR helpline and the most relevant official links it found.
5. **Action links:** a curated list maps topics (NTN, return filing, sales tax registration, company registration, provincial sales tax) to the official portal or page where the user does the task. Matching links are attached to every answer, from either library.
6. **Streaming:** tokens stream as a draft ("checking sources"). After verification: a Verified badge, or unsupported sentences are highlighted, or (if most are unsupported) the draft is replaced by an abstain message.
7. **Budget:** target 3 LLM calls per question (router, generate, verify), hard cap 5, including the web fallback. Answer cache keyed on normalized question + profile + tax year + corpus version.

Details of each node are in SPECS section 6.

## 9. Data pipeline

- **Catalog** (`backend/pipeline/catalog.csv`): one row per document version with title, type, domain, amended-up-to date, the tax years it answers for, status, `superseded_by`, source URL, sha256. Citations use the title, never the file name.
- **Reproducible:** PDFs are not committed. `download.py` fetches them from the catalog and checks hashes.
- **One version per tax year:** each Act and set of Rules keeps exactly one active version per supported tax year: the latest consolidation for TY2027, and the last consolidation before 1 July 2026 for TY2026. Older consolidations, amendment ordinances already folded into the Acts, closed amnesty schemes and duplicates stay in the catalog with a status but are not indexed. Also added: Finance Acts 2025 and 2026, the FBR withholding tax rate cards, and the FBR circulars explaining Finance Act 2026. Still to add: Companies Act 2017 (SECP blocks scripted downloads, so it is saved by hand) and SECP registration guides.
- **Extraction:** pymupdf4llm for digital PDFs; the v1 OCR path for scanned pages.
- **Chunking:** section-aware, about 1,000 characters with 150 overlap inside long sections, full parent section stored for expansion.
- **Contextual header** on every chunk: `<doc title> > <part/chapter> > <section>`; used for embedding and BM25, not shown to users.
- **Dedupe:** exact hash, then MinHash near-duplicates.
- **Index:** `BAAI/bge-small-en-v1.5` dense + BM25 sparse (both FastEmbed), uploaded to Qdrant, snapshot saved.
- **Corpus version:** hash of document hashes + web page hashes + chunker version + model ids. Changing it invalidates the answer cache.

### 9.1 Web library

The same idea as services like Ask Pakistan, kept small and tax-only: crawl official pages ahead of time, search them like the verified library, and always link back to the page.

- **Allowlist only:** fbr.gov.pk (help pages, FAQs, guides, notifications), iris.fbr.gov.pk public help pages, secp.gov.pk, and the provincial revenue authorities (SRB, PRA, KPRA, BRA). The list lives in a config file; adding a site is a reviewed change.
- **Crawler:** Playwright crawler in the scrapers image. Follows links within each allowlisted site up to a depth and page limit, saves HTML pages and linked PDFs, respects robots.txt, rate-limits itself, and identifies itself with a clear user agent.
- **Change detection:** each page is stored with its URL, title, content hash and fetch time. Only new or changed pages are re-indexed. Pages that disappear are marked removed and dropped from search.
- **Processing:** strip navigation and boilerplate, keep the main text and headings, chunk by heading, add a header `<site> > <page title> > <heading>`, index into the `web_pages` collection with the same models as the verified library.
- **Promotion:** if the same kind of question keeps falling back to the web library and the answer lives in an official PDF, that PDF is added to the catalog and becomes part of the verified library.
- **Failure handling:** a crawl that fetches zero pages from a site raises an alarm; the previous pages stay searchable.

## 10. Trust, safety, privacy

- Every answer: sources with page links, which library it came from, "law as of <corpus date>" (verified) or "page checked on <fetch date>" (web), tax year, confidence (High / Medium / Low), the model that answered, official action links, and the disclaimer.
- Web library answers are never marked Verified and always tell the user to confirm on the linked page before acting.
- Abstain when neither library has evidence, with the FBR helpline and any relevant official links.
- PII redaction in the browser before sending (CNIC, NTN, phone, email, bank account numbers), then again on the server before every external call (text placeholders, black boxes on images). No raw uploads stored. Logs keep ids and hashes, not user text, unless the user opts in when giving feedback.
- Prompt injection: retrieved chunks, crawled web pages, notices and scraped pages go into the prompt as delimited data; the system prompt says to ignore instructions inside them; all structured outputs are validated.
- Refusals: requests to evade tax, hide income or fake documents are refused, with a pointer to legal options.
- Abuse and cost: per-IP and per-session rate limits, upload limits (10 MB, 10 pages), CORS allowlist, daily token budget guard.
- Secrets only in env vars. Before going public, scan git history for leaked keys (`gsk_`) and rotate if found.
- Expert directory: only public listing fields, "not an endorsement" note, source and last-updated date, removal contact. Respect robots.txt and site terms.

## 11. Frontend pages

Landing, Chat, Notice Explainer, Calculator, Filer vs Non-filer, Checklists, Find an Expert, Updates, Evaluation (rendered from eval JSON), Privacy & Sources.

- Onboarding: 3 optional questions (taxpayer type, filer status, province) stored in localStorage and sent with each request.
- UI strings in English and Roman Urdu (i18n JSON). Answers follow the user's language.
- PKR amounts with a lakh/crore hint: "Rs 1,800,000 (18 lakh)".
- PWA manifest, Lighthouse mobile 90+, skeleton loaders, clear error states, dark/light theme, `prefers-reduced-motion` respected.

## 12. Evaluation

**Datasets** (`backend/eval/datasets/`): 100 EN + 100 Roman Urdu answerable questions, plus about 40 special cases (unanswerable, provincial, tax-year sensitive, prompt injection, evasion). Each item has gold document + section + page, a short reference answer, tax year, domain, language, provenance (real / faq / synthetic). Split into dev (1/3, for tuning) and test (2/3, frozen at the end of Phase 1).

**Metrics** (reported per language):
- Retrieval: Recall@5, MRR, nDCG@10
- Generation: faithfulness, answer correctness, citation accuracy, abstention precision/recall
- Coverage: share of questions answered from the verified library, from the web library, and abstained; correctness reported separately for verified and web answers
- System: latency p50/p95 (first token, full answer), LLM calls and tokens per question, fallback rate per provider

**Experiments:**
- Ablation on the frozen test set: v1.0 -> dense on new chunks -> + headers -> + BM25 hybrid -> + rerank -> + multi-query -> + parent expansion -> + verification -> + web library fallback
- Rewrite-to-English with bge-small vs multilingual-e5-small without rewrite, on Roman Urdu questions
- Human review: 50 blind, shuffled answers (v1 and v2) rated 1-5 by a tax practitioner or teacher; Cohen's kappa against the LLM judge

**Classifier:** 1,500-2,000 labeled questions (LLM-assisted + manual review). Tested on held-out human-written questions only; synthetic test score reported separately. Compare zero-shot mDeBERTa NLI vs TF-IDF + LogReg vs fine-tuned (SetFit on `paraphrase-multilingual-MiniLM-L12-v2`, or xlm-roberta-base). The served model is int8-quantized ONNX under 300 MB; xlm-roberta-base only wins if it beats the small model by a clear margin. Report accuracy, macro-F1, per-language F1, confusion matrix, latency.

**Tax engine:** pytest cases just below, at and just above every slab boundary for each tax year, cross-checked with published examples.

**Product:** user survey in Phase 0 (target 50+ responses), pilot in Phase 8 with 15-30 users, 5 scripted tasks, SUS questionnaire, task success, feedback themes.

## 13. Roadmap

Phases run in order. A phase is finished only when its "Done when" check passes. Every phase ends with its report section and ADRs written.

### Phase 0: Setup

1. Make sure this folder is a clone of `github.com/kasaam-ali/DaleelAI` (not a copy). Keep `data/` and `.env` local.
2. Add a `.gitignore` (saved as UTF-8) covering `.env`, `myenv/`, `venv/`, `chroma_db/`, `data/`, `qdrant_storage/`, model caches, `node_modules/`.
3. Local toolchain: Python 3.12 for the backend (same as the Docker image, managed with `uv`), Node 24 LTS for the frontend (current Vite needs Node 20.19+). On the dev laptop the backend runs inside Docker, because Windows Smart App Control blocks newly released native Python wheels.
4. Scan git history for secrets: `git log -p --all | Select-String "gsk_"`. Rotate the Groq key if anything shows up.
5. Tag the baseline: `git tag v1.0`, `git push origin v1.0`.
6. Create the monorepo skeleton (`backend/`, `frontend/`, `scrapers/`, `contracts/`, `docs/`) as in SPECS section 11.
7. Write `docker-compose.yml` with backend, frontend, postgres and qdrant.
8. Build the LLM gateway with 2 providers (Groq, Gemini) and fallback.
9. Add a `/health` endpoint and deploy it to Railway; measure RAM and estimate cost.
10. Set up CI (ruff, pytest, frontend build).
11. Launch the user survey (Google Form, English + Roman Urdu).

**Done when:** `docker compose up` works; removing the Groq key makes a call fall back to Gemini; CI is green.

### Phase 1: Data and retrieval

1. Build `catalog.csv` and `download.py`.
2. Clean the corpus: latest consolidated Acts and Rules only; add Finance Act 2025, Finance Act 2026, Companies Act 2017, SECP guides.
3. New extraction (pymupdf4llm + v1 OCR path), section-aware chunking, contextual headers, dedupe.
4. Index into Qdrant (dense + BM25), add reranker. Compare `ms-marco-MiniLM-L-12-v2` with `bge-reranker-base` on dev Recall@5, latency and RAM; keep the small one unless the big one clearly wins and still fits the RAM budget.
5. Web library, first version: write the site allowlist, run a one-off crawl of the most important pages (FBR help and FAQ pages, IRIS guides, SECP registration pages, provincial authority home and registration pages), index them into `web_pages`.
6. Write the official action links list (topic to portal/page).
7. Build eval set v1 from survey questions, FAQs and reviewed synthetic questions, including questions only the web library can answer; freeze the test split.
8. Run v1.0 on the eval set to get baseline numbers.

**Done when:** a Recall@5 / MRR table exists for v1.0 vs dense vs hybrid vs hybrid + rerank.

### Phase 2: Agentic RAG and API

1. Router with structured output and keyword fallback.
2. LangGraph RAG graph: rewrite, retrieve, rerank, expand, sufficiency, web fallback, generate, verify, action links.
3. SSE chat endpoint and contract export with CI drift check.
4. Call budget, LLM cache and answer cache.

**Done when:** dev-set faithfulness, correctness and abstention are reported, the web-only dev questions get a linked web answer instead of an abstain, and no question uses more than 5 LLM calls.

### Phase 3: Chat UI and deploy (M1)

1. Landing page and Chat page: streaming, sources, library label (verified or official website), confidence and Verified badges, action links, feedback buttons.
2. Browser-side PII redaction before the question is sent.
3. Onboarding profile.
4. Deploy backend to Railway and frontend to Vercel.

**Done when (M1):** the public URL answers English and Roman Urdu questions end to end.

### Phase 4: Tax tools

1. Tax rules JSON for TY2026 and TY2027, each value verified against the law with its source, including the section 4AB surcharge and any separate late-filer withholding rates.
2. Deterministic tax engine for salary, freelancer, property and filer vs non-filer.
3. Calculator and Filer vs Non-filer pages, plus chat cards.
4. Write the classifier labeling guidelines, so labeling can run in the background during Phases 4 and 5.

**Done when:** the slab-boundary test suite is green for both tax years.

### Phase 5: Notice explainer and checklists

1. PII redaction module with tests.
2. Notice pipeline: validate, extract, redact, extract fields, retrieve law, explain.
3. Five checklist templates, checklist agent with profile questions, checklist UI with saved progress.

**Done when:** 15-20 sample notices are processed correctly, and a test proves no CNIC/NTN reaches outbound LLM payloads.

### Phase 6: Expert finder

1. Label 1,500-2,000 questions; collect human-written test questions.
2. Train and compare classifiers; export the best one to ONNX.
3. Curated expert directory, Find an Expert page, city filter.
4. Use the classifier for the domain boost in retrieval.

**Done when:** macro-F1 and a confusion matrix are reported on the human-written test set.

### Phase 7: Updates agent (M2)

1. Playwright scraper for FBR notifications, SROs and circulars.
2. Internal ingest endpoint: summarize, tag domain, index, bump corpus version.
3. Updates feed page, manual trigger and replay mode.
4. Turn the one-off web crawl into the scheduled official web crawler with change detection, removed-page handling and the zero-pages alarm.

**Done when (M2):** all 7 features are at MVP.

### Phase 8: Polish and pilot

1. Polish-tier items from section 6.
2. Turn on the scheduled scrape and crawl jobs.
3. Pilot with 15-30 users: 5 scripted tasks, SUS questionnaire, feedback.
4. Fix the top issues found in the pilot.

**Done when:** SUS and task success are measured and the top issues are fixed.

### Phase 9: Final evaluation and demo

1. Final eval on the frozen test set, including the ablation and human review.
2. Evaluation page in the app and figures for the report.
3. Demo script, cached demo answers and a recorded backup video.

**Done when:** the final numbers are in the report.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Free-tier rate and token limits | Role-based fallbacks, call budget, caching, daily budget guard, eval runs split into batches across providers |
| Inconsistent answers across providers | Structured outputs validated with Pydantic; eval records which model answered |
| Railway cost or memory | ONNX serving, small models, measured RAM; Hugging Face Spaces and local compose as plan B |
| Tax law changes mid-project | Versioned rules with sources, updates agent, corpus version |
| Wrong-jurisdiction answers | Router jurisdiction field, provincial eval cases |
| Scraper or crawler breaks (layout change, site down, blocking) | Zero-item alarm, saved HTML fixtures, previous pages stay searchable, manual curation, replay mode |
| Web pages are outdated or vague | Never marked Verified, fetch date shown, user told to confirm on the page; verified library always searched first |
| Crawler load on government sites | Allowlist only, robots.txt, rate limit, change detection so unchanged pages are not re-processed |
| PII leak | Redaction before external calls, no raw storage, tests on outbound payloads |
| Scope creep | Scope tiers, M1/M2 milestones, stretch items only after M2 |
| Viva questions about AI-written code | Understand-before-merge rule, ADRs, progress log |
| Demo-day failure | Cached demo answers, local compose stack, recorded backup video |

## 15. Working rules

- Work on feature branches off `main`; `main` always deploys.
- **Understand-before-merge:** every PR description has 3-5 lines in your own words on what changed and why.
- ADRs in `docs/adr/` for: Qdrant vs Chroma, rewrite-to-English vs multilingual embeddings, LiteLLM gateway, deterministic tax engine, classifier choice, ONNX serving, PII masking, no accounts, own web library vs paid search API.
- Progress log in `docs/report/log.md`: built, broke, learned.
- Report chapters drafted at the end of each phase, figures saved in `docs/report/figures/`.
