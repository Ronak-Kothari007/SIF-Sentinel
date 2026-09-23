"""
SIF Sentinel — Production API v1 Routes (Phase 8)
=================================================

Implements the official v1 REST API:
  - POST /api/v1/analyze-report
  - GET  /api/v1/reports
  - GET  /api/v1/reports/{id}
  - GET  /api/v1/high-risk
  - GET  /api/v1/patterns
  - POST /api/v1/hse-review
  - GET  /api/v1/dashboard-summary
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.api_v1 import (
    AcknowledgeAlertRequest,
    AlertItem,
    AlertListResponse,
    AnalyzeReportRequest,
    AuditLogItem,
    AuditTrailResponse,
    DashboardSummaryResponse,
    FeedbackRequest,
    FeedbackResponse,
    HSEReviewRequest,
    HSEReviewResponse,
    PatternAnalysisResponse,
    ReportListResponse,
    SimilarReportsResponse,
    WorkflowStatusResponse,
)
from app.schemas.decision import DecisionResult, PriorityLevel
from app.services.decision_engine import SIFDecisionEngine
from app.services.report_store import StoredReport, get_repository

logger = logging.getLogger("sif_sentinel.api_v1")

router = APIRouter()

# Shared services
_decision_engine: Optional[SIFDecisionEngine] = None


def get_decision_engine() -> SIFDecisionEngine:
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = SIFDecisionEngine()
    return _decision_engine


# ---------------------------------------------------------------------------
# 1. POST /api/v1/analyze-report
# ---------------------------------------------------------------------------
@router.post(
    "/analyze-report",
    response_model=DecisionResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Safety Report",
    description=(
        "Run full SIF Sentinel AI & rule analysis on a safety report narrative. "
        "Combines DistilBERT/ML probability, extracted activity/hazard/barrier context, "
        "and deterministic safety rules into a transparent HSE triage priority score."
    ),
)
def analyze_report(payload: AnalyzeReportRequest) -> DecisionResult:
    engine = get_decision_engine()
    repo = get_repository()

    logger.info("Analyzing report: %s characters", len(payload.report_text))

    # Calculate automated recurrence signal via Sentence Transformers if not manually specified
    rec_signal = payload.recurring_risk_signal
    if rec_signal is None:
        try:
            rec_signal = repo.calculate_recurrence_signal(payload.report_text)
        except Exception as e:
            logger.warning("Recurrence signal calculation notice: %s", e)
            rec_signal = 0.0

    # Evaluate report with actual model and rule engine
    result = engine.evaluate(
        input_data=payload.report_text,
        report_id=payload.report_id,
        recurring_risk_signal=rec_signal,
    )

    # Persist in repository
    stored = StoredReport(
        report_id=result.report_id,
        report_text=payload.report_text,
        analysis=result,
        final_priority=result.priority,
    )
    repo.save(stored)

    # Persist in SQLAlchemy Database & execute automated workflow
    try:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        from app.services.workflow_service import AutomatedHSEWorkflow
        with SessionLocal() as db:
            DatabaseService.create_report(
                db=db,
                report_id=result.report_id,
                report_text=payload.report_text,
                location=payload.location or result.location or "Unknown",
            )
            DatabaseService.save_analysis(db=db, report_id=result.report_id, analysis=result)
            # Phase 13 Automated Workflow: trigger if HIGH priority
            AutomatedHSEWorkflow.process_analysis_workflow(
                stored_report=stored,
                analysis=result,
                repo=repo,
                db=db,
            )
    except Exception as e:
        logger.warning("Database persistence / workflow notice: %s", e)
        from app.services.workflow_service import AutomatedHSEWorkflow
        AutomatedHSEWorkflow.process_analysis_workflow(
            stored_report=stored,
            analysis=result,
            repo=repo,
            db=None,
        )

    return result


# ---------------------------------------------------------------------------
# 2. GET /api/v1/reports
# ---------------------------------------------------------------------------
@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="List Analyzed Reports",
    description="Retrieve paginated list of analyzed safety reports with optional priority, hazard, and activity filtering.",
)
def list_reports(
    limit: int = Query(default=50, ge=1, le=200, description="Max items per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    priority: Optional[PriorityLevel] = Query(default=None, description="Filter by priority (LOW, MEDIUM, HIGH)"),
    hazard: Optional[str] = Query(default=None, description="Filter by hazard keyword"),
    activity: Optional[str] = Query(default=None, description="Filter by activity keyword"),
) -> ReportListResponse:
    repo = get_repository()
    reports, total = repo.list_all(
        limit=limit,
        offset=offset,
        priority=priority,
        hazard=hazard,
        activity=activity,
    )

    return ReportListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[r.to_summary_item() for r in reports],
    )


# ---------------------------------------------------------------------------
# 3. GET /api/v1/reports/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/reports/{id}",
    response_model=DecisionResult,
    summary="Get Report Analysis",
    description="Retrieve the complete SIF Sentinel decision analysis for a specific report ID.",
)
def get_report(id: str) -> DecisionResult:
    repo = get_repository()
    stored = repo.get(id)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{id}' was not found in the repository.",
        )
    if not stored.analysis.report_text:
        stored.analysis.report_text = stored.report_text

    # Populate human review determination fields side-by-side with original AI output (dual view)
    res = stored.analysis.model_copy()
    res.hse_reviewed = stored.hse_reviewed
    res.review_decision = stored.review_decision
    res.reviewer_id = stored.reviewer_id
    res.reviewed_at = stored.reviewed_at
    res.review_comments = stored.review_comments
    res.final_priority = stored.final_priority
    res.final_activity = stored.final_activity
    res.final_hazard = stored.final_hazard
    res.final_barrier = stored.final_barrier
    res.corrected_priority = stored.corrected_priority
    res.corrected_activity = stored.corrected_activity
    res.corrected_hazard = stored.corrected_hazard
    res.corrected_barrier = stored.corrected_barrier
    res.audit_trail = stored.audit_logs
    res.feedback_items = stored.feedback_items
    return res


# ---------------------------------------------------------------------------
# 4. GET /api/v1/high-risk
# ---------------------------------------------------------------------------
@router.get(
    "/high-risk",
    response_model=ReportListResponse,
    summary="High-Risk Review Queue",
    description="Retrieve all reports triaged as HIGH priority requiring immediate HSE officer verification.",
)
def get_high_risk_reports(
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return"),
) -> ReportListResponse:
    repo = get_repository()
    high_risk_reports = repo.get_high_risk(limit=limit)

    return ReportListResponse(
        total=len(high_risk_reports),
        limit=limit,
        offset=0,
        items=[r.to_summary_item() for r in high_risk_reports],
    )


# ---------------------------------------------------------------------------
# 5. GET /api/v1/similar-reports/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/similar-reports/{id}",
    response_model=SimilarReportsResponse,
    summary="Find Semantically Similar Reports",
    description=(
        "Retrieve semantically similar reports for an observation ID using dense vector "
        "embeddings generated by Sentence Transformers (all-MiniLM-L6-v2) and cosine similarity."
    ),
)
def get_similar_reports(
    id: str,
    limit: int = Query(default=5, ge=1, le=20, description="Max similar reports to return"),
    threshold: float = Query(
        default=0.50, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff"
    ),
) -> SimilarReportsResponse:
    repo = get_repository()
    stored = repo.get(id)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{id}' was not found in the repository.",
        )

    similar_items = repo.find_similar(id, limit=limit, threshold=threshold)
    return SimilarReportsResponse(
        target_report_id=id,
        total_similar=len(similar_items),
        threshold=threshold,
        similar_reports=similar_items,
    )


# ---------------------------------------------------------------------------
# 6. GET /api/v1/patterns
# ---------------------------------------------------------------------------
@router.get(
    "/patterns",
    response_model=PatternAnalysisResponse,
    summary="Recurring Risk Patterns",
    description="Synthesizes prominent hazard trends, activity hotspots, and recurring barrier failure modes across the site.",
)
def get_patterns() -> PatternAnalysisResponse:
    repo = get_repository()
    return repo.get_patterns()


# ---------------------------------------------------------------------------
# 6. POST /api/v1/hse-review
# ---------------------------------------------------------------------------
@router.post(
    "/hse-review",
    response_model=HSEReviewResponse,
    summary="Submit HSE Review Decision",
    description="Record an HSE officer's human verification determination ('confirmed', 'rejected', or 'corrected').",
)
def submit_hse_review(payload: HSEReviewRequest) -> HSEReviewResponse:
    repo = get_repository()
    updated = repo.add_review(
        report_id=payload.report_id,
        reviewer_id=payload.reviewer_id,
        decision=payload.decision,
        corrected_priority=payload.corrected_priority,
        corrected_activity=payload.corrected_activity,
        corrected_hazard=payload.corrected_hazard,
        corrected_barrier=payload.corrected_barrier,
        comments=payload.comments,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot record review: Report '{payload.report_id}' does not exist.",
        )

    logger.info(
        "HSE review recorded: %s by %s (decision: %s)",
        payload.report_id,
        payload.reviewer_id,
        payload.decision,
    )

    # Persist in SQLAlchemy Database
    try:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        with SessionLocal() as db:
            DatabaseService.save_hse_review(
                db=db,
                report_id=payload.report_id,
                reviewer_id=payload.reviewer_id,
                decision=payload.decision,
                original_priority=updated.analysis.priority.value if hasattr(updated.analysis.priority, "value") else str(updated.analysis.priority),
                final_priority=updated.final_priority.value if hasattr(updated.final_priority, "value") else str(updated.final_priority),
                comments=payload.comments,
                original_activity=updated.analysis.activity,
                original_hazard=updated.analysis.hazard,
                original_barrier=updated.analysis.barrier,
                original_sif_probability=updated.analysis.sif_probability,
                corrected_activity=updated.corrected_activity,
                corrected_hazard=updated.corrected_hazard,
                corrected_barrier=updated.corrected_barrier,
            )
            from app.services.workflow_service import AutomatedHSEWorkflow
            AutomatedHSEWorkflow.process_review_resolution(
                stored_report=updated,
                decision=payload.decision,
                reviewer_id=payload.reviewer_id,
                comments=payload.comments,
                repo=repo,
                db=db,
            )
    except Exception as e:
        logger.warning("Database review persistence notice: %s", e)

    original_ai = {
        "priority": updated.analysis.priority.value if hasattr(updated.analysis.priority, "value") else str(updated.analysis.priority),
        "activity": updated.analysis.activity,
        "hazard": updated.analysis.hazard,
        "barrier": updated.analysis.barrier,
        "barrier_status": updated.analysis.barrier_status,
        "sif_probability": updated.analysis.sif_probability,
    }

    corrected = {
        "priority": updated.corrected_priority.value if hasattr(updated.corrected_priority, "value") else str(updated.corrected_priority) if updated.corrected_priority else None,
        "activity": updated.corrected_activity,
        "hazard": updated.corrected_hazard,
        "barrier": updated.corrected_barrier,
    } if payload.decision == "corrected" else None

    return HSEReviewResponse(
        status="success",
        message=f"Review successfully recorded by officer {payload.reviewer_id}.",
        report_id=updated.report_id,
        reviewed_at=updated.reviewed_at,
        reviewer_id=payload.reviewer_id,
        decision=payload.decision,
        original_ai_output=original_ai,
        final_priority=updated.final_priority,
        final_activity=updated.final_activity,
        final_hazard=updated.final_hazard,
        final_barrier=updated.final_barrier,
        corrected_values=corrected,
        comments=payload.comments,
    )


# ---------------------------------------------------------------------------
# 7. POST /api/v1/feedback & GET /api/v1/feedback
# ---------------------------------------------------------------------------
@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Model Annotation / User Feedback",
    description="Submit human officer feedback annotations, false positive/negative tags, or model critiques.",
)
def submit_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    repo = get_repository()
    stored = repo.get(payload.report_id)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot record feedback: Report '{payload.report_id}' does not exist.",
        )

    fb_entry = repo.add_feedback(
        report_id=payload.report_id,
        feedback_type=payload.feedback_type,
        notes=payload.notes,
        user_suggested_priority=payload.user_suggested_priority,
        user_id=payload.user_id,
    )

    # Persist in SQL DB
    try:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        with SessionLocal() as db:
            DatabaseService.save_feedback(
                db=db,
                report_id=payload.report_id,
                user_id=payload.user_id,
                feedback_type=payload.feedback_type,
                notes=payload.notes,
                user_suggested_priority=payload.user_suggested_priority.value if payload.user_suggested_priority and hasattr(payload.user_suggested_priority, "value") else str(payload.user_suggested_priority) if payload.user_suggested_priority else None,
            )
    except Exception as e:
        logger.warning("Database feedback persistence notice: %s", e)

    return FeedbackResponse(
        status="success",
        message="Feedback annotation successfully logged in audit trail.",
        feedback_id=fb_entry["id"],
        report_id=payload.report_id,
        feedback_type=payload.feedback_type,
        user_suggested_priority=payload.user_suggested_priority,
        notes=payload.notes,
        created_at=fb_entry["created_at"],
    )


@router.get(
    "/feedback",
    summary="List Feedback Annotations",
    description="Retrieve list of submitted human feedback annotations, optionally filtered by report ID.",
)
def get_feedback(
    report_id: Optional[str] = Query(default=None, description="Optional target report filter")
) -> list[dict[str, Any]]:
    repo = get_repository()
    return repo.get_feedback(report_id=report_id)


# ---------------------------------------------------------------------------
# 8. GET /api/v1/reports/{id}/audit-trail
# ---------------------------------------------------------------------------
@router.get(
    "/reports/{id}/audit-trail",
    response_model=AuditTrailResponse,
    summary="Get Report Audit Trail",
    description="Retrieve chronological immutable audit trail for a report, including AI triage, officer reviews, and feedback.",
)
def get_report_audit_trail(id: str) -> AuditTrailResponse:
    repo = get_repository()
    stored = repo.get(id)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{id}' was not found in the repository.",
        )

    logs_data = repo.get_audit_trail(id)
    items = [
        AuditLogItem(
            action=log.get("action", "UNKNOWN"),
            entity_type=log.get("entity_type", "report"),
            entity_id=log.get("entity_id", id),
            actor_id=log.get("actor_id", "system"),
            details=log.get("details", {}),
            created_at=log.get("created_at") or stored.created_at,
        )
        for log in logs_data
    ]

    return AuditTrailResponse(
        report_id=id,
        total_logs=len(items),
        logs=items,
    )



# ---------------------------------------------------------------------------
# 7. GET /api/v1/dashboard-summary
# ---------------------------------------------------------------------------
@router.get(
    "/dashboard-summary",
    response_model=DashboardSummaryResponse,
    summary="Executive Dashboard Summary",
    description="Returns high-level safety metrics, SIF precursor rates, review queue counts, and top hazard breakdown.",
)
def get_dashboard_summary() -> DashboardSummaryResponse:
    repo = get_repository()
    return repo.get_dashboard_summary()


# ---------------------------------------------------------------------------
# 8. Alert & Workflow Endpoints (Phase 13: Automated HSE Workflow)
# ---------------------------------------------------------------------------

@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="List Precursor Safety Alerts",
    description="Retrieve list of internal precursor safety alerts generated by automated triage.",
)
def list_alerts(
    acknowledged: Optional[bool] = Query(default=None, description="Filter by acknowledged boolean status"),
    limit: int = Query(default=50, ge=1, le=200, description="Max alerts to return"),
) -> AlertListResponse:
    repo = get_repository()
    alerts, total, unacked = repo.get_alerts(acknowledged=acknowledged, limit=limit)
    return AlertListResponse(
        alerts=alerts,
        total=total,
        unacknowledged_count=unacked,
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertItem,
    summary="Acknowledge Precursor Alert",
    description="Mark an internal HIGH priority alert as acknowledged by an HSE officer.",
)
def acknowledge_alert(
    alert_id: str,
    payload: Optional[AcknowledgeAlertRequest] = None,
) -> AlertItem:
    repo = get_repository()
    officer_id = payload.officer_id if payload else "HSE-OFFICER-01"
    alert = repo.acknowledge_alert(alert_id, officer_id=officer_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' was not found.",
        )

    try:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        with SessionLocal() as db:
            DatabaseService.acknowledge_alert(db, alert_id=alert_id, officer_id=officer_id)
    except Exception as e:
        logger.warning("DB alert acknowledge notice: %s", e)

    return alert


@router.get(
    "/workflow/status/{report_id}",
    response_model=WorkflowStatusResponse,
    summary="Get Report Workflow Status",
    description="Retrieve automated HSE workflow lifecycle status, timestamps, and active alerts for a safety report.",
)
def get_workflow_status(report_id: str) -> WorkflowStatusResponse:
    repo = get_repository()
    stored = repo.get(report_id)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' was not found in the repository.",
        )

    from app.services.workflow_service import WorkflowStatus
    alerts, _, _ = repo.get_alerts(limit=100)
    report_alerts = [a for a in alerts if a.report_id == report_id]

    audit_logs = [
        AuditLogItem(
            action=log.get("action", "UNKNOWN"),
            entity_type=log.get("entity_type", "report"),
            entity_id=log.get("entity_id", report_id),
            actor_id=log.get("actor_id", "system"),
            details=log.get("details", {}),
            created_at=log.get("created_at") or stored.created_at,
        )
        for log in stored.audit_logs
    ]

    final_p = stored.final_priority or stored.analysis.priority
    priority_str = final_p.value if hasattr(final_p, "value") else str(final_p)

    return WorkflowStatusResponse(
        report_id=stored.report_id,
        priority=priority_str,
        workflow_status=stored.workflow_status,
        in_review_queue=stored.in_review_queue,
        queue_entered_at=stored.queue_entered_at,
        workflow_updated_at=stored.workflow_updated_at,
        display_badge=WorkflowStatus.get_display_badge(stored.workflow_status),
        active_alerts=report_alerts,
        audit_trail=audit_logs,
    )


# ---------------------------------------------------------------------------
# Demo Mode Routes (Phase 16)
# ---------------------------------------------------------------------------
from app.api.v1.demo import router as demo_router
router.include_router(demo_router)

