# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF UX — System Usability Scale (SUS) Framework (H31).

Implements the standard Brooke (1996) SUS questionnaire across 8 CARF task
scenarios.  Each scenario carries simulated expert-evaluation SUS responses
(1-5 Likert scale for 10 questions).  The standard SUS scoring formula is
applied:

    Odd  questions (1,3,5,7,9):  contribution = score - 1
    Even questions (2,4,6,8,10): contribution = 5 - score
    SUS total = sum(contributions) * 2.5   (range 0-100)

Pass criterion: mean SUS score >= 68 (above-average usability).

This is a FRAMEWORK benchmark — it sets up the structure for human evaluation.
The simulated scores represent expert evaluation estimates based on the current
CARF Cockpit implementation.

Usage:
    python benchmarks/technical/ux/benchmark_sus.py
    python benchmarks/technical/ux/benchmark_sus.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.sus")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── SUS Questionnaire (Brooke 1996) ─────────────────────────────────────

SUS_QUESTIONS = [
    "I think that I would like to use this system frequently",
    "I found the system unnecessarily complex",
    "I thought the system was easy to use",
    "I think that I would need the support of a technical person to be able to use this system",
    "I found the various functions in this system were well integrated",
    "I thought there was too much inconsistency in this system",
    "I would imagine that most people would learn to use this system very quickly",
    "I found the system very cumbersome to use",
    "I felt very confident using the system",
    "I needed to learn a lot of things before I could get going with this system",
]

# ── Task Scenarios ───────────────────────────────────────────────────────

TASK_SCENARIOS = [
    {
        "id": "T1",
        "name": "Submit a clear domain query and interpret result",
        "description": (
            "User submits a simple factual query (e.g. exchange rate lookup), "
            "receives a Clear-domain routed response, and interprets the answer."
        ),
        # Simulated SUS scores (1-5) for each of the 10 questions.
        # Odd items: higher = better.  Even items: lower = better.
        "sus_scores": [4, 2, 5, 1, 4, 1, 5, 1, 5, 1],
    },
    {
        "id": "T2",
        "name": "Submit a complicated query and review causal analysis",
        "description": (
            "User submits a causal-analysis query with data context, reviews "
            "the causal graph output including ATE, confidence intervals, and "
            "refutation results."
        ),
        "sus_scores": [4, 3, 4, 2, 4, 2, 3, 2, 4, 3],
    },
    {
        "id": "T3",
        "name": "Review Guardian policy verdict explanation",
        "description": (
            "User triggers a query that requires Guardian evaluation, then "
            "reviews the verdict (APPROVED / REJECTED / REQUIRES_ESCALATION) "
            "and its explanatory rationale."
        ),
        "sus_scores": [4, 2, 4, 2, 4, 2, 4, 2, 4, 2],
    },
    {
        "id": "T4",
        "name": "Navigate governance dashboard",
        "description": (
            "User navigates the Cockpit governance board, views active policies, "
            "compliance scores, and cross-domain impact triples."
        ),
        "sus_scores": [3, 3, 3, 3, 4, 2, 3, 3, 3, 3],
    },
    {
        "id": "T5",
        "name": "Export compliance report",
        "description": (
            "User selects a compliance framework (e.g. EU AI Act), generates "
            "the compliance report, and exports it as JSON/PDF."
        ),
        "sus_scores": [4, 2, 4, 2, 4, 1, 4, 2, 4, 2],
    },
    {
        "id": "T6",
        "name": "Configure policy rules",
        "description": (
            "User opens the policy editor, creates a new federated policy rule "
            "with conditions and constraints, saves, and verifies conflict "
            "detection results."
        ),
        "sus_scores": [3, 3, 3, 3, 3, 2, 3, 3, 3, 3],
    },
    {
        "id": "T7",
        "name": "Interpret Bayesian uncertainty visualization",
        "description": (
            "User submits a Complex-domain query, views the Bayesian posterior "
            "distribution visualization, reads credible intervals and free-energy "
            "metrics."
        ),
        "sus_scores": [3, 3, 3, 3, 4, 2, 3, 3, 3, 4],
    },
    {
        "id": "T8",
        "name": "Review audit trail for a specific query",
        "description": (
            "User navigates to the audit trail view, searches for a specific "
            "past query by session ID, reviews the full reasoning chain, domain "
            "classification, and guardian verdict history."
        ),
        "sus_scores": [4, 2, 4, 2, 4, 2, 4, 2, 4, 2],
    },
]


