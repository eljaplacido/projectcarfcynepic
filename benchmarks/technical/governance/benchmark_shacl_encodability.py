# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H49: SHACL Safety Completeness — % of Guardian policies SHACL-encodable.

Hypothesis: A measurable percentage of Guardian policies can be encoded as
W3C SHACL shapes, providing provable zero-violation verification for the
subset that translates cleanly.

Metrics:
    encodability_ratio: % of total policies translatable to SHACL
    yaml_encodability: % of YAML policies encodable
    csl_encodability: % of CSL policies encodable
    non_encodable_details: per-rule reasons for non-translation
    validation_coverage: % of governance state covered by SHACL shapes
    validation_correctness: SHACL violations match CSL expectations
    total_policies, encodable_policies

Targets:
    encodability_ratio >= 0.50 (at least half of policies SHACL-encodable)
    False positive rate (SHACL violation where CSL says OK) = 0
    False negative rate (SHACL OK where CSL says violation) <= 0.05

Usage:
    python benchmarks/technical/governance/benchmark_shacl_encodability.py
    python benchmarks/technical/governance/benchmark_shacl_encodability.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.shacl_encodability")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Test cases for SHACL validation correctness ──────────────────────────
# Each case provides a governance context and the expected CSL+SHACL outcome.

VALIDATION_TEST_CASES = [
    {
        "name": "transfer_within_limit",
        "context": {
            "user.role": "junior",
            "action.type": "transfer",
            "action.amount": 500,
        },
        "expected_violations": 0,
        "description": "Junior transfer of $500 — within $1,000 limit",
    },
    {
        "name": "transfer_exceeds_limit",
        "context": {
            "user.role": "junior",
            "action.type": "transfer",
            "action.amount": 1500,
        },
        "expected_violations": 1,
        "expected_shape_violated": "budget_limits_junior_transfer_limit",
        "description": "Junior transfer of $1,500 — exceeds $1,000 limit",
    },
    {
        "name": "large_amount_clear_domain",
        "context": {
            "domain.confidence": 0.97,
            "domain.entropy": 0.15,
            "action.amount": 50000,
            "domain.type": "Clear",
        },
        "expected_violations": 0,
        "description": "$50,000 transfer in Clear domain — within $100,000 limit",
    },
    {
        "name": "large_amount_chaotic_domain",
        "context": {
            "domain.confidence": 0.40,
            "domain.entropy": 0.92,
            "action.amount": 50000,
            "domain.type": "Chaotic",
        },
        "expected_violations": 1,
        "expected_shape_violated": "budget_limits_domain_financial_limit_chaotic",
        "description": "$50,000 transfer in Chaotic domain — exceeds $10,000 limit",
    },
    {
        "name": "low_confidence_complex",
        "context": {
            "domain.confidence": 0.55,
            "domain.entropy": 0.65,
        },
        "expected_violations": 1,
        "expected_shape_violated": "Shape_ConfidenceThreshold",
        "description": "Confidence 0.55 in Complex domain — below 0.70 threshold",
    },
    {
        "name": "high_entropy_alert",
        "context": {
            "domain.confidence": 0.80,
            "domain.entropy": 0.95,
        },
        "expected_violations": 1,
        "expected_shape_violated": "Shape_EntropyAlert",
        "description": "Entropy 0.95 — exceeds 0.90 alert threshold",
    },
    {
        "name": "data_region_invalid",
        "context": {
            "data.region": "ap-southeast-1",
        },
        "expected_violations": 1,
        "expected_shape_violated": "Shape_DataResidency",
        "description": "Data in ap-southeast-1 — not an approved region",
    },
    {
        "name": "all_clean",
        "context": {
            "domain.confidence": 0.95,
            "domain.entropy": 0.15,
            "session.reflection_count": 1,
            "session.duration_seconds": 30,
            "action.amount": 500,
            "data.region": "us-east-1",
        },
        "expected_violations": 0,
        "description": "All values within policy bounds",
    },
]


def _grade_encodability(ratio: float) -> str:
    if ratio >= 0.80:
        return "validated"
    if ratio >= 0.50:
        return "needs-independent-replication"
    if ratio >= 0.30:
        return "synthetic-only"
    return "aspirational"


