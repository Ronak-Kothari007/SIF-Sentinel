"""
SIF Sentinel — Database Seed Script (Phase 9)
=============================================

Seeds initial users, roles, synthetic safety reports, predictions,
extracted entities, triggered rules, and HSE reviews for local development.

Run:
  python backend/app/db/seed.py
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

# Add backend to sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.db.models import User, Report
from app.db.session import SessionLocal, init_db
from app.services.decision_engine import SIFDecisionEngine
from app.services.db_service import DatabaseService


def _hash_pw(password: str) -> str:
    """Deterministic hash for seeding demo users without external bcrypt dependency."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_database(max_reports: int = 25) -> None:
    """Initialize schema and insert seed records."""
    print("Initializing database tables...")
    init_db()

    db = SessionLocal()
    engine = SIFDecisionEngine()

    try:
        # 1. Seed Users
        existing_users = db.query(User).count()
        if existing_users == 0:
            print("Seeding initial users...")
            demo_users = [
                User(
                    username="admin",
                    email="admin@sifsentinel.internal",
                    hashed_password=_hash_pw("AdminPass2026!"),
                    full_name="System Administrator",
                    role="admin",
                ),
                User(
                    username="hse_officer_1",
                    email="officer1@sifsentinel.internal",
                    hashed_password=_hash_pw("HseReview2026!"),
                    full_name="Senior HSE Officer Ronak",
                    role="hse_officer",
                ),
                User(
                    username="site_supervisor",
                    email="supervisor@sifsentinel.internal",
                    hashed_password=_hash_pw("Supervisor2026!"),
                    full_name="Field Operations Supervisor",
                    role="site_supervisor",
                ),
            ]
            db.add_all(demo_users)
            db.commit()
            print(f"  Inserted {len(demo_users)} users.")
        else:
            print(f"Users already seeded ({existing_users} found).")

        # 2. Seed Reports from synthetic CSV
        existing_reports = db.query(Report).count()
        if existing_reports == 0:
            csv_path = _BACKEND_DIR.parent / "dataset" / "raw" / "synthetic_sample.csv"
            if csv_path.exists():
                print(f"Seeding reports from {csv_path.name}...")
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    seeded_count = 0
                    for i, row in enumerate(reader):
                        if i >= max_reports:
                            break
                        rep_id = row.get("report_id", f"SYN-{i+1:03d}")
                        text = row.get("report_text", "")
                        loc = row.get("location", "Unknown")
                        source = row.get("source", "synthetic")
                        sev = row.get("severity", "medium")

                        # Create Report
                        DatabaseService.create_report(
                            db=db,
                            report_id=rep_id,
                            report_text=text,
                            location=loc,
                            severity_self_rated=sev,
                            source=source,
                        )

                        # Evaluate and save prediction + rules
                        analysis = engine.evaluate(text, report_id=rep_id)
                        DatabaseService.save_analysis(db=db, report_id=rep_id, analysis=analysis)

                        # Save extracted entities if any
                        ctx = engine.extractor.extract(text)
                        if ctx.entities:
                            DatabaseService.save_entities(db=db, report_id=rep_id, entities=ctx.entities)

                        seeded_count += 1

                    # Add an initial HSE review on the first report
                    first_rep = db.query(Report).first()
                    if first_rep:
                        DatabaseService.save_hse_review(
                            db=db,
                            report_id=first_rep.id,
                            reviewer_id="hse_officer_1",
                            decision="confirmed",
                            original_priority="HIGH",
                            final_priority="HIGH",
                            comments="Verified LOTO compliance failure during morning shift handover.",
                        )

                    print(f"  Inserted {seeded_count} reports with predictions, entities, and rules.")
        else:
            print(f"Reports already seeded ({existing_reports} found).")

        print("Database seeding completed successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
