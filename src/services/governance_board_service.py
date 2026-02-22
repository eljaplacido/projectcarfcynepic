"""Governance Board Service — Board CRUD, Templates, and Seeding.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Manages governance boards that group domains, policies, and compliance
configurations into use-case bundles (e.g., scope emissions, CSRD, EU AI Act).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from src.core.governance_models import (
    BoardMember,
    ComplianceArticle,
    ComplianceFramework,
    ComplianceFrameworkConfig,
    ComplianceScore,
    ContextTriple,
    EvidenceType,
    FederatedPolicy,
    FederatedPolicyRule,
    GovernanceAuditEntry,
    GovernanceBoard,
    GovernanceDomain,
    GovernanceEventType,
    ConflictSeverity,
)

logger = logging.getLogger("carf.governance.board")

# Default template directory
_DEFAULT_TEMPLATE_DIR = "config/governance_boards"


# ---------------------------------------------------------------------------
# Built-in board templates
# ---------------------------------------------------------------------------

BOARD_TEMPLATES: dict[str, dict[str, Any]] = {
    "scope_emissions": {
        "name": "GHG Scope 1/2/3 Emissions Tracking",
        "description": "Track and govern greenhouse gas emissions across direct operations, energy, and supply chain.",
        "domain_ids": ["sustainability", "procurement", "finance"],
        "frameworks": ["csrd"],
        "tags": ["ghg", "emissions", "climate"],
    },
    "csrd_esrs": {
        "name": "CSRD/ESRS Reporting",
        "description": "Corporate Sustainability Reporting Directive with ESRS standards coverage.",
        "domain_ids": ["sustainability", "finance", "legal"],
        "frameworks": ["csrd", "gdpr"],
        "tags": ["csrd", "esrs", "reporting"],
    },
    "eu_ai_act": {
        "name": "EU AI Act Compliance",
        "description": "Full EU AI Act compliance governance for high-risk AI systems.",
        "domain_ids": ["security", "legal"],
        "frameworks": ["eu_ai_act", "gdpr"],
        "tags": ["ai", "regulation", "eu"],
    },
    "supply_chain": {
        "name": "Cross-Domain Supply Chain Governance",
        "description": "End-to-end supply chain governance spanning procurement, ESG, security, and finance.",
        "domain_ids": ["procurement", "sustainability", "security", "finance"],
        "frameworks": ["csrd", "iso_27001"],
        "tags": ["supply-chain", "procurement", "esg"],
    },
}


# Template-specific domain definitions
_TEMPLATE_DOMAINS: dict[str, dict[str, dict[str, Any]]] = {
    "scope_emissions": {
        "sustainability": {
            "display_name": "Sustainability",
            "description": "Environmental sustainability and emissions tracking",
            "color": "#10B981",
            "tags": ["ghg", "environment"],
        },
        "procurement": {
            "display_name": "Procurement",
            "description": "Supply chain procurement and Scope 3 tracking",
            "color": "#3B82F6",
            "tags": ["supply-chain", "scope3"],
        },
        "finance": {
            "display_name": "Finance",
            "description": "Carbon budget and financial controls",
            "color": "#F59E0B",
            "tags": ["budget", "carbon-tax"],
        },
    },
    "csrd_esrs": {
        "sustainability": {
            "display_name": "Sustainability",
            "description": "ESRS E1-E5 environmental standards",
            "color": "#10B981",
            "tags": ["esrs", "environment"],
        },
        "finance": {
            "display_name": "Finance",
            "description": "EU taxonomy alignment and financial materiality",
            "color": "#F59E0B",
            "tags": ["taxonomy", "materiality"],
        },
        "legal": {
            "display_name": "Legal & Compliance",
            "description": "CSRD legal requirements and disclosure obligations",
            "color": "#8B5CF6",
            "tags": ["csrd", "disclosure"],
        },
    },
    "eu_ai_act": {
        "security": {
            "display_name": "Security & Risk",
            "description": "AI system security, robustness, and risk management",
            "color": "#EF4444",
            "tags": ["risk", "cybersecurity"],
        },
        "legal": {
            "display_name": "Legal & Compliance",
            "description": "EU AI Act legal compliance, transparency, and human oversight",
            "color": "#8B5CF6",
            "tags": ["regulation", "transparency"],
        },
    },
    "supply_chain": {
        "procurement": {
            "display_name": "Procurement",
            "description": "Supplier verification and procurement governance",
            "color": "#3B82F6",
            "tags": ["suppliers", "verification"],
        },
        "sustainability": {
            "display_name": "Sustainability",
            "description": "ESG screening and environmental supply chain impact",
            "color": "#10B981",
            "tags": ["esg", "screening"],
        },
        "security": {
            "display_name": "Security",
            "description": "Supply chain security and vendor risk assessment",
            "color": "#EF4444",
            "tags": ["vendor-risk", "security"],
        },
        "finance": {
            "display_name": "Finance",
            "description": "Emergency procurement and financial controls",
            "color": "#F59E0B",
            "tags": ["emergency", "controls"],
        },
    },
}


# Template-specific policies
_TEMPLATE_POLICIES: dict[str, list[dict[str, Any]]] = {
    "scope_emissions": [
        {
            "name": "Direct Emissions Reporting",
            "domain_id": "sustainability",
            "namespace": "sustainability.scope1_reporting",
            "description": "Mandatory Scope 1 direct emissions reporting requirements",
            "priority": 90,
            "rules": [
                {
                    "name": "ghg_data_required",
                    "condition": {"emission_scope": "scope_1"},
                    "constraint": {"reporting_frequency": "quarterly", "data_verified": True},
                    "message": "Scope 1 emissions must be reported quarterly with verified data",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "Energy Indirect Emissions",
            "domain_id": "sustainability",
            "namespace": "sustainability.scope2_energy",
            "description": "Scope 2 energy-related indirect emissions tracking",
            "priority": 85,
            "rules": [
                {
                    "name": "energy_tracking",
                    "condition": {"emission_scope": "scope_2"},
                    "constraint": {"market_based": True, "location_based": True},
                    "message": "Both market-based and location-based Scope 2 accounting required",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "Supply Chain Scope 3 Tracing",
            "domain_id": "procurement",
            "namespace": "procurement.scope3_tracing",
            "description": "Scope 3 upstream supply chain emissions tracing",
            "priority": 75,
            "rules": [
                {
                    "name": "supplier_emissions",
                    "condition": {"category": "purchased_goods"},
                    "constraint": {"supplier_disclosure": True, "estimation_method": "spend_based"},
                    "message": "All tier-1 suppliers must disclose emissions or spend-based estimation applies",
                    "severity": "medium",
                },
            ],
        },
        {
            "name": "Carbon Budget Thresholds",
            "domain_id": "finance",
            "namespace": "finance.carbon_budget",
            "description": "Financial carbon budget constraints and thresholds",
            "priority": 80,
            "rules": [
                {
                    "name": "budget_limit",
                    "condition": {"budget_type": "carbon"},
                    "constraint": {"max_annual_tonnes": 50000, "reduction_target_pct": 4.2},
                    "message": "Annual carbon budget capped at 50,000 tCO2e with 4.2% YoY reduction target",
                    "severity": "critical",
                },
            ],
        },
    ],
    "csrd_esrs": [
        {
            "name": "Double Materiality Assessment",
            "domain_id": "sustainability",
            "namespace": "sustainability.double_materiality",
            "description": "CSRD double materiality assessment requirements",
            "priority": 95,
            "rules": [
                {
                    "name": "impact_materiality",
                    "condition": {"assessment_type": "materiality"},
                    "constraint": {"impact_assessment": True, "financial_assessment": True},
                    "message": "Both impact and financial materiality dimensions must be assessed",
                    "severity": "critical",
                },
            ],
        },
        {
            "name": "EU Taxonomy Alignment",
            "domain_id": "finance",
            "namespace": "finance.eu_taxonomy",
            "description": "EU Taxonomy eligible and aligned activity reporting",
            "priority": 90,
            "rules": [
                {
                    "name": "taxonomy_disclosure",
                    "condition": {"reporting_standard": "eu_taxonomy"},
                    "constraint": {"eligible_disclosed": True, "aligned_disclosed": True},
                    "message": "Taxonomy-eligible and taxonomy-aligned KPIs must be disclosed",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "ESRS Standards Coverage",
            "domain_id": "legal",
            "namespace": "legal.esrs_coverage",
            "description": "ESRS E1-G1 standards coverage and gap analysis",
            "priority": 85,
            "rules": [
                {
                    "name": "esrs_coverage",
                    "condition": {"framework": "esrs"},
                    "constraint": {"e1_climate": True, "s1_workforce": True, "g1_conduct": True},
                    "message": "Minimum ESRS coverage: E1 Climate Change, S1 Own Workforce, G1 Business Conduct",
                    "severity": "high",
                },
            ],
        },
    ],
    "eu_ai_act": [
        {
            "name": "Risk Management (Art.9)",
            "domain_id": "security",
            "namespace": "security.ai_risk_management",
            "description": "EU AI Act Article 9 — Risk management system requirements",
            "priority": 95,
            "rules": [
                {
                    "name": "risk_system",
                    "condition": {"ai_risk_level": "high"},
                    "constraint": {"risk_management_system": True, "continuous_monitoring": True},
                    "message": "High-risk AI systems must have a documented risk management system with continuous monitoring",
                    "severity": "critical",
                },
            ],
        },
        {
            "name": "Data Governance (Art.10)",
            "domain_id": "security",
            "namespace": "security.ai_data_governance",
            "description": "EU AI Act Article 10 — Data and data governance",
            "priority": 90,
            "rules": [
                {
                    "name": "data_governance",
                    "condition": {"ai_risk_level": "high"},
                    "constraint": {"data_quality_checks": True, "bias_detection": True},
                    "message": "Training data must undergo quality checks and bias detection",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "Transparency (Art.13)",
            "domain_id": "legal",
            "namespace": "legal.ai_transparency",
            "description": "EU AI Act Article 13 — Transparency and provision of information",
            "priority": 90,
            "rules": [
                {
                    "name": "transparency",
                    "condition": {"ai_system": True},
                    "constraint": {"model_card": True, "user_notification": True},
                    "message": "AI systems must provide model cards and notify users of AI interaction",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "Human Oversight (Art.14)",
            "domain_id": "legal",
            "namespace": "legal.ai_human_oversight",
            "description": "EU AI Act Article 14 — Human oversight measures",
            "priority": 95,
            "rules": [
                {
                    "name": "human_oversight",
                    "condition": {"ai_risk_level": "high"},
                    "constraint": {"human_in_loop": True, "override_capability": True},
                    "message": "High-risk AI must support human-in-the-loop with override capability",
                    "severity": "critical",
                },
            ],
        },
        {
            "name": "Accuracy & Robustness (Art.15)",
            "domain_id": "security",
            "namespace": "security.ai_robustness",
            "description": "EU AI Act Article 15 — Accuracy, robustness, and cybersecurity",
            "priority": 85,
            "rules": [
                {
                    "name": "robustness",
                    "condition": {"ai_system": True},
                    "constraint": {"adversarial_testing": True, "performance_monitoring": True},
                    "message": "AI systems must undergo adversarial testing and continuous performance monitoring",
                    "severity": "high",
                },
            ],
        },
    ],
    "supply_chain": [
        {
            "name": "Supplier Verification",
            "domain_id": "procurement",
            "namespace": "procurement.supplier_verification",
            "description": "Supplier onboarding and verification governance",
            "priority": 90,
            "rules": [
                {
                    "name": "supplier_due_diligence",
                    "condition": {"activity": "supplier_onboarding"},
                    "constraint": {"background_check": True, "financial_check": True},
                    "message": "All new suppliers must pass background and financial due diligence",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "ESG Screening",
            "domain_id": "sustainability",
            "namespace": "sustainability.esg_screening",
            "description": "ESG risk screening for supply chain partners",
            "priority": 85,
            "rules": [
                {
                    "name": "esg_assessment",
                    "condition": {"supplier_tier": "tier_1"},
                    "constraint": {"esg_score_min": 60, "annual_reassessment": True},
                    "message": "Tier-1 suppliers must maintain minimum ESG score of 60 with annual reassessment",
                    "severity": "medium",
                },
            ],
        },
        {
            "name": "Security Risk Assessment",
            "domain_id": "security",
            "namespace": "security.vendor_risk",
            "description": "Vendor cybersecurity risk assessment",
            "priority": 80,
            "rules": [
                {
                    "name": "vendor_security",
                    "condition": {"data_access": True},
                    "constraint": {"security_audit": True, "iso_27001_certified": True},
                    "message": "Vendors with data access must be security-audited and ISO 27001 certified",
                    "severity": "high",
                },
            ],
        },
        {
            "name": "Emergency Procurement",
            "domain_id": "finance",
            "namespace": "finance.emergency_procurement",
            "description": "Emergency procurement financial controls",
            "priority": 70,
            "rules": [
                {
                    "name": "emergency_spend_limit",
                    "condition": {"procurement_type": "emergency"},
                    "constraint": {"max_amount": 100000, "approval_required": True},
                    "message": "Emergency procurement exceeding $100K requires executive approval",
                    "severity": "high",
                },
            ],
        },
    ],
}


class GovernanceBoardService:
    """Service for managing governance boards and templates."""

    def __init__(self, template_dir: str | None = None) -> None:
        self._template_dir = template_dir or os.getenv(
            "GOVERNANCE_BOARD_DIR", _DEFAULT_TEMPLATE_DIR
        )
        self._boards: dict[str, GovernanceBoard] = {}
        self._audit_log: list[GovernanceAuditEntry] = []
        self._templates_loaded = False

    # =====================================================================
    # Template Management
    # =====================================================================

    def list_templates(self) -> list[dict[str, Any]]:
        """List available board templates."""
        templates = []
        for template_id, meta in BOARD_TEMPLATES.items():
            templates.append({
                "template_id": template_id,
                "name": meta["name"],
                "description": meta["description"],
                "domain_ids": meta["domain_ids"],
                "frameworks": meta["frameworks"],
                "tags": meta["tags"],
            })
        # Also load any YAML templates from disk
        self._load_yaml_templates()
        return templates

    def _load_yaml_templates(self) -> None:
        """Load additional templates from YAML files."""
        if self._templates_loaded:
            return
        template_path = Path(self._template_dir)
        if not template_path.is_absolute():
            template_path = Path(__file__).resolve().parent.parent.parent / template_path
        if template_path.exists():
            for yaml_file in sorted(template_path.glob("*.yaml")):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        tid = data.get("template_id", yaml_file.stem)
                        if tid not in BOARD_TEMPLATES:
                            BOARD_TEMPLATES[tid] = {
                                "name": data.get("name", tid),
                                "description": data.get("description", ""),
                                "domain_ids": data.get("domain_ids", []),
                                "frameworks": data.get("frameworks", []),
                                "tags": data.get("tags", []),
                            }
                except Exception as exc:
                    logger.warning(f"Failed to load template {yaml_file.name}: {exc}")
        self._templates_loaded = True

    # =====================================================================
    # Board CRUD
    # =====================================================================

    def create_board(self, board: GovernanceBoard) -> GovernanceBoard:
        """Create a new governance board."""
        self._boards[board.board_id] = board
        self._log_event(
            GovernanceEventType.BOARD_CREATED, "api",
            board.domain_ids,
            {"board_id": board.board_id, "name": board.name},
        )
        return board

    def get_board(self, board_id: str) -> GovernanceBoard | None:
        return self._boards.get(board_id)

    def list_boards(self) -> list[GovernanceBoard]:
        return list(self._boards.values())

    def update_board(self, board_id: str, updates: dict[str, Any]) -> GovernanceBoard | None:
        board = self._boards.get(board_id)
        if board is None:
            return None
        for key, value in updates.items():
            if hasattr(board, key) and key not in ("board_id", "created_at"):
                setattr(board, key, value)
        board.updated_at = datetime.utcnow()
        self._log_event(
            GovernanceEventType.BOARD_UPDATED, "api",
            board.domain_ids,
            {"board_id": board_id, "updated_fields": list(updates.keys())},
        )
        return board

    def delete_board(self, board_id: str) -> bool:
        board = self._boards.pop(board_id, None)
        if board:
            self._log_event(
                GovernanceEventType.BOARD_DELETED, "api",
                board.domain_ids,
                {"board_id": board_id, "name": board.name},
            )
            return True
        return False

    # =====================================================================
    # Template-Based Board Creation
    # =====================================================================

    def create_from_template(self, template_id: str, name: str | None = None) -> GovernanceBoard | None:
        """Create a board with domains and policies from a preset template."""
        template = BOARD_TEMPLATES.get(template_id)
        if template is None:
            return None

        from src.services.federated_policy_service import get_federated_service
        fed_service = get_federated_service()

        board_name = name or template["name"]
        domain_ids = list(template["domain_ids"])

        # Register domains from template
        domain_defs = _TEMPLATE_DOMAINS.get(template_id, {})
        for domain_id in domain_ids:
            if fed_service.get_domain(domain_id) is None:
                domain_def = domain_defs.get(domain_id, {})
                domain = GovernanceDomain(
                    domain_id=domain_id,
                    display_name=domain_def.get("display_name", domain_id.title()),
                    description=domain_def.get("description", ""),
                    policy_namespace=domain_id,
                    tags=domain_def.get("tags", []),
                    color=domain_def.get("color", "#6B7280"),
                )
                fed_service.register_domain(domain)

        # Register policies from template
        policy_namespaces: list[str] = []
        policies_data = _TEMPLATE_POLICIES.get(template_id, [])
        for policy_data in policies_data:
            namespace = policy_data["namespace"]
            if fed_service.get_policy(namespace) is None:
                rules = [
                    FederatedPolicyRule(
                        name=r["name"],
                        condition=r.get("condition", {}),
                        constraint=r.get("constraint", {}),
                        message=r.get("message", ""),
                        severity=ConflictSeverity(r.get("severity", "medium")),
                    )
                    for r in policy_data.get("rules", [])
                ]
                policy = FederatedPolicy(
                    name=policy_data["name"],
                    domain_id=policy_data["domain_id"],
                    namespace=namespace,
                    description=policy_data.get("description", ""),
                    rules=rules,
                    priority=policy_data.get("priority", 50),
                )
                fed_service.add_policy(policy)
            policy_namespaces.append(namespace)

        # Create compliance configs
        compliance_configs = []
        for fw_str in template.get("frameworks", []):
            try:
                fw = ComplianceFramework(fw_str)
                compliance_configs.append(ComplianceFrameworkConfig(
                    framework=fw,
                    enabled=True,
                    target_score=0.8,
                ))
            except ValueError:
                pass

        # Create the board
        board = GovernanceBoard(
            name=board_name,
            description=template["description"],
            template_id=template_id,
            domain_ids=domain_ids,
            policy_namespaces=policy_namespaces,
            compliance_configs=compliance_configs,
            tags=template.get("tags", []),
        )

        return self.create_board(board)

    # =====================================================================
    # Demo Data Seeding
    # =====================================================================

    def seed_demo_data(self, template_id: str) -> GovernanceBoard | None:
        """Create a board from template and seed synthetic triples and cost data."""
        board = self.create_from_template(template_id)
        if board is None:
            return None

        # Seed synthetic triples between domains
        from src.services.governance_graph_service import get_governance_graph_service
        graph_service = get_governance_graph_service()

        domain_ids = board.domain_ids
        for i in range(len(domain_ids)):
            for j in range(i + 1, len(domain_ids)):
                triple = ContextTriple(
                    subject=f"{domain_ids[i]}_policy",
                    predicate="impacts",
                    object=f"{domain_ids[j]}_compliance",
                    domain_source=domain_ids[i],
                    domain_target=domain_ids[j],
                    confidence=0.75,
                    evidence_type=EvidenceType.RULE_BASED,
                    metadata={"seeded": True, "board_id": board.board_id},
                )
                if graph_service.is_available:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(graph_service.save_triple(triple))
                        else:
                            loop.run_until_complete(graph_service.save_triple(triple))
                    except RuntimeError:
                        pass

        # Seed cost data
        from src.services.cost_intelligence_service import get_cost_service
        cost_service = get_cost_service()
        cost_service.compute_full_breakdown(
            session_id=f"seed_{template_id}_{board.board_id}",
            input_tokens=1500,
            output_tokens=800,
            provider="deepseek",
            compute_time_ms=2500.0,
            risk_score=0.3,
            financial_exposure=50000.0,
        )

        return board

    # =====================================================================
    # Board Compliance Aggregation
    # =====================================================================

    def compute_board_compliance(self, board_id: str) -> list[ComplianceScore]:
        """Aggregate compliance scores for a board's configured frameworks."""
        board = self._boards.get(board_id)
        if board is None:
            return []

        from src.services.governance_service import get_governance_service
        gov_service = get_governance_service()

        scores: list[ComplianceScore] = []
        for config in board.compliance_configs:
            if not config.enabled:
                continue

            base_score = gov_service.compute_compliance(config.framework)

            # Merge custom articles if present
            if config.custom_articles:
                existing_ids = {a.article_id for a in base_score.articles}
                for custom in config.custom_articles:
                    if custom.article_id not in existing_ids:
                        base_score.articles.append(custom)

            # Apply custom weights if present
            if config.custom_weights and base_score.articles:
                weighted_sum = 0.0
                total_weight = 0.0
                for article in base_score.articles:
                    weight = config.custom_weights.get(article.article_id, 1.0)
                    weighted_sum += article.score * weight
                    total_weight += weight
                if total_weight > 0:
                    base_score.overall_score = round(weighted_sum / total_weight, 2)

            scores.append(base_score)

        return scores

    # --- Internal ---

    def _log_event(
        self, event_type: GovernanceEventType, actor: str,
        affected_domains: list[str], details: dict[str, Any],
    ) -> None:
        self._audit_log.append(GovernanceAuditEntry(
            event_type=event_type,
            actor=actor,
            affected_domains=affected_domains,
            details=details,
        ))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_board_service: GovernanceBoardService | None = None


def get_board_service() -> GovernanceBoardService:
    """Get or create the governance board service singleton."""
    global _board_service
    if _board_service is None:
        _board_service = GovernanceBoardService()
    return _board_service