def _grade_validation(fp: int, fn: int, total: int) -> str:
    if total == 0:
        return "aspirational"
    if fp == 0 and fn == 0:
        return "validated"
    if fp == 0 and fn / max(1, total) <= 0.10:
        return "needs-independent-replication"
    return "synthetic-only"


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    logger.info("=" * 60)
    logger.info("H49: SHACL Safety Completeness Benchmark")
    logger.info("=" * 60)

    try:
        from src.services.shacl_service import SHACLService, reset_shacl_service
    except ImportError as exc:
        logger.error("SHACL service not importable: %s", exc)
        result = {
            "benchmark_id": "shacl_encodability",
            "hypothesis": "H49",
            "status": "skipped",
            "reason": f"SHACL service unavailable: {exc}",
            "timestamp": None,
        }
        if output_path:
            Path(output_path).write_text(json.dumps(result, indent=2))
        return result

    reset_shacl_service()
    service = SHACLService()

    if not service.available:
        logger.warning("pyshacl/rdflib not installed — install carf[shacl] for real results")
        return {
            "benchmark_id": "shacl_encodability",
            "hypothesis": "H49",
            "status": "skipped",
            "reason": "pyshacl/rdflib not installed. Run: pip install carf[shacl]",
            "encodability_ratio": None,
            "timestamp": None,
        }

    # ── Phase 1: Load policies and measure encodability ─────────────────
    logger.info("Phase 1: Loading and translating policies to SHACL...")
    yaml_path = _PROJECT_ROOT / "config" / "policies.yaml"
    csl_dir = _PROJECT_ROOT / "config" / "policies"

    service.load_all(yaml_path=yaml_path, csl_dir=csl_dir)

    logger.info(
        "Encodability: %d/%d policies (%.1f%%)",
        service._encodable_policies,
        service._total_policies,
        service.encodability_ratio * 100,
    )

    # ── Phase 2: Categorize non-encodable rules ────────────────────────
    non_encodable = [e for e in service.encodability_details if not e["encodable"]]
    encodable = [e for e in service.encodability_details if e["encodable"]]

    logger.info("Encodable rules (%d):", len(encodable))
    for e in encodable:
        logger.info("  + %s::%s → %s", e["policy_name"], e["rule_name"], e["shape_id"])

    if non_encodable:
        logger.info("Non-encodable rules (%d):", len(non_encodable))
        for e in non_encodable:
            logger.info("  - %s::%s — %s", e["policy_name"], e["rule_name"], e["reason"])

    # ── Phase 3: Validation correctness (false positive/negative) ──────
    logger.info("Phase 2: Validation correctness testing...")
    fp_count = 0
    fn_count = 0
    correct_count = 0
    test_results: list[dict[str, Any]] = []

    for case in VALIDATION_TEST_CASES:
        result = service.validate_context(case["context"])
        violation_count = len(result.violations)

        matches_expected = violation_count == case["expected_violations"]
        if not matches_expected:
            if violation_count > case["expected_violations"]:
                fp_count += 1
            else:
                fn_count += 1
        else:
            correct_count += 1

        # Check if specific shape was violated (when expected)
        shape_match = True
        if case.get("expected_shape_violated"):
            shape_names = [v.source_shape.split("#")[-1] for v in result.violations]
            shape_match = case["expected_shape_violated"] in shape_names
            if not shape_match:
                fn_count = max(fn_count + 1, fn_count)

        test_results.append(
            {
                "name": case["name"],
                "description": case["description"],
                "expected_violations": case["expected_violations"],
                "actual_violations": violation_count,
                "matched": matches_expected,
                "violation_details": [
                    {
                        "message": v.result_message,
                        "shape": v.source_shape.split("#")[-1]
                        if "#" in str(v.source_shape)
                        else str(v.source_shape),
                        "constraint": v.source_constraint,
                    }
                    for v in result.violations
                ],
            }
        )

        status = "PASS" if matches_expected else "FAIL"
        logger.info(
            "  %s: %s — expected %d violations, got %d (%d shapes violated)",
            status,
            case["name"],
            case["expected_violations"],
            violation_count,
            len(result.violations),
        )

    total_tests = len(VALIDATION_TEST_CASES)
    logger.info(
        "Validation: %d/%d correct, %d false pos, %d false neg",
        correct_count,
        total_tests,
        fp_count,
        fn_count,
    )

    encodability_grade = _grade_encodability(service.encodability_ratio)
    validation_grade = _grade_validation(fp_count, fn_count, total_tests)

    # Determine overall grade
    grades = [encodability_grade, validation_grade]
    grade_order = ["aspirational", "synthetic-only", "needs-independent-replication", "validated"]
    overall_grade = min(grades, key=lambda g: grade_order.index(g))

    result = {
        "benchmark_id": "shacl_encodability",
        "hypothesis": "H49",
        "hypothesis_text": "SHACL safety completeness — % of Guardian policies SHACL-encodable",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "encodability": {
            "ratio": service.encodability_ratio,
            "total_policies": service._total_policies,
            "encodable_policies": service._encodable_policies,
            "yaml_policies_encodable": sum(
                1
                for e in service.encodability_details
                if e["encodable"]
                and e["policy_name"] in ("financial", "data", "operational", "risk", "escalation")
            ),
            "csl_policies_encodable": sum(
                1
                for e in service.encodability_details
                if e["encodable"]
                and e["policy_name"]
                not in ("financial", "data", "operational", "risk", "escalation")
            ),
            "grade": encodability_grade,
        },
        "validation": {
            "total_tests": total_tests,
            "correct": correct_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "accuracy": correct_count / max(1, total_tests),
            "grade": validation_grade,
            "test_results": test_results,
        },
        "non_encodable_rules": [
            {
                "policy_name": e["policy_name"],
                "rule_name": e["rule_name"],
                "reason": e["reason"],
            }
            for e in non_encodable
        ],
        "encodable_rules": [
            {
                "policy_name": e["policy_name"],
                "rule_name": e["rule_name"],
                "shape_id": e["shape_id"],
            }
            for e in encodable
        ],
        "grade": overall_grade,
    }

    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2))
        logger.info("Results written to %s", output_path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="H49: SHACL Safety Completeness Benchmark")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    result = run_benchmark(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
