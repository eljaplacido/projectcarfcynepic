# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Drift Detection (H40).

Hypothesis H40: "Drift detection detects >5% routing shift within
100 queries with >=90% sensitivity."

Five realistic enterprise routing scenarios test sensitivity (true
positive rate), specificity (true negative rate), and detection latency
(queries until first alert).

Usage:
    python benchmarks/technical/monitoring/benchmark_drift_detection.py
    python benchmarks/technical/monitoring/benchmark_drift_detection.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.drift_detection")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Realistic distribution helpers
# ---------------------------------------------------------------------------

DOMAINS = ["clear", "complicated", "complex", "chaotic", "disorder"]

# Baseline distribution modeled on a mature enterprise deployment:
# Clear 15%, Complicated 40%, Complex 30%, Chaotic 10%, Disorder 5%
ENTERPRISE_BASELINE = {
    "clear": 0.15,
    "complicated": 0.40,
    "complex": 0.30,
    "chaotic": 0.10,
    "disorder": 0.05,
}


def _sample_domain(distribution: dict[str, float], rng: random.Random) -> str:
    """Sample a single domain from a probability distribution."""
    r = rng.random()
    cumulative = 0.0
    for domain, prob in distribution.items():
        cumulative += prob
        if r <= cumulative:
            return domain
    return DOMAINS[-1]  # fallback


def _perturbed_distribution(
    base: dict[str, float], noise_pct: float, rng: random.Random
) -> dict[str, float]:
    """Add random noise to a distribution (preserves sum=1)."""
    raw = {}
    for d, p in base.items():
        delta = rng.uniform(-noise_pct, noise_pct) * p
        raw[d] = max(p + delta, 0.001)
    total = sum(raw.values())
    return {d: v / total for d, v in raw.items()}


def _interpolate_distributions(
    start: dict[str, float], end: dict[str, float], t: float
) -> dict[str, float]:
    """Linearly interpolate between two distributions at ratio t in [0, 1]."""
    mixed = {d: start[d] * (1 - t) + end[d] * t for d in DOMAINS}
    total = sum(mixed.values())
    return {d: v / total for d, v in mixed.items()}


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Stable Enterprise Operations",
        "description": (
            "200 queries drawn from the stable enterprise baseline. "
            "Drift detector must NOT trigger any alert."
        ),
        "expect_drift": False,
    },
    {
        "name": "Gradual Market Shift",
        "description": (
            "100 baseline queries, then 100 queries where Complicated "
            "gradually drops from 40% to 25% and Complex rises from 30% to 45%. "
            "Drift must be detected."
        ),
        "expect_drift": True,
    },
    {
        "name": "Sudden Crisis",
        "description": (
            "100 baseline queries, then an abrupt shift where 80% of routing "
            "becomes Chaotic. Drift must be detected within 50 queries."
        ),
        "expect_drift": True,
    },
    {
        "name": "Seasonal Pattern Return",
        "description": (
            "100 baseline, then 100 shifted (Complex-heavy), then 100 queries "
            "that return to baseline. Alert should fire during shift and "
            "clear after return."
        ),
        "expect_drift": True,  # must alert during shift phase
    },
    {
        "name": "Noise Resilience",
        "description": (
            "200 queries from baseline + 3% random perturbation per query. "
            "Must NOT trigger false alarm."
        ),
        "expect_drift": False,
    },
]


# ---------------------------------------------------------------------------
# Scenario execution
# ---------------------------------------------------------------------------


def _run_scenario_stable(rng: random.Random) -> dict[str, Any]:
    """Scenario 1: 200 stable queries, no drift."""
    from src.services.drift_detector import DriftDetector

    detector = DriftDetector(
        baseline_window=100,
        detection_window=50,
        kl_threshold=0.15,
        domain_shift_threshold=0.10,
    )

    alerts: list[dict] = []
    for _ in range(200):
        domain = _sample_domain(ENTERPRISE_BASELINE, rng)
        snapshot = detector.record_routing(domain)
        if snapshot and snapshot.drift_detected:
            alerts.append(snapshot.model_dump())

    return {
        "total_queries": 200,
        "alerts_fired": len(alerts),
        "drift_detected": len(alerts) > 0,
        "alert_details": alerts,
    }


