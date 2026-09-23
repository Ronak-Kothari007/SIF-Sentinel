"""
SIF Sentinel — Safety Context & Entity Extraction Engine (Phase 6)
==================================================================

A hybrid, modular extraction engine combining deterministic domain gazetteers
and contextual NLP patterns to identify safety entities from industrial reports:
  - activity
  - hazard
  - barrier / control
  - barrier status (e.g. Not Verified, Absent, Failed, Present)
  - location
  - equipment

Architecture:
  BaseEntityExtractor (ABC)
    ├── DeterministicExtractor   (High precision dictionary / gazetteer matching)
    ├── NLPExtractor             (Contextual pattern, modifier & negation binding)
    ├── HybridSafetyExtractor    (Orchestrator combining gazetteers & NLP)
    └── TransformerNERExtractor  (Pluggable interface for future trained NER models)
"""

from __future__ import annotations

import re
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from app.schemas.context import EntityType, ExtractedEntity, SafetyContext


# ---------------------------------------------------------------------------
# Default configuration path
# ---------------------------------------------------------------------------
DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "extraction_rules.yaml"


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------
class BaseEntityExtractor(ABC):
    """Abstract interface for all safety entity extractors."""

    @abstractmethod
    def extract(self, text: str) -> SafetyContext:
        """
        Extract safety context and entities from a text report.

        Args:
            text: Raw safety report string.

        Returns:
            Structured SafetyContext containing primary entities and spans.
        """
        pass


