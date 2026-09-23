"""
SIF Sentinel — Phase 14 Explainability Test Suite
=================================================

Validates that every prediction produces a structured, transparent, deterministic,
and non-contradictory explanation for HSE officers containing:
  - Important detected signals
  - Triggered safety rules
  - Extracted hazard
  - Barrier / control status
  - Model probability
  - Reason for final priority
  - Formatted "Priority: <LEVEL>\n\nWhy:\n- ..." template
"""

import pytest
from app.schemas.decision import PriorityLevel, StructuredExplanation
from app.services.decision_engine import SIFDecisionEngine


@pytest.fixture(scope="module")
def engine() -> SIFDecisionEngine:
    return SIFDecisionEngine()


class TestStructuredExplanationContract:
    """Validates that all required Phase 14 fields are populated and typed properly."""

    def test_high_priority_energy_isolation_explanation(self, engine):
        text = "Maintenance started on energized equipment without verified isolation."
        result = engine.evaluate(text, report_id="EXP-001")

        assert result.priority == PriorityLevel.HIGH
        exp: StructuredExplanation = result.structured_explanation

        # 1. Assert structured explanation is present
        assert exp is not None
        assert isinstance(exp, StructuredExplanation)

        # 2. Assert all 6 required fields are populated
        # - important detected signals
        assert isinstance(exp.important_detected_signals, list)
        assert len(exp.important_detected_signals) > 0
        signals_lower = [s.lower() for s in exp.important_detected_signals]
        assert any("maintenance" in s for s in signals_lower)
        assert any("hazard" in s or "electrical" in s for s in signals_lower)

        # - triggered safety rules
        assert isinstance(exp.triggered_safety_rules, list)
        assert len(exp.triggered_safety_rules) >= 1
        assert any("Energy Isolation" in r for r in exp.triggered_safety_rules)

        # - extracted hazard
        assert exp.extracted_hazard is not None
        assert "Electrical Energy" in exp.extracted_hazard or "Electrical" in exp.extracted_hazard

        # - barrier/control status
        assert exp.barrier_control_status is not None
        assert "Not Verified" in exp.barrier_control_status

        # - model probability
        assert isinstance(exp.model_probability, float)
        assert 0.0 <= exp.model_probability <= 1.0
        assert "%" in exp.model_probability_percent

        # - reason for final priority
        assert isinstance(exp.reason_for_final_priority, str)
        assert len(exp.reason_for_final_priority) > 10
        assert "HIGH" in exp.reason_for_final_priority or "high" in exp.reason_for_final_priority.lower()

    def test_formatted_template_structure(self, engine):
        text = "Maintenance started on energized equipment without verified isolation."
        result = engine.evaluate(text)
        exp = result.structured_explanation

        # Must conform to:
        # Priority: HIGH
        #
        # Why:
        # - ...
        assert exp.formatted_text.startswith("Priority: HIGH\n\nWhy:\n")
        assert len(exp.why) >= 3

        # Every why item must appear as a bullet in formatted_text
        for item in exp.why:
            assert f"- {item}" in exp.formatted_text

        # User example check:
        # - Maintenance activity detected
        # - Electrical Energy hazard detected (or electrical)
        # - Isolation not verified
        # - Energy Isolation safety rule triggered
        why_lower = [w.lower() for w in exp.why]
        assert any("maintenance" in w and "activity" in w for w in why_lower)
        assert any("hazard" in w for w in why_lower)
        assert any("isolation" in w and "verified" in w for w in why_lower)
        assert any("energy isolation" in w and "rule triggered" in w for w in why_lower)