# ── SUS Scoring ──────────────────────────────────────────────────────────


def compute_sus_score(scores: list[int]) -> float:
    """Compute SUS score from a list of 10 Likert responses (1-5).

    For odd-numbered questions (1,3,5,7,9 — indices 0,2,4,6,8):
        contribution = score - 1
    For even-numbered questions (2,4,6,8,10 — indices 1,3,5,7,9):
        contribution = 5 - score
    SUS = sum(contributions) * 2.5
    """
    if len(scores) != 10:
        raise ValueError(f"SUS requires exactly 10 scores, got {len(scores)}")

    total = 0.0
    for i, score in enumerate(scores):
        if score < 1 or score > 5:
            raise ValueError(f"SUS score must be 1-5, got {score} at position {i}")
        if i % 2 == 0:  # Odd question (1-indexed): indices 0,2,4,6,8
            total += score - 1
        else:            # Even question (1-indexed): indices 1,3,5,7,9
            total += 5 - score

    return total * 2.5


# ── Benchmark Runner ─────────────────────────────────────────────────────


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the SUS benchmark across all task scenarios."""
    logger.info("=" * 70)
    logger.info("CARF UX Benchmark — System Usability Scale (H31)")
    logger.info("=" * 70)

    t0 = time.perf_counter()
    individual_results: list[dict[str, Any]] = []

    for scenario in TASK_SCENARIOS:
        sus_score = compute_sus_score(scenario["sus_scores"])

        # Per-question breakdown
        contributions: list[dict[str, Any]] = []
        for i, (question, raw_score) in enumerate(zip(SUS_QUESTIONS, scenario["sus_scores"])):
            if i % 2 == 0:
                contribution = raw_score - 1
            else:
                contribution = 5 - raw_score
            contributions.append({
                "question_number": i + 1,
                "question": question,
                "raw_score": raw_score,
                "contribution": contribution,
            })

        result = {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "description": scenario["description"],
            "sus_score": round(sus_score, 2),
            "passed": sus_score >= 68.0,
            "contributions": contributions,
        }
        individual_results.append(result)

        status = "PASS" if sus_score >= 68.0 else "FAIL"
        logger.info(f"  [{scenario['id']}] {scenario['name']}: "
                     f"SUS={sus_score:.1f} [{status}]")

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Aggregate metrics
    all_scores = [r["sus_score"] for r in individual_results]
    mean_sus = sum(all_scores) / len(all_scores) if all_scores else 0.0
    min_sus = min(all_scores) if all_scores else 0.0
    max_sus = max(all_scores) if all_scores else 0.0
    passing_count = sum(1 for r in individual_results if r["passed"])

    metrics = {
        "sus_score": round(mean_sus, 2),
        "sus_min": round(min_sus, 2),
        "sus_max": round(max_sus, 2),
        "scenarios_total": len(individual_results),
        "scenarios_passing": passing_count,
        "pass_rate": round(passing_count / len(individual_results), 4) if individual_results else 0.0,
        "threshold": 68.0,
        "above_average": mean_sus >= 68.0,
    }

    report = {
        "benchmark": "carf_sus",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": round(elapsed_ms, 2),
        "metrics": metrics,
        "individual_results": individual_results,
        "questionnaire": SUS_QUESTIONS,
    }

    # Summary
    logger.info("")
    logger.info(f"  Mean SUS Score:       {mean_sus:.1f}")
    logger.info(f"  Range:                {min_sus:.1f} – {max_sus:.1f}")
    logger.info(f"  Scenarios Passing:    {passing_count}/{len(individual_results)}")
    logger.info(f"  Above Average (>=68): {mean_sus >= 68.0}")
    logger.info("=" * 70)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="sus", source_reference="benchmark:sus", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF UX — System Usability Scale (H31)")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    run_benchmark(output_path=args.output)


if __name__ == "__main__":
    main()