# ---------------------------------------------------------------------------
# Deterministic Gazetteer Extractor
# ---------------------------------------------------------------------------
class DeterministicExtractor(BaseEntityExtractor):
    """
    High-precision deterministic extractor using domain gazetteers.
    Matches canonical safety terms, aliases, and known equipment/locations
    using exact regex word boundaries.
    """

    def __init__(self, config_path: Optional[Path | str] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_RULES_PATH
        self._load_config()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Extraction rules file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.activities_cfg = data.get("activities", [])
        self.hazards_cfg = data.get("hazards", [])
        self.barriers_cfg = data.get("barriers", [])
        self.locations_cfg = data.get("locations", [])
        self.equipment_cfg = data.get("equipment", [])
        self.status_modifiers_cfg = data.get("barrier_status_modifiers", {})

    def extract(self, text: str) -> SafetyContext:
        if not text or not text.strip():
            return SafetyContext(raw_text=text or "", extraction_method="deterministic")

        entities: list[ExtractedEntity] = []

        # 1. Activities
        for item in self.activities_cfg:
            canonical = item["canonical"]
            for alias in item.get("aliases", []):
                pattern = rf"\b{re.escape(alias)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        ExtractedEntity(
                            entity_type=EntityType.activity,
                            text=match.group(0),
                            normalized_value=canonical,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.92,
                            source="deterministic",
                        )
                    )

        # 2. Hazards
        for item in self.hazards_cfg:
            canonical = item["canonical"]
            category = item.get("category")
            for alias in item.get("aliases", []):
                pattern = rf"\b{re.escape(alias)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        ExtractedEntity(
                            entity_type=EntityType.hazard,
                            text=match.group(0),
                            normalized_value=canonical,
                            category=category,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.92,
                            source="deterministic",
                        )
                    )

        # 3. Barriers
        for item in self.barriers_cfg:
            canonical = item["canonical"]
            category = item.get("category")
            for alias in item.get("aliases", []):
                pattern = rf"\b{re.escape(alias)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        ExtractedEntity(
                            entity_type=EntityType.barrier,
                            text=match.group(0),
                            normalized_value=canonical,
                            category=category,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.90,
                            source="deterministic",
                        )
                    )

        # 4. Locations
        for item in self.locations_cfg:
            canonical = item["canonical"]
            for alias in item.get("aliases", []):
                pattern = rf"\b{re.escape(alias)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        ExtractedEntity(
                            entity_type=EntityType.location,
                            text=match.group(0),
                            normalized_value=canonical,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.90,
                            source="deterministic",
                        )
                    )

        # 5. Equipment
        for item in self.equipment_cfg:
            canonical = item["canonical"]
            for alias in item.get("aliases", []):
                pattern = rf"\b{re.escape(alias)}\b"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append(
                        ExtractedEntity(
                            entity_type=EntityType.equipment,
                            text=match.group(0),
                            normalized_value=canonical,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.88,
                            source="deterministic",
                        )
                    )

        # Deduplicate overlapping spans for the same entity type
        deduped = self._deduplicate_spans(entities)

        return SafetyContext(
            entities=deduped,
            raw_text=text,
            extraction_method="deterministic",
        )

    def _deduplicate_spans(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Keep longest span when spans overlap for the same entity type."""
        if not entities:
            return []

        sorted_entities = sorted(
            entities,
            key=lambda e: (e.entity_type.value, e.start_char, -(e.end_char - e.start_char)),
        )

        deduped: list[ExtractedEntity] = []
        for entity in sorted_entities:
            conflict = False
            for existing in deduped:
                if existing.entity_type == entity.entity_type:
                    # Check overlap
                    if not (entity.end_char <= existing.start_char or entity.start_char >= existing.end_char):
                        conflict = True
                        break
            if not conflict:
                deduped.append(entity)

        return sorted(deduped, key=lambda e: e.start_char)


# ---------------------------------------------------------------------------
# Contextual NLP Pattern Extractor
# ---------------------------------------------------------------------------
class NLPExtractor(BaseEntityExtractor):
    """
    Contextual NLP extractor using linguistic patterns, syntactic heuristics,
    window-based negation resolution, and barrier-status binding.
    """

    # Barrier status modifiers with priority and normalized name
    MODIFIER_MAPPINGS: list[tuple[str, list[str]]] = [
        ("Not Verified", [
            r"without\s+verified",
            r"not\s+verified",
            r"unverified",
            r"no\s+verified",
            r"lacking\s+verification",
            r"verification\s+missing",
            r"not\s+confirmed",
        ]),
        ("Absent", [
            r"without\s+wearing",
            r"without\s+completing",
            r"without\s+clearing",
            r"without\s+providing",
            r"without\s+obtaining",
            r"without\s+a",
            r"without\s+any",
            r"without",
            r"not\s+applied",
            r"not\s+used",
            r"not\s+worn",
            r"not\s+provided",
            r"not\s+performed",
            r"not\s+done",
            r"not\s+obtained",
            r"not\s+closed",
            r"not\s+locked",
            r"not\s+set\s+up",
            r"not\s+enforced",
            r"not\s+de-energized",
            r"missing",
            r"absent",
            r"no\s+attendant",
            r"no\s+barricade",
            r"no\s+harness",
            r"no\s+permit",
            r"no\s+gas\s+test",
            r"no\s+lock",
            r"no\s+spotter",
            r"no\s+guarding",
            r"no",
        ]),
        ("Failed", [
            r"failed",
            r"compromised",
            r"broken",
            r"cracked",
            r"inadequate",
            r"defective",
            r"bypassed",
            r"damaged",
            r"unsecured",
        ]),
        ("Present", [
            r"verified",
            r"in\s+place",
            r"applied",
            r"completed",
            r"performed",
            r"present",
            r"functional",
            r"active",
            r"enforced",
            r"signed\s+off",
            r"signed",
            r"provided",
            r"operated\s+throughout",
            r"satisfactory",
        ]),
    ]

    # Prepositional Equipment Patterns
    EQUIPMENT_PATTERNS: list[str] = [
        r"\b(?:on|with|using|servicing|repairing|inspecting|operating|near)\s+([a-z0-9_-]+\s+(?:equipment|rig|scaffold|panel|crane|pump|valve|drums|separator|grinder))\b",
        r"\b(energized\s+equipment|live\s+circuit|motor\s+control\s+panel|electrical\s+panel|drilling\s+rig|\d+-metre\s+scaffold|crane\s+load|pressure\s+relief\s+valve|isolation\s+valve|gas\s+detector|chemical\s+drums|angle\s+grinder|forklift|crane|pump|scaffold)\b",
    ]

    # Activity action patterns (e.g. "Maintenance started on...", "Welding operation was being...")
    ACTIVITY_PATTERNS: list[tuple[str, str]] = [
        (r"\b(maintenance)\s+(?:started|commenced|was\s+in\s+progress|began|technician)\b", "Maintenance"),
        (r"\b(welding)\s+(?:operation|was|activity|started|commenced)\b", "Welding"),
        (r"\b(cutting)\s+(?:operation|commenced|started|activity)\b", "Cutting"),
        (r"\b(crane\s+lift|lifting)\s+(?:was\s+in\s+progress|operation|activity)\b", "Lifting & Rigging"),
        (r"\b(?:technician|worker)\s+entered\s+(confined\s+space|storage\s+tank|vessel)\b", "Confined Space Entry"),
        (r"\b(?:working|found\s+working)\s+at\s+height\b", "Working at Height"),
        (r"\b(?:routine|pipeline|housekeeping)\s+(inspection)\b", "Inspection & Audit"),
        (r"\b(offloading)\s+of\s+chemical\s+drums\b", "Lifting & Rigging"),
        (r"\b(?:worker|operator)\s+observed\s+using\s+mobile\s+phone\s+while\s+(driving|operating\s+a\s+vehicle)\b", "Driving & Logistics"),
        (r"\b(toolbox\s+meeting)\s+was\s+conducted\b", "Pre-task Briefing"),
        (r"\b(painting|painter)\s+(?:reported|was)\b", "Painting & Blasting"),
        (r"\b(h2s\s+alarm)\s+was\s+triggered.*?(evacuated)\b", "Emergency Response"),
    ]

    # Prepositional Location Patterns
    LOCATION_PATTERNS: list[str] = [
        r"\b(?:in|at|inside|near|into)\s+(?:the\s+)?([a-z0-9_\s-]{3,25}?(?:tank\s+farm|storage\s+tank|wellhead|well\s+site|pump\s+room|pump\s+station|process\s+area|flare\s+stack|derrick|pipe\s+yard|chemical\s+store|storage\s+room|office\s+block|site\s+road|separator\s+station|separator\s+vessel))\b",
    ]

    def extract(self, text: str) -> SafetyContext:
        if not text or not text.strip():
            return SafetyContext(raw_text=text or "", extraction_method="nlp_pattern")

        entities: list[ExtractedEntity] = []

        # 1. NLP Activity Patterns
        for pat, norm in self.ACTIVITY_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                span_text = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                entities.append(
                    ExtractedEntity(
                        entity_type=EntityType.activity,
                        text=span_text,
                        normalized_value=norm,
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=0.88,
                        source="nlp_pattern",
                    )
                )

        # 2. NLP Equipment Patterns
        for pat in self.EQUIPMENT_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                matched_str = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                entities.append(
                    ExtractedEntity(
                        entity_type=EntityType.equipment,
                        text=matched_str.strip(),
                        normalized_value=matched_str.strip().lower(),
                        start_char=match.start(1) if match.lastindex and match.lastindex >= 1 else match.start(),
                        end_char=match.end(1) if match.lastindex and match.lastindex >= 1 else match.end(),
                        confidence=0.85,
                        source="nlp_pattern",
                    )
                )

        # 3. NLP Location Patterns
        for pat in self.LOCATION_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                matched_loc = match.group(1).strip()
                entities.append(
                    ExtractedEntity(
                        entity_type=EntityType.location,
                        text=matched_loc,
                        normalized_value=matched_loc.title(),
                        start_char=match.start(1),
                        end_char=match.end(1),
                        confidence=0.82,
                        source="nlp_pattern",
                    )
                )

        # 4. Contextual Barrier + Status Binding
        barrier_spans = self._extract_barrier_with_status(text)
        entities.extend(barrier_spans)

        return SafetyContext(
            entities=entities,
            raw_text=text,
            extraction_method="nlp_pattern",
        )

    def _extract_barrier_with_status(self, text: str) -> list[ExtractedEntity]:
        """
        Syntactic window matching: detects barrier mentions in close proximity
        to status modifiers (e.g. 'without verified isolation', 'guardrail was missing').
        """
        results: list[ExtractedEntity] = []

        # Common barrier core nouns
        known_barriers: list[tuple[str, str]] = [
            (r"\bisolation\b", "Isolation"),
            (r"\blockout\s+tagout\b|\bloto\b|\blockout\b|\btagout\b", "Isolation"),
            (r"\bgas\s+test(?:ing)?\b|\batmospheric\s+(?:testing|monitoring)\b|\bgas\s+clearance\b", "Gas Testing"),
            (r"\bfall\s+protection\b|\b(?:safety\s+)?harness\b|\bguardrail\b|\bsafety\s+net\b", "Fall Protection"),
            (r"\bhot\s+work\s+permit\b|\bentry\s+permit\b|\bwork\s+permit\b|\bpermit\b", "Hot Work Permit"),
            (r"\bfire\s+watch\b", "Fire Watch"),
            (r"\bexclusion\s+zone\b|\bbarricade\b", "Exclusion Zone"),
            (r"\b(?:machine\s+)?guarding\b|\bprotective\s+guard\b", "Machine Guarding"),
            (r"\bventilation\b", "Ventilation"),
            (r"\bspotter\b|\battendant\b", "Spotter"),
            (r"\bppe\b|\bhard\s+hat\b|\bsafety\s+glasses\b", "PPE"),
        ]

        for status_label, mod_patterns in self.MODIFIER_MAPPINGS:
            for mod_pat in mod_patterns:
                for b_pat, b_norm in known_barriers:
                    # Prefix pattern: [modifier] + [optional words] + [barrier]
                    # e.g. "without verified isolation", "without completing gas test"
                    prefix_regex = rf"\b({mod_pat})\s+(?:completing\s+|wearing\s+|performing\s+|having\s+|a\s+|any\s+)?({b_pat})"
                    for m in re.finditer(prefix_regex, text, re.IGNORECASE):
                        results.append(
                            ExtractedEntity(
                                entity_type=EntityType.barrier,
                                text=m.group(0),
                                normalized_value=b_norm,
                                status=status_label,
                                start_char=m.start(),
                                end_char=m.end(),
                                confidence=0.94 if status_label == "Not Verified" else 0.89,
                                source="nlp_pattern",
                            )
                        )

                    # Postfix pattern: [barrier] + [was/is/not] + [modifier]
                    # e.g. "guardrail was missing", "fire watch was absent", "lockout tagout not applied"
                    postfix_regex = rf"\b({b_pat})\s+(?:was\s+|is\s+|had\s+been\s+)?({mod_pat})\b"
                    for m in re.finditer(postfix_regex, text, re.IGNORECASE):
                        results.append(
                            ExtractedEntity(
                                entity_type=EntityType.barrier,
                                text=m.group(0),
                                normalized_value=b_norm,
                                status=status_label,
                                start_char=m.start(),
                                end_char=m.end(),
                                confidence=0.90,
                                source="nlp_pattern",
                            )
                        )

        return results


# ---------------------------------------------------------------------------
# Hybrid Safety Context Extractor (Default Orchestrator)
# ---------------------------------------------------------------------------
class HybridSafetyExtractor(BaseEntityExtractor):
    """
    Orchestrates deterministic gazetteers and contextual NLP extractors.
    Merges entities, binds barrier statuses, resolves primary fields,
    computes confidence scores, and produces clean structured output.
    """

    def __init__(self, config_path: Optional[Path | str] = None):
        self.deterministic = DeterministicExtractor(config_path=config_path)
        self.nlp = NLPExtractor()

    def extract(self, text: str) -> SafetyContext:
        """
        Execute hybrid safety context extraction on report text.
        """
        if not text or not text.strip():
            return SafetyContext(raw_text=text or "", extraction_method="hybrid")

        clean_text = text.strip()

        # Step 1: Run deterministic gazetteer matching
        det_context = self.deterministic.extract(clean_text)

        # Step 2: Run NLP contextual pattern matching
        nlp_context = self.nlp.extract(clean_text)

        # Step 3: Merge and reconcile extracted entities
        merged_entities = self._merge_entities(clean_text, det_context.entities, nlp_context.entities)

        # Step 4: Resolve primary fields
        primary_activity, act_conf = self._resolve_primary_field(merged_entities, EntityType.activity)
        primary_hazard, haz_conf, haz_cat = self._resolve_primary_hazard(merged_entities)
        primary_barrier, bar_conf, bar_status = self._resolve_primary_barrier(merged_entities, clean_text)
        primary_location, loc_conf = self._resolve_primary_field(merged_entities, EntityType.location)
        primary_equipment, eq_conf = self._resolve_primary_equipment(merged_entities, clean_text)

        # Fallback heuristic: If hazard is still empty but text mentions specific hazard cues
        if not primary_hazard and primary_barrier:
            implied_hazard, implied_cat = self._infer_hazard_from_barrier(primary_barrier)
            if implied_hazard:
                primary_hazard = implied_hazard
                haz_cat = implied_cat
                haz_conf = 0.70

        # Step 5: Synthesize human-readable summary
        summary = self._generate_summary(
            primary_activity, primary_hazard, primary_barrier, bar_status, primary_location, primary_equipment
        )

        return SafetyContext(
            activity=primary_activity,
            activity_confidence=round(act_conf, 2),
            hazard=primary_hazard,
            hazard_category=haz_cat,
            hazard_confidence=round(haz_conf, 2),
            barrier=primary_barrier,
            barrier_status=bar_status,
            barrier_confidence=round(bar_conf, 2),
            location=primary_location,
            location_confidence=round(loc_conf, 2),
            equipment=primary_equipment,
            equipment_confidence=round(eq_conf, 2),
            entities=merged_entities,
            raw_text=clean_text,
            summary=summary,
            extraction_method="hybrid",
        )

    def _merge_entities(
        self,
        text: str,
        det_entities: list[ExtractedEntity],
        nlp_entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """Merge deterministic and NLP entities, resolving overlaps and combining attributes."""
        merged: list[ExtractedEntity] = []

        # Add all deterministic entities as base
        for de in det_entities:
            # Check if any NLP entity provides additional barrier status
            status = None
            if de.entity_type == EntityType.barrier:
                for ne in nlp_entities:
                    if ne.entity_type == EntityType.barrier and ne.status:
                        # Overlapping or within 30 chars
                        if abs(de.start_char - ne.start_char) <= 30:
                            status = ne.status
                            break
            # Check if reinforced by NLP
            is_reinforced = any(
                ne.entity_type == de.entity_type and abs(ne.start_char - de.start_char) <= 15
                for ne in nlp_entities
            )
            confidence = min(0.98, de.confidence + (0.06 if is_reinforced else 0.0))

            merged.append(
                ExtractedEntity(
                    entity_type=de.entity_type,
                    text=de.text,
                    normalized_value=de.normalized_value,
                    start_char=de.start_char,
                    end_char=de.end_char,
                    confidence=round(confidence, 2),
                    source="hybrid" if is_reinforced else "deterministic",
                    category=de.category,
                    status=status,
                )
            )

        # Add NLP entities that are novel
        for ne in nlp_entities:
            overlap = False
            for me in merged:
                if me.entity_type == ne.entity_type:
                    if not (ne.end_char <= me.start_char or ne.start_char >= me.end_char):
                        overlap = True
                        break
            if not overlap:
                merged.append(ne)

        return sorted(merged, key=lambda e: e.start_char)

    def _resolve_primary_field(
        self, entities: list[ExtractedEntity], entity_type: EntityType
    ) -> tuple[Optional[str], float]:
        """Select primary entity by highest confidence and earlier appearance."""
        matches = [e for e in entities if e.entity_type == entity_type]
        if not matches:
            return None, 0.0

        # Sort by confidence desc, then by position asc
        best = sorted(matches, key=lambda e: (-e.confidence, e.start_char))[0]
        return best.normalized_value, best.confidence

    def _resolve_primary_hazard(
        self, entities: list[ExtractedEntity]
    ) -> tuple[Optional[str], float, Optional[str]]:
        matches = [e for e in entities if e.entity_type == EntityType.hazard]
        if not matches:
            return None, 0.0, None

        best = sorted(matches, key=lambda e: (-e.confidence, e.start_char))[0]
        return best.normalized_value, best.confidence, best.category

    def _resolve_primary_barrier(
        self, entities: list[ExtractedEntity], text: str
    ) -> tuple[Optional[str], float, Optional[str]]:
        matches = [e for e in entities if e.entity_type == EntityType.barrier]
        if not matches:
            return None, 0.0, None

        best = sorted(matches, key=lambda e: (-e.confidence, e.start_char))[0]
        status = best.status

        # If barrier status is still None, scan proximity for negation / status words
        if not status:
            status = self._infer_status_from_text_window(best, text)

        return best.normalized_value, best.confidence, status

    def _resolve_primary_equipment(
        self, entities: list[ExtractedEntity], text: str
    ) -> tuple[Optional[str], float]:
        matches = [e for e in entities if e.entity_type == EntityType.equipment]
        if matches:
            best = sorted(matches, key=lambda e: (-e.confidence, e.start_char))[0]
            return best.text if best.text else best.normalized_value, best.confidence

        # Contextual check: "energized equipment" in text
        if "energized equipment" in text.lower():
            return "energized equipment", 0.85

        return None, 0.0

    def _infer_status_from_text_window(self, entity: ExtractedEntity, text: str) -> str:
        """Examine 40-character window before and after barrier mention."""
        window_start = max(0, entity.start_char - 40)
        window_end = min(len(text), entity.end_char + 40)
        window = text[window_start:window_end].lower()

        if "without verified" in window or "not verified" in window:
            return "Not Verified"
        if any(w in window for w in ["without", "absent", "missing", "no ", "not applied", "not used", "not worn", "not performed"]):
            return "Absent"
        if any(w in window for w in ["failed", "cracked", "broken", "defective", "bypassed"]):
            return "Failed"
        if any(w in window for w in ["verified", "in place", "applied", "completed", "functional", "present", "enforced"]):
            return "Present"

        return "Not Verified" if "verified" in window else "Unknown"

    def _infer_hazard_from_barrier(self, barrier: str) -> tuple[Optional[str], Optional[str]]:
        """Map well-known barriers to standard hazards when hazard is omitted."""
        mapping = {
            "Isolation": ("Electrical Energy", "Hazardous Energy"),
            "Gas Testing": ("Toxic Gas / H2S", "Hazardous Atmosphere"),
            "Fall Protection": ("Fall from Height", "Working at Height"),
            "Fire Watch": ("Fire / Explosion", "Thermal / Chemical"),
            "Hot Work Permit": ("Fire / Explosion", "Thermal / Chemical"),
            "Exclusion Zone": ("Struck-By", "Mechanical / Physical"),
            "Machine Guarding": ("Caught Between", "Mechanical / Physical"),
            "Ventilation": ("Asphyxiation", "Hazardous Atmosphere"),
        }
        return mapping.get(barrier, (None, None))

    def _generate_summary(
        self,
        activity: Optional[str],
        hazard: Optional[str],
        barrier: Optional[str],
        barrier_status: Optional[str],
        location: Optional[str],
        equipment: Optional[str],
    ) -> str:
        """Synthesize a concise 1-sentence safety context summary."""
        parts = []
        if activity:
            parts.append(f"Activity: {activity}")
        if equipment:
            parts.append(f"Equipment: {equipment}")
        if hazard:
            parts.append(f"Hazard: {hazard}")
        if barrier:
            bar_desc = f"Barrier: {barrier}"
            if barrier_status:
                bar_desc += f" ({barrier_status})"
            parts.append(bar_desc)
        if location:
            parts.append(f"Location: {location}")

        return " | ".join(parts) if parts else "No specific safety context entities detected"


# ---------------------------------------------------------------------------
# Pluggable Transformer NER Extractor (Future Extensibility)
# ---------------------------------------------------------------------------
class TransformerNERExtractor(BaseEntityExtractor):
    """
    Pluggable transformer-based token classification / NER model extractor.
    Implements the identical BaseEntityExtractor interface, allowing future
    fine-tuned models (e.g. RoBERTa/DeBERTa) to replace or augment the hybrid engine.
    """

    def __init__(self, model_checkpoint: Optional[str] = None):
        self.model_checkpoint = model_checkpoint
        self.model = None
        self.tokenizer = None
        if model_checkpoint:
            self._load_model()

    def _load_model(self) -> None:
        """Load transformer token classification model if checkpoint provided."""
        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_checkpoint)
            self.model = AutoModelForTokenClassification.from_pretrained(self.model_checkpoint)
        except Exception as e:
            # Graceful warning for future integration
            pass

    def extract(self, text: str) -> SafetyContext:
        """
        Execute transformer NER token classification.
        Falls back to hybrid extractor if model is not yet trained.
        """
        if self.model is None:
            # When checkpoint is not yet available, delegate to HybridSafetyExtractor
            hybrid_fallback = HybridSafetyExtractor()
            res = hybrid_fallback.extract(text)
            res.extraction_method = "transformer_ner (fallback to hybrid)"
            return res

        # Future: Real transformer token classification pipeline
        return SafetyContext(raw_text=text, extraction_method="transformer_ner")
