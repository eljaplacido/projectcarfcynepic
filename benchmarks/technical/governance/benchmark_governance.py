# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
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
    # ── 20 more cross-domain pairs ──────────────────────────────────────
    {
        "name": "hr_finance_link",
        "query": "The annual salary review for 200 employees requires a $1.2M "
                 "budget increase that must go through the compensation committee.",
        "expected_domains": {"hr", "finance"},
        "expected_entity_keywords": ["salary", "budget", "compensation"],
        "cross_domain_link": ("hr", "finance"),
    },
    {
        "name": "it_security_link",
        "query": "The migration to Azure cloud infrastructure requires a full "
                 "penetration test and firewall reconfiguration before go-live.",
        "expected_domains": {"it", "security"},
        "expected_entity_keywords": ["cloud", "penetration", "firewall"],
        "cross_domain_link": ("it", "security"),
    },
    {
        "name": "operations_sustainability_link",
        "query": "Our manufacturing plant needs to reduce energy consumption by 20% "
                 "to meet the 2030 net-zero operations target.",
        "expected_domains": {"operations", "sustainability"},
        "expected_entity_keywords": ["manufacturing", "energy", "net-zero"],
        "cross_domain_link": ("operations", "sustainability"),
    },
    {
        "name": "marketing_legal_link",
        "query": "The new product launch campaign makes health claims that need "
                 "legal review for FTC advertising compliance.",
        "expected_domains": {"marketing", "legal"},
        "expected_entity_keywords": ["campaign", "health", "compliance"],
        "cross_domain_link": ("marketing", "legal"),
    },
    {
        "name": "rnd_procurement_link",
        "query": "The R&D lab needs specialized reagents from a sole-source "
                 "supplier requiring a waiver to the competitive bidding policy.",
        "expected_domains": {"rnd", "procurement"},
        "expected_entity_keywords": ["reagent", "supplier", "bidding"],
        "cross_domain_link": ("rnd", "procurement"),
    },
    {
        "name": "hr_legal_link",
        "query": "The employee termination process must comply with local labor "
                 "laws and include a severance agreement reviewed by counsel.",
        "expected_domains": {"hr", "legal"},
        "expected_entity_keywords": ["termination", "labor", "severance"],
        "cross_domain_link": ("hr", "legal"),
    },
    {
        "name": "finance_procurement_link",
        "query": "The capital expenditure approval for $3M in new equipment "
                 "requires three competitive bids and CFO sign-off.",
        "expected_domains": {"finance", "procurement"},
        "expected_entity_keywords": ["capex", "bids", "equipment"],
        "cross_domain_link": ("finance", "procurement"),
    },
    {
        "name": "it_operations_link",
        "query": "The ERP system upgrade will cause 48 hours of downtime "
                 "affecting all warehouse and logistics operations.",
        "expected_domains": {"it", "operations"},
        "expected_entity_keywords": ["erp", "downtime", "warehouse"],
        "cross_domain_link": ("it", "operations"),
    },
    {
        "name": "security_sustainability_link",
        "query": "The physical security team needs to install solar-powered "
                 "surveillance cameras across all facilities to reduce grid load.",
        "expected_domains": {"security", "sustainability"},
        "expected_entity_keywords": ["security", "solar", "surveillance"],
        "cross_domain_link": ("security", "sustainability"),
    },
    {
        "name": "marketing_finance_link",
        "query": "The Q4 digital advertising budget of $800K needs reallocation "
                 "after the social media campaign underperformed by 40%.",
        "expected_domains": {"marketing", "finance"},
        "expected_entity_keywords": ["advertising", "budget", "campaign"],
        "cross_domain_link": ("marketing", "finance"),
    },
    {
        "name": "rnd_legal_link",
        "query": "The new patent filing for our AI algorithm must be completed "
                 "before the research paper is published next month.",
        "expected_domains": {"rnd", "legal"},
        "expected_entity_keywords": ["patent", "algorithm", "research"],
        "cross_domain_link": ("rnd", "legal"),
    },
    {
        "name": "hr_security_link",
        "query": "All new employee onboarding must include background checks "
                 "and cybersecurity awareness training within the first week.",
        "expected_domains": {"hr", "security"},
        "expected_entity_keywords": ["onboarding", "background", "cybersecurity"],
        "cross_domain_link": ("hr", "security"),
    },
    {
        "name": "operations_finance_link",
        "query": "The supply chain disruption increased shipping costs by 35%, "
                 "requiring a quarterly budget revision and logistics rerouting.",
        "expected_domains": {"operations", "finance"},
        "expected_entity_keywords": ["shipping", "budget", "logistics"],
        "cross_domain_link": ("operations", "finance"),
    },
    {
        "name": "procurement_legal_link",
        "query": "The vendor selection process for the $5M IT contract must "
                 "include anti-bribery due diligence and FCPA compliance checks.",
        "expected_domains": {"procurement", "legal"},
        "expected_entity_keywords": ["vendor", "anti-bribery", "fcpa"],
        "cross_domain_link": ("procurement", "legal"),
    },
    {
        "name": "it_finance_link",
        "query": "The SaaS license renewal for 500 seats at $120/user/year "
                 "needs approval from both IT governance and the finance team.",
        "expected_domains": {"it", "finance"},
        "expected_entity_keywords": ["saas", "license", "approval"],
        "cross_domain_link": ("it", "finance"),
    },
    {
        "name": "sustainability_legal_link",
        "query": "Our carbon offset credits must be verified against the EU "
                 "Emissions Trading System regulations before year-end reporting.",
        "expected_domains": {"sustainability", "legal"},
        "expected_entity_keywords": ["carbon", "offset", "regulations"],
        "cross_domain_link": ("sustainability", "legal"),
    },
    {
        "name": "hr_operations_link",
        "query": "The shift scheduling system needs to comply with the new "
                 "collective bargaining agreement limiting overtime to 10 hours/week.",
        "expected_domains": {"hr", "operations"},
        "expected_entity_keywords": ["shift", "bargaining", "overtime"],
        "cross_domain_link": ("hr", "operations"),
    },
    {
        "name": "rnd_finance_link",
        "query": "The R&D tax credit claim for $2.5M in qualified research "
                 "expenses requires documentation of all laboratory activities.",
        "expected_domains": {"rnd", "finance"},
        "expected_entity_keywords": ["tax", "credit", "research"],
        "cross_domain_link": ("rnd", "finance"),
    },
    {
        "name": "marketing_operations_link",
        "query": "The product launch event requires coordination between "
                 "marketing communications and warehouse fulfillment teams.",
        "expected_domains": {"marketing", "operations"},
        "expected_entity_keywords": ["launch", "marketing", "fulfillment"],
        "cross_domain_link": ("marketing", "operations"),
    },
    {
        "name": "rnd_sustainability_link",
        "query": "The new biodegradable packaging R&D project must align with "
                 "our circular economy targets and reduce plastic use by 60%.",
        "expected_domains": {"rnd", "sustainability"},
        "expected_entity_keywords": ["biodegradable", "packaging", "circular"],
        "cross_domain_link": ("rnd", "sustainability"),
    },
    # ── 10 triple-domain chains ─────────────────────────────────────────
    {
        "name": "triple_hr_finance_legal",
        "query": "The executive compensation restructuring requires board approval, "
                 "SEC disclosure filings, and updated employment agreements.",
        "expected_domains": {"hr", "finance", "legal"},
        "expected_entity_keywords": ["compensation", "sec", "employment"],
        "cross_domain_link": ("hr", "finance"),
    },
    {
        "name": "triple_it_security_legal",
        "query": "The data breach incident requires IT forensic analysis, "
                 "security patch deployment, and GDPR breach notification within 72 hours.",
        "expected_domains": {"it", "security", "legal"},
        "expected_entity_keywords": ["breach", "forensic", "gdpr"],
        "cross_domain_link": ("security", "legal"),
    },
    {
        "name": "triple_operations_sustainability_finance",
        "query": "The factory energy retrofit will cost $4M but is projected to "
                 "save $800K annually and reduce emissions by 30%.",
        "expected_domains": {"operations", "sustainability", "finance"},
        "expected_entity_keywords": ["retrofit", "emissions", "cost"],
        "cross_domain_link": ("operations", "sustainability"),
    },
    {
        "name": "triple_marketing_legal_finance",
        "query": "The influencer partnership program requires FTC disclosure "
                 "compliance, contract negotiation, and a $500K marketing budget.",
        "expected_domains": {"marketing", "legal", "finance"},
        "expected_entity_keywords": ["influencer", "ftc", "budget"],
        "cross_domain_link": ("marketing", "legal"),
    },
    {
        "name": "triple_rnd_procurement_finance",
        "query": "The prototype development phase requires sourcing specialized "
                 "components from three vendors with a combined budget of $1.8M.",
        "expected_domains": {"rnd", "procurement", "finance"},
        "expected_entity_keywords": ["prototype", "vendors", "budget"],
        "cross_domain_link": ("rnd", "procurement"),
    },
    {
        "name": "triple_hr_it_security",
        "query": "The remote work policy expansion requires VPN provisioning for "
                 "300 employees and multi-factor authentication enforcement.",
        "expected_domains": {"hr", "it", "security"},
        "expected_entity_keywords": ["remote", "vpn", "mfa"],
        "cross_domain_link": ("it", "security"),
    },
    {
        "name": "triple_procurement_sustainability_legal",
        "query": "All new supplier contracts must include ESG compliance clauses "
                 "aligned with the EU Corporate Sustainability Due Diligence Directive.",
        "expected_domains": {"procurement", "sustainability", "legal"},
        "expected_entity_keywords": ["supplier", "esg", "directive"],
        "cross_domain_link": ("procurement", "sustainability"),
    },
    {
        "name": "triple_operations_it_finance",
        "query": "The warehouse automation project requires $6M in robotic systems, "
                 "IT network upgrades, and revised operational budgets.",
        "expected_domains": {"operations", "it", "finance"},
        "expected_entity_keywords": ["warehouse", "automation", "budget"],
        "cross_domain_link": ("operations", "it"),
    },
    {
        "name": "triple_rnd_security_legal",
        "query": "The AI model training on customer data requires data anonymization "
                 "review, security clearance, and privacy impact assessment.",
        "expected_domains": {"rnd", "security", "legal"},
        "expected_entity_keywords": ["ai", "anonymization", "privacy"],
        "cross_domain_link": ("rnd", "security"),
    },
    {
        "name": "triple_hr_sustainability_operations",
        "query": "The green commuting incentive program for 1000 employees "
                 "needs updated HR policies and adjusted facility parking operations.",
        "expected_domains": {"hr", "sustainability", "operations"},
        "expected_entity_keywords": ["commuting", "incentive", "parking"],
        "cross_domain_link": ("hr", "sustainability"),
    },
    # ── 7 single-domain queries ─────────────────────────────────────────
    {
        "name": "hr_only",
        "query": "How many vacation days do employees accrue per year under "
                 "our current PTO policy?",
        "expected_domains": {"hr"},
        "expected_entity_keywords": ["vacation", "pto", "employees"],
        "cross_domain_link": None,
    },
    {
        "name": "legal_only",
        "query": "What is the statute of limitations for breach of contract "
                 "claims in our jurisdiction?",
        "expected_domains": {"legal"},
        "expected_entity_keywords": ["statute", "breach", "contract"],
        "cross_domain_link": None,
    },
    {
        "name": "security_only",
        "query": "What is the current status of our SOC2 Type II certification "
                 "audit findings?",
        "expected_domains": {"security"},
        "expected_entity_keywords": ["soc2", "certification", "audit"],
        "cross_domain_link": None,
    },
    {
        "name": "it_only",
        "query": "What is the uptime SLA for our production Kubernetes cluster "
                 "over the last 90 days?",
        "expected_domains": {"it"},
        "expected_entity_keywords": ["uptime", "sla", "kubernetes"],
        "cross_domain_link": None,
    },
    {
        "name": "procurement_only",
        "query": "List all approved vendors in our preferred supplier catalog "
                 "for office supplies.",
        "expected_domains": {"procurement"},
        "expected_entity_keywords": ["vendors", "supplier", "catalog"],
        "cross_domain_link": None,
    },
    {
        "name": "sustainability_only",
        "query": "What is our current Scope 1 greenhouse gas emissions baseline "
                 "measurement for the reporting year?",
        "expected_domains": {"sustainability"},
        "expected_entity_keywords": ["scope", "greenhouse", "emissions"],
        "cross_domain_link": None,
    },
    {
        "name": "operations_only",
        "query": "What is the current throughput rate for our main assembly line "
                 "in units per hour?",
        "expected_domains": {"operations"},
        "expected_entity_keywords": ["throughput", "assembly", "units"],
        "cross_domain_link": None,
    },
    # ── 5 null/no-domain queries ────────────────────────────────────────
    {
        "name": "no_domain_weather",
        "query": "What is the weather forecast for Tokyo this weekend?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
        "cross_domain_link": None,
    },
    {
        "name": "no_domain_personal",
        "query": "Can you recommend a good Italian restaurant near downtown?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
        "cross_domain_link": None,
    },
    {
        "name": "no_domain_trivia",
        "query": "Who won the FIFA World Cup in 2022?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
        "cross_domain_link": None,
    },
    {
        "name": "no_domain_math",
        "query": "What is the square root of 144?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
        "cross_domain_link": None,
    },
    {
        "name": "no_domain_greeting",
        "query": "Hello, how are you doing today?",
        "expected_domains": set(),
        "expected_entity_keywords": [],
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
    # ── Multi-provider scenarios ────────────────────────────────────────
    {
        "name": "deepseek_large_input_small_output",
        "input_tokens": 5_000_000,
        "output_tokens": 50_000,
        "provider": "deepseek",
        "expected_llm_cost": 0.714,  # 5M*0.14/1e6 + 50K*0.28/1e6 = 0.70 + 0.014
        "tolerance": 0.01,
    },
    {
        "name": "openai_small_input_large_output",
        "input_tokens": 100_000,
        "output_tokens": 2_000_000,
        "provider": "openai",
        "expected_llm_cost": 12.30,  # 100K*3.0/1e6 + 2M*6.0/1e6 = 0.30 + 12.0
        "tolerance": 0.01,
    },
    {
        "name": "anthropic_small_query",
        "input_tokens": 1_000,
        "output_tokens": 500,
        "provider": "anthropic",
        "expected_llm_cost": 0.0105,  # 1K*3.0/1e6 + 500*15.0/1e6 = 0.003 + 0.0075
        "tolerance": 0.001,
    },
    {
        "name": "openai_output_only",
        "input_tokens": 0,
        "output_tokens": 1_000_000,
        "provider": "openai",
        "expected_llm_cost": 6.00,  # 0 + 1M*6.0/1e6
        "tolerance": 0.01,
    },
    # ── Edge cases ──────────────────────────────────────────────────────
    {
        "name": "very_large_token_count_10M",
        "input_tokens": 10_000_000,
        "output_tokens": 10_000_000,
        "provider": "deepseek",
        "expected_llm_cost": 4.20,  # 10M*0.14/1e6 + 10M*0.28/1e6 = 1.40 + 2.80
        "tolerance": 0.01,
    },
    {
        "name": "fractional_tokens",
        "input_tokens": 1,
        "output_tokens": 1,
        "provider": "anthropic",
        "expected_llm_cost": 0.000018,  # 1*3.0/1e6 + 1*15.0/1e6 = 0.000003 + 0.000015
        "tolerance": 0.00001,
    },
    {
        "name": "negative_tokens_graceful",
        "input_tokens": -100,
        "output_tokens": -50,
        "provider": "deepseek",
        "expected_llm_cost": 0.00,  # Should handle gracefully, clamp to 0
        "tolerance": 0.01,
    },
    {
        "name": "mixed_ratio_anthropic",
        "input_tokens": 800_000,
        "output_tokens": 200_000,
        "provider": "anthropic",
        "expected_llm_cost": 5.40,  # 800K*3.0/1e6 + 200K*15.0/1e6 = 2.40 + 3.0
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
    # ── 13 more true conflicts ──────────────────────────────────────────
    {
        "name": "temporal_conflict_deadlines",
        "policy_a": {
            "name": "quarterly_reporting",
            "domain_id": "finance",
            "namespace": "finance.reporting",
            "rules": [{"name": "q_deadline", "condition": {"type": "reporting"},
                        "constraint": {"deadline": "2026-03-31", "max_spend": 100_000},
                        "message": "Q1 reporting deadline"}],
        },
        "policy_b": {
            "name": "audit_freeze",
            "domain_id": "finance",
            "namespace": "finance.audit",
            "rules": [{"name": "freeze_reporting", "condition": {"type": "reporting"},
                        "constraint": {"deadline": "2026-06-30", "max_spend": 0},
                        "message": "Freeze all reporting until audit complete"}],
        },
        "should_conflict": True,
        "conflict_type": "temporal_contradiction",
    },
    {
        "name": "resource_allocation_conflict",
        "policy_a": {
            "name": "it_expansion",
            "domain_id": "it",
            "namespace": "it.expansion",
            "rules": [{"name": "hire_devs", "condition": {"type": "hiring"},
                        "constraint": {"headcount": 50, "max_spend": 5_000_000},
                        "message": "Hire 50 developers"}],
        },
        "policy_b": {
            "name": "hiring_freeze",
            "domain_id": "hr",
            "namespace": "hr.freeze",
            "rules": [{"name": "no_hiring", "condition": {"type": "hiring"},
                        "constraint": {"headcount": 0, "max_spend": 0},
                        "message": "Company-wide hiring freeze"}],
        },
        "should_conflict": True,
        "conflict_type": "resource_contradiction",
    },
    {
        "name": "priority_conflict_sustainability_vs_cost",
        "policy_a": {
            "name": "green_mandate",
            "domain_id": "sustainability",
            "namespace": "sustainability.mandate",
            "rules": [{"name": "green_only", "condition": {"type": "procurement"},
                        "constraint": {"require_green": True, "max_spend": 1_000_000},
                        "message": "Only green suppliers allowed"}],
        },
        "policy_b": {
            "name": "lowest_cost",
            "domain_id": "procurement",
            "namespace": "procurement.cost",
            "rules": [{"name": "cheapest", "condition": {"type": "procurement"},
                        "constraint": {"require_green": False, "max_spend": 100_000},
                        "message": "Always choose lowest cost supplier"}],
        },
        "should_conflict": True,
        "conflict_type": "priority_contradiction",
    },
    {
        "name": "scope_conflict_data_retention",
        "policy_a": {
            "name": "gdpr_deletion",
            "domain_id": "legal",
            "namespace": "legal.gdpr",
            "rules": [{"name": "delete_data", "condition": {"type": "data_retention"},
                        "constraint": {"retention_days": 30, "max_spend": 0},
                        "message": "Delete personal data after 30 days"}],
        },
        "policy_b": {
            "name": "analytics_retention",
            "domain_id": "it",
            "namespace": "it.analytics",
            "rules": [{"name": "keep_data", "condition": {"type": "data_retention"},
                        "constraint": {"retention_days": 365, "max_spend": 50_000},
                        "message": "Retain data for 365 days for analytics"}],
        },
        "should_conflict": True,
        "conflict_type": "scope_contradiction",
    },
    {
        "name": "authority_conflict_approval",
        "policy_a": {
            "name": "dept_head_approval",
            "domain_id": "procurement",
            "namespace": "procurement.approval",
            "rules": [{"name": "dept_approve", "condition": {"type": "purchase"},
                        "constraint": {"approval_level": "department_head", "max_spend": 500_000},
                        "message": "Department head can approve up to $500K"}],
        },
        "policy_b": {
            "name": "cfo_only_approval",
            "domain_id": "finance",
            "namespace": "finance.approval",
            "rules": [{"name": "cfo_approve", "condition": {"type": "purchase"},
                        "constraint": {"approval_level": "cfo", "max_spend": 100_000},
                        "message": "CFO must approve all purchases over $100K"}],
        },
        "should_conflict": True,
        "conflict_type": "authority_contradiction",
    },
    {
        "name": "threshold_conflict_risk",
        "policy_a": {
            "name": "high_risk_tolerance",
            "domain_id": "rnd",
            "namespace": "rnd.risk",
            "rules": [{"name": "accept_risk", "condition": {"type": "risk_assessment"},
                        "constraint": {"risk_threshold": 0.8, "max_spend": 2_000_000},
                        "message": "Accept projects with up to 80% risk"}],
        },
        "policy_b": {
            "name": "low_risk_tolerance",
            "domain_id": "finance",
            "namespace": "finance.risk",
            "rules": [{"name": "limit_risk", "condition": {"type": "risk_assessment"},
                        "constraint": {"risk_threshold": 0.2, "max_spend": 200_000},
                        "message": "Reject projects with over 20% risk"}],
        },
        "should_conflict": True,
        "conflict_type": "threshold_contradiction",
    },
    {
        "name": "access_control_conflict",
        "policy_a": {
            "name": "open_access_research",
            "domain_id": "rnd",
            "namespace": "rnd.access",
            "rules": [{"name": "open_data", "condition": {"type": "data_access"},
                        "constraint": {"access_level": "public", "max_spend": 0},
                        "message": "Research data should be openly accessible"}],
        },
        "policy_b": {
            "name": "classified_data",
            "domain_id": "security",
            "namespace": "security.access",
            "rules": [{"name": "restrict_data", "condition": {"type": "data_access"},
                        "constraint": {"access_level": "confidential", "max_spend": 100_000},
                        "message": "All data classified as confidential"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "vendor_exclusivity_conflict",
        "policy_a": {
            "name": "exclusive_vendor",
            "domain_id": "procurement",
            "namespace": "procurement.exclusive",
            "rules": [{"name": "sole_source", "condition": {"type": "vendor_selection"},
                        "constraint": {"vendor_count": 1, "max_spend": 1_000_000},
                        "message": "Use exclusive vendor agreement"}],
        },
        "policy_b": {
            "name": "multi_vendor",
            "domain_id": "procurement",
            "namespace": "procurement.diversify",
            "rules": [{"name": "three_bids", "condition": {"type": "vendor_selection"},
                        "constraint": {"vendor_count": 3, "max_spend": 1_000_000},
                        "message": "Require minimum three vendor bids"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "overtime_conflict",
        "policy_a": {
            "name": "mandatory_overtime",
            "domain_id": "operations",
            "namespace": "operations.overtime",
            "rules": [{"name": "require_overtime", "condition": {"type": "scheduling"},
                        "constraint": {"overtime_hours": 20, "max_spend": 500_000},
                        "message": "Mandatory 20 hours overtime per week"}],
        },
        "policy_b": {
            "name": "overtime_ban",
            "domain_id": "hr",
            "namespace": "hr.overtime",
            "rules": [{"name": "no_overtime", "condition": {"type": "scheduling"},
                        "constraint": {"overtime_hours": 0, "max_spend": 0},
                        "message": "No overtime permitted under labor agreement"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "cloud_vs_onprem_conflict",
        "policy_a": {
            "name": "cloud_first",
            "domain_id": "it",
            "namespace": "it.infrastructure",
            "rules": [{"name": "use_cloud", "condition": {"type": "infrastructure"},
                        "constraint": {"deployment": "cloud", "max_spend": 3_000_000},
                        "message": "All new systems must be cloud-hosted"}],
        },
        "policy_b": {
            "name": "onprem_only",
            "domain_id": "security",
            "namespace": "security.infrastructure",
            "rules": [{"name": "use_onprem", "condition": {"type": "infrastructure"},
                        "constraint": {"deployment": "on_premises", "max_spend": 5_000_000},
                        "message": "Sensitive systems must remain on-premises"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "training_budget_conflict",
        "policy_a": {
            "name": "mandatory_training",
            "domain_id": "hr",
            "namespace": "hr.training",
            "rules": [{"name": "train_all", "condition": {"type": "training"},
                        "constraint": {"budget_per_employee": 5_000, "max_spend": 2_500_000},
                        "message": "$5K training budget per employee"}],
        },
        "policy_b": {
            "name": "training_cut",
            "domain_id": "finance",
            "namespace": "finance.training",
            "rules": [{"name": "cut_training", "condition": {"type": "training"},
                        "constraint": {"budget_per_employee": 0, "max_spend": 0},
                        "message": "Eliminate all discretionary training spend"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "release_cadence_conflict",
        "policy_a": {
            "name": "rapid_release",
            "domain_id": "rnd",
            "namespace": "rnd.release",
            "rules": [{"name": "weekly_release", "condition": {"type": "release"},
                        "constraint": {"release_frequency_days": 7, "max_spend": 100_000},
                        "message": "Weekly release cycle"}],
        },
        "policy_b": {
            "name": "quarterly_release",
            "domain_id": "security",
            "namespace": "security.release",
            "rules": [{"name": "quarterly_only", "condition": {"type": "release"},
                        "constraint": {"release_frequency_days": 90, "max_spend": 500_000},
                        "message": "Quarterly releases after full security review"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "marketing_spend_conflict",
        "policy_a": {
            "name": "aggressive_marketing",
            "domain_id": "marketing",
            "namespace": "marketing.spend",
            "rules": [{"name": "big_campaign", "condition": {"type": "campaign"},
                        "constraint": {"max_spend": 2_000_000},
                        "message": "$2M campaign budget approved"}],
        },
        "policy_b": {
            "name": "austerity_measures",
            "domain_id": "finance",
            "namespace": "finance.austerity",
            "rules": [{"name": "cut_marketing", "condition": {"type": "campaign"},
                        "constraint": {"max_spend": 50_000},
                        "message": "Marketing capped at $50K under austerity"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    # ── 10 more non-conflicts ───────────────────────────────────────────
    {
        "name": "disjoint_hr_and_it",
        "policy_a": {
            "name": "pto_policy",
            "domain_id": "hr",
            "namespace": "hr.pto",
            "rules": [{"name": "pto_accrual", "condition": {"type": "leave"},
                        "constraint": {"days_per_year": 25},
                        "message": "25 days PTO per year"}],
        },
        "policy_b": {
            "name": "server_maintenance",
            "domain_id": "it",
            "namespace": "it.maintenance",
            "rules": [{"name": "weekly_maintenance", "condition": {"type": "maintenance"},
                        "constraint": {"window_hours": 4},
                        "message": "4-hour weekly maintenance window"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "disjoint_sustainability_and_marketing",
        "policy_a": {
            "name": "carbon_reporting",
            "domain_id": "sustainability",
            "namespace": "sustainability.reporting",
            "rules": [{"name": "annual_report", "condition": {"type": "reporting"},
                        "constraint": {"frequency": "annual"},
                        "message": "Annual sustainability report"}],
        },
        "policy_b": {
            "name": "brand_guidelines",
            "domain_id": "marketing",
            "namespace": "marketing.brand",
            "rules": [{"name": "brand_colors", "condition": {"type": "branding"},
                        "constraint": {"palette": "corporate"},
                        "message": "Use corporate color palette"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "complementary_security_policies",
        "policy_a": {
            "name": "network_security",
            "domain_id": "security",
            "namespace": "security.network",
            "rules": [{"name": "firewall_rules", "condition": {"type": "network"},
                        "constraint": {"require_firewall": True},
                        "message": "Firewall required on all networks"}],
        },
        "policy_b": {
            "name": "endpoint_security",
            "domain_id": "security",
            "namespace": "security.endpoint",
            "rules": [{"name": "antivirus", "condition": {"type": "endpoint"},
                        "constraint": {"require_antivirus": True},
                        "message": "Antivirus required on all endpoints"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "complementary_finance_policies",
        "policy_a": {
            "name": "expense_reporting",
            "domain_id": "finance",
            "namespace": "finance.expenses",
            "rules": [{"name": "receipt_required", "condition": {"type": "expense"},
                        "constraint": {"receipt_threshold": 25},
                        "message": "Receipts required for expenses over $25"}],
        },
        "policy_b": {
            "name": "travel_policy",
            "domain_id": "finance",
            "namespace": "finance.travel",
            "rules": [{"name": "travel_class", "condition": {"type": "travel"},
                        "constraint": {"class": "economy"},
                        "message": "Economy class for flights under 6 hours"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "same_domain_non_contradicting_hr",
        "policy_a": {
            "name": "onboarding_process",
            "domain_id": "hr",
            "namespace": "hr.onboarding",
            "rules": [{"name": "orientation", "condition": {"type": "onboarding"},
                        "constraint": {"duration_days": 5},
                        "message": "5-day orientation program"}],
        },
        "policy_b": {
            "name": "performance_review",
            "domain_id": "hr",
            "namespace": "hr.performance",
            "rules": [{"name": "annual_review", "condition": {"type": "review"},
                        "constraint": {"frequency": "annual"},
                        "message": "Annual performance reviews"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "disjoint_operations_and_legal",
        "policy_a": {
            "name": "inventory_management",
            "domain_id": "operations",
            "namespace": "operations.inventory",
            "rules": [{"name": "reorder_point", "condition": {"type": "inventory"},
                        "constraint": {"min_stock_days": 14},
                        "message": "Maintain 14-day minimum stock"}],
        },
        "policy_b": {
            "name": "trademark_policy",
            "domain_id": "legal",
            "namespace": "legal.trademark",
            "rules": [{"name": "tm_registration", "condition": {"type": "trademark"},
                        "constraint": {"renewal_months": 12},
                        "message": "Renew trademarks annually"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "complementary_procurement_policies",
        "policy_a": {
            "name": "supplier_onboarding",
            "domain_id": "procurement",
            "namespace": "procurement.onboarding",
            "rules": [{"name": "background_check", "condition": {"type": "supplier"},
                        "constraint": {"require_background_check": True},
                        "message": "Background check required for new suppliers"}],
        },
        "policy_b": {
            "name": "supplier_insurance",
            "domain_id": "procurement",
            "namespace": "procurement.insurance",
            "rules": [{"name": "liability_insurance", "condition": {"type": "supplier"},
                        "constraint": {"min_coverage": 1_000_000},
                        "message": "$1M liability insurance required"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "disjoint_rnd_and_operations",
        "policy_a": {
            "name": "research_ethics",
            "domain_id": "rnd",
            "namespace": "rnd.ethics",
            "rules": [{"name": "irb_review", "condition": {"type": "research"},
                        "constraint": {"require_irb": True},
                        "message": "IRB review required for human subjects research"}],
        },
        "policy_b": {
            "name": "shift_scheduling",
            "domain_id": "operations",
            "namespace": "operations.shifts",
            "rules": [{"name": "shift_length", "condition": {"type": "scheduling"},
                        "constraint": {"max_shift_hours": 12},
                        "message": "Maximum 12-hour shifts"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "complementary_it_policies",
        "policy_a": {
            "name": "password_policy",
            "domain_id": "it",
            "namespace": "it.passwords",
            "rules": [{"name": "password_length", "condition": {"type": "authentication"},
                        "constraint": {"min_length": 12},
                        "message": "Minimum 12-character passwords"}],
        },
        "policy_b": {
            "name": "mfa_policy",
            "domain_id": "it",
            "namespace": "it.mfa",
            "rules": [{"name": "require_mfa", "condition": {"type": "authentication"},
                        "constraint": {"require_mfa": True},
                        "message": "MFA required for all accounts"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "disjoint_marketing_and_rnd",
        "policy_a": {
            "name": "social_media_policy",
            "domain_id": "marketing",
            "namespace": "marketing.social",
            "rules": [{"name": "posting_schedule", "condition": {"type": "social_media"},
                        "constraint": {"posts_per_week": 5},
                        "message": "5 social media posts per week"}],
        },
        "policy_b": {
            "name": "lab_safety",
            "domain_id": "rnd",
            "namespace": "rnd.safety",
            "rules": [{"name": "safety_training", "condition": {"type": "safety"},
                        "constraint": {"training_hours": 8},
                        "message": "8 hours annual lab safety training"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    # ── 4 edge cases ────────────────────────────────────────────────────
    {
        "name": "edge_empty_rules",
        "policy_a": {
            "name": "empty_policy_a",
            "domain_id": "finance",
            "namespace": "finance.empty",
            "rules": [],
        },
        "policy_b": {
            "name": "empty_policy_b",
            "domain_id": "finance",
            "namespace": "finance.empty2",
            "rules": [],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "edge_same_policy_twice",
        "policy_a": {
            "name": "duplicate_policy",
            "domain_id": "security",
            "namespace": "security.duplicate",
            "rules": [{"name": "encrypt_all", "condition": {"type": "encryption"},
                        "constraint": {"require_encryption": True, "max_spend": 100_000},
                        "message": "Encrypt all data at rest"}],
        },
        "policy_b": {
            "name": "duplicate_policy",
            "domain_id": "security",
            "namespace": "security.duplicate",
            "rules": [{"name": "encrypt_all", "condition": {"type": "encryption"},
                        "constraint": {"require_encryption": True, "max_spend": 100_000},
                        "message": "Encrypt all data at rest"}],
        },
        "should_conflict": False,
        "conflict_type": None,
    },
    {
        "name": "edge_overlapping_namespaces",
        "policy_a": {
            "name": "broad_security",
            "domain_id": "security",
            "namespace": "security",
            "rules": [{"name": "all_secure", "condition": {"type": "any"},
                        "constraint": {"classification": "restricted", "max_spend": 500_000},
                        "message": "All resources restricted by default"}],
        },
        "policy_b": {
            "name": "narrow_security",
            "domain_id": "security",
            "namespace": "security.public",
            "rules": [{"name": "public_data", "condition": {"type": "any"},
                        "constraint": {"classification": "public", "max_spend": 0},
                        "message": "Public data classification for marketing materials"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
    },
    {
        "name": "edge_circular_reference",
        "policy_a": {
            "name": "policy_depends_on_b",
            "domain_id": "operations",
            "namespace": "operations.circular_a",
            "rules": [{"name": "depends_b", "condition": {"type": "dependency"},
                        "constraint": {"requires_policy": "policy_depends_on_a", "max_spend": 100_000},
                        "message": "Depends on policy B approval"}],
        },
        "policy_b": {
            "name": "policy_depends_on_a",
            "domain_id": "operations",
            "namespace": "operations.circular_b",
            "rules": [{"name": "depends_a", "condition": {"type": "dependency"},
                        "constraint": {"requires_policy": "policy_depends_on_b", "max_spend": 100_000},
                        "message": "Depends on policy A approval"}],
        },
        "should_conflict": True,
        "conflict_type": "constraint_contradiction",
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
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="governance", source_reference="benchmark:governance", benchmark_config={"script": __file__})


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
