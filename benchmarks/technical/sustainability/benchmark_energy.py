"""Benchmark CARF Energy Profiling per Pipeline Path (H29).

Measures wall-clock execution time as a proxy for energy consumption across
the three primary Cynefin domain paths:

  - Clear:       simple lookup / factual queries
  - Complicated:  causal inference queries
  - Complex:      Bayesian / active-inference queries

For each domain 10 representative queries are executed and average execution
time is measured.  The benchmark verifies *energy proportionality*: simpler
paths should consume less compute (Clear < Complicated < Complex).

An estimated kWh figure is also computed using:
    kWh = time_seconds * TDP_watts / 3600 / 1000

Metrics:
  - energy_proportional: boolean (Clear avg < Complicated avg < Complex avg)
  - per-domain average latency and estimated kWh

Usage:
    python benchmarks/technical/sustainability/benchmark_energy.py
    python benchmarks/technical/sustainability/benchmark_energy.py -o results.json
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
logger = logging.getLogger("benchmark.energy")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"

# ── Constants ────────────────────────────────────────────────────────────

# Thermal Design Power estimate for a typical cloud CPU (watts).
# Used purely for kWh estimation; not a precise measure.
TDP_WATTS = 150.0

# ── Data Helpers ─────────────────────────────────────────────────────────


def _build_causal_data(
    n: int, ate: float, base: float, noise: float, seed: int,
) -> list[dict[str, float]]:
    """Build a simple confounded causal dataset."""
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    X2 = rng.normal(0, 1, n)
    prop = 1 / (1 + np.exp(-(0.5 * X1 - 0.3 * X2)))
    T = rng.binomial(1, prop, n).astype(float)
    Y = base + ate * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, noise, n)
    return [
        {"treatment": float(T[i]), "outcome": round(float(Y[i]), 2),
         "X1": round(float(X1[i]), 4), "X2": round(float(X2[i]), 4)}
        for i in range(n)
    ]


# ── Sample Queries ───────────────────────────────────────────────────────

rng_obs = np.random.default_rng(42)

DOMAIN_QUERIES: dict[str, list[dict[str, Any]]] = {
    "Clear": [
        {"query": "What is the current USD to EUR exchange rate?"},
        {"query": "How many kilowatt-hours are in a megawatt-hour?"},
        {"query": "What is the standard VAT rate in Germany?"},
        {"query": "Convert 100 miles to kilometers."},
        {"query": "What is the boiling point of water in Celsius?"},
        {"query": "How many days are in a leap year?"},
        {"query": "What is the ISO code for the United States dollar?"},
        {"query": "Define GDP in one sentence."},
        {"query": "What is the chemical formula for carbon dioxide?"},
        {"query": "How many bytes are in a kilobyte?"},
    ],
    "Complicated": [
        {"query": "How does marketing spend affect quarterly revenue?",
         "context": {"industry": "marketing", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, 150.0, 500.0, 50.0, seed=10)}}},
        {"query": "What is the causal effect of training hours on productivity?",
         "context": {"industry": "hr", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, 12.0, 40.0, 5.0, seed=20)}}},
        {"query": "Does supplier diversification reduce disruptions?",
         "context": {"industry": "supply_chain", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, -2.0, 5.0, 1.0, seed=30)}}},
        {"query": "Effect of remote work on employee retention?",
         "context": {"industry": "hr", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, 5.0, 80.0, 10.0, seed=40)}}},
        {"query": "Impact of pricing strategy on conversion rate?",
         "context": {"industry": "ecommerce", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, 0.03, 0.10, 0.02, seed=50)}}},
        {"query": "Does inventory buffer reduce stockout frequency?",
         "context": {"industry": "supply_chain", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, -1.5, 4.0, 1.0, seed=60)}}},
        {"query": "Effect of renewable energy adoption on operational cost?",
         "context": {"industry": "energy", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, -20.0, 100.0, 15.0, seed=70)}}},
        {"query": "Impact of safety training on workplace incidents?",
         "context": {"industry": "manufacturing", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, -3.0, 8.0, 2.0, seed=80)}}},
        {"query": "Does customer segmentation improve marketing ROI?",
         "context": {"industry": "marketing", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, 0.08, 0.15, 0.04, seed=90)}}},
        {"query": "Effect of warehouse automation on order fulfillment time?",
         "context": {"industry": "logistics", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome",
             "covariates": ["X1", "X2"],
             "data": _build_causal_data(200, -4.0, 24.0, 3.0, seed=100)}}},
    ],
    "Complex": [
        {"query": "Should we enter the Asian market given uncertain regulatory changes?",
         "context": {"industry": "fintech", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.08, 0.15, 30), 4).tolist()}}},
        {"query": "What strategy for climate adaptation in agriculture?",
         "context": {"industry": "agriculture", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(4.5, 0.8, 25), 4).tolist()}}},
        {"query": "How to allocate R&D budget under technological uncertainty?",
         "context": {"industry": "technology", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.12, 0.05, 20), 4).tolist()}}},
        {"query": "Optimal pricing under demand uncertainty?",
         "context": {"industry": "retail", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(45.0, 12.0, 30), 4).tolist()}}},
        {"query": "Investment portfolio rebalancing under macro uncertainty?",
         "context": {"industry": "finance", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.06, 0.10, 25), 4).tolist()}}},
        {"query": "Should we expand manufacturing capacity amid supply shocks?",
         "context": {"industry": "manufacturing", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(800, 150, 20), 4).tolist()}}},
        {"query": "Optimal staffing levels under seasonal demand uncertainty?",
         "context": {"industry": "hospitality", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(120, 30, 25), 4).tolist()}}},
        {"query": "How to position products in an emerging market with limited data?",
         "context": {"industry": "consumer_goods", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.25, 0.08, 15), 4).tolist()}}},
        {"query": "Risk assessment for a new pharmaceutical compound?",
         "context": {"industry": "pharma", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.65, 0.12, 20), 4).tolist()}}},
        {"query": "Should we adopt a new AI model given uncertain performance gains?",
         "context": {"industry": "technology", "bayesian_inference": {
             "observations": np.round(rng_obs.normal(0.03, 0.01, 20), 4).tolist()}}},
    ],
}


# ── Measurement ──────────────────────────────────────────────────────────

async def measure_query(query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a single CARF pipeline query and return timing info."""
    try:
        from src.workflows.graph import run_carf
        t0 = time.perf_counter()
        final_state = await run_carf(user_input=query, context=context or {})
        elapsed = time.perf_counter() - t0
        return {
            "query": query[:80],
            "elapsed_seconds": round(elapsed, 6),
            "domain": final_state.cynefin_domain.value,
            "error": None,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "query": query[:80],
            "elapsed_seconds": round(elapsed, 6),
            "domain": "ERROR",
            "error": str(exc),
        }


