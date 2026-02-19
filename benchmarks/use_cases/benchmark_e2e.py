"""End-to-End Use Case Benchmark Runner.

Runs full CARF pipeline AND raw LLM baseline for each industry scenario,
comparing domain classification, analysis quality, and policy enforcement.

13 scenarios across 6 industries with realistic numpy-generated datasets
(50-200 rows each) and proper statistical properties for causal/Bayesian analysis.

Usage:
    python benchmarks/use_cases/benchmark_e2e.py
    python benchmarks/use_cases/benchmark_e2e.py --scenarios supply_chain,finance
    python benchmarks/use_cases/benchmark_e2e.py --output results/e2e_results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("carf.benchmark.e2e")


@dataclass
class BenchmarkScenario:
    """A single end-to-end benchmark scenario."""
    name: str
    domain: str
    industry: str
    query: str
    context: dict[str, Any] = field(default_factory=dict)
    data: list[dict[str, Any]] = field(default_factory=list)
    carf_validation: dict[str, Any] = field(default_factory=dict)
    llm_comparison: dict[str, Any] = field(default_factory=dict)


# ── Realistic Data Generators ────────────────────────────────────────────

def _generate_supply_chain_data(n: int = 80, seed: int = 42) -> list[dict[str, Any]]:
    """Supply chain disruption data with confounded treatment assignment.
    num_suppliers causally reduces disruptions; region_risk confounds both.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    region_risk = rng.uniform(0.2, 0.9, n)
    # Companies in riskier regions diversify more
    num_suppliers_prob = 0.3 + 0.5 * region_risk
    num_suppliers = (rng.random(n) * 5 * num_suppliers_prob + 1).astype(int).clip(1, 6)
    lead_time_days = (20 + 10 * region_risk - 2 * num_suppliers + rng.normal(0, 3, n)).clip(15, 60).astype(int)
    disruption_count = (15 - 2.5 * num_suppliers + 8 * region_risk + rng.normal(0, 2, n)).clip(0, 20).astype(int)
    return [{"num_suppliers": int(num_suppliers[i]), "disruption_count": int(disruption_count[i]),
             "region_risk": round(float(region_risk[i]), 3), "lead_time_days": int(lead_time_days[i])}
            for i in range(n)]


def _generate_discount_churn_data(n: int = 100, seed: int = 43) -> list[dict[str, Any]]:
    """Customer churn data: discount reduces churn, tenure confounds both."""
    import numpy as np
    rng = np.random.default_rng(seed)
    tenure_months = rng.integers(1, 61, size=n)
    monthly_spend = (40 + 2 * tenure_months + rng.normal(0, 15, n)).clip(20, 200).round(2)
    # Discounts targeted at at-risk (low-tenure) customers
    discount_prob = 0.6 - 0.005 * tenure_months
    received_discount = (rng.random(n) < discount_prob.clip(0.1, 0.8)).astype(int)
    logit = 1.5 - 0.03 * tenure_months - 0.8 * received_discount - 0.005 * monthly_spend + rng.normal(0, 0.3, n)
    churn_prob = 1 / (1 + np.exp(-logit))
    churned = (rng.random(n) < churn_prob).astype(int)
    return [{"received_discount": int(received_discount[i]), "churned": int(churned[i]),
             "tenure_months": int(tenure_months[i]), "monthly_spend": float(monthly_spend[i])}
            for i in range(n)]


def _generate_scope3_data(n: int = 60, seed: int = 44) -> list[dict[str, Any]]:
    """Scope 3 supplier emissions: program reduces emissions by ~55 tonnes."""
    import numpy as np
    rng = np.random.default_rng(seed)
    in_program = (rng.random(n) < 0.5).astype(int)
    sizes = rng.choice(["small", "medium", "large"], size=n, p=[0.3, 0.45, 0.25])
    regions = rng.choice(["EU", "APAC", "NA"], size=n, p=[0.35, 0.35, 0.30])
    size_baseline = {"small": 120.0, "medium": 170.0, "large": 240.0}
    region_offset = {"EU": -15.0, "APAC": 10.0, "NA": 5.0}
    emissions = np.array([size_baseline[sizes[i]] + region_offset[regions[i]] - 55.0 * in_program[i]
                          + rng.normal(0, 18) for i in range(n)]).clip(50, 300).round(1)
    return [{"in_program": int(in_program[i]), "emissions_tonnes": float(emissions[i]),
             "supplier_size": str(sizes[i]), "region": str(regions[i])} for i in range(n)]


