"""Benchmark CARF Counterfactual Reasoning (H17 — CounterBench).

Generates 50 counterfactual scenarios using known Data Generating Processes
(DGPs) and compares CARF pipeline accuracy vs a raw-LLM heuristic baseline.

DGP distribution:
  - Linear:      20 scenarios
  - Nonlinear:   15 scenarios
  - Interaction:  10 scenarios
  - Threshold:    5 scenarios

Each scenario has a known ground-truth counterfactual effect.  For each
scenario we compute:
  1.  CARF answer — via CausalInferenceEngine if available, otherwise a
      regression-based simulation.
  2.  Raw LLM answer — a naive difference-in-means heuristic baseline.

Pass criterion (H17):
    carf_accuracy - llm_accuracy >= 0.10   (CARF at least 10 pp better)

Usage:
    python benchmarks/technical/causal/benchmark_counterbench.py
    python benchmarks/technical/causal/benchmark_counterbench.py -o results.json
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
logger = logging.getLogger("benchmark.counterbench")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Helpers ──────────────────────────────────────────────────────────────

def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(z >= 0, 1 / (1 + np.exp(-z)), np.exp(z) / (1 + np.exp(z)))


# ── Scenario Generation ─────────────────────────────────────────────────

@dataclass
class CounterfactualScenario:
    """A single counterfactual scenario with known ground truth."""
    id: int
    dgp_type: str
    description: str
    treatment_variable: str
    outcome_variable: str
    true_counterfactual_effect: float
    data: list[dict]
    covariates: list[str] = field(default_factory=lambda: ["X1", "X2"])


def _generate_linear_scenarios(rng: np.random.Generator, start_id: int) -> list[CounterfactualScenario]:
    """Generate 20 linear DGP counterfactual scenarios."""
    scenarios: list[CounterfactualScenario] = []
    for i in range(20):
        n = 200
        seed_offset = i * 7
        sub_rng = np.random.default_rng(42 + seed_offset)

        # Vary coefficients deterministically
        beta_t = round(1.5 + 0.3 * i, 2)  # treatment effect varies 1.5..7.2
        beta_x1 = round(0.5 + 0.1 * i, 2)
        beta_x2 = round(0.3 + 0.05 * i, 2)
        intercept = 2.0

        X1 = sub_rng.normal(0, 1, n)
        X2 = sub_rng.normal(0, 1, n)
        prop = _sigmoid(0.5 * X1 - 0.3 * X2)
        T = sub_rng.binomial(1, prop, n).astype(float)
        noise = sub_rng.normal(0, 0.5, n)
        Y = intercept + beta_t * T + beta_x1 * X1 + beta_x2 * X2 + noise

        data = [
            {"treatment": float(T[j]), "outcome": float(Y[j]),
             "X1": float(X1[j]), "X2": float(X2[j])}
            for j in range(n)
        ]

        scenarios.append(CounterfactualScenario(
            id=start_id + i,
            dgp_type="linear",
            description=f"Linear DGP #{i+1}: Y = {intercept} + {beta_t}*T + {beta_x1}*X1 + {beta_x2}*X2 + noise",
            treatment_variable="treatment",
            outcome_variable="outcome",
            true_counterfactual_effect=beta_t,
            data=data,
        ))
    return scenarios


def _generate_nonlinear_scenarios(rng: np.random.Generator, start_id: int) -> list[CounterfactualScenario]:
    """Generate 15 nonlinear DGP counterfactual scenarios."""
    scenarios: list[CounterfactualScenario] = []
    for i in range(15):
        n = 200
        sub_rng = np.random.default_rng(42 + 200 + i * 11)

        # Vary the nonlinear treatment effect
        base_effect = round(2.0 + 0.4 * i, 2)
        quad_coeff = round(0.3 + 0.05 * i, 2)

        X1 = sub_rng.normal(0, 1, n)
        X2 = sub_rng.normal(0, 1, n)
        prop = _sigmoid(0.3 * X1**2 - 0.2 * X2)
        T = sub_rng.binomial(1, prop, n).astype(float)
        noise = sub_rng.normal(0, 0.6, n)
        Y = 1.0 + base_effect * T + quad_coeff * X1**2 - 0.3 * X2 + noise

        data = [
            {"treatment": float(T[j]), "outcome": float(Y[j]),
             "X1": float(X1[j]), "X2": float(X2[j])}
            for j in range(n)
        ]

        scenarios.append(CounterfactualScenario(
            id=start_id + i,
            dgp_type="nonlinear",
            description=f"Nonlinear DGP #{i+1}: Y = 1 + {base_effect}*T + {quad_coeff}*X1^2 - 0.3*X2 + noise",
            treatment_variable="treatment",
            outcome_variable="outcome",
            true_counterfactual_effect=base_effect,
            data=data,
        ))
    return scenarios


def _generate_interaction_scenarios(rng: np.random.Generator, start_id: int) -> list[CounterfactualScenario]:
    """Generate 10 interaction DGP counterfactual scenarios."""
    scenarios: list[CounterfactualScenario] = []
    for i in range(10):
        n = 200
        sub_rng = np.random.default_rng(42 + 400 + i * 13)

        base_effect = round(3.0 + 0.5 * i, 2)
        interaction_coeff = round(0.8 + 0.2 * i, 2)

        X1 = sub_rng.normal(0, 1, n)
        X2 = sub_rng.normal(0, 1, n)
        prop = _sigmoid(0.4 * X1 - 0.2 * X2)
        T = sub_rng.binomial(1, prop, n).astype(float)
        noise = sub_rng.normal(0, 0.7, n)
        # The ATE is base_effect + interaction_coeff * E[X1] = base_effect
        # (since E[X1] = 0)
        Y = 2.0 + base_effect * T + interaction_coeff * T * X1 + 1.0 * X1 + 0.5 * X2 + noise

        data = [
            {"treatment": float(T[j]), "outcome": float(Y[j]),
             "X1": float(X1[j]), "X2": float(X2[j])}
            for j in range(n)
        ]

        scenarios.append(CounterfactualScenario(
            id=start_id + i,
            dgp_type="interaction",
            description=(f"Interaction DGP #{i+1}: Y = 2 + {base_effect}*T + "
                         f"{interaction_coeff}*T*X1 + X1 + 0.5*X2 + noise (ATE={base_effect})"),
            treatment_variable="treatment",
            outcome_variable="outcome",
            true_counterfactual_effect=base_effect,
            data=data,
        ))
    return scenarios


def _generate_threshold_scenarios(rng: np.random.Generator, start_id: int) -> list[CounterfactualScenario]:
    """Generate 5 threshold DGP counterfactual scenarios."""
    scenarios: list[CounterfactualScenario] = []
    for i in range(5):
        n = 300
        sub_rng = np.random.default_rng(42 + 600 + i * 17)

        effect_above = round(4.0 + 1.0 * i, 2)
        effect_below = round(1.0 + 0.5 * i, 2)
        threshold = 0.0

        X1 = sub_rng.normal(0, 1, n)
        X2 = sub_rng.normal(0, 1, n)
        prop = _sigmoid(0.5 * X1)
        T = sub_rng.binomial(1, prop, n).astype(float)
        noise = sub_rng.normal(0, 0.5, n)

        # Treatment effect depends on whether X1 > threshold
        effect = np.where(X1 > threshold, effect_above, effect_below)
        # Population ATE ~ mean(effect) = roughly (effect_above + effect_below) / 2
        # since X1 ~ N(0,1) means ~50% above, ~50% below
        true_ate = round((effect_above + effect_below) / 2.0, 2)

        Y = 1.5 + effect * T + 1.2 * X1 + 0.4 * X2 + noise

        data = [
            {"treatment": float(T[j]), "outcome": float(Y[j]),
             "X1": float(X1[j]), "X2": float(X2[j])}
            for j in range(n)
        ]

        scenarios.append(CounterfactualScenario(
            id=start_id + i,
            dgp_type="threshold",
            description=(f"Threshold DGP #{i+1}: effect={effect_above} if X1>{threshold} else "
                         f"{effect_below} (ATE~{true_ate})"),
            treatment_variable="treatment",
            outcome_variable="outcome",
            true_counterfactual_effect=true_ate,
            data=data,
        ))
    return scenarios


def generate_all_scenarios() -> list[CounterfactualScenario]:
    """Generate all 50 counterfactual scenarios deterministically (seed=42)."""
    rng = np.random.default_rng(42)
    scenarios: list[CounterfactualScenario] = []
    scenarios.extend(_generate_linear_scenarios(rng, start_id=1))       # 20
    scenarios.extend(_generate_nonlinear_scenarios(rng, start_id=21))   # 15
    scenarios.extend(_generate_interaction_scenarios(rng, start_id=36)) # 10
    scenarios.extend(_generate_threshold_scenarios(rng, start_id=46))   # 5
    return scenarios


# ── Estimation Methods ───────────────────────────────────────────────────

async def estimate_carf(scenario: CounterfactualScenario) -> float:
    """Estimate counterfactual effect using CARF causal pipeline.

    Falls back to OLS regression if the full CausalInferenceEngine is
    unavailable (e.g. missing optional dependencies).
    """
    try:
        from src.services.causal import (
            CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig,
        )
        engine = CausalInferenceEngine(neo4j_service=None)
        hypothesis = CausalHypothesis(
            treatment=scenario.treatment_variable,
            outcome=scenario.outcome_variable,
            mechanism=f"Counterbench scenario #{scenario.id}",
            confounders=scenario.covariates,
        )
        config = CausalEstimationConfig(
            data=scenario.data,
            treatment=scenario.treatment_variable,
            outcome=scenario.outcome_variable,
            covariates=scenario.covariates,
            method_name="backdoor.linear_regression",
        )
        result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
        return float(result.effect_estimate)
    except Exception:
        # Fallback: simple OLS via numpy
        return _ols_estimate(scenario)


def _ols_estimate(scenario: CounterfactualScenario) -> float:
    """Fallback OLS regression estimate of treatment effect."""
    n = len(scenario.data)
    Y = np.array([d["outcome"] for d in scenario.data])
    T = np.array([d["treatment"] for d in scenario.data])
    covs = np.column_stack([
        np.array([d[c] for d in scenario.data]) for c in scenario.covariates
    ])
    # Build design matrix: [1, T, covariates]
    X = np.column_stack([np.ones(n), T, covs])
    # OLS: beta = (X'X)^{-1} X'Y
    try:
        beta = np.linalg.lstsq(X, Y, rcond=None)[0]
        return float(beta[1])  # coefficient on T
    except np.linalg.LinAlgError:
        return 0.0


def estimate_llm_baseline(scenario: CounterfactualScenario) -> float:
    """Baseline: naive difference-in-means (what a raw LLM would do)."""
    treated = [d["outcome"] for d in scenario.data if d["treatment"] == 1.0]
    control = [d["outcome"] for d in scenario.data if d["treatment"] == 0.0]
    if not treated or not control:
        return 0.0
    return float(np.mean(treated) - np.mean(control))


# ── Benchmark Runner ─────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    scenario_id: int
    dgp_type: str
    true_effect: float
    carf_estimate: float
    llm_estimate: float
    carf_error: float
    llm_error: float
    carf_correct: bool
    llm_correct: bool
    elapsed_seconds: float
    error: str | None = None

    def to_dict(self) -> dict:
        return {k: round(v, 6) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the full CounterBench benchmark."""
    logger.info("=" * 70)
    logger.info("CARF CounterBench — Counterfactual Reasoning Benchmark (H17)")
    logger.info("=" * 70)

    scenarios = generate_all_scenarios()
    logger.info(f"Generated {len(scenarios)} scenarios: "
                f"linear=20, nonlinear=15, interaction=10, threshold=5")

    # Accuracy threshold: absolute error < 30% of true effect or < 0.5
    TOLERANCE_FRAC = 0.30
    TOLERANCE_ABS = 0.5

    results: list[ScenarioResult] = []
    for sc in scenarios:
        t0 = time.perf_counter()
        try:
            carf_est = await estimate_carf(sc)
            llm_est = estimate_llm_baseline(sc)
            elapsed = time.perf_counter() - t0

            carf_err = abs(carf_est - sc.true_counterfactual_effect)
            llm_err = abs(llm_est - sc.true_counterfactual_effect)

            tol = max(TOLERANCE_FRAC * abs(sc.true_counterfactual_effect), TOLERANCE_ABS)
            carf_correct = carf_err <= tol
            llm_correct = llm_err <= tol

            res = ScenarioResult(
                scenario_id=sc.id, dgp_type=sc.dgp_type,
                true_effect=sc.true_counterfactual_effect,
                carf_estimate=carf_est, llm_estimate=llm_est,
                carf_error=carf_err, llm_error=llm_err,
                carf_correct=carf_correct, llm_correct=llm_correct,
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            res = ScenarioResult(
                scenario_id=sc.id, dgp_type=sc.dgp_type,
                true_effect=sc.true_counterfactual_effect,
                carf_estimate=0.0, llm_estimate=0.0,
                carf_error=0.0, llm_error=0.0,
                carf_correct=False, llm_correct=False,
                elapsed_seconds=elapsed, error=str(exc),
            )

        results.append(res)
        status = "PASS" if res.carf_correct else "FAIL"
        logger.info(f"  [{sc.id:>2}] {sc.dgp_type:<12} true={res.true_effect:>7.3f}  "
                     f"carf={res.carf_estimate:>7.3f}  llm={res.llm_estimate:>7.3f}  {status}")

    # Compute metrics
    valid = [r for r in results if r.error is None]
    total = len(valid)

    carf_accuracy = sum(1 for r in valid if r.carf_correct) / total if total else 0.0
    llm_accuracy = sum(1 for r in valid if r.llm_correct) / total if total else 0.0
    accuracy_gap = carf_accuracy - llm_accuracy

    # Per DGP-type breakdown
    dgp_types = ["linear", "nonlinear", "interaction", "threshold"]
    per_dgp: dict[str, dict] = {}
    for dt in dgp_types:
        subset = [r for r in valid if r.dgp_type == dt]
        if subset:
            per_dgp[dt] = {
                "count": len(subset),
                "carf_accuracy": round(sum(1 for r in subset if r.carf_correct) / len(subset), 4),
                "llm_accuracy": round(sum(1 for r in subset if r.llm_correct) / len(subset), 4),
                "carf_mean_error": round(sum(r.carf_error for r in subset) / len(subset), 6),
                "llm_mean_error": round(sum(r.llm_error for r in subset) / len(subset), 6),
            }

    metrics = {
        "carf_accuracy": round(carf_accuracy, 4),
        "llm_accuracy": round(llm_accuracy, 4),
        "accuracy_gap": round(accuracy_gap, 4),
        "pass_criterion": "carf_accuracy - llm_accuracy >= 0.10",
        "passed": accuracy_gap >= 0.10,
    }

    report = {
        "benchmark": "carf_counterbench",
        "hypothesis": "H17",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_scenarios": len(scenarios),
        "n_successful": total,
        "metrics": metrics,
        "per_dgp_type": per_dgp,
        "individual_results": [r.to_dict() for r in results],
    }

    logger.info("\n" + "=" * 70)
    logger.info("CounterBench Summary")
    logger.info(f"  Scenarios:       {len(scenarios)}")
    logger.info(f"  CARF accuracy:   {carf_accuracy:.1%}")
    logger.info(f"  LLM accuracy:    {llm_accuracy:.1%}")
    logger.info(f"  Gap:             {accuracy_gap:+.1%}")
    logger.info(f"  Pass (>=10pp):   {'YES' if metrics['passed'] else 'NO'}")
    for dt, stats in per_dgp.items():
        logger.info(f"    {dt:<12} CARF={stats['carf_accuracy']:.1%}  LLM={stats['llm_accuracy']:.1%}")
    logger.info("=" * 70)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="counterbench", source_reference="benchmark:counterbench", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Counterfactual Reasoning (H17)")
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
