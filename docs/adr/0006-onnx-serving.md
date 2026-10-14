# ONNX serving for the domain classifier

## Status

Accepted, 2026-10-14.

## Context

The domain classifier has to run in the slim API image. The training comparison is in ADR 0001.

## Decision

The served file is an int8 matrix multiply, about 62 KB with the vocabulary. TF-IDF stays in Python because the slim image has no `en_US.UTF-8` locale and the ONNX text normalizer will not load. If the ONNX file or the vocabulary is missing, the keyword rules answer instead.

## Consequences

The ONNX file stays gitignored. A checkout without it still classifies, with the weaker keyword model.
