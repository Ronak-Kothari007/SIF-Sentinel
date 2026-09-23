"""
SIF Sentinel — Automated Test Suite for Phase 11 (Recurring-Risk Detection)
===========================================================================

Validates:
1. Dense vector embeddings via Sentence Transformers (all-MiniLM-L6-v2)
2. Cosine similarity without keyword matching (paraphrase semantic proximity)
3. Nearest-neighbor similar reports retrieval (GET /api/v1/similar-reports/{id})
4. Semantic recurring pattern detection with date trend analysis
5. Recurrence signal injection into the multi-factor decision engine
"""

from __future__ import annotations

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.api_v1 import (
    SemanticRecurringPattern,
    SimilarReportsResponse,
    TemporalTrend,
)
from app.schemas.decision import DecisionResult, PriorityLevel
from app.services.embedding_service import (
    EMBEDDING_DIM,
    SemanticEmbeddingService,
    get_embedding_service,
)
from app.services.report_store import ReportRepository, StoredReport, get_repository
from app.services.similarity_engine import RecurringRiskEngine


# ===========================================================================
# 1. Embedding Service Tests
# ===========================================================================

def test_embedding_service_shape_and_norm():
    """Verify that embeddings have dimension 384 and are unit L2-normalized."""
    service = get_embedding_service()
    text = "Maintenance technician opened energized electrical breaker without verified LOTO."
    vec = service.get_embedding(text)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (EMBEDDING_DIM,)
    assert vec.dtype == np.float32
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-3, f"Vector should be unit-normalized, got {norm}"


def test_embedding_batch_generation():
    """Verify batch vector encoding."""
    service = get_embedding_service()
    texts = [
        "Confined space entry without atmospheric gas test.",
        "Scaffolding dismantled without personal fall arrest system.",
        "Minor spill of water in corridor cleaned immediately.",
    ]
    vecs = service.get_embeddings_batch(texts)

    assert isinstance(vecs, np.ndarray)
    assert vecs.shape == (3, EMBEDDING_DIM)
    for i in range(3):
        assert abs(float(np.linalg.norm(vecs[i])) - 1.0) < 1e-3


def test_semantic_similarity_without_keyword_matching():
    """
    CRITICAL REQUIREMENT: Cosine similarity detects conceptual synonymy
    without requiring exact keyword matching.
    """
    service = get_embedding_service()

    # Two reports describing the EXACT same electrical isolation failure in completely different words
    text_a = "Technician worked on live circuit without lockout tagout applied to main feed breaker."
    text_b = "Electrician started servicing energized switchgear without zero-energy verification."

    # A completely unrelated report
    text_unrelated = "Administrative desk chair wheel was broken and replaced by facilities."

    vec_a = service.get_embedding(text_a)
    vec_b = service.get_embedding(text_b)
    vec_unrelated = service.get_embedding(text_unrelated)

    sim_synonym = service.compute_similarity(vec_a, vec_b)
    sim_unrelated = service.compute_similarity(vec_a, vec_unrelated)

    assert sim_synonym > 0.30, f"Semantically identical events should have high similarity, got {sim_synonym}"
    assert sim_unrelated < 0.20, f"Unrelated events should have low similarity, got {sim_unrelated}"
    assert sim_synonym > sim_unrelated + 0.10


# ===========================================================================
# 2. Similarity Engine & Pattern Detection Tests
# ===========================================================================

