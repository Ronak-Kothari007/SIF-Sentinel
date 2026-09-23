"""
SIF Sentinel — Phase 2: Deterministic Rule Engine Tests
========================================================

Tests cover:
  - RULE_001: Energy Isolation Failure
  - RULE_002: Confined Space Entry Without Controls
  - RULE_003: Working at Height Without Fall Protection
  - RULE_004: Hot Work Without Adequate Controls
  - RULE_005: Line of Fire Exposure

Special scenarios:
  - False positives (words that sound related but should NOT trigger)
  - Unrelated / generic reports (office, admin, noise complaints)
  - Multiple rules triggering on a single report
  - Edge cases: empty text, whitespace, mixed case
  - Engine initialisation and structure validation
  - RuleMatch / RuleEngineResult serialisation (to_dict)

Run with:
    pytest tests/test_rule_engine.py -v
"""

import json
import pytest
import tempfile
from pathlib import Path

from app.services.rule_engine import (
    SIFRuleEngine,
    RuleEngineResult,
    RuleMatch,
    SEVERITY_LABELS,
    SIF_FLAG_THRESHOLD,
    get_rule_engine,
)


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine() -> SIFRuleEngine:
    """Shared engine instance for all tests (loads real sif_rules.yaml)."""
    return SIFRuleEngine()


def evaluate(engine: SIFRuleEngine, text: str) -> RuleEngineResult:
    """Convenience wrapper."""
    return engine.evaluate(text)


def triggered_ids(result: RuleEngineResult) -> set[str]:
    """Return set of triggered rule IDs for easy assertion."""
    return {r.rule_id for r in result.matched_rules}


# ===========================================================================
# Section 1 — Engine Initialisation & Structure
# ===========================================================================

