"""
SIF Sentinel — Decision Engine (Phase 7)
========================================

The central synthesis engine that combines:
  1. NLP classifier probability (DistilBERT / Baseline)
  2. Extracted activity
  3. Extracted hazard
  4. Barrier/control status (e.g. Not Verified, Absent, Failed, Present)
  5. Deterministic safety rules
  6. Optional recurring-risk signal

Produces a structured, transparent HSE prioritization result:
  - report_id
  - sif_probability
  - priority (LOW / MEDIUM / HIGH)
  - activity
  - hazard
  - barrier
  - triggered_rules
  - evidence
  - explanation

Safety Governance:
  Scores are prioritization rankings for HSE incident review triage.
  They do NOT forecast, predict, or guarantee accident occurrences.
"""

from __future__ import annotations

import sys
import uuid
import yaml
from pathlib import Path
from typing import Any, Optional

from app.schemas.decision import (
    DecisionInput,
    DecisionResult,
    FactorScores,
    PriorityLevel,
    StructuredExplanation,
    TriggeredRuleSummary,
)
from app.schemas.context import SafetyContext
from app.services.extractor import HybridSafetyExtractor
from app.services.rule_engine import SIFRuleEngine


# ---------------------------------------------------------------------------
# Default paths
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "rules" / "decision_config.yaml"
DISTILBERT_CHECKPOINT = _REPO_ROOT / "models" / "distilbert" / "best_checkpoint"
BASELINE_CHECKPOINT = _REPO_ROOT / "models" / "baseline" / "baseline_pipeline.joblib"


