"""
SIF Sentinel — Report Repository & Data Store (Phase 8)
=======================================================

Provides a thread-safe, in-memory repository for storing analyzed reports,
retrieving reports by ID and filter, managing the HSE review queue, and
computing pattern/dashboard analytics.

Pre-seeds from synthetic datasets on startup for immediate local prototyping.
"""

from __future__ import annotations

import csv
import threading
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import Any, Optional

from app.schemas.api_v1 import (
    ActivityCount,
    AlertItem,
    AuditLogItem,
    BarrierGapItem,
    DashboardSummaryResponse,
    HazardCount,
    PatternAnalysisResponse,
    PriorityDistribution,
    ReportSummaryItem,
    ReviewStatusCounts,
    SemanticRecurringPattern,
    SimilarReportItem,
)
from app.schemas.decision import DecisionResult, PriorityLevel
from app.services.decision_engine import SIFDecisionEngine
from app.services.similarity_engine import RecurringRiskEngine, get_similarity_engine
from app.services.workflow_service import AutomatedHSEWorkflow, WorkflowStatus


@dataclass
class StoredReport:
    """Internal model for an analyzed safety report."""

    report_id: str
    report_text: str
    analysis: DecisionResult  # NEVER OVERWRITTEN - original AI output
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hse_reviewed: bool = False
    review_decision: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None
    final_priority: PriorityLevel = PriorityLevel.LOW
    final_activity: Optional[str] = None
    final_hazard: Optional[str] = None
    final_barrier: Optional[str] = None
    corrected_priority: Optional[PriorityLevel] = None
    corrected_activity: Optional[str] = None
    corrected_hazard: Optional[str] = None
    corrected_barrier: Optional[str] = None
    audit_logs: list[dict[str, Any]] = field(default_factory=list)
    feedback_items: list[dict[str, Any]] = field(default_factory=list)
    workflow_status: str = "PENDING"
    in_review_queue: bool = False
    queue_entered_at: Optional[datetime] = None
    workflow_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.final_priority and self.analysis:
            self.final_priority = self.analysis.priority
        if not self.final_activity and self.analysis:
            self.final_activity = self.analysis.activity
        if not self.final_hazard and self.analysis:
            self.final_hazard = self.analysis.hazard
        if not self.final_barrier and self.analysis:
            self.final_barrier = self.analysis.barrier
        # Initialize audit trail with creation/analysis log if empty
        if not self.audit_logs:
            self.audit_logs.append({
                "action": "ANALYZE_REPORT",
                "entity_type": "report",
                "entity_id": self.report_id,
                "actor_id": "SIF_SENTINEL_AI",
                "details": {
                    "priority": self.analysis.priority.value if hasattr(self.analysis.priority, "value") else str(self.analysis.priority),
                    "sif_probability": self.analysis.sif_probability,
                    "activity": self.analysis.activity,
                    "hazard": self.analysis.hazard,
                    "barrier": self.analysis.barrier,
                },
                "created_at": self.created_at.isoformat() if hasattr(self.created_at, "isoformat") else str(self.created_at),
            })

    def to_summary_item(self) -> ReportSummaryItem:
        """Project to API list summary item."""
        snippet = (
            self.analysis.explanation[:120] + "..."
            if len(self.analysis.explanation) > 120
            else self.analysis.explanation
        )
        return ReportSummaryItem(
            report_id=self.report_id,
            report_text=self.report_text,
            created_at=self.created_at,
            priority=self.final_priority or self.analysis.priority,
            priority_score=self.analysis.priority_score,
            sif_probability=self.analysis.sif_probability,
            activity=self.final_activity or self.analysis.activity,
            hazard=self.final_hazard or self.analysis.hazard,
            barrier=self.final_barrier or self.analysis.barrier,
            barrier_status=self.analysis.barrier_status,
            location=self.analysis.location,
            equipment=self.analysis.equipment,
            triggered_rules_count=len(self.analysis.triggered_rules),
            hse_reviewed=self.hse_reviewed,
            review_decision=self.review_decision,
            reviewer_id=self.reviewer_id,
            review_comments=self.review_comments,
            ai_priority=self.analysis.priority,
            ai_activity=self.analysis.activity,
            ai_hazard=self.analysis.hazard,
            ai_barrier=self.analysis.barrier,
            final_priority=self.final_priority or self.analysis.priority,
            final_activity=self.final_activity or self.analysis.activity,
            final_hazard=self.final_hazard or self.analysis.hazard,
            final_barrier=self.final_barrier or self.analysis.barrier,
            explanation_snippet=snippet,
            workflow_status=self.workflow_status,
            in_review_queue=self.in_review_queue,
            queue_entered_at=self.queue_entered_at,
            alert_triggered=(self.workflow_status == WorkflowStatus.HSE_REVIEW_REQUIRED),
        )


