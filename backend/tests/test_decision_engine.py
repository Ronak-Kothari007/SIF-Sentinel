"""
SIF Sentinel — Unit Tests for Decision Engine (Phase 7)
=======================================================

Tests the composite decision engine combining:
  1. NLP classifier probability
  2. Extracted activity
  3. Extracted hazard
  4. Barrier/control status
  5. Deterministic safety rules
  6. Optional recurring-risk signal

Validates:
  - Target prompt example output schema and values
  - Transparent, configurable scoring mechanisms
  - Escalation policies for high-consequence precursors
  - HSE governance compliance (no accident prediction claims)
  - Edge cases and pre-computed input payloads
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from app.schemas.decision import DecisionInput, DecisionResult, PriorityLevel
from app.services.decision_engine import SIFDecisionEngine, decide_report


# ===========================================================================
# Target Prompt Example Tests
# ===========================================================================

class TestTargetPromptExample:
    """
    Validates:
    Input: “Maintenance started on energized equipment without verified isolation.”
    Required output fields:
      - report_id
      - sif_probability
      - priority (HIGH)
      - activity (Maintenance)
      - hazard (Electrical Energy)
      - barrier (Isolation)
      - triggered_rules
      - evidence
      - explanation
    """

    @pytest.fixture
    def target_text(self) -> str:
        return "Maintenance started on energized equipment without verified isolation."

    @pytest.fixture
    def engine(self) -> SIFDecisionEngine:
        return SIFDecisionEngine()

    def test_target_priority_is_high(self, engine, target_text):
        result = engine.evaluate(target_text)
        assert result.priority == PriorityLevel.HIGH
        assert result.priority.value == "HIGH"
        assert result.priority_score >= 0.70

    def test_target_entities_extracted(self, engine, target_text):
        result = engine.evaluate(target_text)
        assert result.activity == "Maintenance"
        assert result.hazard == "Electrical Energy"
        assert result.barrier == "Isolation"
        assert result.barrier_status == "Not Verified"
        assert result.equipment == "energized equipment"

    def test_target_rules_triggered(self, engine, target_text):
        result = engine.evaluate(target_text)
        assert len(result.triggered_rules) >= 1
        rule_categories = [r.category for r in result.triggered_rules]
        assert "Energy Isolation" in rule_categories

    def test_target_evidence_captured(self, engine, target_text):
        result = engine.evaluate(target_text)
        assert len(result.evidence) >= 1
        evidence_lower = [e.lower() for e in result.evidence]
        assert any("energized equipment" in e or "isolation" in e for e in evidence_lower)

    def test_target_explanation_content(self, engine, target_text):
        result = engine.evaluate(target_text)
        assert "HIGH" in result.explanation
        assert "Isolation" in result.explanation
        assert "Electrical Energy" in result.explanation
        # HSE Governance requirement: must state triage/review purpose, not accident prediction
        assert "does not predict accident" in result.explanation.lower()

    def test_target_json_serialisation(self, engine, target_text):
        result = engine.evaluate(target_text, report_id="SYN-TEST-001")
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # Check required fields
        for key in [
            "report_id",
            "sif_probability",
            "priority",
            "activity",
            "hazard",
            "barrier",
            "triggered_rules",
            "evidence",
            "explanation",
        ]:
            assert key in parsed, f"Missing required key: {key}"

        assert parsed["report_id"] == "SYN-TEST-001"
        assert parsed["priority"] == "HIGH"


# ===========================================================================
# Transparent Configurable Scoring Mechanism Tests
# ===========================================================================

class TestScoringMechanisms:
    @pytest.fixture
    def engine(self) -> SIFDecisionEngine:
        return SIFDecisionEngine()

    def test_higher_probability_increases_score(self, engine):
        inp_low = DecisionInput(
            report_text="Work in progress",
            sif_probability=0.20,
            activity="Maintenance",
            hazard="Slip / Trip / Fall",
            barrier="PPE",
            barrier_status="Present",
        )
        inp_high = DecisionInput(
            report_text="Work in progress",
            sif_probability=0.90,
            activity="Maintenance",
            hazard="Slip / Trip / Fall",
            barrier="PPE",
            barrier_status="Present",
        )

        res_low = engine.evaluate(inp_low)
        res_high = engine.evaluate(inp_high)

        assert res_high.priority_score > res_low.priority_score

    def test_barrier_status_penalty_ordering(self, engine):
        """Not Verified and Failed should produce higher priority score than Present."""
        inp_verified = DecisionInput(
            report_text="Work",
            sif_probability=0.50,
            hazard="Electrical Energy",
            barrier="Isolation",
            barrier_status="Present",
        )
        inp_unverified = DecisionInput(
            report_text="Work",
            sif_probability=0.50,
            hazard="Electrical Energy",
            barrier="Isolation",
            barrier_status="Not Verified",
        )

        res_verified = engine.evaluate(inp_verified)
        res_unverified = engine.evaluate(inp_unverified)

        assert res_unverified.priority_score > res_verified.priority_score

    def test_recurring_risk_signal_elevates_score(self, engine):
        inp_no_rec = DecisionInput(
            report_text="Routine piping check",
            sif_probability=0.40,
            activity="Inspection & Audit",
            hazard="Chemical Exposure",
            barrier="PPE",
            barrier_status="Absent",
            recurring_risk_signal=None,
        )
        inp_with_rec = DecisionInput(
            report_text="Routine piping check",
            sif_probability=0.40,
            activity="Inspection & Audit",
            hazard="Chemical Exposure",
            barrier="PPE",
            barrier_status="Absent",
            recurring_risk_signal=0.85,
        )

        res_no = engine.evaluate(inp_no_rec)
        res_with = engine.evaluate(inp_with_rec)

        assert res_with.priority_score > res_no.priority_score
        assert "recurring risk pattern" in res_with.explanation.lower()


# ===========================================================================
# Safety Escalation Policies Tests
# ===========================================================================

class TestEscalationPolicies:
    @pytest.fixture
    def engine(self) -> SIFDecisionEngine:
        return SIFDecisionEngine()

    def test_escalation_on_critical_rule(self, engine):
        """A text that triggers a CRITICAL rule (severity 4) must escalate to HIGH."""
        text = "LOTO not applied. Breaker was not locked before maintenance began on live circuit."
        res = engine.evaluate(text)
        assert res.priority == PriorityLevel.HIGH
        assert res.escalated is True
        assert "CRITICAL safety rule" in (res.escalation_reason or "")

    def test_escalation_on_critical_hazard_and_compromised_barrier(self, engine):
        """Critical hazard with Not Verified or Absent barrier must escalate to HIGH."""
        inp = DecisionInput(
            report_text="Inspection found issues",
            sif_probability=0.30,  # Low probability from model
            activity="Maintenance",
            hazard="Toxic Gas / H2S",
            barrier="Gas Testing",
            barrier_status="Absent",
        )
        res = engine.evaluate(inp)
        assert res.priority == PriorityLevel.HIGH
        assert res.escalated is True

    def test_benign_report_stays_low(self, engine):
        """Housekeeping or benign meeting report must remain LOW."""
        text = "Toolbox meeting was conducted at the start of shift. All workers signed attendance sheet."
        res = engine.evaluate(text)
        assert res.priority == PriorityLevel.LOW
        assert res.escalated is False


# ===========================================================================
# HSE Governance & Transparency Tests
# ===========================================================================

class TestHSEGovernance:
    @pytest.fixture
    def engine(self) -> SIFDecisionEngine:
        return SIFDecisionEngine()

    def test_no_accident_prediction_claims(self, engine):
        sample_texts = [
            "Maintenance started on energized equipment without verified isolation.",
            "Worker observed on scaffold at 6 metres without harness.",
            "Welding operation without hot work permit.",
            "Housekeeping completed.",
        ]
        for text in sample_texts:
            res = engine.evaluate(text)
            expl = res.explanation.lower()
            assert "will have an accident" not in expl
            assert "predicts an accident" not in expl
            assert "injury prediction" not in expl
            assert "does not predict accident" in expl

    def test_explanation_contains_drivers(self, engine):
        text = "Technician entered confined storage tank without completing gas test."
        res = engine.evaluate(text)
        assert "Key drivers:" in res.explanation
        assert "(1)" in res.explanation


# ===========================================================================
# Edge Cases & Helper API Tests
# ===========================================================================

class TestEdgeCasesAndHelpers:
    @pytest.fixture
    def engine(self) -> SIFDecisionEngine:
        return SIFDecisionEngine()

    def test_empty_string_evaluates_low(self, engine):
        res = engine.evaluate("")
        assert res.priority == PriorityLevel.LOW
        assert res.sif_probability == 0.0

    def test_whitespace_string_evaluates_low(self, engine):
        res = engine.evaluate("   \n\t  ")
        assert res.priority == PriorityLevel.LOW

    def test_precomputed_decision_input(self, engine):
        inp = DecisionInput(
            report_id="PRE-123",
            sif_probability=0.92,
            activity="Welding",
            hazard="Fire / Explosion",
            barrier="Fire Watch",
            barrier_status="Absent",
            recurring_risk_signal=0.50,
        )
        res = engine.evaluate(inp)
        assert res.report_id == "PRE-123"
        assert res.priority == PriorityLevel.HIGH
        assert res.activity == "Welding"
        assert res.barrier == "Fire Watch"

    def test_decide_report_convenience_function(self):
        d = decide_report("Maintenance started on energized equipment without verified isolation.")
        assert isinstance(d, dict)
        assert d["priority"] == "HIGH"
        assert d["activity"] == "Maintenance"
        assert d["barrier_status"] == "Not Verified"
