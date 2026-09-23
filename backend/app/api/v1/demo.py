"""
SIF Sentinel — Controlled Demo Mode API Endpoints (Phase 16)
=============================================================

Provides one-click management for loading and resetting the 10 curated synthetic
demo safety reports through the REAL SIF Sentinel AI and rule pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.demo.scenarios import DEMO_SCENARIOS, DemoScenario
from app.schemas.decision import DecisionResult, PriorityLevel
from app.services.decision_engine import SIFDecisionEngine
from app.services.report_store import StoredReport, get_repository

logger = logging.getLogger("sif_sentinel.demo")

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

# Shared engine instance
_engine: Optional[SIFDecisionEngine] = None


def get_engine() -> SIFDecisionEngine:
    global _engine
    if _engine is None:
        _engine = SIFDecisionEngine()
    return _engine


class DemoStatusResponse(BaseModel):
    """Response detailing current demo dataset presence."""
    is_demo_loaded: bool
    demo_reports_count: int
    total_scenarios_available: int
    demo_categories: list[str]
    last_loaded: Optional[datetime] = None


class DemoLoadedReportItem(BaseModel):
    """Summary of a single demo scenario processed through live pipeline."""
    report_id: str
    title: str
    category: str
    priority: PriorityLevel
    sif_probability: float
    rules_triggered: list[str]
    has_hse_review: bool
    review_decision: Optional[str] = None


class DemoLoadResponse(BaseModel):
    """Response returned upon executing one-click demo ingestion."""
    status: str = "success"
    message: str
    total_loaded: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    rules_fired_count: int
    recurring_patterns_count: int
    items: list[DemoLoadedReportItem] = Field(default_factory=list)


class DemoResetResponse(BaseModel):
    """Response returned upon resetting demo records."""
    status: str = "success"
    message: str
    removed_count: int


@router.get(
    "/status",
    response_model=DemoStatusResponse,
    summary="Get Demo Mode Status",
    description="Check whether the controlled demo dataset is currently loaded in the system.",
)
def get_demo_status() -> DemoStatusResponse:
    repo = get_repository()
    demo_reports = [r for r in repo._reports.values() if r.report_id.startswith("DEMO-SYN-")]
    categories = sorted(list({s.category for s in DEMO_SCENARIOS}))

    return DemoStatusResponse(
        is_demo_loaded=len(demo_reports) > 0,
        demo_reports_count=len(demo_reports),
        total_scenarios_available=len(DEMO_SCENARIOS),
        demo_categories=categories,
        last_loaded=datetime.now(timezone.utc) if demo_reports else None,
    )


@router.post(
    "/load",
    response_model=DemoLoadResponse,
    status_code=status.HTTP_200_OK,
    summary="One-Click Load Demo Dataset",
    description=(
        "Executes the entire live AI, rule, vector similarity, and escalation pipeline "
        "across 10 curated synthetic safety reports. No fake predictions; all computed live."
    ),
)
def load_demo_dataset(
    reset_first: bool = Query(default=True, description="Clean existing demo records before reloading"),
) -> DemoLoadResponse:
    repo = get_repository()
    engine = get_engine()

    # 1. Reset existing demo records if requested
    if reset_first:
        _clean_demo_records(repo)

    logger.info("Starting controlled demo mode ingestion (%d scenarios)...", len(DEMO_SCENARIOS))

    high_count = 0
    med_count = 0
    low_count = 0
    total_rules = 0
    loaded_items: list[DemoLoadedReportItem] = []

    # Import DB & workflow services
    from app.db.session import SessionLocal
    from app.services.db_service import DatabaseService
    from app.services.workflow_service import AutomatedHSEWorkflow

    with SessionLocal() as db:
        for scenario in DEMO_SCENARIOS:
            # Automatic recurrence signal via Sentence Transformers
            try:
                rec_signal = repo.calculate_recurrence_signal(scenario.report_text)
            except Exception:
                rec_signal = 0.0

            # EVALUATE THROUGH REAL PIPELINE (ML + Rule Engine + Feature Extractor)
            result: DecisionResult = engine.evaluate(
                input_data=scenario.report_text,
                report_id=scenario.report_id,
                recurring_risk_signal=rec_signal,
            )
            result.location = scenario.location

            if result.priority == PriorityLevel.HIGH:
                high_count += 1
            elif result.priority == PriorityLevel.MEDIUM:
                med_count += 1
            else:
                low_count += 1

            total_rules += len(result.triggered_rules)

            # Store in Repository (with source="synthetic_demo")
            stored = StoredReport(
                report_id=result.report_id,
                report_text=scenario.report_text,
                analysis=result,
                final_priority=result.priority,
            )
            stored.location = scenario.location
            repo.save(stored)

            # Persist in Database
            try:
                DatabaseService.create_report(
                    db=db,
                    report_id=result.report_id,
                    report_text=scenario.report_text,
                    location=scenario.location,
                    source="synthetic_demo",
                )
                DatabaseService.save_analysis(
                    db=db,
                    report_id=result.report_id,
                    analysis=result,
                    actor_id="demo_loader",
                )

                # Trigger automated workflow (creates internal alert if HIGH)
                AutomatedHSEWorkflow.process_analysis_workflow(
                    stored_report=stored,
                    analysis=result,
                    repo=repo,
                    db=db,
                )
            except Exception as e:
                logger.warning("Demo DB persistence notice for %s: %s", scenario.report_id, e)

            # Pre-staged HSE review (demonstrates human-in-the-loop dual view)
            has_review = False
            review_dec = None
            if scenario.pre_staged_review:
                rev_cfg = scenario.pre_staged_review
                has_review = True
                review_dec = rev_cfg.get("decision", "confirmed")

                corr_p = None
                if rev_cfg.get("corrected_priority"):
                    corr_p = PriorityLevel(rev_cfg["corrected_priority"])

                updated = repo.add_review(
                    report_id=scenario.report_id,
                    reviewer_id=rev_cfg.get("reviewer_id", "HSE-LEAD-DEMO"),
                    decision=review_dec,
                    corrected_priority=corr_p,
                    corrected_activity=rev_cfg.get("corrected_activity"),
                    corrected_hazard=rev_cfg.get("corrected_hazard"),
                    corrected_barrier=rev_cfg.get("corrected_barrier"),
                    comments=rev_cfg.get("comments"),
                )

                if updated:
                    try:
                        DatabaseService.save_hse_review(
                            db=db,
                            report_id=scenario.report_id,
                            reviewer_id=rev_cfg.get("reviewer_id", "HSE-LEAD-DEMO"),
                            decision=review_dec,
                            original_priority=result.priority.value,
                            final_priority=updated.final_priority.value,
                            comments=rev_cfg.get("comments"),
                            original_activity=result.activity,
                            original_hazard=result.hazard,
                            original_barrier=result.barrier,
                            original_sif_probability=result.sif_probability,
                            corrected_activity=rev_cfg.get("corrected_activity"),
                            corrected_hazard=rev_cfg.get("corrected_hazard"),
                            corrected_barrier=rev_cfg.get("corrected_barrier"),
                        )
                        AutomatedHSEWorkflow.process_review_resolution(
                            stored_report=updated,
                            decision=review_dec,
                            reviewer_id=rev_cfg.get("reviewer_id", "HSE-LEAD-DEMO"),
                            comments=rev_cfg.get("comments"),
                            repo=repo,
                            db=db,
                        )
                    except Exception as e:
                        logger.warning("Demo review DB persistence notice for %s: %s", scenario.report_id, e)

            loaded_items.append(
                DemoLoadedReportItem(
                    report_id=scenario.report_id,
                    title=scenario.title,
                    category=scenario.category,
                    priority=result.priority,
                    sif_probability=result.sif_probability,
                    rules_triggered=[r.rule_name for r in result.triggered_rules],
                    has_hse_review=has_review,
                    review_decision=review_dec,
                )
            )

    # Patterns count
    patterns_summary = repo.get_patterns()
    recurring_count = len(patterns_summary.semantic_patterns) + len(patterns_summary.recurring_clusters)

    logger.info(
        "Controlled Demo Mode loaded: %d reports (HIGH: %d, MED: %d, LOW: %d, Rules: %d)",
        len(loaded_items),
        high_count,
        med_count,
        low_count,
        total_rules,
    )

    return DemoLoadResponse(
        status="success",
        message=(
            f"Successfully evaluated and loaded {len(loaded_items)} synthetic demo reports "
            f"through the live AI classifier, rule engine, and similarity pipeline."
        ),
        total_loaded=len(loaded_items),
        high_priority_count=high_count,
        medium_priority_count=med_count,
        low_priority_count=low_count,
        rules_fired_count=total_rules,
        recurring_patterns_count=recurring_count,
        items=loaded_items,
    )


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    summary="Reset Demo Dataset",
    description="Removes all demo records (prefixed with DEMO-SYN-) from the repository and database.",
)
def reset_demo_dataset() -> DemoResetResponse:
    repo = get_repository()
    removed = _clean_demo_records(repo)
    return DemoResetResponse(
        status="success",
        message=f"Cleaned {removed} demo records from active memory and database.",
        removed_count=removed,
    )


def _clean_demo_records(repo: Any) -> int:
    """Internal helper to safely purge DEMO-SYN-* records from both memory and SQL DB."""
    # 1. Clean in-memory repository
    demo_ids = [rid for rid in list(repo._reports.keys()) if rid.startswith("DEMO-SYN-")]
    for rid in demo_ids:
        repo._reports.pop(rid, None)
        # remove from similarity engine if indexed
        if hasattr(repo, "similarity_engine") and repo.similarity_engine is not None:
            try:
                repo.similarity_engine.remove_document(rid)
            except Exception:
                pass

    if hasattr(repo, "_alerts"):
        repo._alerts = {aid: a for aid, a in repo._alerts.items() if not a.report_id.startswith("DEMO-SYN-")}

    # 2. Clean SQL Database
    try:
        from app.db.session import SessionLocal
        from app.db.models import Report, Prediction, TriggeredRule, Entity, HSEReview, Feedback, AuditLog, AlertEvent
        with SessionLocal() as db:
            for rid in demo_ids:
                db.query(AlertEvent).filter(AlertEvent.report_id == rid).delete()
                db.query(HSEReview).filter(HSEReview.report_id == rid).delete()
                db.query(TriggeredRule).filter(TriggeredRule.report_id == rid).delete()
                db.query(Entity).filter(Entity.report_id == rid).delete()
                db.query(Prediction).filter(Prediction.report_id == rid).delete()
                db.query(Feedback).filter(Feedback.report_id == rid).delete()
                db.query(AuditLog).filter(AuditLog.entity_id == rid).delete()
                db.query(Report).filter(Report.id == rid).delete()
            db.commit()
    except Exception as e:
        logger.warning("Notice during demo DB cleanup: %s", e)

    return len(demo_ids)
