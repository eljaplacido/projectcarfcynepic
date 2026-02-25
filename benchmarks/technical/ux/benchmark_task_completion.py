# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF UX — Task Completion Rate & Time-to-Insight (H32).

Measures task completion success rate and time-to-insight across 20 CARF task
scenarios spanning all four Cynefin domains plus governance tasks.  Each task
is executed via the CARF pipeline (or mock where appropriate) and timed.

Task categories:
  - 5 Clear domain tasks (simple lookups)
  - 5 Complicated domain tasks (causal analysis)
  - 5 Complex domain tasks (Bayesian probing)
  - 5 Governance tasks (policy review, compliance check)

Metrics:
  - success_rate >= 0.90 (completed without error)
  - avg_time_to_insight (informational — seconds to meaningful output)

Usage:
    python benchmarks/technical/ux/benchmark_task_completion.py
    python benchmarks/technical/ux/benchmark_task_completion.py -o results.json
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
logger = logging.getLogger("benchmark.task_completion")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Task Definitions ─────────────────────────────────────────────────────

TASK_SCENARIOS: list[dict[str, Any]] = [
    # ── Clear Domain Tasks (5) ────────────────────────────────────────────
    {
        "name": "clear_exchange_rate",
        "category": "Clear",
        "description": "Look up the current USD to EUR exchange rate",
        "query": "What is the current USD to EUR exchange rate?",
        "context": {},
        "expected_steps": 3,
        "max_time_seconds": 10.0,
        "success_criteria": "Response contains a numeric exchange rate value",
    },
    {
        "name": "clear_unit_conversion",
        "category": "Clear",
        "description": "Convert kilowatt-hours to megawatt-hours",
        "query": "How many kilowatt-hours are in a megawatt-hour?",
        "context": {},
        "expected_steps": 3,
        "max_time_seconds": 10.0,
        "success_criteria": "Response contains the conversion factor (1000)",
    },
    {
        "name": "clear_vat_rate",
        "category": "Clear",
        "description": "Look up the standard VAT rate in Germany",
        "query": "What is the standard VAT rate in Germany?",
        "context": {},
        "expected_steps": 3,
        "max_time_seconds": 10.0,
        "success_criteria": "Response references the VAT rate",
    },
    {
        "name": "clear_metric_conversion",
        "category": "Clear",
        "description": "Convert 100 miles to kilometers",
        "query": "Convert 100 miles to kilometers",
        "context": {},
        "expected_steps": 3,
        "max_time_seconds": 10.0,
        "success_criteria": "Response contains a numeric kilometers value",
    },
    {
        "name": "clear_boiling_point",
        "category": "Clear",
        "description": "Look up the boiling point of water at sea level",
        "query": "What is the boiling point of water at sea level in Celsius?",
        "context": {},
        "expected_steps": 3,
        "max_time_seconds": 10.0,
        "success_criteria": "Response contains 100 degrees Celsius",
    },
    # ── Complicated Domain Tasks (5) ──────────────────────────────────────
    {
        "name": "complicated_marketing_spend",
        "category": "Complicated",
        "description": "Analyze causal effect of marketing spend on revenue",
        "query": "How does increasing marketing spend affect quarterly revenue?",
        "context": {
            "industry": "marketing",
            "causal_estimation": {
                "treatment": "marketing_spend_k",
                "outcome": "quarterly_revenue_k",
                "covariates": ["market_size_index", "competition_index", "season_q"],
                "method_name": "backdoor.linear_regression",
                "data": [
                    {"marketing_spend_k": 50, "quarterly_revenue_k": 320, "market_size_index": 0.7, "competition_index": 0.4, "season_q": 1},
                    {"marketing_spend_k": 80, "quarterly_revenue_k": 410, "market_size_index": 0.7, "competition_index": 0.5, "season_q": 2},
                    {"marketing_spend_k": 30, "quarterly_revenue_k": 280, "market_size_index": 0.6, "competition_index": 0.4, "season_q": 3},
                    {"marketing_spend_k": 100, "quarterly_revenue_k": 480, "market_size_index": 0.8, "competition_index": 0.3, "season_q": 4},
                    {"marketing_spend_k": 60, "quarterly_revenue_k": 350, "market_size_index": 0.7, "competition_index": 0.5, "season_q": 1},
                    {"marketing_spend_k": 90, "quarterly_revenue_k": 440, "market_size_index": 0.8, "competition_index": 0.4, "season_q": 2},
                    {"marketing_spend_k": 40, "quarterly_revenue_k": 300, "market_size_index": 0.6, "competition_index": 0.6, "season_q": 3},
                    {"marketing_spend_k": 110, "quarterly_revenue_k": 520, "market_size_index": 0.9, "competition_index": 0.3, "season_q": 4},
                    {"marketing_spend_k": 70, "quarterly_revenue_k": 380, "market_size_index": 0.7, "competition_index": 0.5, "season_q": 1},
                    {"marketing_spend_k": 55, "quarterly_revenue_k": 340, "market_size_index": 0.6, "competition_index": 0.4, "season_q": 2},
                    {"marketing_spend_k": 85, "quarterly_revenue_k": 420, "market_size_index": 0.8, "competition_index": 0.4, "season_q": 3},
                    {"marketing_spend_k": 45, "quarterly_revenue_k": 310, "market_size_index": 0.7, "competition_index": 0.5, "season_q": 4},
                    {"marketing_spend_k": 95, "quarterly_revenue_k": 460, "market_size_index": 0.8, "competition_index": 0.3, "season_q": 1},
                    {"marketing_spend_k": 35, "quarterly_revenue_k": 290, "market_size_index": 0.6, "competition_index": 0.6, "season_q": 2},
                    {"marketing_spend_k": 75, "quarterly_revenue_k": 390, "market_size_index": 0.7, "competition_index": 0.4, "season_q": 3},
                    {"marketing_spend_k": 65, "quarterly_revenue_k": 360, "market_size_index": 0.7, "competition_index": 0.5, "season_q": 4},
                    {"marketing_spend_k": 105, "quarterly_revenue_k": 500, "market_size_index": 0.9, "competition_index": 0.3, "season_q": 1},
                    {"marketing_spend_k": 25, "quarterly_revenue_k": 260, "market_size_index": 0.5, "competition_index": 0.6, "season_q": 2},
                    {"marketing_spend_k": 120, "quarterly_revenue_k": 540, "market_size_index": 0.9, "competition_index": 0.2, "season_q": 3},
                    {"marketing_spend_k": 50, "quarterly_revenue_k": 330, "market_size_index": 0.7, "competition_index": 0.4, "season_q": 4},
                ],
            },
        },
        "expected_steps": 5,
        "max_time_seconds": 30.0,
        "success_criteria": "Response includes causal analysis or effect estimate",
    },
    {
        "name": "complicated_training_productivity",
        "category": "Complicated",
        "description": "Estimate causal effect of employee training on productivity",
        "query": "What is the causal effect of employee training hours on productivity?",
        "context": {
            "industry": "hr",
            "causal_estimation": {
                "treatment": "training_hours",
                "outcome": "productivity_score",
                "covariates": ["experience_years", "department_size", "role_level"],
                "method_name": "backdoor.linear_regression",
                "data": [
                    {"training_hours": 20, "productivity_score": 72, "experience_years": 3, "department_size": 15, "role_level": 2},
                    {"training_hours": 40, "productivity_score": 81, "experience_years": 5, "department_size": 20, "role_level": 3},
                    {"training_hours": 10, "productivity_score": 65, "experience_years": 1, "department_size": 10, "role_level": 1},
                    {"training_hours": 35, "productivity_score": 78, "experience_years": 4, "department_size": 18, "role_level": 2},
                    {"training_hours": 50, "productivity_score": 88, "experience_years": 7, "department_size": 25, "role_level": 4},
                    {"training_hours": 15, "productivity_score": 68, "experience_years": 2, "department_size": 12, "role_level": 1},
                    {"training_hours": 30, "productivity_score": 76, "experience_years": 3, "department_size": 16, "role_level": 2},
                    {"training_hours": 45, "productivity_score": 85, "experience_years": 6, "department_size": 22, "role_level": 3},
                    {"training_hours": 25, "productivity_score": 74, "experience_years": 4, "department_size": 14, "role_level": 2},
                    {"training_hours": 55, "productivity_score": 90, "experience_years": 8, "department_size": 30, "role_level": 4},
                    {"training_hours": 5, "productivity_score": 60, "experience_years": 1, "department_size": 8, "role_level": 1},
                    {"training_hours": 38, "productivity_score": 80, "experience_years": 5, "department_size": 19, "role_level": 3},
                    {"training_hours": 22, "productivity_score": 73, "experience_years": 3, "department_size": 15, "role_level": 2},
                    {"training_hours": 48, "productivity_score": 87, "experience_years": 7, "department_size": 24, "role_level": 4},
                    {"training_hours": 12, "productivity_score": 66, "experience_years": 2, "department_size": 11, "role_level": 1},
                    {"training_hours": 32, "productivity_score": 77, "experience_years": 4, "department_size": 17, "role_level": 2},
                    {"training_hours": 42, "productivity_score": 83, "experience_years": 6, "department_size": 21, "role_level": 3},
                    {"training_hours": 28, "productivity_score": 75, "experience_years": 3, "department_size": 16, "role_level": 2},
                    {"training_hours": 18, "productivity_score": 70, "experience_years": 2, "department_size": 13, "role_level": 1},
                    {"training_hours": 60, "productivity_score": 92, "experience_years": 10, "department_size": 35, "role_level": 5},
                ],
            },
        },
        "expected_steps": 5,
        "max_time_seconds": 30.0,
        "success_criteria": "Response includes effect estimate or causal finding",
    },
    {
        "name": "complicated_supplier_diversification",
        "category": "Complicated",
        "description": "Analyze if supplier diversification reduces disruption",
        "query": "Does supplier diversification reduce supply chain disruption frequency?",
        "context": {"industry": "supply_chain"},
        "expected_steps": 5,
        "max_time_seconds": 30.0,
        "success_criteria": "Response provides causal analysis of diversification effect",
    },
    {
        "name": "complicated_pricing_impact",
        "category": "Complicated",
        "description": "Analyze the causal impact of pricing changes on customer retention",
        "query": "What is the causal impact of a 10% price increase on customer retention?",
        "context": {
            "industry": "retail",
            "causal_estimation": {
                "treatment": "price_increase_pct",
                "outcome": "retention_rate",
                "covariates": ["customer_tenure_months", "avg_monthly_spend", "loyalty_tier"],
                "method_name": "backdoor.linear_regression",
                "data": [
                    {"price_increase_pct": 5, "retention_rate": 0.92, "customer_tenure_months": 24, "avg_monthly_spend": 150, "loyalty_tier": 2},
                    {"price_increase_pct": 10, "retention_rate": 0.85, "customer_tenure_months": 12, "avg_monthly_spend": 80, "loyalty_tier": 1},
                    {"price_increase_pct": 15, "retention_rate": 0.78, "customer_tenure_months": 6, "avg_monthly_spend": 60, "loyalty_tier": 1},
                    {"price_increase_pct": 3, "retention_rate": 0.95, "customer_tenure_months": 36, "avg_monthly_spend": 200, "loyalty_tier": 3},
                    {"price_increase_pct": 8, "retention_rate": 0.88, "customer_tenure_months": 18, "avg_monthly_spend": 120, "loyalty_tier": 2},
                    {"price_increase_pct": 12, "retention_rate": 0.82, "customer_tenure_months": 10, "avg_monthly_spend": 90, "loyalty_tier": 1},
                    {"price_increase_pct": 20, "retention_rate": 0.70, "customer_tenure_months": 4, "avg_monthly_spend": 50, "loyalty_tier": 1},
                    {"price_increase_pct": 7, "retention_rate": 0.90, "customer_tenure_months": 20, "avg_monthly_spend": 130, "loyalty_tier": 2},
                    {"price_increase_pct": 10, "retention_rate": 0.87, "customer_tenure_months": 30, "avg_monthly_spend": 180, "loyalty_tier": 3},
                    {"price_increase_pct": 5, "retention_rate": 0.93, "customer_tenure_months": 28, "avg_monthly_spend": 160, "loyalty_tier": 2},
                    {"price_increase_pct": 15, "retention_rate": 0.80, "customer_tenure_months": 8, "avg_monthly_spend": 70, "loyalty_tier": 1},
                    {"price_increase_pct": 2, "retention_rate": 0.96, "customer_tenure_months": 48, "avg_monthly_spend": 250, "loyalty_tier": 3},
                    {"price_increase_pct": 18, "retention_rate": 0.73, "customer_tenure_months": 5, "avg_monthly_spend": 55, "loyalty_tier": 1},
                    {"price_increase_pct": 6, "retention_rate": 0.91, "customer_tenure_months": 22, "avg_monthly_spend": 140, "loyalty_tier": 2},
                    {"price_increase_pct": 10, "retention_rate": 0.86, "customer_tenure_months": 15, "avg_monthly_spend": 100, "loyalty_tier": 1},
                    {"price_increase_pct": 4, "retention_rate": 0.94, "customer_tenure_months": 32, "avg_monthly_spend": 190, "loyalty_tier": 3},
                    {"price_increase_pct": 12, "retention_rate": 0.83, "customer_tenure_months": 11, "avg_monthly_spend": 95, "loyalty_tier": 1},
                    {"price_increase_pct": 8, "retention_rate": 0.89, "customer_tenure_months": 26, "avg_monthly_spend": 170, "loyalty_tier": 2},
                    {"price_increase_pct": 14, "retention_rate": 0.79, "customer_tenure_months": 7, "avg_monthly_spend": 65, "loyalty_tier": 1},
                    {"price_increase_pct": 9, "retention_rate": 0.88, "customer_tenure_months": 19, "avg_monthly_spend": 125, "loyalty_tier": 2},
                ],
            },
        },
        "expected_steps": 5,
        "max_time_seconds": 30.0,
        "success_criteria": "Response includes directional effect or elasticity analysis",
    },
    {
        "name": "complicated_remote_work_performance",
        "category": "Complicated",
        "description": "Analyze how remote work policy affects team performance",
        "query": "How does our remote work policy affect team performance metrics?",
        "context": {
            "industry": "hr",
            "causal_estimation": {
                "treatment": "remote_days_per_week",
                "outcome": "performance_score",
                "covariates": ["team_size", "tenure_years", "role_seniority"],
                "method_name": "backdoor.linear_regression",
                "data": [
                    {"remote_days_per_week": 0, "performance_score": 72, "team_size": 8, "tenure_years": 3, "role_seniority": 2},
                    {"remote_days_per_week": 1, "performance_score": 75, "team_size": 10, "tenure_years": 4, "role_seniority": 2},
                    {"remote_days_per_week": 2, "performance_score": 80, "team_size": 6, "tenure_years": 5, "role_seniority": 3},
                    {"remote_days_per_week": 3, "performance_score": 82, "team_size": 12, "tenure_years": 6, "role_seniority": 3},
                    {"remote_days_per_week": 4, "performance_score": 78, "team_size": 9, "tenure_years": 2, "role_seniority": 2},
                    {"remote_days_per_week": 5, "performance_score": 74, "team_size": 7, "tenure_years": 1, "role_seniority": 1},
                    {"remote_days_per_week": 2, "performance_score": 81, "team_size": 11, "tenure_years": 7, "role_seniority": 4},
                    {"remote_days_per_week": 3, "performance_score": 83, "team_size": 8, "tenure_years": 5, "role_seniority": 3},
                    {"remote_days_per_week": 1, "performance_score": 76, "team_size": 14, "tenure_years": 3, "role_seniority": 2},
                    {"remote_days_per_week": 0, "performance_score": 70, "team_size": 6, "tenure_years": 2, "role_seniority": 1},
                    {"remote_days_per_week": 4, "performance_score": 79, "team_size": 10, "tenure_years": 4, "role_seniority": 3},
                    {"remote_days_per_week": 2, "performance_score": 82, "team_size": 9, "tenure_years": 8, "role_seniority": 4},
                    {"remote_days_per_week": 5, "performance_score": 73, "team_size": 5, "tenure_years": 1, "role_seniority": 1},
                    {"remote_days_per_week": 3, "performance_score": 84, "team_size": 13, "tenure_years": 6, "role_seniority": 3},
                    {"remote_days_per_week": 1, "performance_score": 74, "team_size": 7, "tenure_years": 2, "role_seniority": 2},
                    {"remote_days_per_week": 2, "performance_score": 79, "team_size": 8, "tenure_years": 4, "role_seniority": 2},
                    {"remote_days_per_week": 4, "performance_score": 77, "team_size": 11, "tenure_years": 3, "role_seniority": 2},
                    {"remote_days_per_week": 3, "performance_score": 85, "team_size": 9, "tenure_years": 9, "role_seniority": 5},
                    {"remote_days_per_week": 0, "performance_score": 71, "team_size": 15, "tenure_years": 2, "role_seniority": 1},
                    {"remote_days_per_week": 5, "performance_score": 76, "team_size": 6, "tenure_years": 3, "role_seniority": 2},
                ],
            },
        },
        "expected_steps": 5,
        "max_time_seconds": 30.0,
        "success_criteria": "Response provides causal or analytical assessment",
    },
    # ── Complex Domain Tasks (5) ──────────────────────────────────────────
    {
        "name": "complex_market_entry",
        "category": "Complex",
        "description": "Bayesian probing for market entry under regulatory uncertainty",
        "query": "Should we enter the Asian market given uncertain regulatory changes?",
        "context": {
            "industry": "fintech",
            "bayesian_inference": {
                "observations": [0.08, 0.12, -0.05, 0.15, 0.03, 0.09, -0.02,
                                 0.11, 0.07, 0.14, 0.01, 0.06, 0.13, -0.01,
                                 0.10, 0.05, 0.08, 0.16, -0.03, 0.09],
            },
        },
        "expected_steps": 6,
        "max_time_seconds": 45.0,
        "success_criteria": "Response includes Bayesian uncertainty or posterior estimate",
    },
    {
        "name": "complex_climate_adaptation",
        "category": "Complex",
        "description": "Bayesian probing for climate adaptation strategy in agriculture",
        "query": "What strategy should we adopt for climate adaptation in agriculture?",
        "context": {
            "industry": "agriculture",
            "bayesian_inference": {
                "observations": [4.5, 5.1, 3.9, 4.8, 4.2, 5.3, 4.0, 4.7,
                                 3.8, 5.0, 4.6, 4.1, 5.2, 3.7, 4.4, 4.9,
                                 4.3, 5.1, 3.6, 4.8, 4.5, 5.0, 4.2, 4.7, 3.9],
            },
        },
        "expected_steps": 6,
        "max_time_seconds": 45.0,
        "success_criteria": "Response includes probabilistic strategy recommendation",
    },
    {
        "name": "complex_rnd_budget",
        "category": "Complex",
        "description": "Bayesian probing for R&D budget allocation under uncertainty",
        "query": "How should we allocate R&D budget under technological uncertainty?",
        "context": {
            "industry": "technology",
            "bayesian_inference": {
                "observations": [0.12, 0.15, 0.08, 0.11, 0.14, 0.09, 0.13,
                                 0.10, 0.16, 0.07, 0.12, 0.11, 0.14, 0.08,
                                 0.13, 0.10, 0.15, 0.09, 0.12, 0.11],
            },
        },
        "expected_steps": 6,
        "max_time_seconds": 45.0,
        "success_criteria": "Response includes uncertainty quantification or Bayesian estimate",
    },
    {
        "name": "complex_cybersecurity_threat",
        "category": "Complex",
        "description": "Bayesian probing for emerging cybersecurity threat assessment",
        "query": "What is the probability of a major cybersecurity breach in the next quarter?",
        "context": {
            "industry": "security",
            "bayesian_inference": {
                "observations": [0.02, 0.05, 0.01, 0.03, 0.08, 0.02, 0.04,
                                 0.01, 0.06, 0.03, 0.02, 0.07, 0.01, 0.04,
                                 0.03, 0.05, 0.02, 0.09, 0.01, 0.03],
            },
        },
        "expected_steps": 6,
        "max_time_seconds": 45.0,
        "success_criteria": "Response includes probability estimate with uncertainty bounds",
    },
    {
        "name": "complex_demand_forecast",
        "category": "Complex",
        "description": "Bayesian probing for demand forecasting under supply chain disruption",
        "query": "How should we adjust our demand forecast given ongoing supply chain disruptions?",
        "context": {
            "industry": "logistics",
            "bayesian_inference": {
                "observations": [1200, 1150, 980, 1100, 1050, 900, 1080, 1020,
                                 950, 1130, 1060, 870, 1010, 990, 1140, 1070,
                                 920, 1090, 1000, 960],
            },
        },
        "expected_steps": 6,
        "max_time_seconds": 45.0,
        "success_criteria": "Response provides adjusted forecast with credible intervals",
    },
    # ── Governance Tasks (5) ──────────────────────────────────────────────
    {
        "name": "governance_policy_review",
        "category": "Governance",
        "description": "Review active governance policies for a specific domain",
        "query": "Review all active procurement policies and their compliance status",
        "context": {"governance_action": "policy_review", "domain": "procurement"},
        "expected_steps": 4,
        "max_time_seconds": 15.0,
        "success_criteria": "Pipeline completes and returns governance-relevant response",
    },
    {
        "name": "governance_compliance_check",
        "category": "Governance",
        "description": "Run EU AI Act compliance check",
        "query": "Run a compliance assessment against the EU AI Act for our AI system",
        "context": {"governance_action": "compliance_check", "framework": "eu_ai_act"},
        "expected_steps": 4,
        "max_time_seconds": 15.0,
        "success_criteria": "Pipeline completes with compliance-relevant output",
    },
    {
        "name": "governance_conflict_detection",
        "category": "Governance",
        "description": "Detect conflicts between procurement and sustainability policies",
        "query": ("Our emergency procurement policy allows $500K spending but the "
                  "sustainability policy requires green-certified vendors only"),
        "context": {"governance_action": "conflict_detection"},
        "expected_steps": 4,
        "max_time_seconds": 15.0,
        "success_criteria": "Pipeline completes and identifies cross-domain concern",
    },
    {
        "name": "governance_audit_trail",
        "category": "Governance",
        "description": "Query the audit trail for a recent governance decision",
        "query": "Show the audit trail for the most recent governance decision on procurement",
        "context": {"governance_action": "audit_trail", "domain": "procurement"},
        "expected_steps": 4,
        "max_time_seconds": 15.0,
        "success_criteria": "Pipeline completes and returns audit-relevant response",
    },
    {
        "name": "governance_cost_analysis",
        "category": "Governance",
        "description": "Analyze the cost breakdown for recent LLM-powered queries",
        "query": "What is the cost breakdown for our last 10 AI-powered governance queries?",
        "context": {"governance_action": "cost_analysis"},
        "expected_steps": 4,
        "max_time_seconds": 15.0,
        "success_criteria": "Pipeline completes with cost-relevant output",
    },
]


