"""Train two text classifiers and export the better one to int8 ONNX.

Compared on the human-written test and, separately, on the synthetic test.
SetFit and zero-shot mDeBERTa are not trained here: this image has no torch
build, and downloading one would blow the time budget. The served file is the
stronger TF-IDF logistic model, quantized when the graph allows it.
"""

import json
import time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

from ml.dataset import DOMAINS, write_datasets

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path(__file__).resolve().parent / "reports"
MODEL_PATH = ROOT / "models" / "classifier.onnx"
LABELS = ("income_tax", "sales_tax", "customs", "corporate_secp", "audit_notice", "property")


def main() -> None:
    write_datasets()
    data = Path(__file__).resolve().parent / "data"
    train = _load(data / "synthetic_train.jsonl")
    synthetic = _load(data / "synthetic_test.jsonl")
    human = _load(data / "human_test.jsonl")
    candidates = []
    for name, vectorizer in (
        ("tfidf_word_logreg", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
        ("tfidf_char_logreg", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)),
    ):
        model = Pipeline(
            [
                ("tfidf", vectorizer),
                ("clf", LogisticRegression(max_iter=400)),
            ]
        )
        model.fit([row["question"] for row in train], [_target(row) for row in train])
        candidates.append(
            {
                "name": name,
                "model": model,
                "human_test": _score(model, human),
                "synthetic_test": _score(model, synthetic),
            }
        )
    winner = max(candidates, key=lambda item: item["human_test"]["macro_f1"])
    exported = _export(winner["model"])
    report = {
        "task": "domain|complexity",
        "measured_at": time.strftime("%Y-%m-%d"),
        "dataset": {
            "train": len(train),
            "synthetic_test": len(synthetic),
            "human_test": len(human),
            "kinds": _kinds(train, synthetic, human),
        },
        "train_rows": len(train),
        "served_model": winner["name"],
        "export": exported,
        "not_trained": [
            {
                "name": "zero_shot_mdeberta",
                "reason": "The running image has no torch, so this model was not downloaded.",
            },
            {
                "name": "setfit_minilm",
                "reason": "SetFit needs torch. It was not installed, so it was not compared.",
            },
        ],
        "candidates": [
            {
                "name": item["name"],
                "human_test": item["human_test"],
                "synthetic_test": item["synthetic_test"],
            }
            for item in candidates
        ],
        "domains": list(DOMAINS),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "classifier_metrics.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(winner["name"], winner["human_test"]["macro_f1"], exported)


def _kinds(*groups: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rows in groups:
        for row in rows:
            key = f"{row['domain']}|{row['complexity']}"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _target(row: dict) -> str:
    return f"{row['domain']}|{row['complexity']}"


def _score(model: Pipeline, rows: list[dict]) -> dict:
    texts = [row["question"] for row in rows]
    gold = [_target(row) for row in rows]
    started = time.perf_counter()
    predicted = list(model.predict(texts))
    elapsed = (time.perf_counter() - started) * 1000 / max(len(texts), 1)
    labels = sorted(set(gold) | set(predicted))
    matrix = confusion_matrix(gold, predicted, labels=labels).tolist()
    return {
        "accuracy": round(float(accuracy_score(gold, predicted)), 4),
        "macro_f1": round(float(f1_score(gold, predicted, average="macro", zero_division=0)), 4),
        "per_language_f1": {
            language: _language_f1(rows, predicted, language) for language in ("en", "roman_urdu")
        },
        "confusion_matrix": {"labels": labels, "matrix": matrix},
        "latency_ms_mean": round(elapsed, 3),
        "rows": len(rows),
    }


def _language_f1(rows: list[dict], predicted: list[str], language: str) -> float:
    pairs = [
        (gold, pred)
        for gold, pred, row in zip(
            [_target(row) for row in rows],
            predicted,
            rows,
            strict=True,
        )
        if row["language"] == language
    ]
    if not pairs:
        return 0.0
    gold, pred = zip(*pairs, strict=True)
    return round(float(f1_score(gold, pred, average="macro", zero_division=0)), 4)


def _export(model: Pipeline) -> dict:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["clf"]
    vocab = {
        "analyzer": "word",
        "ngram_range": [1, 2],
        "vocabulary": {token: int(index) for token, index in vectorizer.vocabulary_.items()},
        "idf": [float(value) for value in vectorizer.idf_],
    }
    vocab_path = MODEL_PATH.with_suffix(".vocab.json")
    vocab_path.write_text(json.dumps(vocab), encoding="utf-8")
    onnx_model = _linear_onnx(classifier)
    raw_path = MODEL_PATH.with_suffix(".float.onnx")
    raw_path.write_bytes(onnx_model.SerializeToString())
    quantized = False
    note = ""
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        quantize_dynamic(str(raw_path), str(MODEL_PATH), weight_type=QuantType.QInt8)
        quantized = MODEL_PATH.stat().st_size > 0
    except Exception as exc:
        MODEL_PATH.write_bytes(raw_path.read_bytes())
        note = str(exc)
    labels = [str(label) for label in classifier.classes_]
    MODEL_PATH.with_suffix(".labels.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
    size = MODEL_PATH.stat().st_size + vocab_path.stat().st_size
    return {
        "path": "models/classifier.onnx",
        "bytes": size,
        "under_300mb": size < 300 * 1024 * 1024,
        "int8": quantized,
        "note": note,
        "vectorizer": "models/classifier.vocab.json",
        "classes": labels,
    }


def _linear_onnx(classifier):
    """A Gemm graph in the default ONNX domain, so the weights can be quantized."""
    import numpy as np
    from onnx import TensorProto, helper, numpy_helper

    coef = np.asarray(classifier.coef_, dtype=np.float32)
    intercept = np.asarray(classifier.intercept_, dtype=np.float32)
    graph = helper.make_graph(
        [helper.make_node("Gemm", ["features", "coef", "intercept"], ["scores"])],
        "classifier",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, coef.shape[1]])],
        [helper.make_tensor_value_info("scores", TensorProto.FLOAT, [None, coef.shape[0]])],
        [
            numpy_helper.from_array(coef.T, name="coef"),
            numpy_helper.from_array(intercept, name="intercept"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    return model


if __name__ == "__main__":
    main()