def test_similarity_engine_indexing_and_retrieval():
    """Verify storing, querying, and ranking similar reports."""
    engine = RecurringRiskEngine()

    dummy_reports = {
        "REP-001": StoredReport(
            report_id="REP-001",
            report_text="Electrician worked on live motor control panel without verified isolation lockout.",
            analysis=DecisionResult(
                report_id="REP-001",
                sif_probability=0.95,
                priority=PriorityLevel.HIGH,
                activity="Maintenance",
                hazard="Electrical Energy",
                barrier="Isolation",
                barrier_status="Absent",
                priority_score=0.95,
                explanation="High electrical risk",
            ),
        ),
        "REP-002": StoredReport(
            report_id="REP-002",
            report_text="Maintenance commenced on energized electrical switchgear with no LOTO padlock isolation.",
            analysis=DecisionResult(
                report_id="REP-002",
                sif_probability=0.92,
                priority=PriorityLevel.HIGH,
                activity="Maintenance",
                hazard="Electrical Energy",
                barrier="Isolation",
                barrier_status="Not Verified",
                priority_score=0.92,
                explanation="High electrical risk",
            ),
        ),
        "REP-003": StoredReport(
            report_id="REP-003",
            report_text="Empty cardboard box disposed in recycling dumpster.",
            analysis=DecisionResult(
                report_id="REP-003",
                sif_probability=0.05,
                priority=PriorityLevel.LOW,
                activity="Housekeeping",
                hazard="Ergonomic",
                barrier="General",
                priority_score=0.10,
                explanation="Low risk housekeeping",
            ),
        ),
    }

    # Index reports
    for rep_id, rep in dummy_reports.items():
        engine.index_report(rep_id, rep.report_text)

    # Query similar reports for REP-001
    similar = engine.find_similar_reports("REP-001", dummy_reports, limit=5, threshold=0.35)

    assert len(similar) >= 1
    # REP-002 should be the top match
    top_match = similar[0]
    assert top_match.report_id == "REP-002"
    assert top_match.similarity_score >= 0.35
    assert top_match.hazard == "Electrical Energy"

    # Self-match (REP-001) must NEVER be included
    assert all(item.report_id != "REP-001" for item in similar)


def test_recurring_pattern_detection_with_trends():
    """
    Test semantic clustering into patterns and temporal trend analysis:
    - pattern ID
    - number of reports
    - common activity
    - common hazard
    - common barrier failure
    - trend direction and dates
    """
    engine = RecurringRiskEngine()

    now = datetime.now(timezone.utc)
    cluster_reports = [
        StoredReport(
            report_id="CONF-001",
            report_text="Worker entered separator vessel without continuous atmospheric gas monitoring.",
            created_at=now - timedelta(days=10),
            analysis=DecisionResult(
                report_id="CONF-001",
                sif_probability=0.95,
                priority=PriorityLevel.HIGH,
                activity="Confined Space Entry",
                hazard="Toxic Gas / H2S",
                barrier="Gas Testing",
                barrier_status="Absent",
                priority_score=0.95,
                explanation="Vessel entry without gas test",
            ),
        ),
        StoredReport(
            report_id="CONF-002",
            report_text="Contractor inside storage tank without atmospheric multi-gas detector test.",
            created_at=now - timedelta(days=5),
            analysis=DecisionResult(
                report_id="CONF-002",
                sif_probability=0.93,
                priority=PriorityLevel.HIGH,
                activity="Confined Space Entry",
                hazard="Toxic Gas / H2S",
                barrier="Gas Testing",
                barrier_status="Absent",
                priority_score=0.93,
                explanation="Tank entry without gas test",
            ),
        ),
        StoredReport(
            report_id="CONF-003",
            report_text="Confined manhole entry executed without pre-entry gas test or standby watch.",
            created_at=now - timedelta(days=1),
            analysis=DecisionResult(
                report_id="CONF-003",
                sif_probability=0.94,
                priority=PriorityLevel.HIGH,
                activity="Confined Space Entry",
                hazard="Toxic Gas / H2S",
                barrier="Gas Testing",
                barrier_status="Not Verified",
                priority_score=0.94,
                explanation="Manhole entry without gas test",
            ),
        ),
    ]

    for r in cluster_reports:
        engine.index_report(r.report_id, r.report_text)

    patterns = engine.detect_recurring_patterns(
        cluster_reports, similarity_threshold=0.45, min_cluster_size=2
    )

    assert len(patterns) >= 1
    pat = patterns[0]

    # Validate required pattern fields
    assert pat.pattern_id.startswith("PAT-SEM-")
    assert pat.number_of_reports >= 2
    assert pat.common_activity == "Confined Space Entry"
    assert pat.common_hazard == "Toxic Gas / H2S"
    assert "Gas Testing" in pat.common_barrier_failure
    assert pat.average_similarity > 0.40
    assert len(pat.representative_text) > 10
    assert "confined" in pat.recommended_action.lower() or "gas" in pat.recommended_action.lower()

    # Validate temporal trend
    assert pat.trend is not None
    assert pat.trend.first_seen is not None
    assert pat.trend.last_seen is not None
    assert pat.trend.span_days >= 4
    assert pat.trend.trend_direction in ["increasing", "stable", "isolated"]


