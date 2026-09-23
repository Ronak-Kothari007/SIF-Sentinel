"""
SIF Sentinel — Model Inference Test Suite (Phase 15)
===================================================

Comprehensive tests for ML model inference layer:
  - DistilBERT fine-tuned transformer inference
  - Baseline TF-IDF + Logistic Regression fallback inference
  - Prediction schema & contract validation
  - Probability bounds [0.0, 1.0] and calibration
  - Edge cases (empty string, long strings, punctuation/unicode)
  - Inference latency validation (< 500ms)
"""

import sys
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.predict_distilbert import DistilBERTPredictor, _confidence_label
from models.predict_baseline import BaselinePredictor
from app.services.decision_engine import SIFDecisionEngine


DISTILBERT_CHECKPOINT = REPO_ROOT / "models" / "distilbert" / "best_checkpoint"
BASELINE_CHECKPOINT = REPO_ROOT / "models" / "baseline" / "baseline_pipeline.joblib"


@pytest.fixture(scope="module")
def distilbert_predictor():
    if not DISTILBERT_CHECKPOINT.exists():
        pytest.skip(f"DistilBERT checkpoint not found at {DISTILBERT_CHECKPOINT}")
    return DistilBERTPredictor(checkpoint_dir=DISTILBERT_CHECKPOINT)


@pytest.fixture(scope="module")
def baseline_predictor():
    if not BASELINE_CHECKPOINT.exists():
        pytest.skip(f"Baseline checkpoint not found at {BASELINE_CHECKPOINT}")
    return BaselinePredictor(model_path=BASELINE_CHECKPOINT)


# ===========================================================================
# 1. DistilBERT Inference Tests
# ===========================================================================

class TestDistilBERTInference:
    """Verifies transformer model inference behavior and contract."""

    def test_distilbert_predicts_sif_precursor(self, distilbert_predictor):
        text = "Maintenance started on energized electrical panel without lockout tagout."
        result = distilbert_predictor.predict(text)

        assert "sif_prediction" in result
        assert "sif_probability" in result
        assert "confidence_label" in result
        assert isinstance(result["sif_probability"], float)
        assert 0.0 <= result["sif_probability"] <= 1.0
        assert result["sif_probability"] >= 0.40  # Precursor signal detected

    def test_distilbert_predicts_non_sif(self, distilbert_predictor):
        text = "Scheduled toolbox talk completed in the office conference room."
        result = distilbert_predictor.predict(text)

        assert isinstance(result["sif_probability"], float)
        assert 0.0 <= result["sif_probability"] <= 1.0
        assert result["sif_probability"] <= 0.45  # Routine safe event

    def test_distilbert_latency(self, distilbert_predictor):
        text = "Worker entered confined tank without air monitoring or entry permit."
        # Warmup
        distilbert_predictor.predict(text)

        start = time.perf_counter()
        result = distilbert_predictor.predict(text)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert elapsed_ms < 500.0, f"Inference took {elapsed_ms:.1f}ms, exceeding 500ms limit"
        assert result["sif_prediction"] in (0, 1)

    def test_distilbert_edge_case_empty(self, distilbert_predictor):
        with pytest.raises(ValueError, match="non-empty string"):
            distilbert_predictor.predict("")

    def test_distilbert_edge_case_long_text(self, distilbert_predictor):
        long_text = "Heavy lifting operation with crane near power line. " * 50
        result = distilbert_predictor.predict(long_text)
        assert 0.0 <= result["sif_probability"] <= 1.0

    def test_distilbert_edge_case_unicode_symbols(self, distilbert_predictor):
        text = "Scaffolding at 20m height ⚠️ Fall arrest harness missing! [ZONE-4] & 35°C."
        result = distilbert_predictor.predict(text)
        assert 0.0 <= result["sif_probability"] <= 1.0


# ===========================================================================
# 2. Baseline Model Fallback Tests
# ===========================================================================

class TestBaselineInference:
    """Verifies baseline TF-IDF + Logistic Regression inference pipeline."""

    def test_baseline_predicts_precursor(self, baseline_predictor):
        text = "Worker exposed to energized bare electrical wires during pump repair."
        result = baseline_predictor.predict(text)

        assert "sif_prediction" in result
        assert "sif_probability" in result
        assert "confidence_label" in result
        assert 0.0 <= result["sif_probability"] <= 1.0

    def test_baseline_empty_string(self, baseline_predictor):
        with pytest.raises(ValueError, match="non-empty string"):
            baseline_predictor.predict("")



# ===========================================================================
# 3. Decision Engine Integration with Model Inference
# ===========================================================================

class TestDecisionEngineModelIntegration:
    """Verifies that the decision engine integrates model inference seamlessly."""

    def test_engine_uses_model_for_sif_probability(self):
        engine = SIFDecisionEngine()
        result = engine.evaluate(
            "Technician bypassed interlock on rotating industrial turbine.",
            report_id="MOD-INT-001"
        )
        assert result.sif_probability > 0.0
        assert result.factor_scores.model_probability == pytest.approx(result.sif_probability, abs=1e-3)

    def test_confidence_label_helper(self):
        assert _confidence_label(0.95) == "HIGH"
        assert _confidence_label(0.65) == "MEDIUM"
        assert _confidence_label(0.35) == "LOW"
        assert _confidence_label(0.15) == "VERY_LOW"
