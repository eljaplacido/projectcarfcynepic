"""Benchmark ChimeraOracle vs DoWhy full pipeline.

Measures H8: ChimeraOracle >= 10x faster with < 20% accuracy loss.

Metrics:
  - Speed ratio (DoWhy time / Oracle time)
  - Accuracy loss (|Oracle ATE - DoWhy ATE| / |DoWhy ATE|)
  - Both absolute ATE values and CIs

Usage:
    python benchmarks/technical/chimera/benchmark_oracle.py
    python benchmarks/technical/chimera/benchmark_oracle.py -o results.json
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
logger = logging.getLogger("benchmark.oracle")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _generate_benchmark_data(n: int = 1000, seed: int = 42) -> tuple[list[dict], float]:
    """Generate synthetic data for Oracle vs DoWhy comparison."""
    rng = np.random.default_rng(seed)
    X1, X2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    prop = 1 / (1 + np.exp(-(0.5 * X1 - 0.3 * X2)))
    T = rng.binomial(1, prop, n).astype(float)
    Y = 2.0 + 3.0 * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, 0.5, n)
    data = [{"treatment": float(T[i]), "outcome": float(Y[i]),
             "X1": float(X1[i]), "X2": float(X2[i])} for i in range(n)]
    return data, 3.0


async def run_dowhy_estimation(data: list[dict]) -> tuple[float, tuple[float, float], float]:
    """Run full DoWhy estimation. Returns (ate, ci, elapsed_ms)."""
    from src.services.causal import CausalInferenceEngine, CausalHypothesis, CausalEstimationConfig

    engine = CausalInferenceEngine(neo4j_service=None)
    hypothesis = CausalHypothesis(
        treatment="treatment", outcome="outcome",
        mechanism="benchmark", confounders=["X1", "X2"],
    )
    config = CausalEstimationConfig(
        data=data, treatment="treatment", outcome="outcome",
        covariates=["X1", "X2"], method_name="backdoor.linear_regression",
    )

    t0 = time.perf_counter()
    result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return result.effect_estimate, result.confidence_interval, elapsed_ms


def run_oracle_prediction(scenario_id: str, context: dict) -> tuple[float, tuple[float, float], float]:
    """Run ChimeraOracle prediction. Returns (ate, ci, elapsed_ms)."""
    from src.services.chimera_oracle import get_oracle_engine

    oracle = get_oracle_engine()
    t0 = time.perf_counter()
    pred = oracle.predict_effect(scenario_id, context)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return pred.effect_estimate, tuple(pred.confidence_interval), elapsed_ms


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run Oracle vs DoWhy comparison benchmark."""
    logger.info("CARF ChimeraOracle vs DoWhy Benchmark")

    data, true_ate = _generate_benchmark_data()
    n_runs = 5

    # Run DoWhy multiple times
    dowhy_ates, dowhy_times = [], []
    for i in range(n_runs):
        try:
            ate, ci, elapsed = await run_dowhy_estimation(data)
            dowhy_ates.append(ate)
            dowhy_times.append(elapsed)
            logger.info(f"  DoWhy run {i+1}: ATE={ate:.4f} in {elapsed:.0f}ms")
        except Exception as exc:
            logger.error(f"  DoWhy run {i+1} failed: {exc}")

    # Try Oracle (may not have a trained model)
    oracle_ates, oracle_times = [], []
    oracle_available = False
    tmp_csv = None
    try:
        import tempfile
        from src.services.chimera_oracle import get_oracle_engine
        oracle = get_oracle_engine()

        # Train on benchmark data if no model exists
        scenario_id = "benchmark_linear"
        if not oracle.has_model(scenario_id):
            logger.info("  Training Oracle model for benchmark...")
            # Write data to temp CSV (train_on_scenario requires CSV path)
            import csv
            tmp_csv = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline=""
            )
            writer = csv.DictWriter(tmp_csv, fieldnames=["treatment", "outcome", "X1", "X2"])
            writer.writeheader()
            writer.writerows(data)
            tmp_csv.close()

            await oracle.train_on_scenario(
                scenario_id=scenario_id,
                csv_path=tmp_csv.name,
                treatment="treatment",
                outcome="outcome",
                covariates=["X1", "X2"],
            )

        oracle_available = True
        for i in range(n_runs):
            try:
                ate, ci, elapsed = run_oracle_prediction(
                    scenario_id, {"X1": 0.0, "X2": 0.0}
                )
                oracle_ates.append(ate)
                oracle_times.append(elapsed)
                logger.info(f"  Oracle run {i+1}: ATE={ate:.4f} in {elapsed:.0f}ms")
            except Exception as exc:
                logger.error(f"  Oracle run {i+1} failed: {exc}")
    except Exception as exc:
        logger.warning(f"  Oracle not available: {exc}")
    finally:
        if tmp_csv is not None:
            import os
            try:
                os.unlink(tmp_csv.name)
            except OSError:
                pass

    # Compute comparison metrics
    speed_ratio = None
    accuracy_loss = None

    if dowhy_times and oracle_times:
        avg_dowhy = np.mean(dowhy_times)
        avg_oracle = np.mean(oracle_times)
        speed_ratio = avg_dowhy / max(avg_oracle, 0.001)

        avg_dowhy_ate = np.mean(dowhy_ates)
        avg_oracle_ate = np.mean(oracle_ates)
        if abs(avg_dowhy_ate) > 0.001:
            accuracy_loss = abs(avg_oracle_ate - avg_dowhy_ate) / abs(avg_dowhy_ate)

    report = {
        "benchmark": "chimera_oracle_vs_dowhy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "true_ate": true_ate,
        "oracle_available": oracle_available,
        "dowhy": {
            "n_runs": len(dowhy_ates),
            "mean_ate": round(float(np.mean(dowhy_ates)), 6) if dowhy_ates else None,
            "mean_latency_ms": round(float(np.mean(dowhy_times)), 2) if dowhy_times else None,
        },
        "oracle": {
            "n_runs": len(oracle_ates),
            "mean_ate": round(float(np.mean(oracle_ates)), 6) if oracle_ates else None,
            "mean_latency_ms": round(float(np.mean(oracle_times)), 2) if oracle_times else None,
        },
        "speed_ratio": round(speed_ratio, 2) if speed_ratio else None,
        "accuracy_loss_pct": round(accuracy_loss * 100, 2) if accuracy_loss is not None else None,
        "h8_passed": (speed_ratio is not None and speed_ratio >= 10.0
                      and accuracy_loss is not None and accuracy_loss < 0.20),
    }

    logger.info(f"\n  Speed Ratio: {speed_ratio:.1f}x" if speed_ratio else "\n  Speed Ratio: N/A")
    logger.info(f"  Accuracy Loss: {accuracy_loss*100:.1f}%" if accuracy_loss is not None else "  Accuracy Loss: N/A")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark Oracle vs DoWhy")
    parser.add_argument("-o", "--output", default=None)
    asyncio.run(run_benchmark(parser.parse_args().output))


if __name__ == "__main__":
    main()
