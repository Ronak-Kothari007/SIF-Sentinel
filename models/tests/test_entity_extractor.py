"""
SIF Sentinel — Unit Tests for models/entity_extractor.py Module & CLI
=====================================================================
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from models.entity_extractor import batch_extract, extract_safety_context, process_csv


class TestModelsEntityExtractorModule:
    def test_extract_safety_context_returns_dict(self):
        result = extract_safety_context("Maintenance started on energized equipment without verified isolation.")
        assert isinstance(result, dict)
        assert result["activity"] == "Maintenance"
        assert result["hazard"] == "Electrical Energy"
        assert result["barrier"] == "Isolation"
        assert result["barrier_status"] == "Not Verified"
        assert result["equipment"] == "energized equipment"

    def test_batch_extract_length_matches(self):
        texts = [
            "Welding operation without hot work permit.",
            "Confined space entry without gas testing.",
            "Routine meeting conducted.",
        ]
        results = batch_extract(texts)
        assert len(results) == 3
        assert results[0]["activity"] == "Welding"
        assert results[1]["barrier"] == "Gas Testing"

    def test_process_csv(self, tmp_path: Path):
        input_csv = tmp_path / "test_input.csv"
        output_csv = tmp_path / "test_output.csv"

        input_csv.write_text(
            "report_id,report_text\n"
            "SYN-TEST-1,Maintenance started on energized equipment without verified isolation.\n"
            "SYN-TEST-2,Worker on scaffold at 6 metres without harness.\n",
            encoding="utf-8",
        )

        process_csv(input_csv, output_csv)
        assert output_csv.exists()

        content = output_csv.read_text(encoding="utf-8")
        assert "extracted_activity" in content
        assert "extracted_hazard" in content
        assert "extracted_barrier" in content
        assert "extracted_barrier_status" in content
        assert "Maintenance" in content
        assert "Electrical Energy" in content
