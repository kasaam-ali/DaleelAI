# LiteLLM as the model gateway

## Status

Accepted, 2026-10-14.

## Context

Drafts, rewrites, and verification need a chat model. One provider being down should not end the request if another key is still live.

## Decision

Every model call goes through LiteLLM. The order is Groq, then Gemini 3.8 and 2.5 on the first Gemini key, then the same Gemini models on the second key, then OpenRouter. Each call has a timeout. A failed judge after a draft has already streamed keeps that draft and marks it unverified.

## Consequences

The app does not bind to one vendor. A saved demo answer can still be served when every provider is down, without calling this gateway.
