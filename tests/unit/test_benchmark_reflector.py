"""Tests for the reflector benchmark scenarios and validation logic."""

import pytest
from benchmarks.technical.reflector.benchmark_reflector import (
    SCENARIOS,
    validate_repair,
    _count_numeric_fields,
    _count_modified_numeric_fields,
)


class TestReflectorBenchmarkScenarios:
    """Verify scenarios are well-formed."""

    def test_all_scenarios_have_required_fields(self):
        """All scenarios must have name, violations, proposed_action, expected."""
        for scenario in SCENARIOS:
            assert "name" in scenario, f"Missing name in scenario"
            assert "violations" in scenario, f"Missing violations in {scenario['name']}"
            assert "proposed_action" in scenario, f"Missing proposed_action in {scenario['name']}"
            assert "expected" in scenario, f"Missing expected in {scenario['name']}"

    def test_scenarios_have_unique_names(self):
        """Scenario names must be unique."""
        names = [s["name"] for s in SCENARIOS]
        assert len(names) == len(set(names))

    def test_violations_are_non_empty_strings(self):
        """Violations must be non-empty string lists."""
        for scenario in SCENARIOS:
            assert len(scenario["violations"]) > 0
            for v in scenario["violations"]:
                assert isinstance(v, str) and len(v) > 0

    def test_proposed_actions_have_action_type(self):
        """All proposed actions should have an action_type."""
        for scenario in SCENARIOS:
            assert "action_type" in scenario["proposed_action"]

    def test_scenario_count(self):
        """Should have exactly 5 scenarios."""
        assert len(SCENARIOS) == 5


class TestValidateRepair:
    """Test the validate_repair logic."""

    def test_budget_repair_validation(self):
        """Budget repair should detect reduced amounts."""
        original = {"action_type": "invest", "amount": 150000}
        repaired = {"action_type": "invest", "amount": 120000}
        scenario = {
            "expected": {"repair_attempted": True, "amount_reduced": True},
        }
        checks = validate_repair(original, repaired, scenario)
        assert checks["action_modified"] is True
        assert checks["repair_attempted"] is True
        assert checks["amount_reduced"] is True

    def test_no_repair_expected(self):
        """Unknown violation should correctly detect no modification."""
        original = {"action_type": "transfer", "region": "us-east-1"}
        scenario = {"expected": {"repair_attempted": False}}
        checks = validate_repair(original, original.copy(), scenario)
        assert checks["correctly_skipped"] is True

    def test_human_review_flag_detection(self):
        """Should detect requires_human_review flag."""
        original = {"action_type": "deploy"}
        repaired = {"action_type": "deploy", "requires_human_review": True}
        scenario = {
            "expected": {"repair_attempted": True, "requires_human_review": True},
        }
        checks = validate_repair(original, repaired, scenario)
        assert checks["requires_human_review"] is True

    def test_values_reduced_detection(self):
        """Should detect numeric value reduction."""
        original = {"action_type": "adjust", "effect_size": 0.95, "margin": 15.0}
        repaired = {"action_type": "adjust", "effect_size": 0.855, "margin": 13.5}
        scenario = {
            "expected": {"repair_attempted": True, "values_reduced": True},
        }
        checks = validate_repair(original, repaired, scenario)
        assert checks["values_reduced"] is True


class TestNumericFieldCounting:
    """Test helper functions for blind mutation detection."""

    def test_count_numeric_fields_flat(self):
        """Count numeric fields in a flat dict."""
        action = {"action_type": "invest", "amount": 150000, "risk": 0.5}
        assert _count_numeric_fields(action) == 2

    def test_count_numeric_fields_nested(self):
        """Count numeric fields including nested dicts."""
        action = {"amount": 100, "parameters": {"margin": 15.0, "name": "test"}}
        assert _count_numeric_fields(action) == 2  # amount + margin

    def test_count_modified_fields(self):
        """Count how many fields changed."""
        original = {"amount": 100, "risk": 0.5}
        repaired = {"amount": 80, "risk": 0.5}
        assert _count_modified_numeric_fields(original, repaired) == 1

    def test_booleans_excluded(self):
        """Booleans should not count as numeric."""
        action = {"amount": 100, "active": True}
        assert _count_numeric_fields(action) == 1
