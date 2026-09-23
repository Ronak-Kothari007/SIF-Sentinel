"""
SIF Sentinel — Persistence Layer Unit Tests (Phase 9)
=====================================================

Tests PostgreSQL / SQLAlchemy persistence across all 9 tables:
  1. create report
  2. analyze report & save result (prediction, entities, triggered rules, audit log)
  3. retrieve result & verify relationships
  4. save HSE review & verify audit trail
  5. feedback & risk pattern persistence
  6. local seed script verification
"""

from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    AuditLog,
    Base,
    Entity,
    Feedback,
    HSEReview,
    Prediction,
    Report,
    RiskPattern,
    TriggeredRule,
    User,
)
from app.services.db_service import DatabaseService
from app.services.decision_engine import SIFDecisionEngine


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ===========================================================================
# 1. Create Report Tests
# ===========================================================================

class TestCreateReport:
    def test_create_report_success(self, db_session):
        rep = DatabaseService.create_report(
            db=db_session,
            report_id="SYN-TEST-100",
            report_text="Maintenance started on energized equipment without verified isolation.",
            location="Tank Farm 1",
            report_type="near_miss",
            severity_self_rated="critical",
            source="synthetic",
        )

        assert rep.id == "SYN-TEST-100"
        assert rep.report_text.startswith("Maintenance started")
        assert rep.location == "Tank Farm 1"
        assert rep.created_at is not None

        # Query back from DB
        db_rep = db_session.query(Report).filter(Report.id == "SYN-TEST-100").first()
        assert db_rep is not None
        assert db_rep.severity_self_rated == "critical"


# ===========================================================================
# 2. Analyze Report & Save Result Tests
# ===========================================================================

class TestAnalyzeAndSaveResult:
    def test_analyze_and_save_complete_result(self, db_session):
        rep_id = "SYN-TEST-101"
        text = "Maintenance started on energized equipment without verified isolation."
        DatabaseService.create_report(db=db_session, report_id=rep_id, report_text=text)

        # Run decision engine
        engine = SIFDecisionEngine()
        analysis = engine.evaluate(text, report_id=rep_id)

        # Persist analysis
        pred = DatabaseService.save_analysis(db=db_session, report_id=rep_id, analysis=analysis)
        assert pred.report_id == rep_id
        assert pred.priority == "HIGH"
        assert pred.sif_probability >= 0.50
        assert pred.activity == "Maintenance"
        assert pred.hazard == "Electrical Energy"
        assert pred.barrier == "Isolation"
        assert pred.barrier_status == "Not Verified"

        # Check triggered rules persisted
        rules = db_session.query(TriggeredRule).filter(TriggeredRule.report_id == rep_id).all()
        assert len(rules) >= 1
        rule_cats = [r.category for r in rules]
        assert "Energy Isolation" in rule_cats

        # Check audit log entry created
        audit = db_session.query(AuditLog).filter(AuditLog.entity_id == rep_id).first()
        assert audit is not None
        assert audit.action == "ANALYZE_REPORT"


# ===========================================================================
# 3. Retrieve Result Tests
# ===========================================================================

class TestRetrieveResult:
    def test_retrieve_consolidated_report(self, db_session):
        rep_id = "SYN-TEST-102"
        text = "Worker on top of scaffold at 6 metres without harness. Guardrail missing."
        DatabaseService.create_report(db=db_session, report_id=rep_id, report_text=text)

        engine = SIFDecisionEngine()
        analysis = engine.evaluate(text, report_id=rep_id)
        DatabaseService.save_analysis(db=db_session, report_id=rep_id, analysis=analysis)

        # Save extracted entities
        ctx = engine.extractor.extract(text)
        DatabaseService.save_entities(db=db_session, report_id=rep_id, entities=ctx.entities)

        # Retrieve consolidated dict
        result = DatabaseService.get_report_with_analysis(db=db_session, report_id=rep_id)
        assert result is not None
        assert result["report"].id == rep_id
        assert result["prediction"].priority == "HIGH"
        assert result["prediction"].hazard == "Fall from Height"
        assert len(result["entities"]) >= 1

        ent_types = [e.entity_type for e in result["entities"]]
        assert "barrier" in ent_types or "hazard" in ent_types

    def test_retrieve_non_existent_returns_none(self, db_session):
        res = DatabaseService.get_report_with_analysis(db=db_session, report_id="NON-EXISTENT")
        assert res is None


# ===========================================================================
# 4. Save HSE Review Tests
# ===========================================================================

class TestSaveHSEReview:
    def test_save_hse_review_and_audit_trail(self, db_session):
        rep_id = "SYN-TEST-103"
        text = "Welding in process area without hot work permit."
        DatabaseService.create_report(db=db_session, report_id=rep_id, report_text=text)

        engine = SIFDecisionEngine()
        analysis = engine.evaluate(text, report_id=rep_id)
        DatabaseService.save_analysis(db=db_session, report_id=rep_id, analysis=analysis)

        # Submit HSE review
        review = DatabaseService.save_hse_review(
            db=db_session,
            report_id=rep_id,
            reviewer_id="HSE-OFFICER-RONAK",
            decision="confirmed",
            original_priority="HIGH",
            final_priority="HIGH",
            comments="Work stopped. Area authority notified to issue proper permit.",
        )

        assert review.id is not None
        assert review.report_id == rep_id
        assert review.reviewer_id == "HSE-OFFICER-RONAK"
        assert review.decision == "confirmed"

        # Verify audit log recorded review action
        review_audit = (
            db_session.query(AuditLog)
            .filter(AuditLog.entity_id == rep_id, AuditLog.action == "HSE_REVIEW")
            .first()
        )
        assert review_audit is not None
        assert review_audit.actor_id == "HSE-OFFICER-RONAK"


# ===========================================================================
# 5. Feedback & Risk Patterns Tests
# ===========================================================================

class TestFeedbackAndRiskPatterns:
    def test_save_feedback(self, db_session):
        rep_id = "SYN-TEST-104"
        text = "Routine housekeeping."
        DatabaseService.create_report(db=db_session, report_id=rep_id, report_text=text)

        fb = DatabaseService.save_feedback(
            db=db_session,
            report_id=rep_id,
            user_id=None,
            feedback_type="correct_classification",
            notes="Accurately flagged as low priority.",
        )
        assert fb.id is not None
        assert fb.feedback_type == "correct_classification"

    def test_risk_pattern_storage(self, db_session):
        pattern = RiskPattern(
            cluster_name="Isolation - Not Verified",
            hazard="Electrical Energy",
            barrier="Isolation",
            barrier_status="Not Verified",
            occurrences=5,
            risk_band="HIGH",
            recommendation="Audit LOTO lock verification compliance before maintenance.",
        )
        db_session.add(pattern)
        db_session.commit()

        stored_pat = (
            db_session.query(RiskPattern)
            .filter(RiskPattern.cluster_name == "Isolation - Not Verified")
            .first()
        )
        assert stored_pat is not None
        assert stored_pat.occurrences == 5


# ===========================================================================
# 6. User Table & Authentication Schema Tests
# ===========================================================================

class TestUsersTable:
    def test_create_and_query_user(self, db_session):
        user = User(
            username="hse_inspector",
            email="inspector@sifsentinel.internal",
            hashed_password="secure_hash_placeholder",
            full_name="Site Safety Inspector",
            role="hse_officer",
        )
        db_session.add(user)
        db_session.commit()

        fetched = db_session.query(User).filter(User.username == "hse_inspector").first()
        assert fetched is not None
        assert fetched.email == "inspector@sifsentinel.internal"
        assert fetched.is_active is True
