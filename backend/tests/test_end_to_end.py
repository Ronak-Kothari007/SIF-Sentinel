"""
SIF Sentinel — Phase 15: Complete End-to-End Workflow Test
==========================================================

Executes the complete, authoritative 9-step industrial safety lifecycle:
  1. Submit report (Ingestion)
  2. Analyze (Full synthesis pipeline)
  3. Detect SIF precursor (ML classifier)
  4. Generate priority (Composite scoring & safety policy)
  5. Trigger rule (Deterministic life-saving rules)
  6. Save result (Dual repository & PostgreSQL persistence, automated escalation)
  7. Show dashboard (Real-time executive aggregation)
  8. HSE confirms/corrects (Human-in-the-loop review with dual-view preservation)
  9. Audit trail records decision (Append-only immutable governance trail)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.decision import PriorityLevel

client = TestClient(app)


class TestCompleteEndToEndLifecycle:
    """End-to-End verification across all 9 operational safety steps."""

    def test_complete_9_step_sif_workflow(self):
        report_id = "E2E-SIF-001"
        report_text = "Maintenance started on energized equipment without verified isolation."
        location = "Substation 4"

        # -------------------------------------------------------------------
        # Step 1: Submit Report & Step 2: Analyze
        # -------------------------------------------------------------------
        payload = {
            "report_id": report_id,
            "report_text": report_text,
            "location": location,
        }
        analyze_resp = client.post("/api/v1/analyze-report", json=payload)
        assert analyze_resp.status_code == 200, f"Analysis failed: {analyze_resp.text}"
        data = analyze_resp.json()

        # -------------------------------------------------------------------
        # Step 3: Detect SIF Precursor
        # -------------------------------------------------------------------
        assert data["report_id"] == report_id
        assert "sif_probability" in data
        assert isinstance(data["sif_probability"], float)
        assert data["sif_probability"] >= 0.40, "SIF precursor signal was not detected"

        # -------------------------------------------------------------------
        # Step 4: Generate Priority
        # -------------------------------------------------------------------
        assert data["priority"] == "HIGH", "High hazard unverified isolation must yield HIGH priority"
        assert data["priority_score"] >= 0.65
        assert "structured_explanation" in data
        structured_exp = data["structured_explanation"]
        assert structured_exp["priority"] == "HIGH"
        assert len(structured_exp["why"]) >= 3
        assert "Priority: HIGH" in structured_exp["formatted_text"]
        assert "predict" in data["governance_notice"].lower()
        assert "does not predict accident" in data["explanation"].lower()

        # -------------------------------------------------------------------
        # Step 5: Trigger Rule
        # -------------------------------------------------------------------
        triggered_rules = data.get("triggered_rules", [])
        assert len(triggered_rules) >= 1, "Expected deterministic safety rules to trigger"
        rule_categories = [r.get("category") for r in triggered_rules]
        assert "Energy Isolation" in rule_categories, "Energy Isolation life-saving rule should trigger"
        assert any(r.get("severity", 0) >= 3 for r in triggered_rules)

        # -------------------------------------------------------------------
        # Step 6: Save Result & Automated Workflow Escalation
        # -------------------------------------------------------------------
        # Verify report can be retrieved by ID
        get_resp = client.get(f"/api/v1/reports/{report_id}")
        assert get_resp.status_code == 200
        saved = get_resp.json()
        assert saved["report_id"] == report_id
        assert saved["in_review_queue"] is True, "HIGH priority report must enter HSE review queue"
        assert saved["workflow_status"] == "HSE_REVIEW_REQUIRED"

        # Verify automated escalation alert was triggered
        alerts_resp = client.get("/api/v1/alerts")
        assert alerts_resp.status_code == 200
        alerts_data = alerts_resp.json()
        alerts_list = alerts_data.get("alerts", alerts_data.get("items", []))
        matching_alerts = [a for a in alerts_list if a["report_id"] == report_id]
        assert len(matching_alerts) >= 1
        alert = matching_alerts[0]
        assert "HIGH PRIORITY" in alert.get("title", alert.get("headline", ""))

        # -------------------------------------------------------------------
        # Step 7: Show Dashboard
        # -------------------------------------------------------------------
        dash_resp = client.get("/api/v1/dashboard-summary")
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()

        assert dash_data["total_reports"] >= 1
        assert dash_data["high_priority_count"] >= 1
        assert dash_data["ai_distribution"]["HIGH"] >= 1
        hazard_names = [h["hazard"] for h in dash_data.get("top_hazards", [])]
        assert "Electrical Energy" in hazard_names or any("electrical" in h.lower() for h in hazard_names)

        # -------------------------------------------------------------------
        # Step 8: HSE Confirms / Corrects (Human-in-the-Loop)
        # -------------------------------------------------------------------
        review_payload = {
            "report_id": report_id,
            "decision": "corrected",
            "reviewer_id": "HSE-LEAD-007",
            "corrected_priority": PriorityLevel.HIGH,
            "corrected_activity": "Emergency Electrical Isolation",
            "corrected_hazard": "High Voltage Electrical Arc",
            "corrected_barrier": "Physical Lockout Padlock",
            "comments": "Confirmed active LOTO violation on main breaker. Padlocks installed and stop work notice posted.",
        }
        review_resp = client.post("/api/v1/hse-review", json=review_payload)
        assert review_resp.status_code == 200
        rev_data = review_resp.json()
        assert rev_data["decision"] == "corrected"
        assert rev_data["original_ai_output"] is not None, "Original AI prediction must be preserved!"
        assert rev_data["original_ai_output"]["priority"] == "HIGH"

        # Verify dual-view state on report retrieval
        retrieved_resp = client.get(f"/api/v1/reports/{report_id}")
        retrieved = retrieved_resp.json()
        assert retrieved["hse_reviewed"] is True
        assert retrieved["review_decision"] == "corrected"
        assert retrieved["final_activity"] == "Emergency Electrical Isolation"
        assert retrieved["activity"] == "Maintenance", "Original AI activity must not be overwritten"

        # -------------------------------------------------------------------
        # Step 9: Audit Trail Records Decision
        # -------------------------------------------------------------------
        audit_resp = client.get(f"/api/v1/reports/{report_id}/audit-trail")
        assert audit_resp.status_code == 200
        audit_data = audit_resp.json()
        assert audit_data["total_logs"] >= 2, "Expected at least ANALYZE_REPORT and HSE_REVIEW logs"

        actions = [log["action"] for log in audit_data["logs"]]
        assert "ANALYZE_REPORT" in actions, "Audit trail missing report analysis log"
        assert "HSE_REVIEW" in actions, "Audit trail missing HSE review decision log"

        # Verify HSE review log integrity
        review_log = next(log for log in audit_data["logs"] if log["action"] == "HSE_REVIEW")
        assert review_log["actor_id"] == "HSE-LEAD-007"
        assert review_log["details"]["decision"] == "corrected"
        assert "LOTO violation" in review_log["details"]["comments"]
        assert review_log.get("created_at") is not None
