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
    SafetyAction,
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
            structured_explanation_json=analysis.structured_explanation.model_dump_json() if analysis.structured_explanation else None,
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
    def get_decision_result(db: Session, report_id: str) -> Optional[DecisionResult]:
        """Fetch report and construct the canonical DecisionResult structure."""
        from app.schemas.decision import DecisionResult, PriorityLevel, TriggeredRuleSummary, FactorScores
        data = DatabaseService.get_report_with_analysis(db, report_id)
        if not data:
            return None
            
        r = data["report"]
        pred = data["prediction"]
        rules = data["rules"]
        reviews = data["reviews"]
        
        if not pred:
            return None
            
        # Get latest review if any
        latest_review = sorted(reviews, key=lambda x: x.reviewed_at)[-1] if reviews else None
        
        # Build rules list
        triggered = []
        evidence = []
        for rule in rules:
            triggered.append(TriggeredRuleSummary(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                category=rule.category,
                severity=rule.severity,
                severity_label=rule.severity_label,
                explanation=rule.explanation
            ))
            if rule.triggered_signals_json:
                import json
                try:
                    signals = json.loads(rule.triggered_signals_json)
                    if isinstance(signals, list):
                        evidence.extend(signals)
                except json.JSONDecodeError:
                    pass
                    
        # Parse factor scores
        factor_scores = None
        if pred.factor_scores_json:
            import json
            try:
                fs_dict = json.loads(pred.factor_scores_json)
                factor_scores = FactorScores(**fs_dict)
            except json.JSONDecodeError:
                pass
                
        structured_explanation = None
        if hasattr(pred, "structured_explanation_json") and pred.structured_explanation_json:
            import json
            try:
                from app.schemas.decision import StructuredExplanation
                se_dict = json.loads(pred.structured_explanation_json)
                structured_explanation = StructuredExplanation(**se_dict)
            except Exception:
                pass
                
        # Build base DecisionResult
        result = DecisionResult(
            report_id=r.id,
            report_text=r.report_text,
            sif_probability=pred.sif_probability,
            priority=PriorityLevel(pred.priority),
            priority_score=pred.priority_score,
            activity=pred.activity,
            hazard=pred.hazard,
            barrier=pred.barrier,
            barrier_status=pred.barrier_status,
            triggered_rules=triggered,
            evidence=list(set(evidence)),
            explanation=pred.explanation,
            location=r.location,
            equipment=None,
            factor_scores=factor_scores,
            escalated=pred.escalated,
            escalation_reason=pred.escalation_reason,
            governance_notice=pred.governance_notice,
            workflow_status=r.workflow_status,
            in_review_queue=r.in_review_queue,
            queue_entered_at=r.queue_entered_at,
            alert_triggered=r.workflow_status == "HSE_REVIEW_REQUIRED",
            structured_explanation=structured_explanation
        )
        
        # Overlay review determinations
        if latest_review:
            result.hse_reviewed = True
            result.review_decision = latest_review.decision
            result.reviewer_id = latest_review.reviewer_id
            result.reviewed_at = latest_review.reviewed_at
            result.review_comments = latest_review.comments
            result.final_priority = PriorityLevel(latest_review.final_priority)
            
            if latest_review.decision == "corrected":
                result.corrected_priority = PriorityLevel(latest_review.final_priority)
                result.corrected_activity = latest_review.corrected_activity
                result.corrected_hazard = latest_review.corrected_hazard
                result.corrected_barrier = latest_review.corrected_barrier
                
                result.final_activity = latest_review.corrected_activity
                result.final_hazard = latest_review.corrected_hazard
                result.final_barrier = latest_review.corrected_barrier
            else:
                result.final_activity = pred.activity
                result.final_hazard = pred.hazard
                result.final_barrier = pred.barrier
        else:
            result.final_priority = PriorityLevel(pred.priority)
            result.final_activity = pred.activity
            result.final_hazard = pred.hazard
            result.final_barrier = pred.barrier
            
        # Attach audit trail
        logs = DatabaseService.get_audit_trail_for_report(db, r.id)
        result.audit_trail = [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "actor_id": log.actor_id,
                "details": json.loads(log.details_json) if log.details_json else {},
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
        
        # Attach feedback
        feedbacks = DatabaseService.get_feedback_for_report(db, r.id)
        result.feedback_items = [
            {
                "id": fb.id,
                "feedback_type": fb.feedback_type,
                "user_suggested_priority": fb.user_suggested_priority,
                "notes": fb.notes,
                "user_id": fb.user_id,
                "created_at": fb.created_at.isoformat(),
            }
            for fb in feedbacks
        ]
        
        return result

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

    @staticmethod
    def create_action(
        db: Session,
        report_id: str,
        title: str,
        priority: str = "HIGH",
        site_location: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> SafetyAction:
        """Create and persist a new trackable HSE action."""
        action = SafetyAction(
            report_id=report_id,
            title=title,
            priority=priority,
            status="Open",
            site_location=site_location,
            assigned_to=assigned_to,
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action

    @staticmethod
    def get_actions(db: Session, limit: int = 50) -> list[SafetyAction]:
        """Fetch all trackable HSE actions."""
        return db.query(SafetyAction).order_by(SafetyAction.created_at.desc()).limit(limit).all()

    @staticmethod
    def update_action_status(
        db: Session,
        action_id: str,
        status: str,
        assigned_to: Optional[str] = None,
    ) -> Optional[SafetyAction]:
        """Update the workflow status of an action."""
        action = db.query(SafetyAction).filter(SafetyAction.id == action_id).first()
        if not action:
            return None
        action.status = status
        if assigned_to is not None:
            action.assigned_to = assigned_to
        db.commit()
        db.refresh(action)
        return action

    @staticmethod
    def list_all(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        priority: Optional[str] = None,
        hazard: Optional[str] = None,
        activity: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query reports with filtering and pagination, mapped for ReportSummaryItem."""
        from sqlalchemy.orm import joinedload
        
        # We eagerly load prediction, hse_reviews, triggered_rules
        query = db.query(Report).options(
            joinedload(Report.predictions),
            joinedload(Report.hse_reviews),
            joinedload(Report.triggered_rules),
            joinedload(Report.alerts)
        )
        
        reports = query.all()
        
        mapped_items = []
        for r in reports:
            pred = r.predictions[0] if r.predictions else None
            review = r.hse_reviews[-1] if r.hse_reviews else None
            
            final_prio = review.final_priority if review else (pred.priority if pred else "LOW")
            final_act = review.corrected_activity if review and review.corrected_activity else (pred.activity if pred else None)
            final_haz = review.corrected_hazard if review and review.corrected_hazard else (pred.hazard if pred else None)
            final_bar = review.corrected_barrier if review and review.corrected_barrier else (pred.barrier if pred else None)
            
            # Apply filters manually for exact parity with in-memory store
            if priority and final_prio != priority:
                continue
            if hazard:
                if not final_haz or hazard.lower() not in final_haz.lower():
                    continue
            if activity:
                if not final_act or activity.lower() not in final_act.lower():
                    continue
                
            snippet = ""
            if pred and pred.explanation:
                snippet = pred.explanation[:120] + "..." if len(pred.explanation) > 120 else pred.explanation
                
            alert_triggered = r.workflow_status == "HSE_REVIEW_REQUIRED"
            
            mapped_items.append({
                "report_id": r.id,
                "report_text": r.report_text,
                "created_at": r.created_at,
                "priority": final_prio,
                "priority_score": pred.priority_score if pred else 0.0,
                "sif_probability": pred.sif_probability if pred else 0.0,
                "activity": final_act,
                "hazard": final_haz,
                "barrier": final_bar,
                "barrier_status": pred.barrier_status if pred else None,
                "location": r.location,
                "equipment": None,
                "triggered_rules_count": len(r.triggered_rules),
                "hse_reviewed": bool(review),
                "review_decision": review.decision if review else None,
                "reviewer_id": review.reviewer_id if review else None,
                "review_comments": review.comments if review else None,
                "ai_priority": pred.priority if pred else None,
                "ai_activity": pred.activity if pred else None,
                "ai_hazard": pred.hazard if pred else None,
                "ai_barrier": pred.barrier if pred else None,
                "final_priority": final_prio,
                "final_activity": final_act,
                "final_hazard": final_haz,
                "final_barrier": final_bar,
                "explanation_snippet": snippet,
                "workflow_status": r.workflow_status,
                "in_review_queue": r.in_review_queue,
                "queue_entered_at": r.queue_entered_at,
                "alert_triggered": alert_triggered,
            })
            
        # Sort descending by date and priority score
        mapped_items.sort(key=lambda x: (x["created_at"], x["priority_score"]), reverse=True)
        total = len(mapped_items)
        return mapped_items[offset : offset + limit], total

    @staticmethod
    def get_high_risk(db: Session, limit: int = 50) -> list[dict[str, Any]]:
        mapped_items, _ = DatabaseService.list_all(db, limit=1000, priority="HIGH")
        return mapped_items[:limit]

    @staticmethod
    def get_dashboard_summary(db: Session) -> dict[str, Any]:
        """Compute aggregate executive dashboard metrics natively."""
        mapped_items, total = DatabaseService.list_all(db, limit=10000)
        if total == 0:
            return {
                "total_reports": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "sif_precursor_rate": 0.0,
                "pending_reviews_count": 0,
                "completed_reviews_count": 0,
                "top_hazards": [],
                "top_activities": [],
                "top_barrier_failures": [],
                "ai_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "hse_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNREVIEWED": 0},
                "review_status": {"pending": 0, "confirmed": 0, "corrected": 0, "rejected": 0, "total_reviewed": 0},
                "agreement_rate": 100.0,
                "active_alerts": [],
                "unread_alerts_count": 0,
            }
            
        high_c = sum(1 for r in mapped_items if r["final_priority"] == "HIGH")
        med_c = sum(1 for r in mapped_items if r["final_priority"] == "MEDIUM")
        low_c = sum(1 for r in mapped_items if r["final_priority"] == "LOW")
        
        sif_flagged = sum(1 for r in mapped_items if r["sif_probability"] >= 0.50 or r["final_priority"] == "HIGH")
        sif_rate = round((sif_flagged / total) * 100, 1) if total > 0 else 0.0
        
        pending = sum(1 for r in mapped_items if not r["hse_reviewed"])
        completed = sum(1 for r in mapped_items if r["hse_reviewed"])
        
        ai_dist = {
            "HIGH": sum(1 for r in mapped_items if r["ai_priority"] == "HIGH"),
            "MEDIUM": sum(1 for r in mapped_items if r["ai_priority"] == "MEDIUM"),
            "LOW": sum(1 for r in mapped_items if r["ai_priority"] == "LOW"),
        }
        
        hse_dist = {
            "HIGH": sum(1 for r in mapped_items if r["hse_reviewed"] and r["final_priority"] == "HIGH"),
            "MEDIUM": sum(1 for r in mapped_items if r["hse_reviewed"] and r["final_priority"] == "MEDIUM"),
            "LOW": sum(1 for r in mapped_items if r["hse_reviewed"] and r["final_priority"] == "LOW"),
            "UNREVIEWED": pending,
        }
        
        rev_status = {
            "pending": pending,
            "confirmed": sum(1 for r in mapped_items if r["hse_reviewed"] and r["review_decision"] == "confirmed"),
            "corrected": sum(1 for r in mapped_items if r["hse_reviewed"] and r["review_decision"] == "corrected"),
            "rejected": sum(1 for r in mapped_items if r["hse_reviewed"] and r["review_decision"] == "rejected"),
            "total_reviewed": completed,
        }
        
        agreed = sum(1 for r in mapped_items if r["hse_reviewed"] and (r["review_decision"] == "confirmed" or r["final_priority"] == r["ai_priority"]))
        agreement_rate = round((agreed / completed) * 100, 1) if completed > 0 else 100.0
        
        active_alerts_models = DatabaseService.get_alerts(db, acknowledged=False, limit=5)
        active_alerts = [
            {
                "alert_id": a.id,
                "report_id": a.report_id,
                "title": a.title,
                "severity": a.severity,
                "message": a.message,
                "workflow_status": a.workflow_status,
                "acknowledged": a.acknowledged,
                "acknowledged_at": a.acknowledged_at,
                "acknowledged_by": a.acknowledged_by,
                "created_at": a.created_at,
            }
            for a in active_alerts_models
        ]
        unread_alerts_count = len(DatabaseService.get_alerts(db, acknowledged=False, limit=1000))
        
        patterns = DatabaseService.get_patterns(db)
        
        return {
            "total_reports": total,
            "high_priority_count": high_c,
            "medium_priority_count": med_c,
            "low_priority_count": low_c,
            "sif_precursor_rate": sif_rate,
            "pending_reviews_count": pending,
            "completed_reviews_count": completed,
            "top_hazards": patterns["top_hazards"],
            "top_activities": patterns["top_activities"],
            "top_barrier_failures": patterns["top_barrier_gaps"],
            "ai_distribution": ai_dist,
            "hse_distribution": hse_dist,
            "review_status": rev_status,
            "agreement_rate": agreement_rate,
            "active_alerts": active_alerts,
            "unread_alerts_count": unread_alerts_count,
        }

    @staticmethod
    def get_patterns(db: Session) -> dict[str, Any]:
        """Synthesize recurring hazard, activity, and barrier failure trends."""
        from collections import Counter
        mapped_items, total = DatabaseService.list_all(db, limit=10000)
        
        if total == 0:
            return {
                "total_analyzed": 0,
                "top_hazards": [],
                "top_activities": [],
                "top_barrier_gaps": [],
                "recurring_clusters": [],
                "summary": "No reports currently loaded."
            }
            
        hazards = [r["ai_hazard"] for r in mapped_items if r["ai_hazard"]]
        haz_counts = Counter(hazards).most_common(5)
        top_haz = [{"hazard": h, "count": c, "percentage": round((c / total) * 100, 1)} for h, c in haz_counts]
        
        activities = [r["ai_activity"] for r in mapped_items if r["ai_activity"]]
        act_counts = Counter(activities).most_common(5)
        top_act = [{"activity": a, "count": c, "percentage": round((c / total) * 100, 1)} for a, c in act_counts]
        
        gaps = [(r["ai_barrier"], r["barrier_status"]) for r in mapped_items if r["ai_barrier"] and r["barrier_status"] in ["Not Verified", "Absent", "Failed"]]
        gap_counts = Counter(gaps).most_common(5)
        top_gaps = [{"barrier": b, "barrier_status": s, "count": c} for (b, s), c in gap_counts]
        
        clusters = []
        for (bar, stat), count in gap_counts[:4]:
            matching_ids = [r["report_id"] for r in mapped_items if r["ai_barrier"] == bar and r["barrier_status"] == stat][:6]
            clusters.append({
                "cluster_name": f"{bar} — {stat}",
                "barrier": bar,
                "barrier_status": stat,
                "occurrences": count,
                "report_count": count,
                "risk_band": "HIGH" if stat in ["Not Verified", "Failed"] else "MEDIUM",
                "recommendation": f"Perform site-wide audit on {bar} verification procedures and defense compliance.",
                "sample_report_ids": matching_ids,
            })
            
        summary = (
            f"Analysis of {total} safety observations indicates prominent risk clusters in "
            f"{top_haz[0]['hazard'] if top_haz else 'high-energy operations'} and "
            f"{top_gaps[0]['barrier'] if top_gaps else 'control verification'}."
        )
        
        return {
            "total_analyzed": total,
            "top_hazards": top_haz,
            "top_activities": top_act,
            "top_barrier_gaps": top_gaps,
            "recurring_clusters": clusters,
            "summary": summary
        }
