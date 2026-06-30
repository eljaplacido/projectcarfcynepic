# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H54 — Real European electricity day-ahead forecasting + conformal coverage (R2).

Directly aligned with the LUT-dissertation electricity-market context: forecast
day-ahead prices for a European bidding zone and wrap the forecaster with CARF's
split-conformal layer, validating both point accuracy (vs a naive seasonal baseline)
and distribution-free interval coverage on **real** realized prices (empirical ground
truth).

Data comes from the ENTSO-E Transparency Platform via ``entsoe-py``. A free API token
is required (``ENTSOE_API_TOKEN``); until it is provided the benchmark records
``status: skipped`` / ``evidence_grade: aspirational`` with **no fabricated metrics**.
Everything except the live fetch (feature build, conformal coverage, metrics) is pure
and unit-tested, so the harness is ready the moment a token is available.

Run (once a token is set):
    export ENTSOE_API_TOKEN=...            # free registration at transparency.entsoe.eu
    pip install "carf[realworld]"
    python -m benchmarks.technical.realworld.benchmark_energy
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("benchmark.energy")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

DEFAULT_ZONE = os.environ.get("ENTSOE_ZONE", "FI")  # Finland bidding zone (LUT context)
ALPHAS = [0.10, 0.20]
COVERAGE_TOLERANCE = 0.07  # real prices are heavy-tailed; allow slightly more slack
MAE_IMPROVEMENT_MIN = 0.05  # forecaster must beat the naive seasonal baseline by >=5%
_CACHE_DIR = _PROJECT_ROOT / "var" / "benchmark_data" / "energy"


def load_entsoe_prices(zone: str = DEFAULT_ZONE, days: int = 60) -> Any | None:
    """Load recent day-ahead prices for a zone as a pandas Series, or None.

    Reads a local cache first; otherwise requires ``entsoe-py`` + ``ENTSOE_API_TOKEN``.
    Returns ``None`` (honest skip) when neither cache nor a usable client/token exists.
    """
    try:
        import pandas as pd
    except Exception:  # pragma: no cover
        return None

    cache_path = _CACHE_DIR / f"day_ahead_prices_{zone}.csv"
    if cache_path.exists():
        s = pd.read_csv(cache_path, index_col=0, parse_dates=True).iloc[:, 0]
        return s

    token = os.environ.get("ENTSOE_API_TOKEN")
    if not token:
        logger.warning("ENTSOE_API_TOKEN not set; skipping live ENTSO-E fetch")
        return None
    try:
        from entsoe import EntsoePandasClient

        client = EntsoePandasClient(api_key=token)
        end = pd.Timestamp.now(tz="Europe/Brussels").normalize()
        start = end - pd.Timedelta(days=days)
        prices = client.query_day_ahead_prices(zone, start=start, end=end)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(cache_path)
        logger.info("Cached %d ENTSO-E price points for %s", len(prices), zone)
        return prices
    except Exception as exc:  # pragma: no cover - network/credential-defensive
        logger.warning("ENTSO-E fetch failed: %s", exc)
        return None


def build_features(prices: Any) -> tuple[Any, Any]:
    """Build a simple autoregressive feature matrix from an hourly price series."""
    import numpy as np
    import pandas as pd

    df = pd.DataFrame({"price": prices.astype(float).to_numpy()})
    for lag in (1, 24, 168):  # previous hour, previous day, previous week
        df[f"lag{lag}"] = df["price"].shift(lag)
    df["hour"] = np.arange(len(df)) % 24
    df = df.dropna().reset_index(drop=True)
    y = df["price"].to_numpy()
    X = df[[c for c in df.columns if c != "price"]].to_numpy()
    return X, y


def naive_seasonal_forecast(prices: Any) -> tuple[Any, Any]:
    """Naive baseline: predict price = price 24h earlier. Returns (y_true, y_pred)."""
    import numpy as np

    arr = np.asarray(prices, dtype=float)
    return arr[168:], arr[168 - 24 : -24]


