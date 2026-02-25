# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for benchmarks/technical/causal/benchmark_counterbench.py."""

import numpy as np

from benchmarks.technical.causal.benchmark_counterbench import (
    CARFEstimate,
    ScenarioResult,
    _bootstrap_ci,
    _generate_confounded_scenarios,
    _generate_linear_scenarios,
    _ols_estimate,
    _ols_estimate_with_ci,
    compute_calibration_metrics,
    estimate_llm_baseline,
    generate_all_scenarios,
)


class TestScenarioGeneration:
    """Tests for scenario generators."""

    def test_generate_all_produces_60_scenarios(self):
        scenarios = generate_all_scenarios()
        assert len(scenarios) == 60

    def test_linear_scenarios_count(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_linear_scenarios(rng, start_id=1)
        assert len(scenarios) == 20
        assert all(s.dgp_type == "linear" for s in scenarios)

    def test_confounded_scenarios_count(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_confounded_scenarios(rng, start_id=51)
        assert len(scenarios) == 10
        assert all(s.dgp_type == "confounded" for s in scenarios)

    def test_confounded_scenarios_have_strong_confounding(self):
        """Verify naive estimator is biased for confounded scenarios."""
        rng = np.random.default_rng(42)
        scenarios = _generate_confounded_scenarios(rng, start_id=51)

        for sc in scenarios:
            estimate_llm_baseline(sc)
            _ols_estimate(sc)
            # Verify confounded scenarios have expected data size
            assert len(sc.data) == 300

    def test_scenario_ids_unique(self):
        scenarios = generate_all_scenarios()
        ids = [s.id for s in scenarios]
        assert len(ids) == len(set(ids))

    def test_dgp_type_distribution(self):
        scenarios = generate_all_scenarios()
        types = [s.dgp_type for s in scenarios]
        assert types.count("linear") == 20
        assert types.count("nonlinear") == 15
        assert types.count("interaction") == 10
        assert types.count("threshold") == 5
        assert types.count("confounded") == 10


class TestOLSEstimate:
    """Tests for OLS estimation."""

    def test_ols_recovers_linear_effect(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_linear_scenarios(rng, start_id=1)
        sc = scenarios[0]  # true effect = 1.5

        est = _ols_estimate(sc)
        assert abs(est - sc.true_counterfactual_effect) < 0.5

    def test_ols_with_ci_returns_carf_estimate(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_linear_scenarios(rng, start_id=1)
        sc = scenarios[0]

        result = _ols_estimate_with_ci(sc)
        assert isinstance(result, CARFEstimate)
        assert result.ci_lower < result.effect
        assert result.ci_upper > result.effect


class TestBootstrapCI:
    """Tests for bootstrap CI."""

    def test_bootstrap_ci_contains_point_estimate(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_linear_scenarios(rng, start_id=1)
        sc = scenarios[0]

        ci_lower, ci_upper = _bootstrap_ci(sc, n_boot=100)
        point_est = _ols_estimate(sc)

        assert ci_lower <= point_est <= ci_upper

    def test_bootstrap_ci_width_positive(self):
        rng = np.random.default_rng(42)
        scenarios = _generate_linear_scenarios(rng, start_id=1)
        sc = scenarios[0]

        ci_lower, ci_upper = _bootstrap_ci(sc)
        assert ci_upper > ci_lower


class TestCalibrationMetrics:
    """Tests for CalibrationMetrics computation."""

    def test_perfect_coverage(self):
        results = [
            ScenarioResult(
                scenario_id=i, dgp_type="linear", true_effect=1.0,
                carf_estimate=1.0, llm_estimate=2.0,
                carf_error=0.0, llm_error=1.0,
                carf_correct=True, llm_correct=False,
                elapsed_seconds=0.1,
                carf_ci_lower=0.5, carf_ci_upper=1.5,
                ci_covers_truth=True,
            )
            for i in range(10)
        ]

        cal = compute_calibration_metrics(results)
        assert cal.ci_coverage_rate == 1.0

    def test_no_coverage(self):
        results = [
            ScenarioResult(
                scenario_id=1, dgp_type="linear", true_effect=5.0,
                carf_estimate=1.0, llm_estimate=2.0,
                carf_error=4.0, llm_error=3.0,
                carf_correct=False, llm_correct=False,
                elapsed_seconds=0.1,
                carf_ci_lower=0.5, carf_ci_upper=1.5,
                ci_covers_truth=False,
            )
        ]

        cal = compute_calibration_metrics(results)
        assert cal.ci_coverage_rate == 0.0

    def test_empty_results(self):
        cal = compute_calibration_metrics([])
        assert cal.ci_coverage_rate == 0.0
        assert cal.mean_ci_width == 0.0


class TestLLMBaseline:
    """Tests for naive LLM baseline estimator."""

    def test_confounded_naive_is_biased(self):
        """Naive diff-in-means should be biased on confounded data."""
        rng = np.random.default_rng(42)
        scenarios = _generate_confounded_scenarios(rng, start_id=51)

        biased_count = 0
        for sc in scenarios:
            naive = estimate_llm_baseline(sc)
            ols = _ols_estimate(sc)
            naive_err = abs(naive - sc.true_counterfactual_effect)
            ols_err = abs(ols - sc.true_counterfactual_effect)
            if naive_err > ols_err:
                biased_count += 1

        # At least 70% of confounded scenarios should show naive bias
        assert biased_count >= 7, f"Only {biased_count}/10 confounded scenarios showed naive bias"
