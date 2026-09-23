"""
SIF Sentinel — Phase 13: Automated HSE Workflow Test Suite
===========================================================

Tests the deterministic, automated HSE review workflow:
When an analysis produces HIGH priority:
  1. Saves the report
  2. Marks it HIGH priority
  3. Places it in the HSE review queue
  4. Creates an alert/event ("HIGH PRIORITY → HSE REVIEW REQUIRED")
  5. Records the escalation event in audit_logs
"""

import pytest
from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from app.schemas.decision import PriorityLevel
from app.services.report_store import get_repository
from app.services.workflow_service import WorkflowStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database schema is initialized for test execution."""
    init_db()


HIGH_RISK_NARRATIVE_1 = (
    "Electrician began maintenance on energized 4160V motor control center without verified "
    "isolation or LOTO locks installed. Arc flash boundary not established."
)

HIGH_RISK_NARRATIVE_2 = (
    "Technician started maintenance on energized pump motor without verified isolation and lockout. "
    "Stored energy not discharged, high voltage hazard present."
)

HIGH_RISK_NARRATIVE_3 = (
    "Operator entered energized electrical transformer bay without verified electrical isolation or lock. "
    "Zero energy state not verified."
)


def test_high_priority_triggers_automated_workflow():
    """
    Verify the 5-step automated workflow sequence when analysis produces HIGH priority:
    1. save the report
    2. mark it HIGH priority
    3. place it in the HSE review queue
    4. create an alert/event ("HIGH PRIORITY → HSE REVIEW REQUIRED")
    5. record the event in audit_logs
    """
    repo = get_repository()

    # Trigger analysis via API
    response = client.post(
        "/api/v1/analyze-report",
        json={"report_text": HIGH_RISK_NARRATIVE_1},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    report_id = data["report_id"]

    # 1. Verify report saved
    stored = repo.get(report_id)
    assert stored is not None
    assert stored.report_id == report_id

    # 2. Verify marked HIGH priority
    assert data["priority"] == "HIGH"
    assert stored.final_priority == PriorityLevel.HIGH

    # 3. Verify placed in HSE review queue with proper workflow status
    assert stored.in_review_queue is True
    assert stored.queue_entered_at is not None
    assert stored.workflow_status == WorkflowStatus.HSE_REVIEW_REQUIRED
    assert data["workflow_status"] == WorkflowStatus.HSE_REVIEW_REQUIRED
    assert data["in_review_queue"] is True
    assert data["alert_triggered"] is True

    # 4. Verify internal alert/event created
    alerts_res = client.get("/api/v1/alerts")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert alerts_data["total"] >= 1

    matching_alerts = [a for a in alerts_data["alerts"] if a["report_id"] == report_id]
    assert len(matching_alerts) >= 1
    alert = matching_alerts[0]
    assert alert["title"] == "HIGH PRIORITY → HSE REVIEW REQUIRED"
    assert alert["severity"] == "HIGH"
    assert alert["workflow_status"] == WorkflowStatus.HSE_REVIEW_REQUIRED
    assert alert["acknowledged"] is False
    assert alert["created_at"] is not None

    # 5. Verify recorded in audit_logs
    audit_res = client.get(f"/api/v1/reports/{report_id}/audit-trail")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()

    alert_logs = [l for l in audit_data["logs"] if l["action"] == "ALERT_TRIGGERED"]
    assert len(alert_logs) >= 1
    escalation_log = alert_logs[0]
    assert escalation_log["actor_id"] == "SIF_SENTINEL_AUTOMATION"
    assert escalation_log["details"]["alert_title"] == "HIGH PRIORITY → HSE REVIEW REQUIRED"
    assert escalation_log["details"]["priority"] == "HIGH"
    assert escalation_log["details"]["workflow_status"] == WorkflowStatus.HSE_REVIEW_REQUIRED


def test_low_priority_does_not_trigger_high_alert():
    """
    Verify deterministic branching: LOW priority reports do NOT trigger
    high-priority escalation alerts or enter the HSE queue.
    """
    repo = get_repository()
    low_risk_narrative = (
        "Warehouse floor routine inspection conducted. Janitor swept trash and "
        "replaced empty trash bags. No hazards observed."
    )

    response = client.post(
        "/api/v1/analyze-report",
        json={"report_text": low_risk_narrative},
    )
    assert response.status_code == 200
    data = response.json()
    report_id = data["report_id"]

    assert data["priority"] == "LOW"
    stored = repo.get(report_id)
    assert stored is not None
    assert stored.workflow_status == WorkflowStatus.CONTROLLED
    assert stored.in_review_queue is False
    assert stored.queue_entered_at is None

    # Assert no active alert for this report
    alerts_res = client.get("/api/v1/alerts")
    alerts_data = alerts_res.json()
    matching_alerts = [a for a in alerts_data["alerts"] if a["report_id"] == report_id]
    assert len(matching_alerts) == 0


def test_alert_acknowledgement_endpoint():
    """
    Verify that an HSE officer can acknowledge an alert via POST /api/v1/alerts/{id}/acknowledge.
    """
    res = client.post("/api/v1/analyze-report", json={"report_text": HIGH_RISK_NARRATIVE_2})
    data = res.json()
    assert data["priority"] == "HIGH"
    report_id = data["report_id"]

    alerts_res = client.get("/api/v1/alerts?acknowledged=false")
    alerts = [a for a in alerts_res.json()["alerts"] if a["report_id"] == report_id]
    assert len(alerts) >= 1
    alert_id = alerts[0]["alert_id"]

    # Acknowledge the alert
    ack_res = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"officer_id": "HSE-SUPERVISOR-99", "notes": "Incident flagged for immediate inspection."},
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["acknowledged"] is True
    assert ack_data["acknowledged_by"] == "HSE-SUPERVISOR-99"
    assert ack_data["acknowledged_at"] is not None


def test_hse_review_resolves_workflow_and_alerts():
    """
    Verify that submitting an HSE review transitions workflow_status and resolves active alerts.
    """
    res = client.post("/api/v1/analyze-report", json={"report_text": HIGH_RISK_NARRATIVE_3})
    data = res.json()
    assert data["priority"] == "HIGH"
    report_id = data["report_id"]

    repo = get_repository()
    stored = repo.get(report_id)
    assert stored.workflow_status == WorkflowStatus.HSE_REVIEW_REQUIRED
    assert stored.in_review_queue is True

    # HSE Officer reviews and confirms
    review_res = client.post(
        "/api/v1/hse-review",
        json={
            "report_id": report_id,
            "reviewer_id": "HSE-SENIOR-OFFICER",
            "decision": "confirmed",
            "comments": "Confirmed critical electrical barrier violation.",
        },
    )
    assert review_res.status_code == 200

    # Verify workflow transition
    updated = repo.get(report_id)
    assert updated.workflow_status == WorkflowStatus.REVIEWED_CONFIRMED
    assert updated.in_review_queue is False

    # Verify audit trail records WORKFLOW_TRANSITION
    audit_res = client.get(f"/api/v1/reports/{report_id}/audit-trail")
    actions = [l["action"] for l in audit_res.json()["logs"]]
    assert "WORKFLOW_TRANSITION" in actions


def test_workflow_status_endpoint():
    """
    Verify GET /api/v1/workflow/status/{report_id} returns lifecycle status and display badge.
    """
    res = client.post("/api/v1/analyze-report", json={"report_text": HIGH_RISK_NARRATIVE_1})
    data = res.json()
    assert data["priority"] == "HIGH"
    report_id = data["report_id"]

    wf_res = client.get(f"/api/v1/workflow/status/{report_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()

    assert wf_data["report_id"] == report_id
    assert wf_data["priority"] == "HIGH"
    assert wf_data["workflow_status"] == WorkflowStatus.HSE_REVIEW_REQUIRED
    assert wf_data["in_review_queue"] is True
    assert wf_data["queue_entered_at"] is not None
    assert wf_data["display_badge"] == "HIGH PRIORITY → HSE REVIEW REQUIRED"
    assert len(wf_data["active_alerts"]) >= 1


def test_dashboard_summary_includes_active_alerts():
    """
    Verify GET /api/v1/dashboard-summary provides active alerts and unread alert count.
    """
    sum_res = client.get("/api/v1/dashboard-summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()

    assert "active_alerts" in sum_data
    assert "unread_alerts_count" in sum_data
    assert isinstance(sum_data["active_alerts"], list)
    assert isinstance(sum_data["unread_alerts_count"], int)
