"""
SIF Sentinel — Pydantic schemas for report-related endpoints.

Schemas define the contract between the frontend and the backend API.
They live separately from database models (which don't exist yet in Phase 1).

Phase 2 update:
  - TriggeredRuleSchema added to expose rule engine output
  - AnalysisResult replaces PlaceholderAnalysis
  - pipeline_status changes from 'placeholder' to 'rules_active'
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReportType(str, Enum):
    unsafe_act = "unsafe_act"
    unsafe_condition = "unsafe_condition"
    near_miss = "near_miss"


class SeverityRating(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PriorityBand(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    critical = "CRITICAL"


# ---------------------------------------------------------------------------
# Request schemas (what the client sends)
# ---------------------------------------------------------------------------

class ReportTestRequest(BaseModel):
    """
    Payload for POST /reports/test.
    Accepts a raw safety report string and optional metadata.
    """

    report_text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The raw text of the safety report.",
        examples=["Worker observed operating angle grinder without face shield near H2S area."],
    )
    report_type: ReportType = Field(
        default=ReportType.near_miss,
        description="Category of the safety report.",
    )
    location: str = Field(
        default="Unknown",
        max_length=200,
        description="Physical location where the incident occurred.",
    )
    severity_self_rated: SeverityRating = Field(
        default=SeverityRating.medium,
        description="Severity as rated by the person submitting the report.",
    )


# ---------------------------------------------------------------------------
# Rule engine output schemas
# ---------------------------------------------------------------------------

class TriggeredRuleSchema(BaseModel):
    """Schema for a single triggered safety rule."""
    rule_id: str = Field(description="Rule identifier, e.g. 'RULE_001'")
    rule_name: str = Field(description="Human-readable rule name")
    category: str = Field(description="SIF precursor category")
    severity: int = Field(description="Severity integer 1–4")
    severity_label: str = Field(description="Severity label: LOW/MEDIUM/HIGH/CRITICAL")
    triggered_signals: list[str] = Field(
        description="Exact phrases in the report text that triggered this rule"
    )
    explanation: str = Field(description="Why this is a SIF precursor")
    reference: str = Field(description="Regulatory or industry standard reference")


# ---------------------------------------------------------------------------
# Analysis result schema
# ---------------------------------------------------------------------------

class AnalysisResult(BaseModel):
    """
    Analysis result returned by the pipeline.

    Phase 2 status:
      - rule_severity_score: REAL — computed by the deterministic rule engine
      - triggered_rules:     REAL — list of matched safety rules with evidence
      - model_confidence:    PLACEHOLDER — DistilBERT not connected until Phase 3
      - priority_score:      COMPOSITE — rule engine + placeholder model confidence
    """

    sif_flag: bool = Field(
        description="True if any HIGH or CRITICAL rule was triggered."
    )
    model_confidence: float = Field(
        description=(
            "ML model confidence (0.0–1.0). PLACEHOLDER in Phase 2 — "
            "DistilBERT will replace this in Phase 3."
        )
    )
    rule_severity_score: float = Field(
        description="Rule engine severity normalised to 0.0–1.0. REAL in Phase 2."
    )
    priority_score: float = Field(
        description="Composite priority score (0.0–1.0)."
    )
    priority_band: PriorityBand = Field(
        description="Priority band: LOW / MEDIUM / HIGH / CRITICAL"
    )
    triggered_rules: list[TriggeredRuleSchema] = Field(
        default_factory=list,
        description="All safety rules that fired, ordered by descending severity.",
    )
    triggered_categories: list[str] = Field(
        default_factory=list,
        description="Unique SIF precursor categories triggered.",
    )
    evidence_summary: str = Field(
        description="One-line summary of all triggered signals and rules."
    )
    explanation: str = Field(
        description="Human-readable explanation of the assigned priority band."
    )
    pipeline_status: str = Field(
        description=(
            "'rules_active': rule engine running on real logic. "
            "'rules_only': no ML model yet (Phase 2). "
            "'complete': full pipeline with ML (Phase 3+)."
        )
    )


# ---------------------------------------------------------------------------
# Full response schema
# ---------------------------------------------------------------------------

class ReportTestResponse(BaseModel):
    """Full response returned by POST /reports/test."""

    report_id: str = Field(description="Temporary UUID for this test report.")
    received_at: datetime = Field(description="Server timestamp when the report was received.")
    report_type: ReportType
    location: str
    word_count: int = Field(description="Word count of the submitted report text.")
    analysis: AnalysisResult
    pipeline_status: str = Field(
        default="rules_only",
        description=(
            "'rules_only': deterministic rule engine active, ML classifier not yet connected. "
            "'complete': full pipeline with ML (Phase 3+)."
        ),
    )


# ---------------------------------------------------------------------------
# Backward-compatible alias — kept so Phase 1 test names still make sense
# PlaceholderAnalysis is no longer used in routes but kept to avoid import errors
# ---------------------------------------------------------------------------

PlaceholderAnalysis = AnalysisResult
