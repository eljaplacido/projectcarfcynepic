# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Plateau Detection (H42).

Hypothesis H42: "Plateau detection identifies convergence within
5 epochs of <0.5% improvement."

Five realistic scenarios model DistilBERT fine-tuning accuracy curves
and verify that the RouterRetrainingService correctly identifies
plateaus, regressions, and ongoing improvement.

Usage:
    python benchmarks/technical/monitoring/benchmark_plateau_detection.py
    python benchmarks/technical/monitoring/benchmark_plateau_detection.py -o results.json
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.plateau_detection")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Realistic training curves (modeled on DistilBERT fine-tuning)
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Normal Training Curve",
        "description": (
            "Classic DistilBERT fine-tuning on domain classification: rapid "
            "early gains tapering to <0.5% improvement by epoch 8. "
            "Plateau detection should fire at epoch 8."
        ),
        "accuracy_curve": [0.60, 0.72, 0.81, 0.86, 0.89, 0.91, 0.92, 0.924, 0.926, 0.927],
        "expect_plateau": True,
        "expect_regression": False,
        "plateau_epoch_range": (7, 10),  # 1-indexed; acceptable detection window
    },
    {
        "name": "Quick Convergence",
        "description": (
            "Pre-trained model already near optimal: converges by epoch 5. "
            "Three consecutive sub-0.5% epochs trigger plateau detection."
        ),
        "accuracy_curve": [0.85, 0.89, 0.91, 0.912, 0.913, 0.9135],
        "expect_plateau": True,
        "expect_regression": False,
        "plateau_epoch_range": (4, 6),
    },
    {
        "name": "Regression",
        "description": (
            "Overfitting scenario: accuracy rises then drops at epoch 4. "
            "Regression should be detected, not plateau."
        ),
        "accuracy_curve": [0.85, 0.88, 0.91, 0.87],
        "expect_plateau": False,
        "expect_regression": True,
        "plateau_epoch_range": None,
    },
    {
        "name": "Oscillating",
        "description": (
            "Unstable training with learning rate too high: accuracy "
            "oscillates without converging. No plateau should be reported."
        ),
        "accuracy_curve": [0.80, 0.85, 0.83, 0.86, 0.84, 0.87],
        "expect_plateau": False,
        "expect_regression": False,  # individual drops are small
        "plateau_epoch_range": None,
    },
    {
        "name": "Steady Improvement",
        "description": (
            "Consistently improving model (data augmentation expanding "
            "the training set). No plateau detected."
        ),
        "accuracy_curve": [0.70, 0.75, 0.80, 0.85, 0.90],
        "expect_plateau": False,
        "expect_regression": False,
        "plateau_epoch_range": None,
    },
]


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