# ── Task Executor ────────────────────────────────────────────────────────


async def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    """Execute a single task scenario through the CARF pipeline.

    Returns timing and success information.
    """
    from src.workflows.graph import run_carf

    t0 = time.perf_counter()
    error_msg: str | None = None
    steps_taken = 0
    success = False

    try:
        final_state = await run_carf(
            user_input=task["query"],
            context=task.get("context", {}),
        )
        elapsed_s = time.perf_counter() - t0

        # Count reasoning steps as a proxy for pipeline steps
        steps_taken = len(getattr(final_state, "reasoning_chain", [])) or 1

        # Success = we got a non-empty final response without error
        has_response = bool(getattr(final_state, "final_response", None))
        within_time = elapsed_s <= task["max_time_seconds"]
        success = has_response and within_time

    except Exception as exc:
        elapsed_s = time.perf_counter() - t0
        error_msg = f"{type(exc).__name__}: {exc}"
        success = False

    return {
        "task_name": task["name"],
        "category": task["category"],
        "description": task["description"],
        "success": success,
        "time_to_complete_s": round(elapsed_s, 3),
        "max_time_seconds": task["max_time_seconds"],
        "within_time_limit": elapsed_s <= task["max_time_seconds"],
        "steps_taken": steps_taken,
        "expected_steps": task["expected_steps"],
        "error": error_msg,
    }


