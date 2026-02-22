"""Integration tests for the CARF Governance subsystem (MAP-PRICE-RESOLVE).

End-to-end governance flow:
- Create domains via FederatedPolicyService
- Register policies
- Run GovernanceService.map_impacts with a mock EpistemicState
- Verify triples are created
- Run compute_cost, verify breakdown
- Run resolve_tensions, verify conflicts returned
- Check audit timeline has entries

Set GOVERNANCE_ENABLED=true and CARF_TEST_MODE=1 for all tests.
"""

import os
import pytest
from unittest.mock import MagicMock

# Ensure governance and test mode are enabled for all tests in this module
os.environ["GOVERNANCE_ENABLED"] = "true"
os.environ["CARF_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset governance singletons between tests for isolation."""
    import src.services.governance_service as gs_mod
    import src.services.federated_policy_service as fps_mod

    gs_mod._governance_service = None
    fps_mod._federated_service = None
    yield
    gs_mod._governance_service = None
    fps_mod._federated_service = None


@pytest.fixture
def federated_service():
    """Create a fresh FederatedPolicyService with no auto-load from config dir."""
    from src.services.federated_policy_service import FederatedPolicyService

    # Point to a non-existent directory so load_policies is a no-op
    service = FederatedPolicyService(policy_dir="/tmp/carf_test_empty_policies")
    service._loaded = True  # Skip auto-load on first access
    return service


@pytest.fixture
def governance_service():
    """Create a fresh GovernanceService."""
    from src.services.governance_service import GovernanceService

    return GovernanceService()


@pytest.fixture
def mock_state():
    """Create a mock EpistemicState with cross-domain text."""
    state = MagicMock()
    state.user_input = "How does procurement supplier risk affect sustainability carbon emissions and security breach probability?"
    state.final_response = "The procurement decisions impact sustainability goals and security posture."
    state.session_id = "test-gov-session-001"
    state.context = {"risk_level": "MEDIUM"}
    state.causal_evidence = None
    state.proposed_action = {"action_type": "invest", "amount": 50000}
    return state


# =========================================================================
# Domain and Policy Registration
# =========================================================================


class TestDomainAndPolicyRegistration:
    """Tests for creating domains and registering policies."""

    def test_create_domains(self, federated_service):
        from src.core.governance_models import GovernanceDomain

        procurement = GovernanceDomain(
            domain_id="procurement",
            display_name="Procurement",
            description="Procurement governance",
            owner_email="proc@test.com",
            policy_namespace="procurement",
            color="#3B82F6",
        )
        sustainability = GovernanceDomain(
            domain_id="sustainability",
            display_name="Sustainability",
            description="Sustainability governance",
            owner_email="green@test.com",
            policy_namespace="sustainability",
            color="#10B981",
        )

        federated_service.register_domain(procurement)
        federated_service.register_domain(sustainability)

        domains = federated_service.list_domains()
        assert len(domains) == 2
        domain_ids = [d.domain_id for d in domains]
        assert "procurement" in domain_ids
        assert "sustainability" in domain_ids

    def test_register_policies(self, federated_service):
        from src.core.governance_models import (
            GovernanceDomain,
            FederatedPolicy,
            FederatedPolicyRule,
            ConflictSeverity,
        )

        # Register domains first
        federated_service.register_domain(GovernanceDomain(
            domain_id="procurement", display_name="Procurement",
            description="", owner_email="", policy_namespace="procurement",
        ))
        federated_service.register_domain(GovernanceDomain(
            domain_id="sustainability", display_name="Sustainability",
            description="", owner_email="", policy_namespace="sustainability",
        ))

        # Register policies
        policy_a = FederatedPolicy(
            name="Spend Cap Policy",
            domain_id="procurement",
            namespace="procurement.spend_cap",
            description="Limits max spend per vendor",
            rules=[
                FederatedPolicyRule(
                    name="max_spend",
                    condition={"vendor_type": "external"},
                    constraint={"max_amount": 100000},
                    message="Vendor spend exceeds cap",
                    severity=ConflictSeverity.HIGH,
                ),
            ],
            priority=80,
        )
        policy_b = FederatedPolicy(
            name="Green Budget Policy",
            domain_id="sustainability",
            namespace="sustainability.green_budget",
            description="Mandates minimum green spend",
            rules=[
                FederatedPolicyRule(
                    name="min_green_spend",
                    condition={"vendor_type": "external"},
                    constraint={"max_amount": 200000},
                    message="Green spend requirement not met",
                    severity=ConflictSeverity.MEDIUM,
                ),
            ],
            priority=90,
        )

        federated_service.add_policy(policy_a)
        federated_service.add_policy(policy_b)

        policies = federated_service.list_policies()
        assert len(policies) == 2

        proc_policies = federated_service.list_policies(domain_id="procurement")
        assert len(proc_policies) == 1
        assert proc_policies[0].name == "Spend Cap Policy"


# =========================================================================
# MAP — Triple Creation
# =========================================================================


class TestMapImpacts:
    """Tests for GovernanceService.map_impacts triple creation."""

    def test_map_impacts_creates_triples(self, governance_service, mock_state):
        triples = governance_service.map_impacts(mock_state)

        # The mock text mentions procurement, sustainability, and security
        assert len(triples) >= 1, "At least one cross-domain triple should be created"

        # All triples should have domain_source and domain_target
        for triple in triples:
            assert triple.domain_source is not None
            assert triple.domain_target is not None
            assert triple.domain_source != triple.domain_target
            assert triple.confidence > 0
            assert triple.session_id == "test-gov-session-001"

    def test_map_impacts_detects_multiple_domains(self, governance_service, mock_state):
        triples = governance_service.map_impacts(mock_state)

        domains_found = set()
        for triple in triples:
            domains_found.add(triple.domain_source)
            domains_found.add(triple.domain_target)

        # Should detect at least procurement and sustainability
        assert "procurement" in domains_found
        assert "sustainability" in domains_found

    def test_map_impacts_with_no_cross_domain_text(self, governance_service):
        state = MagicMock()
        state.user_input = "Hello world"
        state.final_response = "Generic response"
        state.session_id = "test-no-domains"
        state.causal_evidence = None

        triples = governance_service.map_impacts(state)
        # No domain keywords => no cross-domain triples
        assert len(triples) == 0


# =========================================================================
# PRICE — Cost Computation
# =========================================================================


class TestCostComputation:
    """Tests for GovernanceService.compute_cost breakdown."""

    def test_compute_cost_returns_breakdown(self, governance_service, mock_state):
        breakdown = governance_service.compute_cost(
            mock_state,
            input_tokens=500,
            output_tokens=300,
            compute_time_ms=150.0,
        )

        assert breakdown is not None
        assert breakdown.total_cost >= 0
        assert breakdown.llm_token_cost >= 0
        assert breakdown.llm_tokens_used >= 0

    def test_compute_cost_includes_risk_exposure(self, governance_service, mock_state):
        # mock_state.context has risk_level=MEDIUM
        breakdown = governance_service.compute_cost(
            mock_state,
            input_tokens=100,
            output_tokens=100,
            compute_time_ms=50.0,
        )

        # With MEDIUM risk and amount=50000, risk_exposure should be > 0
        assert breakdown.risk_exposure_score >= 0

    def test_compute_cost_logs_audit_event(self, governance_service, mock_state):
        governance_service.compute_cost(mock_state, input_tokens=10, output_tokens=10)

        audit = governance_service.get_audit_timeline()
        cost_events = [e for e in audit if e.event_type.value == "cost_computed"]
        assert len(cost_events) >= 1


# =========================================================================
# RESOLVE — Conflict Detection
# =========================================================================


class TestConflictResolution:
    """Tests for GovernanceService.resolve_tensions conflict detection."""

    def test_resolve_tensions_with_conflicts(self, federated_service):
        from src.core.governance_models import (
            GovernanceDomain,
            FederatedPolicy,
            FederatedPolicyRule,
            ConflictSeverity,
        )
        import src.services.federated_policy_service as fps_mod

        # Set as global singleton so governance_service can access it
        fps_mod._federated_service = federated_service

        federated_service.register_domain(GovernanceDomain(
            domain_id="procurement", display_name="Procurement",
            description="", owner_email="", policy_namespace="procurement",
        ))
        federated_service.register_domain(GovernanceDomain(
            domain_id="sustainability", display_name="Sustainability",
            description="", owner_email="", policy_namespace="sustainability",
        ))

        # Create conflicting policies (same condition keys, different constraint values)
        federated_service.add_policy(FederatedPolicy(
            name="Procurement Budget",
            domain_id="procurement",
            namespace="procurement.budget",
            description="Budget limits",
            rules=[FederatedPolicyRule(
                name="budget_limit",
                condition={"vendor_type": "external"},
                constraint={"max_amount": 100000, "require_approval": True},
                message="Budget limit",
                severity=ConflictSeverity.HIGH,
            )],
            priority=80,
        ))

        federated_service.add_policy(FederatedPolicy(
            name="Green Spending",
            domain_id="sustainability",
            namespace="sustainability.green",
            description="Green spend",
            rules=[FederatedPolicyRule(
                name="green_budget",
                condition={"vendor_type": "external"},
                constraint={"max_amount": 200000, "require_approval": False},
                message="Green budget",
                severity=ConflictSeverity.MEDIUM,
            )],
            priority=90,
        ))

        # Now there should be conflicts
        from src.services.governance_service import GovernanceService

        gov = GovernanceService()
        mock_state = MagicMock()
        conflicts = gov.resolve_tensions(mock_state)

        assert len(conflicts) >= 1
        conflict = conflicts[0]
        assert conflict.policy_a_domain != conflict.policy_b_domain
        assert conflict.resolution is None  # Not yet resolved

    def test_resolve_tensions_returns_empty_when_no_conflicts(self, federated_service):
        import src.services.federated_policy_service as fps_mod

        fps_mod._federated_service = federated_service

        from src.services.governance_service import GovernanceService

        gov = GovernanceService()
        mock_state = MagicMock()
        conflicts = gov.resolve_tensions(mock_state)
        assert len(conflicts) == 0


# =========================================================================
# AUDIT — Timeline Verification
# =========================================================================


class TestAuditTimeline:
    """Tests for governance audit timeline entries."""

    def test_audit_timeline_records_map_events(self, governance_service, mock_state):
        governance_service.map_impacts(mock_state)

        timeline = governance_service.get_audit_timeline()
        assert len(timeline) >= 1

        event_types = [e.event_type.value for e in timeline]
        assert "triple_created" in event_types

    def test_audit_timeline_records_cost_events(self, governance_service, mock_state):
        governance_service.compute_cost(mock_state, input_tokens=10, output_tokens=10)

        timeline = governance_service.get_audit_timeline()
        event_types = [e.event_type.value for e in timeline]
        assert "cost_computed" in event_types

    def test_audit_timeline_has_session_details(self, governance_service, mock_state):
        governance_service.map_impacts(mock_state)

        timeline = governance_service.get_audit_timeline()
        assert len(timeline) >= 1

        # At least one event should reference the session
        has_session = any(
            e.details.get("session_id") == "test-gov-session-001"
            for e in timeline
        )
        assert has_session, "Audit timeline should reference the session ID"

    def test_audit_timeline_respects_limit(self, governance_service, mock_state):
        # Generate multiple events
        for _ in range(5):
            governance_service.map_impacts(mock_state)

        timeline_all = governance_service.get_audit_timeline(limit=100)
        timeline_limited = governance_service.get_audit_timeline(limit=2)

        assert len(timeline_limited) <= 2
        assert len(timeline_all) >= len(timeline_limited)
