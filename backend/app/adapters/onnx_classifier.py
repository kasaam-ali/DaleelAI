"""Load the exported classifier. A missing file uses the keyword rules."""

import json
import re
from pathlib import Path

import numpy as np

from app.core.classifier import LOW_CONFIDENCE, KeywordClassifier, Prediction

_TOKEN = re.compile(r"(?u)\b\w\w+\b")


class OnnxClassifier:
    """TF-IDF in Python, then the int8 linear model. The text pipeline's ONNX
    normalizer needs a locale this image does not have."""

    def __init__(self, path: Path) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        vocab_path = path.with_suffix(".vocab.json")
        payload = json.loads(vocab_path.read_text(encoding="utf-8"))
        if payload.get("analyzer", "word") != "word":
            raise ValueError("This adapter only scores word n-grams.")
        self.vocabulary: dict[str, int] = payload["vocabulary"]
        self.idf = np.asarray(payload["idf"], dtype=np.float32)
        self.labels = [
            line.strip()
            for line in path.with_suffix(".labels.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def predict(self, text: str) -> Prediction:
        features = _tfidf(text, self.vocabulary, self.idf)
        scores = np.asarray(
            self.session.run(None, {self.input_name: features})[0],
            dtype=np.float32,
        ).reshape(-1)
        index = int(np.argmax(scores))
        name = self.labels[index]
        category, _, complexity = name.partition("|")
        score = float(_softmax(scores)[index])
        return Prediction(
            category=category or None,
            complexity="complex" if complexity == "complex" else "simple",
            confidence=score,
            low_confidence=score < LOW_CONFIDENCE,
        )


def load_classifier(kind: str, path: Path):
    if kind == "onnx" and path.is_file() and path.with_suffix(".vocab.json").is_file():
        try:
            return OnnxClassifier(path)
        except Exception:
            return KeywordClassifier()
    return KeywordClassifier()


def _tfidf(text: str, vocabulary: dict[str, int], idf: np.ndarray) -> np.ndarray:
    tokens = _TOKEN.findall(text.lower())
    grams = tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:], strict=False)]
    vector = np.zeros(len(idf), dtype=np.float32)
    for gram in grams:
        index = vocabulary.get(gram)
        if index is not None:
            vector[index] += idf[index]
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector.reshape(1, -1)


def _softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - float(np.max(scores))
    exp = np.exp(shifted)
    return exp / float(np.sum(exp))
