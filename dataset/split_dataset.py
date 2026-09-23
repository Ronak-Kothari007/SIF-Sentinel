"""
SIF Sentinel — Train / Validation / Test Split Script
======================================================

Produces a stratified train/val/test split of a validated SIF Sentinel CSV.

Strategy:
  - Stratify on `sif_precursor` to preserve class balance across all splits.
  - Deduplication before splitting: exact-duplicate report_texts are removed
    (keeping first occurrence) so they cannot appear across both train and test.
  - Split ratios (default): train=70%, val=15%, test=15%
  - Random seed is fixed (default 42) for reproducibility.

Outputs (written to dataset/processed/):
  - train.csv
  - val.csv
  - test.csv
  - split_manifest.json   — records sizes, ratios, seed, source counts, and class dist.

Usage:
    python split_dataset.py path/to/file.csv
    python split_dataset.py path/to/file.csv --train 0.70 --val 0.15 --test 0.15
    python split_dataset.py path/to/file.csv --seed 99 --output-dir path/to/out/
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Safe encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd
from sklearn.model_selection import train_test_split

_DATASET_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_DATASET_DIR))
from schema import COLUMNS, VALID_SIF_PRECURSOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _class_dist(df: pd.DataFrame) -> dict:
    """Return class distribution as a dict {label: count}."""
    counts = df["sif_precursor"].value_counts().sort_index().to_dict()
    return {str(k): int(v) for k, v in counts.items()}


def _source_dist(df: pd.DataFrame) -> dict:
    """Return source distribution as a dict {source: count}."""
    counts = df["source"].value_counts().to_dict()
    return {str(k): int(v) for k, v in counts.items()}


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}%" if total > 0 else "0.0%"


# ---------------------------------------------------------------------------
# Main split logic
# ---------------------------------------------------------------------------

def split_dataset(
    input_path: Path,
    output_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict:
    """
    Load, deduplicate, and split a validated dataset CSV.

    Returns a manifest dict describing the split.
    """
    # ── Sanity check ratios ─────────────────────────────────────────────────
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"train + val + test ratios must sum to 1.0, got {total:.4f}"
        )
    if any(r <= 0 for r in [train_ratio, val_ratio, test_ratio]):
        raise ValueError("All split ratios must be > 0")

    # ── Load ────────────────────────────────────────────────────────────────
    print(f"\nLoading: {input_path}")
    df = pd.read_csv(input_path, dtype={"sif_precursor": "Int64", "report_id": str})
    n_raw = len(df)
    print(f"  Loaded {n_raw} rows")

    # ── Validate required columns ───────────────────────────────────────────
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    # ── Validate sif_precursor values ───────────────────────────────────────
    invalid_labels = df[~df["sif_precursor"].isin(VALID_SIF_PRECURSOR)]
    if not invalid_labels.empty:
        raise ValueError(
            f"{len(invalid_labels)} rows have invalid sif_precursor values. "
            "Run validate_dataset.py first."
        )

    # ── Deduplication ───────────────────────────────────────────────────────
    normalised_text = df["report_text"].astype(str).str.lower().str.strip()
    before_dedup = len(df)
    df = df[~normalised_text.duplicated(keep="first")].reset_index(drop=True)
    n_dupes_removed = before_dedup - len(df)
    if n_dupes_removed > 0:
        print(
            f"  Removed {n_dupes_removed} exact-duplicate row(s) before splitting"
        )
    print(f"  Rows after deduplication: {len(df)}")

    # ── Stratified split ────────────────────────────────────────────────────
    # Check minimum class size for stratification
    min_class_count = df["sif_precursor"].value_counts().min()
    if min_class_count < 3:
        print(
            f"  WARNING: Minority class has only {min_class_count} sample(s). "
            "Stratification may not be possible — falling back to random split."
        )
        stratify_col = None
    else:
        stratify_col = df["sif_precursor"]

    # Step 1: Split off test set
    test_frac = test_ratio
    train_val, test = train_test_split(
        df,
        test_size=test_frac,
        random_state=seed,
        stratify=stratify_col,
        shuffle=True,
    )

    # Step 2: Split remaining into train + val
    # val_ratio relative to the remaining train_val set
    val_frac_of_remaining = val_ratio / (train_ratio + val_ratio)
    stratify_train_val = train_val["sif_precursor"] if stratify_col is not None else None
    train, val = train_test_split(
        train_val,
        test_size=val_frac_of_remaining,
        random_state=seed,
        stratify=stratify_train_val,
        shuffle=True,
    )

    # Verify no text overlap between train and test
    train_texts = set(train["report_text"].astype(str).str.lower().str.strip())
    test_texts = set(test["report_text"].astype(str).str.lower().str.strip())
    val_texts = set(val["report_text"].astype(str).str.lower().str.strip())
    train_test_overlap = train_texts & test_texts
    train_val_overlap = train_texts & val_texts
    if train_test_overlap:
        raise RuntimeError(
            f"BUG: {len(train_test_overlap)} texts appear in both train and test sets!"
        )
    if train_val_overlap:
        raise RuntimeError(
            f"BUG: {len(train_val_overlap)} texts appear in both train and val sets!"
        )

    # ── Write outputs ───────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train.csv"
    val_path   = output_dir / "val.csv"
    test_path  = output_dir / "test.csv"

    train.to_csv(train_path, index=False)
    val.to_csv(val_path, index=False)
    test.to_csv(test_path, index=False)

    # ── Print summary ───────────────────────────────────────────────────────
    n_total = len(df)
    splits = [
        ("train", train),
        ("val",   val),
        ("test",  test),
    ]

    print(f"\n  Split summary (seed={seed}):")
    print(f"  {'Split':<8} {'N':>6}  {'%':>6}  SIF=1  SIF=0")
    print(f"  {'-'*50}")
    for name, split_df in splits:
        n = len(split_df)
        sif1 = int((split_df["sif_precursor"] == 1).sum())
        sif0 = int((split_df["sif_precursor"] == 0).sum())
        print(f"  {name:<8} {n:>6}  {_pct(n, n_total):>6}  {sif1:>5}  {sif0:>5}")
    print(f"  {'TOTAL':<8} {n_total:>6}  {'100.0%':>6}")

    print(f"\n  No text overlap between train/test: OK")
    print(f"  No text overlap between train/val:  OK")
    print(f"\n  Written to: {output_dir}")

    # ── Build manifest ──────────────────────────────────────────────────────
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "output_dir": str(output_dir),
        "seed": seed,
        "ratios": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio,
        },
        "n_raw": n_raw,
        "n_after_dedup": n_total,
        "n_duplicates_removed": n_dupes_removed,
        "splits": {
            name: {
                "n": len(split_df),
                "pct": round(100.0 * len(split_df) / n_total, 2),
                "class_distribution": _class_dist(split_df),
                "source_distribution": _source_dist(split_df),
            }
            for name, split_df in splits
        },
        "overlap_checks": {
            "train_test_text_overlap": len(train_test_overlap),
            "train_val_text_overlap": len(train_val_overlap),
        },
        "output_files": {
            "train": str(train_path),
            "val":   str(val_path),
            "test":  str(test_path),
        },
    }

    manifest_path = output_dir / "split_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Manifest: {manifest_path}\n")

    return manifest


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Produce a stratified train/val/test split of a SIF Sentinel dataset CSV."
    )
    parser.add_argument("input", type=Path, help="Input CSV file to split.")
    parser.add_argument(
        "--train",
        type=float,
        default=0.70,
        metavar="RATIO",
        help="Fraction of data for training (default: 0.70)",
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.15,
        metavar="RATIO",
        help="Fraction of data for validation (default: 0.15)",
    )
    parser.add_argument(
        "--test",
        type=float,
        default=0.15,
        metavar="RATIO",
        help="Fraction of data for test (default: 0.15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory for output CSVs and manifest "
            "(default: dataset/processed/)"
        ),
    )
    args = parser.parse_args()

    output_dir = args.output_dir or (Path(__file__).resolve().parent / "processed")

    try:
        split_dataset(
            input_path=args.input.resolve(),
            output_dir=output_dir.resolve(),
            train_ratio=args.train,
            val_ratio=args.val,
            test_ratio=args.test,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
