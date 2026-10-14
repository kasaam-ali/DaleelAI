# A deterministic tax engine

## Status

Accepted, 2026-10-14.

## Context

Salary, withholding, and filer comparisons are numeric. A model that writes the rupee figure can invent a rate.

## Decision

Published slabs and rates live in versioned rule files. The calculator and the filer comparison run those rules in code. The model may explain a result. It does not compute it.

## Consequences

A slab change is a rule-file change with a test, not a prompt change. The chat card for a calculation comes from the engine.
