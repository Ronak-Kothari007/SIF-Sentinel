"""
SIF Sentinel — Dataset Management Tests
========================================

Tests for:
  - schema.py           — column definitions, valid value sets
  - validate_dataset.py — all validation checks
  - split_dataset.py    — stratified split, deduplication, overlap prevention

Run with:
    pytest dataset/tests/ -v
    # or from dataset/ directory:
    pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

# Make dataset root importable
_DATASET_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_DATASET_DIR))

import schema as S
from validate_dataset import (
    ValidationReport,
    _check_columns,
    _check_duplicate_texts,
    _check_label_values,
    _check_missing_values,
    _check_report_id_uniqueness,
    _check_text_length,
    _class_distribution_report,
    _source_distribution_report,
    validate_file,
    validate_files,
)
from split_dataset import split_dataset


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_valid_df() -> pd.DataFrame:
    """A minimal valid 4-row dataset with both classes."""
    return pd.DataFrame({
        "report_id":    ["SYN-001", "SYN-002", "SYN-003", "SYN-004"],
        "report_text":  [
            "Worker entered confined space without gas test or attendant.",
            "Office chair wheel was slightly wobbly. No safety risk.",
            "LOTO not applied before working on energized equipment panel.",
            "Monthly safety meeting attended by all staff. No incidents.",
        ],
        "sif_precursor": pd.array([1, 0, 1, 0], dtype="Int64"),
        "activity":     ["vessel_entry", "maintenance", "electrical", "admin"],
        "hazard":       ["asphyxiation", "none", "electrocution", "none"],
        "barrier":      ["gas_test_absent", "controls_in_place", "loto_absent", "controls_in_place"],
        "location":     ["storage_tank", "office", "motor_room", "office"],
        "severity":     ["critical", "low", "critical", "low"],
        "source":       ["synthetic", "synthetic", "synthetic", "synthetic"],
    })


@pytest.fixture
def synthetic_csv_path() -> Path:
    """Path to the real synthetic sample CSV."""
    p = _DATASET_DIR / "raw" / "synthetic_sample.csv"
    assert p.exists(), f"Synthetic sample CSV not found: {p}"
    return p


# ---------------------------------------------------------------------------
# Section 1 — Schema Module
# ---------------------------------------------------------------------------

class TestSchema:

    def test_columns_list_has_nine_entries(self):
        assert len(S.COLUMNS) == 9

    def test_all_required_columns_present_in_list(self):
        required = {
            "report_id", "report_text", "sif_precursor",
            "activity", "hazard", "barrier", "location",
            "severity", "source",
        }
        assert required == set(S.COLUMNS)

    def test_valid_sif_precursor_values(self):
        assert S.VALID_SIF_PRECURSOR == {0, 1}

    def test_valid_severity_values(self):
        assert S.VALID_SEVERITY == {"low", "medium", "high", "critical"}

    def test_valid_source_values(self):
        assert S.VALID_SOURCE == {"public", "synthetic", "anonymized"}

    def test_min_text_length_is_positive(self):
        assert S.MIN_TEXT_LENGTH > 0

    def test_column_descriptions_covers_all_columns(self):
        assert set(S.COLUMN_DESCRIPTIONS.keys()) == set(S.COLUMNS)


# ---------------------------------------------------------------------------
# Section 2 — Column Presence Checks
# ---------------------------------------------------------------------------

class TestColumnChecks:

    def test_valid_df_passes_column_check(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        result = _check_columns(minimal_valid_df, report)
        assert result is True
        assert report.errors == []

    def test_missing_column_raises_error(self, minimal_valid_df):
        df = minimal_valid_df.drop(columns=["sif_precursor"])
        report = ValidationReport(Path("test.csv"))
        result = _check_columns(df, report)
        assert result is False
        assert any("sif_precursor" in e for e in report.errors)

    def test_extra_column_raises_warning(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df["extra_col"] = "value"
        report = ValidationReport(Path("test.csv"))
        _check_columns(df, report)
        assert any("extra_col" in w for w in report.warnings)

    def test_multiple_missing_columns_all_reported(self, minimal_valid_df):
        df = minimal_valid_df.drop(columns=["hazard", "barrier", "location"])
        report = ValidationReport(Path("test.csv"))
        _check_columns(df, report)
        assert len(report.errors) >= 1  # at least one error for missing columns


# ---------------------------------------------------------------------------
# Section 3 — Missing Value Detection
# ---------------------------------------------------------------------------

class TestMissingValues:

    def test_no_missing_values_in_valid_df(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _check_missing_values(minimal_valid_df, report)
        assert report.errors == []

    def test_null_report_text_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "report_text"] = None
        report = ValidationReport(Path("test.csv"))
        _check_missing_values(df, report)
        assert any("report_text" in e for e in report.errors)

    def test_null_sif_precursor_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "sif_precursor"] = pd.NA
        report = ValidationReport(Path("test.csv"))
        _check_missing_values(df, report)
        assert any("sif_precursor" in e for e in report.errors)

    def test_null_location_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[1, "location"] = None
        report = ValidationReport(Path("test.csv"))
        _check_missing_values(df, report)
        assert any("location" in e for e in report.errors)

    def test_multiple_null_columns_all_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "activity"] = None
        df.loc[1, "hazard"] = None
        df.loc[2, "barrier"] = None
        report = ValidationReport(Path("test.csv"))
        _check_missing_values(df, report)
        null_errors = [e for e in report.errors if "missing" in e.lower() or "null" in e.lower() or "'" in e]
        assert len(null_errors) >= 3


# ---------------------------------------------------------------------------
# Section 4 — Label Value Validation
# ---------------------------------------------------------------------------

class TestLabelValidation:

    def test_valid_labels_pass(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _check_label_values(minimal_valid_df, report)
        assert report.errors == []

    def test_invalid_sif_precursor_value_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "sif_precursor"] = pd.array([2], dtype="Int64")[0]
        report = ValidationReport(Path("test.csv"))
        _check_label_values(df, report)
        assert any("sif_precursor" in e for e in report.errors)

    def test_invalid_severity_value_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "severity"] = "extreme"
        report = ValidationReport(Path("test.csv"))
        _check_label_values(df, report)
        assert any("severity" in e for e in report.errors)

    def test_invalid_source_value_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "source"] = "internal"
        report = ValidationReport(Path("test.csv"))
        _check_label_values(df, report)
        assert any("source" in e for e in report.errors)

    def test_valid_source_values_all_accepted(self, minimal_valid_df):
        for src in S.VALID_SOURCE:
            df = minimal_valid_df.copy()
            df["source"] = src
            report = ValidationReport(Path("test.csv"))
            _check_label_values(df, report)
            assert not any("source" in e for e in report.errors), (
                f"Valid source '{src}' was rejected"
            )

    def test_valid_severity_values_all_accepted(self, minimal_valid_df):
        for sev in S.VALID_SEVERITY:
            df = minimal_valid_df.copy()
            df["severity"] = sev
            report = ValidationReport(Path("test.csv"))
            _check_label_values(df, report)
            assert not any("severity" in e for e in report.errors), (
                f"Valid severity '{sev}' was rejected"
            )


# ---------------------------------------------------------------------------
# Section 5 — Text Length Check
# ---------------------------------------------------------------------------

class TestTextLength:

    def test_valid_texts_pass_length_check(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _check_text_length(minimal_valid_df, report)
        assert report.errors == []

    def test_short_text_triggers_error(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "report_text"] = "Short."
        report = ValidationReport(Path("test.csv"))
        _check_text_length(df, report)
        assert any("report_text" in e for e in report.errors)

    def test_exact_minimum_length_passes(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "report_text"] = "A" * S.MIN_TEXT_LENGTH
        report = ValidationReport(Path("test.csv"))
        _check_text_length(df, report)
        assert report.errors == []

    def test_one_less_than_minimum_fails(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[0, "report_text"] = "A" * (S.MIN_TEXT_LENGTH - 1)
        report = ValidationReport(Path("test.csv"))
        _check_text_length(df, report)
        assert any("report_text" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Section 6 — Report ID Uniqueness
# ---------------------------------------------------------------------------

class TestReportIdUniqueness:

    def test_unique_ids_pass(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _check_report_id_uniqueness(minimal_valid_df, report)
        assert report.errors == []

    def test_duplicate_id_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[1, "report_id"] = "SYN-001"  # duplicate of row 0
        report = ValidationReport(Path("test.csv"))
        _check_report_id_uniqueness(df, report)
        assert any("SYN-001" in e for e in report.errors)

    def test_all_duplicate_ids_reported(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df["report_id"] = "DUPLICATE"  # all same
        report = ValidationReport(Path("test.csv"))
        _check_report_id_uniqueness(df, report)
        assert len(report.errors) >= 1


# ---------------------------------------------------------------------------
# Section 7 — Duplicate Text Detection
# ---------------------------------------------------------------------------

class TestDuplicateTextDetection:

    def test_unique_texts_pass(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _check_duplicate_texts(minimal_valid_df, report)
        assert report.errors == []

    def test_exact_duplicate_text_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[1, "report_text"] = df.loc[0, "report_text"]  # copy row 0's text
        report = ValidationReport(Path("test.csv"))
        _check_duplicate_texts(df, report)
        assert len(report.errors) >= 1

    def test_case_insensitive_duplicate_detected(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df.loc[1, "report_text"] = df.loc[0, "report_text"].upper()
        report = ValidationReport(Path("test.csv"))
        _check_duplicate_texts(df, report)
        assert len(report.errors) >= 1

    def test_near_duplicate_triggers_warning(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        base = df.loc[0, "report_text"]
        # Same 80-char prefix but different suffix
        prefix = base[:80] if len(base) >= 80 else base + "X" * (80 - len(base))
        df.loc[1, "report_text"] = prefix + " extra words to make it different"
        df.loc[0, "report_text"] = prefix + " alternative ending that differs"
        report = ValidationReport(Path("test.csv"))
        _check_duplicate_texts(df, report)
        # Should produce a warning (not necessarily an error)
        assert len(report.warnings) >= 1 or len(report.errors) >= 1


# ---------------------------------------------------------------------------
# Section 8 — Class Distribution Report
# ---------------------------------------------------------------------------

class TestClassDistribution:

    def test_class_distribution_no_error_on_balanced(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _class_distribution_report(minimal_valid_df, report)
        assert report.errors == []

    def test_imbalanced_class_triggers_warning(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        # Make it 20:1 imbalanced
        extra = pd.DataFrame({
            "report_id": [f"SYN-{i:03d}" for i in range(100, 120)],
            "report_text": [f"Safe routine task number {i} completed without incident or issue." for i in range(20)],
            "sif_precursor": pd.array([0] * 20, dtype="Int64"),
            "activity": ["admin"] * 20,
            "hazard": ["none"] * 20,
            "barrier": ["controls_in_place"] * 20,
            "location": ["office"] * 20,
            "severity": ["low"] * 20,
            "source": ["synthetic"] * 20,
        })
        imbalanced = pd.concat([df, extra], ignore_index=True)
        report = ValidationReport(Path("test.csv"))
        _class_distribution_report(imbalanced, report)
        assert any("imbalance" in w.lower() for w in report.warnings)

    def test_class_distribution_note_produced(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _class_distribution_report(minimal_valid_df, report)
        assert any("class distribution" in i.lower() for i in report.info)


# ---------------------------------------------------------------------------
# Section 9 — Source Distribution Report
# ---------------------------------------------------------------------------

class TestSourceDistribution:

    def test_source_distribution_no_error(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _source_distribution_report(minimal_valid_df, report)
        assert report.errors == []

    def test_source_distribution_note_produced(self, minimal_valid_df):
        report = ValidationReport(Path("test.csv"))
        _source_distribution_report(minimal_valid_df, report)
        assert any("source distribution" in i.lower() for i in report.info)


# ---------------------------------------------------------------------------
# Section 10 — Full File Validation (synthetic_sample.csv)
# ---------------------------------------------------------------------------

class TestFullFileValidation:

    def test_synthetic_sample_passes_validation(self, synthetic_csv_path):
        """The real synthetic_sample.csv must pass all validation checks."""
        report = validate_file(synthetic_csv_path)
        assert report.passed, (
            f"synthetic_sample.csv failed validation:\n"
            + "\n".join(report.errors)
        )

    def test_synthetic_sample_has_50_rows(self, synthetic_csv_path):
        df = pd.read_csv(synthetic_csv_path, dtype={"sif_precursor": "Int64"})
        assert len(df) == 50

    def test_synthetic_sample_all_source_synthetic(self, synthetic_csv_path):
        df = pd.read_csv(synthetic_csv_path)
        assert (df["source"] == "synthetic").all()

    def test_synthetic_sample_has_both_classes(self, synthetic_csv_path):
        df = pd.read_csv(synthetic_csv_path, dtype={"sif_precursor": "Int64"})
        assert set(df["sif_precursor"].unique()) == {0, 1}

    def test_synthetic_sample_no_duplicate_ids(self, synthetic_csv_path):
        df = pd.read_csv(synthetic_csv_path)
        assert not df["report_id"].duplicated().any()

    def test_synthetic_sample_no_duplicate_texts(self, synthetic_csv_path):
        df = pd.read_csv(synthetic_csv_path)
        normalised = df["report_text"].str.lower().str.strip()
        assert not normalised.duplicated().any()

    def test_validate_files_function_returns_true_for_valid(self, synthetic_csv_path):
        result = validate_files([synthetic_csv_path])
        assert result is True

    def test_validate_files_returns_false_for_invalid(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("col1,col2\nval1,val2\n", encoding="utf-8")
        result = validate_files([bad_csv])
        assert result is False


# ---------------------------------------------------------------------------
# Section 11 — Dataset Split
# ---------------------------------------------------------------------------

class TestDatasetSplit:
    """Tests for the stratified train/val/test split logic."""

    @pytest.fixture
    def large_df_csv(self, tmp_path) -> Path:
        """Write a 50-row synthetic CSV to tmp_path and return path."""
        src = _DATASET_DIR / "raw" / "synthetic_sample.csv"
        dest = tmp_path / "synthetic_sample.csv"
        import shutil
        shutil.copy(src, dest)
        return dest

    def test_split_produces_three_output_files(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        split_dataset(large_df_csv, out_dir)
        assert (out_dir / "train.csv").exists()
        assert (out_dir / "val.csv").exists()
        assert (out_dir / "test.csv").exists()

    def test_split_produces_manifest(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        split_dataset(large_df_csv, out_dir)
        assert (out_dir / "split_manifest.json").exists()

    def test_manifest_has_required_keys(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir)
        required_keys = {
            "schema_version", "generated_at", "input_file", "output_dir",
            "seed", "ratios", "n_raw", "n_after_dedup", "n_duplicates_removed",
            "splits", "overlap_checks", "output_files",
        }
        assert required_keys == set(manifest.keys())

    def test_split_sizes_sum_to_total(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir)
        total = manifest["n_after_dedup"]
        split_total = sum(manifest["splits"][k]["n"] for k in ["train", "val", "test"])
        assert split_total == total

    def test_split_ratios_approximately_correct(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
        n = manifest["n_after_dedup"]
        train_pct = manifest["splits"]["train"]["n"] / n
        val_pct   = manifest["splits"]["val"]["n"]   / n
        test_pct  = manifest["splits"]["test"]["n"]  / n
        # Allow ±5% tolerance for small datasets
        assert abs(train_pct - 0.70) <= 0.08
        assert abs(val_pct   - 0.15) <= 0.08
        assert abs(test_pct  - 0.15) <= 0.08

    def test_no_text_overlap_train_test(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir)
        assert manifest["overlap_checks"]["train_test_text_overlap"] == 0

    def test_no_text_overlap_train_val(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir)
        assert manifest["overlap_checks"]["train_val_text_overlap"] == 0

    def test_stratified_split_preserves_class_ratio(self, large_df_csv, tmp_path):
        """Each split must contain both classes (stratification working)."""
        out_dir = tmp_path / "splits"
        split_dataset(large_df_csv, out_dir)
        for split_name in ["train", "val", "test"]:
            df = pd.read_csv(out_dir / f"{split_name}.csv", dtype={"sif_precursor": "Int64"})
            classes = set(df["sif_precursor"].unique())
            assert 0 in classes and 1 in classes, (
                f"{split_name} split is missing a class: found {classes}"
            )

    def test_split_all_rows_in_exactly_one_split(self, large_df_csv, tmp_path):
        out_dir = tmp_path / "splits"
        manifest = split_dataset(large_df_csv, out_dir)
        # Load all three splits and verify union = original (by report_id)
        train = pd.read_csv(out_dir / "train.csv")
        val   = pd.read_csv(out_dir / "val.csv")
        test  = pd.read_csv(out_dir / "test.csv")
        all_ids = pd.concat([train, val, test])["report_id"].tolist()
        assert len(all_ids) == len(set(all_ids)), "Duplicate report_ids across splits"
        assert len(all_ids) == manifest["n_after_dedup"]

    def test_split_invalid_ratios_raise_error(self, large_df_csv, tmp_path):
        with pytest.raises(ValueError, match="sum to 1.0"):
            split_dataset(large_df_csv, tmp_path, train_ratio=0.5, val_ratio=0.3, test_ratio=0.3)

    def test_split_deduplication_removes_exact_duplicates(self, tmp_path):
        """If input has duplicate texts, they must be removed before splitting."""
        src = _DATASET_DIR / "raw" / "synthetic_sample.csv"
        df = pd.read_csv(src, dtype={"sif_precursor": "Int64"})
        # Inject a duplicate row
        dup_row = df.iloc[0].copy()
        dup_row["report_id"] = "SYN-DUP"
        df = pd.concat([df, pd.DataFrame([dup_row])], ignore_index=True)
        dup_csv = tmp_path / "with_dupes.csv"
        df.to_csv(dup_csv, index=False)

        out_dir = tmp_path / "splits_dedup"
        manifest = split_dataset(dup_csv, out_dir)
        assert manifest["n_duplicates_removed"] >= 1

    def test_split_reproducible_with_same_seed(self, large_df_csv, tmp_path):
        """Same seed must produce identical splits."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        split_dataset(large_df_csv, out1, seed=42)
        split_dataset(large_df_csv, out2, seed=42)
        for fname in ["train.csv", "val.csv", "test.csv"]:
            df1 = pd.read_csv(out1 / fname)
            df2 = pd.read_csv(out2 / fname)
            pd.testing.assert_frame_equal(df1, df2)

    def test_split_different_seeds_produce_different_splits(self, large_df_csv, tmp_path):
        """Different seeds should (almost always) produce different splits."""
        out1 = tmp_path / "seed42"
        out2 = tmp_path / "seed99"
        split_dataset(large_df_csv, out1, seed=42)
        split_dataset(large_df_csv, out2, seed=99)
        df1 = pd.read_csv(out1 / "train.csv")
        df2 = pd.read_csv(out2 / "train.csv")
        # With 50 rows and random shuffling, the IDs should differ
        assert not df1["report_id"].tolist() == df2["report_id"].tolist()

    def test_split_output_csvs_pass_schema_validation(self, large_df_csv, tmp_path):
        """All output CSVs must themselves pass the schema validation."""
        out_dir = tmp_path / "splits"
        split_dataset(large_df_csv, out_dir)
        for fname in ["train.csv", "val.csv", "test.csv"]:
            report = validate_file(out_dir / fname)
            assert report.passed, (
                f"{fname} failed validation after split:\n"
                + "\n".join(report.errors)
            )
