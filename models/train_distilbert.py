"""
SIF Sentinel -- Phase 5: DistilBERT Training Script
====================================================

Trains DistilBERT for binary SIF precursor classification.

Key design decisions for a tiny dataset (N=50 total):
- All DistilBERT layers are fine-tuned, not frozen, because the safety domain
  vocabulary ("LOTO", "hot work permit", "exclusion zone") is underrepresented
  in generic pre-training. We rely on a small LR and early stopping to prevent
  overfitting.
- Class-weighted CrossEntropyLoss to prevent the model from collapsing to the
  majority class.
- F2 is the primary metric for early stopping (prioritises recall over precision
  because false negatives -- missed SIF events -- are safety-critical).
- Configurable classification threshold (default 0.50): can be tuned on val set.
- Saves best checkpoint (highest val F2) and final checkpoint separately.

Outputs (models/distilbert/):
    best_checkpoint/           -- best val-F2 model weights + tokenizer
    final_checkpoint/          -- weights after last epoch
    train_metrics.json
    val_metrics.json
    test_metrics.json
    distilbert_report.json     -- full metadata + metrics
    training_log.json          -- per-epoch loss and metrics

Usage:
    python models/train_distilbert.py
    python models/train_distilbert.py --epochs 15 --lr 3e-5 --threshold 0.45
    python models/train_distilbert.py --freeze-base  # only train classifier head
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader

# Resolve paths
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_DATASET_DIR = _ROOT / "dataset" / "processed"
_OUTPUT_DIR  = _ROOT / "models" / "distilbert"

sys.path.insert(0, str(_HERE))
from distilbert_data import (
    MAX_LENGTH,
    MODEL_NAME,
    SIFDataset,
    compute_class_weights,
    load_split,
)


# ---------------------------------------------------------------------------
# Metric computation (mirrors baseline for fair comparison)
# ---------------------------------------------------------------------------

def compute_metrics(
    y_true: list[int],
    y_pred: list[int],
    y_prob: list[float],
    split_name: str,
) -> dict:
    """Compute full metric set. Matches baseline API exactly for comparison."""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]

    try:
        _auc = float(roc_auc_score(y_true, y_prob))
        auc = None if (_auc != _auc) else _auc
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
        "threshold_used": None,   # filled in by caller
        "metrics": {
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1_score":  round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "f2_score":  round(float(fbeta_score(y_true, y_pred, beta=2, zero_division=0)), 4),
            "roc_auc":   round(auc, 4) if auc is not None else None,
        },
        "confusion_matrix": {
            "raw": cm, "labels": ["Non-SIF (0)", "SIF Precursor (1)"],
            "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        },
        "classification_report": report,
    }


def _apply_threshold(probs: list[float], threshold: float) -> list[int]:
    return [1 if p >= threshold else 0 for p in probs]


def _print_metrics(metrics: dict, threshold: float):
    m, cm = metrics["metrics"], metrics["confusion_matrix"]
    split = metrics["split"].upper()
    print(f"\n  [{split}]  N={metrics['n_samples']}  "
          f"(SIF=1:{metrics['n_positive']}, SIF=0:{metrics['n_negative']})  threshold={threshold:.2f}")
    print(f"    Precision  : {m['precision']:.4f}")
    print(f"    Recall     : {m['recall']:.4f}")
    print(f"    F1         : {m['f1_score']:.4f}")
    print(f"    F2(beta=2) : {m['f2_score']:.4f}  <- PRIMARY METRIC")
    if m["roc_auc"] is not None:
        print(f"    ROC-AUC    : {m['roc_auc']:.4f}")
    print(f"    Confusion Matrix:")
    print(f"              Pred 0   Pred 1")
    print(f"    Actual 0   {cm['tn']:>5}    {cm['fp']:>5}   (TN={cm['tn']}, FP={cm['fp']})")
    print(f"    Actual 1   {cm['fn']:>5}    {cm['tp']:>5}   (FN={cm['fn']}, TP={cm['tp']})")


# ---------------------------------------------------------------------------
# Training epoch
# ---------------------------------------------------------------------------

def train_epoch(
    model,
    loader: DataLoader,
    optimizer,
    device: torch.device,
    class_weights: torch.Tensor,
) -> float:
    model.train()
    total_loss = 0.0
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights.to(device))

    for batch in loader:
        input_ids      = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels         = batch["labels"].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits  = outputs.logits
        loss    = criterion(logits, labels)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(loader)


# ---------------------------------------------------------------------------
# Evaluation epoch
# ---------------------------------------------------------------------------

@torch.no_grad()
def eval_epoch(
    model,
    loader: DataLoader,
    device: torch.device,
    threshold: float = 0.50,
) -> tuple[float, list[float], list[int]]:
    """
    Returns (avg_loss, sif_probabilities, true_labels).
    Loss uses unweighted CE (so it is comparable across runs).
    """
    model.eval()
    criterion = torch.nn.CrossEntropyLoss()
    total_loss = 0.0
    all_probs: list[float] = []
    all_labels: list[int] = []

    for batch in loader:
        input_ids      = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels         = batch["labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits  = outputs.logits
        loss    = criterion(logits, labels)
        total_loss += loss.item()

        probs = torch.softmax(logits, dim=-1)[:, 1].cpu().tolist()
        all_probs.extend(probs)
        all_labels.extend(labels.cpu().tolist())

    return total_loss / len(loader), all_probs, all_labels


# ---------------------------------------------------------------------------
# Main training function
# ---------------------------------------------------------------------------

def train(
    train_path: Path,
    val_path: Path,
    test_path: Path,
    output_dir: Path,
    epochs: int = 10,
    lr: float = 2e-5,
    batch_size: int = 8,
    threshold: float = 0.50,
    freeze_base: bool = False,
    seed: int = 42,
) -> dict:
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    torch.manual_seed(seed)
    np.random.seed(seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    best_dir = output_dir / "best_checkpoint"
    final_dir = output_dir / "final_checkpoint"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Device: {device}")

    print("\n" + "=" * 60)
    print("  SIF Sentinel - Phase 5: DistilBERT Training")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────
    print(f"\n  Loading data from {train_path.parent}...")
    X_train, y_train = load_split(train_path)
    X_val,   y_val   = load_split(val_path)
    X_test,  y_test  = load_split(test_path)
    print(f"  Train: {len(X_train)} (SIF=1:{sum(y_train)}, SIF=0:{len(y_train)-sum(y_train)})")
    print(f"  Val:   {len(X_val)} (SIF=1:{sum(y_val)}, SIF=0:{len(y_val)-sum(y_val)})")
    print(f"  Test:  {len(X_test)} (SIF=1:{sum(y_test)}, SIF=0:{len(y_test)-sum(y_test)})")

    # ── Class weights ──────────────────────────────────────────────────────
    class_weights = compute_class_weights(y_train)
    print(f"\n  Class weights: Non-SIF={class_weights[0]:.3f}, SIF={class_weights[1]:.3f}")

    # ── Tokenizer + datasets ───────────────────────────────────────────────
    print(f"\n  Loading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_ds = SIFDataset(X_train, y_train, tokenizer, MAX_LENGTH)
    val_ds   = SIFDataset(X_val,   y_val,   tokenizer, MAX_LENGTH)
    test_ds  = SIFDataset(X_test,  y_test,  tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False)

    # ── Model ──────────────────────────────────────────────────────────────
    print(f"  Loading model: {MODEL_NAME}")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=2
    )

    if freeze_base:
        print("  Freezing DistilBERT base layers (training classifier head only)")
        for name, param in model.named_parameters():
            if "classifier" not in name and "pre_classifier" not in name:
                param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {trainable:,} trainable / {total:,} total")
    model.to(device)

    # ── Optimizer + scheduler ──────────────────────────────────────────────
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr, weight_decay=0.01,
    )
    total_steps = len(train_loader) * epochs
    warmup_steps = max(1, total_steps // 10)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    # ── Training loop ──────────────────────────────────────────────────────
    print(f"\n  Training: {epochs} epochs, LR={lr}, batch={batch_size}, threshold={threshold}")
    print(f"  Early stopping: patience=3 on val F2")
    print(f"  Warmup steps: {warmup_steps}")
    print("\n" + "-" * 60)

    best_val_f2    = -1.0
    best_epoch     = 0
    patience_count = 0
    patience       = 3
    training_log: list[dict] = []

    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device, class_weights)
        scheduler.step()

        val_loss, val_probs, val_true = eval_epoch(model, val_loader, device, threshold)
        val_pred = _apply_threshold(val_probs, threshold)
        val_f2   = float(fbeta_score(val_true, val_pred, beta=2, zero_division=0))
        val_recall = float(recall_score(val_true, val_pred, zero_division=0))

        log_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "val_f2": round(val_f2, 4),
            "val_recall": round(val_recall, 4),
        }
        training_log.append(log_entry)

        improved = "  <-- BEST" if val_f2 > best_val_f2 else ""
        print(f"  Epoch {epoch:02d}/{epochs}  "
              f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  "
              f"val_F2={val_f2:.4f}  val_recall={val_recall:.4f}{improved}")

        if val_f2 > best_val_f2:
            best_val_f2 = val_f2
            best_epoch  = epoch
            patience_count = 0
            # Save best checkpoint
            best_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(best_dir)
            tokenizer.save_pretrained(best_dir)
        else:
            patience_count += 1
            if patience_count >= patience:
                print(f"\n  Early stopping at epoch {epoch} (no improvement for {patience} epochs)")
                break

    print(f"\n  Best checkpoint: epoch {best_epoch}, val F2 = {best_val_f2:.4f}")

    # Save final checkpoint
    final_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)

    # ── Evaluate using best checkpoint ─────────────────────────────────────
    print(f"\n  Loading best checkpoint for evaluation...")
    model = AutoModelForSequenceClassification.from_pretrained(best_dir)
    model.to(device)
    model.eval()

    print("\n" + "-" * 60)
    print("  Evaluation (best checkpoint)")
    print("-" * 60)

    _, train_probs, train_true = eval_epoch(model, train_loader, device, threshold)
    train_pred = _apply_threshold(train_probs, threshold)
    train_metrics = compute_metrics(train_true, train_pred, train_probs, "train")
    train_metrics["threshold_used"] = threshold

    _, val_probs_final, val_true_final = eval_epoch(model, val_loader, device, threshold)
    val_pred_final = _apply_threshold(val_probs_final, threshold)
    val_metrics = compute_metrics(val_true_final, val_pred_final, val_probs_final, "val")
    val_metrics["threshold_used"] = threshold

    _, test_probs, test_true = eval_epoch(model, test_loader, device, threshold)
    test_pred = _apply_threshold(test_probs, threshold)
    test_metrics = compute_metrics(test_true, test_pred, test_probs, "test")
    test_metrics["threshold_used"] = threshold

    _print_metrics(train_metrics, threshold)
    _print_metrics(val_metrics, threshold)
    _print_metrics(test_metrics, threshold)

    # ── Save metric files ──────────────────────────────────────────────────
    for metrics, fname in [
        (train_metrics, "train_metrics.json"),
        (val_metrics,   "val_metrics.json"),
        (test_metrics,  "test_metrics.json"),
    ]:
        p = output_dir / fname
        p.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Save training log
    (output_dir / "training_log.json").write_text(
        json.dumps(training_log, indent=2), encoding="utf-8"
    )

    # ── Full report ────────────────────────────────────────────────────────
    report = {
        "schema_version": "1.0",
        "phase": "5-distilbert",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "base_model": MODEL_NAME,
            "num_labels": 2,
            "max_length": MAX_LENGTH,
            "freeze_base": freeze_base,
            "trainable_params": trainable,
            "total_params": total,
        },
        "training": {
            "epochs_run": len(training_log),
            "epochs_max": epochs,
            "lr": lr,
            "batch_size": batch_size,
            "optimizer": "AdamW",
            "scheduler": "linear_warmup",
            "warmup_steps": warmup_steps,
            "weight_decay": 0.01,
            "class_weights": {"Non-SIF": round(float(class_weights[0]), 4),
                              "SIF": round(float(class_weights[1]), 4)},
            "early_stopping_patience": patience,
            "best_epoch": best_epoch,
            "best_val_f2": round(best_val_f2, 4),
            "device": str(device),
            "seed": seed,
        },
        "classification_threshold": threshold,
        "primary_metric": "f2_score",
        "data": {
            "train_path": str(train_path),
            "val_path":   str(val_path),
            "test_path":  str(test_path),
            "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        },
        "train_metrics":  train_metrics,
        "val_metrics":    val_metrics,
        "test_metrics":   test_metrics,
        "training_log":   training_log,
        "checkpoint_best":  str(best_dir),
        "checkpoint_final": str(final_dir),
    }

    report_path = output_dir / "distilbert_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # ── Final summary ──────────────────────────────────────────────────────
    tm = test_metrics["metrics"]
    print(f"\n{'=' * 60}")
    print(f"  FINAL HELD-OUT TEST METRICS (DistilBERT, threshold={threshold})")
    print(f"{'=' * 60}")
    print(f"  Precision  : {tm['precision']:.4f}")
    print(f"  Recall     : {tm['recall']:.4f}")
    print(f"  F1         : {tm['f1_score']:.4f}")
    print(f"  F2(primary): {tm['f2_score']:.4f}")
    if tm["roc_auc"] is not None:
        print(f"  ROC-AUC    : {tm['roc_auc']:.4f}")
    print(f"{'=' * 60}")
    print(f"  Best checkpoint: {best_dir}")
    print(f"  Report: {report_path}")
    print()

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune DistilBERT for SIF precursor binary classification."
    )
    parser.add_argument("--train",     type=Path, default=_DATASET_DIR / "train.csv")
    parser.add_argument("--val",       type=Path, default=_DATASET_DIR / "val.csv")
    parser.add_argument("--test",      type=Path, default=_DATASET_DIR / "test.csv")
    parser.add_argument("--output",    type=Path, default=_OUTPUT_DIR)
    parser.add_argument("--epochs",    type=int,   default=10)
    parser.add_argument("--lr",        type=float, default=2e-5)
    parser.add_argument("--batch",     type=int,   default=8)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--freeze-base", action="store_true",
                        help="Only train the classifier head (faster but less adaptive)")
    parser.add_argument("--seed",      type=int,   default=42)
    args = parser.parse_args()

    train(
        train_path=args.train.resolve(),
        val_path=args.val.resolve(),
        test_path=args.test.resolve(),
        output_dir=args.output.resolve(),
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch,
        threshold=args.threshold,
        freeze_base=args.freeze_base,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
