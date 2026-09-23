"""
SIF Sentinel — Live Server Verification Script (Phase 8)
========================================================

Spawns a local Uvicorn server running app.main:app on 127.0.0.1:8008,
queries every endpoint via live HTTP requests, prints status codes and
response payloads, and cleanly terminates.
"""

import multiprocessing
import time
import httpx
import uvicorn


def run_server():
    uvicorn.run("app.main:app", host="127.0.0.1", port=8008, log_level="warning")


def main():
    print("=" * 80)
    print("STARTING LOCAL FASTAPI SERVER ON http://127.0.0.1:8008...")
    print("=" * 80)

    server_process = multiprocessing.Process(target=run_server, daemon=True)
    server_process.start()

    # Wait for server to bind
    client = httpx.Client(base_url="http://127.0.0.1:8008", timeout=15.0)
    ready = False
    for _ in range(30):
        try:
            resp = client.get("/health")
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.2)

    if not ready:
        print("Error: Server failed to start within timeout.")
        server_process.terminate()
        return

    print("Server ready! Testing all 7 API endpoints via live HTTP...\n")

    try:
        # 1. POST /api/v1/analyze-report
        print("[1/7] Testing POST /api/v1/analyze-report...")
        payload = {
            "report_text": "Maintenance started on energized equipment without verified isolation.",
            "report_id": "LIVE-TEST-001",
        }
        res1 = client.post("/api/v1/analyze-report", json=payload)
        print(f"      Status: {res1.status_code}")
        d1 = res1.json()
        print(f"      Response: Priority={d1['priority']}, Activity={d1['activity']}, Hazard={d1['hazard']}, Barrier={d1['barrier']} ({d1['barrier_status']})")
        print(f"      Explanation: {d1['explanation'][:90]}...\n")

        # 2. GET /api/v1/reports
        print("[2/7] Testing GET /api/v1/reports?limit=3...")
        res2 = client.get("/api/v1/reports?limit=3")
        print(f"      Status: {res2.status_code}")
        d2 = res2.json()
        print(f"      Total Reports: {d2['total']}, Returned: {len(d2['items'])} items\n")

        # 3. GET /api/v1/reports/{id}
        print("[3/7] Testing GET /api/v1/reports/LIVE-TEST-001...")
        res3 = client.get("/api/v1/reports/LIVE-TEST-001")
        print(f"      Status: {res3.status_code}")
        d3 = res3.json()
        print(f"      Fetched Report ID: {d3['report_id']}, Score: {d3['priority_score']}\n")

        # 4. GET /api/v1/high-risk
        print("[4/7] Testing GET /api/v1/high-risk...")
        res4 = client.get("/api/v1/high-risk?limit=3")
        print(f"      Status: {res4.status_code}")
        d4 = res4.json()
        print(f"      High-Risk Queue Length: {d4['total']}, First item: {d4['items'][0]['report_id']} ({d4['items'][0]['priority']})\n")

        # 5. GET /api/v1/patterns
        print("[5/7] Testing GET /api/v1/patterns...")
        res5 = client.get("/api/v1/patterns")
        print(f"      Status: {res5.status_code}")
        d5 = res5.json()
        top_h = d5['top_hazards'][0]['hazard'] if d5['top_hazards'] else 'None'
        print(f"      Top Hazard: {top_h}, Summary: {d5['summary']}\n")

        # 6. POST /api/v1/hse-review
        print("[6/7] Testing POST /api/v1/hse-review...")
        rev_payload = {
            "report_id": "LIVE-TEST-001",
            "reviewer_id": "HSE-LEAD-RONAK",
            "decision": "confirmed",
            "comments": "Confirmed critical LOTO bypass. Work suspended until electrical clearance verified.",
        }
        res6 = client.post("/api/v1/hse-review", json=rev_payload)
        print(f"      Status: {res6.status_code}")
        d6 = res6.json()
        print(f"      Review Recorded: {d6['status']} by {d6['reviewer_id']}, Final Priority={d6['final_priority']}\n")

        # 7. GET /api/v1/dashboard-summary
        print("[7/7] Testing GET /api/v1/dashboard-summary...")
        res7 = client.get("/api/v1/dashboard-summary")
        print(f"      Status: {res7.status_code}")
        d7 = res7.json()
        print(f"      Total: {d7['total_reports']}, HIGH: {d7['high_priority_count']}, SIF Rate: {d7['sif_precursor_rate']}%, Pending Reviews: {d7['pending_reviews_count']}\n")

        print("=" * 80)
        print("ALL 7 API V1 ENDPOINTS TESTED LIVE AND VERIFIED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        server_process.terminate()
        server_process.join(timeout=2.0)


if __name__ == "__main__":
    main()
