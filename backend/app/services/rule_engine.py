"""
SIF Sentinel — Deterministic Safety Rule Engine
================================================

This module implements the SIF precursor rule engine (Stage 4 of the NLP pipeline).

Design principles:
  - Fully deterministic: same input -> same output, always.
  - No ML model involved. No randomness. No external calls.
  - Rules are loaded from sif_rules.yaml (or .json) at initialisation.
  - Every match records exactly which signal phrase triggered it (the "evidence").
  - Explainable: HSE officers can trace every flag back to a specific phrase.
  - Modular: engine is independent of the ML pipeline and can be used standalone.

Rule structure (in sif_rules.yaml):
    id:          Unique rule identifier (e.g. "RULE_001")
    name:        Human-readable rule name
    category:    SIF precursor category (e.g. "Energy Isolation")
    severity:    Integer 1-4 (LOW / MEDIUM / HIGH / CRITICAL)
    conditions:  Human-readable list of what triggers this rule (for HSE officers)
    signals:     List of lowercase substring phrases the engine matches against text
    explanation: Plain-English explanation of why this is a SIF precursor
    reference:   Regulatory / industry standard citation (optional)

Usage:
    from app.services.rule_engine import SIFRuleEngine
    engine = SIFRuleEngine()
    result = engine.evaluate("Worker entered confined space without gas test")
    print(result.sif_flag)                         # True
    print(result.overall_severity_label)           # 'CRITICAL'
    print(result.matched_rules[0].triggered_signals)  # ['confined space', ...]
    print(result.matched_rules[0].conditions)      # ['confined space entry detected', ...]
"""

from __future__ import annotations

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

SEVERITY_LABELS: dict[int, str] = {
    0: "NONE",
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "CRITICAL",
}

# SIF flag threshold: rules with severity >= this value raise the sif_flag
SIF_FLAG_THRESHOLD = 3  # HIGH or CRITICAL


# ---------------------------------------------------------------------------
# Data classes — public API of the rule engine
# ---------------------------------------------------------------------------

