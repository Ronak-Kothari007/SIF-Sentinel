"""
SIF Sentinel — Decision Engine CLI & Pipeline Module (Phase 7)
==============================================================

Provides command-line and programmatic access to the composite SIF Sentinel
Decision Engine:
- Python API: `evaluate_report(text: str) -> dict`
- CLI tool:
    python models/decision_engine.py --text "..."
    python models/decision_engine.py --demo
    python models/decision_engine.py --input dataset/raw/synthetic_sample.csv --output dataset/processed/decisions_sample.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure backend is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for path in [_REPO_ROOT, _BACKEND_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.schemas.decision import DecisionInput, DecisionResult, PriorityLevel
from app.services.decision_engine import SIFDecisionEngine, decide_report


def evaluate_report(
    text: str,
    report_id: Optional[str] = None,
    recurring_risk_signal: Optional[float] = None,
    config_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """
    Evaluate a single report text and return the result dictionary.
    """
    engine = SIFDecisionEngine(config_path=config_path)
    result = engine.evaluate(text, report_id=report_id, recurring_risk_signal=recurring_risk_signal)
    return result.to_dict()


def batch_evaluate(
    texts: list[str],
    config_path: Optional[Path | str] = None,
) -> list[dict[str, Any]]:
    """
    Evaluate a batch of report texts.
    """
    engine = SIFDecisionEngine(config_path=config_path)
    return [engine.evaluate(t).to_dict() for t in texts]


def run_demo() -> None:
    """Run demonstration across high, medium, and low priority synthetic reports."""
    sample_reports = [
        (
            "SYN-001",
            "Maintenance started on energized equipment without verified isolation.",
            None,
        ),
        (
            "SYN-002",
            "Technician entered confined storage tank without completing gas test. Attendant was absent.",
            None,
        ),
        (
            "SYN-003",
            "Worker on top of scaffold at 6 metres without harness. Guardrail missing on one side.",
            0.65,  # Recurring risk signal
        ),
        (
            "SYN-004",
            "Forklift driver operated near pedestrian walkway with obscured view. Spotter absent.",
            None,
        ),
        (
            "SYN-005",
            "Housekeeping inspection revealed small oil puddle near pump room entrance. Area cordoned off.",
            None,
        ),
        (
            "SYN-006",
            "Toolbox safety meeting conducted at start of shift. JSA reviewed and all workers signed.",
            None,
        ),
    ]

    engine = SIFDecisionEngine()
    print("=" * 80)
    print("SIF SENTINEL — DECISION ENGINE TRIAGE DEMO (SYNTHETIC SAMPLES)")
    print("=" * 80)

    for rep_id, text, rec_sig in sample_reports:
        print(f"\n[Report: {rep_id}] Input: \"{text}\"")
        res = engine.evaluate(text, report_id=rep_id, recurring_risk_signal=rec_sig)
        print("-" * 50)
        print(f"  Priority       : {res.priority.value} (score: {res.priority_score:.3f})")
        print(f"  SIF Prob       : {res.sif_probability:.2%}")
        print(f"  Activity       : {res.activity}")
        print(f"  Hazard         : {res.hazard}")
        print(f"  Barrier        : {res.barrier} [Status: {res.barrier_status}]")
        print(f"  Rules Fired    : {len(res.triggered_rules)} rules ({', '.join(r.rule_name for r in res.triggered_rules) if res.triggered_rules else 'None'})")
        print(f"  Evidence       : {res.evidence}")
        print(f"  Explanation    : {res.explanation}")

    print("\n" + "=" * 80)


def process_csv(input_path: Path, output_path: Path) -> None:
    """Batch process a safety reports CSV with the decision engine."""
    if not input_path.exists():
        print(f"Error: input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    engine = SIFDecisionEngine()
    rows: list[dict[str, Any]] = []

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            rep_id = row.get("report_id", "")
            text = row.get("report_text", "")
            res = engine.evaluate(text, report_id=rep_id)

            row["priority"] = res.priority.value
            row["priority_score"] = f"{res.priority_score:.4f}"
            row["sif_probability"] = f"{res.sif_probability:.4f}"
            row["decision_activity"] = res.activity or ""
            row["decision_hazard"] = res.hazard or ""
            row["decision_barrier"] = res.barrier or ""
            row["decision_barrier_status"] = res.barrier_status or ""
            row["rules_fired_count"] = str(len(res.triggered_rules))
            row["decision_explanation"] = res.explanation
            rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_fields = fieldnames + [
        "priority",
        "priority_score",
        "sif_probability",
        "decision_activity",
        "decision_hazard",
        "decision_barrier",
        "decision_barrier_status",
        "rules_fired_count",
        "decision_explanation",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully processed {len(rows)} records.")
    print(f"Saved decisions to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIF Sentinel — Decision Engine")
    parser.add_argument("--text", type=str, help="Safety report text to evaluate")
    parser.add_argument("--report-id", type=str, default=None, help="Optional report ID")
    parser.add_argument("--demo", action="store_true", help="Run triage demo on diverse synthetic reports")
    parser.add_argument("--input", type=Path, help="Path to input CSV file")
    parser.add_argument("--output", type=Path, help="Path to output CSV file")
    parser.add_argument("--recurrence", type=float, default=None, help="Optional recurrence factor (0.0–1.0)")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON output")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if args.input and args.output:
        process_csv(args.input, args.output)
        return

    if args.text:
        res = evaluate_report(args.text, report_id=args.report_id, recurring_risk_signal=args.recurrence)
        print(json.dumps(res, indent=2 if args.pretty else None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
