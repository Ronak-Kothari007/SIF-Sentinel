"""
SIF Sentinel -- Phase 4: Baseline Classifier Inference
=======================================================

Provides a clean prediction API for the trained TF-IDF + LR baseline.
The API is designed to mirror what the transformer classifier will expose
in Phase 5, so the backend can swap classifiers with a single config change.

Usage (Python API):
    from models.predict_baseline import BaselinePredictor

    predictor = BaselinePredictor()           # auto-loads saved model
    result = predictor.predict("Worker entered confined space without gas test.")
    print(result["sif_prediction"])           # 1
    print(result["sif_probability"])          # 0.92
    print(result["confidence_label"])         # "HIGH"

Usage (CLI):
    python models/predict_baseline.py "Worker entered confined space without gas test."
    python models/predict_baseline.py --file report.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import joblib
import numpy as np

_HERE        = Path(__file__).resolve().parent
_ROOT        = _HERE.parent
_MODEL_PATH  = _ROOT / "models" / "baseline" / "baseline_pipeline.joblib"


# ---------------------------------------------------------------------------
# Confidence band mapping
# ---------------------------------------------------------------------------

def _confidence_label(prob: float) -> str:
    """Map SIF probability to a human-readable confidence label."""
    if prob >= 0.80:
        return "HIGH"
    elif prob >= 0.50:
        return "MEDIUM"
    elif prob >= 0.30:
        return "LOW"
    else:
        return "VERY_LOW"


# ---------------------------------------------------------------------------
# Predictor class
# ---------------------------------------------------------------------------

class BaselinePredictor:
    """
    Wraps the trained TF-IDF + LR pipeline for safe, reusable inference.

    Thread-safety: the sklearn Pipeline.predict() method is stateless at
    inference time, so a single instance can safely handle concurrent calls.

    The predictor exposes:
        predict(text)          -- single text, returns full dict
        predict_batch(texts)   -- list of texts, returns list of dicts
        model_info()           -- returns pipeline metadata
    """

    def __init__(self, model_path: Optional[Path] = None):
        """
        Load the trained pipeline from disk.

        Parameters
        ----------
        model_path : Path, optional
            Override the default model location (models/baseline/baseline_pipeline.joblib).
        """
        path = Path(model_path) if model_path else _MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Baseline model not found at {path}. "
                "Run 'python models/train_baseline.py' first."
            )
        self._pipeline = joblib.load(path)
        
        # --- Monkey Patch for scikit-learn >= 1.5 compatibility ---
        try:
            lr = self._pipeline.named_steps["lr"]
            if not hasattr(lr, "multi_class"):
                # Older models expect this attribute which was removed in 1.5
                lr.multi_class = "auto"
        except Exception:
            pass
            
        self._model_path = path

    def predict(self, text: str) -> dict:
        """
        Predict SIF precursor for a single report text.

        Parameters
        ----------
        text : str
            Raw safety report text.

        Returns
        -------
        dict with keys:
            text              : the input text (truncated to 200 chars for display)
            sif_prediction    : 0 or 1 (hard label)
            sif_probability   : float in [0.0, 1.0], probability of sif_precursor=1
            non_sif_probability: float, probability of sif_precursor=0
            confidence_label  : "VERY_LOW" | "LOW" | "MEDIUM" | "HIGH"
            model             : "tfidf_lr_baseline"
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Input text must be a non-empty string.")

        probs = self._pipeline.predict_proba([text])[0]   # shape (2,)
        pred  = int(self._pipeline.predict([text])[0])
        sif_prob     = float(probs[1])
        non_sif_prob = float(probs[0])

        return {
            "text":              text[:200] + ("..." if len(text) > 200 else ""),
            "sif_prediction":    pred,
            "sif_probability":   round(sif_prob, 4),
            "non_sif_probability": round(non_sif_prob, 4),
            "confidence_label":  _confidence_label(sif_prob),
            "model":             "tfidf_lr_baseline",
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        """
        Predict SIF precursor for a list of texts.

        Parameters
        ----------
        texts : list[str]
            List of raw safety report texts.

        Returns
        -------
        list[dict]
            Each element has the same structure as predict().
        """
        if not texts:
            return []

        probs_all = self._pipeline.predict_proba(texts)   # shape (N, 2)
        preds_all = self._pipeline.predict(texts)          # shape (N,)

        results = []
        for text, pred, probs in zip(texts, preds_all, probs_all):
            sif_prob     = float(probs[1])
            non_sif_prob = float(probs[0])
            results.append({
                "text":              text[:200] + ("..." if len(text) > 200 else ""),
                "sif_prediction":    int(pred),
                "sif_probability":   round(sif_prob, 4),
                "non_sif_probability": round(non_sif_prob, 4),
                "confidence_label":  _confidence_label(sif_prob),
                "model":             "tfidf_lr_baseline",
            })
        return results

    def model_info(self) -> dict:
        """Return metadata about the loaded model."""
        tfidf = self._pipeline.named_steps["tfidf"]
        lr    = self._pipeline.named_steps["lr"]
        return {
            "model": "tfidf_lr_baseline",
            "model_path": str(self._model_path),
            "vectorizer": "TfidfVectorizer",
            "classifier": "LogisticRegression",
            "vocabulary_size": len(tfidf.vocabulary_),
            "ngram_range": list(tfidf.ngram_range),
            "sublinear_tf": tfidf.sublinear_tf,
            "lr_C": lr.C,
            "lr_class_weight": lr.class_weight,
            "n_classes": int(lr.classes_.shape[0]),
            "classes": lr.classes_.tolist(),
        }


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-loaded)
# ---------------------------------------------------------------------------

_predictor: Optional[BaselinePredictor] = None


def get_predictor(model_path: Optional[Path] = None) -> BaselinePredictor:
    """
    Return the module-level singleton BaselinePredictor.

    The first call loads the model from disk. Subsequent calls return the
    cached instance (safe for use in FastAPI lifespan).
    """
    global _predictor
    if _predictor is None:
        _predictor = BaselinePredictor(model_path=model_path)
    return _predictor


def predict_text(text: str) -> dict:
    """
    Convenience function: load predictor (if not already loaded) and predict.
    Intended for use in the FastAPI route handler.
    """
    return get_predictor().predict(text)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run baseline SIF precursor inference on text."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "text", nargs="?",
        help="Report text string to classify.",
    )
    group.add_argument(
        "--file", type=Path,
        help="Path to a plain-text file containing the report.",
    )
    parser.add_argument(
        "--model", type=Path, default=None,
        help="Path to the .joblib model file (default: models/baseline/baseline_pipeline.joblib)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output result as JSON.",
    )
    args = parser.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8").strip()
    else:
        text = args.text

    predictor = BaselinePredictor(model_path=args.model)
    result = predictor.predict(text)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        label = "SIF PRECURSOR" if result["sif_prediction"] == 1 else "Non-SIF"
        print(f"\n  Text     : {result['text']}")
        print(f"  Label    : {label}")
        print(f"  P(SIF=1) : {result['sif_probability']:.4f}  [{result['confidence_label']}]")
        print(f"  P(SIF=0) : {result['non_sif_probability']:.4f}")
        print(f"  Model    : {result['model']}\n")


if __name__ == "__main__":
    main()
