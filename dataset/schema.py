"""
SIF Sentinel — Dataset Schema Definition
=========================================

Canonical column specification for all SIF Sentinel datasets (CSV format).
Import this module in scripts to get the authoritative schema.

Schema version: 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Canonical column names (in order they appear in the CSV)
# ---------------------------------------------------------------------------

COLUMNS: list[str] = [
    "report_id",
    "report_text",
    "sif_precursor",
    "activity",
    "hazard",
    "barrier",
    "location",
    "severity",
    "source",
]

# ---------------------------------------------------------------------------
# Valid values for constrained columns
# ---------------------------------------------------------------------------

VALID_SIF_PRECURSOR: set[int] = {0, 1}

VALID_SEVERITY: set[str] = {"low", "medium", "high", "critical"}

VALID_SOURCE: set[str] = {"public", "synthetic", "anonymized"}

# ---------------------------------------------------------------------------
# Column metadata (for documentation and UI display)
# ---------------------------------------------------------------------------

COLUMN_DESCRIPTIONS: dict[str, str] = {
    "report_id":     "Unique identifier for the report (e.g. SYN-001, PUB-001, ANO-001)",
    "report_text":   "Raw text of the safety observation, near-miss, or incident report",
    "sif_precursor": "Binary label: 1 = SIF precursor present, 0 = not a SIF precursor",
    "activity":      "Primary work activity at time of observation (e.g. welding, lifting)",
    "hazard":        "Primary hazard category identified (e.g. fall_from_height, gas_leak)",
    "barrier":       "Safety barrier status (e.g. controls_in_place, harness_absent)",
    "location":      "Physical location within the facility (e.g. well_site, pump_room)",
    "severity":      "Severity level: low | medium | high | critical",
    "source":        "Data provenance: public | synthetic | anonymized",
}

# ---------------------------------------------------------------------------
# Minimum text length (characters) for a valid report_text
# ---------------------------------------------------------------------------

MIN_TEXT_LENGTH: int = 20

# ---------------------------------------------------------------------------
# Report ID prefixes by source
# ---------------------------------------------------------------------------

SOURCE_ID_PREFIXES: dict[str, str] = {
    "synthetic":  "SYN-",
    "public":     "PUB-",
    "anonymized": "ANO-",
}

SCHEMA_VERSION: str = "1.0"