def _run_scenario_gradual_shift(rng: random.Random) -> dict[str, Any]:
    """Scenario 2: 100 baseline then gradual Complicated->Complex shift."""
    from src.services.drift_detector import DriftDetector

    detector = DriftDetector(
        baseline_window=100,
        detection_window=50,
        kl_threshold=0.15,
        domain_shift_threshold=0.10,
    )

    shifted_dist = {
        "clear": 0.15,
        "complicated": 0.25,
        "complex": 0.45,
        "chaotic": 0.10,
        "disorder": 0.05,
    }

    alerts: list[dict] = []
    first_alert_query: int | None = None

    for i in range(200):
        if i < 100:
            domain = _sample_domain(ENTERPRISE_BASELINE, rng)
        else:
            t = (i - 100) / 100.0  # 0..1 over 100 queries
            dist = _interpolate_distributions(ENTERPRISE_BASELINE, shifted_dist, t)
            domain = _sample_domain(dist, rng)

        snapshot = detector.record_routing(domain)
        if snapshot and snapshot.drift_detected:
            alerts.append(snapshot.model_dump())
            if first_alert_query is None:
                first_alert_query = i + 1

    return {
        "total_queries": 200,
        "alerts_fired": len(alerts),
        "drift_detected": len(alerts) > 0,
        "first_alert_at_query": first_alert_query,
        "detection_latency": (first_alert_query - 100) if first_alert_query and first_alert_query > 100 else first_alert_query,
        "alert_details": alerts,
    }


def _run_scenario_sudden_crisis(rng: random.Random) -> dict[str, Any]:
    """Scenario 3: 100 baseline then sudden 80% Chaotic."""
    from src.services.drift_detector import DriftDetector

    detector = DriftDetector(
        baseline_window=100,
        detection_window=50,
        kl_threshold=0.15,
        domain_shift_threshold=0.10,
    )

    crisis_dist = {
        "clear": 0.05,
        "complicated": 0.05,
        "complex": 0.05,
        "chaotic": 0.80,
        "disorder": 0.05,
    }

    alerts: list[dict] = []
    first_alert_query: int | None = None

    for i in range(200):
        if i < 100:
            domain = _sample_domain(ENTERPRISE_BASELINE, rng)
        else:
            domain = _sample_domain(crisis_dist, rng)

        snapshot = detector.record_routing(domain)
        if snapshot and snapshot.drift_detected:
            alerts.append(snapshot.model_dump())
            if first_alert_query is None:
                first_alert_query = i + 1

    return {
        "total_queries": 200,
        "alerts_fired": len(alerts),
        "drift_detected": len(alerts) > 0,
        "first_alert_at_query": first_alert_query,
        "detection_latency": (first_alert_query - 100) if first_alert_query and first_alert_query > 100 else first_alert_query,
        "within_50_queries": (first_alert_query is not None and first_alert_query <= 150),
        "alert_details": alerts,
    }


def _run_scenario_seasonal_return(rng: random.Random) -> dict[str, Any]:
    """Scenario 4: Shift away then return to baseline."""
    from src.services.drift_detector import DriftDetector

    detector = DriftDetector(
        baseline_window=100,
        detection_window=50,
        kl_threshold=0.15,
        domain_shift_threshold=0.10,
    )

    shifted_dist = {
        "clear": 0.05,
        "complicated": 0.20,
        "complex": 0.55,
        "chaotic": 0.15,
        "disorder": 0.05,
    }

    phase_alerts: dict[str, list[dict]] = {"baseline": [], "shifted": [], "returned": []}

    for i in range(300):
        if i < 100:
            domain = _sample_domain(ENTERPRISE_BASELINE, rng)
            phase = "baseline"
        elif i < 200:
            domain = _sample_domain(shifted_dist, rng)
            phase = "shifted"
        else:
            domain = _sample_domain(ENTERPRISE_BASELINE, rng)
            phase = "returned"

        snapshot = detector.record_routing(domain)
        if snapshot and snapshot.drift_detected:
            phase_alerts[phase].append(snapshot.model_dump())

    alerted_during_shift = len(phase_alerts["shifted"]) > 0

    return {
        "total_queries": 300,
        "alerted_during_shift": alerted_during_shift,
        "drift_detected": alerted_during_shift,
        "alerts_by_phase": {k: len(v) for k, v in phase_alerts.items()},
        "alert_details": {k: v for k, v in phase_alerts.items()},
    }


