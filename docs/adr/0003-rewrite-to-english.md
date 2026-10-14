# Rewrite to English instead of a multilingual embedding

## Status

Accepted, 2026-10-14.

## Context

Questions arrive in English and Roman Urdu. The indexed ordinance text is English. A multilingual embedding would need a second model and a second index.

## Decision

The router rewrites a Roman Urdu question into an English search query. The dense model stays `BAAI/bge-small-en-v1.5`. The answer can still be written in the user's language.

## Consequences

Retrieval quality depends on the rewrite. The documents collection does not have to be re-embedded when the rewrite prompt changes.