def _generate_healthcare_data(n: int = 100, seed: int = 45) -> list[dict[str, Any]]:
    """Treatment effect on recovery: new protocol saves ~8 days."""
    import numpy as np
    rng = np.random.default_rng(seed)
    new_protocol = (rng.random(n) < 0.5).astype(int)
    age = rng.integers(20, 81, size=n)
    severity = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.10, 0.20, 0.35, 0.25, 0.10])
    recovery = (15.0 - 8.0 * new_protocol + 0.15 * age + 4.0 * severity + rng.normal(0, 2.5, n)).clip(5, 45).astype(int)
    return [{"new_protocol": int(new_protocol[i]), "recovery_days": int(recovery[i]),
             "age": int(age[i]), "severity": int(severity[i])} for i in range(n)]


def _generate_energy_grid_data(n: int = 80, seed: int = 46) -> list[dict[str, Any]]:
    """Smart grid efficiency: upgrade reduces transmission loss by ~2%."""
    import numpy as np
    rng = np.random.default_rng(seed)
    smart_grid = (rng.random(n) < 0.45).astype(int)
    grid_age_years = rng.integers(5, 41, size=n)
    peak_load_mw = rng.integers(50, 501, size=n)
    loss = (6.0 - 2.0 * smart_grid + 0.08 * grid_age_years + 0.003 * peak_load_mw + rng.normal(0, 0.7, n)).clip(1.0, 15.0).round(2)
    return [{"smart_grid": int(smart_grid[i]), "transmission_loss_pct": float(loss[i]),
             "grid_age_years": int(grid_age_years[i]), "peak_load_mw": int(peak_load_mw[i])} for i in range(n)]


def _generate_bayesian_observations(mean: float, std: float, n: int, seed: int) -> list[float]:
    """Generate Bayesian observation data with known ground truth."""
    import numpy as np
    rng = np.random.default_rng(seed)
    return [round(float(x), 5) for x in rng.normal(loc=mean, scale=std, size=n)]


# ── Scenario Definitions ─────────────────────────────────────────────────

