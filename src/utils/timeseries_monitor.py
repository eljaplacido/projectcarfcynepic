"""Time-series monitors for operational signals (R1/G6).

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Two complementary, dependency-graceful monitors recommended by the deep-research
brief:

1. **ARIMA forecast intervals** over a metric time series (e.g. the per-window
   KL-divergence of the routing distribution). A genuine distribution shift is one
   that exceeds what the autocorrelation/seasonal structure predicts — so an
   observation *within* the forecast interval is "expected variation" and need not
   raise a drift alert. This reduces false-positive drift alerts caused by temporal
   patterns (e.g. Monday-heavy "Clear" traffic).

2. **Conditional volatility regimes** over a metric series (e.g. API latency). A
   rising volatility regime flags instability before a mean SLA breach. Uses a
   GARCH(1,1) conditional variance when the optional ``arch`` package is installed,
   otherwise a robust EWMA/rolling-std fallback.

Both functions return ``None`` (rather than raising) when the series is too short or
the modelling backend is unavailable, so callers degrade gracefully and — for safety
— never *suppress* an alert on the basis of a model that could not be fitted.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.timeseries_monitor")

# Minimum series length before a model is even attempted.
_MIN_ARIMA_POINTS = 8
_MIN_VOL_POINTS = 8


class ForecastResult(BaseModel):
    """One-step-ahead forecast with a prediction interval."""

    point: float = Field(..., description="Forecast mean for the next step")
    lower: float = Field(..., description="Lower prediction bound at level 1-alpha")
    upper: float = Field(..., description="Upper prediction bound at level 1-alpha")
    alpha: float = Field(..., ge=0.0, le=1.0, description="Miscoverage level")
    model: str = Field(..., description="Backend used: 'arima' or 'sarimax'")


class VolatilityRegime(BaseModel):
    """Conditional-volatility regime classification for a metric series."""

    recent_volatility: float = Field(..., ge=0.0)
    baseline_volatility: float = Field(..., ge=0.0)
    ratio: float = Field(..., ge=0.0, description="recent / baseline volatility")
    regime: str = Field(..., description="'stable' | 'elevated' | 'breach'")
    backend: str = Field(..., description="'garch' or 'ewma'")


def forecast_interval(
    series: list[float],
    alpha: float = 0.05,
    seasonal_period: int | None = None,
) -> ForecastResult | None:
    """Fit ARIMA/SARIMAX on ``series`` and forecast the next value + interval.

    Returns ``None`` when statsmodels is unavailable, the series is too short, or the
    fit fails — callers should treat ``None`` as "no model, do not suppress".
    """
    if len(series) < _MIN_ARIMA_POINTS:
        return None
    try:
        import numpy as np
    except Exception:  # pragma: no cover - numpy is a core dep
        return None

    data = np.asarray(series, dtype=float)
    if not np.all(np.isfinite(data)):
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            if seasonal_period and len(series) >= 2 * seasonal_period:
                from statsmodels.tsa.statespace.sarimax import SARIMAX

                model_name = "sarimax"
                fitted = SARIMAX(
                    data,
                    order=(1, 0, 0),
                    seasonal_order=(1, 0, 0, seasonal_period),
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
            else:
                from statsmodels.tsa.arima.model import ARIMA

                model_name = "arima"
                try:
                    fitted = ARIMA(data, order=(1, 1, 1)).fit()
                except Exception:
                    fitted = ARIMA(data, order=(1, 0, 0)).fit()

            forecast = fitted.get_forecast(steps=1)
            mean = float(forecast.predicted_mean[0])
            ci = forecast.conf_int(alpha=alpha)
            lower = float(ci[0][0])
            upper = float(ci[0][1])
        except Exception as exc:  # pragma: no cover - modelling-defensive
            logger.debug("ARIMA forecast failed: %s", exc)
            return None

    if upper < lower:
        lower, upper = upper, lower
    return ForecastResult(point=mean, lower=lower, upper=upper, alpha=alpha, model=model_name)


def exceeds_forecast(
    history: list[float],
    observed: float,
    alpha: float = 0.05,
    seasonal_period: int | None = None,
) -> bool:
    """True iff ``observed`` is anomalously high vs the ARIMA upper bound.

    Fail-safe: returns True (i.e. "treat as anomalous / do not suppress") whenever no
    model can be fitted, so a missing/short series never silences a real alert.
    """
    forecast = forecast_interval(history, alpha=alpha, seasonal_period=seasonal_period)
    if forecast is None:
        return True
    return observed > forecast.upper


def _window_volatility(data: Any) -> float:
    """Std-dev of first-differences over a window (robust numpy fallback for GARCH).

    Differencing removes slow trends so the estimate reflects short-term volatility;
    plain std (rather than an EWMA recursion) is a far more stable estimator on the
    short windows these monitors operate on.
    """
    import numpy as np

    diffs = np.diff(data)
    if diffs.size == 0:
        return 0.0
    return float(np.std(diffs))


def volatility_regime(
    series: list[float],
    breach_ratio: float = 1.5,
    elevated_ratio: float = 1.2,
    baseline_fraction: float = 0.5,
) -> VolatilityRegime | None:
    """Classify the current volatility regime of a metric series.

    Compares recent conditional volatility to a baseline volatility from the earlier
    part of the series. Uses GARCH(1,1) when ``arch`` is installed, else an EWMA
    fallback. Returns ``None`` when the series is too short.
    """
    if len(series) < _MIN_VOL_POINTS:
        return None
    try:
        import numpy as np
    except Exception:  # pragma: no cover
        return None

    data = np.asarray(series, dtype=float)
    if not np.all(np.isfinite(data)):
        return None

    split = max(2, int(len(data) * baseline_fraction))
    baseline_part = data[:split]
    recent_part = data[split:]
    if recent_part.size < 2 or baseline_part.size < 2:
        return None

    backend = "rolling_std"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from arch import arch_model

            scaled = np.diff(data) * 100.0  # arch prefers ~unit-scale returns
            if scaled.size >= _MIN_VOL_POINTS:
                res = arch_model(scaled, vol="GARCH", p=1, q=1, mean="Zero").fit(disp="off")
                cond_vol = np.asarray(res.conditional_volatility)
                csplit = max(2, int(cond_vol.size * baseline_fraction))
                baseline_vol = float(np.mean(cond_vol[:csplit]))
                recent_vol = float(np.mean(cond_vol[csplit:]))
                backend = "garch"
            else:
                raise RuntimeError("series too short for GARCH")
    except Exception:
        backend = "rolling_std"
        baseline_vol = _window_volatility(baseline_part)
        recent_vol = _window_volatility(recent_part)

    ratio = recent_vol / baseline_vol if baseline_vol > 1e-12 else (float("inf") if recent_vol > 0 else 1.0)
    if ratio >= breach_ratio:
        regime = "breach"
    elif ratio >= elevated_ratio:
        regime = "elevated"
    else:
        regime = "stable"

    return VolatilityRegime(
        recent_volatility=recent_vol,
        baseline_volatility=baseline_vol,
        ratio=float(ratio) if ratio != float("inf") else 1e9,
        regime=regime,
        backend=backend,
    )
