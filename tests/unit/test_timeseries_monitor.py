# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Unit tests for time-series monitors and drift seasonal suppression (R1/G6)."""

import math
import random

from src.services.drift_detector import DriftDetector
from src.utils.timeseries_monitor import (
    ForecastResult,
    VolatilityRegime,
    exceeds_forecast,
    forecast_interval,
    volatility_regime,
)


class TestForecastInterval:
    def test_short_series_returns_none(self):
        assert forecast_interval([1.0, 2.0, 3.0]) is None

    def test_forecast_returns_ordered_interval(self):
        # Noisy stationary series around 0.2.
        rng = random.Random(11)
        series = [0.2 + 0.01 * rng.gauss(0, 1) for _ in range(40)]
        fc = forecast_interval(series, alpha=0.05)
        assert isinstance(fc, ForecastResult)
        assert fc.lower <= fc.point <= fc.upper
        # Forecast should sit near the series mean for a stationary process.
        assert abs(fc.point - 0.2) < 0.1

    def test_seasonal_model_used_when_period_given(self):
        # Weekly-seasonal series: 28 points, period 7.
        series = [1.0, 2.0, 5.0, 3.0, 2.0, 1.0, 0.5] * 4
        fc = forecast_interval(series, alpha=0.1, seasonal_period=7)
        assert fc is not None
        assert fc.model == "sarimax"


class TestExceedsForecast:
    def test_short_history_is_failsafe_true(self):
        # No model can be fitted -> treat as anomalous (do not suppress).
        assert exceeds_forecast([0.1, 0.1, 0.1], observed=0.1) is True

    def test_value_within_pattern_not_flagged(self):
        rng = random.Random(7)
        history = [0.2 + 0.01 * rng.gauss(0, 1) for _ in range(40)]
        assert exceeds_forecast(history, observed=0.205, alpha=0.05) is False

    def test_large_spike_is_flagged(self):
        rng = random.Random(7)
        history = [0.2 + 0.01 * rng.gauss(0, 1) for _ in range(40)]
        assert exceeds_forecast(history, observed=0.95, alpha=0.05) is True


class TestVolatilityRegime:
    def test_short_series_returns_none(self):
        assert volatility_regime([1.0, 2.0, 3.0]) is None

    def test_stable_series_is_stable(self):
        rng = random.Random(3)
        series = [10.0 + 0.1 * rng.gauss(0, 1) for _ in range(120)]
        regime = volatility_regime(series)
        assert isinstance(regime, VolatilityRegime)
        assert regime.regime == "stable"
        assert regime.ratio < 1.2

    def test_rising_volatility_flagged(self):
        rng = random.Random(5)
        calm = [10.0 + 0.05 * rng.gauss(0, 1) for _ in range(30)]
        turbulent = [10.0 + 3.0 * rng.gauss(0, 1) for _ in range(30)]
        regime = volatility_regime(calm + turbulent, breach_ratio=1.5, elevated_ratio=1.2)
        assert regime is not None
        assert regime.regime in {"elevated", "breach"}
        assert regime.ratio > 1.2
        # arch is not installed in this environment -> rolling-std fallback.
        assert regime.backend == "rolling_std"


class TestDriftSeasonalSuppression:
    def test_seasonal_check_disabled_by_default(self):
        detector = DriftDetector()
        assert detector._seasonal_suppression is False
        # Even with a populated series, suppression is inert when disabled.
        detector._kl_series.extend([0.2] * 12)
        expected, upper = detector._seasonal_check(0.25)
        assert expected is False
        assert upper is None

    def test_seasonal_check_suppresses_in_pattern_value(self):
        detector = DriftDetector(seasonal_suppression=True, seasonal_alpha=0.05)
        rng = random.Random(13)
        detector._kl_series.extend([0.2 + 0.01 * rng.gauss(0, 1) for _ in range(40)])
        # A value consistent with the ~0.2 pattern is "expected".
        expected, upper = detector._seasonal_check(0.205)
        assert expected is True
        assert upper is not None and upper > 0.2

    def test_seasonal_check_does_not_suppress_real_spike(self):
        detector = DriftDetector(seasonal_suppression=True, seasonal_alpha=0.05)
        rng = random.Random(13)
        detector._kl_series.extend([0.2 + 0.01 * rng.gauss(0, 1) for _ in range(40)])
        expected, _ = detector._seasonal_check(0.95)
        assert expected is False

    def test_short_series_is_failsafe(self):
        detector = DriftDetector(seasonal_suppression=True)
        detector._kl_series.extend([0.2, 0.2, 0.2])  # below min_series_for_suppression
        expected, upper = detector._seasonal_check(0.9)
        assert expected is False
        assert upper is None

    def test_default_detector_still_flags_genuine_drift(self):
        """Regression guard: with suppression off, a clear shift still alerts."""
        detector = DriftDetector(
            baseline_window=20, detection_window=10, kl_threshold=0.05
        )
        # Baseline: all 'clear'.
        for _ in range(20):
            detector.record_routing("clear")
        # Then a sharp shift to 'chaotic'.
        snapshot = None
        for _ in range(10):
            snapshot = detector.record_routing("chaotic") or snapshot
        assert snapshot is not None
        assert snapshot.drift_detected is True
        assert not math.isnan(snapshot.kl_divergence)
