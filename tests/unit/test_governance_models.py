"""Unit tests for CARF Orchestration Governance Pydantic models.

Tests all models from src.core.governance_models:
- ContextTriple, GovernanceDomain, FederatedPolicy, PolicyConflict
- CostBreakdown, CostBreakdownItem, ComplianceScore, ComplianceArticle
- GovernanceAuditEntry, GovernanceHealth
- Enums: EvidenceType, ConflictType, ConflictSeverity, ComplianceFramework, GovernanceEventType
"""

import os
import pytest
from datetime import datetime
from uuid import UUID

os.environ["CARF_TEST_MODE"] = "1"

from src.core.governance_models import (
    ComplianceArticle,
    ComplianceFramework,
    ComplianceScore,
    ConflictSeverity,
    ConflictType,
    ContextTriple,
    CostAggregate,
    CostBreakdown,
    CostBreakdownItem,
    EvidenceType,
    FederatedPolicy,
    FederatedPolicyRule,
    GovernanceAuditEntry,
    GovernanceDomain,
    GovernanceEventType,
    GovernanceHealth,
    ImpactPath,
    PolicyConflict,
    ROIMetrics,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestEnums:
    """Test all governance enums."""

    def test_evidence_type_values(self):
        assert EvidenceType.LLM_EXTRACTED == "llm_extracted"
        assert EvidenceType.RULE_BASED == "rule_based"
        assert EvidenceType.USER_DEFINED == "user_defined"
        assert EvidenceType.POLICY_DERIVED == "policy_derived"

    def test_conflict_type_values(self):
        assert ConflictType.CONTRADICTORY == "contradictory"
        assert ConflictType.OVERLAPPING == "overlapping"
        assert ConflictType.RESOURCE_CONTENTION == "resource_contention"
        assert ConflictType.PRIORITY_AMBIGUITY == "priority_ambiguity"

    def test_conflict_severity_values(self):
        assert ConflictSeverity.CRITICAL == "critical"
        assert ConflictSeverity.HIGH == "high"
        assert ConflictSeverity.MEDIUM == "medium"
        assert ConflictSeverity.LOW == "low"

    def test_compliance_framework_values(self):
        assert ComplianceFramework.EU_AI_ACT == "eu_ai_act"
        assert ComplianceFramework.CSRD == "csrd"
        assert ComplianceFramework.GDPR == "gdpr"
        assert ComplianceFramework.ISO_27001 == "iso_27001"

    def test_governance_event_type_values(self):
        assert GovernanceEventType.TRIPLE_CREATED == "triple_created"
        assert GovernanceEventType.POLICY_REGISTERED == "policy_registered"
        assert GovernanceEventType.CONFLICT_DETECTED == "conflict_detected"
        assert GovernanceEventType.CONFLICT_RESOLVED == "conflict_resolved"
        assert GovernanceEventType.COMPLIANCE_ASSESSED == "compliance_assessed"
        assert GovernanceEventType.COST_COMPUTED == "cost_computed"
        assert GovernanceEventType.GOVERNANCE_NODE_EXECUTED == "governance_node_executed"


# ---------------------------------------------------------------------------
# ContextTriple
# ---------------------------------------------------------------------------

class TestContextTriple:
    """Test ContextTriple model."""

    def test_creation_with_required_fields(self):
        triple = ContextTriple(
            subject="procurement_spend",
            predicate="increases",
            object="carbon_footprint",
            domain_source="procurement",
            domain_target="sustainability",
        )
        assert triple.subject == "procurement_spend"
        assert triple.predicate == "increases"
        assert triple.object == "carbon_footprint"
        assert triple.domain_source == "procurement"
        assert triple.domain_target == "sustainability"

    def test_defaults(self):
        triple = ContextTriple(
            subject="a", predicate="b", object="c",
            domain_source="d1", domain_target="d2",
        )
        assert triple.confidence == 0.8
        assert triple.evidence_type == EvidenceType.LLM_EXTRACTED
        assert triple.session_id is None
        assert triple.metadata == {}
        assert isinstance(triple.triple_id, UUID)
        assert isinstance(triple.created_at, datetime)

    def test_serialization_roundtrip(self):
        triple = ContextTriple(
            subject="vendor_risk",
            predicate="affects",
            object="budget_allocation",
            domain_source="procurement",
            domain_target="finance",
            confidence=0.9,
        )
        data = triple.model_dump(mode="json")
        assert data["subject"] == "vendor_risk"
        assert data["confidence"] == 0.9
        assert "triple_id" in data

        # Reconstruct
        restored = ContextTriple(**data)
        assert restored.subject == triple.subject
        assert restored.confidence == triple.confidence

    def test_confidence_validation(self):
        with pytest.raises(Exception):
            ContextTriple(
                subject="a", predicate="b", object="c",
                domain_source="d1", domain_target="d2",
                confidence=1.5,
            )


# ---------------------------------------------------------------------------
# GovernanceDomain
# ---------------------------------------------------------------------------

class TestGovernanceDomain:
    """Test GovernanceDomain model."""

    def test_creation(self):
        domain = GovernanceDomain(
            domain_id="procurement",
            display_name="Procurement",
            description="Procurement governance domain",
            tags=["supply-chain", "cost"],
        )
        assert domain.domain_id == "procurement"
        assert domain.display_name == "Procurement"
        assert "supply-chain" in domain.tags
        assert "cost" in domain.tags

    def test_defaults(self):
        domain = GovernanceDomain(
            domain_id="test",
            display_name="Test",
        )
        assert domain.description == ""
        assert domain.owner_email == ""
        assert domain.policy_namespace == ""
        assert domain.tags == []
        assert domain.color == "#6B7280"


# ---------------------------------------------------------------------------
# FederatedPolicy
# ---------------------------------------------------------------------------

class TestFederatedPolicy:
    """Test FederatedPolicy and FederatedPolicyRule models."""

    def test_policy_with_rules(self):
        rule = FederatedPolicyRule(
            name="max_spend",
            condition={"action_type": "purchase"},
            constraint={"max_amount": 100000},
            message="Purchases above 100k require approval",
            severity=ConflictSeverity.HIGH,
        )
        policy = FederatedPolicy(
            name="Spend Control",
            domain_id="procurement",
            namespace="procurement.spend",
            description="Controls procurement spending",
            rules=[rule],
            priority=80,
        )
        assert policy.name == "Spend Control"
        assert policy.domain_id == "procurement"
        assert policy.namespace == "procurement.spend"
        assert len(policy.rules) == 1
        assert policy.rules[0].name == "max_spend"
        assert policy.priority == 80
        assert policy.is_active is True

    def test_policy_defaults(self):
        policy = FederatedPolicy(
            name="Default",
            domain_id="test",
            namespace="test.default",
        )
        assert policy.rules == []
        assert policy.priority == 50
        assert policy.is_active is True
        assert policy.version == "1.0"
        assert policy.tags == []


# ---------------------------------------------------------------------------
# PolicyConflict
# ---------------------------------------------------------------------------

class TestPolicyConflict:
    """Test PolicyConflict model."""

    def test_creation(self):
        conflict = PolicyConflict(
            policy_a_id="policy-1",
            policy_a_name="Spend Control",
            policy_a_domain="procurement",
            policy_b_id="policy-2",
            policy_b_name="Carbon Budget",
            policy_b_domain="sustainability",
            conflict_type=ConflictType.CONTRADICTORY,
            severity=ConflictSeverity.HIGH,
            description="Opposing constraints on emergency procurement",
        )
        assert conflict.policy_a_id == "policy-1"
        assert conflict.policy_b_id == "policy-2"
        assert conflict.conflict_type == ConflictType.CONTRADICTORY
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.resolution is None
        assert conflict.resolved_at is None

    def test_serialization(self):
        conflict = PolicyConflict(
            policy_a_id="p1",
            policy_b_id="p2",
        )
        data = conflict.model_dump(mode="json")
        assert "conflict_id" in data
        assert data["policy_a_id"] == "p1"
        assert data["resolution"] is None


# ---------------------------------------------------------------------------
# CostBreakdown
# ---------------------------------------------------------------------------

class TestCostBreakdown:
    """Test CostBreakdown and CostBreakdownItem models."""

    def test_cost_breakdown_item(self):
        item = CostBreakdownItem(
            category="llm",
            label="LLM API Token Cost",
            amount=0.0042,
            details={"provider": "deepseek", "input_tokens": 1000},
        )
        assert item.category == "llm"
        assert item.amount == 0.0042

    def test_cost_breakdown_with_items(self):
        items = [
            CostBreakdownItem(category="llm", label="LLM Cost", amount=0.01),
            CostBreakdownItem(category="compute", label="Compute Cost", amount=0.005),
            CostBreakdownItem(category="risk", label="Risk Exposure", amount=50.0),
        ]
        breakdown = CostBreakdown(
            session_id="sess-1",
            llm_token_cost=0.01,
            llm_tokens_used=5000,
            total_cost=50.015,
            breakdown_items=items,
        )
        assert breakdown.session_id == "sess-1"
        assert len(breakdown.breakdown_items) == 3
        computed_total = sum(i.amount for i in breakdown.breakdown_items)
        assert abs(computed_total - 50.015) < 0.001

    def test_cost_breakdown_defaults(self):
        breakdown = CostBreakdown()
        assert breakdown.session_id is None
        assert breakdown.llm_token_cost == 0.0
        assert breakdown.total_cost == 0.0
        assert breakdown.breakdown_items == []


# ---------------------------------------------------------------------------
# ComplianceScore
# ---------------------------------------------------------------------------

class TestComplianceScore:
    """Test ComplianceScore and ComplianceArticle models."""

    def test_compliance_article(self):
        article = ComplianceArticle(
            article_id="Art.9",
            title="Risk Management System",
            score=0.85,
            status="compliant",
            evidence=["Guardian layer enforces risk-based policy checks"],
            gaps=[],
        )
        assert article.article_id == "Art.9"
        assert article.score == 0.85
        assert article.status == "compliant"
        assert len(article.evidence) == 1
        assert article.gaps == []

    def test_compliance_score_with_articles(self):
        articles = [
            ComplianceArticle(article_id="Art.9", score=0.85, status="compliant"),
            ComplianceArticle(article_id="Art.10", score=0.75, status="partial", gaps=["No bias detection"]),
        ]
        score = ComplianceScore(
            framework=ComplianceFramework.EU_AI_ACT,
            overall_score=0.80,
            articles=articles,
            gaps=["No bias detection"],
            recommendations=["Implement bias detection"],
        )
        assert score.framework == ComplianceFramework.EU_AI_ACT
        assert score.overall_score == 0.80
        assert len(score.articles) == 2
        assert len(score.gaps) == 1


# ---------------------------------------------------------------------------
# GovernanceAuditEntry
# ---------------------------------------------------------------------------

class TestGovernanceAuditEntry:
    """Test GovernanceAuditEntry model."""

    def test_creation_with_event_types(self):
        entry = GovernanceAuditEntry(
            event_type=GovernanceEventType.TRIPLE_CREATED,
            actor="governance_node",
            affected_domains=["procurement", "sustainability"],
            details={"triples_created": 3},
        )
        assert entry.event_type == GovernanceEventType.TRIPLE_CREATED
        assert entry.actor == "governance_node"
        assert len(entry.affected_domains) == 2
        assert isinstance(entry.entry_id, UUID)

    def test_policy_event(self):
        entry = GovernanceAuditEntry(
            event_type=GovernanceEventType.POLICY_REGISTERED,
            actor="api",
            affected_domains=["finance"],
            details={"namespace": "finance.risk", "rules_count": 3},
            session_id="sess-123",
        )
        assert entry.event_type == GovernanceEventType.POLICY_REGISTERED
        assert entry.session_id == "sess-123"

    def test_defaults(self):
        entry = GovernanceAuditEntry(
            event_type=GovernanceEventType.COST_COMPUTED,
        )
        assert entry.actor == "system"
        assert entry.affected_domains == []
        assert entry.details == {}
        assert entry.session_id is None


# ---------------------------------------------------------------------------
# Ancillary models
# ---------------------------------------------------------------------------

class TestAncillaryModels:
    """Test ImpactPath, CostAggregate, ROIMetrics, GovernanceHealth."""

    def test_impact_path(self):
        path = ImpactPath(
            source_domain="procurement",
            target_domain="sustainability",
            total_confidence=0.7,
            hop_count=2,
        )
        assert path.source_domain == "procurement"
        assert path.hop_count == 2
        assert path.path == []

    def test_cost_aggregate_defaults(self):
        agg = CostAggregate()
        assert agg.total_sessions == 0
        assert agg.total_cost == 0.0
        assert agg.cost_by_category == {}

    def test_roi_metrics(self):
        roi = ROIMetrics(
            ai_analysis_cost=5.0,
            manual_analysis_estimate=600.0,
            time_saved_hours=4.0,
            roi_percentage=11900.0,
        )
        assert roi.roi_percentage == 11900.0
        assert roi.ai_analysis_cost == 5.0

    def test_governance_health(self):
        health = GovernanceHealth(
            enabled=True,
            neo4j_available=False,
            domains_count=5,
            policies_count=12,
            active_conflicts=2,
            status="healthy",
        )
        assert health.enabled is True
        assert health.neo4j_available is False
        assert health.status == "healthy"
