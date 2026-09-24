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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        prio_str = priority.value if hasattr(priority, "value") else str(priority) if priority else None
        reports, total = DatabaseService.list_all(
            db=db,
            limit=limit,
            offset=offset,
            priority=prio_str,
            hazard=hazard,
            activity=activity,
        )

        return ReportListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=reports,
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        res = DatabaseService.get_decision_result(db, id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{id}' was not found in the repository.",
            )
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        high_risk_reports = DatabaseService.get_high_risk(db, limit=limit)
        return ReportListResponse(
            total=len(high_risk_reports),
            limit=limit,
            offset=0,
            items=high_risk_reports,
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
    
    # Verify report exists
    stored = repo.get(id)
    if not stored:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        with SessionLocal() as db:
            if not DatabaseService.get_decision_result(db, id):
                raise HTTPException(status_code=404, detail="Report not found")
                
    # We still use repo for the vector similarity engine
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        db_patterns = DatabaseService.get_patterns(db)
        # We overlay semantic patterns from the in-memory engine
        repo = get_repository()
        semantic_patterns = []
        try:
            # We need to pass stored_reports to detect_recurring_patterns
            # Let's bypass this for now if we can't easily fetch all StoredReports
            semantic_patterns = repo.get_patterns().semantic_patterns
        except Exception:
            pass
            
        db_patterns["semantic_patterns"] = semantic_patterns
        return PatternAnalysisResponse(**db_patterns)


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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    from app.services.workflow_service import AutomatedHSEWorkflow
    
    with SessionLocal() as db:
        # Fetch existing report to get original AI predictions
        res = DatabaseService.get_decision_result(db, payload.report_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot record review: Report '{payload.report_id}' does not exist.",
            )
            
        final_priority_val = res.priority.value if hasattr(res.priority, "value") else str(res.priority)
        if payload.decision == "corrected" and payload.corrected_priority:
            final_priority_val = payload.corrected_priority.value if hasattr(payload.corrected_priority, "value") else str(payload.corrected_priority)
        elif payload.decision == "rejected":
            final_priority_val = "LOW"
            
        review = DatabaseService.save_hse_review(
            db=db,
            report_id=payload.report_id,
            reviewer_id=payload.reviewer_id,
            decision=payload.decision,
            original_priority=res.priority.value if hasattr(res.priority, "value") else str(res.priority),
            final_priority=final_priority_val,
            comments=payload.comments,
            original_activity=res.activity,
            original_hazard=res.hazard,
            original_barrier=res.barrier,
            original_sif_probability=res.sif_probability,
            corrected_activity=payload.corrected_activity,
            corrected_hazard=payload.corrected_hazard,
            corrected_barrier=payload.corrected_barrier,
        )
        
        # Reload to get the fresh object
        updated = DatabaseService.get_decision_result(db, payload.report_id)
        
        # Update actual in-memory repo object if available to sync state for tests
        repo = get_repository()
        repo_stored = repo.get(payload.report_id)
        
        if repo_stored:
            target_report = repo_stored
        else:
            from app.services.report_store import StoredReport
            target_report = StoredReport(
                report_id=updated.report_id,
                report_text=updated.report_text,
                analysis=updated,
                final_priority=updated.final_priority,
                hse_reviewed=True,
                review_decision=payload.decision
            )
        
        AutomatedHSEWorkflow.process_review_resolution(
            stored_report=target_report,
            decision=payload.decision,
            reviewer_id=payload.reviewer_id,
            comments=payload.comments,
            repo=repo,
            db=db,
        )
        
        original_ai = {
            "priority": res.priority.value if hasattr(res.priority, "value") else str(res.priority),
            "activity": res.activity,
            "hazard": res.hazard,
            "barrier": res.barrier,
            "barrier_status": res.barrier_status,
            "sif_probability": res.sif_probability,
        }

        corrected = {
            "priority": payload.corrected_priority.value if hasattr(payload.corrected_priority, "value") else str(payload.corrected_priority) if payload.corrected_priority else None,
            "activity": payload.corrected_activity,
            "hazard": payload.corrected_hazard,
            "barrier": payload.corrected_barrier,
        } if payload.decision == "corrected" else None
        
        return HSEReviewResponse(
            status="success",
            message=f"Review successfully recorded by officer {payload.reviewer_id}.",
            report_id=updated.report_id,
            reviewed_at=review.reviewed_at,
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        res = DatabaseService.get_decision_result(db, payload.report_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot record feedback: Report '{payload.report_id}' does not exist.",
            )
            
        fb = DatabaseService.save_feedback(
            db=db,
            report_id=payload.report_id,
            user_id=payload.user_id,
            feedback_type=payload.feedback_type,
            notes=payload.notes,
            user_suggested_priority=payload.user_suggested_priority.value if payload.user_suggested_priority and hasattr(payload.user_suggested_priority, "value") else str(payload.user_suggested_priority) if payload.user_suggested_priority else None,
        )
        
        return FeedbackResponse(
            status="success",
            message="Feedback annotation successfully logged in audit trail.",
            feedback_id=fb.id,
            report_id=payload.report_id,
            feedback_type=payload.feedback_type,
            user_suggested_priority=payload.user_suggested_priority,
            notes=payload.notes,
            created_at=fb.created_at,
        )


@router.get(
    "/feedback",
    summary="List Feedback Annotations",
    description="Retrieve list of submitted human feedback annotations, optionally filtered by report ID.",
)
def get_feedback(
    report_id: Optional[str] = Query(default=None, description="Optional target report filter")
) -> list[dict[str, Any]]:
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        # To avoid adding a complex query, we can just fetch the report or all reports
        if report_id:
            feedbacks = DatabaseService.get_feedback_for_report(db, report_id)
        else:
            from app.db.models import Feedback
            feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
            
        return [
            {
                "id": fb.id,
                "feedback_type": fb.feedback_type,
                "user_suggested_priority": fb.user_suggested_priority,
                "notes": fb.notes,
                "user_id": fb.user_id,
                "created_at": fb.created_at,
                "report_id": fb.report_id
            }
            for fb in feedbacks
        ]


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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    import json
    
    with SessionLocal() as db:
        res = DatabaseService.get_decision_result(db, id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{id}' was not found in the repository.",
            )
            
        logs_data = DatabaseService.get_audit_trail_for_report(db, id)
        items = [
            AuditLogItem(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                actor_id=log.actor_id,
                details=json.loads(log.details_json) if log.details_json else {},
                created_at=log.created_at,
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        return DashboardSummaryResponse(**DatabaseService.get_dashboard_summary(db))


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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    with SessionLocal() as db:
        alerts = DatabaseService.get_alerts(db, acknowledged=acknowledged, limit=limit)
        unacked = len(DatabaseService.get_alerts(db, acknowledged=False, limit=1000))
        
        alert_items = []
        for a in alerts:
            alert_items.append(AlertItem(
                alert_id=a.id,
                report_id=a.report_id,
                title=a.title,
                severity=a.severity,
                message=a.message,
                workflow_status=a.workflow_status,
                acknowledged=a.acknowledged,
                acknowledged_at=a.acknowledged_at,
                acknowledged_by=a.acknowledged_by,
                created_at=a.created_at,
            ))
            
        return AlertListResponse(
            alerts=alert_items,
            total=len(alert_items),
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
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    
    officer_id = payload.officer_id if payload else "HSE-OFFICER-01"
    with SessionLocal() as db:
        alert = DatabaseService.acknowledge_alert(db, alert_id=alert_id, officer_id=officer_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert with ID '{alert_id}' was not found.",
            )
            
        return AlertItem(
            alert_id=alert.id,
            report_id=alert.report_id,
            title=alert.title,
            severity=alert.severity,
            message=alert.message,
            workflow_status=alert.workflow_status,
            acknowledged=alert.acknowledged,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            created_at=alert.created_at,
        )


@router.get(
    "/workflow/status/{report_id}",
    response_model=WorkflowStatusResponse,
    summary="Get Report Workflow Status",
    description="Retrieve automated HSE workflow lifecycle status, timestamps, and active alerts for a safety report.",
)
def get_workflow_status(report_id: str) -> WorkflowStatusResponse:
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    from app.services.workflow_service import WorkflowStatus
    import json
    
    with SessionLocal() as db:
        res = DatabaseService.get_decision_result(db, report_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' was not found in the repository.",
            )
            
        alerts = DatabaseService.get_alerts(db, limit=100)
        report_alerts = []
        for a in alerts:
            if a.report_id == report_id:
                report_alerts.append(AlertItem(
                    alert_id=a.id,
                    report_id=a.report_id,
                    title=a.title,
                    severity=a.severity,
                    message=a.message,
                    workflow_status=a.workflow_status,
                    acknowledged=a.acknowledged,
                    acknowledged_at=a.acknowledged_at,
                    acknowledged_by=a.acknowledged_by,
                    created_at=a.created_at,
                ))

        audit_logs = []
        for log in res.audit_trail:
            audit_logs.append(AuditLogItem(
                id=log.get("id"),
                action=log.get("action", "UNKNOWN"),
                entity_type=log.get("entity_type", "report"),
                entity_id=log.get("entity_id", report_id),
                actor_id=log.get("actor_id", "system"),
                details=log.get("details", {}),
                created_at=log.get("created_at") or res.reviewed_at or datetime.now(),
            ))

        final_p = res.final_priority or res.priority
        priority_str = final_p.value if hasattr(final_p, "value") else str(final_p)

        return WorkflowStatusResponse(
            report_id=res.report_id,
            priority=priority_str,
            workflow_status=res.workflow_status,
            in_review_queue=res.in_review_queue,
            queue_entered_at=res.queue_entered_at,
            workflow_updated_at=res.queue_entered_at or datetime.now(), # fallback
            display_badge=WorkflowStatus.get_display_badge(res.workflow_status),
            active_alerts=report_alerts,
            audit_trail=audit_logs,
        )


# ---------------------------------------------------------------------------
# Demo Mode Routes (Phase 16)
# ---------------------------------------------------------------------------
from app.api.v1.demo import router as demo_router
router.include_router(demo_router)

# ---------------------------------------------------------------------------
# Action Center Routes (Phase 16)
# ---------------------------------------------------------------------------
from app.api.routes.actions import router as actions_router
router.include_router(actions_router, prefix="/actions", tags=["actions"])


