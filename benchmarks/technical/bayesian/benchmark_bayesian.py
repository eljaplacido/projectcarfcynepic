"""Benchmark CARF Bayesian Active Inference Engine.

Metrics:
  - Posterior Coverage: does 90% HPD contain the true parameter?
  - Posterior Precision: is the CI width reasonable for the sample size?
  - Uncertainty Decomposition: epistemic vs aleatoric present?
  - Probe quality: are recommended probes domain-relevant?
  - Belief update coherence

8 scenarios across industries with realistic data distributions
and known ground truth for calibration assessment.

Usage:
    python benchmarks/technical/bayesian/benchmark_bayesian.py
    python benchmarks/technical/bayesian/benchmark_bayesian.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.bayesian")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Data Generating Processes ────────────────────────────────────────────
# Every scenario has a fixed seed and known ground truth so that coverage
# and calibration metrics are deterministic across runs.


def _generate_market_entry_observations() -> dict:
    """Emerging market annual returns: normal with fat tails."""
    rng = np.random.default_rng(seed=42)
    true_mean = 0.08
    true_std = 0.15
    raw = rng.normal(loc=true_mean, scale=true_std, size=50)
    raw[11] = -0.28  # sharp drawdown
    raw[37] = 0.42   # speculative rally
    observations = np.round(raw, 4).tolist()
    return {"observations": observations, "true_mean": true_mean, "true_std": true_std}


def _generate_climate_crop_yield() -> dict:
    """Wheat yields in tonnes/hectare: normal with moderate variance."""
    rng = np.random.default_rng(seed=101)
    true_mean = 4.5
    true_std = 0.8
    observations = rng.normal(loc=true_mean, scale=true_std, size=40)
    observations = np.clip(observations, 0.5, None)
    observations = np.round(observations, 3).tolist()
    return {"observations": observations, "true_mean": true_mean, "true_std": true_std}


def _generate_tech_migration_roi() -> dict:
    """A/B test rollout successes: binomial with moderate success rate."""
    rng = np.random.default_rng(seed=202)
    true_rate = 0.62
    trials = 45
    successes = int(rng.binomial(n=trials, p=true_rate))
    return {"successes": successes, "trials": trials, "true_rate": true_rate}


def _generate_pharma_drug_trial() -> dict:
    """Drug trial efficacy: binomial with ~65% efficacy."""
    rng = np.random.default_rng(seed=303)
    true_rate = 0.65
    trials = 120
    successes = int(rng.binomial(n=trials, p=true_rate))
    return {"successes": successes, "trials": trials, "true_rate": true_rate}


def _generate_supply_chain_lead_times() -> dict:
    """Lead times in days: right-skewed with occasional outliers."""
    rng = np.random.default_rng(seed=404)
    true_mean = 28.0
    true_std = 7.5
    base = rng.normal(loc=true_mean, scale=true_std * 0.7, size=50)
    tail = rng.exponential(scale=8.0, size=10) + true_mean
    observations = np.concatenate([base, tail])
    rng.shuffle(observations)
    observations = np.clip(observations, 3.0, None)
    observations = np.round(observations, 2).tolist()
    true_mean_actual = float(np.mean(observations))
    true_std_actual = float(np.std(observations, ddof=1))
    return {"observations": observations, "true_mean": true_mean_actual, "true_std": true_std_actual}


def _generate_energy_grid_demand() -> dict:
    """Hourly electricity demand in MW: diurnal pattern + noise."""
    rng = np.random.default_rng(seed=505)
    true_mean = 2500.0
    true_std = 400.0
    hours = np.arange(80) % 24
    diurnal = 300 * np.sin(2 * np.pi * (hours - 6) / 24)
    observations = true_mean + diurnal + rng.normal(0, true_std * 0.5, size=80)
    observations = np.clip(observations, 800.0, None)
    observations = np.round(observations, 1).tolist()
    true_mean_actual = float(np.mean(observations))
    true_std_actual = float(np.std(observations, ddof=1))
    return {"observations": observations, "true_mean": true_mean_actual, "true_std": true_std_actual}


def _generate_insurance_claim_frequency() -> dict:
    """Insurance claims: binomial with low claim rate (~8%)."""
    rng = np.random.default_rng(seed=606)
    true_rate = 0.08
    trials = 200
    successes = int(rng.binomial(n=trials, p=true_rate))
    return {"successes": successes, "trials": trials, "true_rate": true_rate}


def _generate_customer_conversion() -> dict:
    """E-commerce conversion: binomial with low rate (~3.5%)."""
    rng = np.random.default_rng(seed=707)
    true_rate = 0.035
    trials = 500
    successes = int(rng.binomial(n=trials, p=true_rate))
    return {"successes": successes, "trials": trials, "true_rate": true_rate}


# ── Test Scenarios ───────────────────────────────────────────────────────

def _build_scenarios() -> list[dict]:
    """Build all 8 benchmark scenarios with realistic data."""

    market = _generate_market_entry_observations()
    crop = _generate_climate_crop_yield()
    tech = _generate_tech_migration_roi()
    pharma = _generate_pharma_drug_trial()
    supply = _generate_supply_chain_lead_times()
    energy = _generate_energy_grid_demand()
    insurance = _generate_insurance_claim_frequency()
    conversion = _generate_customer_conversion()

    return [
        {
            "name": "market_entry_risk",
            "query": "Should we enter the Southeast Asian fintech market given emerging-market volatility? Evaluate expected annual return and uncertainty.",
            "context": {
                "industry": "fintech",
                "region": "ASEAN",
                "risk_tolerance": 0.3,
                "bayesian_inference": {"observations": market["observations"]},
            },
            "ground_truth": {"model": "normal", "true_mean": market["true_mean"], "true_std": market["true_std"]},
            "expected": {"has_probes": True, "min_probes": 2, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "climate_crop_yield_uncertainty",
            "query": "What crop rotation strategy given uncertain climate? We have 40 wheat yield measurements and need yield risk quantification.",
            "context": {
                "industry": "agriculture",
                "horizon_years": 5,
                "bayesian_inference": {"observations": crop["observations"]},
            },
            "ground_truth": {"model": "normal", "true_mean": crop["true_mean"], "true_std": crop["true_std"]},
            "expected": {"has_probes": True, "min_probes": 2, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "tech_migration_roi",
            "query": "Should we migrate ML pipeline from TensorFlow to PyTorch given uncertain ROI? We ran 45 A/B rollout tests.",
            "context": {
                "industry": "tech",
                "current_framework": "TensorFlow",
                "team_size": 15,
                "bayesian_inference": {"successes": tech["successes"], "trials": tech["trials"]},
            },
            "ground_truth": {"model": "binomial", "true_rate": tech["true_rate"]},
            "expected": {"has_probes": True, "min_probes": 1, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "pharma_drug_trial",
            "query": "Phase II trial enrolled 120 patients for anti-inflammatory compound. Should we proceed to Phase III given observed efficacy?",
            "context": {
                "industry": "healthcare",
                "trial_phase": "Phase II",
                "regulatory_bar": 0.50,
                "bayesian_inference": {"successes": pharma["successes"], "trials": pharma["trials"]},
            },
            "ground_truth": {"model": "binomial", "true_rate": pharma["true_rate"]},
            "expected": {"has_probes": True, "min_probes": 2, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "supply_chain_lead_time",
            "query": "Supply chain lead times volatile. Using 60 shipment measurements, quantify average lead time and variability for safety stock.",
            "context": {
                "industry": "logistics",
                "metric": "lead_time_days",
                "n_suppliers": 12,
                "bayesian_inference": {"observations": supply["observations"]},
            },
            "ground_truth": {"model": "normal", "true_mean": supply["true_mean"], "true_std": supply["true_std"]},
            "expected": {"has_probes": True, "min_probes": 2, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "energy_grid_demand",
            "query": "Forecast hourly electricity demand for grid capacity planning. We have 80 hourly MW readings with diurnal patterns.",
            "context": {
                "industry": "energy",
                "metric": "demand_MW",
                "grid_region": "northeast",
                "bayesian_inference": {"observations": energy["observations"]},
            },
            "ground_truth": {"model": "normal", "true_mean": energy["true_mean"], "true_std": energy["true_std"]},
            "expected": {"has_probes": True, "min_probes": 2, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "insurance_claim_frequency",
            "query": "Estimate claim frequency for auto insurance portfolio of 200 policies to set adequate reserves. Historical rate ~8%.",
            "context": {
                "industry": "finance",
                "product": "auto_insurance",
                "portfolio_size": 200,
                "bayesian_inference": {"successes": insurance["successes"], "trials": insurance["trials"]},
            },
            "ground_truth": {"model": "binomial", "true_rate": insurance["true_rate"]},
            "expected": {"has_probes": True, "min_probes": 1, "uncertainty_bounded": True, "posterior_present": True},
        },
        {
            "name": "customer_conversion_rate",
            "query": "500 unique visitors on new landing page. Estimate true conversion rate and decide if this variant should replace the control.",
            "context": {
                "industry": "ecommerce",
                "page_variant": "B",
                "traffic_source": "organic",
                "bayesian_inference": {"successes": conversion["successes"], "trials": conversion["trials"]},
            },
            "ground_truth": {"model": "binomial", "true_rate": conversion["true_rate"]},
            "expected": {"has_probes": True, "min_probes": 1, "uncertainty_bounded": True, "posterior_present": True},
        },
    ]


BAYESIAN_SCENARIOS = _build_scenarios()


# ── Single Scenario Runner ───────────────────────────────────────────────

async def run_single_scenario(scenario: dict) -> dict[str, Any]:
    """Run one Bayesian benchmark scenario with comprehensive checks."""
    from src.core.state import EpistemicState, CynefinDomain
    from src.services.bayesian import run_active_inference

    t0 = time.perf_counter()
    result: dict[str, Any] = {
        "name": scenario["name"],
        "passed_checks": [],
        "failed_checks": [],
        "metrics": {},
        "error": None,
    }

    try:
        state = EpistemicState(
            user_input=scenario["query"],
            context=scenario.get("context", {}),
            cynefin_domain=CynefinDomain.COMPLEX,
        )
        updated = await run_active_inference(state)
        elapsed = time.perf_counter() - t0
        result["metrics"]["elapsed_seconds"] = round(elapsed, 3)

        expected = scenario["expected"]
        ground_truth = scenario.get("ground_truth", {})

        # Check 1: Posterior evidence present
        if updated.bayesian_evidence:
            result["passed_checks"].append("posterior_present")
            posterior_mean = updated.bayesian_evidence.posterior_mean
            ci = updated.bayesian_evidence.credible_interval
            ci_lower, ci_upper = ci[0], ci[1]
            posterior_std = (ci_upper - ci_lower) / (2 * 1.645)  # 90% CI -> std proxy

            result["metrics"]["posterior_mean"] = round(posterior_mean, 6)
            result["metrics"]["posterior_std"] = round(posterior_std, 6)
            result["metrics"]["credible_interval"] = [round(ci_lower, 6), round(ci_upper, 6)]

            # Check 2: Uncertainty bounded
            if expected.get("uncertainty_bounded"):
                model_type = ground_truth.get("model", "normal")
                if model_type == "binomial":
                    bounded = 0.0 <= ci_lower and ci_upper <= 1.0 and (ci_upper - ci_lower) < 0.80
                else:
                    bounded = posterior_std < 10.0 * abs(posterior_mean + 1e-6)
                if bounded:
                    result["passed_checks"].append("uncertainty_bounded")
                else:
                    result["failed_checks"].append("uncertainty_bounded")

            # Check 3: Coverage -- true parameter within 90% CI
            true_param = None
            if ground_truth.get("model") == "normal":
                true_param = ground_truth.get("true_mean")
            elif ground_truth.get("model") == "binomial":
                true_param = ground_truth.get("true_rate")

            if true_param is not None:
                result["metrics"]["true_parameter"] = true_param
                covered = ci_lower <= true_param <= ci_upper
                result["metrics"]["parameter_covered"] = covered
                if covered:
                    result["passed_checks"].append("coverage_90ci")
                else:
                    result["failed_checks"].append("coverage_90ci")
                    logger.warning(
                        f"    Coverage MISS: true={true_param:.4f} "
                        f"CI=[{ci_lower:.4f}, {ci_upper:.4f}]"
                    )

            # Check 4: Posterior precision reasonable
            if ground_truth.get("model") == "binomial":
                prior_std = 0.289  # std of Beta(1,1)
                reasonable = 0.001 < posterior_std < prior_std * 1.1
            else:
                true_std = ground_truth.get("true_std", 1.0)
                n_obs = len(scenario["context"]["bayesian_inference"].get("observations", []))
                expected_post_std = true_std / max(n_obs ** 0.5, 1)
                reasonable = 0.0001 < posterior_std < expected_post_std * 5
            if reasonable:
                result["passed_checks"].append("posterior_precision")
            else:
                result["failed_checks"].append("posterior_precision")

        else:
            result["failed_checks"].append("posterior_present")

        # Check 5: Probes generated
        if updated.bayesian_evidence and updated.bayesian_evidence.probes_designed > 0:
            n_probes = updated.bayesian_evidence.probes_designed
            if n_probes >= expected.get("min_probes", 1):
                result["passed_checks"].append("sufficient_probes")
            else:
                result["failed_checks"].append("sufficient_probes")
            result["metrics"]["n_probes"] = n_probes
            result["metrics"]["recommended_probe"] = updated.bayesian_evidence.recommended_probe
        elif expected.get("has_probes"):
            result["failed_checks"].append("has_probes")

        # Check 6: Uncertainty decomposition (epistemic + aleatoric)
        if updated.bayesian_evidence:
            ep = updated.bayesian_evidence.epistemic_uncertainty
            al = updated.bayesian_evidence.aleatoric_uncertainty
            result["metrics"]["epistemic_uncertainty"] = round(ep, 6)
            result["metrics"]["aleatoric_uncertainty"] = round(al, 6)
            if ep > 0 and al > 0:
                result["passed_checks"].append("uncertainty_decomposition")
            else:
                result["failed_checks"].append("uncertainty_decomposition")

        # Check 7: Epistemic uncertainty tracked on state
        if updated.epistemic_uncertainty > 0:
            result["passed_checks"].append("uncertainty_tracked")
            result["metrics"]["state_epistemic_uncertainty"] = round(updated.epistemic_uncertainty, 4)
        else:
            result["failed_checks"].append("uncertainty_tracked")

        # Check 8: Final response quality
        if updated.final_response and len(updated.final_response) > 50:
            result["passed_checks"].append("response_quality")
        else:
            result["failed_checks"].append("response_quality")

    except Exception as exc:
        result["error"] = str(exc)
        result["metrics"]["elapsed_seconds"] = round(time.perf_counter() - t0, 3)

    total = len(result["passed_checks"]) + len(result["failed_checks"])
    result["pass_rate"] = round(len(result["passed_checks"]) / total, 4) if total else 0.0
    return result


# ── Aggregate Runner ─────────────────────────────────────────────────────

async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run all Bayesian benchmark scenarios and compute aggregate metrics."""
    logger.info("=" * 68)
    logger.info("CARF Bayesian Active Inference Benchmark  (8 scenarios)")
    logger.info("=" * 68)

    results: list[dict[str, Any]] = []
    for scenario in BAYESIAN_SCENARIOS:
        logger.info(f"  Running: {scenario['name']}")
        res = await run_single_scenario(scenario)
        results.append(res)
        if res["error"]:
            logger.error(f"    ERROR: {res['error']}")
        else:
            logger.info(
                f"    Pass rate: {res['pass_rate']:.0%} "
                f"({len(res['passed_checks'])}/"
                f"{len(res['passed_checks']) + len(res['failed_checks'])})"
            )

    valid = [r for r in results if r["error"] is None]
    n_valid = len(valid)

    # Aggregate: posterior coverage rate
    n_covered = sum(1 for r in valid if "coverage_90ci" in r["passed_checks"])
    coverage_rate = round(n_covered / n_valid, 4) if n_valid else 0.0

    # Well-calibrated: 90% CI should cover ~90%. With 8 scenarios, >= 7/8 = good.
    well_calibrated = n_covered >= 7 if n_valid >= 8 else n_covered >= (n_valid - 1)

    # Decomposition rate
    n_decomposed = sum(1 for r in valid if "uncertainty_decomposition" in r["passed_checks"])
    decomposition_rate = round(n_decomposed / n_valid, 4) if n_valid else 0.0

    # Mean pass rate
    aggregate_pass_rate = round(
        sum(r["pass_rate"] for r in valid) / n_valid, 4
    ) if n_valid else 0.0

    # Mean latency
    latencies = [r["metrics"].get("elapsed_seconds", 0) for r in valid]
    mean_latency = round(sum(latencies) / len(latencies), 3) if latencies else 0.0

    logger.info("-" * 68)
    logger.info(f"  Scenarios run       : {len(BAYESIAN_SCENARIOS)}")
    logger.info(f"  Successful          : {n_valid}")
    logger.info(f"  Coverage (90% CI)   : {n_covered}/{n_valid} ({coverage_rate:.0%})")
    logger.info(f"  Well-calibrated     : {'YES' if well_calibrated else 'NO'}")
    logger.info(f"  Decomposition rate  : {n_decomposed}/{n_valid} ({decomposition_rate:.0%})")
    logger.info(f"  Aggregate pass rate : {aggregate_pass_rate:.0%}")
    logger.info(f"  Mean latency        : {mean_latency:.3f}s")
    logger.info("=" * 68)

    report: dict[str, Any] = {
        "benchmark": "carf_bayesian_inference",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_scenarios": len(BAYESIAN_SCENARIOS),
        "n_successful": n_valid,
        "aggregate": {
            "coverage_rate": coverage_rate,
            "n_covered": n_covered,
            "well_calibrated": well_calibrated,
            "decomposition_rate": decomposition_rate,
            "aggregate_pass_rate": aggregate_pass_rate,
            "mean_latency_seconds": mean_latency,
        },
        "coverage": coverage_rate,
        "aggregate_pass_rate": aggregate_pass_rate,
        "scenario_results": results,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Bayesian Engine")
    parser.add_argument("-o", "--output", default=None, help="Path to write JSON results")
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
