"""Unit tests for GovernanceService — central MAP-PRICE-RESOLVE orchestrator.

Tests map_impacts, compute_cost, resolve_tensions, compute_compliance,
get_impact_graph, get_audit_timeline, and get_health.
"""

import os
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"

from src.core.governance_models import (
    ComplianceFramework,
    ContextTriple,
    CostBreakdown,
    GovernanceEventType,
    GovernanceHealth,
)
from src.services.governance_service import GovernanceService


@pytest.fixture
def gov_service():
    """Create a fresh GovernanceService instance."""
    return GovernanceService()


def _make_state(user_input="", final_response="", context=None, session_id="test-sess"):
    """Build a mock state object (SimpleNamespace mimicking EpistemicState)."""
    return SimpleNamespace(
        user_input=user_input,
        final_response=final_response,
        context=context or {},
        session_id=session_id,
        causal_evidence=None,
        proposed_action=None,
    )


# ---------------------------------------------------------------------------
# MAP — map_impacts
# ---------------------------------------------------------------------------

class TestMapImpacts:
    """Test map_impacts entity extraction and triple creation."""

    def test_mentions_procurement_and_sustainability(self, gov_service):
        state = _make_state(
            user_input="Our procurement spend affects carbon emissions and sustainability goals"
        )
        triples = gov_service.map_impacts(state)
        assert len(triples) >= 1
        domains = set()
        for t in triples:
            domains.add(t.domain_source)
            domains.add(t.domain_target)
        assert "procurement" in domains
        assert "sustainability" in domains

    def test_mentions_three_domains(self, gov_service):
        state = _make_state(
            user_input="The procurement budget impacts our carbon emissions and financial risk"
        )
        triples = gov_service.map_impacts(state)
        # procurement + sustainability + finance = 3 domains, 3 pairs
        assert len(triples) >= 3

    def test_no_domains_returns_empty(self, gov_service):
        state = _make_state(user_input="Hello world, nothing relevant here")
        triples = gov_service.map_impacts(state)
        assert triples == []

    def test_single_domain_no_cross_impact(self, gov_service):
        state = _make_state(user_input="The procurement process is slow")
        triples = gov_service.map_impacts(state)
        assert triples == []

    def test_causal_evidence_extraction(self, gov_service):
        state = _make_state(user_input="supplier cost drives budget overrun")
        state.causal_evidence = SimpleNamespace(
            treatment="supplier cost",
            outcome="budget overrun",
        )
        triples = gov_service.map_impacts(state)
        # Should include the causal evidence triple (procurement -> finance)
        causal_triples = [t for t in triples if t.predicate == "causes"]
        assert len(causal_triples) >= 1

    def test_predicate_extraction(self, gov_service):
        state = _make_state(
            user_input="Procurement spending affects carbon emissions"
        )
        triples = gov_service.map_impacts(state)
        assert len(triples) >= 1
        assert triples[0].predicate == "affects"


# ---------------------------------------------------------------------------
# PRICE — compute_cost
# ---------------------------------------------------------------------------

class TestComputeCost:
    """Test compute_cost with mock state."""

    def test_compute_cost_basic(self, gov_service):
        state = _make_state()
        breakdown = gov_service.compute_cost(
            state, input_tokens=1000, output_tokens=500, compute_time_ms=2000,
        )
        assert isinstance(breakdown, CostBreakdown)
        assert breakdown.llm_input_tokens == 1000
        assert breakdown.llm_output_tokens == 500
        assert breakdown.total_cost >= 0

    def test_compute_cost_with_risk_context(self, gov_service):
        state = _make_state(context={"risk_level": "HIGH"})
        state.proposed_action = {"amount": 100000}
        breakdown = gov_service.compute_cost(
            state, input_tokens=500, output_tokens=200,
        )
        assert breakdown.risk_exposure_score > 0

    def test_compute_cost_zero_tokens(self, gov_service):
        state = _make_state()
        breakdown = gov_service.compute_cost(state, input_tokens=0, output_tokens=0)
        assert breakdown.llm_token_cost == 0.0


# ---------------------------------------------------------------------------
# RESOLVE — resolve_tensions
# ---------------------------------------------------------------------------

class TestResolveTensions:
    """Test resolve_tensions returns conflicts from federated service."""

    def test_resolve_tensions_returns_list(self, gov_service):
        state = _make_state()
        conflicts = gov_service.resolve_tensions(state)
        assert isinstance(conflicts, list)

    def test_get_unresolved_conflicts(self, gov_service):
        conflicts = gov_service.get_unresolved_conflicts()
        assert isinstance(conflicts, list)


# ---------------------------------------------------------------------------
# AUDIT — compute_compliance
# ---------------------------------------------------------------------------

class TestComputeCompliance:
    """Test compliance assessment for each framework."""

    def test_eu_ai_act(self, gov_service):
        score = gov_service.compute_compliance(ComplianceFramework.EU_AI_ACT)
        assert score.framework == ComplianceFramework.EU_AI_ACT
        assert 0 <= score.overall_score <= 1
        assert len(score.articles) > 0
        # EU AI Act has 6 articles assessed
        assert len(score.articles) == 6

    def test_csrd(self, gov_service):
        score = gov_service.compute_compliance(ComplianceFramework.CSRD)
        assert score.framework == ComplianceFramework.CSRD
        assert 0 <= score.overall_score <= 1
        assert len(score.articles) == 4

    def test_gdpr(self, gov_service):
        score = gov_service.compute_compliance(ComplianceFramework.GDPR)
        assert score.framework == ComplianceFramework.GDPR
        assert 0 <= score.overall_score <= 1
        assert len(score.articles) == 3

    def test_iso_27001(self, gov_service):
        score = gov_service.compute_compliance(ComplianceFramework.ISO_27001)
        assert score.framework == ComplianceFramework.ISO_27001
        assert 0 <= score.overall_score <= 1
        assert len(score.articles) == 3


# ---------------------------------------------------------------------------
# Impact graph
# ---------------------------------------------------------------------------

class TestImpactGraph:
    """Test get_impact_graph returns ReactFlow-ready data."""

    def test_get_impact_graph(self, gov_service):
        graph = gov_service.get_impact_graph()
        assert "nodes" in graph
        assert "edges" in graph
        assert isinstance(graph["nodes"], list)
        assert isinstance(graph["edges"], list)


# ---------------------------------------------------------------------------
# Audit timeline
# ---------------------------------------------------------------------------

class TestAuditTimeline:
    """Test get_audit_timeline merges logs from both services."""

    def test_audit_timeline_returns_list(self, gov_service):
        timeline = gov_service.get_audit_timeline()
        assert isinstance(timeline, list)

    def test_audit_timeline_limit(self, gov_service):
        timeline = gov_service.get_audit_timeline(limit=5)
        assert len(timeline) <= 5


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    """Test get_health returns GovernanceHealth."""

    def test_get_health(self, gov_service):
        health = gov_service.get_health()
        assert isinstance(health, GovernanceHealth)
        assert health.enabled is True
        assert health.status in ("healthy", "initialized")