def _run_scenario(
    accuracy_curve: list[float],
) -> dict[str, Any]:
    """Feed an accuracy curve into RouterRetrainingService and record results."""
    from src.services.router_retraining_service import RouterRetrainingService

    service = RouterRetrainingService()

    epoch_results: list[dict[str, Any]] = []
    plateau_detected_at: int | None = None
    regression_detected_at: int | None = None

    for epoch_idx, accuracy in enumerate(accuracy_curve, start=1):
        service.record_accuracy(accuracy, epoch=epoch_idx)
        result = service.check_convergence()

        epoch_entry = {
            "epoch": epoch_idx,
            "accuracy": accuracy,
            "accuracy_delta": result.accuracy_delta,
            "plateau_detected": result.plateau_detected,
            "regressed": result.regressed,
            "converged": result.converged,
            "recommendation": result.recommendation,
        }
        epoch_results.append(epoch_entry)

        if result.plateau_detected and plateau_detected_at is None:
            plateau_detected_at = epoch_idx
        if result.regressed and regression_detected_at is None:
            regression_detected_at = epoch_idx

    return {
        "total_epochs": len(accuracy_curve),
        "plateau_detected": plateau_detected_at is not None,
        "plateau_detected_at": plateau_detected_at,
        "regression_detected": regression_detected_at is not None,
        "regression_detected_at": regression_detected_at,
        "epoch_results": epoch_results,
    }


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Execute all five plateau detection scenarios and compute metrics."""
    logger.info("=== CARF Plateau Detection Benchmark (H42) ===")

    scenario_results: list[dict[str, Any]] = []
    plateau_correct = 0
    plateau_total = 0
    regression_correct = 0
    regression_total = 0
    false_plateau_count = 0
    no_plateau_expected_count = 0

    for idx, scenario_def in enumerate(SCENARIOS):
        logger.info("  Scenario %d: %s", idx + 1, scenario_def["name"])
        t0 = time.perf_counter()

        result = _run_scenario(scenario_def["accuracy_curve"])
        elapsed_ms = (time.perf_counter() - t0) * 1000

        expect_plateau = scenario_def["expect_plateau"]
        expect_regression = scenario_def["expect_regression"]
        detected_plateau = result["plateau_detected"]
        detected_regression = result["regression_detected"]

        # Plateau accuracy
        if expect_plateau:
            plateau_total += 1
            # Check that plateau was detected within the acceptable window
            epoch_range = scenario_def.get("plateau_epoch_range")
            if detected_plateau:
                if epoch_range:
                    lo, hi = epoch_range
                    within_window = lo <= result["plateau_detected_at"] <= hi
                    if within_window:
                        plateau_correct += 1
                else:
                    plateau_correct += 1
        else:
            no_plateau_expected_count += 1
            if detected_plateau:
                false_plateau_count += 1

        # Regression accuracy
        if expect_regression:
            regression_total += 1
            if detected_regression:
                regression_correct += 1

        correct = (
            (expect_plateau == detected_plateau or (expect_plateau and detected_plateau))
            and (expect_regression == detected_regression or not expect_regression)
        )

        result_entry = {
            "scenario": scenario_def["name"],
            "description": scenario_def["description"],
            "accuracy_curve": scenario_def["accuracy_curve"],
            "expected_plateau": expect_plateau,
            "expected_regression": expect_regression,
            "detected_plateau": detected_plateau,
            "detected_plateau_at": result["plateau_detected_at"],
            "detected_regression": detected_regression,
            "detected_regression_at": result["regression_detected_at"],
            "correct": correct,
            "elapsed_ms": round(elapsed_ms, 2),
            "epoch_details": result["epoch_results"],
        }
        scenario_results.append(result_entry)

        tag = "OK" if correct else "FAIL"
        logger.info(
            "    plateau: expected=%s detected=%s (at epoch %s)  "
            "regression: expected=%s detected=%s  [%s] (%.1fms)",
            expect_plateau, detected_plateau, result["plateau_detected_at"],
            expect_regression, detected_regression, tag, elapsed_ms,
        )

    # Aggregate metrics
    plateau_detection_accuracy = (
        plateau_correct / plateau_total if plateau_total else 1.0
    )
    regression_detection_accuracy = (
        regression_correct / regression_total if regression_total else 1.0
    )
    false_plateau_rate = (
        false_plateau_count / no_plateau_expected_count
        if no_plateau_expected_count
        else 0.0
    )

    report: dict[str, Any] = {
        "benchmark": "carf_plateau_detection",
        "hypothesis": "H42",
        "claim": "Plateau detection identifies convergence within 5 epochs of <0.5% improvement",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(SCENARIOS),
        "plateau_detection_accuracy": round(plateau_detection_accuracy, 4),
        "regression_detection_accuracy": round(regression_detection_accuracy, 4),
        "false_plateau_rate": round(false_plateau_rate, 4),
        "plateau_correct": plateau_correct,
        "plateau_total": plateau_total,
        "regression_correct": regression_correct,
        "regression_total": regression_total,
        "false_plateau_count": false_plateau_count,
        "scenario_results": scenario_results,
        "pass": (
            plateau_detection_accuracy >= 0.90
            and regression_detection_accuracy >= 0.90
            and false_plateau_rate <= 0.10
        ),
    }

    logger.info("")
    logger.info("  Plateau Detection Accuracy:    %.2f%%", plateau_detection_accuracy * 100)
    logger.info("  Regression Detection Accuracy: %.2f%%", regression_detection_accuracy * 100)
    logger.info("  False Plateau Rate:            %.2f%%", false_plateau_rate * 100)
    logger.info("  PASS: %s", report["pass"])

    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(
        report,
        benchmark_id="plateau_detection",
        source_reference="benchmark:plateau_detection",
        benchmark_config={"script": __file__},
        dataset_context={
            "dataset_profile": "synthetic_distilbert_training_curves",
            "data_source": "modeled_finetuning_accuracy",
            "total_epochs_across_scenarios": sum(
                len(s["accuracy_curve"]) for s in SCENARIOS
            ),
        },
        sample_context={"total_scenarios": len(SCENARIOS)},
    )

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info("Results written to %s", out)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark CARF Plateau Detection (H42)")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
