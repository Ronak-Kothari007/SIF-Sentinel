"""
SIF Sentinel — Tests for Phase 6 Safety Context & Entity Extractor
==================================================================

Covers:
  - Target user prompt example:
    “Maintenance started on energized equipment without verified isolation.”
  - DeterministicExtractor standalone tests
  - NLPExtractor standalone tests
  - HybridSafetyExtractor integration tests
  - TransformerNERExtractor interface & fallback tests
  - Status modifier bindings (Not Verified, Absent, Failed, Present)
  - Edge cases (empty strings, whitespace, no entities, punctuation)
  - Schema integrity and JSON serialization
"""

from __future__ import annotations

import json
import pytest

from app.schemas.context import EntityType, ExtractedEntity, SafetyContext
from app.services.extractor import (
    BaseEntityExtractor,
    DeterministicExtractor,
    HybridSafetyExtractor,
    NLPExtractor,
    TransformerNERExtractor,
)


# ===========================================================================
# Target Prompt Example Tests
# ===========================================================================

class TestTargetPromptExample:
    """
    Validates the exact prompt specification:
    Input: "Maintenance started on energized equipment without verified isolation."
    Expected conceptual output:
      activity = Maintenance
      hazard = Electrical Energy
      barrier = Isolation
      barrier_status = Not Verified
      equipment = energized equipment
    """

    @pytest.fixture
    def target_text(self) -> str:
        return "Maintenance started on energized equipment without verified isolation."

    @pytest.fixture
    def hybrid_extractor(self) -> HybridSafetyExtractor:
        return HybridSafetyExtractor()

    def test_target_activity(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.activity == "Maintenance"
        assert result.activity_confidence >= 0.85

    def test_target_hazard(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.hazard == "Electrical Energy"
        assert result.hazard_category == "Hazardous Energy"
        assert result.hazard_confidence >= 0.85

    def test_target_barrier(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.barrier == "Isolation"

    def test_target_barrier_status(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.barrier_status == "Not Verified"
        assert result.barrier_confidence >= 0.85

    def test_target_equipment(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.equipment == "energized equipment"

    def test_target_location_is_none(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        assert result.location is None

    def test_target_json_serialisation(self, hybrid_extractor, target_text):
        result = hybrid_extractor.extract(target_text)
        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["activity"] == "Maintenance"
        assert parsed["hazard"] == "Electrical Energy"
        assert parsed["barrier"] == "Isolation"
        assert parsed["barrier_status"] == "Not Verified"
        assert parsed["equipment"] == "energized equipment"
        assert len(parsed["entities"]) >= 3


# ===========================================================================
# Deterministic Extractor Tests
# ===========================================================================

class TestDeterministicExtractor:
    @pytest.fixture
    def extractor(self) -> DeterministicExtractor:
        return DeterministicExtractor()

    def test_extract_activities(self, extractor):
        res = extractor.extract("Welding and cutting operations underway.")
        act_types = [e.normalized_value for e in res.entities if e.entity_type == EntityType.activity]
        assert "Welding" in act_types
        assert "Cutting" in act_types

    def test_extract_hazards(self, extractor):
        res = extractor.extract("Exposed to toxic gas and flammable vapours near the unit.")
        haz_types = [e.normalized_value for e in res.entities if e.entity_type == EntityType.hazard]
        assert "Toxic Gas / H2S" in haz_types

    def test_extract_barriers(self, extractor):
        res = extractor.extract("LOTO applied and hot work permit obtained.")
        barriers = [e.normalized_value for e in res.entities if e.entity_type == EntityType.barrier]
        assert "Isolation" in barriers
        assert "Hot Work Permit" in barriers

    def test_extract_locations(self, extractor):
        res = extractor.extract("Incident occurred at the wellhead inside tank farm area.")
        locs = [e.normalized_value for e in res.entities if e.entity_type == EntityType.location]
        assert "Wellhead" in locs or "Tank Farm" in locs

    def test_extract_equipment(self, extractor):
        res = extractor.extract("Forklift and mobile crane operating near chemical drums.")
        eqs = [e.normalized_value for e in res.entities if e.entity_type == EntityType.equipment]
        assert "forklift" in eqs
        assert "crane" in eqs or "chemical drums" in eqs

    def test_character_offsets_are_accurate(self, extractor):
        text = "Welding was performed."
        res = extractor.extract(text)
        assert len(res.entities) >= 1
        entity = res.entities[0]
        assert text[entity.start_char:entity.end_char].lower() == "welding"


# ===========================================================================
# NLP Extractor Tests (Modifier & Status Binding)
# ===========================================================================

class TestNLPExtractor:
    @pytest.fixture
    def extractor(self) -> NLPExtractor:
        return NLPExtractor()

    def test_prefix_modifier_not_verified(self, extractor):
        text = "Maintenance started without verified isolation on the pump."
        res = extractor.extract(text)
        barriers = [e for e in res.entities if e.entity_type == EntityType.barrier]
        assert any(b.status == "Not Verified" for b in barriers)

    def test_prefix_modifier_absent(self, extractor):
        text = "Worker climbed scaffold without wearing a harness."
        res = extractor.extract(text)
        barriers = [e for e in res.entities if e.entity_type == EntityType.barrier]
        assert any(b.status == "Absent" for b in barriers)

    def test_postfix_modifier_missing(self, extractor):
        text = "Guardrail was missing on the elevated walkway."
        res = extractor.extract(text)
        barriers = [e for e in res.entities if e.entity_type == EntityType.barrier]
        assert any(b.status == "Absent" for b in barriers)

    def test_postfix_modifier_not_applied(self, extractor):
        text = "Lockout tagout not applied before repair."
        res = extractor.extract(text)
        barriers = [e for e in res.entities if e.entity_type == EntityType.barrier]
        assert any(b.status == "Absent" for b in barriers)

    def test_postfix_modifier_present(self, extractor):
        text = "Gas testing was performed before entry."
        res = extractor.extract(text)
        barriers = [e for e in res.entities if e.entity_type == EntityType.barrier]
        assert any(b.status == "Present" for b in barriers)

    def test_equipment_detection(self, extractor):
        text = "Operator working on energized equipment with handheld grinder."
        res = extractor.extract(text)
        eqs = [e.normalized_value for e in res.entities if e.entity_type == EntityType.equipment]
        assert any("energized equipment" in eq for eq in eqs)


# ===========================================================================
# Hybrid Safety Extractor Integration Tests
# ===========================================================================

class TestHybridSafetyExtractor:
    @pytest.fixture
    def extractor(self) -> HybridSafetyExtractor:
        return HybridSafetyExtractor()

    def test_confined_space_scenario(self, extractor):
        text = "Technician entered confined storage tank without completing gas test. Attendant was absent."
        res = extractor.extract(text)
        assert res.activity in ["Confined Space Entry", "Maintenance"]
        assert res.barrier == "Gas Testing"
        assert res.barrier_status == "Absent"
        assert res.location == "Storage Tank"

    def test_working_at_height_scenario(self, extractor):
        text = "Worker at height on top of 6-metre scaffold without harness. Guardrail missing."
        res = extractor.extract(text)
        assert res.hazard == "Fall from Height"
        assert res.barrier == "Fall Protection"
        assert res.barrier_status == "Absent"
        assert "scaffold" in (res.equipment or "").lower()

    def test_hot_work_scenario(self, extractor):
        text = "Welding operation was being carried out in process area. Fire watch was absent."
        res = extractor.extract(text)
        assert res.activity == "Welding"
        assert res.hazard == "Fire / Explosion"
        assert res.barrier == "Fire Watch"
        assert res.barrier_status == "Absent"
        assert res.location == "Process Area"

    def test_crane_lift_scenario(self, extractor):
        text = "Crane lift was in progress. Workers found standing below crane load. No barricade set up."
        res = extractor.extract(text)
        assert res.activity == "Lifting & Rigging"
        assert res.hazard == "Struck-By"
        assert res.barrier == "Exclusion Zone"
        assert res.barrier_status == "Absent"
        assert "crane" in (res.equipment or "").lower()

    def test_routine_compliant_report(self, extractor):
        text = "Toolbox meeting was conducted. All workers signed attendance sheet. No hazards."
        res = extractor.extract(text)
        assert res.activity == "Pre-task Briefing"
        assert res.hazard is None
        assert res.barrier_status is None or res.barrier_status == "Present"


# ===========================================================================
# Modularity & Architecture Tests
# ===========================================================================

class TestArchitectureAndModularity:
    def test_extractor_implements_base_class(self):
        assert issubclass(DeterministicExtractor, BaseEntityExtractor)
        assert issubclass(NLPExtractor, BaseEntityExtractor)
        assert issubclass(HybridSafetyExtractor, BaseEntityExtractor)
        assert issubclass(TransformerNERExtractor, BaseEntityExtractor)

    def test_transformer_ner_fallback(self):
        extractor = TransformerNERExtractor(model_checkpoint=None)
        res = extractor.extract("Maintenance started on energized equipment without verified isolation.")
        assert res.activity == "Maintenance"
        assert "transformer_ner" in res.extraction_method

    def test_custom_rules_path_missing_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            DeterministicExtractor(config_path="nonexistent_path/rules.yaml")


# ===========================================================================
# Edge Cases & Validation Tests
# ===========================================================================

class TestEdgeCases:
    @pytest.fixture
    def extractor(self) -> HybridSafetyExtractor:
        return HybridSafetyExtractor()

    def test_empty_string(self, extractor):
        res = extractor.extract("")
        assert res.activity is None
        assert res.hazard is None
        assert res.entities == []
        assert res.raw_text == ""

    def test_whitespace_only(self, extractor):
        res = extractor.extract("    \n\t   ")
        assert res.activity is None
        assert res.entities == []

    def test_punctuation_only(self, extractor):
        res = extractor.extract("...???!!! ---")
        assert res.activity is None
        assert res.entities == []

    def test_irrelevant_text(self, extractor):
        res = extractor.extract("The quarterly balance sheet was reviewed by the accounting team.")
        assert res.activity is None
        assert res.hazard is None
        assert res.barrier is None

    def test_to_dict_keys(self, extractor):
        res = extractor.extract("Welding in process area.")
        d = res.to_dict()
        assert "activity" in d
        assert "hazard" in d
        assert "barrier" in d
        assert "barrier_status" in d
        assert "location" in d
        assert "equipment" in d
        assert "entities" in d
        assert "summary" in d
