"""
SIF Sentinel -- Phase 4: Baseline Classifier Tests
====================================================

Tests for:
  - train_baseline.py  -- pipeline construction, metric computation, top features
  - predict_baseline.py -- BaselinePredictor inference, batch, model_info, errors

The tests use the *real* trained model in models/baseline/baseline_pipeline.joblib.
They do NOT mock the pipeline so that we catch actual inference regressions.

Sections:
  1. TestBuildPipeline      -- pipeline construction
  2. TestLoadSplit          -- CSV loading helpers
  3. TestComputeMetrics     -- metric correctness against known inputs
  4. TestTopFeatures        -- feature extraction from trained model
  5. TestBaselinePredictor  -- single-text prediction, confidence labels
  6. TestBatchPredict       -- batch prediction
  7. TestModelInfo          -- model metadata structure
  8. TestPredictorErrors    -- error handling (missing model, empty text)
  9. TestRealModelInference -- end-to-end inference on known examples using real model
  10. TestPredictFunction   -- module-level predict_text helper
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Resolve project root so imports work from any working directory
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from models.train_baseline import build_pipeline, compute_metrics, load_split, top_features
from models.predict_baseline import BaselinePredictor, _confidence_label, predict_text

_MODEL_PATH = _ROOT / "models" / "baseline" / "baseline_pipeline.joblib"
_MODEL_EXISTS = _MODEL_PATH.exists()

pytestmark_needs_model = pytest.mark.skipif(
    not _MODEL_EXISTS,
    reason="Trained model not found -- run 'python models/train_baseline.py' first",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def predictor():
    """Load the real trained model once for the entire module."""
    if not _MODEL_EXISTS:
        pytest.skip("Trained model not found")
    return BaselinePredictor(model_path=_MODEL_PATH)


@pytest.fixture
def tiny_pipeline():
    """A fresh (untrained) pipeline for structural tests."""
    return build_pipeline()


@pytest.fixture
def small_csv(tmp_path):
    """Write a minimal valid CSV split to a temp file and return its Path."""
    df = pd.DataFrame({
        "report_id":    ["SYN-001", "SYN-002", "SYN-003", "SYN-004"],
        "report_text":  [
            "Worker entered confined space without gas test or permit.",
            "Routine toolbox meeting held. No incidents reported.",
            "Hot work without permit near flammable storage area.",
            "Fire extinguisher inspection completed successfully.",
        ],
        "sif_precursor": [1, 0, 1, 0],
        "activity":      ["excavation", "pre_task", "welding", "inspection"],
        "hazard":        ["asphyxiation", "none", "fire", "none"],
        "barrier":       ["absent", "controls_in_place", "absent", "controls_in_place"],
        "location":      ["pit", "office", "yard", "plant"],
        "severity":      ["critical", "low", "high", "low"],
        "source":        ["synthetic"] * 4,
    })
    p = tmp_path / "test_split.csv"
    df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------------------------
# 1. TestBuildPipeline
# ---------------------------------------------------------------------------

class TestBuildPipeline:
    def test_pipeline_has_two_steps(self, tiny_pipeline):
        assert len(tiny_pipeline.steps) == 2

    def test_pipeline_step_names(self, tiny_pipeline):
        assert tiny_pipeline.steps[0][0] == "tfidf"
        assert tiny_pipeline.steps[1][0] == "lr"

    def test_tfidf_ngram_range(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["tfidf"].ngram_range == (1, 2)

    def test_tfidf_max_features(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["tfidf"].max_features == 5000

    def test_tfidf_sublinear_tf(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["tfidf"].sublinear_tf is True

    def test_lr_class_weight_balanced(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["lr"].class_weight == "balanced"

    def test_lr_max_iter(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["lr"].max_iter == 1000

    def test_lr_solver(self, tiny_pipeline):
        assert tiny_pipeline.named_steps["lr"].solver == "lbfgs"

    def test_pipeline_fits_tiny_data(self, tiny_pipeline):
        texts  = ["gas test absent in confined space", "routine safety meeting held"]
        labels = [1, 0]
        tiny_pipeline.fit(texts, labels)
        preds = tiny_pipeline.predict(texts)
        assert len(preds) == 2


# ---------------------------------------------------------------------------
# 2. TestLoadSplit
# ---------------------------------------------------------------------------

class TestLoadSplit:
    def test_load_returns_tuple(self, small_csv):
        texts, labels = load_split(small_csv)
        assert isinstance(texts, list)
        assert isinstance(labels, list)

    def test_load_correct_length(self, small_csv):
        texts, labels = load_split(small_csv)
        assert len(texts) == 4
        assert len(labels) == 4

    def test_load_labels_are_ints(self, small_csv):
        _, labels = load_split(small_csv)
        for lbl in labels:
            assert isinstance(lbl, int)
            assert lbl in {0, 1}

    def test_load_texts_are_strings(self, small_csv):
        texts, _ = load_split(small_csv)
        for t in texts:
            assert isinstance(t, str)

    def test_load_missing_column_raises(self, tmp_path):
        p = tmp_path / "bad.csv"
        pd.DataFrame({"report_id": ["x"], "report_text": ["text"]}).to_csv(p, index=False)
        with pytest.raises(ValueError, match="missing columns"):
            load_split(p)


# ---------------------------------------------------------------------------
# 3. TestComputeMetrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def _make_probs(self, y_pred):
        """Convert binary predictions to fake probability arrays for metric tests."""
        probs = []
        for p in y_pred:
            probs.append(0.9 if p == 1 else 0.1)
        return np.array(probs)

    def test_perfect_predictions_all_ones(self):
        y_true = [1, 1, 1, 0, 0]
        y_pred = [1, 1, 1, 0, 0]
        probs  = self._make_probs(y_pred)
        m = compute_metrics(y_true, y_pred, probs, "test")
        assert m["metrics"]["precision"] == 1.0
        assert m["metrics"]["recall"] == 1.0
        assert m["metrics"]["f1_score"] == 1.0
        assert m["metrics"]["f2_score"] == 1.0

    def test_all_wrong_predictions(self):
        y_true = [1, 1, 0, 0]
        y_pred = [0, 0, 1, 1]
        probs  = self._make_probs(y_pred)
        m = compute_metrics(y_true, y_pred, probs, "test")
        assert m["metrics"]["precision"] == 0.0
        assert m["metrics"]["recall"] == 0.0

    def test_f2_weights_recall_over_precision(self):
        # High recall, low precision scenario: F2 should be decent
        y_true = [1, 1, 1, 0, 0, 0]
        y_pred = [1, 1, 1, 1, 1, 0]  # TP=3 FP=2 FN=0 TN=1
        probs  = self._make_probs(y_pred)
        m = compute_metrics(y_true, y_pred, probs, "test")
        assert m["metrics"]["recall"] == 1.0
        assert m["metrics"]["f2_score"] > m["metrics"]["f1_score"]

    def test_confusion_matrix_structure(self):
        y_true = [1, 0, 1, 0]
        y_pred = [1, 0, 0, 1]  # FN=1, FP=1
        probs  = self._make_probs(y_pred)
        m = compute_metrics(y_true, y_pred, probs, "test")
        cm = m["confusion_matrix"]
        assert cm["tp"] == 1
        assert cm["tn"] == 1
        assert cm["fn"] == 1
        assert cm["fp"] == 1

    def test_n_samples_is_correct(self):
        y = [0, 1, 0, 1, 1]
        m = compute_metrics(y, y, self._make_probs(y), "test")
        assert m["n_samples"] == 5

    def test_n_positive_negative(self):
        y_true = [1, 1, 0, 0, 0]
        m = compute_metrics(y_true, y_true, self._make_probs(y_true), "test")
        assert m["n_positive"] == 2
        assert m["n_negative"] == 3

    def test_metrics_dict_has_required_keys(self):
        y = [0, 1]
        m = compute_metrics(y, y, self._make_probs(y), "train")
        for key in ("precision", "recall", "f1_score", "f2_score"):
            assert key in m["metrics"]

    def test_classification_report_in_output(self):
        y = [0, 1, 0, 1]
        m = compute_metrics(y, y, self._make_probs(y), "val")
        assert "classification_report" in m
        assert isinstance(m["classification_report"], dict)

    def test_split_name_stored(self):
        y = [0, 1]
        m = compute_metrics(y, y, self._make_probs(y), "my_split")
        assert m["split"] == "my_split"

    def test_roc_auc_none_for_single_class(self):
        y_true = [1, 1, 1]
        y_pred = [1, 1, 1]
        probs  = np.array([0.9, 0.8, 0.95])
        m = compute_metrics(y_true, y_pred, probs, "test")
        assert m["metrics"]["roc_auc"] is None


# ---------------------------------------------------------------------------
# 4. TestTopFeatures
# ---------------------------------------------------------------------------

class TestTopFeatures:
    @pytestmark_needs_model
    def test_top_features_has_required_keys(self, predictor):
        features = top_features(predictor._pipeline, n=10)
        assert "top_sif_precursor_features" in features
        assert "top_non_sif_features" in features

    @pytestmark_needs_model
    def test_top_sif_features_count(self, predictor):
        features = top_features(predictor._pipeline, n=10)
        assert len(features["top_sif_precursor_features"]) == 10

    @pytestmark_needs_model
    def test_top_non_sif_features_count(self, predictor):
        features = top_features(predictor._pipeline, n=10)
        assert len(features["top_non_sif_features"]) == 10

    @pytestmark_needs_model
    def test_each_feature_has_feature_and_coefficient(self, predictor):
        features = top_features(predictor._pipeline, n=5)
        for f in features["top_sif_precursor_features"]:
            assert "feature" in f
            assert "coefficient" in f
            assert isinstance(f["feature"], str)
            assert isinstance(f["coefficient"], float)

    @pytestmark_needs_model
    def test_sif_features_have_positive_coefficients(self, predictor):
        features = top_features(predictor._pipeline, n=5)
        for f in features["top_sif_precursor_features"]:
            assert f["coefficient"] > 0, (
                f"SIF feature '{f['feature']}' should have positive coefficient"
            )

    @pytestmark_needs_model
    def test_non_sif_features_have_negative_coefficients(self, predictor):
        features = top_features(predictor._pipeline, n=5)
        for f in features["top_non_sif_features"]:
            assert f["coefficient"] < 0, (
                f"Non-SIF feature '{f['feature']}' should have negative coefficient"
            )


# ---------------------------------------------------------------------------
# 5. TestBaselinePredictor
# ---------------------------------------------------------------------------

class TestBaselinePredictor:
    @pytestmark_needs_model
    def test_predict_returns_dict(self, predictor):
        result = predictor.predict("Worker found in confined space without gas test.")
        assert isinstance(result, dict)

    @pytestmark_needs_model
    def test_predict_has_required_keys(self, predictor):
        result = predictor.predict("Some safety text report here for the test.")
        for key in ("text", "sif_prediction", "sif_probability", "non_sif_probability",
                    "confidence_label", "model"):
            assert key in result, f"Missing key: {key}"

    @pytestmark_needs_model
    def test_predict_sif_prediction_is_0_or_1(self, predictor):
        result = predictor.predict("Some safety text report here.")
        assert result["sif_prediction"] in {0, 1}

    @pytestmark_needs_model
    def test_probabilities_sum_to_one(self, predictor):
        result = predictor.predict("Worker at height without harness.")
        total = result["sif_probability"] + result["non_sif_probability"]
        assert abs(total - 1.0) < 1e-4

    @pytestmark_needs_model
    def test_sif_probability_is_float(self, predictor):
        result = predictor.predict("Confined space entry without gas test.")
        assert isinstance(result["sif_probability"], float)

    @pytestmark_needs_model
    def test_probability_in_range(self, predictor):
        result = predictor.predict("Worker in exclusion zone during crane lift.")
        assert 0.0 <= result["sif_probability"] <= 1.0

    @pytestmark_needs_model
    def test_model_name_is_baseline(self, predictor):
        result = predictor.predict("Some report text for testing purposes.")
        assert result["model"] == "tfidf_lr_baseline"

    @pytestmark_needs_model
    def test_sif_report_predicts_high_probability(self, predictor):
        """A clear SIF report should score >0.5 probability for sif_precursor=1."""
        text = "Worker entered confined space without gas test. No attendant present."
        result = predictor.predict(text)
        assert result["sif_probability"] > 0.5, (
            f"Expected SIF probability > 0.5 for clear SIF report, got {result['sif_probability']}"
        )

    @pytestmark_needs_model
    def test_non_sif_report_predicts_low_probability(self, predictor):
        """A clearly non-SIF report should score <0.5 probability for sif_precursor=1."""
        text = "Monthly safety statistics meeting held. No incidents this period. All workers complied."
        result = predictor.predict(text)
        assert result["sif_probability"] < 0.5, (
            f"Expected SIF probability < 0.5 for non-SIF report, got {result['sif_probability']}"
        )

    @pytestmark_needs_model
    def test_text_truncated_at_200_chars(self, predictor):
        long_text = "A" * 300
        result = predictor.predict(long_text)
        assert len(result["text"]) <= 204  # 200 + len("...")


# ---------------------------------------------------------------------------
# 6. TestBatchPredict
# ---------------------------------------------------------------------------

class TestBatchPredict:
    @pytestmark_needs_model
    def test_batch_returns_list(self, predictor):
        texts = [
            "Worker at height without harness.",
            "Toolbox meeting completed. No incidents.",
        ]
        results = predictor.predict_batch(texts)
        assert isinstance(results, list)

    @pytestmark_needs_model
    def test_batch_length_matches_input(self, predictor):
        texts = ["text one", "text two", "text three"]
        results = predictor.predict_batch(texts)
        assert len(results) == 3

    @pytestmark_needs_model
    def test_batch_each_result_has_required_keys(self, predictor):
        texts = ["Worker fell from scaffold without harness.", "Inspection completed OK."]
        for result in predictor.predict_batch(texts):
            for key in ("sif_prediction", "sif_probability", "non_sif_probability", "confidence_label"):
                assert key in result

    @pytestmark_needs_model
    def test_batch_empty_input_returns_empty_list(self, predictor):
        assert predictor.predict_batch([]) == []

    @pytestmark_needs_model
    def test_batch_probabilities_sum_to_one(self, predictor):
        texts = ["Some text for testing prediction batch mode here."]
        result = predictor.predict_batch(texts)[0]
        total = result["sif_probability"] + result["non_sif_probability"]
        assert abs(total - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# 7. TestModelInfo
# ---------------------------------------------------------------------------

class TestModelInfo:
    @pytestmark_needs_model
    def test_model_info_is_dict(self, predictor):
        info = predictor.model_info()
        assert isinstance(info, dict)

    @pytestmark_needs_model
    def test_model_info_has_required_keys(self, predictor):
        info = predictor.model_info()
        for key in ("model", "vectorizer", "classifier", "vocabulary_size",
                    "ngram_range", "n_classes", "classes"):
            assert key in info, f"Missing key: {key}"

    @pytestmark_needs_model
    def test_model_is_tfidf_lr_baseline(self, predictor):
        info = predictor.model_info()
        assert info["model"] == "tfidf_lr_baseline"

    @pytestmark_needs_model
    def test_n_classes_is_2(self, predictor):
        info = predictor.model_info()
        assert info["n_classes"] == 2

    @pytestmark_needs_model
    def test_classes_contains_0_and_1(self, predictor):
        info = predictor.model_info()
        assert set(info["classes"]) == {0, 1}

    @pytestmark_needs_model
    def test_vocabulary_size_is_positive(self, predictor):
        info = predictor.model_info()
        assert info["vocabulary_size"] > 0

    @pytestmark_needs_model
    def test_ngram_range_is_1_2(self, predictor):
        info = predictor.model_info()
        assert info["ngram_range"] == [1, 2]


# ---------------------------------------------------------------------------
# 8. TestPredictorErrors
# ---------------------------------------------------------------------------

class TestPredictorErrors:
    def test_missing_model_raises_file_not_found(self, tmp_path):
        fake_path = tmp_path / "nonexistent.joblib"
        with pytest.raises(FileNotFoundError, match="Baseline model not found"):
            BaselinePredictor(model_path=fake_path)

    @pytestmark_needs_model
    def test_empty_string_raises_value_error(self, predictor):
        with pytest.raises(ValueError, match="non-empty string"):
            predictor.predict("")

    @pytestmark_needs_model
    def test_whitespace_only_raises_value_error(self, predictor):
        with pytest.raises(ValueError, match="non-empty string"):
            predictor.predict("   ")


# ---------------------------------------------------------------------------
# 9. TestRealModelInference -- end-to-end on known examples
# ---------------------------------------------------------------------------

class TestRealModelInference:
    """
    These tests use specific, semantically clear examples and assert on the
    DIRECTION of the prediction (SIF vs Non-SIF), not exact probabilities,
    so they are robust to minor model version differences.
    """

    SIF_EXAMPLES = [
        "Worker entered confined space without gas test or attendant.",
        "Cutting operation in tank farm without hot work permit. Gas detected.",
        "Workers found below crane load. No exclusion zone established.",
        "Worker on scaffold at 6 metres without harness. Guardrail missing.",
        "Equipment energized during maintenance. Lockout tagout not applied.",
    ]

    NON_SIF_EXAMPLES = [
        "Routine safety meeting conducted. All workers attended. No incidents.",
        "Monthly fire extinguisher inspection completed. All units serviceable.",
        "New staff safety orientation held. Acknowledgement forms signed.",
        "Water quality test results satisfactory. No anomalies found.",
    ]

    @pytestmark_needs_model
    @pytest.mark.parametrize("text", SIF_EXAMPLES)
    def test_sif_example_predicts_positive(self, predictor, text):
        result = predictor.predict(text)
        assert result["sif_prediction"] == 1, (
            f"Expected SIF=1 for: '{text}'\n"
            f"Got prediction={result['sif_prediction']}, P(SIF=1)={result['sif_probability']}"
        )

    @pytestmark_needs_model
    @pytest.mark.parametrize("text", NON_SIF_EXAMPLES)
    def test_non_sif_example_predicts_negative(self, predictor, text):
        result = predictor.predict(text)
        assert result["sif_prediction"] == 0, (
            f"Expected SIF=0 for: '{text}'\n"
            f"Got prediction={result['sif_prediction']}, P(SIF=1)={result['sif_probability']}"
        )


# ---------------------------------------------------------------------------
# 10. TestConfidenceLabel
# ---------------------------------------------------------------------------

class TestConfidenceLabel:
    def test_very_low_label(self):
        assert _confidence_label(0.10) == "VERY_LOW"

    def test_low_label(self):
        assert _confidence_label(0.35) == "LOW"

    def test_medium_label(self):
        assert _confidence_label(0.65) == "MEDIUM"

    def test_high_label(self):
        assert _confidence_label(0.85) == "HIGH"

    def test_boundary_at_0_50(self):
        assert _confidence_label(0.50) == "MEDIUM"

    def test_boundary_at_0_30(self):
        assert _confidence_label(0.30) == "LOW"

    def test_boundary_at_0_80(self):
        assert _confidence_label(0.80) == "HIGH"


# ---------------------------------------------------------------------------
# 11. TestMetricsJsonFiles
# ---------------------------------------------------------------------------

class TestMetricsJsonFiles:
    """Verify that the saved JSON metric files are valid and well-structured."""

    _METRICS_DIR = _ROOT / "models" / "baseline"

    @pytest.mark.skipif(
        not (_ROOT / "models" / "baseline" / "test_metrics.json").exists(),
        reason="Metrics files not found -- run training first",
    )
    def test_test_metrics_json_is_valid(self):
        p = self._METRICS_DIR / "test_metrics.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in ("split", "n_samples", "metrics", "confusion_matrix"):
            assert key in data

    @pytest.mark.skipif(
        not (_ROOT / "models" / "baseline" / "baseline_report.json").exists(),
        reason="Baseline report not found -- run training first",
    )
    def test_baseline_report_has_all_sections(self):
        p = self._METRICS_DIR / "baseline_report.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in ("schema_version", "phase", "pipeline", "data",
                    "primary_metric", "train_metrics", "val_metrics",
                    "test_metrics", "top_features", "model_path"):
            assert key in data, f"Missing key in baseline_report.json: {key}"

    @pytest.mark.skipif(
        not (_ROOT / "models" / "baseline" / "baseline_report.json").exists(),
        reason="Baseline report not found -- run training first",
    )
    def test_primary_metric_is_f2(self):
        p = self._METRICS_DIR / "baseline_report.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["primary_metric"] == "f2_score"

    @pytest.mark.skipif(
        not (_ROOT / "models" / "baseline" / "test_metrics.json").exists(),
        reason="Metrics files not found -- run training first",
    )
    def test_test_f2_is_float_in_range(self):
        p = self._METRICS_DIR / "test_metrics.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        f2 = data["metrics"]["f2_score"]
        assert isinstance(f2, float)
        assert 0.0 <= f2 <= 1.0
