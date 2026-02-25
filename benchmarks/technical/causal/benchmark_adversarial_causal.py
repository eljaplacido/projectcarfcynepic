# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Adversarial Causal Inference Robustness (H24).

Tests the causal inference engine against 10 adversarial data-generating
processes, each embedding a specific form of statistical bias:

  1. Confounding injection (unmeasured confounder)
  2. Selection bias (non-random sampling)
  3. Measurement error (noisy treatment)
  4. Collider bias
  5. Reverse causation setup
  6. Simpson's paradox
  7. Mediator confounding
  8. Time-varying confounding
  9. Interference / spillover effects
  10. Informative censoring

Each DGP generates N=500 synthetic observations (seed=42) with a known true
ATE.  The benchmark checks whether the estimated ATE falls within 50% of the
true value.

Metrics:
  - robustness_rate: fraction of scenarios handled correctly (target >= 0.70)

Usage:
    python benchmarks/technical/causal/benchmark_adversarial_causal.py
    python benchmarks/technical/causal/benchmark_adversarial_causal.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.adversarial_causal")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Utility ──────────────────────────────────────────────────────────────

def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(z >= 0, 1 / (1 + np.exp(-z)), np.exp(z) / (1 + np.exp(z)))


# ── Adversarial DGP Generators ───────────────────────────────────────────

def _dgp_confounding_injection(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Unmeasured confounder U drives both T and Y.  True ATE = 3.0."""
    rng = np.random.default_rng(seed)
    U = rng.normal(0, 1, n)          # unmeasured
    X1 = rng.normal(0, 1, n)
    prop = _sigmoid(0.8 * U + 0.3 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 2.0 + 3.0 * T + 2.0 * U + 1.0 * X1 + rng.normal(0, 0.5, n)
    # Only X1 is observed; U is hidden
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i])} for i in range(n)]
    return data, 3.0, "confounding_injection"


def _dgp_selection_bias(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Non-random sampling: only units with high X1 are kept.  True ATE = 2.0."""
    rng = np.random.default_rng(seed)
    n_full = n * 3  # oversample then filter
    X1 = rng.normal(0, 1, n_full)
    X2 = rng.normal(0, 1, n_full)
    prop = _sigmoid(0.4 * X1 - 0.2 * X2)
    T = rng.binomial(1, prop, n_full).astype(float)
    Y = 1.0 + 2.0 * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, 0.8, n_full)
    # Selection: keep only if X1 > -0.5 (non-random)
    mask = X1 > -0.5
    idx = np.where(mask)[0][:n]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "X2": float(X2[i])} for i in idx]
    return data, 2.0, "selection_bias"


