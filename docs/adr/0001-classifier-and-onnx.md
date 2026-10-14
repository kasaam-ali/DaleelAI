# Classifier choice and ONNX serving

## Status

Accepted, 2026-10-14.

## Context

Retrieval needs a domain so the matching chunks can get the 1.2 boost, and the expert finder needs a category. The plan compares a zero-shot NLI model, TF-IDF plus logistic regression, and a fine-tuned SetFit model. The served file has to be int8 ONNX under 300 MB.

## Decision

The running image has no torch build. Downloading mDeBERTa or SetFit would add a large model and a new runtime, so those two were not trained. Their absence is recorded in the metrics file.

Two scikit-learn models were trained on the synthetic set and scored separately on the human-written test and the synthetic test. Word n-grams and character n-grams tied at macro-F1 0.986 on the 72 human questions. The word model is served because it is the first of the two and it is faster.

The export is a quantized matrix multiply, not a text pipeline. The slim image has no `en_US.UTF-8` locale, and the ONNX text normalizer refuses to load without it. TF-IDF stays in Python. The linear weights are int8 ONNX, about 62 KB with the vocabulary file.

If the ONNX file or the vocabulary file is missing, the API uses the keyword rules.

## Consequences

Human and synthetic scores stay in separate blocks of `backend/ml/reports/classifier_metrics.json`. A later image that has torch can add SetFit without changing the API. The keyword fallback covers a fresh checkout, because the ONNX file is gitignored.