SCENARIOS: list[BenchmarkScenario] = [
    # Supply Chain — Complicated (80 rows)
    BenchmarkScenario(
        name="Supply Chain Disruption Risk",
        domain="complicated",
        industry="supply_chain",
        query="What is the causal effect of supplier diversification on supply chain disruption frequency?",
        context={"hypothesis": "Diversifying suppliers reduces disruption risk",
                 "treatment_variable": "num_suppliers", "outcome_variable": "disruption_count"},
        data=_generate_supply_chain_data(n=80, seed=42),
        carf_validation={"expected_domain": "complicated", "expect_causal_evidence": True, "effect_direction": "negative"},
        llm_comparison={"check_domain": True, "check_causal_reasoning": True},
    ),
    # Finance — Complicated (100 rows)
    BenchmarkScenario(
        name="Discount Impact on Churn",
        domain="complicated",
        industry="financial_risk",
        query="What is the causal effect of discount offers on customer churn rate?",
        context={"hypothesis": "Discount offers reduce customer churn",
                 "treatment_variable": "received_discount", "outcome_variable": "churned"},
        data=_generate_discount_churn_data(n=100, seed=43),
        carf_validation={"expected_domain": "complicated", "expect_causal_evidence": True, "effect_direction": "negative"},
        llm_comparison={"check_domain": True, "check_causal_reasoning": True},
    ),
    # Finance — Chaotic
    BenchmarkScenario(
        name="Fraud Crisis Detection",
        domain="chaotic",
        industry="financial_risk",
        query="URGENT: 200 suspicious transactions detected across 8 accounts in 2 minutes, total exposure $1.5M. Multiple credential stuffing patterns identified.",
        context={"type": "crisis", "severity": "critical"},
        carf_validation={"expected_domain": "chaotic", "expect_escalation": True, "expect_action_type": "emergency_stop"},
        llm_comparison={"check_urgency": True, "check_action_recommendation": True},
    ),
    # Sustainability — Complicated (60 rows)
    BenchmarkScenario(
        name="Scope 3 Supplier Program Impact",
        domain="complicated",
        industry="sustainability",
        query="What is the causal effect of the supplier sustainability program on Scope 3 emissions per tonne?",
        context={"hypothesis": "Supplier program reduces Scope 3 emissions",
                 "treatment_variable": "in_program", "outcome_variable": "emissions_tonnes"},
        data=_generate_scope3_data(n=60, seed=44),
        carf_validation={"expected_domain": "complicated", "expect_causal_evidence": True, "effect_direction": "negative"},
        llm_comparison={"check_domain": True, "check_causal_reasoning": True},
    ),
    # Sustainability — Complex (Bayesian with 40 ROI observations)
    BenchmarkScenario(
        name="Renewable Energy ROI Uncertainty",
        domain="complex",
        industry="sustainability",
        query="How uncertain are we about the long-term ROI of our solar panel investment given changing energy markets and policy risk?",
        context={
            "hypothesis": "Solar ROI is positive but highly uncertain",
            "uncertainty_factors": ["energy_price_volatility", "policy_changes", "technology_degradation"],
            "bayesian_inference": {
                "observations": _generate_bayesian_observations(mean=0.08, std=0.12, n=40, seed=47),
                "draws": 500, "tune": 500, "chains": 2, "target_accept": 0.9, "seed": 47,
            },
        },
        carf_validation={"expected_domain": "complex", "expect_response": True, "expect_bayesian_evidence": True},
        llm_comparison={"check_uncertainty_acknowledgment": True},
    ),
    # Critical Infra — Chaotic
    BenchmarkScenario(
        name="Grid Cascade Failure",
        domain="chaotic",
        industry="critical_infra",
        query="EMERGENCY: Transmission line failure causing cascade across 4 substations. Frequency below 49.2Hz and dropping. 300,000 customers at risk.",
        context={"type": "crisis", "severity": "critical"},
        carf_validation={"expected_domain": "chaotic", "expect_escalation": True, "expect_action_type": "emergency_stop"},
        llm_comparison={"check_urgency": True, "check_action_recommendation": True},
    ),
    # Healthcare — Complicated (100 rows)
    BenchmarkScenario(
        name="Treatment Effect on Recovery",
        domain="complicated",
        industry="healthcare",
        query="What is the causal effect of the new rehabilitation protocol on patient recovery time?",
        context={"hypothesis": "New protocol reduces recovery time",
                 "treatment_variable": "new_protocol", "outcome_variable": "recovery_days"},
        data=_generate_healthcare_data(n=100, seed=45),
        carf_validation={"expected_domain": "complicated", "expect_causal_evidence": True, "effect_direction": "negative"},
        llm_comparison={"check_domain": True, "check_causal_reasoning": True},
    ),
    # Energy — Complex (Bayesian with 60 frequency deviation observations)
    BenchmarkScenario(
        name="Renewable Grid Stability Uncertainty",
        domain="complex",
        industry="energy",
        query="What probes should we design to understand how increasing renewable penetration affects grid frequency stability?",
        context={
            "hypothesis": "Higher renewable share increases frequency deviation uncertainty",
            "uncertainty_factors": ["intermittency", "storage_capacity", "demand_response"],
            "bayesian_inference": {
                "observations": _generate_bayesian_observations(mean=0.02, std=0.01, n=60, seed=48),
                "draws": 500, "tune": 500, "chains": 2, "target_accept": 0.9, "seed": 48,
            },
        },
        carf_validation={"expected_domain": "complex", "expect_response": True, "expect_bayesian_evidence": True},
        llm_comparison={"check_uncertainty_acknowledgment": True, "check_probe_suggestion": True},
    ),
    # Disorder — Ambiguous
    BenchmarkScenario(
        name="Ambiguous Strategy Question",
        domain="disorder",
        industry="general",
        query="Should we do something about the thing?",
        context={"type": "ambiguous"},
        carf_validation={"expected_domain": "disorder", "expect_escalation": True},
        llm_comparison={"check_clarification_request": True},
    ),
    # Energy — Complicated (80 rows)
    BenchmarkScenario(
        name="Energy Grid Efficiency",
        domain="complicated",
        industry="energy",
        query="What is the causal effect of smart grid upgrades on transmission loss percentage?",
        context={"hypothesis": "Smart grid upgrades reduce transmission losses",
                 "treatment_variable": "smart_grid", "outcome_variable": "transmission_loss_pct"},
        data=_generate_energy_grid_data(n=80, seed=46),
        carf_validation={"expected_domain": "complicated", "expect_causal_evidence": True, "effect_direction": "negative"},
        llm_comparison={"check_domain": True, "check_causal_reasoning": True},
    ),
    # Insurance — Chaotic
    BenchmarkScenario(
        name="Insurance Fraud Detection",
        domain="chaotic",
        industry="financial_risk",
        query="URGENT: Coordinated fraud ring detected - 47 identical claims filed across 12 states in 30 minutes using synthetic identities. Estimated exposure $3.2M.",
        context={"type": "crisis", "severity": "critical"},
        carf_validation={"expected_domain": "chaotic", "expect_escalation": True, "expect_action_type": "emergency_stop"},
        llm_comparison={"check_urgency": True, "check_action_recommendation": True},
    ),
    # Finance — Complex (Bayesian with 50 daily return observations)
    BenchmarkScenario(
        name="Market Recovery Uncertainty",
        domain="complex",
        industry="financial_risk",
        query="Given the recent market crash, how uncertain are we about the pace and magnitude of recovery? What safe-to-fail probes for portfolio re-entry?",
        context={
            "hypothesis": "Market recovery is underway but pace is highly uncertain",
            "uncertainty_factors": ["monetary_policy", "corporate_earnings", "geopolitical_risk"],
            "bayesian_inference": {
                "observations": _generate_bayesian_observations(mean=0.003, std=0.025, n=50, seed=49),
                "draws": 500, "tune": 500, "chains": 2, "target_accept": 0.9, "seed": 49,
            },
        },
        carf_validation={"expected_domain": "complex", "expect_response": True, "expect_bayesian_evidence": True},
        llm_comparison={"check_uncertainty_acknowledgment": True},
    ),
    # Disorder — Contradictory
    BenchmarkScenario(
        name="Contradictory Requirements",
        domain="disorder",
        industry="general",
        query="We need to simultaneously cut costs by 40%, increase headcount by 25%, launch in 3 new markets, and reduce operational risk to zero. The board expects all of this by next quarter.",
        context={"type": "ambiguous", "contradictions": ["cut_costs_vs_increase_headcount", "expand_vs_zero_risk"]},
        carf_validation={"expected_domain": "disorder", "expect_escalation": True},
        llm_comparison={"check_clarification_request": True},
    ),
]


