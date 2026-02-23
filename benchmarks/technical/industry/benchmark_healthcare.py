"""Benchmark CARF IHDP-Style Causal Healthcare Benchmark (H35).

Generates a synthetic dataset inspired by the Infant Health and Development
Program (IHDP), widely used for causal inference benchmarking:

  - 747 subjects
  - 6 continuous features (birth_weight, head_circumference, weeks_preterm,
    birth_length, apgar_score, neonatal_health_index)
  - 19 binary features (mother_education_*, race_*, prenatal_care, etc.)
  - Binary treatment
  - Continuous outcome
  - Known Conditional Average Treatment Effect (CATE) from the DGP

The benchmark runs CARF's causal estimation and compares the result against
the RCT-equivalent ground truth embedded in the DGP.

Metrics:
  - cate_accuracy_vs_rct >= 0.90 (fraction of subjects whose CATE estimate
    is within 30% of the true individual treatment effect)

Usage:
    python benchmarks/technical/industry/benchmark_healthcare.py
    python benchmarks/technical/industry/benchmark_healthcare.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.healthcare")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Utility ──────────────────────────────────────────────────────────────

def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(z >= 0, 1 / (1 + np.exp(-z)), np.exp(z) / (1 + np.exp(z)))


# ── IHDP-Inspired Data Generation ───────────────────────────────────────

CONTINUOUS_FEATURES = [
    "birth_weight_kg",
    "head_circumference_cm",
    "weeks_preterm",
    "birth_length_cm",
    "apgar_score",
    "neonatal_health_index",
]

BINARY_FEATURES = [
    "mother_education_high_school",
    "mother_education_some_college",
    "mother_education_college",
    "mother_education_graduate",
    "mother_married",
    "mother_employed",
    "race_white",
    "race_black",
    "race_hispanic",
    "race_other",
    "prenatal_care_first_trimester",
    "prenatal_vitamins",
    "previous_preterm_birth",
    "smoking_during_pregnancy",
    "alcohol_during_pregnancy",
    "gestational_diabetes",
    "hypertension",
    "multiple_birth",
    "urban_residence",
]


def generate_ihdp_dataset(
    n: int = 747, seed: int = 42,
) -> tuple[list[dict[str, Any]], np.ndarray, float]:
    """Generate IHDP-inspired synthetic dataset.

    Returns:
        data: list of dicts (each row = one subject)
        true_ites: array of true individual treatment effects
        true_ate: population average treatment effect
    """
    rng = np.random.default_rng(seed)

    # ── Continuous features ──────────────────────────────────────────────
    birth_weight = rng.normal(3.0, 0.6, n).clip(0.5, 5.5)
    head_circ = rng.normal(34.0, 2.5, n).clip(25.0, 42.0)
    weeks_preterm = rng.exponential(2.0, n).clip(0.0, 16.0)
    birth_length = rng.normal(50.0, 3.0, n).clip(35.0, 60.0)
    apgar = rng.integers(3, 11, size=n).astype(float)
    nhi = rng.beta(5, 2, n) * 100.0  # 0-100 index

    continuous = np.column_stack([
        birth_weight, head_circ, weeks_preterm,
        birth_length, apgar, nhi,
    ])

    # ── Binary features ──────────────────────────────────────────────────
    binary_probs = [
        0.30,  # high_school
        0.25,  # some_college
        0.20,  # college
        0.08,  # graduate
        0.55,  # married
        0.45,  # employed
        0.55,  # white
        0.25,  # black
        0.15,  # hispanic
        0.05,  # other
        0.70,  # prenatal_first_tri
        0.65,  # prenatal_vitamins
        0.12,  # previous_preterm
        0.15,  # smoking
        0.08,  # alcohol
        0.06,  # gestational_diabetes
        0.10,  # hypertension
        0.03,  # multiple_birth
        0.60,  # urban
    ]
    binary = np.column_stack([
        rng.binomial(1, p, n).astype(float) for p in binary_probs
    ])

    # ── Treatment assignment (non-random, confounded) ────────────────────
    # Higher-risk infants more likely to receive treatment (like IHDP)
    logit_ps = (
        -0.5
        - 0.8 * (birth_weight - 3.0)
        - 0.3 * (head_circ - 34.0) / 2.5
        + 0.4 * weeks_preterm / 2.0
        - 0.2 * apgar / 10.0
        + 0.3 * binary[:, 12]   # previous_preterm
        + 0.2 * binary[:, 13]   # smoking
    )
    propensity = _sigmoid(logit_ps)
    T = rng.binomial(1, propensity, n).astype(float)

    # ── Outcome generation with heterogeneous treatment effect ───────────
    # Base outcome: cognitive development score (0-100 scale)
    Y0 = (
        40.0
        + 5.0 * (birth_weight - 3.0)
        + 1.5 * (head_circ - 34.0)
        - 2.0 * weeks_preterm
        + 0.5 * birth_length
        + 2.0 * apgar
        + 0.1 * nhi
        + 3.0 * binary[:, 2]   # college education
        + 5.0 * binary[:, 3]   # graduate education
        + 2.0 * binary[:, 4]   # married
        - 3.0 * binary[:, 13]  # smoking
        - 2.0 * binary[:, 14]  # alcohol
        + rng.normal(0, 3.0, n)
    )

    # Heterogeneous treatment effect: larger for higher-risk infants
    tau = (
        8.0
        + 3.0 * (weeks_preterm / 4.0)
        - 1.5 * (birth_weight - 3.0)
        + 1.0 * binary[:, 10]  # prenatal care
        + 0.5 * binary[:, 11]  # vitamins
        + rng.normal(0, 1.0, n)
    )
    tau = np.clip(tau, 0.0, 25.0)  # treatment always helps or is neutral

    Y1 = Y0 + tau
    Y_observed = np.where(T == 1, Y1, Y0)

    true_ites = tau
    true_ate = float(np.mean(tau))

    # ── Assemble dataset ─────────────────────────────────────────────────
    data: list[dict[str, Any]] = []
    for i in range(n):
        row: dict[str, Any] = {
            "subject_id": i + 1,
            "treatment": float(T[i]),
            "outcome": round(float(Y_observed[i]), 2),
        }
        for j, name in enumerate(CONTINUOUS_FEATURES):
            row[name] = round(float(continuous[i, j]), 4)
        for j, name in enumerate(BINARY_FEATURES):
            row[name] = float(binary[i, j])
        data.append(row)

    return data, true_ites, true_ate


# ── CATE Estimation ──────────────────────────────────────────────────────

async def estimate_cate(
    data: list[dict[str, Any]],
) -> tuple[float, np.ndarray]:
    """Estimate ATE and per-subject CATE using CARF or fallback OLS.

    Returns:
        estimated_ate: float
        estimated_cates: array of per-subject estimates
    """
    covariates = CONTINUOUS_FEATURES + BINARY_FEATURES

    try:
        from src.services.causal import (
            CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig,
        )
        engine = CausalInferenceEngine(neo4j_service=None)

        hypothesis = CausalHypothesis(
            treatment="treatment", outcome="outcome",
            mechanism="IHDP-style: developmental intervention -> cognitive score",
            confounders=covariates,
        )
        config = CausalEstimationConfig(
            data=data, treatment="treatment", outcome="outcome",
            covariates=covariates,
            method_name="backdoor.linear_regression",
        )
        result = await engine.estimate_effect(
            hypothesis=hypothesis, estimation_config=config,
        )
        estimated_ate = result.effect_estimate

        # For CATE, use the estimated ATE as a uniform estimate for now
        # (full HTE estimation would use EconML T-learner)
        estimated_cates = np.full(len(data), estimated_ate)
        return estimated_ate, estimated_cates

    except Exception as exc:
        logger.warning(f"Causal service unavailable ({exc}); using OLS fallback.")

        # OLS fallback
        n = len(data)
        Y = np.array([d["outcome"] for d in data])
        T = np.array([d["treatment"] for d in data])

        X_list = []
        for cov in covariates:
            X_list.append([d.get(cov, 0.0) for d in data])
        X = np.column_stack(X_list)

        # OLS with treatment and covariates
        X_full = np.column_stack([np.ones(n), T, X])
        try:
            beta = np.linalg.lstsq(X_full, Y, rcond=None)[0]
        except np.linalg.LinAlgError:
            beta = np.zeros(X_full.shape[1])

        estimated_ate = float(beta[1])  # coefficient on treatment

        # Simple CATE approximation using T-learner approach
        # Fit separate models for treated and control
        treated_mask = T == 1
        control_mask = T == 0

        X_t = np.column_stack([np.ones(treated_mask.sum()), X[treated_mask]])
        X_c = np.column_stack([np.ones(control_mask.sum()), X[control_mask]])

        try:
            beta_t = np.linalg.lstsq(X_t, Y[treated_mask], rcond=None)[0]
            beta_c = np.linalg.lstsq(X_c, Y[control_mask], rcond=None)[0]
        except np.linalg.LinAlgError:
            # Fallback: uniform ATE
            return estimated_ate, np.full(n, estimated_ate)

        # Predict Y1 and Y0 for all subjects
        X_all = np.column_stack([np.ones(n), X])
        Y1_hat = X_all @ beta_t
        Y0_hat = X_all @ beta_c
        estimated_cates = Y1_hat - Y0_hat

        return estimated_ate, estimated_cates


# ── Benchmark ────────────────────────────────────────────────────────────

async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run IHDP-style causal healthcare benchmark."""
    logger.info("=" * 70)
    logger.info("CARF IHDP-Style Healthcare Causal Benchmark (H35)")
    logger.info("=" * 70)

    t0 = time.perf_counter()
    data, true_ites, true_ate = generate_ihdp_dataset(n=747, seed=42)
    logger.info(f"  Generated {len(data)} subjects, true ATE = {true_ate:.4f}")

    estimated_ate, estimated_cates = await estimate_cate(data)
    elapsed = time.perf_counter() - t0

    logger.info(f"  Estimated ATE = {estimated_ate:.4f}")

    # Evaluate CATE accuracy
    # For each subject: is the estimated CATE within 30% of the true ITE?
    n = len(data)
    correct_count = 0
    individual_results: list[dict[str, Any]] = []

    for i in range(n):
        true_ite = float(true_ites[i])
        est_cate = float(estimated_cates[i])
        bias = est_cate - true_ite

        # Within 30% tolerance
        if abs(true_ite) < 0.5:
            # Near-zero true effect: check absolute closeness
            is_accurate = abs(bias) < 1.0
        else:
            is_accurate = abs(bias) <= 0.30 * abs(true_ite)

        if is_accurate:
            correct_count += 1

        # Only include a summary for logging (not all 747)
        individual_results.append({
            "subject_id": i + 1,
            "true_ite": round(true_ite, 4),
            "estimated_cate": round(est_cate, 4),
            "bias": round(bias, 4),
            "accurate": is_accurate,
        })

    cate_accuracy = correct_count / max(n, 1)

    # ATE-level accuracy
    ate_bias = estimated_ate - true_ate
    ate_relative_error = abs(ate_bias) / max(abs(true_ate), 0.01)

    # Summary stats
    all_biases = estimated_cates - true_ites
    rmse = float(np.sqrt(np.mean(all_biases ** 2)))
    mae = float(np.mean(np.abs(all_biases)))

    report: dict[str, Any] = {
        "benchmark": "carf_healthcare_ihdp",
        "hypothesis": "H35",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_subjects": n,
        "n_continuous_features": len(CONTINUOUS_FEATURES),
        "n_binary_features": len(BINARY_FEATURES),
        "elapsed_seconds": round(elapsed, 4),
        "metrics": {
            "cate_accuracy_vs_rct": round(cate_accuracy, 4),
            "cate_accuracy_target": 0.90,
            "cate_accuracy_passed": cate_accuracy >= 0.90,
            "true_ate": round(true_ate, 4),
            "estimated_ate": round(estimated_ate, 4),
            "ate_bias": round(ate_bias, 4),
            "ate_relative_error": round(ate_relative_error, 4),
            "cate_rmse": round(rmse, 4),
            "cate_mae": round(mae, 4),
            "n_accurate": correct_count,
        },
        "individual_results": individual_results,
    }

    logger.info("\n" + "=" * 70)
    logger.info(f"  True ATE:          {true_ate:.4f}")
    logger.info(f"  Estimated ATE:     {estimated_ate:.4f}  (bias={ate_bias:.4f})")
    logger.info(f"  CATE Accuracy:     {cate_accuracy:.0%}  ({correct_count}/{n} subjects)")
    logger.info(f"  CATE RMSE:         {rmse:.4f}")
    logger.info(f"  CATE MAE:          {mae:.4f}")
    logger.info(f"  Target: >= 90%  |  {'PASSED' if cate_accuracy >= 0.90 else 'FAILED'}")
    logger.info("=" * 70)

    from benchmarks import finalize_benchmark_report

    report = finalize_benchmark_report(report, benchmark_id="healthcare", source_reference="benchmark:healthcare", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CARF IHDP-Style Healthcare Causal (H35)",
    )
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