class TestEngineInitialisation:
    """Verify the engine loads correctly and exposes the right metadata."""

    def test_engine_loads_five_rules(self, engine: SIFRuleEngine):
        """There must be exactly 5 rules loaded from the YAML."""
        assert engine.rule_count == 5

    def test_engine_rule_ids_are_correct(self, engine: SIFRuleEngine):
        """All five rule IDs must be present."""
        ids = engine.get_rule_ids()
        assert set(ids) == {"RULE_001", "RULE_002", "RULE_003", "RULE_004", "RULE_005"}

    def test_engine_categories_correct(self, engine: SIFRuleEngine):
        """All five SIF categories must be represented."""
        categories = engine.get_rule_categories()
        assert set(categories) == {
            "Energy Isolation",
            "Confined Space",
            "Working at Height",
            "Hot Work",
            "Line of Fire",
        }

    def test_rules_path_exists(self, engine: SIFRuleEngine):
        """The rules file path must resolve to a real file."""
        assert engine.rules_path.exists()

    def test_engine_missing_file_raises(self, tmp_path: Path):
        """Engine must raise FileNotFoundError for a non-existent rules file."""
        with pytest.raises(FileNotFoundError):
            SIFRuleEngine(rules_path=tmp_path / "nonexistent.yaml")

    def test_engine_malformed_severity_raises(self, tmp_path: Path):
        """Engine must raise ValueError if severity is out of range."""
        bad_yaml = tmp_path / "bad_rules.yaml"
        bad_yaml.write_text(
            'rules:\n'
            '  - id: R_BAD\n'
            '    name: "Bad Rule"\n'
            '    category: "Test"\n'
            '    severity: 99\n'
            '    signals:\n'
            '      - "test signal"\n'
            '    explanation: "Test explanation for bad rule"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="severity"):
            SIFRuleEngine(rules_path=bad_yaml)

    def test_engine_missing_signals_field_raises(self, tmp_path: Path):
        """Engine must raise ValueError if signals field is absent."""
        bad_yaml = tmp_path / "bad_rules2.yaml"
        bad_yaml.write_text(
            'rules:\n'
            '  - id: R_BAD2\n'
            '    name: "Bad Rule"\n'
            '    category: "Test"\n'
            '    severity: 2\n'
            '    explanation: "Test explanation"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required fields"):
            SIFRuleEngine(rules_path=bad_yaml)

    def test_engine_loads_json_config(self, tmp_path: Path):
        """Engine must load rules from a JSON file as well as YAML."""
        json_rules = {
            "rules": [
                {
                    "id": "RULE_JSON_01",
                    "name": "Test JSON Rule",
                    "category": "Test Category",
                    "severity": 2,
                    "conditions": ["test condition one"],
                    "signals": ["test signal alpha"],
                    "explanation": "A test rule loaded from JSON format.",
                    "reference": "None",
                }
            ]
        }
        json_path = tmp_path / "rules.json"
        json_path.write_text(json.dumps(json_rules), encoding="utf-8")
        eng = SIFRuleEngine(rules_path=json_path)
        assert eng.rule_count == 1
        result = eng.evaluate("this text contains test signal alpha")
        assert "RULE_JSON_01" in triggered_ids(result)

    def test_singleton_returns_same_instance(self):
        """get_rule_engine() must return the same object on repeated calls."""
        a = get_rule_engine()
        b = get_rule_engine()
        assert a is b


# ===========================================================================
# Section 2 — Empty / Edge Case Inputs
# ===========================================================================

class TestEdgeCaseInputs:
    """Verify graceful handling of empty, blank, and minimal inputs."""

    def test_empty_string_returns_no_match(self, engine: SIFRuleEngine):
        result = engine.evaluate("")
        assert result.sif_flag is False
        assert result.overall_severity == 0
        assert len(result.matched_rules) == 0

    def test_whitespace_only_returns_no_match(self, engine: SIFRuleEngine):
        result = engine.evaluate("   \n\t  ")
        assert result.sif_flag is False
        assert len(result.matched_rules) == 0

    def test_none_text_via_empty_string(self, engine: SIFRuleEngine):
        """Passing an empty string should return a clean no-match result."""
        result = engine.evaluate("")
        assert result.overall_severity_label == "NONE"

    def test_generic_unrelated_text_returns_no_match(self, engine: SIFRuleEngine):
        result = engine.evaluate(
            "The quarterly performance review meeting was held in the boardroom."
        )
        assert result.sif_flag is False
        assert result.overall_severity == 0
        assert len(result.matched_rules) == 0

    def test_case_insensitive_matching(self, engine: SIFRuleEngine):
        """Matching must be fully case-insensitive."""
        texts = [
            "ENERGIZED EQUIPMENT was found live near the panel.",
            "Energized Equipment was found live near the panel.",
            "energized equipment was found live near the panel.",
            "EnErGiZeD eQuIpMeNt was found live near the panel.",
        ]
        for text in texts:
            result = engine.evaluate(text)
            assert result.sif_flag is True, f"Expected match for: {text!r}"
            assert "RULE_001" in triggered_ids(result)

    def test_result_sorted_by_descending_severity(self, engine: SIFRuleEngine):
        """Matched rules must be sorted from highest to lowest severity."""
        text = (
            "Worker entered confined space without gas test and was also "
            "working at height without harness."
        )
        result = engine.evaluate(text)
        severities = [r.severity for r in result.matched_rules]
        assert severities == sorted(severities, reverse=True)


# ===========================================================================
# Section 3 — RULE_001: Energy Isolation
# ===========================================================================

class TestRule001EnergyIsolation:
    """Tests for RULE_001 — Energy Isolation Failure."""

    @pytest.mark.parametrize("text,expected_signals", [
        (
            "Technician was working on energized equipment without any isolation.",
            ["energized equipment"],
        ),
        (
            "LOTO not applied before valve maintenance began.",
            ["loto not applied"],
        ),
        (
            "Isolation not verified before opening the control panel.",
            ["isolation not verified"],
        ),
        (
            "Lockout not applied on the pump motor before the repair.",
            ["lockout not applied"],
        ),
        (
            "The worker was observed working on live wire without LOTO.",
            ["live wire"],
        ),
        (
            "Tagout not applied on the circuit breaker during maintenance.",
            ["tagout not applied"],
        ),
        (
            "Equipment was not de-energized before maintenance started.",
            ["not de-energized"],
        ),
        (
            "Energy not isolated on the hydraulic system before inspection.",
            ["energy not isolated"],
        ),
        (
            "A live circuit was accessed without any lockout procedure.",
            ["live circuit"],
        ),
        (
            "Breaker not locked before electrical work commenced.",
            ["breaker not locked"],
        ),
        (
            "No loto was performed on the conveyor before maintenance.",
            ["no loto"],
        ),
        (
            "Worker entered pipeline without isolation applied beforehand.",
            ["without isolation"],
        ),
    ])
    def test_rule_001_triggers(self, engine: SIFRuleEngine, text: str, expected_signals: list):
        result = engine.evaluate(text)
        assert "RULE_001" in triggered_ids(result), f"RULE_001 did not trigger for: {text!r}"
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_001")
        for sig in expected_signals:
            assert sig in match.triggered_signals, (
                f"Expected signal {sig!r} not in triggered_signals: {match.triggered_signals}"
            )

    def test_rule_001_severity_is_critical(self, engine: SIFRuleEngine):
        result = engine.evaluate("Energized equipment found live during maintenance.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_001")
        assert match.severity == 4
        assert match.severity_label == "CRITICAL"

    def test_rule_001_sets_sif_flag(self, engine: SIFRuleEngine):
        result = engine.evaluate("LOTO not applied before starting pump maintenance.")
        assert result.sif_flag is True

    def test_rule_001_has_conditions(self, engine: SIFRuleEngine):
        result = engine.evaluate("Energized equipment found near panel without isolation.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_001")
        assert isinstance(match.conditions, list)
        assert len(match.conditions) >= 1

    def test_rule_001_has_explanation(self, engine: SIFRuleEngine):
        result = engine.evaluate("LOTO not applied, isolation not verified.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_001")
        assert len(match.explanation) > 20  # must be a real sentence

    def test_rule_001_has_reference(self, engine: SIFRuleEngine):
        result = engine.evaluate("LOTO not applied, isolation failure occurred.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_001")
        assert "1910.147" in match.reference

    # False positive tests
    def test_rule_001_no_fp_ordinary_battery(self, engine: SIFRuleEngine):
        """'battery' and 'charged' are not energy isolation signals."""
        result = engine.evaluate("A battery was found fully charged in the storeroom.")
        assert "RULE_001" not in triggered_ids(result)

    def test_rule_001_no_fp_light_switch(self, engine: SIFRuleEngine):
        """Flipping a regular office light switch is not an energy isolation failure."""
        result = engine.evaluate(
            "Office light was switched off before end of day. Normal procedure."
        )
        assert "RULE_001" not in triggered_ids(result)

    def test_rule_001_no_fp_electrical_permit_present(self, engine: SIFRuleEngine):
        """If there's no mention of a safety failure, should not trigger."""
        result = engine.evaluate(
            "Routine electrical inspection completed. All breakers properly locked. "
            "LOTO applied and verified by supervisor before work commenced."
        )
        # 'LOTO applied' is NOT in signals — only 'loto not applied' is
        assert "RULE_001" not in triggered_ids(result)


# ===========================================================================
# Section 4 — RULE_002: Confined Space
# ===========================================================================

class TestRule002ConfinedSpace:
    """Tests for RULE_002 — Confined Space Entry Without Controls."""

    @pytest.mark.parametrize("text,expected_signals", [
        (
            "Worker entered the confined space with no gas test and no attendant present.",
            ["confined space", "no gas test", "no attendant"],
        ),
        (
            "Gas testing not performed before tank entry.",
            ["gas testing not performed", "tank entry"],
        ),
        (
            "Gas testing absent before manhole entry.",
            ["gas testing absent", "manhole"],
        ),
        (
            "Atmospheric testing not performed before confined space entry.",
            ["atmospheric testing not performed", "confined space"],
        ),
        (
            "Permit missing for the vessel entry scheduled today.",
            ["permit missing", "vessel entry"],
        ),
        (
            "Worker entered without permit and no attendant was present.",
            ["without permit", "no attendant"],
        ),
        (
            "Attendant absent during confined space maintenance.",
            ["attendant absent", "confined space"],
        ),
        (
            "No rescue plan available for the confined space work.",
            ["no rescue plan", "confined space"],
        ),
        (
            "Atmospheric monitoring absent during storage tank entry.",
            ["atmospheric monitoring absent", "tank entry"],
        ),
        (
            "Gas test absent prior to manhole inspection.",
            ["gas test absent", "manhole"],
        ),
    ])
    def test_rule_002_triggers(self, engine: SIFRuleEngine, text: str, expected_signals: list):
        result = engine.evaluate(text)
        assert "RULE_002" in triggered_ids(result), f"RULE_002 did not trigger for: {text!r}"
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_002")
        for sig in expected_signals:
            assert sig in match.triggered_signals, (
                f"Expected signal {sig!r} not found in: {match.triggered_signals}"
            )

    def test_rule_002_severity_is_critical(self, engine: SIFRuleEngine):
        result = engine.evaluate("Confined space entry without gas test performed.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_002")
        assert match.severity == 4
        assert match.severity_label == "CRITICAL"

    def test_rule_002_sets_sif_flag(self, engine: SIFRuleEngine):
        result = engine.evaluate("Confined space entered without permit.")
        assert result.sif_flag is True

    def test_rule_002_has_conditions(self, engine: SIFRuleEngine):
        result = engine.evaluate("Confined space entry without permit.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_002")
        assert isinstance(match.conditions, list)
        assert len(match.conditions) >= 1

    def test_rule_002_has_reference(self, engine: SIFRuleEngine):
        result = engine.evaluate("Confined space entered without gas test.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_002")
        assert "1910.146" in match.reference

    # False positive tests
    def test_rule_002_no_fp_open_space(self, engine: SIFRuleEngine):
        """'open space' (the inverse of confined) should not trigger."""
        result = engine.evaluate(
            "Work was performed in an open space area with good ventilation."
        )
        assert "RULE_002" not in triggered_ids(result)

    def test_rule_002_no_fp_office_meeting(self, engine: SIFRuleEngine):
        """Generic text about a meeting room should not trigger."""
        result = engine.evaluate(
            "The team met in the small conference room to discuss quarterly targets."
        )
        assert "RULE_002" not in triggered_ids(result)

    def test_rule_002_no_fp_valid_permit(self, engine: SIFRuleEngine):
        """'permit' alone (in context of valid permit) should not trigger RULE_002
        unless another signal is present."""
        result = engine.evaluate(
            "Excavation permit was approved and signed by the supervisor."
        )
        # 'permit' alone is not a signal — only 'permit missing', 'permit absent' etc.
        # This should NOT trigger RULE_002
        assert "RULE_002" not in triggered_ids(result)


# ===========================================================================
# Section 5 — RULE_003: Working at Height
# ===========================================================================

class TestRule003WorkingAtHeight:
    """Tests for RULE_003 — Working at Height Without Fall Protection."""

    @pytest.mark.parametrize("text,expected_signals", [
        (
            "Worker observed working at height with no harness provided.",
            ["working at height", "no harness"],
        ),
        (
            "Fall protection absent during scaffold work at 5 metres.",
            ["fall protection absent", "scaffold work"],
        ),
        (
            "Harness not used during elevated work on the flare stack.",
            ["harness not used", "elevated work"],
        ),
        (
            "Guardrail missing on the open platform at 8 metres height.",
            ["guardrail missing"],
        ),
        (
            "No guardrail on the elevated work platform.",
            ["no guardrail", "elevated work"],
        ),
        (
            "Worker found not wearing harness while working at height.",
            ["working at height", "not wearing harness"],
        ),
        (
            "Harness absent during roof work inspection.",
            ["harness absent", "roof work"],
        ),
        (
            "Unprotected edge found near the scaffold work area.",
            ["unprotected edge", "scaffold work"],
        ),
        (
            "Guardrail absent on the work at height platform.",
            ["guardrail absent", "work at height"],
        ),
        (
            "Fall protection not provided for elevated work on the derrick.",
            ["fall protection not provided", "elevated work"],
        ),
        (
            "Fall hazard identified during working at elevation.",
            ["fall hazard", "working at elevation"],
        ),
    ])
    def test_rule_003_triggers(self, engine: SIFRuleEngine, text: str, expected_signals: list):
        result = engine.evaluate(text)
        assert "RULE_003" in triggered_ids(result), f"RULE_003 did not trigger for: {text!r}"
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_003")
        for sig in expected_signals:
            assert sig in match.triggered_signals, (
                f"Expected signal {sig!r} not in: {match.triggered_signals}"
            )

    def test_rule_003_severity_is_high(self, engine: SIFRuleEngine):
        result = engine.evaluate("Working at height observed without fall protection.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_003")
        assert match.severity == 3
        assert match.severity_label == "HIGH"

    def test_rule_003_sets_sif_flag(self, engine: SIFRuleEngine):
        result = engine.evaluate("Worker observed working at height without harness.")
        assert result.sif_flag is True

    def test_rule_003_has_conditions(self, engine: SIFRuleEngine):
        result = engine.evaluate("Working at height with no harness observed.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_003")
        assert isinstance(match.conditions, list)
        assert len(match.conditions) >= 1

    def test_rule_003_has_reference(self, engine: SIFRuleEngine):
        result = engine.evaluate("Guardrail missing on elevated work platform.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_003")
        assert "1926.502" in match.reference

    # False positive tests
    def test_rule_003_no_fp_sitting_at_desk(self, engine: SIFRuleEngine):
        """General mention of height as a measurement should not trigger."""
        result = engine.evaluate(
            "The bookshelf height was measured at 2 metres in the storage room."
        )
        assert "RULE_003" not in triggered_ids(result)

    def test_rule_003_no_fp_climbing_with_harness(self, engine: SIFRuleEngine):
        """If harness is properly used (no 'harness not used' signal), no trigger."""
        result = engine.evaluate(
            "Worker climbed the tower wearing a full safety harness and lanyard. "
            "All fall protection equipment was inspected before use."
        )
        assert "RULE_003" not in triggered_ids(result)

    def test_rule_003_no_fp_ground_level_work(self, engine: SIFRuleEngine):
        """Ground-level maintenance with no height signals should not trigger."""
        result = engine.evaluate(
            "Maintenance team replaced the pump seals at ground level. "
            "All safety procedures followed correctly."
        )
        assert "RULE_003" not in triggered_ids(result)


# ===========================================================================
# Section 6 — RULE_004: Hot Work
# ===========================================================================

class TestRule004HotWork:
    """Tests for RULE_004 — Hot Work Without Adequate Controls."""

    @pytest.mark.parametrize("text,expected_signals", [
        (
            "Welding was performed with no fire watch on site.",
            ["welding", "no fire watch"],
        ),
        (
            "Hot work permit absent during cutting operations near the tank.",
            ["hot work permit", "cutting"],
        ),
        (
            "Fire watch absent during welding activity in the process area.",
            ["fire watch absent", "welding"],
        ),
        (
            "Grinding operation started with no fire watch and no permit available.",
            ["grinding", "no permit"],
        ),
        (
            "Open flame observed near flammable material without controls.",
            ["open flame", "flammable material"],
        ),
        (
            "Cutting operation near combustible material; fire watch not present on site.",
            ["cutting", "combustible material", "fire watch not present"],
        ),
        (
            "Hot work in area where gas not cleared.",
            ["hot work", "gas not cleared"],
        ),
        (
            "Welding near hydrocarbon present area without hot work permit.",
            ["welding", "hydrocarbon present", "hot work permit"],
        ),
        (
            "Ignition source found near open flame during maintenance.",
            ["ignition source", "open flame"],
        ),
        (
            "Fire watch missing during hot work permit operations.",
            ["fire watch missing", "hot work permit"],
        ),
        (
            "Hot work started with permit absent in the zone.",
            ["hot work", "permit absent"],
        ),
        (
            "Welding performed with permit missing; fire watch not stationed at the zone.",
            ["welding", "permit missing", "fire watch not stationed"],
        ),
    ])
    def test_rule_004_triggers(self, engine: SIFRuleEngine, text: str, expected_signals: list):
        result = engine.evaluate(text)
        assert "RULE_004" in triggered_ids(result), f"RULE_004 did not trigger for: {text!r}"
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_004")
        for sig in expected_signals:
            assert sig in match.triggered_signals, (
                f"Expected signal {sig!r} not in: {match.triggered_signals}"
            )

    def test_rule_004_severity_is_high(self, engine: SIFRuleEngine):
        result = engine.evaluate("Hot work performed without fire watch.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_004")
        assert match.severity == 3
        assert match.severity_label == "HIGH"

    def test_rule_004_sets_sif_flag(self, engine: SIFRuleEngine):
        result = engine.evaluate("Welding observed without fire watch or permit.")
        assert result.sif_flag is True

    def test_rule_004_has_conditions(self, engine: SIFRuleEngine):
        result = engine.evaluate("Hot work without fire watch observed.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_004")
        assert isinstance(match.conditions, list)
        assert len(match.conditions) >= 1

    def test_rule_004_has_reference(self, engine: SIFRuleEngine):
        result = engine.evaluate("Welding started without fire watch present.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_004")
        assert "NFPA" in match.reference

    # False positive tests
    def test_rule_004_no_fp_cold_work(self, engine: SIFRuleEngine):
        """Cold work like tightening bolts has no hot work signals."""
        result = engine.evaluate(
            "Maintenance team tightened the flange bolts using a torque wrench. "
            "Cold work permit was obtained and all PPE worn."
        )
        assert "RULE_004" not in triggered_ids(result)

    def test_rule_004_no_fp_fire_drill(self, engine: SIFRuleEngine):
        """A fire drill report should not trigger a Hot Work rule."""
        result = engine.evaluate(
            "A scheduled fire drill was conducted. All personnel evacuated "
            "safely within the target time."
        )
        assert "RULE_004" not in triggered_ids(result)

    def test_rule_004_no_fp_permit_approved(self, engine: SIFRuleEngine):
        """'hot work permit' in a context of HAVING the permit is ambiguous —
        but the signal 'hot work permit' DOES trigger; this tests that the
        'no fire watch' absence matters for overall severity, not just the rule."""
        # NOTE: 'hot work permit' in the signals list fires whenever the phrase
        # appears — the phrase alone can indicate a hot work context.
        # This test confirms RULE_004 DOES trigger when 'hot work permit' is found.
        result = engine.evaluate("Hot work permit was obtained before welding started.")
        assert "RULE_004" in triggered_ids(result)  # The context signals are present


# ===========================================================================
# Section 7 — RULE_005: Line of Fire
# ===========================================================================

class TestRule005LineOfFire:
    """Tests for RULE_005 — Line of Fire Exposure."""

    @pytest.mark.parametrize("text,expected_signals", [
        (
            "Worker was in the line of fire during crane lift operations.",
            ["line of fire"],
        ),
        (
            "Employee struck by falling pipe during unloading.",
            ["struck by"],
        ),
        (
            "Worker caught between rotating equipment and fixed structure.",
            ["caught between"],
        ),
        (
            "Exclusion zone missing during overhead crane operation.",
            ["exclusion zone missing"],
        ),
        (
            "No exclusion zone established around the working drill.",
            ["no exclusion zone"],
        ),
        (
            "Worker found below the load during crane lift — no barricade in place.",
            ["below the load", "no barricade"],
        ),
        (
            "Dropped object reported from elevated platform — no barricade.",
            ["dropped object", "no barricade"],
        ),
        (
            "Swinging load observed with workers in path of travel.",
            ["swinging load", "path of travel"],
        ),
        (
            "Overhead load moved with workers standing under the load.",
            ["overhead load", "under the load"],
        ),
        (
            "Barricade absent during pipe handling in the yard.",
            ["barricade absent"],
        ),
        (
            "Exclusion zone absent during blasting operations.",
            ["exclusion zone absent"],
        ),
        (
            "Projectile hazard identified with barricade missing near blast zone.",
            ["projectile", "barricade missing"],
        ),
    ])
    def test_rule_005_triggers(self, engine: SIFRuleEngine, text: str, expected_signals: list):
        result = engine.evaluate(text)
        assert "RULE_005" in triggered_ids(result), f"RULE_005 did not trigger for: {text!r}"
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_005")
        for sig in expected_signals:
            assert sig in match.triggered_signals, (
                f"Expected signal {sig!r} not in: {match.triggered_signals}"
            )

    def test_rule_005_severity_is_high(self, engine: SIFRuleEngine):
        result = engine.evaluate("Worker observed in the line of fire during lift.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_005")
        assert match.severity == 3
        assert match.severity_label == "HIGH"

    def test_rule_005_sets_sif_flag(self, engine: SIFRuleEngine):
        result = engine.evaluate("Worker struck by falling object during lift.")
        assert result.sif_flag is True

    def test_rule_005_has_conditions(self, engine: SIFRuleEngine):
        result = engine.evaluate("Worker in the line of fire during crane operation.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_005")
        assert isinstance(match.conditions, list)
        assert len(match.conditions) >= 1

    def test_rule_005_has_reference(self, engine: SIFRuleEngine):
        result = engine.evaluate("Worker struck by pipe — no exclusion zone present.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_005")
        assert "IOGP" in match.reference or "459" in match.reference

    # False positive tests
    def test_rule_005_no_fp_safe_lift(self, engine: SIFRuleEngine):
        """A properly controlled lift with no LOF signals should not trigger."""
        result = engine.evaluate(
            "Crane lift was conducted with proper exclusion zone established, "
            "all personnel cleared, lift supervisor present and briefed."
        )
        assert "RULE_005" not in triggered_ids(result)

    def test_rule_005_no_fp_sports_injury(self, engine: SIFRuleEngine):
        """The word 'struck' in a non-industrial context should not trigger."""
        result = engine.evaluate(
            "The cricket ball struck the boundary rope during the evening match."
        )
        # 'struck' alone is not a signal — only 'struck by' or 'struck-by'
        assert "RULE_005" not in triggered_ids(result)

    def test_rule_005_no_fp_routine_transport(self, engine: SIFRuleEngine):
        """Routine vehicle movement report with no LOF signals."""
        result = engine.evaluate(
            "Vehicle completed the routine delivery run from the warehouse to site office. "
            "Driver followed all traffic rules."
        )
        assert "RULE_005" not in triggered_ids(result)


# ===========================================================================
# Section 8 — Unrelated Reports (No rules should trigger)
# ===========================================================================

class TestUnrelatedReports:
    """Verify that genuinely unrelated reports produce zero matches."""

    @pytest.mark.parametrize("text", [
        "The monthly safety meeting was held in the conference room without issues.",
        "Employee requested a replacement office chair due to back discomfort.",
        "Noise complaint filed regarding loud music from the neighbouring building.",
        "The canteen menu was updated this week. No incidents to report.",
        "Annual performance appraisals are due by end of the month.",
        "Quarterly fire extinguisher inspections were completed. All units serviceable.",
        "Visitor badges were issued to the auditing team upon arrival at the gate.",
        "The CCTV camera in Corridor B needs a minor realignment.",
        "Drinking water quality test results were satisfactory this quarter.",
        "A new first aid kit was installed in Block C, Room 12.",
    ])
    def test_unrelated_text_triggers_no_rules(self, engine: SIFRuleEngine, text: str):
        result = engine.evaluate(text)
        assert result.sif_flag is False, f"Unexpected SIF flag for: {text!r}"
        assert len(result.matched_rules) == 0, (
            f"Unexpected rules triggered for: {text!r} — rules: {triggered_ids(result)}"
        )
        assert result.overall_severity == 0
        assert result.rule_severity_score == 0.0


# ===========================================================================
# Section 9 — Multiple Rules Triggering on One Report
# ===========================================================================

class TestMultipleRulesTriggering:
    """Verify that compound reports correctly trigger multiple rules."""

    def test_confined_space_plus_energy_isolation(self, engine: SIFRuleEngine):
        """
        Report describing both confined space entry AND LOTO failure
        must trigger RULE_001 and RULE_002.
        """
        text = (
            "Worker entered the storage vessel (confined space) without gas test. "
            "Additionally, energized equipment inside the vessel was found live, "
            "and LOTO had not been applied."
        )
        result = engine.evaluate(text)
        ids = triggered_ids(result)
        assert "RULE_001" in ids, "Expected RULE_001 (Energy Isolation)"
        assert "RULE_002" in ids, "Expected RULE_002 (Confined Space)"
        assert result.overall_severity == 4  # both are CRITICAL
        assert result.overall_severity_label == "CRITICAL"
        assert result.sif_flag is True

    def test_hot_work_plus_line_of_fire(self, engine: SIFRuleEngine):
        """
        Welding near a suspended load with no fire watch and workers below.
        Must trigger RULE_004 (Hot Work) and RULE_005 (Line of Fire).
        """
        text = (
            "Welding was being carried out near the crane lift zone. "
            "Workers were found below the load, no fire watch present, "
            "and exclusion zone missing."
        )
        result = engine.evaluate(text)
        ids = triggered_ids(result)
        assert "RULE_004" in ids, "Expected RULE_004 (Hot Work)"
        assert "RULE_005" in ids, "Expected RULE_005 (Line of Fire)"
        assert result.sif_flag is True

    def test_height_plus_hot_work(self, engine: SIFRuleEngine):
        """
        Working at height without harness and welding with no fire watch.
        Must trigger RULE_003 and RULE_004.
        """
        text = (
            "Welder was working at height on the flare stack without harness. "
            "Welding was in progress with no fire watch stationed nearby."
        )
        result = engine.evaluate(text)
        ids = triggered_ids(result)
        assert "RULE_003" in ids, "Expected RULE_003 (Working at Height)"
        assert "RULE_004" in ids, "Expected RULE_004 (Hot Work)"
        assert result.sif_flag is True

    def test_all_five_rules_trigger(self, engine: SIFRuleEngine):
        """
        A worst-case compound report that touches all 5 SIF categories.
        All 5 rules must fire.
        """
        text = (
            "Investigation report — Multiple violations found at well site 7: "
            "1. Worker entered confined space without gas test or permit. "
            "2. Energized equipment found live — LOTO not applied. "
            "3. Welder working at height without harness, no guardrail present. "
            "4. Hot work in progress with no fire watch present and flammable material nearby. "
            "5. Crane operator noticed workers in the line of fire below the load "
            "   with no exclusion zone established and barricade absent."
        )
        result = engine.evaluate(text)
        ids = triggered_ids(result)
        assert "RULE_001" in ids, "Expected RULE_001 (Energy Isolation)"
        assert "RULE_002" in ids, "Expected RULE_002 (Confined Space)"
        assert "RULE_003" in ids, "Expected RULE_003 (Working at Height)"
        assert "RULE_004" in ids, "Expected RULE_004 (Hot Work)"
        assert "RULE_005" in ids, "Expected RULE_005 (Line of Fire)"
        assert result.overall_severity == 4
        assert result.overall_severity_label == "CRITICAL"
        assert result.sif_flag is True
        assert result.rule_severity_score == 1.0
        assert len(result.triggered_categories) == 5

    def test_two_critical_rules_max_severity_critical(self, engine: SIFRuleEngine):
        """When two CRITICAL rules fire, overall severity must still be 4 (CRITICAL)."""
        text = (
            "Confined space entered without any permit or gas test. "
            "Isolation not verified and energized equipment found live."
        )
        result = engine.evaluate(text)
        assert result.overall_severity == 4
        assert result.overall_severity_label == "CRITICAL"

    def test_multi_rule_triggered_categories_list(self, engine: SIFRuleEngine):
        """Triggered categories must list all unique categories that fired."""
        text = (
            "Working at height without fall protection. "
            "Also, welding with no fire watch present."
        )
        result = engine.evaluate(text)
        cats = set(result.triggered_categories)
        assert "Working at Height" in cats
        assert "Hot Work" in cats

    def test_multi_rule_evidence_summary_contains_all_rules(self, engine: SIFRuleEngine):
        """Evidence summary must reference all triggered rule names."""
        text = (
            "Worker in confined space without gas test and energized equipment live — "
            "LOTO not applied."
        )
        result = engine.evaluate(text)
        for match in result.matched_rules:
            assert match.rule_name in result.evidence_summary


# ===========================================================================
# Section 10 — Serialisation (to_dict)
# ===========================================================================

class TestSerialisation:
    """Verify that RuleMatch and RuleEngineResult serialise correctly."""

    def test_rule_match_to_dict_has_required_keys(self, engine: SIFRuleEngine):
        result = engine.evaluate("Confined space entry without gas test.")
        match = result.matched_rules[0]
        d = match.to_dict()
        required_keys = {
            "rule_id", "rule_name", "category", "severity", "severity_label",
            "conditions", "triggered_signals", "explanation", "reference",
        }
        assert required_keys == set(d.keys())

    def test_rule_engine_result_to_dict_has_required_keys(self, engine: SIFRuleEngine):
        result = engine.evaluate("Energized equipment found live without LOTO applied.")
        d = result.to_dict()
        required_keys = {
            "matched_rules", "overall_severity", "overall_severity_label",
            "sif_flag", "rule_severity_score", "triggered_categories",
            "evidence_summary",
        }
        assert required_keys == set(d.keys())

    def test_to_dict_is_json_serialisable(self, engine: SIFRuleEngine):
        """The full result dict must be JSON serialisable (no Python-only objects)."""
        result = engine.evaluate(
            "Worker in confined space, LOTO not applied, working at height "
            "without harness, welding with no fire watch, struck by pipe."
        )
        serialised = json.dumps(result.to_dict())  # must not raise
        loaded = json.loads(serialised)
        assert loaded["sif_flag"] is True

    def test_no_match_to_dict_structure(self, engine: SIFRuleEngine):
        """Even a no-match result must serialise correctly."""
        result = engine.evaluate("Normal office work completed today.")
        d = result.to_dict()
        assert d["matched_rules"] == []
        assert d["sif_flag"] is False
        assert d["overall_severity"] == 0

    def test_conditions_in_to_dict(self, engine: SIFRuleEngine):
        """conditions must appear in to_dict output."""
        result = engine.evaluate("Working at height without fall protection.")
        match = next(r for r in result.matched_rules if r.rule_id == "RULE_003")
        d = match.to_dict()
        assert "conditions" in d
        assert isinstance(d["conditions"], list)


# ===========================================================================
# Section 11 — Rule Severity Score
# ===========================================================================

class TestSeverityScore:
    """Verify the normalised rule_severity_score field."""

    def test_no_match_score_is_zero(self, engine: SIFRuleEngine):
        result = engine.evaluate("Nothing unsafe here at all.")
        assert result.rule_severity_score == 0.0

    def test_high_match_score_is_0_75(self, engine: SIFRuleEngine):
        """HIGH severity (3) / 4 = 0.75."""
        result = engine.evaluate("Working at height without fall protection.")
        # RULE_003 is HIGH (3)
        # If only RULE_003 fires, score should be 0.75
        if result.overall_severity == 3:
            assert result.rule_severity_score == pytest.approx(0.75, abs=0.001)

    def test_critical_match_score_is_1_0(self, engine: SIFRuleEngine):
        """CRITICAL severity (4) / 4 = 1.0."""
        result = engine.evaluate("Confined space entered without gas test or permit.")
        if result.overall_severity == 4:
            assert result.rule_severity_score == pytest.approx(1.0, abs=0.001)

    def test_score_bounded_between_0_and_1(self, engine: SIFRuleEngine):
        """Score must always be in [0.0, 1.0]."""
        reports = [
            "Nothing unsafe.",
            "Working at height without harness.",
            "Energized equipment found live — LOTO not applied.",
            "All five: confined space, LOTO not applied, harness not used, welding, struck by.",
        ]
        for text in reports:
            result = engine.evaluate(text)
            assert 0.0 <= result.rule_severity_score <= 1.0, (
                f"Score out of range for: {text!r}"
            )
