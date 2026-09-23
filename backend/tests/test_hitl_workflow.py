"""
SIF Sentinel — Automated Tests for Phase 12 (Human-in-the-Loop Workflow)
========================================================================

Verifies:
1. CONFIRM, REJECT, and CORRECT actions
2. Multi-dimensional correction (priority, activity, hazard, barrier)
3. Non-destructive dual storage (original AI prediction vs. HSE determination)
4. Immutable audit trail generation and retrieval
5. User feedback endpoint (POST and GET /api/v1/feedback)
6. Executive dashboard AI result vs. HSE result distribution and review status
"""

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.schemas.decision import PriorityLevel
from app.services.report_store import get_repository


@pytest.fixture(scope="module")
def client():
    # Ensure repository is initialized and seeded
    repo = get_repository()
    repo.seed_from_csv()
    with TestClient(app) as c:
        yield c


def test_hse_confirm_action(client):
    """Verify HSE CONFIRM action validates AI prediction without modifications."""
    # First analyze a report
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Scaffold worker at 8m height disconnected lanyard to move across platform."},
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    rep_id = rep_data["report_id"]
    orig_priority = rep_data["priority"]

    # Submit CONFIRM
    review_res = client.post(
        "/api/v1/hse-review",
        json={
            "report_id": rep_id,
            "reviewer_id": "HSE-LEAD-01",
            "decision": "confirmed",
            "comments": "Confirmed work at height violation; 100% tie-off mandatory.",
        },
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["status"] == "success"
    assert rev_data["decision"] == "confirmed"
    assert rev_data["final_priority"] == orig_priority
    assert rev_data["original_ai_output"]["priority"] == orig_priority

    # Verify report state
    get_res = client.get(f"/api/v1/reports/{rep_id}")
    assert get_res.status_code == 200
    report_details = get_res.json()
    assert report_details["hse_reviewed"] is True
    assert report_details["review_decision"] == "confirmed"
    assert report_details["reviewer_id"] == "HSE-LEAD-01"
    assert report_details["final_priority"] == orig_priority


def test_hse_reject_action(client):
    """Verify HSE REJECT action marks non-precursor and de-escalates priority to LOW."""
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Spill kit missing secondary absorbent pad in maintenance warehouse."},
    )
    assert rep_res.status_code == 200
    rep_id = rep_res.json()["report_id"]

    # Submit REJECT
    review_res = client.post(
        "/api/v1/hse-review",
        json={
            "report_id": rep_id,
            "reviewer_id": "HSE-OFFICER-04",
            "decision": "rejected",
            "comments": "Minor housekeeping issue; no high energy present, not a SIF precursor.",
        },
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()
    assert rev_data["decision"] == "rejected"
    assert rev_data["final_priority"] == "LOW"

    # Verify report
    get_res = client.get(f"/api/v1/reports/{rep_id}")
    report_details = get_res.json()
    assert report_details["hse_reviewed"] is True
    assert report_details["review_decision"] == "rejected"
    assert report_details["final_priority"] == "LOW"


def test_hse_correct_action_multi_dimension(client):
    """
    CRITICAL REQUIREMENT: CORRECT allows changing:
    - priority
    - activity
    - hazard
    - barrier
    """
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Mechanic cleaned hydraulic line near compressor station using solvent."},
    )
    assert rep_res.status_code == 200
    orig_data = rep_res.json()
    rep_id = orig_data["report_id"]

    # Submit CORRECT with all 4 dimensions
    review_res = client.post(
        "/api/v1/hse-review",
        json={
            "report_id": rep_id,
            "reviewer_id": "HSE-SUPERVISOR-99",
            "decision": "corrected",
            "corrected_priority": "HIGH",
            "corrected_activity": "Chemical Handling",
            "corrected_hazard": "Toxic / Hazardous Substances",
            "corrected_barrier": "Personal Protective Equipment",
            "comments": "High pressure hydraulic line was pressurized; flammable solvent in enclosed area.",
        },
    )
    assert review_res.status_code == 200
    rev_data = review_res.json()

    assert rev_data["decision"] == "corrected"
    assert rev_data["final_priority"] == "HIGH"
    assert rev_data["final_activity"] == "Chemical Handling"
    assert rev_data["final_hazard"] == "Toxic / Hazardous Substances"
    assert rev_data["final_barrier"] == "Personal Protective Equipment"

    # Verify corrected_values snapshot returned
    assert rev_data["corrected_values"]["priority"] == "HIGH"
    assert rev_data["corrected_values"]["activity"] == "Chemical Handling"
    assert rev_data["corrected_values"]["hazard"] == "Toxic / Hazardous Substances"
    assert rev_data["corrected_values"]["barrier"] == "Personal Protective Equipment"


