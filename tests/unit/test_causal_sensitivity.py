# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the quantified causal sensitivity scorer."""

from __future__ import annotations

import math

import pytest

from src.services.causal_sensitivity import (
    DEFAULT_MIN_E_VALUE,
    assess_robustness,
    compute_e_value,
    e_value_from_rr,
    summarize_refutations,
)


class TestEValueFromRR:
    def test_rr_one_yields_unity(self):
        assert e_value_from_rr(1.0) == 1.0

    def test_known_vanderweele_ding_values(self):
        # VanderWeele & Ding (2017) Table 1 reference points.
        # RR=2 → E ≈ 3.414; RR=3.9 → E ≈ 7.26
        assert math.isclose(e_value_from_rr(2.0), 2 + math.sqrt(2 * 1), rel_tol=1e-6)
        assert math.isclose(e_value_from_rr(2.0), 3.4142135, rel_tol=1e-5)
        # Symmetry: RR=0.5 should give the same E-value as RR=2.
        assert math.isclose(
            e_value_from_rr(0.5), e_value_from_rr(2.0), rel_tol=1e-9
        )

    def test_invalid_rr_returns_nan(self):
        assert math.isnan(e_value_from_rr(-1.0))
        assert math.isnan(e_value_from_rr(0.0))
        assert math.isnan(e_value_from_rr(float("inf")))


class TestComputeEValueContinuous:
    def test_zero_effect_collapses_to_unity(self):
        e_point, e_ci = compute_e_value(
            0.0, confidence_interval=(-0.1, 0.1), outcome_sd=1.0
        )
        assert e_point == 1.0
        # CI crosses null → CI E-value snaps to 1.0
        assert e_ci == 1.0

    def test_strong_standardised_effect_yields_high_e_value(self):
        # d=1.0 (one SD effect) → RR ≈ exp(0.91) ≈ 2.484
        # E ≈ 2.484 + sqrt(2.484*1.484) ≈ 4.41
        e_point, _ = compute_e_value(1.0, outcome_sd=1.0)
        assert e_point is not None
        assert e_point > 4.0

    def test_ci_e_value_uses_bound_nearest_null(self):
        # Wide CI [0.05, 0.95] in standardised units (sd=1) — the bound
        # nearest null is 0.05 → very small RR → CI E-value barely above 1.
        e_point, e_ci = compute_e_value(
            0.5, confidence_interval=(0.05, 0.95), outcome_sd=1.0
        )
        assert e_point is not None and e_ci is not None
        assert e_ci < e_point
        assert e_ci >= 1.0

    def test_non_finite_effect_yields_none(self):
        e_point, e_ci = compute_e_value(float("nan"))
        assert e_point is None and e_ci is None


class TestSummarizeRefutations:
    def test_skipped(self):
        assert summarize_refutations(None) == (0, 0, "skipped")
        assert summarize_refutations({}) == (0, 0, "skipped")

    def test_passed(self):
        assert summarize_refutations({"a": True, "b": True}) == (2, 2, "passed")

    def test_partial(self):
        assert summarize_refutations({"a": True, "b": False}) == (1, 2, "partial")

    def test_failed(self):
        assert summarize_refutations({"a": False, "b": False}) == (0, 2, "failed")


class TestAssessRobustness:
    def test_strong_evidence_is_robust(self):
        report = assess_robustness(
            effect=1.0,
            confidence_interval=(0.6, 1.4),
            refutation_results={
                "placebo_treatment_refuter": True,
                "random_common_cause": True,
                "data_subset_refuter": True,
            },
            outcome_sd=1.0,
        )
        assert report.robust is True
        assert report.refutation_status == "passed"
        assert report.e_value is not None and report.e_value > DEFAULT_MIN_E_VALUE

    def test_weak_e_value_blocks_robustness(self):
        # Standardised effect d=0.02 → RR≈1.018, E≈1.16, well below the
        # 1.25 default threshold. Refutations all pass, so the only thing
        # blocking robustness is the weak E-value.
        report = assess_robustness(
            effect=0.02,
            confidence_interval=(0.005, 0.035),
            refutation_results={
                "placebo_treatment_refuter": True,
                "random_common_cause": True,
                "data_subset_refuter": True,
            },
            outcome_sd=1.0,
        )
        assert report.robust is False
        assert report.e_value is not None and report.e_value < DEFAULT_MIN_E_VALUE
        assert any("e-value" in r.lower() for r in report.reasons)

    def test_failed_refutations_block_robustness_even_with_strong_effect(self):
        report = assess_robustness(
            effect=1.5,
            confidence_interval=(1.2, 1.8),
            refutation_results={
                "placebo_treatment_refuter": False,
                "random_common_cause": False,
            },
            outcome_sd=1.0,
        )
        assert report.robust is False
        assert report.refutation_status == "failed"

    def test_skipped_refutations_block_robustness(self):
        report = assess_robustness(
            effect=1.0,
            confidence_interval=(0.5, 1.5),
            refutation_results=None,
            outcome_sd=1.0,
        )
        assert report.robust is False
        assert report.refutation_status == "skipped"

    def test_ci_crossing_null_blocks_robustness(self):
        report = assess_robustness(
            effect=0.6,
            confidence_interval=(-0.2, 1.4),
            refutation_results={
                "placebo_treatment_refuter": True,
                "random_common_cause": True,
                "data_subset_refuter": True,
            },
            outcome_sd=1.0,
        )
        assert report.robust is False
        assert any("crosses the null" in r for r in report.reasons)

    def test_partial_refutation_default_warns_only(self):
        report = assess_robustness(
            effect=1.0,
            confidence_interval=(0.6, 1.4),
            refutation_results={
                "placebo_treatment_refuter": True,
                "random_common_cause": False,
                "data_subset_refuter": True,
            },
            outcome_sd=1.0,
        )
        # Default require_all_refutations=False → still robust
        assert report.refutation_status == "partial"
        assert report.robust is True
        assert any("only 2/3" in r for r in report.reasons)

    def test_partial_refutation_strict_mode_blocks(self):
        report = assess_robustness(
            effect=1.0,
            confidence_interval=(0.6, 1.4),
            refutation_results={
                "placebo_treatment_refuter": True,
                "random_common_cause": False,
                "data_subset_refuter": True,
            },
            outcome_sd=1.0,
            require_all_refutations=True,
        )
        assert report.robust is False

    def test_to_dict_round_trips(self):
        report = assess_robustness(
            effect=1.0,
            confidence_interval=(0.6, 1.4),
            refutation_results={"a": True, "b": True},
            outcome_sd=1.0,
        )
        data = report.to_dict()
        assert data["e_value"] == report.e_value
        assert data["refutation_status"] == "passed"
        assert isinstance(data["reasons"], list)
