"""Benchmark CARF Causal Inference Engine against synthetic and realistic DGPs.

Metrics:
  - ATE MSE (Mean Squared Error between estimated and true ATE)
  - ATE Bias (signed difference)
  - CI Coverage at 95% and 90% confidence levels
  - Refutation Pass Rate
  - Heterogeneous Treatment Effect robustness

Test cases span 3 synthetic baselines and 5 industry-specific realistic
data-generating processes with confounded treatment assignment.

Usage:
    python benchmarks/technical/causal/benchmark_causal.py
    python benchmarks/technical/causal/benchmark_causal.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.causal")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Utility ──────────────────────────────────────────────────────────────

def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(z >= 0, 1 / (1 + np.exp(-z)), np.exp(z) / (1 + np.exp(z)))


# ── Synthetic Baseline DGPs ──────────────────────────────────────────────

def _generate_linear_dgp(n: int = 500, seed: int = 42) -> tuple[list[dict], float]:
    """Linear DGP: Y = 2 + 3*T + 1.5*X1 + 0.5*X2 + noise. True ATE = 3.0."""
    rng = np.random.default_rng(seed)
    X1, X2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    prop = _sigmoid(0.5 * X1 - 0.3 * X2)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 2.0 + 3.0 * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, 0.5, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "X2": float(X2[i])} for i in range(n)]
    return data, 3.0


def _generate_nonlinear_dgp(n: int = 500, seed: int = 123) -> tuple[list[dict], float]:
    """Nonlinear DGP: True ATE = 2.5."""
    rng = np.random.default_rng(seed)
    X1, X2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    prop = _sigmoid(0.3 * X1**2 - 0.2 * X2)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 1.0 + 2.5 * T + 0.8 * X1**2 - 0.3 * X2 + rng.normal(0, 0.8, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "X2": float(X2[i])} for i in range(n)]
    return data, 2.5


def _generate_null_dgp(n: int = 500, seed: int = 456) -> tuple[list[dict], float]:
    """Null DGP: True ATE = 0.0."""
    rng = np.random.default_rng(seed)
    X1, X2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    prop = _sigmoid(0.4 * X1)
    T = rng.binomial(1, prop, n).astype(float)
    Y = 1.0 + 2.0 * X1 + rng.normal(0, 0.5, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "X2": float(X2[i])} for i in range(n)]
    return data, 0.0


# ── Industry-Specific Realistic DGPs ─────────────────────────────────────

def _generate_supply_chain_dgp(n: int = 500, seed: int = 100) -> tuple[list[dict], float, list[str]]:
    """Supply-chain resilience. Treatment: diversified sourcing. True ATE: -8.5 days."""
    rng = np.random.default_rng(seed)
    company_revenue = rng.lognormal(mean=10, sigma=1.0, size=n)
    region_risk = rng.uniform(0.1, 1.0, n)
    inventory_buffer = rng.exponential(scale=20, size=n)
    logit_ps = -1.0 + 0.0003 * company_revenue + 1.2 * region_risk - 0.01 * inventory_buffer
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = 20.0 - 8.5 * T - 0.003 * company_revenue + 5.0 * region_risk + 0.1 * inventory_buffer + rng.normal(0, 3.0, n)
    covariates = ["company_revenue", "region_risk", "inventory_buffer"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "company_revenue": float(company_revenue[i]), "region_risk": float(region_risk[i]),
             "inventory_buffer": float(inventory_buffer[i])} for i in range(n)]
    return data, -8.5, covariates


def _generate_healthcare_dgp(n: int = 800, seed: int = 200) -> tuple[list[dict], float, list[str]]:
    """Healthcare treatment effect. True ATE: -5.2 days recovery."""
    rng = np.random.default_rng(seed)
    patient_age = rng.normal(55, 15, n).clip(18, 95)
    severity = rng.integers(1, 6, size=n).astype(float)
    comorbidity = rng.poisson(1.5, n).astype(float)
    logit_ps = -2.0 + 0.02 * patient_age + 0.4 * severity + 0.3 * comorbidity
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = 10.0 + 0.3 * patient_age + 4.0 * severity + 2.0 * comorbidity - 5.2 * T + rng.normal(0, 2.5, n)
    covariates = ["patient_age", "severity", "comorbidity"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "patient_age": float(patient_age[i]), "severity": float(severity[i]),
             "comorbidity": float(comorbidity[i])} for i in range(n)]
    return data, -5.2, covariates


def _generate_marketing_dgp(n: int = 600, seed: int = 300) -> tuple[list[dict], float, list[str]]:
    """Marketing spend ROI. True ATE: 0.045 (4.5pp conversion lift)."""
    rng = np.random.default_rng(seed)
    brand_awareness = rng.beta(2, 5, n)
    market_competition = rng.beta(5, 2, n)
    season_quarter = rng.integers(1, 5, size=n).astype(float)
    season_effect = np.where(season_quarter == 4, 0.03, np.where(season_quarter == 2, 0.01, 0.0))
    logit_ps = -0.5 + 2.0 * brand_awareness - 1.5 * market_competition + 0.1 * season_quarter
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = np.clip(0.02 + 0.045 * T + 0.10 * brand_awareness + (-0.05) * market_competition + season_effect + rng.normal(0, 0.02, n), 0.0, 1.0)
    covariates = ["brand_awareness", "market_competition", "season_quarter"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "brand_awareness": float(brand_awareness[i]), "market_competition": float(market_competition[i]),
             "season_quarter": float(season_quarter[i])} for i in range(n)]
    return data, 0.045, covariates


def _generate_sustainability_dgp(n: int = 400, seed: int = 400) -> tuple[list[dict], float, list[str]]:
    """Sustainability programme. True ATE: -45.0 tonnes emissions."""
    rng = np.random.default_rng(seed)
    facility_size = rng.lognormal(mean=8, sigma=0.5, size=n)
    production_volume = rng.lognormal(mean=5, sigma=0.8, size=n)
    renewable_pct = rng.beta(2, 5, n) * 100
    logit_ps = -1.5 + 0.0001 * facility_size + 0.0002 * production_volume - 0.03 * renewable_pct
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = 200.0 + 0.01 * facility_size + 0.5 * production_volume - 1.5 * renewable_pct + (-45.0) * T + rng.normal(0, 15.0, n)
    covariates = ["facility_size", "production_volume", "renewable_pct"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "facility_size": float(facility_size[i]), "production_volume": float(production_volume[i]),
             "renewable_pct": float(renewable_pct[i])} for i in range(n)]
    return data, -45.0, covariates


def _generate_education_dgp(n: int = 700, seed: int = 500) -> tuple[list[dict], float, list[str]]:
    """Education intervention. True ATE: 7.8 test score points."""
    rng = np.random.default_rng(seed)
    prior_gpa = rng.normal(2.5, 0.7, n).clip(0, 4.0)
    household_income_k = rng.lognormal(mean=3.8, sigma=0.6, size=n)
    school_quality = rng.uniform(0.3, 1.0, n)
    logit_ps = 0.5 - 1.0 * prior_gpa + 0.01 * household_income_k + 0.8 * school_quality
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = np.clip(30.0 + 7.8 * T + 10.0 * prior_gpa + 0.05 * household_income_k + 5.0 * school_quality + rng.normal(0, 5.0, n), 0.0, 100.0)
    covariates = ["prior_gpa", "household_income_k", "school_quality"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "prior_gpa": float(prior_gpa[i]), "household_income_k": float(household_income_k[i]),
             "school_quality": float(school_quality[i])} for i in range(n)]
    return data, 7.8, covariates


# ── Heterogeneous Treatment Effect DGP ───────────────────────────────────

def _generate_heterogeneous_dgp(n: int = 800, seed: int = 777) -> tuple[list[dict], float, list[str], dict[str, float]]:
    """DGP with treatment-effect heterogeneity by age subgroup.
    young (age<35): ATE=4.0, middle (35-55): ATE=8.0, senior (>=55): ATE=12.0.
    """
    rng = np.random.default_rng(seed)
    age = rng.normal(45, 15, n).clip(18, 85)
    income_k = rng.lognormal(3.5, 0.5, n)
    health_index = rng.beta(5, 2, n)
    subgroup_ate = np.where(age < 35, 4.0, np.where(age < 55, 8.0, 12.0))
    logit_ps = -0.5 + 0.01 * age - 0.005 * income_k + 1.0 * health_index
    T = rng.binomial(1, _sigmoid(logit_ps), n).astype(float)
    Y = 20.0 + subgroup_ate * T + 0.1 * age + 0.02 * income_k + 10.0 * health_index + rng.normal(0, 3.0, n)
    population_ate = float(np.mean(subgroup_ate))
    covariates = ["age", "income_k", "health_index"]
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "age": float(age[i]), "income_k": float(income_k[i]),
             "health_index": float(health_index[i])} for i in range(n)]
    subgroup_ates = {"young_lt35": 4.0, "middle_35_55": 8.0, "senior_gte55": 12.0, "population_ate": population_ate}
    return data, population_ate, covariates, subgroup_ates


# ── Data-classes ─────────────────────────────────────────────────────────

@dataclass
class CausalTestCase:
    name: str
    data: list[dict]
    true_ate: float
    treatment: str = "treatment"
    outcome: str = "outcome"
    covariates: list[str] = field(default_factory=lambda: ["X1", "X2"])
    category: str = "synthetic"
    subgroup_ates: dict[str, float] | None = None


@dataclass
class CausalTestResult:
    name: str
    true_ate: float
    category: str = "synthetic"
    estimated_ate: float = 0.0
    bias: float = 0.0
    mse: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    ci_covers_true: bool = False
    ci_lower_90: float = 0.0
    ci_upper_90: float = 0.0
    ci_covers_true_90: bool = False
    refutation_results: dict[str, bool] = field(default_factory=dict)
    refutation_pass_rate: float = 0.0
    elapsed_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {k: round(v, 6) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


def _rescale_ci(ci_lo_95: float, ci_hi_95: float, est: float) -> tuple[float, float]:
    """Approximate 90% CI from 95% CI (z=1.645/1.96 scale factor)."""
    scale = 1.645 / 1.96
    half_95 = (ci_hi_95 - ci_lo_95) / 2.0
    half_90 = half_95 * scale
    return est - half_90, est + half_90


async def run_single(tc: CausalTestCase) -> CausalTestResult:
    """Run a single causal benchmark."""
    t0 = time.perf_counter()
    try:
        from src.services.causal import (
            CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig,
        )
        engine = CausalInferenceEngine(neo4j_service=None)
        hypothesis = CausalHypothesis(
            treatment=tc.treatment, outcome=tc.outcome,
            mechanism=f"Benchmark: {tc.name}", confounders=tc.covariates,
        )
        config = CausalEstimationConfig(
            data=tc.data, treatment=tc.treatment, outcome=tc.outcome,
            covariates=tc.covariates, method_name="backdoor.linear_regression",
        )
        result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
        elapsed = time.perf_counter() - t0

        est = result.effect_estimate
        bias = est - tc.true_ate
        ci_lo, ci_hi = result.confidence_interval
        ci_lo_90, ci_hi_90 = _rescale_ci(ci_lo, ci_hi, est)
        refs = result.refutation_results or {}
        ref_rate = sum(1 for v in refs.values() if v) / len(refs) if refs else 0.0

        return CausalTestResult(
            name=tc.name, true_ate=tc.true_ate, category=tc.category,
            estimated_ate=est, bias=bias, mse=bias**2,
            ci_lower=ci_lo, ci_upper=ci_hi,
            ci_covers_true=ci_lo <= tc.true_ate <= ci_hi,
            ci_lower_90=ci_lo_90, ci_upper_90=ci_hi_90,
            ci_covers_true_90=ci_lo_90 <= tc.true_ate <= ci_hi_90,
            refutation_results=refs, refutation_pass_rate=ref_rate,
            elapsed_seconds=elapsed,
        )
    except Exception as exc:
        return CausalTestResult(
            name=tc.name, true_ate=tc.true_ate, category=tc.category,
            elapsed_seconds=time.perf_counter() - t0, error=str(exc),
        )


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run all causal benchmarks."""
    logger.info("CARF Causal Inference Benchmark (synthetic + industry + heterogeneous)")

    # Build test cases
    test_cases: list[CausalTestCase] = []

    for gen_fn, name in [(_generate_linear_dgp, "synthetic_linear"),
                          (_generate_nonlinear_dgp, "synthetic_nonlinear"),
                          (_generate_null_dgp, "synthetic_null")]:
        data, ate = gen_fn()
        test_cases.append(CausalTestCase(name=name, data=data, true_ate=ate, category="synthetic"))

    for gen_fn, name in [(_generate_supply_chain_dgp, "industry_supply_chain"),
                          (_generate_healthcare_dgp, "industry_healthcare"),
                          (_generate_marketing_dgp, "industry_marketing_roi"),
                          (_generate_sustainability_dgp, "industry_sustainability"),
                          (_generate_education_dgp, "industry_education")]:
        data, ate, covs = gen_fn()
        test_cases.append(CausalTestCase(name=name, data=data, true_ate=ate, covariates=covs, category="industry"))

    hte_data, hte_ate, hte_covs, hte_subgroups = _generate_heterogeneous_dgp()
    test_cases.append(CausalTestCase(
        name="heterogeneous_treatment_effect", data=hte_data, true_ate=hte_ate,
        covariates=hte_covs, category="heterogeneous", subgroup_ates=hte_subgroups,
    ))

    results = []
    for tc in test_cases:
        logger.info(f"  Running: {tc.name} (category={tc.category}, true ATE={tc.true_ate})")
        res = await run_single(tc)
        results.append(res)
        if res.error:
            logger.error(f"    ERROR: {res.error}")
        else:
            logger.info(f"    ATE={res.estimated_ate:.4f} bias={res.bias:.4f} MSE={res.mse:.6f} "
                         f"CI95=[{res.ci_lower:.4f},{res.ci_upper:.4f}] covers={res.ci_covers_true} "
                         f"CI90=[{res.ci_lower_90:.4f},{res.ci_upper_90:.4f}] covers90={res.ci_covers_true_90}")

    valid = [r for r in results if r.error is None]
    n = len(valid)

    def _agg(subset: list[CausalTestResult]) -> dict[str, Any]:
        ns = len(subset)
        if ns == 0:
            return {}
        return {
            "n": ns,
            "mse": round(sum(r.mse for r in subset) / ns, 6),
            "mean_abs_bias": round(sum(abs(r.bias) for r in subset) / ns, 6),
            "ci_coverage_95": round(sum(1 for r in subset if r.ci_covers_true) / ns, 4),
            "ci_coverage_90": round(sum(1 for r in subset if r.ci_covers_true_90) / ns, 4),
            "mean_refutation_pass_rate": round(sum(r.refutation_pass_rate for r in subset) / ns, 4),
        }

    report = {
        "benchmark": "carf_causal_inference",
        "version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_test_cases": len(test_cases), "n_successful": n,
        "aggregate_metrics": {
            "all": _agg(valid),
            "synthetic": _agg([r for r in valid if r.category == "synthetic"]),
            "industry": _agg([r for r in valid if r.category == "industry"]),
            "heterogeneous": _agg([r for r in valid if r.category == "heterogeneous"]),
        },
        "test_results": [r.to_dict() for r in results],
    }

    logger.info("=== Aggregate ===")
    for label, agg in report["aggregate_metrics"].items():
        if agg:
            logger.info(f"  {label}: {json.dumps(agg)}")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Causal Inference")
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