def compute_metrics(
    mae_model: float,
    mae_naive: float,
    coverage_per_alpha: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pure metric computation (testable without ENTSO-E)."""
    import math

    mae_improvement = (mae_naive - mae_model) / mae_naive if mae_naive > 0 else 0.0
    coverage_ok = all(c["passed"] for c in coverage_per_alpha)
    metrics: dict[str, Any] = {
        "mae_model": round(mae_model, 4),
        "mae_naive": round(mae_naive, 4),
        "mae_improvement": round(mae_improvement, 4) if math.isfinite(mae_improvement) else None,
        "coverage_per_alpha": coverage_per_alpha,
    }
    metrics["passed"] = bool(mae_improvement >= MAE_IMPROVEMENT_MIN and coverage_ok)
    return metrics


def _coverage_rows(y_true: Any, y_pred: Any, abs_resid_cal: Any) -> list[dict[str, Any]]:
    from src.utils.conformal import conformal_regression_quantile, regression_coverage

    rows = []
    for alpha in ALPHAS:
        qhat = conformal_regression_quantile(abs_resid_cal, alpha=alpha)
        cov = regression_coverage(y_true, y_pred, qhat)
        nominal = 1.0 - alpha
        rows.append({
            "alpha": alpha,
            "nominal_coverage": round(nominal, 4),
            "empirical_coverage": round(cov, 4),
            "interval_half_width": round(qhat, 4),
            "passed": cov >= nominal - COVERAGE_TOLERANCE,
        })
    return rows


def run_benchmark(zone: str = DEFAULT_ZONE) -> dict[str, Any]:
    from benchmarks import finalize_benchmark_report

    prices = load_entsoe_prices(zone)
    if prices is None or len(prices) < 400:
        report = {
            "hypothesis": "H54",
            "claim": "On real ENTSO-E day-ahead prices, CARF's forecaster beats a naive "
            "seasonal baseline and its conformal intervals achieve nominal coverage",
            "status": "skipped",
            "passed": False,
            "evidence_grade": "aspirational",
            "reason": "ENTSO-E data unavailable (set ENTSOE_API_TOKEN and install carf[realworld])",
            "data_source": "ENTSO-E Transparency Platform via entsoe-py (query_day_ahead_prices)",
            "zone": zone,
        }
        return finalize_benchmark_report(report, benchmark_id="energy_realworld")

    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor

    X, y = build_features(prices)
    n = len(y)
    n_tr, n_cal = int(0.6 * n), int(0.2 * n)
    Xtr, ytr = X[:n_tr], y[:n_tr]
    Xcal, ycal = X[n_tr : n_tr + n_cal], y[n_tr : n_tr + n_cal]
    Xte, yte = X[n_tr + n_cal :], y[n_tr + n_cal :]

    model = GradientBoostingRegressor(n_estimators=300, max_depth=4, random_state=54)
    model.fit(Xtr, ytr)
    abs_resid_cal = np.abs(ycal - model.predict(Xcal))
    yhat_te = model.predict(Xte)
    mae_model = float(np.mean(np.abs(yte - yhat_te)))

    yt_naive, yp_naive = naive_seasonal_forecast(prices)
    mae_naive = float(np.mean(np.abs(yt_naive - yp_naive)))

    coverage = _coverage_rows(yte, yhat_te, abs_resid_cal)
    metrics = compute_metrics(mae_model, mae_naive, coverage)

    report = {
        "hypothesis": "H54",
        "claim": "On real ENTSO-E day-ahead prices, CARF's forecaster beats a naive "
        f"seasonal baseline by >={MAE_IMPROVEMENT_MIN:.0%} and its conformal intervals "
        "achieve nominal coverage",
        "metric": "mae_improvement + conformal_coverage",
        "zone": zone,
        **metrics,
        "dataset_profile": "real",
        "ground_truth_type": "empirical",
        "data_source": "ENTSO-E Transparency Platform (day-ahead prices)",
        "n_test": int(len(yte)),
        "samples": int(len(yte)),
        "evidence_grade": "validated",
    }
    return finalize_benchmark_report(
        report,
        benchmark_id="energy_realworld",
        source_reference="ENTSO-E Transparency Platform day-ahead prices; conformal forecasting",
        dataset_context={"dataset_profile": "real", "ground_truth_type": "empirical", "zone": zone},
        sample_context={"n_test": int(len(yte))},
    )


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    report = run_benchmark()
    out_path = Path(__file__).with_name("benchmark_energy_results.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report.get("status") == "skipped":
        print(f"[H54] ENTSO-E energy benchmark SKIPPED — {report['reason']}")
    else:
        status = "PASS" if report["passed"] else "FAIL"
        print(f"[H54] ENTSO-E day-ahead forecasting ({report['zone']}): {status}")
        print(f"  MAE model {report['mae_model']:.2f} vs naive {report['mae_naive']:.2f}"
              f"  ({report['mae_improvement']:.1%} better)")
        for c in report["coverage_per_alpha"]:
            print(f"  alpha={c['alpha']:.2f} nominal={c['nominal_coverage']:.2f}"
                  f" empirical={c['empirical_coverage']:.2f} {'ok' if c['passed'] else 'MISS'}")
    print(f"  results -> {out_path}")


if __name__ == "__main__":
    main()
