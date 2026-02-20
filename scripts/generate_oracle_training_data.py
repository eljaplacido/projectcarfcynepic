"""Generate training data and train ChimeraOracle models for H8 benchmark.

Produces 3 production-grade datasets with known ATEs, writes temp CSVs,
and calls ChimeraOracleEngine.train_on_scenario().

Datasets:
  benchmark_linear        — 1000 rows, ATE=3.0, covariates X1/X2
  supply_chain_benchmark  — 800 rows, ATE=-8.5, covariates region_risk/lead_time
  healthcare_benchmark    — 800 rows, ATE=-5.2, covariates age/severity

Usage:
    python scripts/generate_oracle_training_data.py
    python scripts/generate_oracle_training_data.py -o scripts/oracle_training_results.json
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("carf.oracle_training")


# ── Dataset Generators ────────────────────────────────────────────────────

def generate_benchmark_linear(n: int = 1000, seed: int = 42) -> tuple[list[dict], dict]:
    """Linear treatment effect dataset (true ATE = 3.0).

    Y = 2.0 + 3.0*T + 1.5*X1 + 0.5*X2 + noise
    """
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    X2 = rng.normal(0, 1, n)
    prop = 1 / (1 + np.exp(-(0.5 * X1 - 0.3 * X2)))
    T = rng.binomial(1, prop, n).astype(float)
    Y = 2.0 + 3.0 * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, 0.5, n)

    data = [
        {"treatment": float(T[i]), "outcome": float(Y[i]),
         "X1": float(X1[i]), "X2": float(X2[i])}
        for i in range(n)
    ]
    config = {
        "scenario_id": "benchmark_linear",
        "treatment": "treatment",
        "outcome": "outcome",
        "covariates": ["X1", "X2"],
        "true_ate": 3.0,
    }
    return data, config


def generate_supply_chain_benchmark(n: int = 800, seed: int = 100) -> tuple[list[dict], dict]:
    """Supply chain benchmark (true ATE ~ -8.5 disruptions).

    disruption_count = 30 - 8.5*diversified + 10*region_risk + 2*lead_time_weeks + noise
    """
    rng = np.random.default_rng(seed)
    region_risk = rng.uniform(0.1, 0.95, n)
    lead_time = rng.uniform(1, 8, n).round(1)
    # Confounded: riskier regions more likely to diversify
    div_prob = 0.3 + 0.4 * region_risk
    diversified = rng.binomial(1, div_prob, n).astype(float)
    disruptions = (
        30 - 8.5 * diversified + 10 * region_risk + 2 * lead_time
        + rng.normal(0, 2.5, n)
    ).clip(0, 60).round(1)

    data = [
        {"diversified": float(diversified[i]), "disruption_count": float(disruptions[i]),
         "region_risk": float(region_risk[i]), "lead_time": float(lead_time[i])}
        for i in range(n)
    ]
    config = {
        "scenario_id": "supply_chain_benchmark",
        "treatment": "diversified",
        "outcome": "disruption_count",
        "covariates": ["region_risk", "lead_time"],
        "true_ate": -8.5,
    }
    return data, config


def generate_healthcare_benchmark(n: int = 800, seed: int = 200) -> tuple[list[dict], dict]:
    """Healthcare benchmark (true ATE ~ -5.2 days recovery).

    recovery_days = 20 - 5.2*new_treatment + 0.15*age + 3*severity + noise
    """
    rng = np.random.default_rng(seed)
    age = rng.integers(25, 80, size=n).astype(float)
    severity = rng.uniform(1, 5, n).round(1)
    # Confounded: older/sicker patients more likely to get new treatment
    treat_prob = 0.3 + 0.003 * age + 0.05 * severity
    treat_prob = np.clip(treat_prob, 0.1, 0.9)
    new_treatment = rng.binomial(1, treat_prob, n).astype(float)
    recovery = (
        20 - 5.2 * new_treatment + 0.15 * age + 3 * severity
        + rng.normal(0, 2.0, n)
    ).clip(3, 50).round(1)

    data = [
        {"new_treatment": float(new_treatment[i]), "recovery_days": float(recovery[i]),
         "age": float(age[i]), "severity": float(severity[i])}
        for i in range(n)
    ]
    config = {
        "scenario_id": "healthcare_benchmark",
        "treatment": "new_treatment",
        "outcome": "recovery_days",
        "covariates": ["age", "severity"],
        "true_ate": -5.2,
    }
    return data, config


# ── Training Pipeline ─────────────────────────────────────────────────────

async def train_all(output_path: str | None = None) -> dict[str, Any]:
    """Generate datasets, write temp CSVs, and train oracle models."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    generators = [
        generate_benchmark_linear,
        generate_supply_chain_benchmark,
        generate_healthcare_benchmark,
    ]

    results = []
    for gen_fn in generators:
        data, config = gen_fn()
        scenario_id = config["scenario_id"]
        logger.info(f"Training '{scenario_id}' on {len(data)} rows (true ATE={config['true_ate']})")

        # Write to temp CSV
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(tmp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        tmp.close()

        try:
            result = await engine.train_on_scenario(
                scenario_id=scenario_id,
                csv_path=tmp.name,
                treatment=config["treatment"],
                outcome=config["outcome"],
                covariates=config["covariates"],
                n_estimators=100,
            )
            entry = {
                "scenario_id": scenario_id,
                "status": result.status,
                "n_samples": result.n_samples,
                "true_ate": config["true_ate"],
                "estimated_ate": result.average_treatment_effect,
                "effect_std": result.effect_std,
                "model_version": result.model_version,
                "model_path": result.model_path,
            }
            logger.info(
                f"  {scenario_id}: ATE={result.average_treatment_effect:.2f} "
                f"(true={config['true_ate']:.1f}), status={result.status}"
            )
        except Exception as e:
            entry = {
                "scenario_id": scenario_id,
                "status": "failed",
                "error": str(e),
            }
            logger.error(f"  {scenario_id} FAILED: {e}")
        finally:
            import os
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        results.append(entry)

    report = {
        "script": "generate_oracle_training_data",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models_trained": sum(1 for r in results if r.get("status") == "trained"),
        "models_failed": sum(1 for r in results if r.get("status") == "failed"),
        "available_scenarios": engine.get_available_scenarios(),
        "results": results,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results written to {out}")

    logger.info(
        f"\nTraining complete: {report['models_trained']} trained, "
        f"{report['models_failed']} failed"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate oracle training data and train models")
    parser.add_argument("-o", "--output", default=None, help="Output JSON path")
    args = parser.parse_args()
    asyncio.run(train_all(output_path=args.output))


if __name__ == "__main__":
    main()
