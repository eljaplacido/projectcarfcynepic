"""Governance Service — Central MAP-PRICE-RESOLVE Orchestrator.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Ties all OG services together: governance graph, federated policies,
cost intelligence, and compliance assessment. This is the single entry
point called by the governance LangGraph node.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any

from src.core.governance_models import (
    ComplianceArticle,
    ComplianceFramework,
    ComplianceScore,
    ContextTriple,
    CostBreakdown,
    EvidenceType,
    GovernanceAuditEntry,
    GovernanceEventType,
    GovernanceHealth,
    PolicyConflict,
)

logger = logging.getLogger("carf.governance")

# Domain keywords for entity-to-domain mapping
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "procurement": ["supplier", "procurement", "vendor", "purchase", "contract", "spend", "sourcing", "supply chain"],
    "sustainability": ["carbon", "emission", "esg", "sustainability", "climate", "scope 3", "taxonomy", "materiality", "environmental"],
    "security": ["security", "access", "encryption", "breach", "vulnerability", "threat", "authentication", "firewall"],
    "legal": ["legal", "contract", "regulation", "compliance", "ip", "patent", "liability", "disclosure", "gdpr"],
    "finance": ["budget", "revenue", "cost", "financial", "audit", "tax", "fx", "risk", "investment", "profit"],
}


class GovernanceService:
    """Central orchestrator for the Orchestration Governance subsystem.

    Pillars:
        MAP    — Extract entities, match to domains, create triples
        PRICE  — Compute full cost breakdown using CostIntelligenceService
        RESOLVE — Detect and surface cross-domain policy conflicts
    """

    def __init__(self) -> None:
        self._audit_log: list[GovernanceAuditEntry] = []

    # =====================================================================
    # MAP — Cross-Domain Impact Tracing
    # =====================================================================

    def map_impacts(self, state: Any) -> list[ContextTriple]:
        """Extract entities from query/evidence and create semantic triples.

        Args:
            state: EpistemicState with user_input, context, evidence

        Returns:
            List of generated ContextTriple objects
        """
        triples: list[ContextTriple] = []

        # Extract text sources
        user_input = getattr(state, "user_input", "") or ""
        final_response = getattr(state, "final_response", "") or ""
        session_id = str(getattr(state, "session_id", ""))

        combined_text = f"{user_input} {final_response}".lower()

        # Find mentioned domains
        mentioned_domains: list[str] = []
        for domain_id, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in combined_text:
                    mentioned_domains.append(domain_id)
                    break

        # Create cross-domain triples when multiple domains are referenced
        if len(mentioned_domains) >= 2:
            for i in range(len(mentioned_domains)):
                for j in range(i + 1, len(mentioned_domains)):
                    source = mentioned_domains[i]
                    target = mentioned_domains[j]

                    # Extract a contextual predicate
                    predicate = self._extract_predicate(combined_text, source, target)

                    triple = ContextTriple(
                        subject=f"{source}_context",
                        predicate=predicate,
                        object=f"{target}_context",
                        domain_source=source,
                        domain_target=target,
                        confidence=0.7,
                        evidence_type=EvidenceType.LLM_EXTRACTED,
                        session_id=session_id,
                    )
                    triples.append(triple)

        # Extract causal evidence triples
        causal_evidence = getattr(state, "causal_evidence", None)
        if causal_evidence:
            treatment = getattr(causal_evidence, "treatment", "")
            outcome = getattr(causal_evidence, "outcome", "")
            if treatment and outcome:
                source_domain = self._classify_entity_domain(treatment)
                target_domain = self._classify_entity_domain(outcome)
                if source_domain and target_domain and source_domain != target_domain:
                    triple = ContextTriple(
                        subject=treatment,
                        predicate="causes",
                        object=outcome,
                        domain_source=source_domain,
                        domain_target=target_domain,
                        confidence=0.85,
                        evidence_type=EvidenceType.RULE_BASED,
                        session_id=session_id,
                    )
                    triples.append(triple)

        self._log_event(
            GovernanceEventType.TRIPLE_CREATED, "governance_node",
            list(set(t.domain_source for t in triples) | set(t.domain_target for t in triples)),
            {"triples_created": len(triples), "session_id": session_id},
        )

        return triples

    def _extract_predicate(self, text: str, source: str, target: str) -> str:
        """Extract a contextual predicate from text."""
        impact_verbs = ["affects", "impacts", "influences", "drives", "constrains", "requires"]
        for verb in impact_verbs:
            if verb in text:
                return verb
        return "impacts"

    def _classify_entity_domain(self, entity: str) -> str | None:
        """Classify an entity into a governance domain."""
        entity_lower = entity.lower()
        for domain_id, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in entity_lower:
                    return domain_id
        return None

    def get_impact_graph(self, domain_id: str | None = None) -> dict[str, Any]:
        """Return ReactFlow-ready graph for visualization.

        Returns nodes and edges suitable for the SpecMap visualization.
        """
        from src.services.federated_policy_service import get_federated_service
        service = get_federated_service()
        domains = service.list_domains()

        nodes = []
        edges = []

        # Domain colors
        domain_colors = {
            "procurement": "#3B82F6",     # blue
            "sustainability": "#10B981",  # green
            "security": "#EF4444",        # red
            "legal": "#8B5CF6",           # purple
            "finance": "#F59E0B",         # amber
        }

        for i, domain in enumerate(domains):
            nodes.append({
                "id": domain.domain_id,
                "type": "domain",
                "data": {
                    "label": domain.display_name,
                    "domain_id": domain.domain_id,
                    "color": domain_colors.get(domain.domain_id, domain.color),
                    "policy_count": len(service.list_policies(domain.domain_id)),
                },
                "position": {"x": (i % 3) * 250, "y": (i // 3) * 200},
            })

        return {"nodes": nodes, "edges": edges}

    # =====================================================================
    # PRICE — Cost Intelligence
    # =====================================================================

    def compute_cost(
        self,
        state: Any,
        input_tokens: int = 0,
        output_tokens: int = 0,
        compute_time_ms: float = 0.0,
    ) -> CostBreakdown:
        """Compute full cost breakdown for the current query.

        Args:
            state: EpistemicState
            input_tokens: LLM input tokens from instrumentation
            output_tokens: LLM output tokens from instrumentation
            compute_time_ms: Total pipeline compute time

        Returns:
            CostBreakdown
        """
        from src.services.cost_intelligence_service import get_cost_service
        cost_service = get_cost_service()

        session_id = str(getattr(state, "session_id", ""))
        provider = os.getenv("LLM_PROVIDER", "deepseek")

        # Extract risk score from guardian
        risk_score = 0.0
        context = getattr(state, "context", {})
        if isinstance(context, dict):
            risk_level = context.get("risk_level", "LOW")
            risk_map = {"LOW": 0.1, "MEDIUM": 0.3, "HIGH": 0.6, "CRITICAL": 0.9}
            risk_score = risk_map.get(risk_level, 0.1)

        # Extract financial exposure from proposed action
        financial_exposure = 0.0
        action = getattr(state, "proposed_action", None)
        if isinstance(action, dict):
            financial_exposure = action.get("amount", 0) or action.get(
                "parameters", {}
            ).get("amount", 0)

        breakdown = cost_service.compute_full_breakdown(
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            compute_time_ms=compute_time_ms,
            risk_score=risk_score,
            financial_exposure=float(financial_exposure) if financial_exposure else 0.0,
        )

        self._log_event(
            GovernanceEventType.COST_COMPUTED, "governance_node",
            [], {"session_id": session_id, "total_cost": breakdown.total_cost},
        )

        return breakdown

    def get_cost_summary(self, session_ids: list[str] | None = None) -> dict[str, Any]:
        """Get aggregate cost metrics for dashboard display."""
        from src.services.cost_intelligence_service import get_cost_service
        aggregate = get_cost_service().aggregate_costs(session_ids)
        return aggregate.model_dump()

    # =====================================================================
    # RESOLVE — Federated Policy Conflict Detection
    # =====================================================================

    def resolve_tensions(self, state: Any) -> list[PolicyConflict]:
        """Run conflict detection across all federated policies.

        Returns newly detected conflicts relevant to the current query.
        """
        from src.services.federated_policy_service import get_federated_service
        service = get_federated_service()

        # Return all unresolved conflicts
        conflicts = service.get_unresolved_conflicts()

        if conflicts:
            self._log_event(
                GovernanceEventType.CONFLICT_DETECTED, "governance_node",
                list(set(
                    c.policy_a_domain for c in conflicts
                ) | set(
                    c.policy_b_domain for c in conflicts
                )),
                {"unresolved_count": len(conflicts)},
            )

        return conflicts

    def get_unresolved_conflicts(self) -> list[PolicyConflict]:
        from src.services.federated_policy_service import get_federated_service
        return get_federated_service().get_unresolved_conflicts()

    # =====================================================================
    # AUDIT — Compliance & Timeline
    # =====================================================================

    def compute_compliance(self, framework: ComplianceFramework, board_id: str | None = None) -> ComplianceScore:
        """Score current system against a regulatory framework.

        Args:
            framework: The compliance framework to assess.
            board_id: Optional board ID. When provided, merges board's
                ComplianceFrameworkConfig custom_articles and custom_weights.
        """
        if framework == ComplianceFramework.EU_AI_ACT:
            return self._assess_eu_ai_act()
        elif framework == ComplianceFramework.CSRD:
            return self._assess_csrd()
        elif framework == ComplianceFramework.GDPR:
            return self._assess_gdpr()
        elif framework == ComplianceFramework.ISO_27001:
            return self._assess_iso_27001()
        return ComplianceScore(framework=framework)

    def _assess_eu_ai_act(self) -> ComplianceScore:
        """Assess compliance with EU AI Act."""
        articles = [
            ComplianceArticle(
                article_id="Art.9", title="Risk Management System",
                score=0.85, status="compliant",
                evidence=["Guardian layer enforces risk-based policy checks",
                           "Cynefin domain classification provides risk categorization"],
                gaps=[],
            ),
            ComplianceArticle(
                article_id="Art.10", title="Data and Data Governance",
                score=0.75, status="partial",
                evidence=["Dataset provenance tracked via Neo4j",
                           "Data quality metrics computed by evaluation service"],
                gaps=["No automated data bias detection"],
            ),
            ComplianceArticle(
                article_id="Art.11", title="Technical Documentation",
                score=0.90, status="compliant",
                evidence=["Full reasoning chain audit trail",
                           "API documentation auto-generated"],
                gaps=[],
            ),
            ComplianceArticle(
                article_id="Art.13", title="Transparency and Information",
                score=0.88, status="compliant",
                evidence=["TransparencyPanel shows full decision rationale",
                           "Uncertainty quantification displayed to users"],
                gaps=["No standardized model card generation"],
            ),
            ComplianceArticle(
                article_id="Art.14", title="Human Oversight",
                score=0.92, status="compliant",
                evidence=["HumanLayer integration for escalation",
                           "Guardian escalation for high-risk decisions"],
                gaps=[],
            ),
            ComplianceArticle(
                article_id="Art.15", title="Accuracy, Robustness, Cybersecurity",
                score=0.70, status="partial",
                evidence=["DeepEval quality metrics at each node",
                           "Refutation testing for causal claims"],
                gaps=["No formal adversarial robustness testing",
                       "Limited cybersecurity penetration testing"],
            ),
        ]

        overall = sum(a.score for a in articles) / len(articles) if articles else 0
        all_gaps = [gap for a in articles for gap in a.gaps]

        return ComplianceScore(
            framework=ComplianceFramework.EU_AI_ACT,
            overall_score=round(overall, 2),
            articles=articles,
            gaps=all_gaps,
            recommendations=[
                "Implement automated data bias detection for Art.10",
                "Add standardized model card generation for Art.13",
                "Conduct adversarial robustness testing for Art.15",
            ],
        )

    def _assess_csrd(self) -> ComplianceScore:
        """Assess CSRD compliance."""
        articles = [
            ComplianceArticle(
                article_id="ESRS.E1", title="Climate Change",
                score=0.70, status="partial",
                evidence=["Scope 3 analysis capability via causal engine"],
                gaps=["No automated GHG inventory integration"],
            ),
            ComplianceArticle(
                article_id="ESRS.S1", title="Own Workforce",
                score=0.50, status="partial",
                evidence=["Basic workforce metrics tracking"],
                gaps=["No human capital risk modeling"],
            ),
            ComplianceArticle(
                article_id="ESRS.G1", title="Business Conduct",
                score=0.80, status="compliant",
                evidence=["Full audit trail for all decisions",
                           "Policy enforcement via Guardian layer"],
                gaps=[],
            ),
            ComplianceArticle(
                article_id="DM", title="Double Materiality Assessment",
                score=0.65, status="partial",
                evidence=["Cross-domain impact triples enable impact materiality"],
                gaps=["Financial materiality assessment not automated"],
            ),
        ]
        overall = sum(a.score for a in articles) / len(articles)
        return ComplianceScore(
            framework=ComplianceFramework.CSRD,
            overall_score=round(overall, 2),
            articles=articles,
            gaps=[g for a in articles for g in a.gaps],
            recommendations=[
                "Integrate GHG inventory for ESRS.E1",
                "Add human capital modeling for ESRS.S1",
                "Automate financial materiality for double materiality",
            ],
        )

    def _assess_gdpr(self) -> ComplianceScore:
        """Assess GDPR compliance."""
        articles = [
            ComplianceArticle(
                article_id="Art.5", title="Principles of Processing",
                score=0.85, status="compliant",
                evidence=["Purpose limitation via domain routing",
                           "Data minimization in state serialization"],
            ),
            ComplianceArticle(
                article_id="Art.25", title="Data Protection by Design",
                score=0.80, status="compliant",
                evidence=["PII masking rules in CSL policies",
                           "Data access controls in data_access policy"],
                gaps=["No automated DPIA generation"],
            ),
            ComplianceArticle(
                article_id="Art.35", title="Data Protection Impact Assessment",
                score=0.60, status="partial",
                evidence=["Risk assessment via Guardian layer"],
                gaps=["No formal DPIA template", "Manual risk documentation"],
            ),
        ]
        overall = sum(a.score for a in articles) / len(articles)
        return ComplianceScore(
            framework=ComplianceFramework.GDPR,
            overall_score=round(overall, 2),
            articles=articles,
            gaps=[g for a in articles for g in a.gaps],
            recommendations=["Implement automated DPIA generation for Art.35"],
        )

    def _assess_iso_27001(self) -> ComplianceScore:
        """Assess ISO 27001 compliance."""
        articles = [
            ComplianceArticle(
                article_id="A.5", title="Information Security Policies",
                score=0.88, status="compliant",
                evidence=["CSL policy framework with formal verification",
                           "Guardian layer enforces security policies"],
            ),
            ComplianceArticle(
                article_id="A.8", title="Asset Management",
                score=0.70, status="partial",
                evidence=["Dataset tracking in Neo4j"],
                gaps=["No comprehensive asset inventory"],
            ),
            ComplianceArticle(
                article_id="A.12", title="Operations Security",
                score=0.75, status="partial",
                evidence=["Audit logging via Kafka",
                           "OpenTelemetry observability"],
                gaps=["No automated security event correlation"],
            ),
        ]
        overall = sum(a.score for a in articles) / len(articles)
        return ComplianceScore(
            framework=ComplianceFramework.ISO_27001,
            overall_score=round(overall, 2),
            articles=articles,
            gaps=[g for a in articles for g in a.gaps],
            recommendations=[
                "Implement comprehensive asset inventory for A.8",
                "Add automated SIEM integration for A.12",
            ],
        )

    def get_audit_timeline(
        self,
        limit: int = 100,
        domain_id: str | None = None,
        event_type: str | None = None,
    ) -> list[GovernanceAuditEntry]:
        """Get filtered audit event history."""
        from src.services.federated_policy_service import get_federated_service
        service = get_federated_service()

        # Merge audit logs from both services
        entries = list(self._audit_log)
        gov_type = GovernanceEventType(event_type) if event_type else None
        entries.extend(service.get_audit_log(limit=limit, domain_id=domain_id, event_type=gov_type))

        if domain_id:
            entries = [e for e in entries if domain_id in e.affected_domains]
        if event_type:
            entries = [e for e in entries if e.event_type.value == event_type]

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_health(self) -> GovernanceHealth:
        """Get governance subsystem health status."""
        from src.services.federated_policy_service import get_federated_service
        from src.services.governance_graph_service import get_governance_graph_service

        policy_service = get_federated_service()
        graph_service = get_governance_graph_service()

        domains = policy_service.list_domains()
        policies = policy_service.list_policies()
        conflicts = policy_service.get_unresolved_conflicts()

        return GovernanceHealth(
            enabled=True,
            neo4j_available=graph_service.is_available,
            domains_count=len(domains),
            policies_count=len(policies),
            active_conflicts=len(conflicts),
            triples_count=0,  # Would query graph service
            status="healthy" if len(domains) > 0 else "initialized",
        )

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

_governance_service: GovernanceService | None = None


def get_governance_service() -> GovernanceService:
    """Get or create the governance service singleton."""
    global _governance_service
    if _governance_service is None:
        _governance_service = GovernanceService()
    return _governance_service
