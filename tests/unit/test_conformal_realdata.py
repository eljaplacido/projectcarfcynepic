# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for split-conformal regression + real-data coverage (R2 / H53)."""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.technical.realworld.benchmark_conformal_realdata import (
    COVERAGE_TOLERANCE,
    compute_coverage,
    load_real_dataset,
)
from src.utils.conformal import conformal_regression_quantile, regression_coverage


class TestConformalRegressionHelpers:
    def test_quantile_requires_residuals(self):
        with pytest.raises(ValueError):
            conformal_regression_quantile([])

    def test_tiny_set_is_conservative(self):
        # Too few points for the requested alpha -> qhat = inf -> full coverage.
        assert conformal_regression_quantile([1.0, 2.0], alpha=0.01) == float("inf")

    @pytest.mark.parametrize("alpha", [0.05, 0.1, 0.2])
    def test_marginal_coverage_guarantee_synthetic(self, alpha):
        """Coverage on a fresh draw meets ~1-alpha for an exchangeable residual stream."""
        rng = np.random.default_rng(7)
        cal_resid = np.abs(rng.normal(0, 1, 1000))
        qhat = conformal_regression_quantile(cal_resid, alpha=alpha)
        # Test residuals from the same distribution.
        test_resid = np.abs(rng.normal(0, 1, 2000))
        coverage = float(np.mean(test_resid <= qhat))
        assert coverage >= (1 - alpha) - 0.04

    def test_regression_coverage_basic(self):
        y_true = np.array([10.0, 12.0, 8.0])
        y_pred = np.array([10.0, 10.0, 10.0])  # residuals 0, 2, 2
        assert regression_coverage(y_true, y_pred, qhat=2.0) == pytest.approx(1.0)
        assert regression_coverage(y_true, y_pred, qhat=1.0) == pytest.approx(1 / 3)


@pytest.mark.skipif(load_real_dataset() is None, reason="sklearn diabetes unavailable")
class TestRealDataCoverage:
    def test_coverage_meets_nominal_on_real_data(self):
        from sklearn.ensemble import GradientBoostingRegressor

        X, y = load_real_dataset()
        rng = np.random.default_rng(53)
        idx = rng.permutation(len(y))
        n_tr, n_cal = int(0.5 * len(y)), int(0.25 * len(y))
        tr, cal, te = idx[:n_tr], idx[n_tr : n_tr + n_cal], idx[n_tr + n_cal :]
        model = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=53)
        model.fit(X[tr], y[tr])
        abs_resid = np.abs(y[cal] - model.predict(X[cal]))
        result = compute_coverage(y[te], model.predict(X[te]), abs_resid, alpha=0.1)
        assert result["empirical_coverage"] >= 0.90 - COVERAGE_TOLERANCE
        assert result["passed"] is True