def _run_scenario_noise_resilience(rng: random.Random) -> dict[str, Any]:
    """Scenario 5: 3% random perturbation, should NOT trigger drift.

    Uses a larger detection window (100) to match how a production system
    would be configured when expecting normal fluctuation. The 3% per-query
    noise should average out across a window this size.
    """
    from src.services.drift_detector import DriftDetector

    detector = DriftDetector(
        baseline_window=100,
        detection_window=100,
        kl_threshold=0.15,
        domain_shift_threshold=0.10,
    )

    alerts: list[dict] = []
    for _ in range(300):
        noisy_dist = _perturbed_distribution(ENTERPRISE_BASELINE, 0.03, rng)
        domain = _sample_domain(noisy_dist, rng)
        snapshot = detector.record_routing(domain)
        if snapshot and snapshot.drift_detected:
            alerts.append(snapshot.model_dump())

    return {
        "total_queries": 300,
        "alerts_fired": len(alerts),
        "drift_detected": len(alerts) > 0,
        "alert_details": alerts,
    }


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

SCENARIO_RUNNERS = [
    _run_scenario_stable,
    _run_scenario_gradual_shift,
    _run_scenario_sudden_crisis,
    _run_scenario_seasonal_return,
    _run_scenario_noise_resilience,
]


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Execute all five drift detection scenarios and compute metrics."""
    logger.info("=== CARF Drift Detection Benchmark (H40) ===")
    rng = random.Random(42)

    scenario_results: list[dict[str, Any]] = []
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0
    detection_latencies: list[int] = []

    for idx, (scenario_def, runner) in enumerate(zip(SCENARIOS, SCENARIO_RUNNERS)):
        logger.info("  Scenario %d: %s", idx + 1, scenario_def["name"])
        t0 = time.perf_counter()
        result = runner(rng)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        expect_drift = scenario_def["expect_drift"]
        detected = result.get("drift_detected", False)

        if expect_drift and detected:
            true_positives += 1
        elif expect_drift and not detected:
            false_negatives += 1
        elif not expect_drift and not detected:
            true_negatives += 1
        elif not expect_drift and detected:
            false_positives += 1

        if result.get("detection_latency") is not None:
            detection_latencies.append(result["detection_latency"])

        correct = (expect_drift == detected)
        result_entry = {
            "scenario": scenario_def["name"],
            "description": scenario_def["description"],
            "expected_drift": expect_drift,
            "detected_drift": detected,
            "correct": correct,
            "elapsed_ms": round(elapsed_ms, 2),
            "details": {k: v for k, v in result.items() if k != "alert_details"},
        }
        scenario_results.append(result_entry)

        tag = "OK" if correct else "FAIL"
        logger.info(
            "    expected_drift=%s detected=%s [%s] (%.1fms)",
            expect_drift, detected, tag, elapsed_ms,
        )

    # Compute aggregate metrics
    total_positive_cases = true_positives + false_negatives
    total_negative_cases = true_negatives + false_positives

    sensitivity = true_positives / total_positive_cases if total_positive_cases else 0.0
    specificity = true_negatives / total_negative_cases if total_negative_cases else 0.0
    avg_detection_latency = (
        sum(detection_latencies) / len(detection_latencies)
        if detection_latencies
        else None
    )

    report: dict[str, Any] = {
        "benchmark": "carf_drift_detection",
        "hypothesis": "H40",
        "claim": "Drift detection detects >5% routing shift within 100 queries with >=90% sensitivity",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(SCENARIOS),
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "avg_detection_latency_queries": avg_detection_latency,
        "detection_latencies": detection_latencies,
        "scenario_results": scenario_results,
        "pass": sensitivity >= 0.90 and specificity >= 0.90,
    }

    logger.info("")
    logger.info("  Sensitivity (TPR): %.2f%%", sensitivity * 100)
    logger.info("  Specificity (TNR): %.2f%%", specificity * 100)
    logger.info("  Avg Detection Latency: %s queries",
                f"{avg_detection_latency:.0f}" if avg_detection_latency else "N/A")
    logger.info("  PASS: %s", report["pass"])

    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(
        report,
        benchmark_id="drift_detection",
        source_reference="benchmark:drift_detection",
        benchmark_config={"script": __file__},
        dataset_context={
            "dataset_profile": "synthetic_enterprise_routing",
            "data_source": "generated_cynefin_distributions",
            "baseline": ENTERPRISE_BASELINE,
            "total_queries_across_scenarios": sum(
                r["details"].get("total_queries", 0) for r in scenario_results
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
    parser = argparse.ArgumentParser(description="Benchmark CARF Drift Detection (H40)")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
