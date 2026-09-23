"""
SIF Sentinel -- Phase 4: Baseline ML Classifier
================================================
Trains a TF-IDF + Logistic Regression binary classifier for sif_precursor.
See docstring in each function for details.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_DATASET_DIR = _ROOT / "dataset" / "processed"
_MODELS_DIR  = _ROOT / "models" / "baseline"


def build_pipeline() -> Pipeline:
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True,
        min_df=1,
        strip_accents="unicode",
        lowercase=True,
        token_pattern=r"(?u)\b\w\w+\b",
    )
    lr = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )
    return Pipeline([("tfidf", tfidf), ("lr", lr)])


def load_split(path: Path) -> tuple[list[str], list[int]]:
    df = pd.read_csv(path, dtype={"sif_precursor": int, "report_id": str})
    missing = {"report_text", "sif_precursor"} - set(df.columns)
    if missing:
        raise ValueError(f"CSV at {path} is missing columns: {missing}")
    return df["report_text"].astype(str).tolist(), df["sif_precursor"].tolist()


def compute_metrics(y_true, y_pred, y_prob, split_name: str) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()  # always 2x2
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    try:
        _auc = float(roc_auc_score(y_true, y_prob))
        auc = None if (_auc != _auc) else _auc  # NaN check (sklearn 1.9 returns nan)
    except Exception:
        auc = None
    report = classification_report(
        y_true, y_pred,
        labels=[0, 1],
        target_names=["Non-SIF (0)", "SIF Precursor (1)"],
        output_dict=True, zero_division=0,
    )
    return {
        "split": split_name,
        "n_samples":  len(y_true),
        "n_positive": int(sum(y_true)),
        "n_negative": int(len(y_true) - sum(y_true)),
        "metrics": {
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1_score":  round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "f2_score":  round(float(fbeta_score(y_true, y_pred, beta=2, zero_division=0)), 4),
            "roc_auc":   round(auc, 4) if auc is not None else None,
        },
        "confusion_matrix": {"raw": cm, "labels": ["Non-SIF (0)", "SIF Precursor (1)"],
                             "tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "classification_report": report,
    }


def top_features(pipeline: Pipeline, n: int = 20) -> dict:
    feature_names = pipeline.named_steps["tfidf"].get_feature_names_out()
    coef = pipeline.named_steps["lr"].coef_[0]
    top_sif = np.argsort(coef)[::-1][:n]
    top_non = np.argsort(coef)[:n]
    return {
        "top_sif_precursor_features": [
            {"feature": str(feature_names[i]), "coefficient": round(float(coef[i]), 4)}
            for i in top_sif
        ],
        "top_non_sif_features": [
            {"feature": str(feature_names[i]), "coefficient": round(float(coef[i]), 4)}
            for i in top_non
        ],
    }


def _print_metrics(metrics: dict):
    m, cm = metrics["metrics"], metrics["confusion_matrix"]
    print(f"\n  [{metrics['split'].upper()}]  N={metrics['n_samples']}  "
          f"(SIF=1:{metrics['n_positive']}, SIF=0:{metrics['n_negative']})")
    print(f"    Precision  : {m['precision']:.4f}")
    print(f"    Recall     : {m['recall']:.4f}")
    print(f"    F1         : {m['f1_score']:.4f}")
    print(f"    F2(beta=2) : {m['f2_score']:.4f}  <- PRIMARY METRIC")
    if m["roc_auc"] is not None:
        print(f"    ROC-AUC    : {m['roc_auc']:.4f}")
    print(f"    Confusion Matrix (rows=actual, cols=predicted):")
    print(f"              Pred 0   Pred 1")
    print(f"    Actual 0   {cm['tn']:>5}    {cm['fp']:>5}   (TN={cm['tn']}, FP={cm['fp']})")
    print(f"    Actual 1   {cm['fn']:>5}    {cm['tp']:>5}   (FN={cm['fn']}, TP={cm['tp']})")


def train(train_path: Path, val_path: Path, test_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("  SIF Sentinel - Phase 4: Baseline Classifier Training")
    print("=" * 60)

    print("\n  Loading splits...")
    X_train, y_train = load_split(train_path)
    X_val,   y_val   = load_split(val_path)
    X_test,  y_test  = load_split(test_path)
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    print("\n  Building TF-IDF(1,2) + LogisticRegression pipeline...")
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    vocab_size = len(pipeline.named_steps["tfidf"].vocabulary_)
    print(f"  TF-IDF vocabulary: {vocab_size} features")

    print("\n" + "-" * 60)
    print("  Evaluation")
    print("-" * 60)

    train_metrics = compute_metrics(y_train, pipeline.predict(X_train).tolist(),
                                    pipeline.predict_proba(X_train)[:, 1], "train")
    val_metrics   = compute_metrics(y_val, pipeline.predict(X_val).tolist(),
                                    pipeline.predict_proba(X_val)[:, 1], "val")
    test_metrics  = compute_metrics(y_test, pipeline.predict(X_test).tolist(),
                                    pipeline.predict_proba(X_test)[:, 1], "test")

    _print_metrics(train_metrics)
    _print_metrics(val_metrics)
    _print_metrics(test_metrics)

    features = top_features(pipeline, n=20)
    print(f"\n  Top 10 SIF Precursor signal n-grams:")
    for f in features["top_sif_precursor_features"][:10]:
        print(f"    {f['feature']:<35}  coef={f['coefficient']:+.4f}")
    print(f"\n  Top 10 Non-SIF signal n-grams:")
    for f in features["top_non_sif_features"][:10]:
        print(f"    {f['feature']:<35}  coef={f['coefficient']:+.4f}")

    model_path = output_dir / "baseline_pipeline.joblib"
    joblib.dump(pipeline, model_path)
    print(f"\n  Saved: {model_path}")

    for metrics, fname in [
        (train_metrics, "train_metrics.json"),
        (val_metrics,   "val_metrics.json"),
        (test_metrics,  "test_metrics.json"),
    ]:
        p = output_dir / fname
        p.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"  Saved: {p}")

    report = {
        "schema_version": "1.0",
        "phase": "4-baseline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": {
            "vectorizer": "TfidfVectorizer", "classifier": "LogisticRegression",
            "ngram_range": [1, 2], "max_features": 5000, "sublinear_tf": True,
            "class_weight": "balanced", "C": 1.0, "solver": "lbfgs",
            "vocabulary_size": vocab_size,
        },
        "data": {
            "train_path": str(train_path), "val_path": str(val_path), "test_path": str(test_path),
            "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        },
        "primary_metric": "f2_score",
        "primary_metric_rationale": (
            "F2 (beta=2) weights recall twice as heavily as precision. "
            "In safety classification, a missed SIF precursor (false negative) "
            "is significantly more dangerous than a false alarm (false positive)."
        ),
        "baseline_rationale": (
            "TF-IDF + Logistic Regression is the Phase 4 baseline for five reasons: "
            "(1) Interpretability -- LR coefficients expose which n-grams drive each class, "
            "satisfying safety system explainability requirements. "
            "(2) Benchmarking -- sets the performance floor so transformer gains are measurable. "
            "(3) Error analysis -- false negatives reveal vocabulary gaps the transformer must cover. "
            "(4) Data validation -- near-chance accuracy signals data quality problems cheaply. "
            "(5) Production fallback -- serves predictions without GPU dependency."
        ),
        "train_metrics": train_metrics, "val_metrics": val_metrics, "test_metrics": test_metrics,
        "top_features": features,
        "model_path": str(model_path),
    }

    report_path = output_dir / "baseline_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Saved: {report_path}")

    tm = test_metrics["metrics"]
    print(f"\n{'=' * 60}")
    print(f"  FINAL HELD-OUT TEST METRICS")
    print(f"{'=' * 60}")
    print(f"  Precision  : {tm['precision']:.4f}")
    print(f"  Recall     : {tm['recall']:.4f}")
    print(f"  F1         : {tm['f1_score']:.4f}")
    print(f"  F2(primary): {tm['f2_score']:.4f}")
    if tm["roc_auc"] is not None:
        print(f"  ROC-AUC    : {tm['roc_auc']:.4f}")
    print(f"{'=' * 60}\n")
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Train SIF Sentinel TF-IDF + LR baseline classifier."
    )
    parser.add_argument("--train",  type=Path, default=_DATASET_DIR / "train.csv")
    parser.add_argument("--val",    type=Path, default=_DATASET_DIR / "val.csv")
    parser.add_argument("--test",   type=Path, default=_DATASET_DIR / "test.csv")
    parser.add_argument("--output", type=Path, default=_MODELS_DIR)
    args = parser.parse_args()
    train(args.train.resolve(), args.val.resolve(), args.test.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
