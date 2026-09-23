"""
SIF Sentinel — Phase 1 API Tests

Tests for:
  - GET  /health
  - POST /reports/test

Uses FastAPI's TestClient (backed by httpx) — no server needs to be running.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self):
        """Health endpoint must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_ok(self):
        """Status field must be 'ok'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_has_version(self):
        """Response must include a version string."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert len(data["version"]) > 0

    def test_health_has_environment(self):
        """Response must include environment."""
        response = client.get("/health")
        data = response.json()
        assert "environment" in data

    def test_health_has_message(self):
        """Response must include a message field."""
        response = client.get("/health")
        data = response.json()
        assert "message" in data


# ---------------------------------------------------------------------------
# POST /reports/test — basic submission tests
# ---------------------------------------------------------------------------

class TestReportTestEndpoint:

    BASE_PAYLOAD = {
        "report_text": "Worker observed without safety helmet near excavation site.",
        "report_type": "unsafe_act",
        "location": "Block A, Well Site 12",
        "severity_self_rated": "medium",
    }

    def test_returns_200(self):
        """Endpoint must return HTTP 200 for a valid payload."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        assert response.status_code == 200

    def test_response_has_report_id(self):
        """Response must include a report_id string."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        assert "report_id" in data
        assert len(data["report_id"]) > 0

    def test_response_has_analysis(self):
        """Response must include an analysis block with all Phase 2 fields."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        assert "analysis" in data
        analysis = data["analysis"]
        assert "sif_flag" in analysis
        assert "priority_band" in analysis
        assert "priority_score" in analysis
        assert "model_confidence" in analysis
        assert "explanation" in analysis
        assert "rule_severity_score" in analysis
        assert "evidence_summary" in analysis
        assert "triggered_rules" in analysis
        assert "triggered_categories" in analysis
        assert "pipeline_status" in analysis

    def test_priority_band_valid_value(self):
        """Priority band must be one of the allowed values."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        valid_bands = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert data["analysis"]["priority_band"] in valid_bands

    def test_priority_score_in_range(self):
        """Priority score must be between 0.0 and 1.0."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        score = data["analysis"]["priority_score"]
        assert 0.0 <= score <= 1.0

    def test_word_count_correct(self):
        """Word count in response must match actual word count of submitted text."""
        payload = {**self.BASE_PAYLOAD, "report_text": "one two three four five"}
        response = client.post("/reports/test", json=payload)
        data = response.json()
        assert data["word_count"] == 5

    def test_pipeline_status_is_placeholder(self):
        """pipeline_status must be 'rules_only' in Phase 2 (rule engine is active)."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        assert data["pipeline_status"] == "rules_only"

    def test_location_echoed_back(self):
        """Location submitted should be echoed back in the response."""
        response = client.post("/reports/test", json=self.BASE_PAYLOAD)
        data = response.json()
        assert data["location"] == self.BASE_PAYLOAD["location"]


# ---------------------------------------------------------------------------
# Priority keyword heuristic tests
# ---------------------------------------------------------------------------

class TestPlaceholderPriorityHeuristic:

    def test_critical_rule_triggers_high_or_critical_band(self):
        """Reports with CRITICAL-severity rule signals (LOTO failure) should get HIGH+ band.
        With Phase 2 weights (65% rules + 35% model placeholder), a single CRITICAL rule
        yields composite score 0.755 = HIGH band. sif_flag must be True."""
        payload = {
            "report_text": "LOTO not applied before maintenance on energized equipment.",
            "report_type": "near_miss",
            "location": "Pump House A",
            "severity_self_rated": "critical",
        }
        response = client.post("/reports/test", json=payload)
        data = response.json()
        assert data["analysis"]["priority_band"] in {"HIGH", "CRITICAL"}
        assert data["analysis"]["sif_flag"] is True

    def test_confined_space_triggers_high_band(self):
        """Reports mentioning 'confined space' with missing controls should get HIGH band."""
        payload = {
            "report_text": "Worker entered confined space without gas test or attendant.",
            "report_type": "unsafe_act",
            "location": "Storage Tank 3",
            "severity_self_rated": "high",
        }
        response = client.post("/reports/test", json=payload)
        data = response.json()
        assert data["analysis"]["priority_band"] == "HIGH"
        assert data["analysis"]["sif_flag"] is True

    def test_low_text_triggers_low_band(self):
        """A generic, low-risk report should get LOW band."""
        payload = {
            "report_text": "Office chair wheel was slightly wobbly during normal work.",
            "report_type": "unsafe_condition",
            "location": "Admin Block",
            "severity_self_rated": "low",
        }
        response = client.post("/reports/test", json=payload)
        data = response.json()
        assert data["analysis"]["priority_band"] == "LOW"
        assert data["analysis"]["sif_flag"] is False


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_empty_report_text_rejected(self):
        """Report text shorter than 10 characters must be rejected."""
        payload = {
            "report_text": "Short",
            "report_type": "near_miss",
            "location": "Site A",
            "severity_self_rated": "low",
        }
        response = client.post("/reports/test", json=payload)
        assert response.status_code == 422

    def test_missing_report_text_rejected(self):
        """Missing report_text must be rejected with 422."""
        response = client.post("/reports/test", json={})
        assert response.status_code == 422

    def test_invalid_report_type_rejected(self):
        """Invalid report_type must be rejected with 422."""
        payload = {
            "report_text": "Worker observed without safety helmet near excavation site.",
            "report_type": "unknown_type",
            "location": "Site A",
            "severity_self_rated": "low",
        }
        response = client.post("/reports/test", json=payload)
        assert response.status_code == 422

    def test_invalid_severity_rejected(self):
        """Invalid severity_self_rated must be rejected with 422."""
        payload = {
            "report_text": "Worker observed without safety helmet near excavation site.",
            "report_type": "near_miss",
            "location": "Site A",
            "severity_self_rated": "extreme",
        }
        response = client.post("/reports/test", json=payload)
        assert response.status_code == 422
