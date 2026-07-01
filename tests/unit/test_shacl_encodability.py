"""Unit tests for H49 SHACL Encodability Benchmark (R3)."""

import json
import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def reset_shacl():
    from src.services.shacl_service import reset_shacl_service

    reset_shacl_service()
    yield
    reset_shacl_service()


class TestH49Benchmark:
    def test_run_benchmark_returns_dict(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        assert isinstance(result, dict)
        assert result["benchmark_id"] == "shacl_encodability"

    def test_run_benchmark_encodability(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        assert result["encodability"]["ratio"] > 0.0
        assert result["encodability"]["total_policies"] > 0
        assert result["encodability"]["encodable_policies"] > 0

    def test_run_benchmark_grade(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        assert result["grade"] in (
            "validated",
            "needs-independent-replication",
            "synthetic-only",
            "aspirational",
        )

    def test_run_benchmark_validation_section(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        assert "validation" in result
        assert result["validation"]["total_tests"] > 0

    def test_run_benchmark_non_encodable_rules(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        # Escalation rules should be non-encodable
        escalation_entries = [
            e for e in result["non_encodable_rules"] if e["policy_name"] == "escalation"
        ]
        assert len(escalation_entries) > 0

    def test_run_benchmark_encodable_rules(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        # Budget limits should have encodable rules
        budget_entries = [
            e for e in result["encodable_rules"] if e["policy_name"] == "budget_limits"
        ]
        assert len(budget_entries) > 0

    def test_run_benchmark_with_output(self, tmp_path):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        output = tmp_path / "h49_result.json"
        run_benchmark(str(output))
        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded["benchmark_id"] == "shacl_encodability"

    def test_yaml_encodability_positive(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import run_benchmark

        result = run_benchmark()
        assert result["encodability"]["yaml_policies_encodable"] > 0


class TestH49ValidationCases:
    def test_validation_test_cases_well_formed(self):
        from benchmarks.technical.governance.benchmark_shacl_encodability import (
            VALIDATION_TEST_CASES,
        )

        assert len(VALIDATION_TEST_CASES) >= 5
        for case in VALIDATION_TEST_CASES:
            assert "name" in case
            assert "context" in case
            assert isinstance(case["context"], dict)
            assert "expected_violations" in case
            assert "description" in case