def test_recurrence_signal_calculation():
    """Verify automated recurrence signal against high risk reports."""
    engine = RecurringRiskEngine()

    high_risk = [
        StoredReport(
            report_id="HR-1",
            report_text="Maintenance technician working on live 480V circuit with no lock out tag out.",
            analysis=DecisionResult(
                report_id="HR-1",
                sif_probability=0.95,
                priority=PriorityLevel.HIGH,
                activity="Maintenance",
                hazard="Electrical Energy",
                barrier="Isolation",
                priority_score=0.95,
                explanation="Live breaker",
            ),
        )
    ]
    engine.index_report(high_risk[0].report_id, high_risk[0].report_text)

    # High similarity narrative
    rec_signal_high = engine.calculate_recurrence_signal(
        "Electrician servicing energized circuit without LOTO padlock verification.",
        high_risk,
    )
    assert rec_signal_high > 0.0, f"Expected non-zero recurrence signal, got {rec_signal_high}"

    # Completely different narrative
    rec_signal_low = engine.calculate_recurrence_signal(
        "Office supplies ordered for administrative reception desk.",
        high_risk,
    )
    assert rec_signal_low == 0.0


# ===========================================================================
# 3. REST API Integration Tests
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    # Ensure repository is seeded
    repo = get_repository()
    repo.seed_from_csv()
    with TestClient(app) as test_client:
        yield test_client


def test_api_get_similar_reports_success(client):
    """Test GET /api/v1/similar-reports/{id} with valid report ID."""
    # Fetch a report first to know a valid ID
    rep_res = client.get("/api/v1/reports?limit=1")
    assert rep_res.status_code == 200
    items = rep_res.json()["items"]
    assert len(items) > 0
    target_id = items[0]["report_id"]

    # Query similar reports
    res = client.get(f"/api/v1/similar-reports/{target_id}?limit=3&threshold=0.30")
    assert res.status_code == 200
    data = res.json()

    assert data["target_report_id"] == target_id
    assert "similar_reports" in data
    assert isinstance(data["similar_reports"], list)

    for item in data["similar_reports"]:
        assert item["report_id"] != target_id
        assert item["similarity_score"] >= 0.30
        assert len(item["report_text"]) > 0
        assert item["priority"] in ["HIGH", "MEDIUM", "LOW"]


def test_api_get_similar_reports_not_found(client):
    """Test GET /api/v1/similar-reports/{id} with nonexistent ID returns 404."""
    res = client.get("/api/v1/similar-reports/NONEXISTENT-REPORT-999")
    assert res.status_code == 404
    detail = res.json()["detail"]
    assert "not found" in detail.lower()


def test_api_patterns_contains_semantic_patterns(client):
    """Test GET /api/v1/patterns returns semantic_patterns from Sentence Transformers."""
    res = client.get("/api/v1/patterns")
    assert res.status_code == 200
    data = res.json()

    assert "semantic_patterns" in data
    assert isinstance(data["semantic_patterns"], list)

    if len(data["semantic_patterns"]) > 0:
        pat = data["semantic_patterns"][0]
        assert "pattern_id" in pat
        assert "number_of_reports" in pat
        assert "common_activity" in pat
        assert "common_hazard" in pat
        assert "common_barrier_failure" in pat
        assert "trend" in pat
        assert "representative_text" in pat
        assert "average_similarity" in pat
        assert "recommended_action" in pat


def test_api_analyze_report_automatic_recurrence(client):
    """Test POST /api/v1/analyze-report computes and uses recurrence signal automatically."""
    payload = {
        "report_text": "Second maintenance crew found energized breaker without verified isolation in substation.",
        "location": "Substation 2",
    }
    res = client.post("/api/v1/analyze-report", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["priority"] == "HIGH"
    assert data["hazard"] == "Electrical Energy"
    assert data["barrier"] == "Isolation"
    assert data["sif_probability"] >= 0.45
    assert data["priority_score"] >= 0.65

    # Verify report is now indexable and queryable for similar reports
    new_id = data["report_id"]
    sim_res = client.get(f"/api/v1/similar-reports/{new_id}?limit=3&threshold=0.35")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["target_report_id"] == new_id
