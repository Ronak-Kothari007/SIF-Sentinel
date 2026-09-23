"""
SIF Sentinel — Unit Tests for models/decision_engine.py Module & CLI
====================================================================
"""

from __future__ import annotations

import pytest
from pathlib import Path

from models.decision_engine import batch_evaluate, evaluate_report, process_csv


class TestModelsDecisionEngineModule:
    def test_evaluate_report_returns_dict(self):
        result = evaluate_report("Maintenance started on energized equipment without verified isolation.")
        assert isinstance(result, dict)
        assert result["priority"] == "HIGH"
        assert result["activity"] == "Maintenance"
        assert result["hazard"] == "Electrical Energy"
        assert result["barrier"] == "Isolation"
        assert "does not predict accident" in result["explanation"].lower()

    def test_batch_evaluate_length_matches(self):
        texts = [
            "Welding operation without hot work permit.",
            "Confined space entry without gas testing.",
            "Toolbox safety meeting conducted. All workers attended.",
        ]
        results = batch_evaluate(texts)
        assert len(results) == 3
        assert results[0]["priority"] in ["HIGH", "MEDIUM"]
        assert results[2]["priority"] == "LOW"

    def test_process_csv(self, tmp_path: Path):
        input_csv = tmp_path / "reports_in.csv"
        output_csv = tmp_path / "decisions_out.csv"

        input_csv.write_text(
            "report_id,report_text\n"
            "SYN-DEC-1,Maintenance started on energized equipment without verified isolation.\n"
            "SYN-DEC-2,Toolbox meeting conducted at start of shift. No incidents.\n",
            encoding="utf-8",
        )

        process_csv(input_csv, output_csv)
        assert output_csv.exists()

        content = output_csv.read_text(encoding="utf-8")
        assert "priority" in content
        assert "HIGH" in content
        assert "LOW" in content
        assert "decision_activity" in content
