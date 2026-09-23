"""
SIF Sentinel -- Phase 5: DistilBERT Inference Service
======================================================

Provides a clean, reusable prediction API for the fine-tuned DistilBERT model.
Mirrors the BaselinePredictor API from predict_baseline.py so the FastAPI
route can swap models with a single config change.

API:
    from models.predict_distilbert import DistilBERTPredictor, get_predictor

    predictor = get_predictor()   # singleton, auto-loads best checkpoint
    result = predictor.predict("Worker entered confined space without gas test.")
    print(result["sif_prediction"])   # 0 or 1
    print(result["sif_probability"])  # float [0.0, 1.0]
    print(result["confidence_label"]) # VERY_LOW / LOW / MEDIUM / HIGH

CLI:
    python models/predict_distilbert.py "Worker found at height without harness."
    python models/predict_distilbert.py "Toolbox meeting held. No incidents." --json
    python models/predict_distilbert.py --file report.txt --threshold 0.45
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

import torch

_HERE       = Path(__file__).resolve().parent
_ROOT       = _HERE.parent
_BEST_CKPT  = _ROOT / "models" / "distilbert" / "best_checkpoint"

sys.path.insert(0, str(_HERE))
from distilbert_data import MAX_LENGTH, DEFAULT_THRESHOLD


# ---------------------------------------------------------------------------
# Confidence band
# ---------------------------------------------------------------------------

def _confidence_label(prob: float) -> str:
    if prob >= 0.80: return "HIGH"
    if prob >= 0.50: return "MEDIUM"
    if prob >= 0.30: return "LOW"
    return "VERY_LOW"


# ---------------------------------------------------------------------------
# Predictor class
# ---------------------------------------------------------------------------

class DistilBERTPredictor:
    """
    Wraps the fine-tuned DistilBERT pipeline for inference.

    Thread-safety: the model.eval() + torch.no_grad() context makes inference
    stateless. A single instance can handle concurrent requests.

    Parameters
    ----------
    checkpoint_dir : Path, optional
        Directory containing model weights + tokenizer saved by
        model.save_pretrained() / tokenizer.save_pretrained().
        Defaults to models/distilbert/best_checkpoint/.
    threshold : float
        Classification threshold for P(SIF=1). Default 0.50.
        Lower = more sensitive (fewer missed SIFs, more false alarms).
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        ckpt = Path(checkpoint_dir) if checkpoint_dir else _BEST_CKPT
        if not ckpt.exists():
            raise FileNotFoundError(
                f"DistilBERT checkpoint not found at {ckpt}. "
                "Run 'python models/train_distilbert.py' first."
            )

        self._device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._threshold = threshold
        self._ckpt_dir  = ckpt

        self._tokenizer = AutoTokenizer.from_pretrained(str(ckpt))
        self._model     = AutoModelForSequenceClassification.from_pretrained(str(ckpt))
        self._model.to(self._device)
        self._model.eval()

    # ── Single prediction ──────────────────────────────────────────────────

    def predict(self, text: str, threshold: Optional[float] = None) -> dict:
        """
        Predict SIF precursor for a single report text.

        Parameters
        ----------
        text : str  Non-empty safety report string.
        threshold : float, optional  Override instance threshold for this call.

        Returns
        -------
        dict with keys matching BaselinePredictor.predict() for API compatibility:
            text, sif_prediction, sif_probability, non_sif_probability,
            confidence_label, model, threshold_used
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Input text must be a non-empty string.")

        thr = threshold if threshold is not None else self._threshold
        sif_prob, non_sif_prob = self._infer_single(text)
        pred = 1 if sif_prob >= thr else 0

        return {
            "text":              text[:200] + ("..." if len(text) > 200 else ""),
            "sif_prediction":    pred,
            "sif_probability":   round(sif_prob, 4),
            "non_sif_probability": round(non_sif_prob, 4),
            "confidence_label":  _confidence_label(sif_prob),
            "model":             "distilbert_finetuned",
            "threshold_used":    thr,
        }

    # ── Batch prediction ───────────────────────────────────────────────────

    def predict_batch(
        self,
        texts: list[str],
        threshold: Optional[float] = None,
    ) -> list[dict]:
        """Predict SIF precursor for a list of texts (vectorised)."""
        if not texts:
            return []

        thr = threshold if threshold is not None else self._threshold
        probs = self._infer_batch(texts)  # list of (sif_prob, non_sif_prob) tuples

        results = []
        for text, (sif_prob, non_sif_prob) in zip(texts, probs):
            pred = 1 if sif_prob >= thr else 0
            results.append({
                "text":              text[:200] + ("..." if len(text) > 200 else ""),
                "sif_prediction":    pred,
                "sif_probability":   round(sif_prob, 4),
                "non_sif_probability": round(non_sif_prob, 4),
                "confidence_label":  _confidence_label(sif_prob),
                "model":             "distilbert_finetuned",
                "threshold_used":    thr,
            })
        return results

    # ── Model metadata ─────────────────────────────────────────────────────

    def model_info(self) -> dict:
        return {
            "model":          "distilbert_finetuned",
            "base_model":     "distilbert-base-uncased",
            "checkpoint_dir": str(self._ckpt_dir),
            "threshold":      self._threshold,
            "device":         str(self._device),
            "n_parameters":   sum(p.numel() for p in self._model.parameters()),
            "max_length":     MAX_LENGTH,
        }

    # ── Internal inference ─────────────────────────────────────────────────

    @torch.no_grad()
    def _infer_single(self, text: str) -> tuple[float, float]:
        enc = self._tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        input_ids      = enc["input_ids"].to(self._device)
        attention_mask = enc["attention_mask"].to(self._device)

        logits = self._model(input_ids=input_ids, attention_mask=attention_mask).logits
        probs  = torch.softmax(logits, dim=-1)[0].cpu().tolist()
        return float(probs[1]), float(probs[0])

    @torch.no_grad()
    def _infer_batch(self, texts: list[str]) -> list[tuple[float, float]]:
        enc = self._tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        input_ids      = enc["input_ids"].to(self._device)
        attention_mask = enc["attention_mask"].to(self._device)

        logits    = self._model(input_ids=input_ids, attention_mask=attention_mask).logits
        probs_all = torch.softmax(logits, dim=-1).cpu().tolist()
        return [(row[1], row[0]) for row in probs_all]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_predictor: Optional[DistilBERTPredictor] = None


def get_predictor(
    checkpoint_dir: Optional[Path] = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> DistilBERTPredictor:
    """Return the module-level singleton (lazy-loaded)."""
    global _predictor
    if _predictor is None:
        _predictor = DistilBERTPredictor(checkpoint_dir=checkpoint_dir, threshold=threshold)
    return _predictor


def predict_text(text: str, threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Convenience function for FastAPI route handlers."""
    return get_predictor(threshold=threshold).predict(text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run DistilBERT SIF precursor inference."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("text", nargs="?", help="Report text string.")
    group.add_argument("--file", type=Path, help="Path to plain-text report file.")
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--threshold",  type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--json", action="store_true", help="Output as JSON.")
    args = parser.parse_args()

    text = args.file.read_text(encoding="utf-8").strip() if args.file else args.text

    predictor = DistilBERTPredictor(
        checkpoint_dir=args.checkpoint,
        threshold=args.threshold,
    )
    result = predictor.predict(text)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        label = "SIF PRECURSOR" if result["sif_prediction"] == 1 else "Non-SIF"
        print(f"\n  Text     : {result['text']}")
        print(f"  Label    : {label}")
        print(f"  P(SIF=1) : {result['sif_probability']:.4f}  [{result['confidence_label']}]")
        print(f"  P(SIF=0) : {result['non_sif_probability']:.4f}")
        print(f"  Threshold: {result['threshold_used']}")
        print(f"  Model    : {result['model']}\n")


if __name__ == "__main__":
    main()
