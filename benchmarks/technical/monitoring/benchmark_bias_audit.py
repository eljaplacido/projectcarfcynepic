# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Bias Audit (H41).

Hypothesis H41: "Memory bias detection sensitivity >= 90% for >10%
domain skew in 100+ entries."

Five realistic scenarios simulate accumulated agent memory with
varying bias patterns and verify that the BiasAuditor reliably
distinguishes biased from unbiased corpora.

Usage:
    python benchmarks/technical/monitoring/benchmark_bias_audit.py
    python benchmarks/technical/monitoring/benchmark_bias_audit.py -o results.json
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
logger = logging.getLogger("benchmark.bias_audit")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Realistic synthetic memory generation
# ---------------------------------------------------------------------------

DOMAINS = ["clear", "complicated", "complex", "chaotic", "disorder"]

# Realistic query templates per domain — modeled on actual enterprise queries
QUERY_TEMPLATES: dict[str, list[str]] = {
    "clear": [
        "What is the current exchange rate for USD/EUR?",
        "Look up the latest quarterly revenue for ACME Corp.",
        "Show me the regulatory filing deadline for Q3 2026.",
        "Retrieve the standard operating procedure for customer onboarding.",
        "What is the current inventory level for product SKU-4829?",
    ],
    "complicated": [
        "Analyze the causal impact of our pricing change on customer churn.",
        "Run a regression analysis on marketing spend vs lead conversion.",
        "Estimate the treatment effect of the new training program on productivity.",
        "What are the key drivers of supply chain delays in the EU region?",
        "Decompose revenue variance between volume, price, and mix effects.",
    ],
    "complex": [
        "How might emerging regulations affect our expansion strategy?",
        "Explore the systemic risks in our multi-tier supplier network.",
        "What feedback loops exist between customer satisfaction and retention?",
        "Model the interaction effects between our three concurrent initiatives.",
        "Assess the emergent patterns in employee turnover data.",
    ],
    "chaotic": [
        "Our primary data center is unreachable — what is the fallback plan?",
        "Breaking: major competitor just acquired our key supplier.",
        "Critical security breach detected in the payment processing system.",
        "Unexpected regulatory order to halt all EU operations immediately.",
        "Production line has failed with cascading downstream impacts.",
    ],
    "disorder": [
        "Something is wrong but we don't know what domain this falls into.",
        "Please just help us figure out what is going on.",
        "The situation is unclear — classify and route appropriately.",
        "We have conflicting signals from multiple dashboards.",
        "No one agrees on what category of problem this is.",
    ],
}


class _MockMemoryEntry:
    """Lightweight mock of MemoryEntry for bias audit testing."""

    def __init__(
        self,
        query: str,
        domain: str,
        quality_score: float | None = None,
        guardian_verdict: str | None = None,
    ) -> None:
        self.query = query
        self.domain = domain
        self.quality_score = quality_score
        self.guardian_verdict = guardian_verdict


class _MockMemoryStore:
    """Lightweight mock of AgentMemory for controlled scenarios."""

    def __init__(self, entries: list[_MockMemoryEntry]) -> None:
        self._entries = entries


class _MockAgentMemory:
    """Wraps _MockMemoryStore so BiasAuditor can access ._store._entries."""

    def __init__(self, entries: list[_MockMemoryEntry]) -> None:
        self._store = _MockMemoryStore(entries)


