"""
SIF Sentinel — Dataset Validation Script
=========================================

Validates one or more SIF Sentinel CSV files against the canonical schema.

Checks performed:
  1. Required columns present
  2. No extra/unknown columns
  3. Missing values detected per column
  4. sif_precursor values are 0 or 1
  5. severity values are in {low, medium, high, critical}
  6. source values are in {public, synthetic, anonymized}
  7. report_id uniqueness (within file)
  8. report_text minimum length
  9. Duplicate report_text detection (exact and near-duplicate)
 10. Class distribution report for sif_precursor
 11. Source distribution report

Usage:
    python validate_dataset.py path/to/file.csv [path/to/file2.csv ...]
    python validate_dataset.py --all        # validates all CSVs in raw/ and processed/

Exit codes:
    0 = all validations passed (or only warnings issued)
    1 = one or more errors found
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Safe encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

# Allow running from any directory
_DATASET_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_DATASET_DIR))
from schema import (
    COLUMNS,
    MIN_TEXT_LENGTH,
    VALID_SEVERITY,
    VALID_SIF_PRECURSOR,
    VALID_SOURCE,
)


# ---------------------------------------------------------------------------
# ANSI colour helpers (graceful fallback on Windows without colour support)
# ---------------------------------------------------------------------------

try:
    import os
    _USE_COLOR = sys.stdout.isatty() and os.name != "nt"
except Exception:
    _USE_COLOR = False


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def red(t: str) -> str:    return _c(t, "31")
def green(t: str) -> str:  return _c(t, "32")
def yellow(t: str) -> str: return _c(t, "33")
def bold(t: str) -> str:   return _c(t, "1")
def cyan(t: str) -> str:   return _c(t, "36")


# ---------------------------------------------------------------------------
# Validation result accumulator
# ---------------------------------------------------------------------------

class ValidationReport:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def note(self, msg: str):
        self.info.append(msg)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def print_summary(self):
        label = green("PASS") if self.passed else red("FAIL")
        print(f"\n{bold(str(self.filepath.name))}  [{label}]")
        print(f"  Errors:   {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")
        for e in self.errors:
            print(f"  {red('ERROR')}   {e}")
        for w in self.warnings:
            print(f"  {yellow('WARN')}    {w}")
        for i in self.info:
            print(f"  {cyan('INFO')}    {i}")


# ---------------------------------------------------------------------------
# Core validation checks
# ---------------------------------------------------------------------------

def _check_columns(df: pd.DataFrame, report: ValidationReport) -> bool:
    """Check that all required columns are present and no extra columns exist."""
    present = set(df.columns.tolist())
    required = set(COLUMNS)

    missing_cols = required - present
    extra_cols = present - required

    if missing_cols:
        report.error(f"Missing required columns: {sorted(missing_cols)}")
        return False  # can't proceed without required columns

    if extra_cols:
        report.warn(f"Extra columns found (not in schema): {sorted(extra_cols)}")

    return True


def _check_missing_values(df: pd.DataFrame, report: ValidationReport):
    """Detect missing (NaN / empty string) values per column."""
    for col in COLUMNS:
        if col not in df.columns:
            continue
        null_count = df[col].isna().sum()
        if col == "report_text":
            empty_str = (df[col].astype(str).str.strip() == "").sum()
            null_count += empty_str
        if null_count > 0:
            report.error(
                f"Column '{col}': {null_count} missing value(s) "
                f"(row indices: {list(df[df[col].isna()].index[:5])}{'...' if null_count > 5 else ''})"
            )
        else:
            report.note(f"Column '{col}': no missing values")


def _check_label_values(df: pd.DataFrame, report: ValidationReport):
    """Validate sif_precursor, severity, and source column values."""
    # sif_precursor
    if "sif_precursor" in df.columns:
        invalid = df[~df["sif_precursor"].isin(VALID_SIF_PRECURSOR)]
        if not invalid.empty:
            report.error(
                f"'sif_precursor' has {len(invalid)} invalid value(s): "
                f"{invalid['sif_precursor'].unique().tolist()}. "
                f"Must be 0 or 1."
            )

    # severity
    if "severity" in df.columns:
        invalid = df[~df["severity"].str.lower().isin(VALID_SEVERITY)]
        if not invalid.empty:
            report.error(
                f"'severity' has {len(invalid)} invalid value(s): "
                f"{invalid['severity'].unique().tolist()}. "
                f"Valid: {sorted(VALID_SEVERITY)}"
            )

    # source
    if "source" in df.columns:
        invalid = df[~df["source"].str.lower().isin(VALID_SOURCE)]
        if not invalid.empty:
            report.error(
                f"'source' has {len(invalid)} invalid value(s): "
                f"{invalid['source'].unique().tolist()}. "
                f"Valid: {sorted(VALID_SOURCE)}"
            )


def _check_text_length(df: pd.DataFrame, report: ValidationReport):
    """Flag report texts that are shorter than the minimum allowed length."""
    if "report_text" not in df.columns:
        return
    short = df[df["report_text"].astype(str).str.len() < MIN_TEXT_LENGTH]
    if not short.empty:
        report.error(
            f"'report_text': {len(short)} row(s) shorter than {MIN_TEXT_LENGTH} chars. "
            f"IDs: {short['report_id'].tolist()[:10]}"
        )
    else:
        report.note(f"'report_text': all texts >= {MIN_TEXT_LENGTH} chars")


def _check_report_id_uniqueness(df: pd.DataFrame, report: ValidationReport):
    """Detect duplicate report_id values within the file."""
    if "report_id" not in df.columns:
        return
    dupes = df[df["report_id"].duplicated(keep=False)]
    if not dupes.empty:
        dup_ids = dupes["report_id"].unique().tolist()
        report.error(
            f"'report_id': {len(dup_ids)} duplicate ID(s) found: {dup_ids[:10]}"
        )
    else:
        report.note(f"'report_id': all {len(df)} IDs are unique")


def _check_duplicate_texts(df: pd.DataFrame, report: ValidationReport):
    """
    Detect duplicate report texts.

    Exact duplicates: identical normalised text.
    Near-duplicates: texts that share the same first 80 characters after normalisation.
    """
    if "report_text" not in df.columns:
        return

    # Exact duplicates
    normalised = df["report_text"].astype(str).str.lower().str.strip()
    exact_dupes = df[normalised.duplicated(keep=False)]
    if not exact_dupes.empty:
        n = exact_dupes["report_id"].nunique()
        report.error(
            f"Exact duplicate report_text found in {n} rows: "
            f"{exact_dupes['report_id'].tolist()[:10]}"
        )
    else:
        report.note("No exact duplicate report texts found")

    # Near-duplicate detection (same 80-char prefix)
    prefix_80 = normalised.str[:80]
    prefix_dupes = df[prefix_80.duplicated(keep=False) & ~normalised.duplicated(keep=False)]
    if not prefix_dupes.empty:
        report.warn(
            f"Possible near-duplicate texts ({len(prefix_dupes)} rows share same 80-char prefix): "
            f"{prefix_dupes['report_id'].tolist()[:10]}"
        )
    else:
        report.note("No near-duplicate texts detected (80-char prefix check)")


def _class_distribution_report(df: pd.DataFrame, report: ValidationReport):
    """Print class distribution for sif_precursor."""
    if "sif_precursor" not in df.columns:
        return
    counts = df["sif_precursor"].value_counts().sort_index()
    total = len(df)
    lines = ["Class distribution for 'sif_precursor':"]
    for label, count in counts.items():
        pct = 100.0 * count / total
        bar = "#" * int(pct / 5)
        lines.append(f"    {label} ({['Non-SIF','SIF-Precursor'][int(label)]}): "
                     f"{count:4d} / {total} ({pct:5.1f}%) {bar}")
    # Imbalance warning
    if len(counts) == 1:
        report.warn(
            f"Only one class present ({counts.index[0]}). "
            "Dataset cannot be used for binary classification training."
        )
    elif len(counts) == 2:
        minority = counts.min()
        majority = counts.max()
        ratio = majority / minority if minority > 0 else float("inf")
        if ratio > 4.0:
            report.warn(
                f"Class imbalance detected - majority:minority ratio = {ratio:.1f}:1. "
                "Consider oversampling, undersampling, or class-weighted loss."
            )
    report.note("\n".join(lines))


def _source_distribution_report(df: pd.DataFrame, report: ValidationReport):
    """Print source distribution."""
    if "source" not in df.columns:
        return
    counts = df["source"].value_counts()
    lines = ["Source distribution:"]
    for src, count in counts.items():
        pct = 100.0 * count / len(df)
        lines.append(f"    {src}: {count} ({pct:.1f}%)")
    report.note("\n".join(lines))


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate_file(filepath: Path) -> ValidationReport:
    """Run all validation checks on a single CSV file."""
    report = ValidationReport(filepath)

    # Load CSV
    try:
        df = pd.read_csv(filepath, dtype={"sif_precursor": "Int64", "report_id": str})
    except Exception as exc:
        report.error(f"Failed to read CSV: {exc}")
        return report

    report.note(f"Loaded {len(df)} rows x {len(df.columns)} columns")

    # Run checks
    if not _check_columns(df, report):
        return report  # can't continue without required columns

    _check_missing_values(df, report)
    _check_label_values(df, report)
    _check_text_length(df, report)
    _check_report_id_uniqueness(df, report)
    _check_duplicate_texts(df, report)
    _class_distribution_report(df, report)
    _source_distribution_report(df, report)

    return report


def validate_files(paths: list[Path]) -> bool:
    """Validate multiple files. Returns True if all pass."""
    all_passed = True
    print(bold(f"\n{'='*60}"))
    print(bold("  SIF Sentinel - Dataset Validation"))
    print(bold(f"{'='*60}"))
    print(f"  Files to validate: {len(paths)}")

    for path in paths:
        if not path.exists():
            print(f"\n{red('ERROR')} File not found: {path}")
            all_passed = False
            continue
        report = validate_file(path)
        report.print_summary()
        if not report.passed:
            all_passed = False

    print(bold(f"\n{'='*60}"))
    outcome = green("ALL PASSED") if all_passed else red("VALIDATION FAILED")
    print(f"  Overall: {outcome}")
    print(bold(f"{'='*60}\n"))
    return all_passed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate SIF Sentinel dataset CSV files against the canonical schema."
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="CSV file(s) to validate.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all CSV files found in dataset/raw/ and dataset/processed/.",
    )
    args = parser.parse_args()

    dataset_dir = Path(__file__).resolve().parent

    if args.all or not args.files:
        paths = sorted(
            list((dataset_dir / "raw").glob("*.csv"))
            + list((dataset_dir / "processed").glob("*.csv"))
        )
        if not paths:
            print(yellow("No CSV files found in dataset/raw/ or dataset/processed/"))
            sys.exit(0)
    else:
        paths = [p.resolve() for p in args.files]

    passed = validate_files(paths)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
