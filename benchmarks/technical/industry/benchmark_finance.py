"""Benchmark CARF Finance / VaR Backtesting (H36).

Validates Value at Risk (VaR) model correctness using synthetic portfolio
returns with known distributional properties.  Generates 1000 days of
returns from a mixture-of-normals distribution (fat tails), computes 99%
VaR via historical simulation, backtests exception counts, and applies
the Kupiec POF (Proportion of Failures) likelihood-ratio test.

Metrics:
  - kupiec_pvalue:  p-value from Kupiec LR test (chi-squared(1))
  - var_99:         computed 99% VaR threshold
  - exception_rate: observed proportion of VaR breaches
  - pass:           kupiec_pvalue > 0.05 (model not rejected)

Usage:
    python benchmarks/technical/industry/benchmark_finance.py
    python benchmarks/technical/industry/benchmark_finance.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.finance")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Synthetic Return Generator ───────────────────────────────────────────


def generate_synthetic_returns(
    n_days: int = 1000,
    seed: int = 42,
) -> list[float]:
    """Generate synthetic daily portfolio returns from a mixture of normals.

    The mixture produces realistic fat tails:
      - 95% of the time: N(mu=0.0005, sigma=0.02)   — normal market
      - 5%  of the time: N(mu=-0.01,  sigma=0.05)    — stress event

    Returns a list of *n_days* float values.
    """
    import numpy as np

    rng = np.random.default_rng(seed)

    # Component selection: 0 = normal market, 1 = stress
    component = rng.binomial(1, 0.05, size=n_days)

    normal_returns = rng.normal(0.0005, 0.02, size=n_days)
    stress_returns = rng.normal(-0.01, 0.05, size=n_days)

    returns = [
        float(stress_returns[i]) if component[i] else float(normal_returns[i])
        for i in range(n_days)
    ]
    return returns


# ── VaR Computation ──────────────────────────────────────────────────────


def compute_historical_var(returns: list[float], confidence: float = 0.99) -> float:
    """Compute VaR at the given confidence level using historical simulation.

    VaR is the (1 - confidence) quantile of the loss distribution.
    Since returns are profit/loss, VaR = -quantile(returns, 1 - confidence).
    """
    import numpy as np

    arr = np.array(returns)
    quantile = np.percentile(arr, (1.0 - confidence) * 100.0)
    return float(-quantile)  # Positive number representing potential loss


# ── Kupiec POF Test ──────────────────────────────────────────────────────


def kupiec_pof_test(
    T: int,
    N: int,
    p: float,
) -> tuple[float, float]:
    """Kupiec Proportion of Failures (POF) likelihood-ratio test.

    Parameters
    ----------
    T : int
        Total number of backtesting days.
    N : int
        Number of VaR exceptions (days where loss > VaR).
    p : float
        Expected exception probability (1 - confidence level).

    Returns
    -------
    lr_stat : float
        Likelihood-ratio test statistic.
    pvalue : float
        p-value from chi-squared(1) distribution.

    Formula
    -------
    LR = -2 * ln((1-p)^(T-N) * p^N) + 2 * ln((1-N/T)^(T-N) * (N/T)^N)

    Under H0, LR ~ chi-squared(1).
    """
    # Edge cases
    if N == 0:
        # No exceptions: log(p^0) = 0, and (N/T)^N = 0^0 = 1
        log_restricted = (T - N) * math.log(1 - p)
        # Unrestricted: (1 - 0/T)^T * (0/T)^0 = 1^T * 1 = 1 => log = 0
        log_unrestricted = 0.0
        lr_stat = -2.0 * log_restricted + 2.0 * log_unrestricted
    elif N == T:
        # All days are exceptions
        log_restricted = N * math.log(p)
        log_unrestricted = 0.0  # (N/T)^N = 1^N = 1
        lr_stat = -2.0 * log_restricted + 2.0 * log_unrestricted
    else:
        n_hat = N / T
        log_restricted = (T - N) * math.log(1 - p) + N * math.log(p)
        log_unrestricted = (T - N) * math.log(1 - n_hat) + N * math.log(n_hat)
        lr_stat = -2.0 * log_restricted + 2.0 * log_unrestricted

    # p-value from chi-squared(1) using survival function
    # chi-squared(1) CDF: P(X <= x) = erf(sqrt(x/2))
    # p-value = 1 - CDF = erfc(sqrt(x/2))
    pvalue = math.erfc(math.sqrt(max(lr_stat, 0.0) / 2.0))

    return lr_stat, pvalue


# ── Benchmark Runner ─────────────────────────────────────────────────────


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the VaR backtesting benchmark."""
    logger.info("CARF Finance / VaR Backtesting Benchmark (H36)")

    t_start = time.perf_counter()

    # 1. Generate synthetic returns
    logger.info("  Generating 1000 days of synthetic portfolio returns (seed=42)...")
    returns = generate_synthetic_returns(n_days=1000, seed=42)
    T = len(returns)

    # Basic return statistics
    import numpy as np

    arr = np.array(returns)
    return_stats = {
        "count": T,
        "mean": round(float(arr.mean()), 6),
        "std": round(float(arr.std()), 6),
        "min": round(float(arr.min()), 6),
        "max": round(float(arr.max()), 6),
        "skewness": round(float(((arr - arr.mean()) ** 3).mean() / arr.std() ** 3), 4),
        "kurtosis": round(float(((arr - arr.mean()) ** 4).mean() / arr.std() ** 4), 4),
    }
    logger.info(f"    Mean={return_stats['mean']:.6f}, Std={return_stats['std']:.6f}, "
                f"Skew={return_stats['skewness']:.4f}, Kurt={return_stats['kurtosis']:.4f}")

    # 2. Compute 99% VaR via historical simulation
    confidence = 0.99
    var_99 = compute_historical_var(returns, confidence=confidence)
    logger.info(f"  99% VaR (historical simulation): {var_99:.6f}")

    # 3. Backtest: count exceptions
    p = 1.0 - confidence  # Expected exception rate = 0.01
    losses = [-r for r in returns]  # Convert returns to losses (positive = loss)
    exceptions = sum(1 for loss in losses if loss > var_99)
    exception_rate = exceptions / T

    logger.info(f"  Exceptions: {exceptions}/{T} (rate={exception_rate:.4f}, expected={p:.4f})")

    # 4. Kupiec POF test
    lr_stat, kupiec_pvalue = kupiec_pof_test(T=T, N=exceptions, p=p)
    logger.info(f"  Kupiec LR statistic: {lr_stat:.4f}")
    logger.info(f"  Kupiec p-value:      {kupiec_pvalue:.4f}")

    # 5. Determine pass/fail
    model_not_rejected = kupiec_pvalue > 0.05
    logger.info(f"  Model accepted (pvalue > 0.05): {model_not_rejected}")

    elapsed_s = time.perf_counter() - t_start

    # Individual daily results (first 20 + any exception days for brevity)
    individual_results = []
    for i, r in enumerate(returns):
        loss = -r
        is_exception = loss > var_99
        if i < 20 or is_exception:
            individual_results.append({
                "day": i + 1,
                "return": round(r, 6),
                "loss": round(loss, 6),
                "var_99": round(var_99, 6),
                "is_exception": is_exception,
            })

    metrics = {
        "kupiec_pvalue": round(kupiec_pvalue, 6),
        "kupiec_lr_statistic": round(lr_stat, 6),
        "var_99": round(var_99, 6),
        "exception_count": exceptions,
        "exception_rate": round(exception_rate, 6),
        "expected_exception_rate": p,
        "total_days": T,
        "model_not_rejected": model_not_rejected,
    }

    report = {
        "benchmark": "carf_finance_var_backtest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "return_statistics": return_stats,
        "elapsed_seconds": round(elapsed_s, 3),
        "individual_results": individual_results,
    }

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("Finance VaR Benchmark Summary:")
    logger.info(f"  99% VaR:           {var_99:.6f}")
    logger.info(f"  Exceptions:        {exceptions}/{T}")
    logger.info(f"  Kupiec p-value:    {kupiec_pvalue:.4f}")
    logger.info(f"  RESULT:            {'PASS' if model_not_rejected else 'FAIL'}")
    logger.info(f"  Elapsed:           {elapsed_s:.2f}s")
    logger.info("=" * 60)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="finance", source_reference="benchmark:finance", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Finance / VaR Backtesting (H36)")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    run_benchmark(output_path=args.output)


if __name__ == "__main__":
    main()
