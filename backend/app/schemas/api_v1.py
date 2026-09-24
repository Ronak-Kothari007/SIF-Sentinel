"""
SIF Sentinel — Production API v1 Pydantic Schemas (Phase 8)
===========================================================

Defines request/response schemas, validation rules, and structured error models
for the production FastAPI endpoints:
  - POST /api/v1/analyze-report
  - GET  /api/v1/reports
  - GET  /api/v1/reports/{id}
  - GET  /api/v1/high-risk
  - GET  /api/v1/patterns
  - POST /api/v1/hse-review
  - GET  /api/v1/dashboard-summary
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.decision import DecisionResult, PriorityLevel


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class AnalyzeReportRequest(BaseModel):
    """Payload for POST /api/v1/analyze-report."""

    report_text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Raw narrative description of the safety observation or near-miss.",
        examples=["Maintenance started on energized equipment without verified isolation."],
    )
    report_id: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional custom report ID. If omitted, a unique ID is generated.",
        examples=["SYN-001"],
    )
    location: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional facility location / plant zone override.",
        examples=["Tank Farm 3"],
    )
    recurring_risk_signal: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional recurrence/similarity score from similarity engine (0.0 to 1.0).",
        examples=[0.75],
    )


class HSEReviewRequest(BaseModel):
    """Payload for POST /api/v1/hse-review."""

    report_id: str = Field(
        ...,
        description="Unique ID of the report being reviewed.",
        examples=["SYN-001"],
    )
    reviewer_id: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="HSE officer employee ID or username.",
        examples=["HSE-OFFICER-07"],
    )
    decision: str = Field(
        ...,
        pattern=r"^(confirmed|rejected|corrected)$",
        description="HSE determination: 'confirmed', 'rejected', or 'corrected'.",
        examples=["confirmed"],
    )
    corrected_priority: Optional[PriorityLevel] = Field(
        default=None,
        description="Officer-adjusted priority if decision is 'corrected'.",
        examples=[PriorityLevel.HIGH],
    )
    corrected_activity: Optional[str] = Field(
        default=None,
        description="Officer-adjusted work activity if decision is 'corrected'.",
        examples=["Hot Work"],
    )
    corrected_hazard: Optional[str] = Field(
        default=None,
        description="Officer-adjusted primary hazard if decision is 'corrected'.",
        examples=["Thermal Energy"],
    )
    corrected_barrier: Optional[str] = Field(
        default=None,
        description="Officer-adjusted critical barrier if decision is 'corrected'.",
        examples=["Permit to Work"],
    )
    comments: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="HSE officer notes, corrective action references, or rationale.",
        examples=["Confirmed LOTO bypass on motor feed panel. Stop work notice issued."],
    )


# ---------------------------------------------------------------------------
# Item & List Response Schemas
# ---------------------------------------------------------------------------

class ReportSummaryItem(BaseModel):
    """Summary item representation for lists and queries."""

    report_id: str
    report_text: str
    created_at: datetime
    priority: PriorityLevel
    priority_score: float
    sif_probability: float
    activity: Optional[str] = None
    hazard: Optional[str] = None
    barrier: Optional[str] = None
    barrier_status: Optional[str] = None
    location: Optional[str] = None
    equipment: Optional[str] = None
    triggered_rules_count: int = 0
    hse_reviewed: bool = False
    review_decision: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_comments: Optional[str] = None
    ai_priority: Optional[PriorityLevel] = None
    ai_activity: Optional[str] = None
    ai_hazard: Optional[str] = None
    ai_barrier: Optional[str] = None
    final_priority: Optional[PriorityLevel] = None
    final_activity: Optional[str] = None
    final_hazard: Optional[str] = None
    final_barrier: Optional[str] = None
    explanation_snippet: str = ""
    workflow_status: str = "PENDING"
    in_review_queue: bool = False
    queue_entered_at: Optional[datetime] = None
    alert_triggered: bool = False


class ReportListResponse(BaseModel):
    """Paginated response envelope for GET /api/v1/reports."""

    total: int = Field(ge=0, description="Total matching reports count in repository")
    limit: int = Field(ge=1, description="Page limit requested")
    offset: int = Field(ge=0, description="Page offset requested")
    items: list[ReportSummaryItem] = Field(default_factory=list, description="List of report items")


class HSEReviewResponse(BaseModel):
    """Response returned by POST /api/v1/hse-review."""

    status: str = Field(default="success", description="Review submission status")
    message: str = Field(description="Action confirmation message")
    report_id: str
    reviewed_at: datetime
    reviewer_id: str
    decision: str
    original_ai_output: dict[str, Any] = Field(default_factory=dict, description="Original un-overwritten AI model prediction")
    final_priority: PriorityLevel
    final_activity: Optional[str] = None
    final_hazard: Optional[str] = None
    final_barrier: Optional[str] = None
    corrected_values: Optional[dict[str, Any]] = None
    comments: Optional[str] = None


# ---------------------------------------------------------------------------
# Feedback & Audit Trail Schemas (Phase 12)
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    """Payload for POST /api/v1/feedback."""

    report_id: str = Field(..., description="Target safety report identifier", examples=["SYN-001"])
    feedback_type: str = Field(
        ...,
        description="Type of feedback: 'false_positive', 'false_negative', 'label_correction', 'general_feedback'",
        examples=["label_correction"],
    )
    user_suggested_priority: Optional[PriorityLevel] = Field(
        default=None,
        description="Optional suggested triage priority from user",
    )
    notes: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Officer feedback annotations, model critique, or ground-truth rationale",
        examples=["Classifier flagged housekeeping but missed nearby high pressure steam line."],
    )
    user_id: Optional[str] = Field(default=None, description="Optional submitting user or officer ID")


class FeedbackResponse(BaseModel):
    """Response for POST /api/v1/feedback."""

    status: str = Field(default="success")
    message: str
    feedback_id: str
    report_id: str
    feedback_type: str
    user_suggested_priority: Optional[PriorityLevel] = None
    notes: str
    created_at: datetime


class AuditLogItem(BaseModel):
    """Immutable audit trail log record."""

    id: Optional[str] = None
    action: str = Field(description="Action executed: ANALYZE_REPORT, HSE_REVIEW, FEEDBACK_SUBMITTED")
    entity_type: str = Field(description="Entity type: report, hse_review, feedback")
    entity_id: str = Field(description="Target report or review ID")
    actor_id: str = Field(description="User, officer, or system agent that executed action")
    details: dict[str, Any] = Field(default_factory=dict, description="Full action snapshot payload")
    created_at: datetime = Field(description="Action execution timestamp")


class AuditTrailResponse(BaseModel):
    """Response for GET /api/v1/reports/{id}/audit-trail."""

    report_id: str
    total_logs: int
    logs: list[AuditLogItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Semantic Similarity & Recurring Risk Schemas (Phase 11)
# ---------------------------------------------------------------------------

class SimilarReportItem(BaseModel):
    """Semantically similar report item retrieved via dense vector search."""

    report_id: str = Field(description="Unique report identifier")
    similarity_score: float = Field(ge=0.0, le=1.0, description="Cosine similarity score (0.0 to 1.0)")
    report_text: str = Field(description="Narrative text of similar observation")
    priority: PriorityLevel = Field(description="Triage priority of similar report")
    activity: Optional[str] = Field(default=None, description="Identified activity")
    hazard: Optional[str] = Field(default=None, description="Identified hazard")
    barrier: Optional[str] = Field(default=None, description="Identified barrier")
    barrier_status: Optional[str] = Field(default=None, description="Barrier condition")
    created_at: Optional[datetime] = Field(default=None, description="Observation timestamp")


class SimilarReportsResponse(BaseModel):
    """Response for GET /api/v1/similar-reports/{id}."""

    target_report_id: str = Field(description="Query reference report ID")
    total_similar: int = Field(ge=0, description="Count of matching semantically similar reports")
    threshold: float = Field(ge=0.0, le=1.0, description="Minimum cosine similarity cutoff applied")
    similar_reports: list[SimilarReportItem] = Field(
        default_factory=list, description="Ranked list of semantically similar reports"
    )


class TemporalTrend(BaseModel):
    """Temporal progression and frequency dynamics of a recurring risk pattern."""

    trend_direction: str = Field(description="Direction: 'increasing', 'stable', 'decreasing', or 'isolated'")
    first_seen: Optional[datetime] = Field(default=None, description="Timestamp of earliest report in pattern")
    last_seen: Optional[datetime] = Field(default=None, description="Timestamp of most recent report in pattern")
    span_days: int = Field(default=0, description="Span in days between first and last occurrence")
    date_counts: dict[str, int] = Field(default_factory=dict, description="Counts by date")


class SemanticRecurringPattern(BaseModel):
    """
    Cluster of semantically similar safety reports identified via Sentence Transformers (all-MiniLM-L6-v2).
    Represents a systemic precursor failure pattern across the facility.
    """

    pattern_id: str = Field(description="Unique pattern identifier, e.g. 'PAT-SEM-001'")
    number_of_reports: int = Field(ge=1, description="Number of correlated safety reports")
    report_ids: list[str] = Field(default_factory=list, description="Report IDs in this cluster")
    common_activity: str = Field(description="Most prevalent work activity")
    common_hazard: str = Field(description="Most prevalent hazard category")
    common_barrier_failure: str = Field(description="Dominant barrier failure mode")
    trend: Optional[TemporalTrend] = Field(default=None, description="Date trend analysis")
    representative_text: str = Field(description="Medoid observation narrative exemplifying the pattern")
    average_similarity: float = Field(ge=0.0, le=1.0, description="Mean intra-cluster cosine similarity")
    recommended_action: str = Field(description="Prescriptive safety mitigation recommendation")


# ---------------------------------------------------------------------------
# Analytics & Aggregation Schemas
# ---------------------------------------------------------------------------

class HazardCount(BaseModel):
    hazard: str
    count: int
    percentage: float


class ActivityCount(BaseModel):
    activity: str
    count: int
    percentage: float


class BarrierGapItem(BaseModel):
    barrier: str
    barrier_status: str
    count: int


class PatternAnalysisResponse(BaseModel):
    """Response for GET /api/v1/patterns."""

    total_analyzed: int
    top_hazards: list[HazardCount]
    top_activities: list[ActivityCount]
    top_barrier_gaps: list[BarrierGapItem]
    recurring_clusters: list[dict[str, Any]]
    semantic_patterns: list[SemanticRecurringPattern] = Field(
        default_factory=list, description="Semantic clusters discovered via Sentence Transformers"
    )
    summary: str


class PriorityDistribution(BaseModel):
    """Priority category distribution counts."""
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0
    UNREVIEWED: Optional[int] = None


class ReviewStatusCounts(BaseModel):
    """Breakdown of human officer review triage."""
    pending: int = 0
    confirmed: int = 0
    corrected: int = 0
    rejected: int = 0
    total_reviewed: int = 0


class DashboardSummaryResponse(BaseModel):
    """Response for GET /api/v1/dashboard-summary."""

    total_reports: int = Field(description="Total safety reports logged")
    high_priority_count: int = Field(description="Reports triaged as HIGH priority")
    medium_priority_count: int = Field(description="Reports triaged as MEDIUM priority")
    low_priority_count: int = Field(description="Reports triaged as LOW priority")
    sif_precursor_rate: float = Field(
        description="Percentage of total reports identified as potential SIF precursors"
    )
    pending_reviews_count: int = Field(description="High-priority reports awaiting officer review")
    completed_reviews_count: int = Field(description="Reports verified and signed off")
    top_hazards: list[HazardCount] = Field(default_factory=list)
    top_activities: list[ActivityCount] = Field(default_factory=list)
    top_barrier_failures: list[BarrierGapItem] = Field(default_factory=list)
    # Phase 12 Human-in-the-loop metrics:
    ai_distribution: PriorityDistribution = Field(default_factory=PriorityDistribution, description="Original AI model predictions")
    hse_distribution: PriorityDistribution = Field(default_factory=PriorityDistribution, description="Final HSE officer determinations")
    review_status: ReviewStatusCounts = Field(default_factory=ReviewStatusCounts, description="Officer review status breakdown")
    agreement_rate: float = Field(default=100.0, description="Agreement % between AI and HSE determinations")
    # Phase 13 Automated Workflow alerts:
    active_alerts: list[AlertItem] = Field(default_factory=list, description="Active or unacknowledged high-priority safety alerts")
    unread_alerts_count: int = Field(default=0, description="Count of unacknowledged high-priority alerts")


# ---------------------------------------------------------------------------
# Structured Error Response
# ---------------------------------------------------------------------------

class StructuredErrorResponse(BaseModel):
    """Standardized API error envelope for client consumption."""

    detail: str = Field(description="Human-readable error description")
    error_code: str = Field(description="Machine-readable error classification code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Server error timestamp")
    path: Optional[str] = Field(default=None, description="Request path that caused the error")


# ---------------------------------------------------------------------------
# Alert & Automated Workflow Schemas (Phase 13)
# ---------------------------------------------------------------------------

class AlertItem(BaseModel):
    """Internal HSE alert event schema for high-priority precursor escalations."""

    alert_id: str = Field(description="Unique alert identifier")
    report_id: str = Field(description="Associated safety report identifier")
    title: str = Field(description="Alert headline (e.g. HIGH PRIORITY → HSE REVIEW REQUIRED)")
    severity: str = Field(default="HIGH", description="Alert severity: HIGH or CRITICAL")
    message: str = Field(description="Actionable alert message detailing SIF risk and hazard")
    workflow_status: str = Field(default="HSE_REVIEW_REQUIRED", description="Current workflow lifecycle state")
    acknowledged: bool = Field(default=False, description="Whether an HSE officer has acknowledged this alert")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Timestamp of officer acknowledgement")
    acknowledged_by: Optional[str] = Field(default=None, description="Officer identifier who acknowledged the alert")
    created_at: datetime = Field(description="Alert creation timestamp")
    report_text_snippet: Optional[str] = Field(default=None, description="Narrative snippet")
    hazard: Optional[str] = Field(default=None, description="Identified hazard")
    barrier: Optional[str] = Field(default=None, description="Compromised barrier")
    sif_probability: Optional[float] = Field(default=None, description="SIF precursor probability")


class AlertListResponse(BaseModel):
    """Response for GET /api/v1/alerts."""

    alerts: list[AlertItem] = Field(default_factory=list, description="List of alert events")
    total: int = Field(description="Total alert events count")
    unacknowledged_count: int = Field(description="Count of unacknowledged alerts")


class AcknowledgeAlertRequest(BaseModel):
    """Payload for POST /api/v1/alerts/{alert_id}/acknowledge."""

    officer_id: str = Field(default="HSE-OFFICER-01", max_length=100, description="Reviewing officer identifier")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional acknowledgement note")


class WorkflowStatusResponse(BaseModel):
    """Response for GET /api/v1/workflow/status/{report_id}."""

    report_id: str
    priority: str
    workflow_status: str
    in_review_queue: bool
    queue_entered_at: Optional[datetime] = None
    workflow_updated_at: datetime
    display_badge: str
    active_alerts: list[AlertItem] = Field(default_factory=list)
    audit_trail: list[AuditLogItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Action Center Schemas (Phase 16)
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    """Schema for a trackable HSE Action."""
    
    id: str = Field(description="Unique action identifier")
    report_id: str = Field(description="Associated safety report identifier")
    title: str = Field(description="Short action title")
    priority: PriorityLevel = Field(default=PriorityLevel.HIGH, description="Risk priority")
    status: str = Field(default="Open", description="Status: Open, Assigned, In Progress, Verification, Closed")
    site_location: Optional[str] = Field(default=None, description="Location context")
    assigned_to: Optional[str] = Field(default=None, description="Assigned personnel")
    due_date: Optional[datetime] = Field(default=None, description="Target completion date")
    created_at: datetime
    updated_at: datetime


class ActionListResponse(BaseModel):
    """Response for GET /api/v1/actions."""
    
    actions: list[ActionItem] = Field(default_factory=list)
    total: int = Field(description="Total count of actions")


class UpdateActionStatusRequest(BaseModel):
    """Payload for PUT /api/v1/actions/{id}/status."""
    
    status: str = Field(description="New status string")
    assigned_to: Optional[str] = Field(default=None, description="Update assignee")

