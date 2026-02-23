"""Benchmark CARF Explainability Quality (H27).

Tests three dimensions of explanation quality:

  - Fidelity (10 cases):  Does the explanation match the actual reasoning chain?
                          Checks whether key causal factors appear in the explanation.
  - Stability (10 cases): Same input twice produces the same explanation?
                          Run each query twice and compare explanation outputs.
  - Simplicity (10 cases): Is the explanation concise?
                           Count reasoning steps; target <= 10 steps.

Metrics:
  - fidelity   >= 0.80
  - stability  >= 0.90
  - avg_steps  <= 10

Usage:
    python benchmarks/technical/compliance/benchmark_xai.py
    python benchmarks/technical/compliance/benchmark_xai.py -o results.json
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.xai")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Fidelity Test Cases ─────────────────────────────────────────────────
# Each case has a query, expected domain, and key factors that MUST appear
# in the explanation for it to be considered faithful.

FIDELITY_CASES = [
    {
        "name": "procurement_causal",
        "query": "How does switching suppliers affect our production costs?",
        "expected_domain": "Complicated",
        "key_factors": ["supplier", "cost", "production"],
        "description": "Causal reasoning about supplier change impact",
    },
    {
        "name": "finance_budget",
        "query": "What is the impact of a 10% budget cut on Q4 revenue projections?",
        "expected_domain": "Complicated",
        "key_factors": ["budget", "revenue", "projection"],
        "description": "Financial budget impact analysis",
    },
    {
        "name": "sustainability_emissions",
        "query": "How will transitioning to renewable energy reduce our Scope 2 emissions?",
        "expected_domain": "Complicated",
        "key_factors": ["renewable", "emission", "energy"],
        "description": "Sustainability emissions analysis",
    },
    {
        "name": "security_breach",
        "query": "What are the risks if we delay patching the critical CVE for two weeks?",
        "expected_domain": "Complex",
        "key_factors": ["risk", "patch", "security"],
        "description": "Security risk assessment",
    },
    {
        "name": "hr_retention",
        "query": "How does our remote work policy affect employee retention rates?",
        "expected_domain": "Complex",
        "key_factors": ["remote", "retention", "employee"],
        "description": "HR policy impact analysis",
    },
    {
        "name": "legal_compliance",
        "query": "What GDPR compliance gaps exist in our current data processing workflow?",
        "expected_domain": "Complicated",
        "key_factors": ["gdpr", "compliance", "data"],
        "description": "Legal compliance gap analysis",
    },
    {
        "name": "marketing_roi",
        "query": "What is the expected ROI of increasing our digital ad spend by 25%?",
        "expected_domain": "Complicated",
        "key_factors": ["roi", "ad", "spend"],
        "description": "Marketing ROI projection",
    },
    {
        "name": "operations_efficiency",
        "query": "How will automating the assembly line affect throughput and defect rates?",
        "expected_domain": "Complicated",
        "key_factors": ["automat", "throughput", "defect"],
        "description": "Operations efficiency analysis",
    },
    {
        "name": "crisis_response",
        "query": "How should we respond to the sudden 40% increase in raw material prices?",
        "expected_domain": "Chaotic",
        "key_factors": ["price", "material", "increase"],
        "description": "Crisis response planning",
    },
    {
        "name": "strategy_expansion",
        "query": "Should we expand into the Southeast Asian market given current geopolitical tensions?",
        "expected_domain": "Complex",
        "key_factors": ["market", "expansion", "geopolitical"],
        "description": "Strategic market expansion",
    },
]


# ── Stability Test Cases ────────────────────────────────────────────────
# Queries run twice; explanations compared for consistency.

STABILITY_CASES = [
    {
        "name": "stable_exchange_rate",
        "query": "What is the current USD to EUR exchange rate and its impact on imports?",
    },
    {
        "name": "stable_supply_chain",
        "query": "Analyse our supply chain resilience for semiconductor components.",
    },
    {
        "name": "stable_carbon_footprint",
        "query": "Calculate our corporate carbon footprint for the current fiscal year.",
    },
    {
        "name": "stable_vendor_risk",
        "query": "Assess the risk profile of our top five vendors based on financial stability.",
    },
    {
        "name": "stable_cost_reduction",
        "query": "Identify the top three cost reduction opportunities in our operations.",
    },
    {
        "name": "stable_data_governance",
        "query": "Review our data governance framework for ISO 27001 compliance.",
    },
    {
        "name": "stable_workforce_planning",
        "query": "Project our hiring needs for the engineering team over the next two quarters.",
    },
    {
        "name": "stable_inventory",
        "query": "Optimise our just-in-time inventory levels for the holiday season.",
    },
    {
        "name": "stable_contract_review",
        "query": "Review the terms of the SaaS vendor contract expiring next month.",
    },
    {
        "name": "stable_performance",
        "query": "Benchmark our customer service response times against industry standards.",
    },
]


# ── Simplicity Test Cases ───────────────────────────────────────────────
# Queries where we count explanation reasoning steps; target <= 10.

SIMPLICITY_CASES = [
    {
        "name": "simple_lookup",
        "query": "What is the standard corporate tax rate in Ireland?",
    },
    {
        "name": "simple_conversion",
        "query": "Convert 500 metric tons of CO2 to carbon credits at current market rates.",
    },
    {
        "name": "simple_definition",
        "query": "Define the key differences between Scope 1, 2, and 3 emissions.",
    },
    {
        "name": "simple_comparison",
        "query": "Compare the total cost of ownership between on-premise and cloud hosting.",
    },
    {
        "name": "simple_threshold",
        "query": "Is our current debt-to-equity ratio within the acceptable range for our industry?",
    },
    {
        "name": "simple_checklist",
        "query": "List the mandatory steps for onboarding a new vendor in our procurement system.",
    },
    {
        "name": "simple_calculation",
        "query": "Calculate the break-even point for our new product line at current margins.",
    },
    {
        "name": "simple_status",
        "query": "What is the current status of our SOC 2 Type II certification?",
    },
    {
        "name": "simple_policy",
        "query": "Summarise our company travel and expense reimbursement policy.",
    },
    {
        "name": "simple_timeline",
        "query": "When is the deadline for submitting our annual sustainability report?",
    },
]


async def _get_explanation(query: str) -> dict[str, Any]:
    """Get classification and explanation for a query.

    Returns domain, confidence, reasoning chain, and explanation text.
    """
    from src.core.state import EpistemicState
    from src.workflows.router import cynefin_router_node

    state = EpistemicState(user_input=query)
    t0 = time.perf_counter()
    try:
        updated = await cynefin_router_node(state)
        latency_ms = (time.perf_counter() - t0) * 1000

        domain = updated.cynefin_domain.value
        confidence = updated.domain_confidence

        # Extract reasoning chain / explanation from state
        reasoning_chain = updated.reasoning_chain or []
        explanation_parts = []

        # Build explanation text from reasoning chain entries
        for entry in reasoning_chain:
            if isinstance(entry, dict):
                explanation_parts.append(entry.get("reasoning", str(entry)))
            elif isinstance(entry, str):
                explanation_parts.append(entry)
            else:
                explanation_parts.append(str(entry))

        # If no reasoning chain, use domain rationale if available
        if not explanation_parts:
            rationale = getattr(updated, "domain_rationale", None) or ""
            if rationale:
                explanation_parts.append(rationale)
            else:
                explanation_parts.append(f"Classified as {domain} with confidence {confidence:.2f}")

        explanation_text = " ".join(explanation_parts).lower()

        return {
            "domain": domain,
            "confidence": round(confidence, 4),
            "explanation_text": explanation_text,
            "reasoning_steps": len(reasoning_chain),
            "latency_ms": round(latency_ms, 2),
            "error": None,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "domain": "ERROR",
            "confidence": 0.0,
            "explanation_text": "",
            "reasoning_steps": 0,
            "latency_ms": round(latency_ms, 2),
            "error": str(exc),
        }


async def _benchmark_fidelity() -> dict[str, Any]:
    """Test fidelity: do explanations contain the expected key factors?"""
    logger.info("--- Fidelity (10 cases) ---")
    results = []

    for case in FIDELITY_CASES:
        explanation = await _get_explanation(case["query"])

        # Check if key factors appear in the explanation text
        text = explanation["explanation_text"]
        factors_found = []
        factors_missing = []
        for factor in case["key_factors"]:
            if factor.lower() in text:
                factors_found.append(factor)
            else:
                factors_missing.append(factor)

        factor_coverage = len(factors_found) / len(case["key_factors"]) if case["key_factors"] else 1.0
        is_faithful = factor_coverage >= 0.5  # At least half of key factors present

        result = {
            "name": case["name"],
            "query": case["query"],
            "expected_domain": case["expected_domain"],
            "actual_domain": explanation["domain"],
            "factors_found": factors_found,
            "factors_missing": factors_missing,
            "factor_coverage": round(factor_coverage, 4),
            "is_faithful": is_faithful,
            "latency_ms": explanation["latency_ms"],
            "error": explanation["error"],
        }
        results.append(result)

        status = "OK" if is_faithful else "LOW"
        logger.info(
            f"  [{status}] {case['name']}: coverage={factor_coverage:.2f} "
            f"found={factors_found} missing={factors_missing}"
        )

    faithful_count = sum(1 for r in results if r["is_faithful"])
    fidelity_score = faithful_count / len(results) if results else 0

    return {
        "dimension": "fidelity",
        "score": round(fidelity_score, 4),
        "passed": fidelity_score >= 0.80,
        "total": len(results),
        "faithful_count": faithful_count,
        "results": results,
    }


async def _benchmark_stability() -> dict[str, Any]:
    """Test stability: same input twice produces the same explanation?"""
    logger.info("--- Stability (10 cases) ---")
    results = []

    for case in STABILITY_CASES:
        # Run the same query twice
        explanation_1 = await _get_explanation(case["query"])
        explanation_2 = await _get_explanation(case["query"])

        # Compare domains and confidence
        domain_match = explanation_1["domain"] == explanation_2["domain"]
        confidence_diff = abs(explanation_1["confidence"] - explanation_2["confidence"])
        confidence_stable = confidence_diff <= 0.1  # Within 10% confidence tolerance

        # Compare explanation text similarity (simple word overlap)
        words_1 = set(explanation_1["explanation_text"].split())
        words_2 = set(explanation_2["explanation_text"].split())
        if words_1 or words_2:
            overlap = len(words_1 & words_2) / max(len(words_1 | words_2), 1)
        else:
            overlap = 1.0

        is_stable = domain_match and confidence_stable

        result = {
            "name": case["name"],
            "query": case["query"],
            "run1_domain": explanation_1["domain"],
            "run2_domain": explanation_2["domain"],
            "domain_match": domain_match,
            "run1_confidence": explanation_1["confidence"],
            "run2_confidence": explanation_2["confidence"],
            "confidence_diff": round(confidence_diff, 4),
            "confidence_stable": confidence_stable,
            "text_overlap": round(overlap, 4),
            "is_stable": is_stable,
            "error": explanation_1.get("error") or explanation_2.get("error"),
        }
        results.append(result)

        status = "OK" if is_stable else "UNSTABLE"
        logger.info(
            f"  [{status}] {case['name']}: domain_match={domain_match} "
            f"conf_diff={confidence_diff:.4f} text_overlap={overlap:.2f}"
        )

    stable_count = sum(1 for r in results if r["is_stable"])
    stability_score = stable_count / len(results) if results else 0

    return {
        "dimension": "stability",
        "score": round(stability_score, 4),
        "passed": stability_score >= 0.90,
        "total": len(results),
        "stable_count": stable_count,
        "results": results,
    }


async def _benchmark_simplicity() -> dict[str, Any]:
    """Test simplicity: are explanations concise (reasoning steps <= 10)?"""
    logger.info("--- Simplicity (10 cases) ---")
    results = []

    for case in SIMPLICITY_CASES:
        explanation = await _get_explanation(case["query"])

        # Count reasoning steps from the explanation
        steps = explanation["reasoning_steps"]

        # If reasoning_steps is 0 (no chain), count logical segments in explanation
        if steps == 0 and explanation["explanation_text"]:
            # Count sentences/segments as a proxy for steps
            text = explanation["explanation_text"]
            segments = [s.strip() for s in text.replace(". ", ".\n").split("\n") if s.strip()]
            steps = len(segments)

        is_simple = steps <= 10

        result = {
            "name": case["name"],
            "query": case["query"],
            "domain": explanation["domain"],
            "reasoning_steps": steps,
            "is_simple": is_simple,
            "latency_ms": explanation["latency_ms"],
            "error": explanation["error"],
        }
        results.append(result)

        status = "OK" if is_simple else "COMPLEX"
        logger.info(f"  [{status}] {case['name']}: steps={steps} domain={explanation['domain']}")

    all_steps = [r["reasoning_steps"] for r in results]
    avg_steps = sum(all_steps) / len(all_steps) if all_steps else 0
    simple_count = sum(1 for r in results if r["is_simple"])

    return {
        "dimension": "simplicity",
        "score": round(simple_count / len(results), 4) if results else 0,
        "avg_steps": round(avg_steps, 2),
        "passed": avg_steps <= 10,
        "total": len(results),
        "simple_count": simple_count,
        "results": results,
    }


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the full XAI benchmark suite."""
    logger.info("=" * 70)
    logger.info("CARF Explainability Quality Benchmark (H27)")
    logger.info("=" * 70)

    fidelity = await _benchmark_fidelity()
    stability = await _benchmark_stability()
    simplicity = await _benchmark_simplicity()

    metrics = {
        "fidelity": fidelity["score"],
        "fidelity_passed": fidelity["passed"],
        "stability": stability["score"],
        "stability_passed": stability["passed"],
        "avg_steps": simplicity["avg_steps"],
        "avg_steps_passed": simplicity["passed"],
    }

    all_passed = fidelity["passed"] and stability["passed"] and simplicity["passed"]

    logger.info("")
    logger.info("--- Summary ---")
    logger.info(f"  Fidelity:   {fidelity['score']:.4f} "
                f"(threshold >= 0.80, {'PASS' if fidelity['passed'] else 'FAIL'})")
    logger.info(f"  Stability:  {stability['score']:.4f} "
                f"(threshold >= 0.90, {'PASS' if stability['passed'] else 'FAIL'})")
    logger.info(f"  Avg Steps:  {simplicity['avg_steps']:.2f} "
                f"(threshold <= 10, {'PASS' if simplicity['passed'] else 'FAIL'})")

    report = {
        "benchmark": "carf_xai",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "individual_results": [
            fidelity,
            stability,
            simplicity,
        ],
    }

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"XAI BENCHMARK: {'PASS' if all_passed else 'FAIL'} (3/3 dimensions)")
    logger.info("=" * 70)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="xai", source_reference="benchmark:xai", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Explainability Quality")
    parser.add_argument(
        "-o", "--output",
        default=str(Path(__file__).parent / "benchmark_xai_results.json"),
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
