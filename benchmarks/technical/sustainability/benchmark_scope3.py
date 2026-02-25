# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Scope 3 Emission Attribution Accuracy (H30).

Generates 20 synthetic EPA-style emission records with known causal factors
and attribution weights.  Each record contains:

  - facility_id, emission_tonnes, energy_kwh, transport_km, waste_tonnes
  - Known ground-truth attribution weights for energy, transport, and waste

The benchmark tests whether CARF's causal analysis correctly attributes
emissions to the dominant source for each facility.  In test mode the causal
pipeline is simulated by running a linear regression and checking if the
estimated coefficients agree directionally with the known weights.

Metrics:
  - estimate_accuracy >= 0.85 (fraction of facilities where dominant source
    is correctly identified)

Usage:
    python benchmarks/technical/sustainability/benchmark_scope3.py
    python benchmarks/technical/sustainability/benchmark_scope3.py -o results.json
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
logger = logging.getLogger("benchmark.scope3")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Synthetic Data Generation ────────────────────────────────────────────

def generate_emission_records(
    n: int = 20, seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, float]]]:
    """Generate synthetic EPA-style emission records with known attribution.

    Returns:
        records: list of dicts with facility data
        ground_truth: list of dicts with true attribution weights per facility
    """
    rng = np.random.default_rng(seed)

    records: list[dict[str, Any]] = []
    ground_truth: list[dict[str, float]] = []

    for i in range(n):
        facility_id = f"FAC-{i + 1:03d}"

        # True attribution weights for this facility (sum to ~1.0)
        w_energy = rng.uniform(0.1, 0.7)
        w_transport = rng.uniform(0.1, 0.7)
        w_waste = rng.uniform(0.05, 0.3)
        total_w = w_energy + w_transport + w_waste
        w_energy /= total_w
        w_transport /= total_w
        w_waste /= total_w

        # Generate features
        energy_kwh = rng.uniform(50_000, 500_000)
        transport_km = rng.uniform(1_000, 100_000)
        waste_tonnes = rng.uniform(10, 500)

        # Emission driven by weighted combination + noise
        base_emission = (
            w_energy * (energy_kwh / 1000.0)       # scale to comparable range
            + w_transport * (transport_km / 100.0)
            + w_waste * (waste_tonnes * 2.0)
        )
        noise = rng.normal(0, base_emission * 0.05)  # 5% noise
        emission_tonnes = max(0.0, base_emission + noise)

        records.append({
            "facility_id": facility_id,
            "emission_tonnes": round(float(emission_tonnes), 2),
            "energy_kwh": round(float(energy_kwh), 2),
            "transport_km": round(float(transport_km), 2),
            "waste_tonnes": round(float(waste_tonnes), 2),
        })

        # Determine dominant source
        weights = {"energy": w_energy, "transport": w_transport, "waste": w_waste}
        dominant = max(weights, key=weights.get)  # type: ignore[arg-type]

        ground_truth.append({
            "facility_id": facility_id,
            "w_energy": round(float(w_energy), 4),
            "w_transport": round(float(w_transport), 4),
            "w_waste": round(float(w_waste), 4),
            "dominant_source": dominant,
        })

    return records, ground_truth


# ── Causal Attribution ───────────────────────────────────────────────────