def _generate_entries(
    n: int,
    domain_distribution: dict[str, float],
    quality_fn: Any | None = None,
    verdict_fn: Any | None = None,
    rng: random.Random | None = None,
) -> list[_MockMemoryEntry]:
    """Generate realistic mock memory entries.

    Args:
        n: Number of entries to generate.
        domain_distribution: Probability distribution over DOMAINS.
        quality_fn: Optional callable(domain, rng) -> float for quality score.
        verdict_fn: Optional callable(domain, rng) -> str|None for verdicts.
        rng: Random number generator.
    """
    if rng is None:
        rng = random.Random(42)

    entries: list[_MockMemoryEntry] = []
    for _ in range(n):
        # Sample domain
        r = rng.random()
        cumulative = 0.0
        domain = DOMAINS[-1]
        for d, prob in domain_distribution.items():
            cumulative += prob
            if r <= cumulative:
                domain = d
                break

        # Pick a realistic query
        templates = QUERY_TEMPLATES.get(domain, QUERY_TEMPLATES["disorder"])
        query = rng.choice(templates)

        # Quality score
        quality = quality_fn(domain, rng) if quality_fn else rng.uniform(0.6, 0.9)

        # Guardian verdict
        verdict = verdict_fn(domain, rng) if verdict_fn else None

        entries.append(_MockMemoryEntry(
            query=query,
            domain=domain,
            quality_score=quality,
            guardian_verdict=verdict,
        ))

    return entries


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Balanced Research Lab",
        "description": (
            "100 entries, ~20% per domain, quality 0.6-0.9. "
            "No systematic bias should be detected."
        ),
        "expect_bias": False,
    },
    {
        "name": "Finance-Heavy Deployment",
        "description": (
            "200 entries, 65% Complicated (causal analysis dominates), "
            "rest distributed. Distribution bias expected."
        ),
        "expect_bias": True,
    },
    {
        "name": "Quality Gap",
        "description": (
            "150 entries, balanced domain distribution, but Complex domain "
            "avg quality 0.35-0.45 vs others 0.75-0.90. Quality bias expected."
        ),
        "expect_bias": True,
    },
    {
        "name": "Approval Disparity",
        "description": (
            "120 entries with Guardian verdicts. Chaotic domain 30% approval "
            "vs others 85%+. Verdict bias expected."
        ),
        "expect_bias": True,
    },
    {
        "name": "Clean Production System",
        "description": (
            "500 entries with realistic but non-systematic variation. "
            "No bias should be detected."
        ),
        "expect_bias": False,
    },
]


def _build_scenario_1(rng: random.Random) -> _MockAgentMemory:
    """Balanced research lab: ~20% per domain, quality 0.6-0.9."""
    balanced = {d: 0.20 for d in DOMAINS}
    entries = _generate_entries(100, balanced, rng=rng)
    return _MockAgentMemory(entries)


def _build_scenario_2(rng: random.Random) -> _MockAgentMemory:
    """Finance-heavy: 65% Complicated."""
    skewed = {
        "clear": 0.08,
        "complicated": 0.65,
        "complex": 0.12,
        "chaotic": 0.10,
        "disorder": 0.05,
    }
    entries = _generate_entries(200, skewed, rng=rng)
    return _MockAgentMemory(entries)


def _build_scenario_3(rng: random.Random) -> _MockAgentMemory:
    """Quality gap: balanced domains but Complex quality much lower."""
    balanced = {d: 0.20 for d in DOMAINS}

    def quality_fn(domain: str, r: random.Random) -> float:
        if domain == "complex":
            return r.uniform(0.30, 0.45)
        return r.uniform(0.75, 0.90)

    entries = _generate_entries(150, balanced, quality_fn=quality_fn, rng=rng)
    return _MockAgentMemory(entries)


def _build_scenario_4(rng: random.Random) -> _MockAgentMemory:
    """Approval disparity: Chaotic domain 30% approval vs 85%+ elsewhere."""
    balanced = {d: 0.20 for d in DOMAINS}

    def verdict_fn(domain: str, r: random.Random) -> str:
        if domain == "chaotic":
            return "approved" if r.random() < 0.30 else "rejected"
        return "approved" if r.random() < 0.88 else "rejected"

    entries = _generate_entries(120, balanced, verdict_fn=verdict_fn, rng=rng)
    return _MockAgentMemory(entries)


def _build_scenario_5(rng: random.Random) -> _MockAgentMemory:
    """Clean production: 500 entries, realistic but no systematic bias."""
    # Slight natural variation (not perfectly uniform, but not biased)
    natural = {
        "clear": 0.18,
        "complicated": 0.22,
        "complex": 0.21,
        "chaotic": 0.19,
        "disorder": 0.20,
    }

    def quality_fn(domain: str, r: random.Random) -> float:
        # Natural quality variation per domain (small spread)
        base = {"clear": 0.78, "complicated": 0.76, "complex": 0.74,
                "chaotic": 0.73, "disorder": 0.75}
        return r.gauss(base.get(domain, 0.75), 0.05)

    entries = _generate_entries(500, natural, quality_fn=quality_fn, rng=rng)
    return _MockAgentMemory(entries)


