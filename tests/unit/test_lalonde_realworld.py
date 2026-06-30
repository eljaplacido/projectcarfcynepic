# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the LaLonde real-data causal benchmark (R2 / H51)."""

from __future__ import annotations

import pytest

from benchmarks.technical.realworld.benchmark_lalonde import (
    BIAS_REDUCTION_MIN,
    COVARIATES,
    EXPERIMENTAL_REL_ERROR_MAX,
    compute_metrics,
    diff_in_means,
    load_lalonde,
)


class TestComputeMetrics:
    """Pure metric logic — no DoWhy required."""

    def test_passes_on_good_recovery_and_bias_reduction(self):
        m = compute_metrics(
            ground_truth=1794.0,
            experimental_estimate=1676.0,
            observational_naive=-15205.0,
            observational_adjusted=752.0,
        )
        assert m["experimental_rel_error"] < EXPERIMENTAL_REL_ERROR_MAX
        assert m["bias_reduction"] > BIAS_REDUCTION_MIN
        assert m["passed"] is True

    def test_fails_on_poor_experimental_recovery(self):
        m = compute_metrics(
            ground_truth=1794.0,
            experimental_estimate=500.0,  # 72% error
            observational_naive=-15205.0,
            observational_adjusted=752.0,
        )
        assert m["passed"] is False

    def test_fails_when_adjustment_does_not_reduce_bias(self):
        m = compute_metrics(
            ground_truth=1794.0,
            experimental_estimate=1700.0,
            observational_naive=-15205.0,
            observational_adjusted=-14000.0,  # barely better than naive
        )
        assert m["bias_reduction"] < BIAS_REDUCTION_MIN
        assert m["passed"] is False

    def test_experimental_only_passes_without_observational(self):
        m = compute_metrics(1794.0, 1700.0, None, None)
        assert "bias_reduction" not in m
        assert m["passed"] is True


@pytest.mark.skipif(load_lalonde() is None, reason="LaLonde/PSID dataset unavailable")
class TestRealLaLondeData:
    """Validates against the actual bundled Dehejia-Wahba data."""

    def test_experimental_ground_truth_matches_known_value(self):
        nsw, _ = load_lalonde()
        gt = diff_in_means(nsw)
        # Dehejia-Wahba experimental ATE on the 445-row NSW subset is ~$1,794.
        assert 1700 < gt < 1900
        assert len(nsw) == 445

    def test_covariates_present(self):
        nsw, _ = load_lalonde()
        for col in COVARIATES + ["treat", "re78"]:
            assert col in nsw.columns

    @pytest.mark.asyncio
    async def test_carf_recovers_experimental_ate(self):
        """The engine's estimate on the RCT sample is within tolerance of the truth."""
        from benchmarks.technical.realworld.benchmark_lalonde import _carf_ate

        nsw, _ = load_lalonde()
        gt = diff_in_means(nsw)
        est = await _carf_ate(nsw.to_dict("records"), COVARIATES)
        rel_err = abs(est["effect"] - gt) / abs(gt)
        assert rel_err <= EXPERIMENTAL_REL_ERROR_MAX