class SIFDecisionEngine:
    """
    SIF Sentinel Composite Decision Engine.
    Coordinates the ML classifier, deterministic rule engine, entity extractor,
    and configurable multi-factor prioritization formula.
    """

    def __init__(
        self,
        config_path: Optional[Path | str] = None,
        rule_engine: Optional[SIFRuleEngine] = None,
        extractor: Optional[HybridSafetyExtractor] = None,
    ):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._load_config()

        # Modular dependencies
        self.rule_engine = rule_engine or SIFRuleEngine()
        self.extractor = extractor or HybridSafetyExtractor()
        self._classifier = None

    def _load_config(self) -> None:
        """Load scoring weights, multipliers, and policies from YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Decision configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        self.weights = cfg.get("weights", {})
        self.hazard_multipliers = cfg.get("hazard_multipliers", {})
        self.activity_multipliers = cfg.get("activity_multipliers", {})
        self.barrier_status_scores = cfg.get("barrier_status_scores", {})
        self.thresholds = cfg.get("priority_thresholds", {"HIGH": 0.65, "MEDIUM": 0.35, "LOW": 0.0})
        self.escalation_policies = cfg.get("escalation_policies", {})
        self.governance_notice = cfg.get("governance_notice", "").strip()

    def _get_classifier(self) -> Any:
        """Lazy load best available classifier (DistilBERT -> Baseline -> None)."""
        if self._classifier is not None:
            return self._classifier

        # Try DistilBERT first
        if DISTILBERT_CHECKPOINT.exists():
            try:
                from models.predict_distilbert import DistilBERTPredictor
                self._classifier = DistilBERTPredictor(str(DISTILBERT_CHECKPOINT))
                return self._classifier
            except Exception:
                pass

        # Try Baseline TF-IDF
        if BASELINE_CHECKPOINT.exists():
            try:
                from models.predict_baseline import BaselinePredictor
                self._classifier = BaselinePredictor(str(BASELINE_CHECKPOINT))
                return self._classifier
            except Exception:
                pass

        return None

    def evaluate(
        self,
        input_data: DecisionInput | str,
        report_id: Optional[str] = None,
        recurring_risk_signal: Optional[float] = None,
    ) -> DecisionResult:
        """
        Evaluate a safety report and produce an authoritative DecisionResult.

        Args:
            input_data: Either a raw report text string or a structured DecisionInput.
            report_id: Optional unique report identifier (generated if omitted).
            recurring_risk_signal: Optional past recurrence score (0.0–1.0).

        Returns:
            DecisionResult matching the Phase 7 specification.
        """
        # 1. Normalize input parameters
        if isinstance(input_data, str):
            rep_text = input_data.strip()
            rep_id = report_id or f"REP-{uuid.uuid4().hex[:8].upper()}"
            sif_prob = None
            extracted_act = None
            extracted_haz = None
            extracted_bar = None
            extracted_status = None
            extracted_loc = None
            extracted_eq = None
            recurrence = recurring_risk_signal
        else:
            rep_text = (input_data.report_text or "").strip()
            rep_id = input_data.report_id or report_id or f"REP-{uuid.uuid4().hex[:8].upper()}"
            sif_prob = input_data.sif_probability
            extracted_act = input_data.activity
            extracted_haz = input_data.hazard
            extracted_bar = input_data.barrier
            extracted_status = input_data.barrier_status
            extracted_loc = input_data.location
            extracted_eq = input_data.equipment
            recurrence = input_data.recurring_risk_signal if input_data.recurring_risk_signal is not None else recurring_risk_signal

        ctx: Optional[SafetyContext] = None
        # 2. Extract context if not provided
        if not (extracted_act and extracted_haz and extracted_bar and extracted_status):
            if rep_text:
                ctx = self.extractor.extract(rep_text)
                extracted_act = extracted_act or ctx.activity
                extracted_haz = extracted_haz or ctx.hazard
                extracted_bar = extracted_bar or ctx.barrier
                extracted_status = extracted_status or ctx.barrier_status
                extracted_loc = extracted_loc or ctx.location
                extracted_eq = extracted_eq or ctx.equipment

        # 3. Evaluate deterministic safety rules
        rule_matches = []
        rule_evidence = []
        rule_severity_max = 0
        if rep_text:
            rule_result = self.rule_engine.evaluate(rep_text)
            rule_severity_max = rule_result.overall_severity
            for m in rule_result.matched_rules:
                rule_evidence.extend(m.triggered_signals)
                rule_matches.append(
                    TriggeredRuleSummary(
                        rule_id=m.rule_id,
                        rule_name=m.rule_name,
                        category=m.category,
                        severity=m.severity,
                        severity_label=m.severity_label,
                        explanation=m.explanation,
                    )
                )

        # 4. Determine SIF precursor probability from classifier if not supplied
        if sif_prob is None:
            if rep_text:
                clf = self._get_classifier()
                if clf is not None:
                    pred = clf.predict(rep_text)
                    sif_prob = float(pred.get("sif_probability", pred.get("probability", 0.50)))
                else:
                    # Fallback: estimate from rule severity and hazard presence
                    sif_prob = min(0.95, (rule_severity_max / 4.0) * 0.8 + 0.15) if rule_severity_max > 0 else 0.10
            else:
                sif_prob = 0.0

        # 5. Calculate transparent factor scores and composite priority score
        factor_scores, priority_score = self._calculate_scores(
            sif_probability=sif_prob,
            rule_severity=rule_severity_max,
            hazard=extracted_haz,
            activity=extracted_act,
            barrier_status=extracted_status,
            recurrence_signal=recurrence,
        )

        # 6. Apply safety escalation policies
        priority_level, final_score, escalated, escalation_reason = self._determine_priority(
            composite_score=priority_score,
            rule_severity=rule_severity_max,
            hazard=extracted_haz,
            barrier_status=extracted_status,
            sif_probability=sif_prob,
        )

        # 7. Generate transparent, itemized explanation for HSE users
        # Deduplicate evidence phrases from rules and entity mentions
        entity_evidence = [e.text for e in getattr(ctx, "entities", []) if getattr(e, "confidence", 0) >= 0.85] if rep_text else []
        deduped_evidence = list(dict.fromkeys(rule_evidence + entity_evidence))

        explanation, structured_exp = self._generate_explanation(
            priority=priority_level,
            sif_prob=sif_prob,
            activity=extracted_act,
            hazard=extracted_haz,
            barrier=extracted_bar,
            barrier_status=extracted_status,
            triggered_rules=rule_matches,
            evidence=deduped_evidence,
            escalated=escalated,
            escalation_reason=escalation_reason,
            recurrence=recurrence,
        )

        return DecisionResult(
            report_id=rep_id,
            report_text=rep_text,
            sif_probability=round(sif_prob, 4),
            priority=priority_level,
            activity=extracted_act,
            hazard=extracted_haz,
            barrier=extracted_bar,
            triggered_rules=rule_matches,
            evidence=deduped_evidence,
            explanation=explanation,
            priority_score=round(final_score, 4),
            barrier_status=extracted_status,
            location=extracted_loc,
            equipment=extracted_eq,
            factor_scores=factor_scores,
            escalated=escalated,
            escalation_reason=escalation_reason,
            governance_notice=self.governance_notice,
            structured_explanation=structured_exp,
        )

    def _calculate_scores(
        self,
        sif_probability: float,
        rule_severity: int,
        hazard: Optional[str],
        activity: Optional[str],
        barrier_status: Optional[str],
        recurrence_signal: Optional[float],
    ) -> tuple[FactorScores, float]:
        """Compute normalized individual factor scores and weighted composite score."""
        # 1. Model score
        f_model = max(0.0, min(1.0, float(sif_probability)))

        # 2. Rule severity score (normalized 1-4 to 0.0-1.0)
        f_rule = max(0.0, min(1.0, rule_severity / 4.0))

        # 3. Barrier compromise score
        f_barrier = self.barrier_status_scores.get(
            barrier_status or "default", self.barrier_status_scores.get("default", 0.40)
        )

        # 4. Critical hazard multiplier
        f_hazard = self.hazard_multipliers.get(
            hazard or "default", self.hazard_multipliers.get("default", 0.40)
        )

        # 5. Critical activity multiplier
        f_activity = self.activity_multipliers.get(
            activity or "default", self.activity_multipliers.get("default", 0.40)
        )

        # 6. Recurrence factor
        f_recurrence = max(0.0, min(1.0, float(recurrence_signal))) if recurrence_signal is not None else None

        factors = FactorScores(
            model_probability=round(f_model, 4),
            rule_severity=round(f_rule, 4),
            barrier_failure=round(f_barrier, 4),
            critical_hazard=round(f_hazard, 4),
            critical_activity=round(f_activity, 4),
            recurring_pattern=round(f_recurrence, 4) if f_recurrence is not None else None,
        )

        # Weighted calculation
        w = self.weights.copy()
        if f_recurrence is None:
            # Renormalize without recurrence
            rec_w = w.pop("recurring_pattern", 0.10)
            total_remaining = sum(w.values())
            if total_remaining > 0:
                w = {k: v / total_remaining for k, v in w.items()}
            composite = (
                w.get("model_probability", 0.33) * f_model
                + w.get("rule_severity", 0.28) * f_rule
                + w.get("barrier_failure", 0.22) * f_barrier
                + w.get("critical_hazard", 0.11) * f_hazard
                + w.get("critical_activity", 0.06) * f_activity
            )
        else:
            composite = (
                w.get("model_probability", 0.30) * f_model
                + w.get("rule_severity", 0.25) * f_rule
                + w.get("barrier_failure", 0.20) * f_barrier
                + w.get("critical_hazard", 0.15) * f_hazard
                + w.get("critical_activity", 0.10) * f_activity
                + w.get("recurring_pattern", 0.10) * f_recurrence
            )

        composite = max(0.0, min(1.0, composite))
        return factors, composite

    def _determine_priority(
        self,
        composite_score: float,
        rule_severity: int,
        hazard: Optional[str],
        barrier_status: Optional[str],
        sif_probability: float,
    ) -> tuple[PriorityLevel, float, bool, Optional[str]]:
        """Apply thresholds and safety escalation policies."""
        escalated = False
        escalation_reason = None
        score = composite_score

        # Check Escalation Policy 1: Critical Rule Fired
        if self.escalation_policies.get("escalate_on_critical_rule", True) and rule_severity >= 4:
            escalated = True
            escalation_reason = "Elevated to HIGH: CRITICAL safety rule (severity 4/4) triggered."
            score = max(score, self.thresholds.get("HIGH", 0.65) + 0.05)
            return PriorityLevel.HIGH, score, escalated, escalation_reason

        # Check Escalation Policy 2: High Consequence Hazard with Failed/Unverified Barrier
        haz_mult = self.hazard_multipliers.get(hazard or "", 0.0)
        is_barrier_critical = barrier_status in ["Not Verified", "Failed", "Absent"]
        if (
            self.escalation_policies.get("escalate_on_critical_barrier_failure", True)
            and haz_mult >= 0.95
            and is_barrier_critical
        ):
            escalated = True
            escalation_reason = (
                f"Elevated to HIGH: Critical hazard ({hazard}) detected with compromised barrier ({barrier_status})."
            )
            score = max(score, self.thresholds.get("HIGH", 0.65) + 0.05)
            return PriorityLevel.HIGH, score, escalated, escalation_reason

        # Threshold mapping
        high_thresh = self.thresholds.get("HIGH", 0.65)
        med_thresh = self.thresholds.get("MEDIUM", 0.35)

        if score >= high_thresh or sif_probability >= self.escalation_policies.get("model_high_threshold", 0.85):
            return PriorityLevel.HIGH, score, False, None
        elif score >= med_thresh or sif_probability >= self.escalation_policies.get("model_medium_threshold", 0.60):
            return PriorityLevel.MEDIUM, score, False, None
        else:
            return PriorityLevel.LOW, score, False, None

    def _generate_explanation(
        self,
        priority: PriorityLevel,
        sif_prob: float,
        activity: Optional[str],
        hazard: Optional[str],
        barrier: Optional[str],
        barrier_status: Optional[str],
        triggered_rules: list[TriggeredRuleSummary],
        evidence: list[str],
        escalated: bool,
        escalation_reason: Optional[str],
        recurrence: Optional[float],
    ) -> tuple[str, StructuredExplanation]:
        """
        Construct a transparent, itemized, and non-contradictory explanation (Phase 14).
        Produces both a structured object (StructuredExplanation) and a formatted string.
        """
        prob_pct = f"{sif_prob * 100:.1f}%"

        # -------------------------------------------------------------------
        # 1. Important Detected Signals
        # -------------------------------------------------------------------
        signals: list[str] = []
        if activity:
            signals.append(f"{activity} activity detected")
        if hazard:
            signals.append(f"{hazard} hazard detected")
        if barrier and barrier_status:
            signals.append(f"{barrier} status: {barrier_status}")
        elif barrier_status:
            signals.append(f"Barrier status: {barrier_status}")
        elif barrier:
            signals.append(f"Barrier identified: {barrier}")

        if sif_prob >= 0.70:
            signals.append(f"Elevated ML precursor probability ({prob_pct})")
        elif sif_prob >= 0.40:
            signals.append(f"Moderate ML precursor probability ({prob_pct})")
        else:
            signals.append(f"Low ML precursor probability ({prob_pct})")

        if recurrence is not None and recurrence >= 0.50:
            signals.append(f"Recurring risk pattern detected (similarity score: {recurrence:.2f})")

        if evidence:
            unique_evidence = list(dict.fromkeys(evidence))[:3]
            signals.append(f"Physical evidence indicators: '{', '.join(unique_evidence)}'")

        # -------------------------------------------------------------------
        # 2. Triggered Safety Rules
        # -------------------------------------------------------------------
        rules_list: list[str] = [
            f"{r.rule_name} (Severity {r.severity_label})"
            for r in triggered_rules
        ]

        # -------------------------------------------------------------------
        # 3. Barrier / Control Status representation
        # -------------------------------------------------------------------
        if barrier and barrier_status:
            barrier_ctrl_status = f"{barrier} ({barrier_status})"
        elif barrier_status:
            barrier_ctrl_status = barrier_status
        elif barrier:
            barrier_ctrl_status = f"{barrier} (Status Unspecified)"
        else:
            barrier_ctrl_status = None

        # -------------------------------------------------------------------
        # 4. Reason for Final Priority
        # -------------------------------------------------------------------
        if escalated and escalation_reason:
            reason_for_priority = escalation_reason
        elif priority == PriorityLevel.HIGH:
            if triggered_rules and sif_prob >= 0.65:
                reason_for_priority = (
                    f"Prioritized as HIGH due to elevated precursor probability ({prob_pct}) "
                    f"combined with life-saving safety rule triggers."
                )
            elif triggered_rules:
                reason_for_priority = (
                    "Prioritized as HIGH due to deterministic life-saving safety rule triggers."
                )
            elif barrier_status in ["Not Verified", "Failed", "Absent"]:
                reason_for_priority = (
                    f"Prioritized as HIGH due to compromised critical barrier ({barrier_status}) "
                    f"under high-consequence operating conditions."
                )
            else:
                reason_for_priority = (
                    f"Prioritized as HIGH based on strong ML precursor indicators ({prob_pct})."
                )
        elif priority == PriorityLevel.MEDIUM:
            if triggered_rules:
                reason_for_priority = (
                    "Prioritized as MEDIUM due to advisory safety rule triggers requiring supervisor review."
                )
            elif sif_prob >= 0.40:
                reason_for_priority = (
                    f"Prioritized as MEDIUM due to moderate precursor probability ({prob_pct})."
                )
            elif hazard:
                reason_for_priority = (
                    f"Prioritized as MEDIUM due to identified hazard ({hazard}) without critical barrier failure."
                )
            else:
                reason_for_priority = (
                    "Prioritized as MEDIUM for scheduled HSE review and supervisor follow-up."
                )
        else:
            reason_for_priority = (
                f"Classified as LOW priority for routine logging: no critical safety rules triggered "
                f"and low precursor probability ({prob_pct})."
            )

        # -------------------------------------------------------------------
        # 5. Itemized "Why" Bullets (Strict Non-Contradiction)
        # -------------------------------------------------------------------
        why: list[str] = []

        if priority == PriorityLevel.HIGH:
            if activity:
                why.append(f"{activity} activity detected")
            if hazard:
                why.append(f"{hazard} hazard detected")
            if barrier and barrier_status:
                b_stat = barrier_status.lower()
                why.append(f"{barrier} {b_stat}")
            elif barrier_status:
                why.append(f"Barrier {barrier_status.lower()}")
            elif barrier:
                why.append(f"{barrier} barrier identified")

            if triggered_rules:
                for r in triggered_rules:
                    why.append(f"{r.rule_name} safety rule triggered")

            if sif_prob >= 0.70:
                why.append(f"Elevated SIF precursor probability ({prob_pct})")
            if recurrence is not None and recurrence >= 0.50:
                why.append(f"Recurring risk pattern detected (similarity: {recurrence:.2f})")
            if escalated and escalation_reason and not any(r.rule_name in escalation_reason for r in triggered_rules):
                why.append(f"Safety override applied: {escalation_reason}")

            if not why:
                why.append(f"High precursor indicators detected ({prob_pct})")

        elif priority == PriorityLevel.MEDIUM:
            if activity:
                why.append(f"{activity} activity detected")
            if hazard:
                why.append(f"{hazard} hazard detected")
            if barrier and barrier_status:
                why.append(f"{barrier} status: {barrier_status}")
            elif barrier:
                why.append(f"{barrier} barrier observed")

            if triggered_rules:
                for r in triggered_rules:
                    why.append(f"{r.rule_name} rule triggered")
            else:
                why.append("No critical life-saving rule violations")

            if sif_prob >= 0.40:
                why.append(f"Moderate precursor probability ({prob_pct})")
            if recurrence is not None and recurrence >= 0.50:
                why.append(f"Elevated recurrence pattern observed ({recurrence:.2f})")

            if not why:
                why.append("Advisory safety indicators require supervisor verification")

        else:  # LOW priority
            if activity:
                why.append(f"{activity} activity observed under standard conditions")
            if hazard:
                why.append(f"Routine operational condition ({hazard})")
            if barrier and barrier_status and barrier_status.lower() in ["verified", "intact", "present"]:
                why.append(f"{barrier} barrier confirmed {barrier_status.lower()}")
            else:
                why.append("Standard operational controls in place")

            why.append("No life-saving safety rules triggered")
            why.append(f"Low precursor probability ({prob_pct})")

        # -------------------------------------------------------------------
        # 6. Format the Template
        # -------------------------------------------------------------------
        why_block = "\n".join(f"- {w}" for w in why)
        formatted_template = f"Priority: {priority.value}\n\nWhy:\n{why_block}"

        # -------------------------------------------------------------------
        # 7. Legacy Key Drivers & Governance (Preserves Backward Compatibility)
        # -------------------------------------------------------------------
        drivers = []
        if sif_prob >= 0.70:
            drivers.append(f"Model identified strong SIF precursor signals (probability: {prob_pct})")
        elif sif_prob >= 0.40:
            drivers.append(f"Model identified moderate precursor indicators (probability: {prob_pct})")
        else:
            drivers.append(f"Model precursor probability is low ({prob_pct})")

        if triggered_rules:
            crit_rules = [r for r in triggered_rules if r.severity >= 3]
            rule_names = ", ".join(r.rule_name for r in triggered_rules[:2])
            if crit_rules:
                drivers.append(f"Deterministic safety rules triggered: {rule_names} (severity: {crit_rules[0].severity_label})")
            else:
                drivers.append(f"Safety rules matched: {rule_names}")
        else:
            drivers.append("No deterministic life-saving rules were triggered")

        if barrier and barrier_status:
            haz_str = f" involving {hazard}" if hazard else ""
            act_str = f" during {activity}" if activity else ""
            drivers.append(f"Safety barrier issue: {barrier} is {barrier_status}{haz_str}{act_str}")
        elif hazard:
            drivers.append(f"Primary hazard observed: {hazard}")

        if recurrence is not None and recurrence >= 0.50:
            drivers.append(f"Elevated recurring risk pattern detected (similarity score: {recurrence:.2f})")

        if escalated and escalation_reason:
            drivers.append(f"Safety policy override: {escalation_reason}")

        numbered_drivers = "; ".join(f"({i+1}) {d}" for i, d in enumerate(drivers))

        full_explanation_parts = [
            formatted_template,
            f"Key drivers: {numbered_drivers}.",
        ]
        if evidence:
            unique_evidence = list(dict.fromkeys(evidence))[:4]
            full_explanation_parts.append(f"Trigger evidence: '{', '.join(unique_evidence)}'.")
        full_explanation_parts.append(
            "Note: This score prioritizes HSE review attention and does not predict accident occurrence."
        )

        full_explanation = " ".join(full_explanation_parts)

        structured_obj = StructuredExplanation(
            priority=priority,
            important_detected_signals=signals,
            triggered_safety_rules=rules_list,
            extracted_hazard=hazard,
            extracted_activity=activity,
            barrier_control_status=barrier_ctrl_status,
            model_probability=round(sif_prob, 4),
            model_probability_percent=prob_pct,
            reason_for_final_priority=reason_for_priority,
            why=why,
            formatted_text=formatted_template,
        )

        self._validate_explanation_consistency(structured_obj)

        return full_explanation, structured_obj

    @staticmethod
    def _validate_explanation_consistency(explanation: StructuredExplanation) -> None:
        """
        Validates that the structured explanation does not contradict model outputs or inputs.
        Guarantees deterministic explainability integrity.
        """
        priority = explanation.priority
        bullets_text = " ".join(explanation.why).lower()

        if priority == PriorityLevel.HIGH:
            # High priority must not state routine or low risk
            for contradiction in [
                "low precursor probability",
                "routine operational condition",
                "standard operational controls in place",
                "no life-saving safety rules triggered",
            ]:
                if contradiction in bullets_text:
                    raise ValueError(
                        f"Explanation contradiction: HIGH priority contains contradictory statement '{contradiction}'"
                    )

        elif priority == PriorityLevel.LOW:
            # Low priority must not state high danger or life-saving rule triggers
            for contradiction in [
                "safety rule triggered",
                "elevated sif precursor probability",
                "high precursor indicators",
                "critical barrier",
            ]:
                if contradiction in bullets_text:
                    raise ValueError(
                        f"Explanation contradiction: LOW priority contains contradictory statement '{contradiction}'"
                    )

        # Rule check: cannot claim safety rule triggered in why if no rules are recorded
        if not explanation.triggered_safety_rules:
            if any("safety rule triggered" in b.lower() for b in explanation.why):
                raise ValueError(
                    "Explanation contradiction: 'safety rule triggered' present in why bullets when no rules fired."
                )


# ---------------------------------------------------------------------------
# Convenience Module API
# ---------------------------------------------------------------------------
def decide_report(
    text: str,
    report_id: Optional[str] = None,
    recurring_risk_signal: Optional[float] = None,
    config_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """
    Convenience function: evaluate a report and return dictionary.
    """
    engine = SIFDecisionEngine(config_path=config_path)
    result = engine.evaluate(text, report_id=report_id, recurring_risk_signal=recurring_risk_signal)
    return result.to_dict()