SCENARIO_BUILDERS = [
    _build_scenario_1,
    _build_scenario_2,
    _build_scenario_3,
    _build_scenario_4,
    _build_scenario_5,
]


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Execute all five bias audit scenarios and compute metrics."""
    logger.info("=== CARF Bias Audit Benchmark (H41) ===")

    from src.services.bias_auditor import BiasAuditor

    rng = random.Random(42)
    auditor = BiasAuditor(
        chi_squared_threshold=0.05,
        quality_disparity_threshold=0.20,
        approval_disparity_threshold=0.15,
    )

    scenario_results: list[dict[str, Any]] = []
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0

    for idx, (scenario_def, builder) in enumerate(zip(SCENARIOS, SCENARIO_BUILDERS)):
        logger.info("  Scenario %d: %s", idx + 1, scenario_def["name"])
        t0 = time.perf_counter()

        mock_memory = builder(rng)
        bias_report = auditor.audit(mock_memory)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        expect_bias = scenario_def["expect_bias"]
        detected = bias_report.overall_bias_detected

        if expect_bias and detected:
            true_positives += 1
        elif expect_bias and not detected:
            false_negatives += 1
        elif not expect_bias and not detected:
            true_negatives += 1
        elif not expect_bias and detected:
            false_positives += 1

        correct = (expect_bias == detected)
        result_entry = {
            "scenario": scenario_def["name"],
            "description": scenario_def["description"],
            "expected_bias": expect_bias,
            "detected_bias": detected,
            "correct": correct,
            "elapsed_ms": round(elapsed_ms, 2),
            "bias_report": {
                "total_entries": bias_report.total_entries,
                "distribution_biased": bias_report.distribution_biased,
                "quality_biased": bias_report.quality_biased,
                "approval_rate_disparity": bias_report.approval_rate_disparity,
                "quality_disparity": bias_report.quality_disparity,
                "chi_squared_statistic": bias_report.chi_squared_statistic,
                "chi_squared_p_value": bias_report.chi_squared_p_value,
                "findings": bias_report.findings,
            },
        }
        scenario_results.append(result_entry)

        tag = "OK" if correct else "FAIL"
        logger.info(
            "    expected_bias=%s detected=%s [%s] (%.1fms)",
            expect_bias, detected, tag, elapsed_ms,
        )
        if bias_report.findings:
            for finding in bias_report.findings:
                logger.info("      -> %s", finding)

    # Aggregate metrics
    total_positive_cases = true_positives + false_negatives
    total_negative_cases = true_negatives + false_positives

    bias_detection_accuracy = (
        (true_positives + true_negatives) / len(SCENARIOS) if SCENARIOS else 0.0
    )
    sensitivity = true_positives / total_positive_cases if total_positive_cases else 0.0
    false_alarm_rate = false_positives / total_negative_cases if total_negative_cases else 0.0
    detection_specificity = true_negatives / total_negative_cases if total_negative_cases else 0.0

    report: dict[str, Any] = {
        "benchmark": "carf_bias_audit",
        "hypothesis": "H41",
        "claim": "Memory bias detection sensitivity >= 90% for >10% domain skew in 100+ entries",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(SCENARIOS),
        "bias_detection_accuracy": round(bias_detection_accuracy, 4),
        "sensitivity": round(sensitivity, 4),
        "false_alarm_rate": round(false_alarm_rate, 4),
        "detection_specificity": round(detection_specificity, 4),
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "scenario_results": scenario_results,
        "pass": sensitivity >= 0.90 and detection_specificity >= 0.90,
    }

    logger.info("")
    logger.info("  Bias Detection Accuracy: %.2f%%", bias_detection_accuracy * 100)
    logger.info("  Sensitivity (TPR):       %.2f%%", sensitivity * 100)
    logger.info("  False Alarm Rate (FPR):  %.2f%%", false_alarm_rate * 100)
    logger.info("  Specificity (TNR):       %.2f%%", detection_specificity * 100)
    logger.info("  PASS: %s", report["pass"])

    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(
        report,
        benchmark_id="bias_audit",
        source_reference="benchmark:bias_audit",
        benchmark_config={"script": __file__},
        dataset_context={
            "dataset_profile": "synthetic_agent_memory_corpus",
            "data_source": "generated_memory_entries",
            "domains": DOMAINS,
            "total_entries_across_scenarios": sum(
                r["bias_report"]["total_entries"] for r in scenario_results
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
    parser = argparse.ArgumentParser(description="Benchmark CARF Bias Audit (H41)")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
