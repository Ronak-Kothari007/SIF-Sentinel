"""
SIF Sentinel — Controlled Demo Mode Scenarios (Phase 16)
========================================================

Curated set of 10 realistic synthetic industrial safety reports explicitly
marked as demo observations. Each scenario exercises distinct operational
conditions, hazard modes, barrier states, and deterministic safety rules:

  1. DEMO-SYN-001: Energy Isolation Failure (Critical Precursor - HIGH)
  2. DEMO-SYN-002: Confined Space Entry Violation (Critical Precursor - HIGH)
  3. DEMO-SYN-003: Working at Height without 100% Tie-Off (Critical Precursor - HIGH)
  4. DEMO-SYN-004: Hot Work in Flammable Vapor Zone (Critical Precursor - HIGH)
  5. DEMO-SYN-005: Line of Fire / Suspended Tandem Crane Lift (High Priority - HIGH)
  6. DEMO-SYN-006: Non-SIF Routine Housekeeping Observation (Baseline Control - LOW)
  7. DEMO-SYN-007: Non-SIF Ergonomic Workstation Adjustment (Baseline Control - LOW)
  8. DEMO-SYN-008: Near Miss - Forklift / Pedestrian Interface Caught in Time (MEDIUM)
  9. DEMO-SYN-009: Ambiguous Case - Subtle High-Pressure Booster Pump Vibration (Borderline)
 10. DEMO-SYN-010: Recurring Risk Pattern - Electrical Interlock Jumper Bypass (HIGH, links with #1)

All records are evaluated through the LIVE AI classifier, entity extractor,
deterministic rule engine, and Sentence Transformers embedding pipeline.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class DemoScenario(BaseModel):
    """Metadata and raw text for a controlled synthetic demo safety observation."""

    report_id: str
    title: str
    category: str
    location: str
    report_text: str
    source: str = "synthetic_demo"
    is_demo: bool = True
    expected_hazard: str
    expected_activity: str
    expected_rule_id: Optional[str] = None
    expected_priority: str
    pre_staged_review: Optional[dict[str, Any]] = None


DEMO_SCENARIOS: list[DemoScenario] = [
    # 1. Energy Isolation
    DemoScenario(
        report_id="DEMO-SYN-001",
        title="Omitted LOTO on 4160V Motor Control Center",
        category="energy_isolation",
        location="MCC Building 4 - Unit 12",
        report_text=(
            "Contractor electrician accessed energized equipment without isolation during 4160V motor control center cubicle MCC-04 maintenance. "
            "LOTO not applied and isolation not verified prior to opening the live switchgear cabinet."
        ),
        expected_hazard="Electrical Energy",
        expected_activity="Maintenance",
        expected_rule_id="RULE_001",
        expected_priority="HIGH",
        pre_staged_review={
            "decision": "confirmed",
            "reviewer_id": "HSE-LEAD-DEMO",
            "comments": "Confirmed critical life-saving rule violation. Immediate stop work issued, MCC isolated and locked out.",
        },
    ),

    # 2. Confined Space
    DemoScenario(
        report_id="DEMO-SYN-002",
        title="Unpermitted Entry into Crude Storage Tank",
        category="confined_space",
        location="Tank Farm 2 - Tank TK-102",
        report_text=(
            "Two mechanical fitters performed confined space tank entry into crude storage vessel TK-102 through bottom manway to replace internal steam coils. "
            "Gas testing absent, permit missing, and attendant absent at the entrance."
        ),
        expected_hazard="Toxic / Flammable Atmosphere",
        expected_activity="Confined Space Entry",
        expected_rule_id="RULE_002",
        expected_priority="HIGH",
    ),

    # 3. Working at Height
    DemoScenario(
        report_id="DEMO-SYN-003",
        title="Insulator on Scaffolding Top Rail without Tie-Off",
        category="working_at_height",
        location="Crude Distillation Column C-101 (Level 4)",
        report_text=(
            "Insulation technician observed working at height on scaffolding platform 8 meters above concrete deck without harness and guardrail missing. "
            "Fall protection absent on the elevated scaffold."
        ),
        expected_hazard="Fall from Height",
        expected_activity="Working at Height",
        expected_rule_id="RULE_003",
        expected_priority="HIGH",
    ),

    # 4. Hot Work in Flammable Zone
    DemoScenario(
        report_id="DEMO-SYN-004",
        title="Oxy-Acetylene Torch Cutting Near Hydrocarbon Separator",
        category="hot_work",
        location="Gas Processing Plant - Train B",
        report_text=(
            "Welders initiated hot work and cutting on structural steel 3 meters from hydrocarbon flare condensate separator. "
            "Fire watch absent, flammable material present without clearance, and hot work permit not obtained."
        ),
        expected_hazard="Thermal Energy / Flammable Gas",
        expected_activity="Hot Work",
        expected_rule_id="RULE_004",
        expected_priority="HIGH",
    ),

    # 5. Line of Fire / Heavy Lifting
    DemoScenario(
        report_id="DEMO-SYN-005",
        title="Personnel Under Suspended 25-Ton Tandem Crane Lift",
        category="line_of_fire",
        location="Offshore Module Fabrication Yard - Bay 3",
        report_text=(
            "During 25-ton tandem crane lift of heavy vessel spool piece, two riggers entered the line of fire and walked directly under the load. "
            "No exclusion zone established and barricade missing around active lift radius."
        ),
        expected_hazard="Suspended Load / Struck By",
        expected_activity="Heavy Lifting",
        expected_rule_id="RULE_005",
        expected_priority="HIGH",
    ),

    # 6. Non-SIF Routine Observation
    DemoScenario(
        report_id="DEMO-SYN-006",
        title="Housekeeping Pallet Scrap in Warehouse Walkway",
        category="routine_housekeeping",
        location="Central Logistics Warehouse - Bay C",
        report_text=(
            "During routine morning 5S housekeeping walk in Warehouse 2, several empty cardboard packing boxes "
            "and wooden pallet scraps were found partially obstructing the marked pedestrian walkway near Bay C. "
            "Materials were neatly restacked in the designated recycling bin and the walkway was swept clear."
        ),
        expected_hazard="Housekeeping / Slip-Trip",
        expected_activity="Housekeeping",
        expected_rule_id=None,
        expected_priority="LOW",
    ),

    # 7. Non-SIF Ergonomics Observation
    DemoScenario(
        report_id="DEMO-SYN-007",
        title="Control Room Display Height Ergonomic Adjustment",
        category="ergonomics",
        location="Central Control Room - Console 2",
        report_text=(
            "Console operator submitted an ergonomic observation requesting review of the SCADA display monitor "
            "height due to mild neck fatigue experienced during extended 12-hour shift handovers. Facilities team "
            "adjusted the articulated monitor arm 5 cm upward to achieve eye-level alignment."
        ),
        expected_hazard="Ergonomics",
        expected_activity="Office / Console Work",
        expected_rule_id=None,
        expected_priority="LOW",
    ),

    # 8. Near Miss (Barrier Functional)
    DemoScenario(
        report_id="DEMO-SYN-008",
        title="Forklift Near Miss at Workshop Blind Corner",
        category="near_miss",
        location="Maintenance Fabrication Workshop - Door 1",
        report_text=(
            "Forklift operator transporting a pallet of chemical drums stopped abruptly when a pedestrian contractor "
            "stepped out from behind a blind doorway corner near Maintenance Shop 1. The pedestrian was wearing a "
            "high-visibility vest, the forklift audible backup beeper was sounding, and both stopped without contact. "
            "A convex mirror has been requested for the doorway."
        ),
        expected_hazard="Mobile Equipment / Pedestrian Interface",
        expected_activity="Material Handling",
        expected_rule_id=None,
        expected_priority="MEDIUM",
    ),

    # 9. Ambiguous Case (Subtle Precursor Signal)
    DemoScenario(
        report_id="DEMO-SYN-009",
        title="Abnormal Vibration on 2200 PSI Booster Pump Flange",
        category="ambiguous_precursor",
        location="High-Pressure Injection Skid - Pump P-204A",
        report_text=(
            "Night shift technician observed unusual high-frequency vibration and a faint whistling sound at the discharge "
            "flange of high-pressure water alternating injection booster pump P-204A. Operating pressure was logged at 2200 psi. "
            "No visible fluid weeping was detected, but vibration has steadily increased over the past three shifts."
        ),
        expected_hazard="Mechanical / High Pressure Energy",
        expected_activity="Operational Inspection",
        expected_rule_id=None,
        expected_priority="MEDIUM",
        pre_staged_review={
            "decision": "corrected",
            "reviewer_id": "HSE-SPECIALIST-02",
            "corrected_priority": "HIGH",
            "corrected_activity": "High Pressure Injection",
            "corrected_hazard": "High Pressure Fluid Energy",
            "corrected_barrier": "Flange Integrity Inspection",
            "comments": "Escalated to HIGH: 2200 psi flange vibration is a recognized precursor to catastrophic seal failure. Immediate ultrasonic non-destructive testing ordered.",
        },
    ),

    # 10. Recurring Risk Pattern (Links with #1)
    DemoScenario(
        report_id="DEMO-SYN-010",
        title="Bypassed Interlock Jumper on 4160V Feeder Panel",
        category="recurring_energy_isolation",
        location="Substation 3 - 4160V Switchgear Room",
        report_text=(
            "Electrical technician servicing 4160V feeder panel P-102 found energized equipment accessed without isolation. "
            "Temporary jumper wire bypassed door interlock with no loto applied and breaker not locked."
        ),
        expected_hazard="Electrical Energy",
        expected_activity="Maintenance",
        expected_rule_id="RULE_001",
        expected_priority="HIGH",
    ),
]
