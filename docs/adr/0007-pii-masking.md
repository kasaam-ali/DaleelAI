# Mask personal numbers before a model call

## Status

Accepted, 2026-10-14.

## Context

A question or a notice can contain a CNIC, an NTN, a phone number, an email, or a bank account. Those values must not be sent to a model or written into the chat log.

## Decision

The browser masks them before send. The server masks the same patterns again before routing, retrieval, or a model call. An uploaded notice is read in memory and is not stored.

## Consequences

The model sees a placeholder such as `[CNIC]`. A user can still ask the tax question. The original number is not recoverable from the stored turn.