def estimate_kwh(seconds: float, tdp_watts: float = TDP_WATTS) -> float:
    """Estimate energy consumption from wall-clock time and TDP."""
    return seconds * tdp_watts / 3600.0 / 1000.0


# ── Benchmark ────────────────────────────────────────────────────────────

async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run energy profiling benchmark across Cynefin domains."""
    logger.info("=" * 70)
    logger.info("CARF Energy Profiling Benchmark (H29)")
    logger.info("=" * 70)

    domain_results: dict[str, list[dict[str, Any]]] = {}

    for domain in ["Clear", "Complicated", "Complex"]:
        logger.info(f"\n--- Domain: {domain} ({len(DOMAIN_QUERIES[domain])} queries) ---")
        domain_results[domain] = []

        for item in DOMAIN_QUERIES[domain]:
            res = await measure_query(item["query"], item.get("context"))
            domain_results[domain].append(res)
            if res["error"]:
                logger.warning(f"  [{domain}] ERROR: {res['error'][:80]}")
            else:
                logger.info(
                    f"  [{domain}] {res['elapsed_seconds']:.3f}s  "
                    f"({estimate_kwh(res['elapsed_seconds']):.8f} kWh)"
                )

    # Compute per-domain stats
    domain_stats: dict[str, dict[str, Any]] = {}
    domain_avgs: dict[str, float] = {}

    for domain, results in domain_results.items():
        times = [r["elapsed_seconds"] for r in results if r["error"] is None]
        if times:
            avg_time = float(np.mean(times))
            avg_kwh = estimate_kwh(avg_time)
        else:
            avg_time = 0.0
            avg_kwh = 0.0

        domain_avgs[domain] = avg_time
        domain_stats[domain] = {
            "n_queries": len(results),
            "n_successful": len(times),
            "avg_seconds": round(avg_time, 6),
            "min_seconds": round(float(np.min(times)), 6) if times else 0.0,
            "max_seconds": round(float(np.max(times)), 6) if times else 0.0,
            "std_seconds": round(float(np.std(times)), 6) if times else 0.0,
            "avg_estimated_kwh": round(avg_kwh, 10),
            "total_estimated_kwh": round(estimate_kwh(sum(times)), 10) if times else 0.0,
        }

    # Energy proportionality check
    clear_avg = domain_avgs.get("Clear", 0.0)
    complicated_avg = domain_avgs.get("Complicated", 0.0)
    complex_avg = domain_avgs.get("Complex", 0.0)
    energy_proportional = clear_avg < complicated_avg < complex_avg

    report: dict[str, Any] = {
        "benchmark": "carf_energy_profiling",
        "hypothesis": "H29",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tdp_watts": TDP_WATTS,
        "metrics": {
            "energy_proportional": energy_proportional,
            "clear_avg_seconds": round(clear_avg, 6),
            "complicated_avg_seconds": round(complicated_avg, 6),
            "complex_avg_seconds": round(complex_avg, 6),
            "clear_avg_kwh": round(estimate_kwh(clear_avg), 10),
            "complicated_avg_kwh": round(estimate_kwh(complicated_avg), 10),
            "complex_avg_kwh": round(estimate_kwh(complex_avg), 10),
        },
        "domain_stats": domain_stats,
        "individual_results": {
            domain: results for domain, results in domain_results.items()
        },
    }

    logger.info("\n" + "=" * 70)
    logger.info("  Energy Proportionality Check:")
    logger.info(f"    Clear avg:       {clear_avg:.4f}s  ({estimate_kwh(clear_avg):.8f} kWh)")
    logger.info(f"    Complicated avg: {complicated_avg:.4f}s  ({estimate_kwh(complicated_avg):.8f} kWh)")
    logger.info(f"    Complex avg:     {complex_avg:.4f}s  ({estimate_kwh(complex_avg):.8f} kWh)")
    logger.info(f"    Proportional:    {'PASSED' if energy_proportional else 'FAILED'}")
    logger.info("=" * 70)

    from benchmarks import finalize_benchmark_report

    report = finalize_benchmark_report(report, benchmark_id="energy", source_reference="benchmark:energy", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Energy Profiling (H29)")
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