def _dgp_measurement_error(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Treatment measured with noise.  True ATE = 4.0."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    T_star = rng.binomial(1, _sigmoid(0.5 * X1), n).astype(float)
    # Observed treatment has 15% misclassification
    flip = rng.binomial(1, 0.15, n).astype(float)
    T_obs = np.abs(T_star - flip)
    Y = 3.0 + 4.0 * T_star + 1.0 * X1 + rng.normal(0, 1.0, n)
    data = [{"treatment": float(T_obs[i]), "outcome": float(Y[i]),
             "X1": float(X1[i])} for i in range(n)]
    return data, 4.0, "measurement_error"


def _dgp_collider_bias(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """C is a collider of T and Y; conditioning on C biases the estimate.  True ATE = 2.5."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    prop = _sigmoid(0.3 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 1.0 + 2.5 * T + 1.5 * X1 + rng.normal(0, 0.5, n)
    C = 0.5 * T + 0.5 * Y + rng.normal(0, 0.3, n)  # collider
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "C": float(C[i])} for i in range(n)]
    return data, 2.5, "collider_bias"


def _dgp_reverse_causation(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Y actually causes T (reverse).  True ATE of T on Y = 0.0."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    Y = 5.0 + 2.0 * X1 + rng.normal(0, 1.0, n)
    # T is a consequence of Y, not a cause
    T = (Y > np.median(Y)).astype(float)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i])} for i in range(n)]
    return data, 0.0, "reverse_causation"


def _dgp_simpsons_paradox(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Simpson's paradox: within-group effect is positive, marginal is negative.  True ATE = 1.5."""
    rng = np.random.default_rng(seed)
    group = rng.binomial(1, 0.5, n).astype(float)
    prop = _sigmoid(-1.0 + 2.0 * group)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 2.0 + 1.5 * T + 5.0 * group + rng.normal(0, 0.5, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "group": float(group[i])} for i in range(n)]
    return data, 1.5, "simpsons_paradox"


def _dgp_mediator_confounding(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """M is a mediator and also confounded.  True total ATE = 3.0."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    prop = _sigmoid(0.5 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    U = rng.normal(0, 1, n)  # unmeasured confounder of M and Y
    M = 1.0 * T + 0.5 * U + rng.normal(0, 0.3, n)  # mediator
    Y = 1.0 + 2.0 * T + 1.0 * M + 0.8 * U + 0.5 * X1 + rng.normal(0, 0.5, n)
    # Total effect of T on Y = 2.0 (direct) + 1.0 * 1.0 (via M) = 3.0
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "M": float(M[i])} for i in range(n)]
    return data, 3.0, "mediator_confounding"


def _dgp_time_varying_confounding(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Time-varying confounder: L_t affects both T_t and Y_t.  True ATE = 2.0."""
    rng = np.random.default_rng(seed)
    L_prev = rng.normal(0, 1, n)
    T_prev = rng.binomial(1, _sigmoid(0.5 * L_prev), n).astype(float)
    # Current period
    L_curr = 0.5 * L_prev + 0.3 * T_prev + rng.normal(0, 0.5, n)
    prop = _sigmoid(0.4 * L_curr + 0.2 * L_prev)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 3.0 + 2.0 * T + 1.0 * L_curr + 0.5 * L_prev + rng.normal(0, 0.8, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "L_prev": float(L_prev[i]), "L_curr": float(L_curr[i]),
             "T_prev": float(T_prev[i])} for i in range(n)]
    return data, 2.0, "time_varying_confounding"


def _dgp_interference_spillover(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Spillover: treatment of neighbours affects own outcome.  True direct ATE = 2.5."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    prop = _sigmoid(0.3 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    # Spillover: fraction of neighbours treated (cyclic network)
    neighbour_frac = np.array([
        (T[(i - 1) % n] + T[(i + 1) % n]) / 2.0 for i in range(n)
    ])
    Y = 1.0 + 2.5 * T + 1.0 * neighbour_frac + 1.5 * X1 + rng.normal(0, 0.5, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "neighbour_frac": float(neighbour_frac[i])}
            for i in range(n)]
    return data, 2.5, "interference_spillover"


def _dgp_informative_censoring(n: int = 500, seed: int = 42) -> tuple[list[dict], float, str]:
    """Informative censoring: units with worse outcomes are more likely to drop.  True ATE = -3.0."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    prop = _sigmoid(0.4 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    Y_full = 10.0 + (-3.0) * T + 2.0 * X1 + rng.normal(0, 1.5, n)
    # Censoring depends on Y: worse outcomes more likely censored
    censor_prob = _sigmoid(-0.5 * Y_full + 3.0)
    censored = rng.binomial(1, censor_prob, n).astype(bool)
    observed = ~censored
    idx = np.where(observed)[0]
    if len(idx) < 50:
        idx = np.arange(n)  # fallback: keep all if too few observed
    data = [{"treatment": float(T[i]), "outcome": float(Y_full[i]),
             "X1": float(X1[i])} for i in idx[:n]]
    return data, -3.0, "informative_censoring"


# ── All DGP functions ────────────────────────────────────────────────────

ALL_DGPS = [
    _dgp_confounding_injection,
    _dgp_selection_bias,
    _dgp_measurement_error,
    _dgp_collider_bias,
    _dgp_reverse_causation,
    _dgp_simpsons_paradox,
    _dgp_mediator_confounding,
    _dgp_time_varying_confounding,
    _dgp_interference_spillover,
    _dgp_informative_censoring,
]


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class AdversarialTestResult:
    scenario: str
    true_ate: float
    estimated_ate: float = 0.0
    bias: float = 0.0
    within_50pct: bool = False
    elapsed_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {k: round(v, 6) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


# ── Runner ───────────────────────────────────────────────────────────────

async def run_single_scenario(
    data: list[dict], true_ate: float, scenario_name: str,
) -> AdversarialTestResult:
    """Run CARF causal estimation on a single adversarial scenario."""
    t0 = time.perf_counter()
    try:
        from src.services.causal import (
            CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig,
        )
        engine = CausalInferenceEngine(neo4j_service=None)

        # Infer covariates from data keys (exclude treatment/outcome)
        covariates = [k for k in data[0].keys() if k not in ("treatment", "outcome")]

        hypothesis = CausalHypothesis(
            treatment="treatment", outcome="outcome",
            mechanism=f"Adversarial benchmark: {scenario_name}",
            confounders=covariates,
        )
        config = CausalEstimationConfig(
            data=data, treatment="treatment", outcome="outcome",
            covariates=covariates,
            method_name="backdoor.linear_regression",
        )
        result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
        elapsed = time.perf_counter() - t0

        est = result.effect_estimate
        bias = est - true_ate

        # Within 50% check:
        # For null ATE (0.0), check if estimate is close to zero (|est| < 1.0)
        if abs(true_ate) < 1e-6:
            within = abs(est) < 1.0
        else:
            within = abs(bias) <= 0.50 * abs(true_ate)

        return AdversarialTestResult(
            scenario=scenario_name, true_ate=true_ate,
            estimated_ate=est, bias=bias,
            within_50pct=within, elapsed_seconds=elapsed,
        )
    except Exception as exc:
        return AdversarialTestResult(
            scenario=scenario_name, true_ate=true_ate,
            elapsed_seconds=time.perf_counter() - t0, error=str(exc),
        )


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run all 10 adversarial causal DGP scenarios."""
    logger.info("=" * 70)
    logger.info("CARF Adversarial Causal Inference Benchmark (H24)")
    logger.info("=" * 70)

    results: list[AdversarialTestResult] = []

    for dgp_fn in ALL_DGPS:
        data, true_ate, scenario_name = dgp_fn(n=500, seed=42)
        logger.info(f"  Running scenario: {scenario_name} (true ATE={true_ate})")
        res = await run_single_scenario(data, true_ate, scenario_name)
        results.append(res)

        if res.error:
            logger.error(f"    ERROR: {res.error}")
        else:
            status = "PASS" if res.within_50pct else "FAIL"
            logger.info(
                f"    ATE={res.estimated_ate:.4f}  bias={res.bias:.4f}  "
                f"within_50pct={res.within_50pct}  [{status}]"
            )

    # Aggregate metrics
    valid = [r for r in results if r.error is None]
    n_valid = len(valid)
    n_within = sum(1 for r in valid if r.within_50pct)
    robustness_rate = n_within / max(n_valid, 1)

    report: dict[str, Any] = {
        "benchmark": "carf_adversarial_causal",
        "hypothesis": "H24",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_scenarios": len(ALL_DGPS),
        "n_successful": n_valid,
        "n_within_50pct": n_within,
        "metrics": {
            "robustness_rate": round(robustness_rate, 4),
            "robustness_target": 0.70,
            "robustness_passed": robustness_rate >= 0.70,
            "mean_absolute_bias": round(
                sum(abs(r.bias) for r in valid) / max(n_valid, 1), 6
            ),
            "mean_elapsed_seconds": round(
                sum(r.elapsed_seconds for r in valid) / max(n_valid, 1), 4
            ),
        },
        "individual_results": [r.to_dict() for r in results],
    }

    logger.info("\n" + "=" * 70)
    logger.info(f"  Robustness Rate: {robustness_rate:.0%}  ({n_within}/{n_valid} scenarios)")
    logger.info(f"  Target: >= 70%  |  {'PASSED' if robustness_rate >= 0.70 else 'FAILED'}")
    logger.info("=" * 70)

    from benchmarks import finalize_benchmark_report

    report = finalize_benchmark_report(report, benchmark_id="adversarial_causal", source_reference="benchmark:adversarial_causal", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Adversarial Causal Inference (H24)")
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
