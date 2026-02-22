"""Benchmark CARF Orchestration Governance (OG) Subsystem.

Tests all four pillars of the MAP-PRICE-RESOLVE-AUDIT framework:

  MAP:     Triple extraction accuracy — known entity-domain mappings vs extracted
  PRICE:   Cost computation precision — known token counts × provider rates
  RESOLVE: Conflict detection rate — known contradictory policies vs detected
  AUDIT:   Compliance scoring validity — framework scores within realistic bounds

Metrics:
  - MAP accuracy: % of known cross-domain impacts correctly identified
  - MAP precision: % of extracted triples that are truly relevant
  - PRICE error: absolute error vs hand-computed expected cost
  - RESOLVE detection rate: % of planted conflicts detected
  - RESOLVE false positive rate: conflicts flagged on non-conflicting policies
  - AUDIT compliance score range: per-framework, within [0, 1]
  - Governance node latency: P95 < 50ms (non-blocking requirement)
  - Feature-flag overhead: 0ms when GOVERNANCE_ENABLED=false

Usage:
    python benchmarks/technical/governance/benchmark_governance.py
    python benchmarks/technical/governance/benchmark_governance.py -o results.json
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
logger = logging.getLogger("benchmark.governance")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"


# ── MAP Pillar Test Cases ────────────────────────────────────────────────
# Each case has a query, known entities/domains, and expected cross-domain links.
# Ground truth derived from realistic enterprise scenarios.

MAP_TEST_CASES = [
    {
        "name": "procurement_sustainability_link",
        "query": "Our key supplier in Vietnam has high carbon emissions. "
                 "Should we switch to a local supplier to meet our Scope 3 targets?",
        "expected_domains": {"procurement", "sustainability"},
        "expected_entity_keywords": ["supplier", "carbon", "scope"],
        "cross_domain_link": ("procurement", "sustainability"),
    },
    {
        "name": "finance_security_link",
        "query": "The Q3 budget allocation for cybersecurity infrastructure "
                 "needs CFO approval before we can proceed with the SOC2 audit.",
        "expected_domains": {"finance", "security"},
        "expected_entity_keywords": ["budget", "cybersecurity", "audit"],
        "cross_domain_link": ("finance", "security"),
    },
    {
        "name": "legal_procurement_link",
        "query": "We need to review the vendor contract terms for IP protection "
                 "before signing the $2M procurement agreement.",
        "expected_domains": {"legal", "procurement"},
        "expected_entity_keywords": ["contract", "vendor", "procurement"],
        "cross_domain_link": ("legal", "procurement"),
    },
    {
        "name": "sustainability_finance_link",
        "query": "The CSRD double materiality assessment shows a $500K gap in "
                 "our ESG reporting budget for Scope 1 and Scope 2 verification.",
        "expected_domains": {"sustainability", "finance"},
        "expected_entity_keywords": ["csrd", "esg", "budget"],
        "cross_domain_link": ("sustainability", "finance"),
    },
    {
        "name": "security_legal_link",
        "query": "The GDPR data processing agreement with our cloud provider "
                 "needs to include encryption-at-rest requirements.",
        "expected_domains": {"security", "legal"},
        "expected_entity_keywords": ["gdpr", "encryption", "data"],
        "cross_domain_link": ("security", "legal"),
    },
    {
        "name": "triple_domain_chain",
        "query": "Our sustainable procurement strategy requires legal review of "
                 "EU taxonomy alignment clauses in all new supplier contracts.",
        "expected_domains": {"procurement", "sustainability", "legal"},
        "expected_entity_keywords": ["procurement", "taxonomy", "contract"],
        "cross_domain_link": ("procurement", "sustainability"),
    },
    {
        "name": "no_cross_domain",
        "query": "What is the current weather forecast for Helsinki?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
        "cross_domain_link": None,
    },
    {
        "name": "finance_only",
        "query": "What was our Q2 revenue compared to the forecast?",
        "expected_domains": {"finance"},
        "expected_entity_keywords": ["revenue", "forecast"],
        "cross_domain_link": None,
    },
]


# ── PRICE Pillar Test Cases ──────────────────────────────────────────────
# Hand-computed expected costs based on known pricing.
# DeepSeek: $0.14/1M input, $0.28/1M output
# OpenAI:   $3.00/1M input, $6.00/1M output
# Anthropic: $3.00/1M input, $15.00/1M output
# Ollama:   $0.00 (local)

PRICE_TEST_CASES = [
    {
        "name": "deepseek_1M_tokens",
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "provider": "deepseek",
        "expected_llm_cost": 0.42,  # 0.14 + 0.28
        "tolerance": 0.01,
    },
    {
        "name": "openai_1M_tokens",
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "provider": "openai",
        "expected_llm_cost": 9.00,  # 3.0 + 6.0
        "tolerance": 0.01,
    },
    {
        "name": "anthropic_1M_tokens",
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "provider": "anthropic",
        "expected_llm_cost": 18.00,  # 3.0 + 15.0
        "tolerance": 0.01,
    },
    {
        "name": "ollama_free",
        "input_tokens": 500_000,
        "output_tokens": 500_000,
        "provider": "ollama",
        "expected_llm_cost": 0.00,
        "tolerance": 0.001,
    },
    {
        "name": "zero_tokens",
        "input_tokens": 0,
        "output_tokens": 0,
        "provider": "deepseek",
        "expected_llm_cost": 0.00,
        "tolerance": 0.001,
    },
    {
        "name": "deepseek_small_query",
        "input_tokens": 500,
        "output_tokens": 200,
        "provider": "deepseek",
        "expected_llm_cost": 0.000126,  # 500*0.14/1e6 + 200*0.28/1e6
        "tolerance": 0.0001,
    },
    {
        "name": "unknown_provider_fallback",
        "input_tokens": 1_000_000,
        "output_tokens": 0,
        "provider": "unknown_xyz",
        "expected_llm_cost": 0.14,  # Falls back to deepseek input rate
        "tolerance": 0.01,
    },
]


# ── RESOLVE Pillar Test Cases ────────────────────────────────────────────
# Policies that should conflict vs policies that should NOT conflict.

RESOLVE_CONFLICT_CASES = [
    {
        "name": "spend_vs_budget_conflict",
        "policy_a": {
            "name": "emergency_procurement",
            "domain_id": "procurement",
            "namespace": "procurement.emergency",
            "rules": [{"name": "emergency_cap", "condition": {"type": "emergency"},
                        "constraint": {"max_spend": 500_000}, "message": "Emergency cap"}],
        },
        "policy_b": {
            "name": "budget_freeze",
            "domain_id": "finance",
            "namespace": "finance.freeze",
            "rules": [{"name": "freeze_all", "condition": {"type": "any"},
                        "constraint": {"max_spend": 0}, "message": "Budget frozen"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "priority_cap_conflict",
        "policy_a": {
            "name": "sustainability_priority",
            "domain_id": "sustainability",
            "namespace": "sustainability.priority",
            "rules": [{"name": "green_first", "condition": {"type": "procurement"},
                        "constraint": {"max_spend": 200_000, "require_green": True},
                        "message": "Green procurement required"}],
        },
        "policy_b": {
            "name": "cost_cap",
            "domain_id": "finance",
            "namespace": "finance.cap",
            "rules": [{"name": "spend_cap", "condition": {"type": "procurement"},
                        "constraint": {"max_spend": 50_000, "require_green": False},
                        "message": "Strict cost cap"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "compatible_policies",
        "policy_a": {
            "name": "data_classification",
            "domain_id": "security",
            "namespace": "security.classification",
            "rules": [{"name": "classify", "condition": {}, "constraint": {},
                        "message": "Classify data"}],
        },
        "policy_b": {
            "name": "contract_review",
            "domain_id": "legal",
            "namespace": "legal.contracts",
            "rules": [{"name": "review", "condition": {}, "constraint": {},
                        "message": "Review contracts"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
]


# ── AUDIT Pillar (Compliance) Test Cases ─────────────────────────────────

COMPLIANCE_FRAMEWORKS = ["eu_ai_act", "csrd", "gdpr", "iso_27001"]

# Expected minimum article counts per framework (realistic validation)
EXPECTED_MIN_ARTICLES = {
    "eu_ai_act": 3,   # At minimum Art. 9, 12, 13, 14
    "csrd": 2,
    "gdpr": 2,
    "iso_27001": 2,
}


# ── Benchmark Functions ──────────────────────────────────────────────────

class _MockState:
    """Minimal state-like object for MAP pillar benchmarks."""
    def __init__(self, user_input: str):
        self.user_input = user_input
        self.final_response = ""
        self.session_id = "benchmark"
        self.causal_evidence = None


def benchmark_map_pillar() -> dict[str, Any]:
    """Benchmark MAP pillar: triple extraction accuracy."""
    from src.services.governance_service import GovernanceService

    service = GovernanceService()
    results = []

    for case in MAP_TEST_CASES:
        mock_state = _MockState(case["query"])
        t0 = time.perf_counter()
        triples = service.map_impacts(mock_state)
        latency_ms = (time.perf_counter() - t0) * 1000

        # Extract domains found in triples
        found_domains: set[str] = set()
        for t in triples:
            found_domains.add(t.domain_source)
            found_domains.add(t.domain_target)
        found_domains.discard("")
        found_domains.discard("general")

        # Check domain detection
        expected = case["expected_domains"]
        domain_recall = (
            len(expected & found_domains) / len(expected)
            if expected else (1.0 if not found_domains else 0.0)
        )

        # Check cross-domain link
        link_detected = False
        if case["cross_domain_link"]:
            src, tgt = case["cross_domain_link"]
            for t in triples:
                if (t.domain_source == src and t.domain_target == tgt) or \
                   (t.domain_source == tgt and t.domain_target == src):
                    link_detected = True
                    break

        link_correct = link_detected if case["cross_domain_link"] else not any(
            t.domain_source != t.domain_target for t in triples
        )

        results.append({
            "name": case["name"],
            "expected_domains": sorted(expected),
            "found_domains": sorted(found_domains),
            "domain_recall": round(domain_recall, 4),
            "triple_count": len(triples),
            "link_detected": link_detected,
            "link_correct": link_correct,
            "latency_ms": round(latency_ms, 2),
        })

    # Aggregate
    recalls = [r["domain_recall"] for r in results if r["expected_domains"]]
    link_accuracy = sum(1 for r in results if r["link_correct"]) / len(results) if results else 0
    avg_latency = sum(r["latency_ms"] for r in results) / len(results) if results else 0

    return {
        "pillar": "MAP",
        "total_cases": len(results),
        "avg_domain_recall": round(sum(recalls) / len(recalls), 4) if recalls else 0,
        "cross_domain_link_accuracy": round(link_accuracy, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "individual_results": results,
    }


def benchmark_price_pillar() -> dict[str, Any]:
    """Benchmark PRICE pillar: cost computation precision."""
    from src.services.cost_intelligence_service import CostIntelligenceService

    service = CostIntelligenceService()
    results = []

    for case in PRICE_TEST_CASES:
        t0 = time.perf_counter()
        actual_cost = service.compute_llm_cost(
            case["input_tokens"], case["output_tokens"], case["provider"]
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        error = abs(actual_cost - case["expected_llm_cost"])
        within_tolerance = error <= case["tolerance"]

        results.append({
            "name": case["name"],
            "provider": case["provider"],
            "expected_cost": case["expected_llm_cost"],
            "actual_cost": round(actual_cost, 6),
            "absolute_error": round(error, 6),
            "within_tolerance": within_tolerance,
            "latency_ms": round(latency_ms, 4),
        })

    # Full breakdown test
    t0 = time.perf_counter()
    breakdown = service.compute_full_breakdown(
        session_id="benchmark-session",
        input_tokens=10_000,
        output_tokens=5_000,
        provider="deepseek",
        compute_time_ms=2500,
    )
    breakdown_latency = (time.perf_counter() - t0) * 1000

    # Aggregation test
    service.compute_full_breakdown(session_id="bench-agg-1", input_tokens=1000, output_tokens=500)
    service.compute_full_breakdown(session_id="bench-agg-2", input_tokens=2000, output_tokens=1000)
    agg = service.aggregate_costs()

    accuracy = sum(1 for r in results if r["within_tolerance"]) / len(results) if results else 0

    return {
        "pillar": "PRICE",
        "total_cases": len(results),
        "accuracy": round(accuracy, 4),
        "max_absolute_error": round(max(r["absolute_error"] for r in results), 6) if results else 0,
        "breakdown_valid": breakdown.total_cost > 0 and len(breakdown.breakdown_items) >= 3,
        "breakdown_latency_ms": round(breakdown_latency, 2),
        "aggregation_valid": agg.total_sessions >= 2 and agg.total_cost > 0,
        "individual_results": results,
    }


def _make_policy(data: dict) -> Any:
    """Create a FederatedPolicy from a dict spec."""
    from src.core.governance_models import FederatedPolicy, FederatedPolicyRule
    rules = [FederatedPolicyRule(**r) for r in data.get("rules", [])]
    return FederatedPolicy(
        name=data["name"],
        domain_id=data["domain_id"],
        namespace=data["namespace"],
        rules=rules,
    )


def benchmark_resolve_pillar() -> dict[str, Any]:
    """Benchmark RESOLVE pillar: conflict detection accuracy."""
    from src.services.federated_policy_service import FederatedPolicyService

    results = []

    for case in RESOLVE_CONFLICT_CASES:
        service = FederatedPolicyService()  # Fresh service per case

        from src.core.governance_models import GovernanceDomain

        # Register domains
        service.register_domain(GovernanceDomain(
            domain_id=case["policy_a"]["domain_id"],
            display_name=case["policy_a"]["domain_id"].title(),
        ))
        if case["policy_b"]["domain_id"] != case["policy_a"]["domain_id"]:
            service.register_domain(GovernanceDomain(
                domain_id=case["policy_b"]["domain_id"],
                display_name=case["policy_b"]["domain_id"].title(),
            ))

        # Add policy A
        policy_a = _make_policy(case["policy_a"])
        service.add_policy(policy_a)

        # Detect conflicts against policy B
        policy_b = _make_policy(case["policy_b"])
        t0 = time.perf_counter()
        conflicts = service.detect_conflicts(policy_b)
        latency_ms = (time.perf_counter() - t0) * 1000

        conflict_detected = len(conflicts) > 0
        correct = conflict_detected == case["should_conflict"]

        results.append({
            "name": case["name"],
            "should_conflict": case["should_conflict"],
            "conflict_detected": conflict_detected,
            "conflicts_found": len(conflicts),
            "correct": correct,
            "latency_ms": round(latency_ms, 2),
        })

    # Metrics
    true_conflicts = [r for r in results if r["should_conflict"]]
    false_conflicts = [r for r in results if not r["should_conflict"]]

    detection_rate = (
        sum(1 for r in true_conflicts if r["conflict_detected"]) / len(true_conflicts)
        if true_conflicts else 0
    )
    false_positive_rate = (
        sum(1 for r in false_conflicts if r["conflict_detected"]) / len(false_conflicts)
        if false_conflicts else 0
    )

    return {
        "pillar": "RESOLVE",
        "total_cases": len(results),
        "conflict_detection_rate": round(detection_rate, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "overall_accuracy": round(
            sum(1 for r in results if r["correct"]) / len(results), 4
        ) if results else 0,
        "individual_results": results,
    }


def benchmark_audit_pillar() -> dict[str, Any]:
    """Benchmark AUDIT pillar: compliance scoring validity."""
    from src.core.governance_models import ComplianceFramework
    from src.services.governance_service import GovernanceService

    service = GovernanceService()
    results = []

    framework_map = {
        "eu_ai_act": ComplianceFramework.EU_AI_ACT,
        "csrd": ComplianceFramework.CSRD,
        "gdpr": ComplianceFramework.GDPR,
        "iso_27001": ComplianceFramework.ISO_27001,
    }

    for framework in COMPLIANCE_FRAMEWORKS:
        t0 = time.perf_counter()
        score = service.compute_compliance(framework_map[framework])
        latency_ms = (time.perf_counter() - t0) * 1000

        score_dict = score.model_dump()
        valid_score = 0.0 <= score_dict["overall_score"] <= 1.0
        min_articles = EXPECTED_MIN_ARTICLES.get(framework, 1)
        has_articles = len(score_dict["articles"]) >= min_articles
        has_gaps = isinstance(score_dict.get("gaps"), list)
        has_recommendations = isinstance(score_dict.get("recommendations"), list)

        # Validate each article has required fields
        articles_valid = all(
            "article_id" in a and "title" in a and "score" in a and "status" in a
            for a in score_dict["articles"]
        )

        results.append({
            "framework": framework,
            "overall_score": round(score_dict["overall_score"], 4),
            "article_count": len(score_dict["articles"]),
            "gap_count": len(score_dict.get("gaps", [])),
            "recommendation_count": len(score_dict.get("recommendations", [])),
            "valid_score_range": valid_score,
            "has_min_articles": has_articles,
            "articles_well_formed": articles_valid,
            "has_gaps": has_gaps,
            "has_recommendations": has_recommendations,
            "latency_ms": round(latency_ms, 2),
        })

    # All frameworks must produce valid scores
    all_valid = all(
        r["valid_score_range"] and r["has_min_articles"] and r["articles_well_formed"]
        for r in results
    )

    return {
        "pillar": "AUDIT",
        "total_frameworks": len(results),
        "all_valid": all_valid,
        "avg_compliance_score": round(
            sum(r["overall_score"] for r in results) / len(results), 4
        ) if results else 0,
        "framework_results": results,
    }


async def benchmark_governance_node_latency(iterations: int = 20) -> dict[str, Any]:
    """Benchmark governance node latency overhead.

    Measures actual governance_node() execution time to verify
    the < 50ms P95 requirement.
    """
    from src.core.state import EpistemicState, CynefinDomain, GuardianVerdict
    from src.workflows.graph import governance_node

    state = EpistemicState(
        user_input="Evaluate the impact of switching to a local supplier on our "
                   "Scope 3 carbon emissions and procurement costs.",
        cynefin_domain=CynefinDomain.COMPLICATED,
        domain_confidence=0.85,
        guardian_verdict=GuardianVerdict.APPROVED,
        final_response="Analysis indicates switching suppliers reduces Scope 3 by 15%.",
        context={"provider": "deepseek"},
    )

    latencies: list[float] = []

    # Warm up
    for _ in range(3):
        await governance_node(state)

    # Measure
    for _ in range(iterations):
        t0 = time.perf_counter()
        await governance_node(state)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95_idx = int(len(latencies) * 0.95) - 1
    p95 = latencies[max(0, p95_idx)] if latencies else 0
    p99_idx = int(len(latencies) * 0.99) - 1
    p99 = latencies[max(0, p99_idx)] if latencies else 0

    return {
        "iterations": iterations,
        "avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "min_ms": round(min(latencies), 2) if latencies else 0,
        "max_ms": round(max(latencies), 2) if latencies else 0,
        "p95_under_50ms": p95 < 50.0,
        "all_latencies_ms": [round(l, 2) for l in latencies],
    }


def benchmark_feature_flag_overhead() -> dict[str, Any]:
    """Verify zero overhead when GOVERNANCE_ENABLED=false.

    Measures route_after_guardian() latency with and without governance
    to confirm the feature flag adds no overhead when disabled.
    """
    from src.core.state import EpistemicState, GuardianVerdict
    from src.workflows.graph import route_after_guardian

    state = EpistemicState(
        user_input="Test query",
        guardian_verdict=GuardianVerdict.APPROVED,
    )

    iterations = 100

    # With governance disabled
    original = os.environ.get("GOVERNANCE_ENABLED")
    os.environ["GOVERNANCE_ENABLED"] = "false"
    disabled_latencies: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = route_after_guardian(state)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000  # microseconds
        disabled_latencies.append(elapsed_us)
    assert result == "end", f"Expected 'end' when disabled, got '{result}'"

    # With governance enabled
    os.environ["GOVERNANCE_ENABLED"] = "true"
    enabled_latencies: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = route_after_guardian(state)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        enabled_latencies.append(elapsed_us)
    assert result == "governance", f"Expected 'governance' when enabled, got '{result}'"

    # Restore
    if original is not None:
        os.environ["GOVERNANCE_ENABLED"] = original
    else:
        os.environ.pop("GOVERNANCE_ENABLED", None)

    avg_disabled = sum(disabled_latencies) / len(disabled_latencies)
    avg_enabled = sum(enabled_latencies) / len(enabled_latencies)

    return {
        "iterations": iterations,
        "disabled_avg_us": round(avg_disabled, 2),
        "enabled_avg_us": round(avg_enabled, 2),
        "overhead_us": round(avg_enabled - avg_disabled, 2),
        "zero_overhead": abs(avg_enabled - avg_disabled) < 100,  # < 100us difference
    }


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the full Governance benchmark suite."""
    logger.info("=" * 70)
    logger.info("CARF Orchestration Governance Benchmark")
    logger.info("=" * 70)

    # ── MAP ──
    logger.info("\n--- MAP Pillar: Triple Extraction ---")
    map_results = benchmark_map_pillar()
    logger.info(f"  Domain Recall:          {map_results['avg_domain_recall']:.1%}")
    logger.info(f"  Cross-Domain Accuracy:  {map_results['cross_domain_link_accuracy']:.1%}")
    logger.info(f"  Avg Latency:            {map_results['avg_latency_ms']:.1f}ms")

    # ── PRICE ──
    logger.info("\n--- PRICE Pillar: Cost Computation ---")
    price_results = benchmark_price_pillar()
    logger.info(f"  Accuracy:               {price_results['accuracy']:.1%}")
    logger.info(f"  Max Absolute Error:     ${price_results['max_absolute_error']:.6f}")
    logger.info(f"  Breakdown Valid:        {price_results['breakdown_valid']}")
    logger.info(f"  Aggregation Valid:      {price_results['aggregation_valid']}")

    # ── RESOLVE ──
    logger.info("\n--- RESOLVE Pillar: Conflict Detection ---")
    resolve_results = benchmark_resolve_pillar()
    logger.info(f"  Detection Rate:         {resolve_results['conflict_detection_rate']:.1%}")
    logger.info(f"  False Positive Rate:    {resolve_results['false_positive_rate']:.1%}")
    logger.info(f"  Overall Accuracy:       {resolve_results['overall_accuracy']:.1%}")

    # ── AUDIT ──
    logger.info("\n--- AUDIT Pillar: Compliance Scoring ---")
    audit_results = benchmark_audit_pillar()
    logger.info(f"  All Frameworks Valid:   {audit_results['all_valid']}")
    logger.info(f"  Avg Compliance Score:   {audit_results['avg_compliance_score']:.1%}")
    for fw in audit_results["framework_results"]:
        logger.info(f"    {fw['framework']:>12}: {fw['overall_score']:.1%} "
                     f"({fw['article_count']} articles, {fw['gap_count']} gaps)")

    # ── Governance Node Latency ──
    logger.info("\n--- Governance Node Latency ---")
    latency_results = await benchmark_governance_node_latency()
    logger.info(f"  Avg:  {latency_results['avg_ms']:.1f}ms")
    logger.info(f"  P50:  {latency_results['p50_ms']:.1f}ms")
    logger.info(f"  P95:  {latency_results['p95_ms']:.1f}ms")
    logger.info(f"  P95 < 50ms: {latency_results['p95_under_50ms']}")

    # ── Feature Flag Overhead ──
    logger.info("\n--- Feature Flag Overhead ---")
    flag_results = benchmark_feature_flag_overhead()
    logger.info(f"  Disabled avg:   {flag_results['disabled_avg_us']:.1f}us")
    logger.info(f"  Enabled avg:    {flag_results['enabled_avg_us']:.1f}us")
    logger.info(f"  Overhead:       {flag_results['overhead_us']:.1f}us")
    logger.info(f"  Zero overhead:  {flag_results['zero_overhead']}")

    # ── Assemble Report ──
    report = {
        "benchmark": "carf_governance",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "map": map_results,
        "price": price_results,
        "resolve": resolve_results,
        "audit": audit_results,
        "latency": latency_results,
        "feature_flag": flag_results,
        # Aggregate metrics for report generator
        "map_accuracy": map_results["cross_domain_link_accuracy"],
        "price_accuracy": price_results["accuracy"],
        "conflict_detection_rate": resolve_results["conflict_detection_rate"],
        "conflict_false_positive_rate": resolve_results["false_positive_rate"],
        "compliance_all_valid": audit_results["all_valid"],
        "governance_p95_ms": latency_results["p95_ms"],
        "governance_p95_under_50ms": latency_results["p95_under_50ms"],
    }

    # Summary
    logger.info("\n" + "=" * 70)
    pillars_passed = sum([
        map_results["cross_domain_link_accuracy"] >= 0.7,
        price_results["accuracy"] >= 0.95,
        resolve_results["conflict_detection_rate"] >= 0.8,
        audit_results["all_valid"],
        latency_results["p95_under_50ms"],
        flag_results["zero_overhead"],
    ])
    logger.info(f"GOVERNANCE BENCHMARK: {pillars_passed}/6 checks passed")
    logger.info("=" * 70)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Governance")
    parser.add_argument(
        "-o", "--output",
        default=str(Path(__file__).parent / "benchmark_governance_results.json"),
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
