# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the IHDP real-covariate CATE benchmark (R2 / H52)."""

from __future__ import annotations

import pytest

from benchmarks.technical.realworld.benchmark_ihdp import (
    ATE_REL_ERROR_MAX,
    COVARIATES,
    PEHE_IMPROVEMENT_MIN,
    causal_forest_cate,
    compute_metrics,
    load_ihdp,
    pehe,
)


class TestComputeMetrics:
    """Pure metric logic — no DoWhy/EconML required."""

    def test_passes_on_good_recovery_and_heterogeneity(self):
        m = compute_metrics(true_ate=4.016, carf_ate_value=3.93, pehe_cf=0.66, pehe_const=0.86)
        assert m["ate_rel_error"] < ATE_REL_ERROR_MAX
        assert m["pehe_improvement"] > PEHE_IMPROVEMENT_MIN
        assert m["passed"] is True

    def test_fails_on_poor_ate(self):
        m = compute_metrics(true_ate=4.016, carf_ate_value=1.0, pehe_cf=0.66, pehe_const=0.86)
        assert m["passed"] is False

    def test_fails_when_no_heterogeneity_captured(self):
        # CForest no better than constant baseline.
        m = compute_metrics(true_ate=4.016, carf_ate_value=3.9, pehe_cf=0.85, pehe_const=0.86)
        assert m["pehe_improvement"] < PEHE_IMPROVEMENT_MIN
        assert m["passed"] is False

    def test_ate_only_without_pehe(self):
        m = compute_metrics(4.016, 3.9, None, None)
        assert "pehe_improvement" not in m
        assert m["passed"] is True


def test_pehe_is_rmse_of_ite():
    assert pehe([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0
    assert pehe([0.0, 0.0], [1.0, 1.0]) == pytest.approx(1.0)


@pytest.mark.skipif(load_ihdp() is None, reason="IHDP dataset unavailable (no cache / no network)")
class TestRealIHDPData:
    """Validates against the actual NPCI realization."""

    def test_true_ate_matches_known_value(self):
        import numpy as np

        df, true_ite = load_ihdp()
        assert len(df) == 747
        assert float(np.mean(true_ite)) == pytest.approx(4.016, abs=0.05)

    def test_covariates_present(self):
        df, _ = load_ihdp()
        for col in COVARIATES + ["treat", "y"]:
            assert col in df.columns

    def test_causal_forest_beats_constant_on_pehe(self):
        """CARF's CATE estimator captures real heterogeneity better than a constant effect."""
        import numpy as np

        df, true_ite = load_ihdp()
        cf = causal_forest_cate(df, true_ite)
        assert cf is not None
        pehe_const = pehe(np.full_like(true_ite, float(np.mean(true_ite))), true_ite)
        improvement = (pehe_const - cf["pehe"]) / pehe_const
        assert improvement >= PEHE_IMPROVEMENT_MIN