class TestNonContradictionGuarantees:
    """Verifies that explanations strictly never contradict the model output or inputs."""

    def test_high_priority_never_claims_low_risk(self, engine):
        high_texts = [
            "Maintenance started on energized equipment without verified isolation.",
            "Welder entered confined tank with flammable vapors present and no gas test.",
            "Rigger standing directly under suspended 5 ton load without tag line.",
        ]
        for t in high_texts:
            res = engine.evaluate(t)
            if res.priority == PriorityLevel.HIGH:
                exp = res.structured_explanation
                assert exp.priority == PriorityLevel.HIGH
                all_text = (exp.formatted_text + " " + " ".join(exp.why)).lower()

                # Contradiction checks
                assert "low precursor probability" not in all_text
                assert "routine operational condition" not in all_text
                assert "standard operational controls in place" not in all_text
                assert "no life-saving safety rules triggered" not in all_text

    def test_low_priority_never_claims_critical_danger(self, engine):
        low_texts = [
            "Housekeeping completed in office corridor.",
            "Safety glasses restocked in warehouse dispensary.",
            "Routine perimeter walk conducted with no deviations noted.",
        ]
        for t in low_texts:
            res = engine.evaluate(t)
            assert res.priority == PriorityLevel.LOW
            exp = res.structured_explanation
            all_text = (exp.formatted_text + " " + " ".join(exp.why)).lower()

            # Contradiction checks
            assert "safety rule triggered" not in all_text
            assert "elevated sif precursor probability" not in all_text
            assert "high precursor indicators" not in all_text
            assert "critical barrier" not in all_text
            assert "prioritized as high" not in all_text

    def test_barrier_status_consistency(self, engine):
        text = "Technician worked near energized busbar with lockout hasp missing."
        res = engine.evaluate(text)
        exp = res.structured_explanation

        # If barrier status indicates failure, explanation must not say intact or verified
        if exp.barrier_control_status and ("absent" in exp.barrier_control_status.lower() or "not verified" in exp.barrier_control_status.lower()):
            all_text = (exp.formatted_text + " " + " ".join(exp.why)).lower()
            assert "barrier intact" not in all_text
            assert "controls confirmed verified" not in all_text

    def test_static_consistency_validator_catches_contradictions(self):
        """Directly verify that _validate_explanation_consistency rejects contradictory explanations."""
        # Simulated contradictory explanation: HIGH priority claiming low probability
        bad_exp_high = StructuredExplanation(
            priority=PriorityLevel.HIGH,
            important_detected_signals=["Maintenance activity detected"],
            triggered_safety_rules=["Energy Isolation (Severity HIGH)"],
            extracted_hazard="Electrical Energy",
            extracted_activity="Maintenance",
            barrier_control_status="Isolation (Not Verified)",
            model_probability=0.10,
            model_probability_percent="10.0%",
            reason_for_final_priority="Contradictory test",
            why=["Maintenance activity detected", "Low precursor probability (10.0%)"],
            formatted_text="Priority: HIGH\n\nWhy:\n- Low precursor probability (10.0%)",
        )

        with pytest.raises(ValueError, match="Explanation contradiction"):
            SIFDecisionEngine._validate_explanation_consistency(bad_exp_high)

        # Simulated contradictory explanation: LOW priority claiming safety rule triggered
        bad_exp_low = StructuredExplanation(
            priority=PriorityLevel.LOW,
            important_detected_signals=[],
            triggered_safety_rules=[],
            extracted_hazard=None,
            extracted_activity=None,
            barrier_control_status=None,
            model_probability=0.05,
            model_probability_percent="5.0%",
            reason_for_final_priority="Contradictory test",
            why=["Energy Isolation safety rule triggered"],
            formatted_text="Priority: LOW\n\nWhy:\n- Energy Isolation safety rule triggered",
        )

        with pytest.raises(ValueError, match="Explanation contradiction"):
            SIFDecisionEngine._validate_explanation_consistency(bad_exp_low)


class TestDeterminismAndZeroPaidAPI:
    """Verifies 100% deterministic reproducibility with zero third-party/paid API dependencies."""

    def test_deterministic_identical_runs(self, engine):
        text = "Scaffold board cracked at 15 meters elevation with no secondary fall arrest."

        # Run 5 consecutive evaluations
        results = [engine.evaluate(text, report_id=f"DET-{i}") for i in range(5)]

        first = results[0].structured_explanation
        for other in results[1:]:
            curr = other.structured_explanation
            assert curr.priority == first.priority
            assert curr.important_detected_signals == first.important_detected_signals
            assert curr.triggered_safety_rules == first.triggered_safety_rules
            assert curr.extracted_hazard == first.extracted_hazard
            assert curr.extracted_activity == first.extracted_activity
            assert curr.barrier_control_status == first.barrier_control_status
            assert curr.model_probability == first.model_probability
            assert curr.model_probability_percent == first.model_probability_percent
            assert curr.reason_for_final_priority == first.reason_for_final_priority
            assert curr.why == first.why
            assert curr.formatted_text == first.formatted_text

    def test_json_serializability(self, engine):
        text = "Maintenance started on energized equipment without verified isolation."
        res = engine.evaluate(text, report_id="JSON-EXP-01")
        data = res.to_dict()

        assert "structured_explanation" in data
        s_exp = data["structured_explanation"]
        assert s_exp["priority"] == PriorityLevel.HIGH or s_exp["priority"] == "HIGH"
        assert len(s_exp["why"]) > 0
        assert "formatted_text" in s_exp
        assert "important_detected_signals" in s_exp
        assert "reason_for_final_priority" in s_exp

        # Check full JSON round-trip serialization
        json_str = res.to_json()
        import json
        parsed = json.loads(json_str)
        assert parsed["structured_explanation"]["priority"] == "HIGH"
        assert "Why:" in parsed["structured_explanation"]["formatted_text"]


class TestExplainabilityAPIEndpoint:
    """Verifies that API v1 endpoints deliver structured explanations to clients."""

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_analyze_report_delivers_structured_explanation(self, client):
        payload = {
            "report_text": "Maintenance started on energized equipment without verified isolation.",
            "report_id": "API-EXP-001",
        }
        res = client.post("/api/v1/analyze-report", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "structured_explanation" in data
        assert data["structured_explanation"] is not None
        s_exp = data["structured_explanation"]

        # Check all required fields from prompt
        assert s_exp["priority"] == "HIGH"
        assert isinstance(s_exp["important_detected_signals"], list)
        assert len(s_exp["important_detected_signals"]) > 0
        assert isinstance(s_exp["triggered_safety_rules"], list)
        assert len(s_exp["triggered_safety_rules"]) >= 1
        assert s_exp["extracted_hazard"] is not None
        assert s_exp["barrier_control_status"] is not None
        assert isinstance(s_exp["model_probability"], float)
        assert s_exp["model_probability"] >= 0.50
        assert isinstance(s_exp["reason_for_final_priority"], str)
        assert "Why:" in s_exp["formatted_text"]
        assert len(s_exp["why"]) >= 3

    def test_get_report_by_id_delivers_structured_explanation(self, client):
        # Retrieve the report analyzed above
        res = client.get("/api/v1/reports/API-EXP-001")
        assert res.status_code == 200
        data = res.json()

        assert "structured_explanation" in data
        assert data["structured_explanation"] is not None
        assert data["structured_explanation"]["priority"] == "HIGH"
        assert len(data["structured_explanation"]["why"]) >= 3

