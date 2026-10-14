# Qdrant instead of Chroma

## Status

Accepted, 2026-10-14.

## Context

The library needs one collection for ordinance chunks and another for official web pages. Each chunk has a dense vector and a BM25 sparse vector, and a query has to filter by tax year.

## Decision

Qdrant stores both collections. Hybrid search uses the server's reciprocal rank fusion. Chroma was not used, because the hybrid filter and the two named vectors are already a single query here.

## Consequences

`documents` is the ordinance index and is not rebuilt for an ablation. `web_pages` can gain official pages without touching `documents`.
