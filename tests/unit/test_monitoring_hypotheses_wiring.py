# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for H40-H43 monitoring hypotheses wiring in generate_report.

Backs roadmap deliverable P0.6: ensure the unified report no longer silently
drops the four Phase 18 monitoring benchmarks.
"""

from __future__ import annotations

import pytest

from benchmarks.reports.generate_report import HYPOTHESES, evaluate_hypotheses


@pytest.fixture
def monitoring_results() -> dict:
    """Synthetic results that match each monitoring benchmark's actual emit shape."""
    return {
        "monitoring_drift": {
            "sensitivity": 0.95,
            "specificity": 0.92,
            "true_positives": 8,
            "true_negatives": 4,
            "total_scenarios": 5,
        },
        "monitoring_bias": {
            "bias_detection_accuracy": 0.93,
            "sensitivity": 0.95,
            "false_alarm_rate": 0.05,
            "detection_specificity": 0.95,
            "total_scenarios": 7,
        },
        "monitoring_plateau": {
            "plateau_detection_accuracy": 0.91,
            "regression_detection_accuracy": 0.93,
            "false_plateau_rate": 0.07,
            "total_scenarios": 6,
        },
        "monitoring_guardian": {
            "guardian_enforcement_rate": 1.0,
            "fast_path_availability_rate": 1.0,
            "fallback_rate": 1.0,
            "passed_tests": 4,
            "total_tests": 4,
        },
    }


def _eval_by_id(results: dict) -> dict:
    return {e["id"]: e for e in evaluate_hypotheses(results)}


def test_hypotheses_includes_h40_h43():
    ids = {h["id"] for h in HYPOTHESES}
    assert {"H40", "H41", "H42", "H43"}.issubset(ids)


def test_hypotheses_total_is_43_with_h20_absent():
    ids = [h["id"] for h in HYPOTHESES]
    assert len(ids) == 43
    assert "H20" not in ids


def test_h40_drift_sensitivity_pass(monitoring_results):
    e = _eval_by_id(monitoring_results)["H40"]
    assert e["status"] == "evaluated"
    assert e["metric_value"] == 0.95
    assert e["passed"] is True
    assert e["details"]["specificity"] == 0.92


def test_h40_drift_sensitivity_fail():
    e = _eval_by_id({"monitoring_drift": {"sensitivity": 0.80, "specificity": 0.99}})["H40"]
    assert e["status"] == "evaluated"
    assert e["passed"] is False


def test_h41_bias_detection_accuracy_pass(monitoring_results):
    e = _eval_by_id(monitoring_results)["H41"]
    assert e["status"] == "evaluated"
    assert e["metric_value"] == 0.93
    assert e["passed"] is True
    assert e["details"]["sensitivity"] == 0.95


def test_h42_plateau_detection_accuracy_pass(monitoring_results):
    e = _eval_by_id(monitoring_results)["H42"]
    assert e["status"] == "evaluated"
    assert e["metric_value"] == 0.91
    assert e["passed"] is True
    assert e["details"]["regression_detection_accuracy"] == 0.93


def test_h43_fast_path_guardian_enforcement_pass(monitoring_results):
    e = _eval_by_id(monitoring_results)["H43"]
    assert e["status"] == "evaluated"
    assert e["metric_value"] == 1.0
    assert e["passed"] is True


def test_h43_fast_path_guardian_partial_enforcement_fails():
    e = _eval_by_id({"monitoring_guardian": {"guardian_enforcement_rate": 0.99}})["H43"]
    assert e["status"] == "evaluated"
    assert e["passed"] is False


def test_h40_h43_status_no_data_when_results_absent():
    evals = _eval_by_id({})
    for hid in ("H40", "H41", "H42", "H43"):
        assert evals[hid]["status"] == "no_data"
        assert evals[hid]["passed"] is None
        assert evals[hid]["metric_value"] is None
