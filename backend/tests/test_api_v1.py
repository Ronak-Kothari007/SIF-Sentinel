"""
SIF Sentinel — Production API v1 Integration Tests (Phase 8)
=============================================================

Comprehensive test suite verifying all 7 endpoints:
  1. POST /api/v1/analyze-report
  2. GET  /api/v1/reports
  3. GET  /api/v1/reports/{id}
  4. GET  /api/v1/high-risk
  5. GET  /api/v1/patterns
  6. POST /api/v1/hse-review
  7. GET  /api/v1/dashboard-summary
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ===========================================================================
# 1. POST /api/v1/analyze-report Tests
# ===========================================================================

class TestAnalyzeReportEndpoint:
    def test_target_example_analysis(self):
        """Verify the exact prompt input returns full SIF analysis and HIGH priority."""
        payload = {
            "report_text": "Maintenance started on energized equipment without verified isolation."
        }
        response = client.post("/api/v1/analyze-report", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "report_id" in data
        assert data["sif_probability"] >= 0.50
        assert data["priority"] == "HIGH"
        assert data["activity"] == "Maintenance"
        assert data["hazard"] == "Electrical Energy"
        assert data["barrier"] == "Isolation"
        assert data["barrier_status"] == "Not Verified"
        assert data["equipment"] == "energized equipment"
        assert len(data["triggered_rules"]) >= 1
        assert len(data["evidence"]) >= 1
        assert "does not predict accident" in data["explanation"].lower()
        assert "X-Process-Time-Ms" in response.headers

    def test_analyze_with_custom_report_id_and_location(self):
        payload = {
            "report_text": "Cutting operation in tank farm without hot work permit. Gas detected.",
            "report_id": "TEST-CUT-001",
            "location": "Tank Farm 2",
            "recurring_risk_signal": 0.80,
        }
        response = client.post("/api/v1/analyze-report", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["report_id"] == "TEST-CUT-001"
        assert data["priority"] == "HIGH"
        assert data["activity"] == "Cutting"
        assert data["barrier"] in ["Hot Work Permit", "Gas Testing"]

    def test_validation_error_on_short_text(self):
        payload = {"report_text": "Too short"}
        response = client.post("/api/v1/analyze-report", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "report_text" in data["detail"]

    def test_validation_error_on_empty_payload(self):
        response = client.post("/api/v1/analyze-report", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"


# ===========================================================================
# 2. GET /api/v1/reports Tests
# ===========================================================================

class TestGetReportsEndpoint:
    def test_get_reports_returns_paginated_list(self):
        response = client.get("/api/v1/reports?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert data["total"] >= 1
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert "items" in data
        assert len(data["items"]) <= 10

    def test_filter_reports_by_priority(self):
        response = client.get("/api/v1/reports?priority=HIGH")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["priority"] == "HIGH"

    def test_filter_reports_by_hazard(self):
        response = client.get("/api/v1/reports?hazard=Electrical")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert "electrical" in item["hazard"].lower()


# ===========================================================================
# 3. GET /api/v1/reports/{id} Tests
# ===========================================================================

class TestGetReportByIdEndpoint:
    def test_get_existing_report(self):
        # Create a report first
        payload = {
            "report_text": "Worker at height on top of 6-metre scaffold without harness.",
            "report_id": "TEST-SCAFFOLD-999",
        }
        create_resp = client.post("/api/v1/analyze-report", json=payload)
        assert create_resp.status_code == 200

        # Retrieve by ID
        get_resp = client.get("/api/v1/reports/TEST-SCAFFOLD-999")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["report_id"] == "TEST-SCAFFOLD-999"
        assert data["priority"] == "HIGH"
        assert data["hazard"] == "Fall from Height"

    def test_get_non_existent_report_returns_404(self):
        response = client.get("/api/v1/reports/NON-EXISTENT-ID-XYZ")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
        assert "NON-EXISTENT-ID-XYZ" in data["detail"]


# ===========================================================================
# 4. GET /api/v1/high-risk Tests
# ===========================================================================

class TestHighRiskQueueEndpoint:
    def test_get_high_risk_reports(self):
        response = client.get("/api/v1/high-risk?limit=20")
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert item["priority"] == "HIGH"

        # Verify items are sorted descending by priority score
        scores = [item["priority_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)


# ===========================================================================
# 5. GET /api/v1/patterns Tests
# ===========================================================================

class TestPatternsEndpoint:
    def test_get_patterns_returns_aggregated_trends(self):
        response = client.get("/api/v1/patterns")
        assert response.status_code == 200
        data = response.json()

        assert data["total_analyzed"] >= 1
        assert "top_hazards" in data
        assert "top_activities" in data
        assert "top_barrier_gaps" in data
        assert "recurring_clusters" in data
        assert len(data["summary"]) > 0

        # Top hazards have counts and percentages
        if data["top_hazards"]:
            haz = data["top_hazards"][0]
            assert "hazard" in haz
            assert haz["count"] >= 1
            assert 0.0 <= haz["percentage"] <= 100.0


# ===========================================================================
# 6. POST /api/v1/hse-review Tests
# ===========================================================================

class TestHSEReviewEndpoint:
    def test_submit_confirmed_review(self):
        # Create a report to review
        payload = {
            "report_text": "Confined space entry into separator without gas clearance.",
            "report_id": "TEST-REV-001",
        }
        client.post("/api/v1/analyze-report", json=payload)

        review_payload = {
            "report_id": "TEST-REV-001",
            "reviewer_id": "HSE-OFFICER-05",
            "decision": "confirmed",
            "comments": "Immediate stop work issued. Site supervisor briefed.",
        }
        response = client.post("/api/v1/hse-review", json=review_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["report_id"] == "TEST-REV-001"
        assert data["reviewer_id"] == "HSE-OFFICER-05"
        assert data["decision"] == "confirmed"
        assert data["final_priority"] == "HIGH"

    def test_submit_corrected_review(self):
        payload = {
            "report_text": "Administrative staff reported flickering bulb in corridor.",
            "report_id": "TEST-REV-CORR",
        }
        client.post("/api/v1/analyze-report", json=payload)

        review_payload = {
            "report_id": "TEST-REV-CORR",
            "reviewer_id": "HSE-LEAD-01",
            "decision": "corrected",
            "corrected_priority": "LOW",
            "comments": "Reclassified to LOW: facility maintenance item only.",
        }
        response = client.post("/api/v1/hse-review", json=review_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["decision"] == "corrected"
        assert data["final_priority"] == "LOW"

    def test_submit_review_for_non_existent_report(self):
        review_payload = {
            "report_id": "DOES-NOT-EXIST",
            "reviewer_id": "HSE-LEAD-01",
            "decision": "confirmed",
        }
        response = client.post("/api/v1/hse-review", json=review_payload)
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"

    def test_submit_review_invalid_decision(self):
        review_payload = {
            "report_id": "TEST-REV-001",
            "reviewer_id": "HSE-LEAD-01",
            "decision": "invalid_choice",
        }
        response = client.post("/api/v1/hse-review", json=review_payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"


# ===========================================================================
# 7. GET /api/v1/dashboard-summary Tests
# ===========================================================================

class TestDashboardSummaryEndpoint:
    def test_get_dashboard_summary_metrics(self):
        response = client.get("/api/v1/dashboard-summary")
        assert response.status_code == 200
        data = response.json()

        assert "total_reports" in data
        assert data["total_reports"] >= 1
        assert "high_priority_count" in data
        assert "medium_priority_count" in data
        assert "low_priority_count" in data
        assert "sif_precursor_rate" in data
        assert "pending_reviews_count" in data
        assert "completed_reviews_count" in data
        assert "top_hazards" in data
        assert "top_activities" in data
        assert "top_barrier_failures" in data


# ===========================================================================
# OpenAPI & Backward Compatibility Tests
# ===========================================================================

class TestOpenAPIAndBackwardCompatibility:
    def test_openapi_json_schema(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        # All 7 v1 endpoints are registered
        assert "/api/v1/analyze-report" in paths
        assert "/api/v1/reports" in paths
        assert "/api/v1/reports/{id}" in paths
        assert "/api/v1/high-risk" in paths
        assert "/api/v1/patterns" in paths
        assert "/api/v1/hse-review" in paths
        assert "/api/v1/dashboard-summary" in paths

    def test_health_endpoint_still_works(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_legacy_reports_test_endpoint_still_works(self):
        payload = {
            "report_text": "Worker observed operating angle grinder without face shield near H2S area."
        }
        response = client.post("/reports/test", json=payload)
        assert response.status_code == 200
