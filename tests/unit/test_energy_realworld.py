# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the ENTSO-E energy benchmark harness (R2 / H54).

The live fetch needs a token, but all pure logic (features, naive baseline, conformal
coverage, metrics, skip path) is validated offline so the harness is verified before a
key is available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from benchmarks.technical.realworld.benchmark_energy import (
    MAE_IMPROVEMENT_MIN,
    build_features,
    compute_metrics,
    load_entsoe_prices,
    naive_seasonal_forecast,
    run_benchmark,
)


def _synthetic_prices(n: int = 500) -> pd.Series:
    rng = np.random.default_rng(0)
    hours = np.arange(n)
    # Daily + weekly seasonality + noise (resembles a price curve).
    series = (
        50
        + 15 * np.sin(2 * np.pi * hours / 24)
        + 5 * np.sin(2 * np.pi * hours / 168)
        + rng.normal(0, 3, n)
    )
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    return pd.Series(series, index=idx)


class TestPureLogic:
    def test_build_features_shapes_and_lags(self):
        prices = _synthetic_prices(300)
        X, y = build_features(prices)
        # 168-hour max lag dropped from the front.
        assert len(y) == 300 - 168
        assert X.shape[0] == len(y)
        assert X.shape[1] == 4  # lag1, lag24, lag168, hour

    def test_naive_seasonal_alignment(self):
        prices = _synthetic_prices(300)
        yt, yp = naive_seasonal_forecast(prices)
        assert len(yt) == len(yp) == 300 - 168
        # Naive prediction is the value 24h before each target.
        arr = prices.to_numpy()
        assert yp[0] == pytest.approx(arr[168 - 24])

    def test_compute_metrics_pass(self):
        coverage = [
            {"alpha": 0.1, "passed": True},
            {"alpha": 0.2, "passed": True},
        ]
        m = compute_metrics(mae_model=8.0, mae_naive=10.0, coverage_per_alpha=coverage)
        assert m["mae_improvement"] == pytest.approx(0.2)
        assert m["mae_improvement"] >= MAE_IMPROVEMENT_MIN
        assert m["passed"] is True

    def test_compute_metrics_fails_without_coverage(self):
        coverage = [{"alpha": 0.1, "passed": False}]
        m = compute_metrics(mae_model=8.0, mae_naive=10.0, coverage_per_alpha=coverage)
        assert m["passed"] is False

    def test_compute_metrics_fails_without_mae_gain(self):
        coverage = [{"alpha": 0.1, "passed": True}]
        m = compute_metrics(mae_model=9.9, mae_naive=10.0, coverage_per_alpha=coverage)
        assert m["mae_improvement"] < MAE_IMPROVEMENT_MIN
        assert m["passed"] is False


class TestSkipPath:
    def test_load_returns_none_without_token_or_cache(self, monkeypatch):
        monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
        # Use a zone unlikely to have a local cache file.
        assert load_entsoe_prices(zone="__NO_SUCH_ZONE__") is None

    def test_run_benchmark_skips_honestly(self, monkeypatch):
        monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
        report = run_benchmark(zone="__NO_SUCH_ZONE__")
        assert report["status"] == "skipped"
        assert report["evidence_grade"] == "aspirational"
        assert report["passed"] is False
        # No fabricated metrics on the skip path.
        assert "mae_model" not in report
