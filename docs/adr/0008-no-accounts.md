# No accounts

## Status

Accepted, 2026-10-14.

## Context

The product answers tax questions and stores a short chat and checklist progress. An account would mean passwords, email, and a longer retention story.

## Decision

There is no signup and no login. A session id in the browser ties the chat and the checklist to that device. Feedback is stored against that session.

## Consequences

Progress does not follow the user to another device. There is no password to leak. Clearing site data starts a new session.
