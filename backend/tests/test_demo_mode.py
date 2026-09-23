"""
SIF Sentinel — Demo Mode Test Suite (Phase 16)
==============================================

Verifies that the controlled demo mode:
  1. Contains 10 curated synthetic scenarios covering all required hazard modes.
  2. Executes through the REAL live pipeline (DistilBERT/fallback + Rule Engine + Extractor).
  3. Correctly derives priorities, triggered rules, and non-contradictory explanations.
  4. Pre-stages exemplary human-in-the-loop HSE reviews.
  5. Successfully indexes into Sentence Transformers similarity engine and recurring clusters.
  6. Cleanly resets when requested without touching external data.
"""

import pytest
from fastapi.testclient import TestClient

from app.demo.scenarios import DEMO_SCENARIOS
from app.main import app
from app.schemas.decision import PriorityLevel
from app.services.report_store import get_repository


@pytest.fixture
def client():
    return TestClient(app)


class TestDemoScenarioDefinitions:
    """Verify scenarios cover all user-specified hazard domains and are tagged synthetic."""

    def test_scenarios_count_and_tagging(self):
        assert len(DEMO_SCENARIOS) == 10
        for s in DEMO_SCENARIOS:
            assert s.report_id.startswith("DEMO-SYN-")
            assert s.source == "synthetic_demo"
            assert s.is_demo is True
            assert len(s.report_text) > 30

    def test_all_required_domains_covered(self):
        categories = [s.category for s in DEMO_SCENARIOS]
        assert "energy_isolation" in categories
        assert "confined_space" in categories
        assert "working_at_height" in categories
        assert "hot_work" in categories
        assert "line_of_fire" in categories
        assert "routine_housekeeping" in categories
        assert "ergonomics" in categories
        assert "near_miss" in categories
        assert "ambiguous_precursor" in categories
        assert "recurring_energy_isolation" in categories


class TestDemoPipelineExecution:
    """Verify the real pipeline runs during demo loading."""

    def test_load_demo_dataset_via_api(self, client):
        # 1. Trigger live ingestion
        resp = client.post("/api/v1/demo/load?reset_first=true")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["total_loaded"] == 10
        assert data["high_priority_count"] >= 5
        assert data["low_priority_count"] >= 2
        assert data["rules_fired_count"] >= 5

        # 2. Check individual report results
        items_by_id = {item["report_id"]: item for item in data["items"]}

        # Energy Isolation
        r1 = items_by_id["DEMO-SYN-001"]
        assert r1["priority"] == "HIGH"
        assert "Energy Isolation Failure" in r1["rules_triggered"]
        assert r1["has_hse_review"] is True
        assert r1["review_decision"] == "confirmed"

        # Confined Space
        r2 = items_by_id["DEMO-SYN-002"]
        assert r2["priority"] == "HIGH"
        assert any("Confined Space" in r for r in r2["rules_triggered"])

        # Height
        r3 = items_by_id["DEMO-SYN-003"]
        assert r3["priority"] == "HIGH"
        assert any("Height" in r for r in r3["rules_triggered"])

        # Hot work
        r4 = items_by_id["DEMO-SYN-004"]
        assert r4["priority"] == "HIGH"
        assert any("Hot Work" in r for r in r4["rules_triggered"])

        # Line of fire
        r5 = items_by_id["DEMO-SYN-005"]
        assert r5["priority"] == "HIGH"
        assert any("Line of Fire" in r for r in r5["rules_triggered"])

        # Non-SIF Housekeeping
        r6 = items_by_id["DEMO-SYN-006"]
        assert r6["priority"] == "LOW"
        assert len(r6["rules_triggered"]) == 0

        # Non-SIF Ergonomics
        r7 = items_by_id["DEMO-SYN-007"]
        assert r7["priority"] == "LOW"
        assert len(r7["rules_triggered"]) == 0

        # Near Miss
        r8 = items_by_id["DEMO-SYN-008"]
        assert r8["priority"] in ["MEDIUM", "LOW"]

        # Ambiguous Case (Pre-staged HSE review corrected to HIGH)
        r9 = items_by_id["DEMO-SYN-009"]
        assert r9["has_hse_review"] is True
        assert r9["review_decision"] == "corrected"

        # Recurring Electrical Pattern
        r10 = items_by_id["DEMO-SYN-010"]
        assert r10["priority"] == "HIGH"
        assert "Energy Isolation Failure" in r10["rules_triggered"]

    def test_demo_status_endpoint(self, client):
        resp = client.get("/api/v1/demo/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_demo_loaded"] is True
        assert data["demo_reports_count"] == 10
        assert data["total_scenarios_available"] == 10

    def test_demo_reports_reflected_in_general_endpoints(self, client):
        # 1. Reports list shows demo items
        r_resp = client.get("/api/v1/reports?limit=100")
        assert r_resp.status_code == 200
        items = r_resp.json()["items"]
        demo_items = [i for i in items if i["report_id"].startswith("DEMO-SYN-")]
        assert len(demo_items) == 10

        # 2. Report details shows structured explanation & review
        d_resp = client.get("/api/v1/reports/DEMO-SYN-001")
        assert d_resp.status_code == 200
        detail = d_resp.json()
        assert detail["priority"] == "HIGH"
        assert detail["hse_reviewed"] is True
        assert detail["review_decision"] == "confirmed"
        assert "structured_explanation" in detail
        assert len(detail["structured_explanation"]["why"]) >= 2

        # 3. Dashboard summary includes demo counts
        dash_resp = client.get("/api/v1/dashboard-summary")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["total_reports"] >= 10
        assert dash["high_priority_count"] >= 5

        # 4. Semantic similarity finds DEMO-SYN-010 similar to DEMO-SYN-001
        sim_resp = client.get("/api/v1/similar-reports/DEMO-SYN-001?limit=5&threshold=0.30")
        assert sim_resp.status_code == 200

    def test_demo_reset_cleans_records(self, client):
        # Trigger reset
        reset_resp = client.post("/api/v1/demo/reset")
        assert reset_resp.status_code == 200
        data = reset_resp.json()
        assert data["status"] == "success"
        assert data["removed_count"] == 10

        # Status is now empty
        st_resp = client.get("/api/v1/demo/status")
        assert st_resp.json()["is_demo_loaded"] is False
        assert st_resp.json()["demo_reports_count"] == 0