# ── Pipeline Runners ─────────────────────────────────────────────────────

async def run_carf_scenario(scenario: BenchmarkScenario) -> dict[str, Any]:
    """Run a scenario through the full CARF pipeline."""
    from src.workflows.graph import run_carf
    context: dict[str, Any] = dict(scenario.context)
    if scenario.data:
        context["benchmark_data"] = scenario.data
    start_time = time.perf_counter()
    try:
        state = await run_carf(user_input=scenario.query, context=context)
        duration_ms = (time.perf_counter() - start_time) * 1000
        return {
            "success": True,
            "domain": state.cynefin_domain.value,
            "confidence": state.domain_confidence,
            "has_causal_evidence": state.causal_evidence is not None,
            "has_bayesian_evidence": state.bayesian_evidence is not None,
            "escalation": state.should_escalate_to_human(),
            "action_type": state.proposed_action.get("action_type") if state.proposed_action else None,
            "guardian_verdict": state.guardian_verdict.value if state.guardian_verdict else None,
            "has_response": state.final_response is not None,
            "reasoning_steps": len(state.reasoning_chain),
            "duration_ms": round(duration_ms, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "duration_ms": round((time.perf_counter() - start_time) * 1000, 2)}


async def run_llm_scenario(scenario: BenchmarkScenario) -> dict[str, Any]:
    """Run a scenario through the raw LLM baseline."""
    try:
        from benchmarks.baselines.raw_llm_baseline import get_llm_response
        result = await get_llm_response(scenario.query, scenario.context)
        return {"success": True, "domain": result.get("domain", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "action_type": result.get("action_type"), "duration_ms": result.get("duration_ms", 0.0)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_carf_result(result: dict, validation: dict) -> dict[str, bool]:
    """Validate CARF result against expected criteria."""
    checks: dict[str, bool] = {}
    if not result.get("success"):
        return {"pipeline_success": False}
    if "expected_domain" in validation:
        checks["domain_match"] = result["domain"].lower() == validation["expected_domain"].lower()
    if validation.get("expect_causal_evidence"):
        checks["has_causal_evidence"] = result.get("has_causal_evidence", False)
    if validation.get("expect_bayesian_evidence"):
        checks["has_bayesian_evidence"] = result.get("has_bayesian_evidence", False)
    if validation.get("expect_escalation"):
        checks["escalation_triggered"] = result.get("escalation", False)
    if "expect_action_type" in validation:
        checks["action_type_match"] = result.get("action_type") == validation["expect_action_type"]
    if validation.get("expect_response"):
        checks["has_response"] = result.get("has_response", False)
    return checks


async def run_all_scenarios(
    industries: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run all benchmark scenarios."""
    scenarios = SCENARIOS
    if industries:
        scenarios = [s for s in scenarios if s.industry in industries]

    logger.info(f"Running {len(scenarios)} e2e benchmark scenarios...")
    total_data_rows = sum(len(s.data) for s in scenarios)
    logger.info(f"Total data rows across all scenarios: {total_data_rows}")

    results = []
    for i, scenario in enumerate(scenarios):
        logger.info(f"\n[{i + 1}/{len(scenarios)}] {scenario.name} ({scenario.domain}/{scenario.industry}, {len(scenario.data)} rows)")
        logger.info("  Running CARF pipeline...")
        carf_result = await run_carf_scenario(scenario)
        logger.info("  Running LLM baseline...")
        llm_result = await run_llm_scenario(scenario)
        carf_checks = validate_carf_result(carf_result, scenario.carf_validation)
        carf_passed = all(carf_checks.values()) if carf_checks else False

        results.append({
            "scenario": scenario.name, "domain": scenario.domain, "industry": scenario.industry,
            "data_rows": len(scenario.data),
            "carf": {"result": carf_result, "validation": carf_checks, "passed": carf_passed},
            "llm_baseline": {"result": llm_result},
            "comparison": {
                "carf_domain_correct": carf_result.get("domain", "").lower() == scenario.domain,
                "llm_domain_correct": llm_result.get("domain", "").lower() == scenario.domain,
                "carf_faster": carf_result.get("duration_ms", float("inf")) < llm_result.get("duration_ms", float("inf")),
            },
        })

        status = "PASS" if carf_passed else "FAIL"
        logger.info(f"  CARF: {status} | Domain: {carf_result.get('domain')} | {carf_result.get('duration_ms', 0):.0f}ms")
        logger.info(f"  LLM:  Domain: {llm_result.get('domain')} | {llm_result.get('duration_ms', 0):.0f}ms")

    total = len(results)
    carf_passed = sum(1 for r in results if r["carf"]["passed"])
    carf_domain_correct = sum(1 for r in results if r["comparison"]["carf_domain_correct"])
    llm_domain_correct = sum(1 for r in results if r["comparison"]["llm_domain_correct"])

    domain_stats: dict[str, dict[str, int]] = {}
    for r in results:
        d = r["domain"]
        if d not in domain_stats:
            domain_stats[d] = {"total": 0, "passed": 0, "domain_correct": 0}
        domain_stats[d]["total"] += 1
        if r["carf"]["passed"]:
            domain_stats[d]["passed"] += 1
        if r["comparison"]["carf_domain_correct"]:
            domain_stats[d]["domain_correct"] += 1

    summary = {
        "total_scenarios": total,
        "total_data_rows": total_data_rows,
        "carf_passed": carf_passed,
        "carf_pass_rate": carf_passed / total if total else 0,
        "carf_domain_accuracy": carf_domain_correct / total if total else 0,
        "llm_domain_accuracy": llm_domain_correct / total if total else 0,
        "domain_breakdown": domain_stats,
        "results": results,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"\nResults written to {output_path}")

    logger.info(f"\n{'='*60}")
    logger.info(f"E2E Benchmark Summary:")
    logger.info(f"  Total scenarios:      {total} ({total_data_rows} data rows)")
    logger.info(f"  CARF pass rate:       {carf_passed}/{total} ({carf_passed / total:.1%})")
    logger.info(f"  CARF domain accuracy: {carf_domain_correct}/{total} ({carf_domain_correct / total:.1%})")
    logger.info(f"  LLM domain accuracy:  {llm_domain_correct}/{total} ({llm_domain_correct / total:.1%})")
    for domain, stats in sorted(domain_stats.items()):
        logger.info(f"    {domain:12s}: {stats['passed']}/{stats['total']} passed, {stats['domain_correct']}/{stats['total']} domain correct")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end use case benchmarks")
    parser.add_argument("--scenarios", type=str, default=None, help="Comma-separated industry filter")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "e2e_results.json")
    args = parser.parse_args()
    industries = args.scenarios.split(",") if args.scenarios else None
    asyncio.run(run_all_scenarios(industries=industries, output_path=args.output))


if __name__ == "__main__":
    main()
