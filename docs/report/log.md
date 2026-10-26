# DaleelAI log

## 17 Oct 2026

Legal answers now stay on the section the question actually asked about. "bechta" (selling clothes) no longer matches the property verb "bech", so an EasyPaisa question does not pull plot tax. A section phrase has to end on a boundary, so Section 236C and Section 236K are not treated as utility Section 236. An Upwork freelancer answer names Section 154A and Section 114. An EasyPaisa or NTN answer names Section 181 and does not cite plot sections. A plot answer still names seller 236C, buyer 236K, the Rs 15 lakh gain under 37(1A), that a 2-year hold is not automatic zero, and late-filer withholding under 100BA and the Tenth Schedule, without salary 149, rent 15 or 155, or electricity 235. The FBR notice path is unchanged (122 and 114).

The primary answer path searches the local `documents` collection, then local `web_pages` only when documents has no hit. A known curated note is streamed before that search, so the first token does not wait on the model or on Qdrant. If there is no curated note and the local indexes have no hit, the question falls through to the heavier retrieval path. This pass does not call pakistangov.online or any other external site.

Checks: `ruff check .` passed with no findings. `pytest -q` passed, 257 tests. Frontend `vitest run` passed, 45 tests in 7 files.

Qdrant snapshots, point counts unchanged (documents 18,600 before and after; web_pages 30 before and after):

- `C:\Users\ahmed\Desktop\DaleelAI\backups\qdrant\documents-8492160767170528-2026-10-16-19-14-01.snapshot` (101,594,112 bytes)
- `C:\Users\ahmed\Desktop\DaleelAI\backups\qdrant\web_pages-8492160767170528-2026-10-16-19-14-33.snapshot` (963,584 bytes)
