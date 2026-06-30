# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H53 — Conformal prediction-interval coverage on real data (R2).

Extends H46 (synthetic conformal router coverage) to a **real** dataset and to the
regression setting, validating that CARF's split-conformal layer delivers its
distribution-free marginal-coverage guarantee on real-world data rather than only on
generator-defined synthetic inputs.

Uses scikit-learn's bundled **diabetes** dataset (442 real patients, 10 features,
disease-progression target) — real and fully offline, so the benchmark is
deterministic and needs no network. A gradient-boosting regressor is fit on a train
split; absolute residuals on a disjoint calibration split set the conformal threshold;
empirical coverage is measured on a held-out test split across several miscoverage
levels.

Evidence grade: ``validated`` — real data, empirical (measured) coverage, deterministic
(fixed split seed), reproducible offline.

Run:
    python -m benchmarks.technical.realworld.benchmark_conformal_realdata
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("benchmark.conformal_realdata")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SEED = 53
ALPHAS = [0.05, 0.10, 0.20]
COVERAGE_TOLERANCE = 0.05  # finite-sample slack below nominal level


def load_real_dataset() -> tuple[Any, Any] | None:
    """Load the bundled real diabetes dataset as ``(X, y)``; None if sklearn absent."""
    try:
        from sklearn.datasets import load_diabetes

        data = load_diabetes()
        return data.data, data.target
    except Exception as exc:  # pragma: no cover - sklearn is a core dep
        logger.warning("Real dataset unavailable: %s", exc)
        return None


def compute_coverage(y_true: Any, y_pred: Any, abs_residuals_cal: Any, alpha: float) -> dict[str, Any]:
    """Fit the conformal threshold on calibration residuals and measure test coverage."""
    from src.utils.conformal import conformal_regression_quantile, regression_coverage

    qhat = conformal_regression_quantile(abs_residuals_cal, alpha=alpha)
    coverage = regression_coverage(y_true, y_pred, qhat)
    nominal = 1.0 - alpha
    return {
        "alpha": alpha,
        "nominal_coverage": round(nominal, 4),
        "empirical_coverage": round(coverage, 4),
        "interval_half_width": round(qhat, 4),
        "passed": coverage >= nominal - COVERAGE_TOLERANCE,
    }


def run_benchmark() -> dict[str, Any]:
    from benchmarks import finalize_benchmark_report

    loaded = load_real_dataset()
    if loaded is None:
        report = {
            "hypothesis": "H53",
            "claim": "Conformal prediction intervals achieve >= 1-alpha marginal coverage on real data",
            "status": "skipped",
            "passed": False,
            "evidence_grade": "aspirational",
            "reason": "scikit-learn diabetes dataset unavailable",
            "data_source": "sklearn.datasets.load_diabetes",
        }
        return finalize_benchmark_report(report, benchmark_id="conformal_realdata")

    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor

    X, y = loaded
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(y))
    n_train = int(0.5 * len(y))
    n_cal = int(0.25 * len(y))
    tr, cal, te = idx[:n_train], idx[n_train : n_train + n_cal], idx[n_train + n_cal :]

    model = GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=SEED)
    model.fit(X[tr], y[tr])
    abs_resid_cal = np.abs(y[cal] - model.predict(X[cal]))
    y_pred_test = model.predict(X[te])

    per_alpha = [compute_coverage(y[te], y_pred_test, abs_resid_cal, a) for a in ALPHAS]
    all_pass = all(r["passed"] for r in per_alpha)
    headline = next(r for r in per_alpha if r["alpha"] == 0.10)

    report = {
        "hypothesis": "H53",
        "claim": "Split-conformal regression intervals achieve >= 1-alpha marginal coverage "
        "on the real sklearn diabetes dataset",
        "metric": "conformal_coverage",
        "conformal_coverage": headline["empirical_coverage"],
        "nominal_coverage": headline["nominal_coverage"],
        "interval_half_width": headline["interval_half_width"],
        "threshold": round(headline["nominal_coverage"] - COVERAGE_TOLERANCE, 4),
        "coverage_tolerance": COVERAGE_TOLERANCE,
        "per_alpha": per_alpha,
        "passed": all_pass,
        "method": "split-conformal regression (absolute-residual quantile)",
        "dataset_profile": "real",
        "ground_truth_type": "empirical",
        "data_source": "sklearn.datasets.load_diabetes (442 real patients)",
        "n_train": int(n_train),
        "n_calibration": int(n_cal),
        "n_test": int(len(te)),
        "samples": int(len(te)),
        "seed": SEED,
        "evidence_grade": "validated",
    }
    return finalize_benchmark_report(
        report,
        benchmark_id="conformal_realdata",
        source_reference="sklearn diabetes (Efron et al. 2004); split-conformal regression coverage",
        dataset_context={"dataset_profile": "real", "ground_truth_type": "empirical"},
        sample_context={"n_test": int(len(te))},
        benchmark_config={"alphas": ALPHAS, "seed": SEED},
    )


def main() -> None:
    report = run_benchmark()
    out_path = Path(__file__).with_name("benchmark_conformal_realdata_results.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report.get("status") == "skipped":
        print("[H53] Real-data conformal coverage SKIPPED")
    else:
        status = "PASS" if report["passed"] else "FAIL"
        print(f"[H53] Real-data conformal coverage: {status}")
        for r in report["per_alpha"]:
            print(f"  alpha={r['alpha']:.2f}  nominal={r['nominal_coverage']:.3f}  "
                  f"empirical={r['empirical_coverage']:.3f}  half-width={r['interval_half_width']:.1f}  "
                  f"{'ok' if r['passed'] else 'MISS'}")
    print(f"  results -> {out_path}")


if __name__ == "__main__":
    main()