class ReportRepository:
    """Thread-safe in-memory store for reports and HSE review actions."""

    def __init__(self, similarity_engine: Optional[RecurringRiskEngine] = None):
        self._lock = threading.RLock()
        self._reports: dict[str, StoredReport] = {}
        self._alerts: dict[str, AlertItem] = {}
        self._seeded = False
        self.similarity_engine = similarity_engine or get_similarity_engine()

    def create_alert(self, alert_item: AlertItem) -> AlertItem:
        """Store an internal alert event in the repository."""
        with self._lock:
            self._alerts[alert_item.alert_id] = alert_item
            return alert_item

    def get_alerts(
        self,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
    ) -> tuple[list[AlertItem], int, int]:
        """Fetch alert events, total count, and unacknowledged count."""
        with self._lock:
            all_alerts = sorted(
                self._alerts.values(),
                key=lambda a: a.created_at,
                reverse=True,
            )
            unacknowledged_count = sum(1 for a in all_alerts if not a.acknowledged)
            filtered = all_alerts
            if acknowledged is not None:
                filtered = [a for a in all_alerts if a.acknowledged == acknowledged]
            return filtered[:limit], len(all_alerts), unacknowledged_count

    def acknowledge_alert(
        self,
        alert_id: str,
        officer_id: str = "HSE-OFFICER-01",
        notes: Optional[str] = None,
    ) -> Optional[AlertItem]:
        """Mark an alert as acknowledged by an HSE officer."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = officer_id
            return alert

    def resolve_alerts_for_report(
        self,
        report_id: str,
        resolved_status: str = "RESOLVED",
    ) -> list[AlertItem]:
        """Mark all active alerts for a report as resolved following HSE review."""
        with self._lock:
            resolved = []
            for a in self._alerts.values():
                if a.report_id == report_id:
                    a.workflow_status = resolved_status
                    a.acknowledged = True
                    resolved.append(a)
            return resolved

    def save(self, stored_report: StoredReport) -> StoredReport:
        """Store or update an analyzed report and index its dense semantic embedding."""
        with self._lock:
            self._reports[stored_report.report_id] = stored_report
            # Automatically index embedding for semantic search and recurring pattern analysis
            try:
                self.similarity_engine.index_report(
                    stored_report.report_id, stored_report.report_text
                )
            except Exception as e:
                logger.warning("Semantic embedding indexing notice for %s: %s", stored_report.report_id, e)
            return stored_report

    def find_similar(
        self,
        report_id: str,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[SimilarReportItem]:
        """Find semantically similar reports using dense vector cosine similarity."""
        with self._lock:
            return self.similarity_engine.find_similar_reports(
                report_id=report_id,
                stored_reports=self._reports,
                limit=limit,
                threshold=threshold,
            )

    def calculate_recurrence_signal(self, text: str) -> float:
        """Calculate recurrence score against known high-risk precursor reports."""
        with self._lock:
            high_risk = self.get_high_risk()
            return self.similarity_engine.calculate_recurrence_signal(text, high_risk)

    def get(self, report_id: str) -> Optional[StoredReport]:
        """Fetch report by its unique ID."""
        with self._lock:
            return self._reports.get(report_id)

    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        priority: Optional[PriorityLevel] = None,
        hazard: Optional[str] = None,
        activity: Optional[str] = None,
    ) -> tuple[list[StoredReport], int]:
        """Query reports with filtering and pagination."""
        with self._lock:
            items = list(self._reports.values())

            # Apply filters
            if priority:
                items = [r for r in items if (r.final_priority or r.analysis.priority) == priority]
            if hazard:
                items = [r for r in items if r.analysis.hazard and hazard.lower() in r.analysis.hazard.lower()]
            if activity:
                items = [r for r in items if r.analysis.activity and activity.lower() in r.analysis.activity.lower()]

            # Sort descending by priority score and date
            sorted_items = sorted(
                items,
                key=lambda r: (r.analysis.priority_score, r.created_at),
                reverse=True,
            )

            total = len(sorted_items)
            paginated = sorted_items[offset : offset + limit]
            return paginated, total

    def get_high_risk(self, limit: int = 50) -> list[StoredReport]:
        """Retrieve all HIGH priority reports ordered by priority score."""
        with self._lock:
            high_risk = [
                r
                for r in self._reports.values()
                if (r.final_priority or r.analysis.priority) == PriorityLevel.HIGH
            ]
            sorted_high = sorted(high_risk, key=lambda r: r.analysis.priority_score, reverse=True)
            return sorted_high[:limit]

    def add_review(
        self,
        report_id: str,
        reviewer_id: str,
        decision: str,
        corrected_priority: Optional[PriorityLevel] = None,
        corrected_activity: Optional[str] = None,
        corrected_hazard: Optional[str] = None,
        corrected_barrier: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> Optional[StoredReport]:
        """Apply an HSE officer review decision without overwriting original AI output."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return None

            now = datetime.now(timezone.utc)
            report.hse_reviewed = True
            report.review_decision = decision
            report.reviewer_id = reviewer_id
            report.reviewed_at = now
            report.review_comments = comments

            # Original AI prediction in report.analysis is preserved (never overwritten!)
            if decision == "corrected":
                if corrected_priority:
                    report.final_priority = corrected_priority
                    report.corrected_priority = corrected_priority
                if corrected_activity:
                    report.final_activity = corrected_activity
                    report.corrected_activity = corrected_activity
                if corrected_hazard:
                    report.final_hazard = corrected_hazard
                    report.corrected_hazard = corrected_hazard
                if corrected_barrier:
                    report.final_barrier = corrected_barrier
                    report.corrected_barrier = corrected_barrier
            elif decision == "confirmed":
                report.final_priority = report.analysis.priority
                report.final_activity = report.analysis.activity
                report.final_hazard = report.analysis.hazard
                report.final_barrier = report.analysis.barrier
            elif decision == "rejected":
                report.final_priority = PriorityLevel.LOW

            # Record audit trail entry
            audit_entry = {
                "action": "HSE_REVIEW",
                "entity_type": "hse_review",
                "entity_id": report_id,
                "actor_id": reviewer_id,
                "details": {
                    "decision": decision,
                    "original_ai_output": {
                        "priority": report.analysis.priority.value if hasattr(report.analysis.priority, "value") else str(report.analysis.priority),
                        "activity": report.analysis.activity,
                        "hazard": report.analysis.hazard,
                        "barrier": report.analysis.barrier,
                        "sif_probability": report.analysis.sif_probability,
                    },
                    "final_determination": {
                        "priority": report.final_priority.value if hasattr(report.final_priority, "value") else str(report.final_priority),
                        "activity": report.final_activity,
                        "hazard": report.final_hazard,
                        "barrier": report.final_barrier,
                    },
                    "corrected_values": {
                        "priority": report.corrected_priority.value if hasattr(report.corrected_priority, "value") else str(report.corrected_priority) if report.corrected_priority else None,
                        "activity": report.corrected_activity,
                        "hazard": report.corrected_hazard,
                        "barrier": report.corrected_barrier,
                    } if decision == "corrected" else None,
                    "comments": comments,
                },
                "created_at": now.isoformat(),
            }
            report.audit_logs.append(audit_entry)
            # Phase 13: Transition workflow status and resolve active alerts
            AutomatedHSEWorkflow.process_review_resolution(
                stored_report=report,
                decision=decision,
                reviewer_id=reviewer_id,
                comments=comments,
                repo=self,
            )

            return report

    def add_feedback(
        self,
        report_id: str,
        feedback_type: str,
        notes: str,
        user_suggested_priority: Optional[PriorityLevel] = None,
        user_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Attach user feedback annotation to a report and record audit log."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return None

            now = datetime.now(timezone.utc)
            fb_entry = {
                "id": f"FB-{uuid.uuid4().hex[:8].upper()}",
                "report_id": report_id,
                "user_id": user_id,
                "feedback_type": feedback_type,
                "user_suggested_priority": user_suggested_priority,
                "notes": notes,
                "created_at": now,
            }
            report.feedback_items.append(fb_entry)

            # Audit log
            audit_entry = {
                "action": "FEEDBACK_SUBMITTED",
                "entity_type": "feedback",
                "entity_id": report_id,
                "actor_id": user_id or "anonymous_hse_user",
                "details": {
                    "feedback_type": feedback_type,
                    "user_suggested_priority": user_suggested_priority.value if hasattr(user_suggested_priority, "value") else str(user_suggested_priority) if user_suggested_priority else None,
                    "notes": notes,
                },
                "created_at": now.isoformat(),
            }
            report.audit_logs.append(audit_entry)
            return fb_entry

    def get_audit_trail(self, report_id: str) -> list[dict[str, Any]]:
        """Fetch audit log records for a report."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return []
            return list(report.audit_logs)

    def get_feedback(self, report_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Fetch feedback records optionally filtered by report_id."""
        with self._lock:
            if report_id:
                report = self._reports.get(report_id)
                return list(report.feedback_items) if report else []
            all_fb = []
            for r in self._reports.values():
                all_fb.extend(r.feedback_items)
            return sorted(all_fb, key=lambda x: x["created_at"], reverse=True)


    def get_patterns(self) -> PatternAnalysisResponse:
        """Synthesize recurring hazard, activity, and barrier failure trends."""
        with self._lock:
            reports = list(self._reports.values())
            total = len(reports)
            if total == 0:
                return PatternAnalysisResponse(
                    total_analyzed=0,
                    top_hazards=[],
                    top_activities=[],
                    top_barrier_gaps=[],
                    recurring_clusters=[],
                    summary="No reports currently loaded.",
                )

            # 1. Top Hazards
            hazards = [r.analysis.hazard for r in reports if r.analysis.hazard]
            haz_counts = Counter(hazards).most_common(5)
            top_haz = [
                HazardCount(hazard=h, count=c, percentage=round((c / total) * 100, 1))
                for h, c in haz_counts
            ]

            # 2. Top Activities
            activities = [r.analysis.activity for r in reports if r.analysis.activity]
            act_counts = Counter(activities).most_common(5)
            top_act = [
                ActivityCount(activity=a, count=c, percentage=round((c / total) * 100, 1))
                for a, c in act_counts
            ]

            # 3. Top Barrier Gaps
            gaps = [
                (r.analysis.barrier, r.analysis.barrier_status)
                for r in reports
                if r.analysis.barrier and r.analysis.barrier_status in ["Not Verified", "Absent", "Failed"]
            ]
            gap_counts = Counter(gaps).most_common(5)
            top_gaps = [
                BarrierGapItem(barrier=b, barrier_status=s, count=c) for (b, s), c in gap_counts
            ]

            # 4. Synthesize recurring clusters
            clusters = []
            for (bar, stat), count in gap_counts[:4]:
                matching_ids = [
                    r.report_id for r in reports
                    if r.analysis.barrier == bar and r.analysis.barrier_status == stat
                ][:6]
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
                f"{top_haz[0].hazard if top_haz else 'high-energy operations'} and "
                f"{top_gaps[0].barrier if top_gaps else 'control verification'}."
            )

            # 5. Detect semantic recurring patterns via Sentence Transformers
            try:
                semantic_patterns = self.similarity_engine.detect_recurring_patterns(
                    reports, similarity_threshold=0.60
                )
            except Exception as e:
                logger.warning("Semantic recurring pattern detection notice: %s", e)
                semantic_patterns = []

            return PatternAnalysisResponse(
                total_analyzed=total,
                top_hazards=top_haz,
                top_activities=top_act,
                top_barrier_gaps=top_gaps,
                recurring_clusters=clusters,
                semantic_patterns=semantic_patterns,
                summary=summary,
            )

    def get_dashboard_summary(self) -> DashboardSummaryResponse:
        """Compute aggregate executive dashboard metrics."""
        with self._lock:
            reports = list(self._reports.values())
            total = len(reports)
            if total == 0:
                return DashboardSummaryResponse(
                    total_reports=0,
                    high_priority_count=0,
                    medium_priority_count=0,
                    low_priority_count=0,
                    sif_precursor_rate=0.0,
                    pending_reviews_count=0,
                    completed_reviews_count=0,
                    top_hazards=[],
                    top_activities=[],
                    top_barrier_failures=[],
                    ai_distribution=PriorityDistribution(),
                    hse_distribution=PriorityDistribution(),
                    review_status=ReviewStatusCounts(),
                    agreement_rate=100.0,
                )

            high_c = sum(1 for r in reports if (r.final_priority or r.analysis.priority) == PriorityLevel.HIGH)
            med_c = sum(1 for r in reports if (r.final_priority or r.analysis.priority) == PriorityLevel.MEDIUM)
            low_c = sum(1 for r in reports if (r.final_priority or r.analysis.priority) == PriorityLevel.LOW)

            # SIF precursor flag rate (reports with high/medium priority or sif_prob >= 0.50)
            sif_flagged = sum(1 for r in reports if r.analysis.sif_probability >= 0.50 or r.analysis.priority == PriorityLevel.HIGH)
            sif_rate = round((sif_flagged / total) * 100, 1)

            pending = sum(
                1
                for r in reports
                if not r.hse_reviewed
            )
            completed = sum(1 for r in reports if r.hse_reviewed)

            # AI distribution (original AI outputs)
            ai_dist = PriorityDistribution(
                HIGH=sum(1 for r in reports if r.analysis.priority == PriorityLevel.HIGH),
                MEDIUM=sum(1 for r in reports if r.analysis.priority == PriorityLevel.MEDIUM),
                LOW=sum(1 for r in reports if r.analysis.priority == PriorityLevel.LOW),
            )

            # HSE distribution (final post-review determinations)
            hse_dist = PriorityDistribution(
                HIGH=sum(1 for r in reports if r.hse_reviewed and r.final_priority == PriorityLevel.HIGH),
                MEDIUM=sum(1 for r in reports if r.hse_reviewed and r.final_priority == PriorityLevel.MEDIUM),
                LOW=sum(1 for r in reports if r.hse_reviewed and r.final_priority == PriorityLevel.LOW),
                UNREVIEWED=sum(1 for r in reports if not r.hse_reviewed),
            )

            # Review status breakdown
            rev_status = ReviewStatusCounts(
                pending=pending,
                confirmed=sum(1 for r in reports if r.hse_reviewed and r.review_decision == "confirmed"),
                corrected=sum(1 for r in reports if r.hse_reviewed and r.review_decision == "corrected"),
                rejected=sum(1 for r in reports if r.hse_reviewed and r.review_decision == "rejected"),
                total_reviewed=completed,
            )

            # Agreement rate between AI prediction and HSE decision
            if completed > 0:
                agreed = sum(
                    1 for r in reports
                    if r.hse_reviewed and (r.review_decision == "confirmed" or r.final_priority == r.analysis.priority)
                )
                agreement_rate = round((agreed / completed) * 100, 1)
            else:
                agreement_rate = 100.0

            patterns = self.get_patterns()
            active_alerts_list, _, unread_count = self.get_alerts(acknowledged=False, limit=5)

            return DashboardSummaryResponse(
                total_reports=total,
                high_priority_count=high_c,
                medium_priority_count=med_c,
                low_priority_count=low_c,
                sif_precursor_rate=sif_rate,
                pending_reviews_count=pending,
                completed_reviews_count=completed,
                top_hazards=patterns.top_hazards,
                top_activities=patterns.top_activities,
                top_barrier_failures=patterns.top_barrier_gaps,
                ai_distribution=ai_dist,
                hse_distribution=hse_dist,
                review_status=rev_status,
                agreement_rate=agreement_rate,
                active_alerts=active_alerts_list,
                unread_alerts_count=unread_count,
            )

    def seed_from_csv(
        self,
        csv_path: Optional[Path | str] = None,
        max_records: int = 30,
        engine: Optional[SIFDecisionEngine] = None,
    ) -> int:
        """Seed repository with real evaluations of synthetic safety reports."""
        with self._lock:
            if self._seeded or len(self._reports) > 0:
                return len(self._reports)

        path = Path(csv_path) if csv_path else None
        if not path or not path.exists():
            candidates = [
                Path(__file__).resolve().parents[3] / "dataset" / "raw" / "synthetic_sample.csv",
                Path(__file__).resolve().parents[2] / "dataset" / "raw" / "synthetic_sample.csv",
            ]
            for cand in candidates:
                if cand.exists():
                    path = cand
                    break

        if not path or not path.exists():
            return 0

        decision_engine = engine or SIFDecisionEngine()
        loaded = 0

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_records:
                    break
                rep_id = row.get("report_id", f"SYN-{i+1:03d}")
                text = row.get("report_text", "")
                if not text:
                    continue

                analysis = decision_engine.evaluate(text, report_id=rep_id)
                stored = StoredReport(
                    report_id=rep_id,
                    report_text=text,
                    analysis=analysis,
                    final_priority=analysis.priority,
                )
                self.save(stored)
                # Phase 13: Automatically trigger workflow on seeded records
                AutomatedHSEWorkflow.process_analysis_workflow(stored, analysis, self)
                loaded += 1

        with self._lock:
            self._seeded = True

        return loaded


# Global singleton repository
_repository_instance: Optional[ReportRepository] = None


def get_repository() -> ReportRepository:
    """Get the global singleton ReportRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ReportRepository()
        # Automatically seed on first call
        _repository_instance.seed_from_csv()
    return _repository_instance