async def attribute_emissions(records: list[dict[str, Any]]) -> dict[str, str]:
    """Run CARF causal service to attribute emissions, or simulate if unavailable.

    Returns dict mapping facility_id -> predicted dominant source.
    """
    # Prepare data for causal analysis
    # Treatment variables are energy, transport, waste; outcome is emission
    data_for_causal = []
    for rec in records:
        data_for_causal.append({
            "outcome": rec["emission_tonnes"],
            "energy": rec["energy_kwh"] / 1000.0,    # normalise
            "transport": rec["transport_km"] / 100.0,
            "waste": rec["waste_tonnes"] * 2.0,
        })

    try:
        from src.services.causal import (
            CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig,
        )

        engine = CausalInferenceEngine(neo4j_service=None)
        source_effects: dict[str, float] = {}

        for source_var in ["energy", "transport", "waste"]:
            covariates = [v for v in ["energy", "transport", "waste"] if v != source_var]
            hypothesis = CausalHypothesis(
                treatment=source_var, outcome="outcome",
                mechanism=f"Scope 3 attribution: {source_var} -> emissions",
                confounders=covariates,
            )
            config = CausalEstimationConfig(
                data=data_for_causal, treatment=source_var, outcome="outcome",
                covariates=covariates,
                method_name="backdoor.linear_regression",
            )
            result = await engine.estimate_effect(
                hypothesis=hypothesis, estimation_config=config,
            )
            source_effects[source_var] = abs(result.effect_estimate)

        # For each facility, attribute to the source with the highest per-unit effect
        # weighted by that facility's feature value
        attributions: dict[str, str] = {}
        for rec in records:
            fid = rec["facility_id"]
            scores = {
                "energy": source_effects.get("energy", 0.0) * (rec["energy_kwh"] / 1000.0),
                "transport": source_effects.get("transport", 0.0) * (rec["transport_km"] / 100.0),
                "waste": source_effects.get("waste", 0.0) * (rec["waste_tonnes"] * 2.0),
            }
            attributions[fid] = max(scores, key=scores.get)  # type: ignore[arg-type]

        return attributions

    except Exception as exc:
        logger.warning(f"Causal service unavailable ({exc}); using OLS simulation.")

        # Fallback: simple OLS regression to estimate coefficients
        Y = np.array([d["outcome"] for d in data_for_causal])
        X = np.column_stack([
            [d["energy"] for d in data_for_causal],
            [d["transport"] for d in data_for_causal],
            [d["waste"] for d in data_for_causal],
        ])
        # Add intercept
        X_int = np.column_stack([np.ones(len(Y)), X])
        try:
            beta = np.linalg.lstsq(X_int, Y, rcond=None)[0]
        except np.linalg.LinAlgError:
            beta = np.zeros(4)

        coefs = {"energy": abs(beta[1]), "transport": abs(beta[2]), "waste": abs(beta[3])}

        attributions = {}
        for rec in records:
            fid = rec["facility_id"]
            scores = {
                "energy": coefs["energy"] * (rec["energy_kwh"] / 1000.0),
                "transport": coefs["transport"] * (rec["transport_km"] / 100.0),
                "waste": coefs["waste"] * (rec["waste_tonnes"] * 2.0),
            }
            attributions[fid] = max(scores, key=scores.get)  # type: ignore[arg-type]

        return attributions


# ── Benchmark ────────────────────────────────────────────────────────────

async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run scope 3 emission attribution benchmark."""
    logger.info("=" * 70)
    logger.info("CARF Scope 3 Emission Attribution Benchmark (H30)")
    logger.info("=" * 70)

    t0 = time.perf_counter()
    records, ground_truth = generate_emission_records(n=20, seed=42)
    attributions = await attribute_emissions(records)
    elapsed = time.perf_counter() - t0

    # Evaluate accuracy
    individual_results: list[dict[str, Any]] = []
    correct = 0

    for gt in ground_truth:
        fid = gt["facility_id"]
        predicted = attributions.get(fid, "unknown")
        expected = gt["dominant_source"]
        is_correct = predicted == expected
        if is_correct:
            correct += 1

        individual_results.append({
            "facility_id": fid,
            "expected_dominant": expected,
            "predicted_dominant": predicted,
            "correct": is_correct,
            "true_weights": {
                "energy": gt["w_energy"],
                "transport": gt["w_transport"],
                "waste": gt["w_waste"],
            },
        })

        status = "OK" if is_correct else "MISS"
        logger.info(
            f"  {fid}: expected={expected:<10} predicted={predicted:<10} [{status}]"
        )

    n_total = len(ground_truth)
    accuracy = correct / max(n_total, 1)

    report: dict[str, Any] = {
        "benchmark": "carf_scope3_attribution",
        "hypothesis": "H30",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_facilities": n_total,
        "elapsed_seconds": round(elapsed, 4),
        "metrics": {
            "estimate_accuracy": round(accuracy, 4),
            "accuracy_target": 0.85,
            "accuracy_passed": accuracy >= 0.85,
            "n_correct": correct,
            "n_total": n_total,
        },
        "individual_results": individual_results,
    }

    logger.info("\n" + "=" * 70)
    logger.info(f"  Accuracy: {accuracy:.0%}  ({correct}/{n_total} facilities)")
    logger.info(f"  Target: >= 85%  |  {'PASSED' if accuracy >= 0.85 else 'FAILED'}")
    logger.info("=" * 70)

    from benchmarks import finalize_benchmark_report

    report = finalize_benchmark_report(report, benchmark_id="scope3", source_reference="benchmark:scope3", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CARF Scope 3 Emission Attribution (H30)",
    )
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
