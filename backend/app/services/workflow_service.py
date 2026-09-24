"""
SIF Sentinel — Automated HSE Workflow Service (Phase 13)
=========================================================

Implements deterministic, automated HSE review workflows:
When an analysis produces HIGH priority:
  1. Saves the report
  2. Marks it HIGH priority
  3. Places it in the HSE review queue (in_review_queue=True, queue_entered_at=now)
  4. Creates an internal alert/event ("HIGH PRIORITY → HSE REVIEW REQUIRED")
  5. Records the escalation event in audit_logs (action="ALERT_TRIGGERED", actor="SIF_SENTINEL_AUTOMATION")

Also handles workflow resolution when an HSE officer confirms, corrects, or rejects
a report, transitioning the workflow state and resolving active alerts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.schemas.api_v1 import AlertItem
from app.schemas.decision import DecisionResult, PriorityLevel

logger = logging.getLogger(__name__)


class WorkflowStatus:
    """Canonical HSE workflow lifecycle states."""

    HSE_REVIEW_REQUIRED = "HSE_REVIEW_REQUIRED"
    ROUTINE_MONITORING = "ROUTINE_MONITORING"
    CONTROLLED = "CONTROLLED"
    REVIEWED_CONFIRMED = "REVIEWED_CONFIRMED"
    REVIEWED_CORRECTED = "REVIEWED_CORRECTED"
    REVIEWED_REJECTED = "REVIEWED_REJECTED"

    DISPLAY_BADGES = {
        HSE_REVIEW_REQUIRED: "HIGH PRIORITY → HSE REVIEW REQUIRED",
        ROUTINE_MONITORING: "MEDIUM PRIORITY → ROUTINE MONITORING",
        CONTROLLED: "LOW PRIORITY → CONTROLLED",
        REVIEWED_CONFIRMED: "REVIEWED & CONFIRMED BY HSE",
        REVIEWED_CORRECTED: "REVIEWED & CORRECTED BY HSE",
        REVIEWED_REJECTED: "DE-ESCALATED / REJECTED BY HSE",
    }

    @classmethod
    def get_display_badge(cls, status: str) -> str:
        return cls.DISPLAY_BADGES.get(status, status)


class AutomatedHSEWorkflow:
    """Deterministic orchestrator for automated safety triage and escalations."""

    @staticmethod
    def process_analysis_workflow(
        stored_report: Any,
        analysis: DecisionResult,
        repo: Any,
        db: Optional[Any] = None,
    ) -> Optional[AlertItem]:
        """
        Execute automated workflow rules based on analysis priority.
        If HIGH priority, triggers the 5-step automated escalation sequence.
        """
        now = datetime.now(timezone.utc)
        is_high = (
            analysis.priority == PriorityLevel.HIGH
            or str(analysis.priority).upper() == "HIGH"
        )

        if is_high:
            # Step 1 & 2: Save report & mark it HIGH priority
            stored_report.final_priority = PriorityLevel.HIGH
            stored_report.workflow_status = WorkflowStatus.HSE_REVIEW_REQUIRED
            stored_report.workflow_updated_at = now

            # Step 3: Place it in the HSE review queue
            stored_report.in_review_queue = True
            stored_report.queue_entered_at = now

            # Sync analysis response object
            analysis.workflow_status = WorkflowStatus.HSE_REVIEW_REQUIRED
            analysis.in_review_queue = True
            analysis.queue_entered_at = now
            analysis.alert_triggered = True

            # Step 4: Create internal alert/event
            alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
            title = "HIGH PRIORITY → HSE REVIEW REQUIRED"
            message = (
                f"Automated SIF Triage: Report {stored_report.report_id} classified as HIGH priority "
                f"({analysis.sif_probability * 100:.1f}% SIF probability). "
                f"Hazard: {analysis.hazard or 'Unspecified'}. "
                f"Barrier: {analysis.barrier or 'Unspecified'} ({analysis.barrier_status or 'Unknown'}). "
                f"Immediate HSE officer verification required."
            )

            alert_item = AlertItem(
                alert_id=alert_id,
                report_id=stored_report.report_id,
                title=title,
                severity="HIGH",
                message=message,
                workflow_status=WorkflowStatus.HSE_REVIEW_REQUIRED,
                acknowledged=False,
                created_at=now,
                report_text_snippet=stored_report.report_text[:120],
                hazard=analysis.hazard,
                barrier=analysis.barrier,
                sif_probability=analysis.sif_probability,
            )

            # Persist alert in memory repository
            repo.create_alert(alert_item)

            # Step 5: Record the event in audit_logs
            audit_details = {
                "workflow_status": WorkflowStatus.HSE_REVIEW_REQUIRED,
                "alert_id": alert_id,
                "alert_title": title,
                "priority": "HIGH",
                "sif_probability": analysis.sif_probability,
                "hazard": analysis.hazard,
                "barrier": analysis.barrier,
                "barrier_status": analysis.barrier_status,
                "triggered_rules": [r.rule_id for r in analysis.triggered_rules],
                "queue_entered_at": now.isoformat(),
            }

            audit_entry = {
                "action": "ALERT_TRIGGERED",
                "entity_type": "report",
                "entity_id": stored_report.report_id,
                "actor_id": "SIF_SENTINEL_AUTOMATION",
                "details": audit_details,
                "created_at": now.isoformat(),
            }
            stored_report.audit_logs.append(audit_entry)

            # Persist to database if db session provided
            if db is not None:
                try:
                    from app.services.db_service import DatabaseService
                    DatabaseService.create_alert_event(
                        db=db,
                        report_id=stored_report.report_id,
                        title=title,
                        severity="HIGH",
                        message=message,
                        workflow_status=WorkflowStatus.HSE_REVIEW_REQUIRED,
                    )
                    DatabaseService.update_report_workflow(
                        db=db,
                        report_id=stored_report.report_id,
                        workflow_status=WorkflowStatus.HSE_REVIEW_REQUIRED,
                        in_review_queue=True,
                        queue_entered_at=now,
                    )
                    DatabaseService.record_audit_log(
                        db=db,
                        action="ALERT_TRIGGERED",
                        entity_type="report",
                        entity_id=stored_report.report_id,
                        actor_id="SIF_SENTINEL_AUTOMATION",
                        details=audit_details,
                    )
                except Exception as e:
                    logger.warning("Database alert persistence notice: %s", e)

            logger.info("Automated HSE workflow triggered for report %s: %s", stored_report.report_id, title)
            return alert_item

        elif analysis.priority == PriorityLevel.MEDIUM or str(analysis.priority).upper() == "MEDIUM":
            stored_report.workflow_status = WorkflowStatus.ROUTINE_MONITORING
            stored_report.in_review_queue = False
            stored_report.queue_entered_at = None
            stored_report.workflow_updated_at = now
            analysis.workflow_status = WorkflowStatus.ROUTINE_MONITORING
            analysis.in_review_queue = False
            analysis.alert_triggered = False

            if db is not None:
                try:
                    from app.services.db_service import DatabaseService
                    DatabaseService.update_report_workflow(
                        db=db,
                        report_id=stored_report.report_id,
                        workflow_status=WorkflowStatus.ROUTINE_MONITORING,
                        in_review_queue=False,
                    )
                except Exception as e:
                    logger.warning("DB workflow update notice: %s", e)
            return None

        else:
            stored_report.workflow_status = WorkflowStatus.CONTROLLED
            stored_report.in_review_queue = False
            stored_report.queue_entered_at = None
            stored_report.workflow_updated_at = now
            analysis.workflow_status = WorkflowStatus.CONTROLLED
            analysis.in_review_queue = False
            analysis.alert_triggered = False

            if db is not None:
                try:
                    from app.services.db_service import DatabaseService
                    DatabaseService.update_report_workflow(
                        db=db,
                        report_id=stored_report.report_id,
                        workflow_status=WorkflowStatus.CONTROLLED,
                        in_review_queue=False,
                    )
                except Exception as e:
                    logger.warning("DB workflow update notice: %s", e)
            return None

    @staticmethod
    def process_review_resolution(
        stored_report: Any,
        decision: str,
        reviewer_id: str,
        comments: Optional[str],
        repo: Any,
        db: Optional[Any] = None,
    ) -> str:
        """
        Transition workflow status and resolve active alerts upon HSE review completion.
        """
        now = datetime.now(timezone.utc)
        decision_norm = decision.lower()

        if decision_norm == "confirmed":
            new_status = WorkflowStatus.REVIEWED_CONFIRMED
        elif decision_norm == "corrected":
            new_status = WorkflowStatus.REVIEWED_CORRECTED
        elif decision_norm == "rejected":
            new_status = WorkflowStatus.REVIEWED_REJECTED
        else:
            new_status = f"REVIEWED_{decision.upper()}"

        stored_report.workflow_status = new_status
        stored_report.in_review_queue = False
        stored_report.workflow_updated_at = now

        # Resolve in-memory alerts
        repo.resolve_alerts_for_report(stored_report.report_id, resolved_status=new_status)

        # Audit log entry for workflow transition
        audit_details = {
            "previous_status": stored_report.workflow_status,
            "new_status": new_status,
            "decision": decision.upper(),
            "reviewer_id": reviewer_id,
            "comments": comments or "",
            "resolved_at": now.isoformat(),
        }

        stored_report.audit_logs.append({
            "action": "WORKFLOW_TRANSITION",
            "entity_type": "report",
            "entity_id": stored_report.report_id,
            "actor_id": reviewer_id,
            "details": audit_details,
            "created_at": now.isoformat(),
        })

        if db is not None:
            try:
                from app.services.db_service import DatabaseService
                DatabaseService.update_report_workflow(
                    db=db,
                    report_id=stored_report.report_id,
                    workflow_status=new_status,
                    in_review_queue=False,
                )
                DatabaseService.resolve_report_alerts(
                    db=db,
                    report_id=stored_report.report_id,
                    resolved_status=new_status,
                )
                DatabaseService.record_audit_log(
                    db=db,
                    action="WORKFLOW_TRANSITION",
                    entity_type="report",
                    entity_id=stored_report.report_id,
                    actor_id=reviewer_id,
                    details=audit_details,
                )
                
                # Phase 16: Auto-create Action if HIGH/CRITICAL priority and confirmed/corrected
                fp = stored_report.final_priority
                fp_str = fp.value if hasattr(fp, "value") else str(fp)
                is_high_risk = fp_str.upper() in ("HIGH", "CRITICAL")
                if is_high_risk and decision_norm in ("confirmed", "corrected"):
                    barrier_text = getattr(stored_report, 'final_barrier', None) or getattr(stored_report.analysis, 'barrier', None) or 'critical controls'
                    hazard_text = getattr(stored_report, 'final_hazard', None) or getattr(stored_report.analysis, 'hazard', None) or 'identified hazard'
                    location_text = getattr(stored_report, 'location', None) or getattr(stored_report.analysis, 'location', 'Unknown') if hasattr(stored_report, 'analysis') else 'Unknown'
                    action_title = f"Investigate and verify {barrier_text} controls for {hazard_text}"
                    try:
                        repo.create_action(
                            report_id=stored_report.report_id,
                            title=action_title,
                            priority=fp_str,
                            site_location=location_text,
                            assigned_to=None
                        )
                    except Exception as act_e:
                        logger.warning("Failed to create in-memory action: %s", act_e)
                    try:
                        DatabaseService.create_action(
                            db=db,
                            report_id=stored_report.report_id,
                            title=action_title,
                            priority=fp_str,
                            site_location=location_text,
                            assigned_to=None
                        )
                        logger.info("Auto-created action for report %s after HSE review (%s)", stored_report.report_id, decision_norm)
                    except Exception as act_e:
                        logger.warning("Failed to auto-create DB action: %s", act_e)

            except Exception as e:
                logger.warning("DB workflow resolution notice: %s", e)

        else:
            # InMemory only (no DB)
            fp = stored_report.final_priority
            fp_str = fp.value if hasattr(fp, "value") else str(fp)
            is_high_risk = fp_str.upper() in ("HIGH", "CRITICAL")
            if is_high_risk and decision_norm in ("confirmed", "corrected"):
                barrier_text = getattr(stored_report, 'final_barrier', None) or 'critical controls'
                hazard_text = getattr(stored_report, 'final_hazard', None) or 'identified hazard'
                action_title = f"Investigate and verify {barrier_text} controls for {hazard_text}"
                try:
                    repo.create_action(
                        report_id=stored_report.report_id,
                        title=action_title,
                        priority=fp_str,
                        site_location=getattr(stored_report, 'location', 'Unknown'),
                        assigned_to=None
                    )
                except Exception as act_e:
                    logger.warning("Failed to auto-create action in memory: %s", act_e)

        return new_status

