# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H46 — Conformal Router Coverage benchmark (R1/G2).

Validates the central claim of split-conformal router calibration:

    P( true_domain in prediction_set(X) ) >= 1 - alpha   (marginal coverage)

The router emits a probability distribution over the five Cynefin domains. We fit a
split-conformal (LAC) calibration on a held-out calibration split and measure the
*empirical* coverage on a disjoint test split across several miscoverage levels. The
hypothesis passes when empirical coverage meets the nominal 1 - alpha level (within a
small finite-sample tolerance) at every tested alpha.

This is a synthetic-ground-truth sanity benchmark: the domain distributions are
generated, so coverage validates the calibration *mathematics*, not real-world router
accuracy. Evidence grade: synthetic-only.

Run:
    python -m benchmarks.technical.calibration.benchmark_conformal_router
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from benchmarks import finalize_benchmark_report
from src.utils.conformal import (
    average_set_size,
    empirical_coverage,
    fit_conformal,
)

DOMAINS = ["Clear", "Complicated", "Complex", "Chaotic", "Disorder"]
SEED = 46
ALPHAS = [0.05, 0.10, 0.20]
N_CAL = 800
N_TEST = 800
SHARPNESS = 0.45  # how strongly the true-label score dominates (lower = harder/overlapping)
COVERAGE_TOLERANCE = 0.03  # finite-sample slack below nominal level


def _synthetic_router_scores(n: int, seed: int):
    """Generate (softmax-like domain distribution, true_domain) pairs."""
    rng = random.Random(seed)
    scores: list[dict[str, float]] = []
    labels: list[str] = []
    for _ in range(n):
        true = rng.choice(DOMAINS)
        raw = {d: rng.random() for d in DOMAINS}
        raw[true] += SHARPNESS
        total = sum(raw.values())
        scores.append({d: v / total for d, v in raw.items()})
        labels.append(true)
    return scores, labels


def run_benchmark() -> dict:
    cal_scores, cal_labels = _synthetic_router_scores(N_CAL, SEED)
    test_scores, test_labels = _synthetic_router_scores(N_TEST, SEED + 1)

    per_alpha = []
    all_pass = True
    for alpha in ALPHAS:
        calibration = fit_conformal(cal_scores, cal_labels, alpha=alpha)
        coverage = empirical_coverage(test_scores, test_labels, calibration)
        avg_size = average_set_size(test_scores, calibration)
        nominal = 1.0 - alpha
        passed = coverage >= nominal - COVERAGE_TOLERANCE
        all_pass = all_pass and passed
        per_alpha.append(
            {
                "alpha": alpha,
                "nominal_coverage": round(nominal, 4),
                "empirical_coverage": round(coverage, 4),
                "avg_set_size": round(avg_size, 4),
                "qhat": calibration.qhat,
                "passed": passed,
            }
        )

    # Headline metric: coverage at the default alpha=0.10.
    headline = next(r for r in per_alpha if r["alpha"] == 0.10)

    report = {
        "hypothesis": "H46",
        "claim": "Conformal router prediction sets achieve >= 1-alpha marginal coverage",
        "metric": "conformal_coverage",
        "conformal_coverage": headline["empirical_coverage"],
        "nominal_coverage": headline["nominal_coverage"],
        "avg_set_size": headline["avg_set_size"],
        "threshold": round(headline["nominal_coverage"] - COVERAGE_TOLERANCE, 4),
        "coverage_tolerance": COVERAGE_TOLERANCE,
        "per_alpha": per_alpha,
        "passed": all_pass,
        "method": "split-conformal LAC (Sadinle et al. 2019)",
        "dataset_profile": "synthetic",
        "data_source": "benchmarks/technical/calibration/benchmark_conformal_router.py (seeded generator)",
        "n_calibration": N_CAL,
        "n_test": N_TEST,
        "samples": N_TEST,
        "seed": SEED,
    }

    return finalize_benchmark_report(
        report,
        benchmark_id="conformal_router",
        source_reference="R1/G2 conformal router coverage (deep-research integration roadmap)",
        dataset_context={"dataset_profile": "synthetic", "domains": DOMAINS},
        sample_context={"n_calibration": N_CAL, "n_test": N_TEST},
        benchmark_config={"alphas": ALPHAS, "sharpness": SHARPNESS, "seed": SEED},
    )


def main() -> None:
    report = run_benchmark()
    out_path = Path(__file__).with_name("benchmark_conformal_router_results.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    status = "PASS" if report["passed"] else "FAIL"
    print(f"[H46] Conformal router coverage: {status}")
    for r in report["per_alpha"]:
        print(
            f"  alpha={r['alpha']:.2f}  nominal={r['nominal_coverage']:.3f}  "
            f"empirical={r['empirical_coverage']:.3f}  avg_set={r['avg_set_size']:.2f}  "
            f"{'ok' if r['passed'] else 'MISS'}"
        )
    print(f"  results -> {out_path}")


if __name__ == "__main__":
    main()
