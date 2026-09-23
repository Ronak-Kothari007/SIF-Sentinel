"""
SIF Sentinel — Report routes.

POST /reports/test
    Accepts a raw safety report string and returns analysis from the
    deterministic rule engine (Phase 2).

    Phase 2 changes vs Phase 1:
      - The real SIFRuleEngine is now called for every submission.
      - rule_severity_score and triggered_rules are populated from the engine.
      - model_confidence is still a placeholder (DistilBERT connects in Phase 3).
      - pipeline_status changes from 'placeholder' to 'rules_only'.
      - priority_score is now a composite: 0.65 * rule_score + 0.35 * model_conf.

Design principle:
    The AnalysisResult response shape is unchanged — the frontend built against
    Phase 1 continues to work without any modifications.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.report import (
    AnalysisResult,
    PriorityBand,
    ReportTestRequest,
    ReportTestResponse,
    TriggeredRuleSchema,
)
from app.services.rule_engine import get_rule_engine, RuleEngineResult

router = APIRouter()


# ---------------------------------------------------------------------------
# Priority band derivation
# ---------------------------------------------------------------------------

# Weights for composite score (Phase 2: rule engine only, ML placeholder)
_W_RULE = 0.65   # weight for deterministic rule engine
_W_MODEL = 0.35  # weight for placeholder model confidence (Phase 3 will supply real value)

# Placeholder model confidence: low but non-zero so score reflects some uncertainty
_PLACEHOLDER_MODEL_CONF = 0.30


def _derive_priority_band(score: float) -> PriorityBand:
    """
    Convert a composite priority score to a PriorityBand.

    Bands (matching ARCHITECTURE.md):
        0.00 - 0.39 => LOW
        0.40 - 0.59 => MEDIUM
        0.60 - 0.79 => HIGH
        0.80 - 1.00 => CRITICAL
    """
    if score >= 0.80:
        return PriorityBand.critical
    elif score >= 0.60:
        return PriorityBand.high
    elif score >= 0.40:
        return PriorityBand.medium
    else:
        return PriorityBand.low


def _build_explanation(result: RuleEngineResult, word_count: int, score: float) -> str:
    """
    Build a human-readable explanation of the analysis result.

    In Phase 3, LIME token attributions will replace or supplement this.
    """
    if not result.matched_rules:
        return (
            f"No SIF precursor signals were detected by the rule engine in this "
            f"{word_count}-word report. Priority assigned as LOW. "
            f"Note: ML classification (Phase 3) may detect additional risks."
        )

    rule_names = ", ".join(r.rule_name for r in result.matched_rules)
    categories = ", ".join(result.triggered_categories)
    return (
        f"Rule engine detected {len(result.matched_rules)} SIF precursor rule(s): "
        f"{rule_names}. "
        f"Triggered categories: {categories}. "
        f"Overall rule severity: {result.overall_severity_label}. "
        f"Composite priority score: {score:.2f}. "
        f"ML confidence is a placeholder — DistilBERT will replace this in Phase 3."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/test",
    response_model=ReportTestResponse,
    summary="Test Report Submission (Phase 2 — Rule Engine Active)",
    description=(
        "Submit a safety report text and receive an analysis from the deterministic "
        "SIF rule engine. The ML classifier is not connected yet (Phase 3). "
        "Response shape is identical to the final pipeline output."
    ),
)
def test_report_submission(payload: ReportTestRequest) -> ReportTestResponse:
    """
    Accepts a safety report and runs the deterministic rule engine against it.

    **Phase 2 Status:**
    - Rule engine: **ACTIVE** (real deterministic matching against sif_rules.yaml)
    - ML classifier: **PLACEHOLDER** (DistilBERT connects in Phase 3)
    - Priority score: composite (65% rule engine + 35% placeholder model confidence)

    **Returns:**
    - triggered_rules: all SIF rules that fired, with evidence and explanations
    - sif_flag: True if any HIGH or CRITICAL rule was triggered
    - evidence_summary: concise summary of all matched signals
    """
    # Generate a temporary report ID (will come from DB in future phases)
    report_id = str(uuid.uuid4())

    # Count words for basic stats
    word_count = len(payload.report_text.split())

    # ── Stage 1: Run the deterministic rule engine ──────────────────────────
    engine = get_rule_engine()
    rule_result = engine.evaluate(payload.report_text)

    # ── Stage 2: Placeholder model confidence ──────────────────────────────
    # Phase 3 will call the DistilBERT classifier here.
    model_confidence = _PLACEHOLDER_MODEL_CONF

    # ── Stage 3: Composite priority score ──────────────────────────────────
    priority_score = round(
        _W_RULE * rule_result.rule_severity_score
        + _W_MODEL * model_confidence,
        4,
    )

    # If rule engine flagged a SIF precursor, ensure score is above LOW band
    if rule_result.sif_flag and priority_score < 0.40:
        priority_score = 0.40

    priority_band = _derive_priority_band(priority_score)

    # ── Stage 4: Build explanation ──────────────────────────────────────────
    explanation = _build_explanation(rule_result, word_count, priority_score)

    # ── Stage 5: Convert rule matches to API schema ─────────────────────────
    triggered_rules = [
        TriggeredRuleSchema(
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            category=r.category,
            severity=r.severity,
            severity_label=r.severity_label,
            triggered_signals=r.triggered_signals,
            explanation=r.explanation,
            reference=r.reference,
        )
        for r in rule_result.matched_rules
    ]

    analysis = AnalysisResult(
        sif_flag=rule_result.sif_flag,
        model_confidence=model_confidence,
        rule_severity_score=rule_result.rule_severity_score,
        priority_score=priority_score,
        priority_band=priority_band,
        triggered_rules=triggered_rules,
        triggered_categories=rule_result.triggered_categories,
        evidence_summary=rule_result.evidence_summary,
        explanation=explanation,
        pipeline_status="rules_only",
    )

    return ReportTestResponse(
        report_id=report_id,
        received_at=datetime.now(timezone.utc),
        report_type=payload.report_type,
        location=payload.location,
        word_count=word_count,
        analysis=analysis,
        pipeline_status="rules_only",
    )
