"""
SIF Sentinel — SQLAlchemy Database Models (Phase 9)
===================================================

Defines the relational tables for persistent storage of safety reports,
predictions, entities, triggered rules, HSE reviews, feedback,
risk pattern clusters, and audit logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ===========================================================================
# 1. users Table
# ===========================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), default="hse_officer", nullable=False)  # admin, hse_officer, supervisor
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    reports = relationship("Report", back_populates="submitted_by_user")
    feedback = relationship("Feedback", back_populates="user")


# ===========================================================================
# 2. reports Table
# ===========================================================================
class Report(Base):
    __tablename__ = "reports"

    id = Column(String(50), primary_key=True)  # e.g. SYN-001 or REP-...
    report_text = Column(Text, nullable=False)
    report_type = Column(String(50), default="near_miss", nullable=False)
    location = Column(String(100), default="Unknown", nullable=False)
    severity_self_rated = Column(String(50), default="medium", nullable=False)
    source = Column(String(50), default="synthetic", nullable=False)  # synthetic, public, anonymized
    source_file_name = Column(String(255), nullable=True)
    source_file_path = Column(String(255), nullable=True)
    submitted_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    workflow_status = Column(String(50), default="PENDING", nullable=False)
    in_review_queue = Column(Boolean, default=False, nullable=False)
    queue_entered_at = Column(DateTime(timezone=True), nullable=True)

    submitted_by_user = relationship("User", back_populates="reports")
    predictions = relationship("Prediction", back_populates="report", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="report", cascade="all, delete-orphan")
    triggered_rules = relationship("TriggeredRule", back_populates="report", cascade="all, delete-orphan")
    hse_reviews = relationship("HSEReview", back_populates="report", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="report", cascade="all, delete-orphan")
    alerts = relationship("AlertEvent", back_populates="report", cascade="all, delete-orphan")


# ===========================================================================
# 3. predictions Table
# ===========================================================================
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    sif_probability = Column(Float, nullable=False)
    priority = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH
    priority_score = Column(Float, nullable=False)
    activity = Column(String(100), nullable=True)
    hazard = Column(String(100), nullable=True)
    barrier = Column(String(100), nullable=True)
    barrier_status = Column(String(50), nullable=True)
    model_name = Column(String(50), default="DistilBERT", nullable=False)
    explanation = Column(Text, nullable=False)
    escalated = Column(Boolean, default=False, nullable=False)
    escalation_reason = Column(Text, nullable=True)
    factor_scores_json = Column(Text, nullable=True)
    structured_explanation_json = Column(Text, nullable=True)
    governance_notice = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="predictions")


# ===========================================================================
# 4. entities Table
# ===========================================================================
class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # activity, hazard, barrier, location, equipment
    surface_text = Column(String(200), nullable=False)
    normalized_value = Column(String(100), nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    status = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    source = Column(String(50), default="hybrid", nullable=False)  # deterministic, nlp_pattern, hybrid
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="entities")


# ===========================================================================
# 5. triggered_rules Table
# ===========================================================================
class TriggeredRule(Base):
    __tablename__ = "triggered_rules"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False)  # e.g. RULE_001
    rule_name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    severity = Column(Integer, nullable=False)
    severity_label = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    explanation = Column(Text, nullable=False)
    triggered_signals_json = Column(Text, nullable=False)  # JSON array of signals
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="triggered_rules")


# ===========================================================================
# 6. hse_reviews Table
# ===========================================================================
class HSEReview(Base):
    __tablename__ = "hse_reviews"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(100), nullable=False)
    decision = Column(String(50), nullable=False)  # confirmed, rejected, corrected
    original_priority = Column(String(20), nullable=False)
    original_activity = Column(String(100), nullable=True)
    original_hazard = Column(String(100), nullable=True)
    original_barrier = Column(String(100), nullable=True)
    original_sif_probability = Column(Float, nullable=True)
    final_priority = Column(String(20), nullable=False)
    corrected_activity = Column(String(100), nullable=True)
    corrected_hazard = Column(String(100), nullable=True)
    corrected_barrier = Column(String(100), nullable=True)
    comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="hse_reviews")


# ===========================================================================
# 7. feedback Table
# ===========================================================================
class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=lambda: f"FB-{uuid.uuid4().hex[:8].upper()}")
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    feedback_type = Column(String(50), nullable=False)  # false_positive, false_negative, label_correction
    user_suggested_priority = Column(String(20), nullable=True)
    notes = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="feedback")
    user = relationship("User", back_populates="feedback")


# ===========================================================================
# 8. risk_patterns Table
# ===========================================================================
class RiskPattern(Base):
    __tablename__ = "risk_patterns"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    cluster_name = Column(String(100), nullable=False, index=True)
    hazard = Column(String(100), nullable=False)
    barrier = Column(String(100), nullable=False)
    barrier_status = Column(String(50), nullable=False)
    occurrences = Column(Integer, default=1, nullable=False)
    risk_band = Column(String(20), default="HIGH", nullable=False)
    recommendation = Column(Text, nullable=False)
    last_detected_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ===========================================================================
# 9. audit_logs Table
# ===========================================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    action = Column(String(50), nullable=False, index=True)  # ANALYZE_REPORT, HSE_REVIEW, UPDATE_PRIORITY
    entity_type = Column(String(50), nullable=False)  # report, prediction, hse_review
    entity_id = Column(String(50), nullable=False, index=True)
    actor_id = Column(String(100), nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ===========================================================================
# 10. alert_events Table (Phase 13: Automated HSE Workflow)
# ===========================================================================
class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)  # "HIGH PRIORITY → HSE REVIEW REQUIRED"
    severity = Column(String(20), default="HIGH", nullable=False)  # HIGH, CRITICAL
    message = Column(Text, nullable=False)
    workflow_status = Column(String(50), default="HSE_REVIEW_REQUIRED", nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    report = relationship("Report", back_populates="alerts")


# ===========================================================================
# 11. safety_actions Table (Phase 16: Action Center)
# ===========================================================================
class SafetyAction(Base):
    __tablename__ = "safety_actions"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    report_id = Column(String(50), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    priority = Column(String(20), default="HIGH", nullable=False)
    status = Column(String(50), default="Open", nullable=False)  # Open, Assigned, In Progress, Verification, Closed
    site_location = Column(String(100), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    report = relationship("Report", backref="actions")
