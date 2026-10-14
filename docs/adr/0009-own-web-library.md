# Our own web library instead of a paid search API

## Status

Accepted, 2026-10-14.

## Context

When the ordinance library is not enough, the assistant may cite an official page. A paid search API would return the open web, including blogs.

## Decision

Official pages are crawled from an allowlist and stored in the `web_pages` collection. A page is removed only when a later crawl names it. A crawl that fetches nothing leaves the previous pages in place. Replay fixtures cover a demo when the live site is empty or blocked.

## Consequences

Coverage is only the allowlist. A new authority needs a prefix in the config before its URL can be stored. There is no per-query search bill.
