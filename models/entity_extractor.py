"""
SIF Sentinel — Safety Context / Entity Extraction CLI & Pipeline Module
=======================================================================

Provides convenient access to the Phase 6 Safety Context Extractor:
- Python API: `extract_safety_context(text: str) -> dict`
- CLI tool:
    python models/entity_extractor.py --text "..."
    python models/entity_extractor.py --demo
    python models/entity_extractor.py --input dataset/raw/synthetic_sample.csv --output dataset/processed/extracted_sample.csv
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

from app.schemas.context import EntityType, ExtractedEntity, SafetyContext
from app.services.extractor import (
    BaseEntityExtractor,
    DeterministicExtractor,
    HybridSafetyExtractor,
    NLPExtractor,
    TransformerNERExtractor,
)


def extract_safety_context(text: str, config_path: Optional[Path | str] = None) -> dict[str, Any]:
    """
    Convenience function: extracts structured safety context as a dict.

    Args:
        text: Safety observation or incident report text.
        config_path: Optional custom path to extraction rules YAML.

    Returns:
        Structured dictionary matching the SafetyContext schema.
    """
    extractor = HybridSafetyExtractor(config_path=config_path)
    result = extractor.extract(text)
    return result.to_dict()


def batch_extract(texts: list[str], config_path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    """
    Run extraction on a batch of report texts.
    """
    extractor = HybridSafetyExtractor(config_path=config_path)
    return [extractor.extract(t).to_dict() for t in texts]


def run_demo() -> None:
    """Run extraction demo on diverse synthetic safety reports."""
    sample_reports = [
        "Maintenance started on energized equipment without verified isolation.",
        "Technician entered confined storage tank without completing gas test. Attendant was absent.",
        "Worker observed on top of scaffold at 6 metres without harness. Guardrail missing.",
        "Welding operation was being carried out in process area without hot work permit or fire watch.",
        "Workers found standing below crane load within exclusion zone. No barricade present.",
        "Routine safety meeting conducted in office block. All workers attended. No incidents to report.",
    ]

    extractor = HybridSafetyExtractor()
    print("=" * 80)
    print("SIF SENTINEL — SAFETY CONTEXT EXTRACTION DEMO (SYNTHETIC SAMPLES)")
    print("=" * 80)

    for i, text in enumerate(sample_reports, 1):
        print(f"\n[Sample {i}] Input: \"{text}\"")
        res = extractor.extract(text)
        print("-" * 50)
        print(f"  Activity       : {res.activity} (conf: {res.activity_confidence})")
        print(f"  Hazard         : {res.hazard} [Category: {res.hazard_category}]")
        print(f"  Barrier        : {res.barrier}")
        print(f"  Barrier Status : {res.barrier_status}")
        print(f"  Location       : {res.location}")
        print(f"  Equipment      : {res.equipment}")
        print(f"  Entities Found : {len(res.entities)} spans")
        print(f"  Summary        : {res.summary}")

    print("\n" + "=" * 80)


def process_csv(input_path: Path, output_path: Path) -> None:
    """Read reports CSV, perform entity extraction, and write augmented CSV."""
    if not input_path.exists():
        print(f"Error: input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    extractor = HybridSafetyExtractor()
    rows: list[dict[str, Any]] = []

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            text = row.get("report_text", "")
            ctx = extractor.extract(text)
            row["extracted_activity"] = ctx.activity or ""
            row["extracted_hazard"] = ctx.hazard or ""
            row["extracted_barrier"] = ctx.barrier or ""
            row["extracted_barrier_status"] = ctx.barrier_status or ""
            row["extracted_location"] = ctx.location or ""
            row["extracted_equipment"] = ctx.equipment or ""
            row["extraction_summary"] = ctx.summary
            rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_fields = fieldnames + [
        "extracted_activity",
        "extracted_hazard",
        "extracted_barrier",
        "extracted_barrier_status",
        "extracted_location",
        "extracted_equipment",
        "extraction_summary",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully processed {len(rows)} records.")
    print(f"Saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIF Sentinel — Safety Context Extractor")
    parser.add_argument("--text", type=str, help="Single report text to analyze")
    parser.add_argument("--demo", action="store_true", help="Run demonstration on synthetic reports")
    parser.add_argument("--input", type=Path, help="Path to input CSV file")
    parser.add_argument("--output", type=Path, help="Path to output CSV file")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON output")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if args.input and args.output:
        process_csv(args.input, args.output)
        return

    if args.text:
        res = extract_safety_context(args.text)
        print(json.dumps(res, indent=2 if args.pretty else None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
