"""Benchmark CARF Reflector self-correction capabilities.

Metrics:
  - repair_attempt_rate — % of violations where repair was attempted
  - repair_success_rate — % where action was actually modified
  - convergence_rate — % where repaired action would pass guardian
  - blind_mutation_rate — % where ALL numbers were modified (measures bluntness)

Usage:
    python benchmarks/technical/reflector/benchmark_reflector.py
    python benchmarks/technical/reflector/benchmark_reflector.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.reflector")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Scenario Definitions ─────────────────────────────────────────────────

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "budget_repair_converges",
        "description": "Budget exceeded violation — repair should reduce amount and converge",
        "violations": ["Budget exceeded: 150000 > 100000"],
        "proposed_action": {
            "action_type": "investment",
            "description": "Increase marketing budget",
            "amount": 150000,
            "parameters": {"monthly_spend": 12500},
        },
        "expected": {
            "repair_attempted": True,
            "amount_reduced": True,
            "max_attempts": 2,
        },
    },
    {
        "name": "threshold_repair_converges",
        "description": "Threshold exceeded for effect_size — 0.9x reduction, passes on retry",
        "violations": ["Threshold exceeded for effect_size"],
        "proposed_action": {
            "action_type": "adjustment",
            "description": "Apply pricing adjustment",
            "effect_size": 0.95,
            "parameters": {"margin_pct": 15.0},
        },
        "expected": {
            "repair_attempted": True,
            "values_reduced": True,
            "reduction_factor": 0.9,
        },
    },
    {
        "name": "approval_flags_human",
        "description": "Missing approval for deployment — should set requires_human_review",
        "violations": ["Missing approval for deployment"],
        "proposed_action": {
            "action_type": "deployment",
            "description": "Deploy model to production",
            "parameters": {"environment": "production"},
        },
        "expected": {
            "repair_attempted": True,
            "requires_human_review": True,
        },
    },
    {
        "name": "unknown_violation_no_repair",
        "description": "Unknown violation type — repair not attempted",
        "violations": ["Data residency requires EU storage"],
        "proposed_action": {
            "action_type": "data_transfer",
            "description": "Transfer data to US region",
            "parameters": {"region": "us-east-1"},
        },
        "expected": {
            "repair_attempted": False,
        },
    },
    {
        "name": "multi_violation_repair",
        "description": "Budget + threshold combined — both repairs applied",
        "violations": [
            "Budget exceeded: 200000 > 100000",
            "Threshold exceeded for risk_score",
        ],
        "proposed_action": {
            "action_type": "investment",
            "description": "High-risk investment proposal",
            "amount": 200000,
            "risk_score": 0.85,
            "parameters": {"allocation_pct": 25.0},
        },
        "expected": {
            "repair_attempted": True,
            "multiple_repairs": True,
        },
    },
]


def validate_repair(
    original: dict[str, Any],
    repaired: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, bool]:
    """Validate that the repair correctly addressed the violation."""
    checks: dict[str, bool] = {}
    expected = scenario["expected"]

    # Check if repair was attempted (action was modified)
    was_modified = original != repaired
    checks["action_modified"] = was_modified

    if expected.get("repair_attempted"):
        checks["repair_attempted"] = was_modified

        if expected.get("amount_reduced"):
            orig_amount = original.get("amount", 0)
            new_amount = repaired.get("amount", orig_amount)
            checks["amount_reduced"] = isinstance(new_amount, (int, float)) and new_amount < orig_amount

        if expected.get("values_reduced"):
            # Check that at least one numeric value was reduced
            any_reduced = False
            for key in original:
                if isinstance(original[key], (int, float)) and not isinstance(original[key], bool):
                    if isinstance(repaired.get(key), (int, float)):
                        if repaired[key] < original[key]:
                            any_reduced = True
            checks["values_reduced"] = any_reduced

        if expected.get("requires_human_review"):
            checks["requires_human_review"] = repaired.get("requires_human_review") is True

        if expected.get("multiple_repairs"):
            # Both budget and threshold should be addressed
            budget_addressed = False
            threshold_addressed = False
            for key in original:
                if isinstance(original[key], (int, float)) and not isinstance(original[key], bool):
                    if isinstance(repaired.get(key), (int, float)) and repaired[key] < original[key]:
                        budget_addressed = True
                        threshold_addressed = True
            checks["multiple_repairs_applied"] = budget_addressed and threshold_addressed

    else:
        # Repair should NOT have been attempted
        checks["correctly_skipped"] = not was_modified

    return checks


def _count_numeric_fields(action: dict[str, Any]) -> int:
    """Count numeric fields in an action (excluding booleans)."""
    count = 0
    for value in action.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            count += 1
        elif isinstance(value, dict):
            for sub_val in value.values():
                if isinstance(sub_val, (int, float)) and not isinstance(sub_val, bool) and sub_val > 0:
                    count += 1
    return count


def _count_modified_numeric_fields(original: dict[str, Any], repaired: dict[str, Any]) -> int:
    """Count how many numeric fields were modified."""
    modified = 0
    for key in original:
        if isinstance(original[key], (int, float)) and not isinstance(original[key], bool):
            if isinstance(repaired.get(key), (int, float)) and repaired[key] != original[key]:
                modified += 1
        elif isinstance(original[key], dict) and isinstance(repaired.get(key), dict):
            for sub_key in original[key]:
                orig_val = original[key].get(sub_key)
                new_val = repaired[key].get(sub_key)
                if isinstance(orig_val, (int, float)) and not isinstance(orig_val, bool):
                    if isinstance(new_val, (int, float)) and new_val != orig_val:
                        modified += 1
    return modified


async def run_single_reflector_test(scenario: dict[str, Any]) -> dict[str, Any]:
    """Create EpistemicState, call reflector_node(), and validate the repair."""
    from src.core.state import EpistemicState, GuardianVerdict
    from src.workflows.graph import reflector_node

    original_action = scenario["proposed_action"].copy()

    state = EpistemicState(
        user_input=f"Benchmark test: {scenario['name']}",
        proposed_action=scenario["proposed_action"].copy(),
        policy_violations=scenario["violations"],
        guardian_verdict=GuardianVerdict.REJECTED,
        reflection_count=0,
        context={},
    )

    result_state = await reflector_node(state)
    repaired_action = result_state.proposed_action or {}

    # Validate the repair
    checks = validate_repair(original_action, repaired_action, scenario)

    # Compute blind mutation rate
    total_numeric = _count_numeric_fields(original_action)
    modified_numeric = _count_modified_numeric_fields(original_action, repaired_action)
    blind_mutation = (modified_numeric == total_numeric and total_numeric > 0)

    return {
        "scenario": scenario["name"],
        "description": scenario["description"],
        "violations": scenario["violations"],
        "original_action": original_action,
        "repaired_action": repaired_action,
        "repair_attempted": original_action != repaired_action,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "blind_mutation": blind_mutation,
        "numeric_fields_total": total_numeric,
        "numeric_fields_modified": modified_numeric,
        "reflection_count": result_state.reflection_count,
        "repair_details": result_state.context.get("repair_details", []),
    }


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the full reflector benchmark suite."""
    logger.info("CARF Reflector Self-Correction Benchmark")
    logger.info(f"  Running {len(SCENARIOS)} scenarios...")

    results = []
    for scenario in SCENARIOS:
        logger.info(f"  [{scenario['name']}] {scenario['description']}")
        result = await run_single_reflector_test(scenario)
        results.append(result)
        status = "PASS" if result["all_checks_passed"] else "FAIL"
        logger.info(f"    {status} — checks: {result['checks']}")

    # Compute aggregate metrics
    total = len(results)
    repair_attempted_count = sum(1 for r in results if r["repair_attempted"])
    repair_success_count = sum(1 for r in results if r["all_checks_passed"])
    blind_mutation_count = sum(1 for r in results if r["blind_mutation"])

    # Scenarios where repair was expected
    expected_repair = [r for r in results if SCENARIOS[results.index(r)]["expected"].get("repair_attempted")]
    convergence_count = sum(1 for r in expected_repair if r["all_checks_passed"])

    metrics = {
        "repair_attempt_rate": repair_attempted_count / total if total else 0,
        "repair_success_rate": repair_success_count / total if total else 0,
        "convergence_rate": convergence_count / len(expected_repair) if expected_repair else 0,
        "blind_mutation_rate": blind_mutation_count / total if total else 0,
    }

    report = {
        "benchmark": "carf_reflector_self_correction",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": total,
        "passed": repair_success_count,
        "failed": total - repair_success_count,
        "metrics": metrics,
        "results": results,
    }

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Reflector Benchmark Summary:")
    logger.info(f"  Scenarios:            {total}")
    logger.info(f"  Passed:               {repair_success_count}/{total}")
    logger.info(f"  Repair attempt rate:  {metrics['repair_attempt_rate']:.0%}")
    logger.info(f"  Repair success rate:  {metrics['repair_success_rate']:.0%}")
    logger.info(f"  Convergence rate:     {metrics['convergence_rate']:.0%}")
    logger.info(f"  Blind mutation rate:  {metrics['blind_mutation_rate']:.0%}")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Reflector Self-Correction")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(output_path=args.output))


if __name__ == "__main__":
    main()
