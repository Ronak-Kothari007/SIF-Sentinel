"""
SIF Sentinel — Pydantic Schemas for Safety Context & Entity Extraction
======================================================================

Defines the structured output contract for Phase 6 entity extraction:
identifying activity, hazard, barrier/control, barrier status, location,
and equipment from safety observation reports.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    activity = "activity"
    hazard = "hazard"
    barrier = "barrier"
    barrier_status = "barrier_status"
    location = "location"
    equipment = "equipment"


class ExtractedEntity(BaseModel):
    """A single identified entity span in the input text."""

    entity_type: EntityType = Field(description="Class of entity extracted")
    text: str = Field(description="Exact span of text extracted from report")
    normalized_value: str = Field(description="Canonical normalized name")
    start_char: int = Field(ge=0, description="Start character offset in text")
    end_char: int = Field(ge=0, description="End character offset in text")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    source: str = Field(
        default="hybrid",
        description="Source of extraction: deterministic, nlp_pattern, hybrid, or transformer_ner",
    )
    category: Optional[str] = Field(
        default=None,
        description="Optional high-level taxonomy category (e.g. Hazardous Energy)",
    )
    status: Optional[str] = Field(
        default=None,
        description="Status qualifier if applicable (specifically for barriers, e.g. 'Not Verified')",
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class SafetyContext(BaseModel):
    """
    Consolidated safety context extracted from a safety report.
    Provides canonical primary fields alongside the full list of detected spans.
    """

    activity: Optional[str] = Field(
        default=None,
        description="Primary work activity underway (e.g. Maintenance, Welding, Lifting)",
    )
    activity_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in primary activity"
    )

    hazard: Optional[str] = Field(
        default=None,
        description="Primary hazard identified (e.g. Electrical Energy, Fall from Height)",
    )
    hazard_category: Optional[str] = Field(
        default=None,
        description="High-level hazard category (e.g. Hazardous Energy, Thermal)",
    )
    hazard_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in primary hazard"
    )

    barrier: Optional[str] = Field(
        default=None,
        description="Primary barrier or control identified (e.g. Isolation, Gas Testing)",
    )
    barrier_status: Optional[str] = Field(
        default=None,
        description="Condition of the barrier: 'Not Verified', 'Absent', 'Failed', 'Present'",
    )
    barrier_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in primary barrier and status"
    )

    location: Optional[str] = Field(
        default=None,
        description="Physical location / plant zone (e.g. Tank Farm, Wellhead, Pump Room)",
    )
    location_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in detected location"
    )

    equipment: Optional[str] = Field(
        default=None,
        description="Key equipment or machinery involved (e.g. energized equipment, scaffold, crane)",
    )
    equipment_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in detected equipment"
    )

    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="All individual entity mentions identified in the text",
    )

    raw_text: str = Field(
        default="",
        description="The original input report text",
    )

    summary: str = Field(
        default="",
        description="Concise synthesis of the extracted safety context",
    )

    extraction_method: str = Field(
        default="hybrid",
        description="Extraction pipeline utilized (deterministic, nlp_pattern, hybrid, or transformer_ner)",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a clean dictionary structure."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Serialize directly to structured JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