def test_original_ai_prediction_preservation(client):
    """
    CRITICAL REQUIREMENT: HSE correction must NOT silently overwrite the original AI prediction.
    Store both.
    """
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Forklift driver carried empty pallet in loading bay."},
    )
    assert rep_res.status_code == 200
    initial_analysis = rep_res.json()
    rep_id = initial_analysis["report_id"]

    orig_prob = initial_analysis["sif_probability"]
    orig_prio = initial_analysis["priority"]
    orig_act = initial_analysis["activity"]
    orig_haz = initial_analysis["hazard"]
    orig_bar = initial_analysis["barrier"]

    # Now apply a severe correction
    client.post(
        "/api/v1/hse-review",
        json={
            "report_id": rep_id,
            "reviewer_id": "CHIEF-SAFETY-OFFICER",
            "decision": "corrected",
            "corrected_priority": "HIGH",
            "corrected_activity": "Material Handling / Forklift Operations",
            "corrected_hazard": "Struck-By Mobile Plant",
            "corrected_barrier": "Physical Exclusion Zone",
            "comments": "Pedestrian walked in direct line of forklift blind spot.",
        },
    )

    # Fetch report and verify BOTH original AI output and HSE determination coexist
    get_res = client.get(f"/api/v1/reports/{rep_id}")
    report_details = get_res.json()

    # Original AI values must remain intact!
    assert report_details["priority"] == orig_prio, "Original AI priority must not be overwritten"
    assert report_details["sif_probability"] == orig_prob, "Original AI probability must not be overwritten"
    assert report_details["activity"] == orig_act, "Original AI activity must not be overwritten"
    assert report_details["hazard"] == orig_haz, "Original AI hazard must not be overwritten"
    assert report_details["barrier"] == orig_bar, "Original AI barrier must not be overwritten"

    # Human determinations are stored alongside:
    assert report_details["final_priority"] == "HIGH"
    assert report_details["final_activity"] == "Material Handling / Forklift Operations"
    assert report_details["final_hazard"] == "Struck-By Mobile Plant"
    assert report_details["final_barrier"] == "Physical Exclusion Zone"
    assert report_details["review_decision"] == "corrected"
    assert report_details["reviewer_id"] == "CHIEF-SAFETY-OFFICER"


def test_audit_trail_generation_and_endpoint(client):
    """Verify audit trail records creation, review events, and provides GET endpoint."""
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Hot work began on storage tank roof with no fire watch posted."},
    )
    rep_id = rep_res.json()["report_id"]

    # Submit review
    client.post(
        "/api/v1/hse-review",
        json={
            "report_id": rep_id,
            "reviewer_id": "AUDITOR-01",
            "decision": "confirmed",
            "comments": "Confirmed critical barrier failure. Hot work stopped.",
        },
    )

    # Call audit trail endpoint
    trail_res = client.get(f"/api/v1/reports/{rep_id}/audit-trail")
    assert trail_res.status_code == 200
    trail_data = trail_res.json()

    assert trail_data["report_id"] == rep_id
    assert trail_data["total_logs"] >= 2  # Creation/Analysis log + HSE Review log

    actions = [log["action"] for log in trail_data["logs"]]
    assert "ANALYZE_REPORT" in actions
    assert "HSE_REVIEW" in actions

    # Inspect the HSE_REVIEW log entry
    review_log = next(log for log in trail_data["logs"] if log["action"] == "HSE_REVIEW")
    assert review_log["actor_id"] == "AUDITOR-01"
    assert review_log["details"]["decision"] == "confirmed"
    assert "original_ai_output" in review_log["details"]
    assert "final_determination" in review_log["details"]


def test_feedback_endpoint(client):
    """Verify POST and GET /api/v1/feedback endpoint."""
    rep_res = client.post(
        "/api/v1/analyze-report",
        json={"report_text": "Electrician checked control cabinet voltage using calibrated multimeter."},
    )
    rep_id = rep_res.json()["report_id"]

    # Submit feedback
    fb_res = client.post(
        "/api/v1/feedback",
        json={
            "report_id": rep_id,
            "feedback_type": "false_positive",
            "user_suggested_priority": "LOW",
            "notes": "Work was performed de-energized under verified lockout tagout permit. Model false positive.",
            "user_id": "OPERATOR-SITE-B",
        },
    )
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["status"] == "success"
    assert fb_data["report_id"] == rep_id
    assert fb_data["feedback_type"] == "false_positive"
    assert fb_data["feedback_id"].startswith("FB-")

    # Verify GET /api/v1/feedback filtered by report_id
    query_res = client.get(f"/api/v1/feedback?report_id={rep_id}")
    assert query_res.status_code == 200
    fb_list = query_res.json()
    assert len(fb_list) >= 1
    assert fb_list[0]["notes"] == "Work was performed de-energized under verified lockout tagout permit. Model false positive."

    # Verify audit trail contains FEEDBACK_SUBMITTED
    trail_res = client.get(f"/api/v1/reports/{rep_id}/audit-trail")
    actions = [log["action"] for log in trail_res.json()["logs"]]
    assert "FEEDBACK_SUBMITTED" in actions


def test_dashboard_ai_vs_hse_summary(client):
    """
    CRITICAL REQUIREMENT: Update the dashboard to show:
    - AI result
    - HSE result
    - review status
    """
    res = client.get("/api/v1/dashboard-summary")
    assert res.status_code == 200
    data = res.json()

    # AI distribution
    assert "ai_distribution" in data
    assert "HIGH" in data["ai_distribution"]
    assert "MEDIUM" in data["ai_distribution"]
    assert "LOW" in data["ai_distribution"]

    # HSE distribution
    assert "hse_distribution" in data
    assert "HIGH" in data["hse_distribution"]
    assert "MEDIUM" in data["hse_distribution"]
    assert "LOW" in data["hse_distribution"]
    assert "UNREVIEWED" in data["hse_distribution"]

    # Review status breakdown
    assert "review_status" in data
    rev_status = data["review_status"]
    assert "pending" in rev_status
    assert "confirmed" in rev_status
    assert "corrected" in rev_status
    assert "rejected" in rev_status
    assert "total_reviewed" in rev_status

    # Agreement rate
    assert "agreement_rate" in data
    assert 0.0 <= data["agreement_rate"] <= 100.0