# ── Benchmark Runner ─────────────────────────────────────────────────────


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the task completion benchmark across all 20 scenarios."""
    logger.info("=" * 70)
    logger.info("CARF UX Benchmark — Task Completion Rate & Time-to-Insight (H32)")
    logger.info("=" * 70)

    t0_total = time.perf_counter()
    individual_results: list[dict[str, Any]] = []

    for i, task in enumerate(TASK_SCENARIOS, 1):
        logger.info(f"  [{i}/{len(TASK_SCENARIOS)}] {task['category']}: {task['name']}")
        result = await execute_task(task)
        individual_results.append(result)

        status = "PASS" if result["success"] else "FAIL"
        logger.info(f"    {status} — {result['time_to_complete_s']:.2f}s "
                     f"(limit: {result['max_time_seconds']:.0f}s)")
        if result["error"]:
            logger.info(f"    Error: {result['error'][:100]}")

    total_elapsed_s = time.perf_counter() - t0_total

    # Aggregate by category
    categories = ["Clear", "Complicated", "Complex", "Governance"]
    category_stats: dict[str, dict[str, Any]] = {}

    for cat in categories:
        cat_results = [r for r in individual_results if r["category"] == cat]
        if not cat_results:
            continue
        cat_successes = sum(1 for r in cat_results if r["success"])
        cat_times = [r["time_to_complete_s"] for r in cat_results if r["success"]]
        category_stats[cat] = {
            "total": len(cat_results),
            "successful": cat_successes,
            "success_rate": round(cat_successes / len(cat_results), 4),
            "avg_time_s": round(sum(cat_times) / len(cat_times), 3) if cat_times else 0.0,
            "max_time_s": round(max(cat_times), 3) if cat_times else 0.0,
        }

    # Overall metrics
    total_tasks = len(individual_results)
    successful_tasks = sum(1 for r in individual_results if r["success"])
    success_rate = successful_tasks / total_tasks if total_tasks else 0.0

    successful_times = [r["time_to_complete_s"] for r in individual_results if r["success"]]
    avg_time_to_insight = (
        sum(successful_times) / len(successful_times)
        if successful_times else 0.0
    )

    metrics = {
        "success_rate": round(success_rate, 4),
        "avg_time_to_insight": round(avg_time_to_insight, 3),
        "total_tasks": total_tasks,
        "successful_tasks": successful_tasks,
        "failed_tasks": total_tasks - successful_tasks,
        "threshold_success_rate": 0.90,
        "meets_threshold": success_rate >= 0.90,
    }

    report = {
        "benchmark": "carf_task_completion",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_s": round(total_elapsed_s, 2),
        "metrics": metrics,
        "category_stats": category_stats,
        "individual_results": individual_results,
    }

    # Summary
    logger.info("")
    logger.info(f"  Total Tasks:           {total_tasks}")
    logger.info(f"  Successful:            {successful_tasks}/{total_tasks}")
    logger.info(f"  Success Rate:          {success_rate:.1%} (threshold: 90%)")
    logger.info(f"  Avg Time-to-Insight:   {avg_time_to_insight:.2f}s")
    logger.info("")
    for cat, stats in category_stats.items():
        logger.info(f"    {cat:<14} {stats['successful']}/{stats['total']} "
                     f"({stats['success_rate']:.0%}), avg={stats['avg_time_s']:.2f}s")
    logger.info("=" * 70)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="task_completion", source_reference="benchmark:task_completion", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CARF UX — Task Completion Rate & Time-to-Insight (H32)",
    )
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(output_path=args.output))


if __name__ == "__main__":
    main()
