# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Unit tests for split-conformal router calibration (R1/G2)."""

import random

import pytest

from src.utils.conformal import (
    ConformalCalibration,
    average_set_size,
    empirical_coverage,
    fit_conformal,
    load_calibration,
    prediction_set,
    save_calibration,
)

DOMAINS = ["Clear", "Complicated", "Complex", "Chaotic", "Disorder"]


def _synthetic_dataset(n: int, sharpness: float, seed: int):
    """Generate (softmax-like scores, true_label) pairs.

    `sharpness` controls how confidently the score for the true label dominates;
    higher → easier separation → smaller conformal sets.
    """
    rng = random.Random(seed)
    scores_list: list[dict[str, float]] = []
    labels: list[str] = []
    for _ in range(n):
        true = rng.choice(DOMAINS)
        raw = {d: rng.random() for d in DOMAINS}
        raw[true] += sharpness  # boost the true label
        total = sum(raw.values())
        scores_list.append({d: v / total for d, v in raw.items()})
        labels.append(true)
    return scores_list, labels


class TestConformalCalibration:
    def test_fit_requires_matching_lengths(self):
        with pytest.raises(ValueError):
            fit_conformal([{"Clear": 1.0}], ["Clear", "Complex"])

    def test_fit_requires_examples(self):
        with pytest.raises(ValueError):
            fit_conformal([], [])

    @pytest.mark.parametrize("alpha", [0.05, 0.1, 0.2])
    def test_marginal_coverage_guarantee(self, alpha):
        """Empirical coverage on a fresh test split should meet ~ 1 - alpha.

        Split-conformal guarantees marginal coverage >= 1 - alpha in expectation;
        we allow a small finite-sample slack below the nominal level.
        """
        cal_scores, cal_labels = _synthetic_dataset(600, sharpness=2.0, seed=1)
        test_scores, test_labels = _synthetic_dataset(600, sharpness=2.0, seed=2)

        calibration = fit_conformal(cal_scores, cal_labels, alpha=alpha)
        coverage = empirical_coverage(test_scores, test_labels, calibration)

        assert coverage >= (1 - alpha) - 0.05
        # Sanity: sets are subsets of the label space and non-trivial.
        assert 1.0 <= average_set_size(test_scores, calibration) <= len(DOMAINS)

    def test_prediction_set_never_empty(self):
        cal_scores, cal_labels = _synthetic_dataset(200, sharpness=1.5, seed=3)
        calibration = fit_conformal(cal_scores, cal_labels, alpha=0.1)
        pset = prediction_set(dict.fromkeys(DOMAINS, 0.2), calibration)
        assert len(pset) >= 1

    def test_sharper_scores_give_smaller_sets(self):
        sharp_scores, sharp_labels = _synthetic_dataset(400, sharpness=4.0, seed=4)
        fuzzy_scores, fuzzy_labels = _synthetic_dataset(400, sharpness=0.3, seed=5)

        sharp_cal = fit_conformal(sharp_scores, sharp_labels, alpha=0.1)
        fuzzy_cal = fit_conformal(fuzzy_scores, fuzzy_labels, alpha=0.1)

        assert average_set_size(sharp_scores, sharp_cal) < average_set_size(
            fuzzy_scores, fuzzy_cal
        )

    def test_tiny_calibration_set_is_conservative(self):
        """Too few points for the requested alpha → qhat = inf → full coverage set."""
        calibration = fit_conformal([{"Clear": 0.9, "Complex": 0.1}], ["Clear"], alpha=0.05)
        assert calibration.qhat == float("inf")
        pset = prediction_set({d: 1.0 / len(DOMAINS) for d in DOMAINS}, calibration)
        assert set(pset) == set(calibration.labels)

    def test_save_and_load_roundtrip(self, tmp_path):
        cal_scores, cal_labels = _synthetic_dataset(100, sharpness=2.0, seed=6)
        calibration = fit_conformal(cal_scores, cal_labels, alpha=0.1)
        path = tmp_path / "router_conformal.json"
        save_calibration(calibration, path)

        loaded = load_calibration(path)
        assert isinstance(loaded, ConformalCalibration)
        assert loaded.qhat == pytest.approx(calibration.qhat)
        assert loaded.labels == calibration.labels

    def test_load_missing_returns_none(self, tmp_path):
        assert load_calibration(tmp_path / "does_not_exist.json") is None


class TestRouterConformalIntegration:
    @pytest.mark.asyncio
    async def test_router_records_prediction_set_when_calibrated(self, tmp_path):
        """When a calibration artifact is present, classify() attaches a prediction set."""
        import os

        from src.core.state import EpistemicState
        from src.workflows.router import CynefinRouter

        cal_scores, cal_labels = _synthetic_dataset(300, sharpness=2.0, seed=7)
        calibration = fit_conformal(cal_scores, cal_labels, alpha=0.1)
        path = tmp_path / "router_conformal.json"
        save_calibration(calibration, path)

        os.environ["CARF_CONFORMAL_PATH"] = str(path)
        try:
            router = CynefinRouter()
            assert router._conformal is not None
            state = EpistemicState(user_input="What is the current stock price for AAPL?")
            result = await router.classify(state)
            assert "router_prediction_set" in result.context
            assert isinstance(result.context["router_prediction_set"], list)
            assert "router_ambiguous" in result.context
        finally:
            os.environ.pop("CARF_CONFORMAL_PATH", None)

    @pytest.mark.asyncio
    async def test_router_no_calibration_is_noop(self):
        """No artifact → no prediction-set metadata, classification unchanged."""
        import os

        from src.core.state import CynefinDomain, EpistemicState
        from src.workflows.router import CynefinRouter

        os.environ["CARF_CONFORMAL_PATH"] = "models/__definitely_missing__.json"
        try:
            router = CynefinRouter()
            assert router._conformal is None
            state = EpistemicState(user_input="What is the current stock price for AAPL?")
            result = await router.classify(state)
            assert "router_prediction_set" not in result.context
            assert result.cynefin_domain == CynefinDomain.CLEAR
        finally:
            os.environ.pop("CARF_CONFORMAL_PATH", None)
