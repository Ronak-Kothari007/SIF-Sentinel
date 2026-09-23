"""
SIF Sentinel — Database Persistence Service (Phase 9)
=====================================================

Encapsulates all database persistence operations:
  - creating and saving reports
  - persisting predictions, extracted entities, and triggered rules
  - recording HSE review decisions
  - managing user feedback
  - writing audit log entries
"""

from __future__ import annotations

import json
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.db.models import (
    AlertEvent,
    AuditLog,
    Entity,
    Feedback,
    HSEReview,
    Prediction,
    Report,
    RiskPattern,
    TriggeredRule,
    User,
)
from app.schemas.decision import DecisionResult


class DatabaseService:
    """Service layer managing SQLAlchemy transactions across all 9 tables."""

    @staticmethod
    def create_report(
        db: Session,
        report_id: str,
        report_text: str,
        location: str = "Unknown",
        report_type: str = "near_miss",
        severity_self_rated: str = "medium",
        source: str = "synthetic",
        submitted_by_user_id: Optional[str] = None,
    ) -> Report:
        # Idempotent: return/update existing report if ID already present
        existing = db.query(Report).filter(Report.id == report_id).first()
        if existing:
            existing.report_text = report_text
            existing.location = location
            db.commit()
            db.refresh(existing)
            return existing

        report = Report(
            id=report_id,
            report_text=report_text,
            location=location,
            report_type=report_type,
            severity_self_rated=severity_self_rated,
            source=source,
            submitted_by_user_id=submitted_by_user_id,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def save_analysis(
        db: Session,
        report_id: str,
        analysis: DecisionResult,
        actor_id: str = "system",
    ) -> Prediction:
        """
        Persist prediction result, extracted entities, triggered rules, and audit log.
        """
        # Clean up any existing prediction/rules for idempotent re-analysis
        existing_pred = db.query(Prediction).filter(Prediction.report_id == report_id).first()
        if existing_pred:
            db.delete(existing_pred)
            db.query(TriggeredRule).filter(TriggeredRule.report_id == report_id).delete()
            db.commit()

        # 1. Create Prediction
        factor_scores_dict = analysis.factor_scores.model_dump() if analysis.factor_scores else None
        pred = Prediction(
            report_id=report_id,
            sif_probability=analysis.sif_probability,
            priority=analysis.priority.value,
            priority_score=analysis.priority_score,
            activity=analysis.activity,
            hazard=analysis.hazard,
            barrier=analysis.barrier,
            barrier_status=analysis.barrier_status,
            model_name="DistilBERT",
            explanation=analysis.explanation,
            escalated=analysis.escalated,
            escalation_reason=analysis.escalation_reason,
            factor_scores_json=json.dumps(factor_scores_dict) if factor_scores_dict else None,
            governance_notice=analysis.governance_notice,
        )
        db.add(pred)

        # 2. Persist Triggered Rules
        for r in analysis.triggered_rules:
            tr = TriggeredRule(
                report_id=report_id,
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                category=r.category,
                severity=r.severity,
                severity_label=r.severity_label,
                explanation=r.explanation or "",
                triggered_signals_json=json.dumps(analysis.evidence),
            )
            db.add(tr)

        # 3. Create Audit Log
        audit = AuditLog(
            action="ANALYZE_REPORT",
            entity_type="report",
            entity_id=report_id,
            actor_id=actor_id,
            details_json=json.dumps({
                "priority": analysis.priority.value,
                "sif_probability": analysis.sif_probability,
                "rules_fired": len(analysis.triggered_rules),
            }),
        )
        db.add(audit)

        db.commit()
        db.refresh(pred)
        return pred

    @staticmethod
    def save_entities(
        db: Session,
        report_id: str,
        entities: list[Any],
    ) -> list[Entity]:
        """Persist individual entity spans identified in the report."""
        persisted = []
        for e in entities:
            ent = Entity(
                report_id=report_id,
                entity_type=e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
                surface_text=e.text,
                normalized_value=e.normalized_value,
                start_char=e.start_char,
                end_char=e.end_char,
                confidence=e.confidence,
                status=e.status,
                category=e.category,
                source=e.source,
            )
            db.add(ent)
            persisted.append(ent)
        db.commit()
        return persisted

    @staticmethod
    def get_report_with_analysis(
        db: Session,
        report_id: str,
    ) -> Optional[dict[str, Any]]:
        """Retrieve complete consolidated report, analysis, and reviews from database."""
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return None

        latest_prediction = (
            db.query(Prediction)
            .filter(Prediction.report_id == report_id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        rules = db.query(TriggeredRule).filter(TriggeredRule.report_id == report_id).all()
        entities = db.query(Entity).filter(Entity.report_id == report_id).all()
        reviews = db.query(HSEReview).filter(HSEReview.report_id == report_id).all()

        return {
            "report": report,
            "prediction": latest_prediction,
            "rules": rules,
            "entities": entities,
            "reviews": reviews,
        }

    @staticmethod
    def save_hse_review(
        db: Session,
        report_id: str,
        reviewer_id: str,
        decision: str,
        original_priority: str,
        final_priority: str,
        comments: Optional[str] = None,
        original_activity: Optional[str] = None,
        original_hazard: Optional[str] = None,
        original_barrier: Optional[str] = None,
        original_sif_probability: Optional[float] = None,
        corrected_activity: Optional[str] = None,
        corrected_hazard: Optional[str] = None,
        corrected_barrier: Optional[str] = None,
    ) -> HSEReview:
        """Record an HSE officer review and append to audit log without overwriting original AI output."""
        review = HSEReview(
            report_id=report_id,
            reviewer_id=reviewer_id,
            decision=decision,
            original_priority=original_priority,
            original_activity=original_activity,
            original_hazard=original_hazard,
            original_barrier=original_barrier,
            original_sif_probability=original_sif_probability,
            final_priority=final_priority,
            corrected_activity=corrected_activity,
            corrected_hazard=corrected_hazard,
            corrected_barrier=corrected_barrier,
            comments=comments,
        )
        db.add(review)

        # Audit log entry with full before/after snapshot
        audit_details = {
            "action": "HSE_REVIEW",
            "decision": decision,
            "reviewer_id": reviewer_id,
            "original_ai_output": {
                "priority": original_priority,
                "activity": original_activity,
                "hazard": original_hazard,
                "barrier": original_barrier,
                "sif_probability": original_sif_probability,
            },
            "final_determination": {
                "priority": final_priority,
                "activity": corrected_activity or original_activity,
                "hazard": corrected_hazard or original_hazard,
                "barrier": corrected_barrier or original_barrier,
            },
            "corrected_values": {
                "priority": final_priority if decision == "corrected" else None,
                "activity": corrected_activity,
                "hazard": corrected_hazard,
                "barrier": corrected_barrier,
            } if decision == "corrected" else None,
            "comments": comments,
        }

        audit = AuditLog(
            action="HSE_REVIEW",
            entity_type="hse_review",
            entity_id=report_id,
            actor_id=reviewer_id,
            details_json=json.dumps(audit_details),
        )
        db.add(audit)

        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def save_feedback(
        db: Session,
        report_id: str,
        user_id: Optional[str],
        feedback_type: str,
        notes: str,
        user_suggested_priority: Optional[str] = None,
    ) -> Feedback:
        """Store model feedback submitted by site officers and record audit entry."""
        fb = Feedback(
            report_id=report_id,
            user_id=user_id,
            feedback_type=feedback_type,
            user_suggested_priority=user_suggested_priority,
            notes=notes,
        )
        db.add(fb)

        # Audit log entry
        audit = AuditLog(
            action="FEEDBACK_SUBMITTED",
            entity_type="feedback",
            entity_id=report_id,
            actor_id=user_id or "anonymous_hse_user",
            details_json=json.dumps({
                "feedback_type": feedback_type,
                "user_suggested_priority": user_suggested_priority,
                "notes": notes,
            }),
        )
        db.add(audit)

        db.commit()
        db.refresh(fb)
        return fb

    @staticmethod
    def get_audit_trail_for_report(db: Session, report_id: str) -> list[AuditLog]:
        """Fetch chronological audit trail for a specific report."""
        return (
            db.query(AuditLog)
            .filter(AuditLog.entity_id == report_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

    @staticmethod
    def get_feedback_for_report(db: Session, report_id: str) -> list[Feedback]:
        """Fetch all feedback submitted for a report."""
        return (
            db.query(Feedback)
            .filter(Feedback.report_id == report_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )

    @staticmethod
    def record_audit_log(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Create a generic audit log entry."""
        audit = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            details_json=json.dumps(details) if details else None,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    @staticmethod
    def create_alert_event(
        db: Session,
        report_id: str,
        title: str,
        severity: str = "HIGH",
        message: str = "",
        workflow_status: str = "HSE_REVIEW_REQUIRED",
    ) -> AlertEvent:
        """Create and persist an internal alert event (e.g. HIGH priority escalation)."""
        alert = AlertEvent(
            report_id=report_id,
            title=title,
            severity=severity,
            message=message,
            workflow_status=workflow_status,
            acknowledged=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def get_alerts(
        db: Session,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
    ) -> list[AlertEvent]:
        """Fetch alert events ordered by creation timestamp."""
        query = db.query(AlertEvent)
        if acknowledged is not None:
            query = query.filter(AlertEvent.acknowledged == acknowledged)
        return query.order_by(AlertEvent.created_at.desc()).limit(limit).all()

    @staticmethod
    def acknowledge_alert(
        db: Session,
        alert_id: str,
        officer_id: str = "HSE-OFFICER",
    ) -> Optional[AlertEvent]:
        """Mark an alert as acknowledged by an HSE officer."""
        from datetime import datetime, timezone
        alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
        if not alert:
            return None
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = officer_id
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_report_alerts(
        db: Session,
        report_id: str,
        resolved_status: str = "RESOLVED",
    ) -> list[AlertEvent]:
        """Mark all alerts for a report as resolved following review."""
        alerts = db.query(AlertEvent).filter(AlertEvent.report_id == report_id).all()
        for a in alerts:
            a.workflow_status = resolved_status
            a.acknowledged = True
        db.commit()
        return alerts

    @staticmethod
    def update_report_workflow(
        db: Session,
        report_id: str,
        workflow_status: str,
        in_review_queue: bool,
        queue_entered_at: Optional[Any] = None,
    ) -> Optional[Report]:
        """Update workflow status and review queue status of a report."""
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return None
        report.workflow_status = workflow_status
        report.in_review_queue = in_review_queue
        if queue_entered_at is not None:
            report.queue_entered_at = queue_entered_at
        db.commit()
        db.refresh(report)
        return report
