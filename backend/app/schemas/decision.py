"""
SIF Sentinel — Pydantic Schemas for Decision Engine (Phase 7)
=============================================================

Defines the contract for the composite decision engine that synthesizes
classifier probability, extracted entities, barrier status, deterministic rules,
and recurring risk into a transparent HSE review prioritization score.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TriggeredRuleSummary(BaseModel):
    """Compact summary of a triggered deterministic safety rule."""

    rule_id: str = Field(description="Rule identifier, e.g. 'RULE_001'")
    rule_name: str = Field(description="Human-readable rule name")
    category: str = Field(description="SIF precursor category")
    severity: int = Field(description="Severity integer 1-4")
    severity_label: str = Field(description="Severity label (LOW, MEDIUM, HIGH, CRITICAL)")
    explanation: Optional[str] = Field(default=None, description="Regulatory explanation")


class FactorScores(BaseModel):
    """Transparent breakdown of the numerical factors feeding the composite score."""

    model_probability: float = Field(ge=0.0, le=1.0, description="Normalized model precursor probability")
    rule_severity: float = Field(ge=0.0, le=1.0, description="Normalized rule engine severity score")
    barrier_failure: float = Field(ge=0.0, le=1.0, description="Barrier compromise / failure score")
    critical_hazard: float = Field(ge=0.0, le=1.0, description="Hazard consequence multiplier")
    critical_activity: float = Field(ge=0.0, le=1.0, description="Activity consequence multiplier")
    recurring_pattern: Optional[float] = Field(default=None, description="Recurrence / pattern factor")


class StructuredExplanation(BaseModel):
    """
    Structured explanation breakdown for HSE transparency (Phase 14).
    Ensures every prediction produces an itemized, non-contradictory rationale.
    """

    priority: PriorityLevel = Field(description="Triage priority level")
    important_detected_signals: list[str] = Field(
        default_factory=list, description="Key contextual signals detected"
    )
    triggered_safety_rules: list[str] = Field(
        default_factory=list, description="Deterministic safety rules fired with severity"
    )
    extracted_hazard: Optional[str] = Field(
        default=None, description="Extracted primary hazard"
    )
    extracted_activity: Optional[str] = Field(
        default=None, description="Extracted operational activity"
    )
    barrier_control_status: Optional[str] = Field(
        default=None, description="Condition of safety barrier or control"
    )
    model_probability: float = Field(
        ge=0.0, le=1.0, description="Raw ML precursor probability"
    )
    model_probability_percent: str = Field(
        description="Formatted percentage string (e.g. 94.2%)"
    )
    reason_for_final_priority: str = Field(
        description="Primary operational justification for the assigned priority"
    )
    why: list[str] = Field(
        default_factory=list, description="Itemized bullet list answering WHY"
    )
    formatted_text: str = Field(
        description="Clean formatted human-readable explanation matching the required template"
    )


class DecisionInput(BaseModel):
    """
    Input payload for the decision engine.
    Can be called either with raw text (triggering full pipeline)
    or with pre-computed components.
    """

    report_id: Optional[str] = Field(default=None, description="Unique report identifier")
    report_text: Optional[str] = Field(default=None, description="Raw report description")

    # Optional pre-computed pipeline components
    sif_probability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Pre-computed classifier probability"
    )
    activity: Optional[str] = Field(default=None, description="Extracted work activity")
    hazard: Optional[str] = Field(default=None, description="Extracted hazard")
    barrier: Optional[str] = Field(default=None, description="Extracted barrier or control")
    barrier_status: Optional[str] = Field(default=None, description="Status of the barrier (e.g. Not Verified, Absent)")
    location: Optional[str] = Field(default=None, description="Facility location")
    equipment: Optional[str] = Field(default=None, description="Involved equipment")
    recurring_risk_signal: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Optional recurrence score from similarity engine"
    )


class DecisionResult(BaseModel):
    """
    Authoritative output structure from the SIF Sentinel Decision Engine.
    Conforms directly to the Phase 7 specification for HSE review triage.
    """

    report_id: str = Field(description="Unique report identifier")
    report_text: Optional[str] = Field(default=None, description="Original narrative description of the safety report")
    sif_probability: float = Field(ge=0.0, le=1.0, description="ML classifier SIF precursor probability")
    priority: PriorityLevel = Field(description="HSE review priority: LOW, MEDIUM, or HIGH")
    activity: Optional[str] = Field(default=None, description="Identified work activity")
    hazard: Optional[str] = Field(default=None, description="Identified primary hazard")
    barrier: Optional[str] = Field(default=None, description="Identified safety barrier / control")
    triggered_rules: list[TriggeredRuleSummary] = Field(
        default_factory=list, description="List of deterministic safety rules fired"
    )
    evidence: list[str] = Field(
        default_factory=list, description="Phrases in the report text serving as physical evidence"
    )
    explanation: str = Field(
        description="Clear, itemized rationale explaining to HSE officers WHY the report was prioritized"
    )

    # Additional rich metadata for transparency and reporting
    priority_score: float = Field(
        ge=0.0, le=1.0, description="Composite prioritization score (0.0 to 1.0) for HSE ranking"
    )
    barrier_status: Optional[str] = Field(
        default=None, description="Extracted barrier condition (e.g. Not Verified, Absent, Failed)"
    )
    location: Optional[str] = Field(default=None, description="Extracted location")
    equipment: Optional[str] = Field(default=None, description="Extracted equipment")
    factor_scores: Optional[FactorScores] = Field(
        default=None, description="Granular factor score breakdown"
    )
    escalated: bool = Field(
        default=False, description="True if priority was elevated via a safety policy override"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Reason for safety override escalation if applicable"
    )
    governance_notice: str = Field(
        default="SIF Sentinel prioritization score triages reports for HSE review and does not predict accidents.",
        description="Safety governance statement",
    )

    # Phase 12 Human-in-the-loop review determinations (dual view)
    hse_reviewed: bool = Field(default=False, description="Whether an HSE officer has reviewed this report")
    review_decision: Optional[str] = Field(default=None, description="HSE decision: confirmed, rejected, corrected")
    reviewer_id: Optional[str] = Field(default=None, description="Officer ID who completed review")
    reviewed_at: Optional[datetime] = Field(default=None, description="Review timestamp")
    review_comments: Optional[str] = Field(default=None, description="Officer comments / rationale")
    final_priority: Optional[PriorityLevel] = Field(default=None, description="Officer-validated final priority")
    final_activity: Optional[str] = Field(default=None, description="Officer-validated final activity")
    final_hazard: Optional[str] = Field(default=None, description="Officer-validated final hazard")
    final_barrier: Optional[str] = Field(default=None, description="Officer-validated final barrier")
    corrected_priority: Optional[PriorityLevel] = Field(default=None, description="Officer correction for priority")
    corrected_activity: Optional[str] = Field(default=None, description="Officer correction for activity")
    corrected_hazard: Optional[str] = Field(default=None, description="Officer correction for hazard")
    corrected_barrier: Optional[str] = Field(default=None, description="Officer correction for barrier")
    audit_trail: list[dict[str, Any]] = Field(default_factory=list, description="Append-only immutable audit trail")
    feedback_items: list[dict[str, Any]] = Field(default_factory=list, description="Model feedback and annotations")

    # Phase 13 Automated Workflow Status
    workflow_status: str = Field(default="PENDING", description="Automated HSE workflow status")
    in_review_queue: bool = Field(default=False, description="Whether report is in the HSE review queue")
    queue_entered_at: Optional[datetime] = Field(default=None, description="Timestamp entered review queue")
    alert_triggered: bool = Field(default=False, description="Whether an automated HIGH PRIORITY alert was triggered")

    # Phase 14 Structured Explanation
    structured_explanation: Optional[StructuredExplanation] = Field(
        default=None, description="Detailed deterministic, non-contradictory explanation breakdown"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict conforming to the canonical schema."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Direct JSON serialization."""
        return json.dumps(self.to_dict(), indent=indent)