@dataclass
class RuleMatch:
    """
    Represents a single rule that was triggered by the report text.

    Attributes:
        rule_id:           Rule identifier from config (e.g. 'RULE_001')
        rule_name:         Human-readable rule name
        category:          SIF precursor category (e.g. 'Energy Isolation')
        severity:          Integer severity 1-4
        severity_label:    Human label ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
        conditions:        Human-readable list of conditions that define this rule
                           (for HSE officer audit — does NOT affect matching)
        triggered_signals: The exact phrases in the report text that matched
        explanation:       Plain-English explanation of why this is a SIF precursor
        reference:         Regulatory or industry standard reference
    """
    rule_id: str
    rule_name: str
    category: str
    severity: int
    severity_label: str
    conditions: list[str]
    triggered_signals: list[str]
    explanation: str
    reference: str

    def to_dict(self) -> dict:
        """Serialise to a plain dict for API responses."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "severity_label": self.severity_label,
            "conditions": self.conditions,
            "triggered_signals": self.triggered_signals,
            "explanation": self.explanation.strip(),
            "reference": self.reference,
        }


@dataclass
class RuleEngineResult:
    """
    The complete output of the rule engine for a single report.

    Attributes:
        matched_rules:          All rules that fired, in descending severity order
        overall_severity:       Max severity across all triggered rules (0 if none)
        overall_severity_label: Human label for overall_severity
        sif_flag:               True if any rule with severity >= 3 (HIGH) was triggered
        rule_severity_score:    Normalised score 0.0-1.0 (overall_severity / 4.0)
        triggered_categories:   Unique SIF categories that were flagged
        evidence_summary:       Short human-readable summary of all triggered signals
    """
    matched_rules: list[RuleMatch] = field(default_factory=list)
    overall_severity: int = 0
    overall_severity_label: str = "NONE"
    sif_flag: bool = False
    rule_severity_score: float = 0.0
    triggered_categories: list[str] = field(default_factory=list)
    evidence_summary: str = "No SIF precursor signals detected by rule engine."

    def to_dict(self) -> dict:
        """Serialise to a plain dict for API responses."""
        return {
            "matched_rules": [r.to_dict() for r in self.matched_rules],
            "overall_severity": self.overall_severity,
            "overall_severity_label": self.overall_severity_label,
            "sif_flag": self.sif_flag,
            "rule_severity_score": self.rule_severity_score,
            "triggered_categories": self.triggered_categories,
            "evidence_summary": self.evidence_summary,
        }


# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------

class SIFRuleEngine:
    """
    Deterministic SIF precursor rule engine.

    Loads rules from sif_rules.yaml (or sif_rules.json if YAML is absent)
    and evaluates them against report text using case-insensitive substring
    matching. The engine is stateless after initialisation — safe to share
    across requests.

    No ML model, no randomness, no external calls. Every result is fully
    auditable back to a specific phrase in the report text.
    """

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        """
        Initialise the engine by loading rules from YAML or JSON.

        Args:
            rules_path: Path to sif_rules.yaml or sif_rules.json.
                        Defaults to the standard location relative to this
                        file: ../../rules/sif_rules.yaml
        """
        if rules_path is None:
            rules_path = (
                Path(__file__).resolve().parent.parent / "rules" / "sif_rules.yaml"
            )
        self._rules_path = rules_path
        self._rules: list[dict] = self._load_rules(rules_path)

    def _load_rules(self, path: Path) -> list[dict]:
        """
        Parse and validate the rules config file (YAML or JSON).

        Args:
            path: Absolute path to the rules file.

        Returns:
            Validated list of rule dicts.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If any rule is malformed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            suffix = path.suffix.lower()
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(
                    f"Unsupported rules file format: {suffix!r}. "
                    "Use .yaml, .yml, or .json"
                )

        rules = data.get("rules", [])
        self._validate_rules(rules)
        return rules

    @staticmethod
    def _validate_rules(rules: list[dict]) -> None:
        """
        Verify each rule has all required fields and valid values.
        Raises ValueError on the first malformed rule encountered.

        Required fields: id, name, category, severity, signals, explanation
        Optional fields: conditions, reference
        """
        required_fields = {"id", "name", "category", "severity", "signals", "explanation"}
        for rule in rules:
            missing = required_fields - set(rule.keys())
            if missing:
                raise ValueError(
                    f"Rule '{rule.get('id', '?')}' is missing required fields: {missing}"
                )
            if not isinstance(rule["severity"], int) or not (1 <= rule["severity"] <= 4):
                raise ValueError(
                    f"Rule '{rule['id']}': severity must be an integer 1-4, "
                    f"got {rule['severity']!r}"
                )
            if not isinstance(rule["signals"], list) or len(rule["signals"]) == 0:
                raise ValueError(
                    f"Rule '{rule['id']}': signals must be a non-empty list"
                )
            # conditions is optional but if present must be a list
            if "conditions" in rule and not isinstance(rule["conditions"], list):
                raise ValueError(
                    f"Rule '{rule['id']}': conditions must be a list if present"
                )

    # ── Public API ──────────────────────────────────────────────────────────

    def evaluate(self, text: str) -> RuleEngineResult:
        """
        Evaluate all rules against the given report text.

        Matching is case-insensitive substring search. A rule fires if
        at least one of its signal phrases is found anywhere in the text.
        Signal matching is based on substring containment, not word boundaries,
        so "welding" matches "welding fumes" and "auto-welding".

        Args:
            text: The safety report text (plain string).

        Returns:
            RuleEngineResult containing all triggered rules, severity,
            conditions, evidence, and explanation.
        """
        if not text or not text.strip():
            return RuleEngineResult(
                evidence_summary="Empty report text. No rules evaluated."
            )

        text_lower = text.lower()
        matched_rules: list[RuleMatch] = []

        for rule in self._rules:
            triggered_signals = [
                signal
                for signal in rule["signals"]
                if signal.lower() in text_lower
            ]
            if not triggered_signals:
                continue

            severity = rule["severity"]
            matched_rules.append(
                RuleMatch(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    category=rule["category"],
                    severity=severity,
                    severity_label=SEVERITY_LABELS[severity],
                    conditions=rule.get("conditions", []),
                    triggered_signals=triggered_signals,
                    explanation=rule["explanation"].strip(),
                    reference=rule.get("reference", ""),
                )
            )

        # Sort by descending severity so highest-risk rules appear first
        matched_rules.sort(key=lambda r: r.severity, reverse=True)

        if not matched_rules:
            return RuleEngineResult()

        overall_severity = max(r.severity for r in matched_rules)
        triggered_categories = list(
            dict.fromkeys(r.category for r in matched_rules)  # preserve insertion order
        )
        sif_flag = overall_severity >= SIF_FLAG_THRESHOLD
        rule_severity_score = round(overall_severity / 4.0, 4)

        # Build a concise human-readable evidence summary
        evidence_parts = []
        for rule in matched_rules:
            signals_str = ", ".join(f'"{s}"' for s in rule.triggered_signals)
            evidence_parts.append(
                f"{rule.rule_name} ({rule.severity_label}): triggered by {signals_str}"
            )
        evidence_summary = " | ".join(evidence_parts)

        return RuleEngineResult(
            matched_rules=matched_rules,
            overall_severity=overall_severity,
            overall_severity_label=SEVERITY_LABELS[overall_severity],
            sif_flag=sif_flag,
            rule_severity_score=rule_severity_score,
            triggered_categories=triggered_categories,
            evidence_summary=evidence_summary,
        )

    @property
    def rule_count(self) -> int:
        """Number of rules currently loaded."""
        return len(self._rules)

    @property
    def rules_path(self) -> Path:
        """Path to the loaded rules file."""
        return self._rules_path

    def get_rule_ids(self) -> list[str]:
        """Return the list of rule IDs in load order."""
        return [r["id"] for r in self._rules]

    def get_rule_categories(self) -> list[str]:
        """Return the unique list of rule categories in load order."""
        return list(dict.fromkeys(r["category"] for r in self._rules))


# ---------------------------------------------------------------------------
# Module-level singleton — import and reuse this across the application
# ---------------------------------------------------------------------------

_engine_instance: Optional[SIFRuleEngine] = None


def get_rule_engine() -> SIFRuleEngine:
    """
    Return the shared SIFRuleEngine singleton.

    Initialises on first call and reuses thereafter.
    This avoids re-reading the YAML file on every request.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SIFRuleEngine()
    return _engine_instance
