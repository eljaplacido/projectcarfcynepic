"""Unit tests for FederatedPolicyService.

Tests domain CRUD, policy CRUD, conflict detection/resolution,
CSL conversion, and audit logging.
"""

import os
import tempfile
import pytest
from pathlib import Path

os.environ["CARF_TEST_MODE"] = "1"

from src.core.governance_models import (
    ConflictSeverity,
    ConflictType,
    FederatedPolicy,
    FederatedPolicyRule,
    GovernanceDomain,
    GovernanceEventType,
)
from src.services.federated_policy_service import FederatedPolicyService


@pytest.fixture
def service():
    """Create a fresh FederatedPolicyService with an empty temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = FederatedPolicyService(policy_dir=tmpdir)
        yield svc


@pytest.fixture
def service_with_domain(service):
    """Service with a pre-registered domain."""
    domain = GovernanceDomain(
        domain_id="procurement",
        display_name="Procurement",
        description="Procurement governance domain",
        tags=["supply-chain"],
    )
    service.register_domain(domain)
    return service


@pytest.fixture
def sample_policy():
    """Create a sample FederatedPolicy."""
    return FederatedPolicy(
        name="Spend Control",
        domain_id="procurement",
        namespace="procurement.spend",
        description="Controls procurement spending limits",
        rules=[
            FederatedPolicyRule(
                name="max_spend",
                condition={"action_type": "purchase"},
                constraint={"max_amount": 100000},
                message="Purchases above 100k require approval",
                severity=ConflictSeverity.HIGH,
            ),
        ],
        priority=80,
    )


# ---------------------------------------------------------------------------
# Load policies
# ---------------------------------------------------------------------------

class TestLoadPolicies:
    """Test loading policies from directory."""

    def test_load_empty_directory(self, service):
        service.load_policies()
        assert service._loaded is True
        assert len(service.list_domains()) == 0

    def test_load_from_nonexistent_directory(self):
        svc = FederatedPolicyService(policy_dir="/nonexistent/path/abc123")
        svc.load_policies()
        assert svc._loaded is True
        assert len(svc.list_domains()) == 0

    def test_load_yaml_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_content = """
domain:
  id: test_domain
  display_name: Test Domain
  description: A test domain
  tags:
    - test
policies:
  - name: test_policy
    namespace: test_domain.policy1
    description: Test policy
    priority: 60
    rules:
      - name: rule1
        condition:
          action_type: test
        constraint:
          allowed: true
        message: Test rule
        severity: low
"""
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text(yaml_content, encoding="utf-8")

            svc = FederatedPolicyService(policy_dir=tmpdir)
            svc.load_policies()

            assert len(svc.list_domains()) == 1
            domain = svc.get_domain("test_domain")
            assert domain is not None
            assert domain.display_name == "Test Domain"

            policies = svc.list_policies()
            assert len(policies) == 1
            assert policies[0].namespace == "test_domain.policy1"


# ---------------------------------------------------------------------------
# Domain CRUD
# ---------------------------------------------------------------------------

class TestDomainCRUD:
    """Test domain registration, listing, retrieval, and updates."""

    def test_register_domain(self, service):
        domain = GovernanceDomain(
            domain_id="sustainability",
            display_name="Sustainability",
        )
        result = service.register_domain(domain)
        assert result.domain_id == "sustainability"

    def test_list_domains(self, service_with_domain):
        domains = service_with_domain.list_domains()
        assert len(domains) >= 1
        assert any(d.domain_id == "procurement" for d in domains)

    def test_get_domain(self, service_with_domain):
        domain = service_with_domain.get_domain("procurement")
        assert domain is not None
        assert domain.display_name == "Procurement"

    def test_get_nonexistent_domain(self, service):
        assert service.get_domain("nonexistent") is None

    def test_update_domain(self, service_with_domain):
        updated = service_with_domain.update_domain("procurement", {
            "description": "Updated description"
        })
        assert updated is not None
        assert updated.description == "Updated description"

    def test_update_nonexistent_domain(self, service):
        assert service.update_domain("nonexistent", {"description": "x"}) is None


# ---------------------------------------------------------------------------
# Policy CRUD
# ---------------------------------------------------------------------------

class TestPolicyCRUD:
    """Test policy add, list, get, update, remove."""

    def test_add_policy(self, service, sample_policy):
        result = service.add_policy(sample_policy)
        assert result.namespace == "procurement.spend"
        assert result.name == "Spend Control"

    def test_list_all_policies(self, service, sample_policy):
        service.add_policy(sample_policy)
        policies = service.list_policies()
        assert len(policies) == 1

    def test_list_policies_by_domain(self, service, sample_policy):
        service.add_policy(sample_policy)
        proc_policies = service.list_policies(domain_id="procurement")
        assert len(proc_policies) == 1
        other_policies = service.list_policies(domain_id="security")
        assert len(other_policies) == 0

    def test_get_policy_by_namespace(self, service, sample_policy):
        service.add_policy(sample_policy)
        policy = service.get_policy("procurement.spend")
        assert policy is not None
        assert policy.name == "Spend Control"

    def test_get_nonexistent_policy(self, service):
        assert service.get_policy("nonexistent.ns") is None

    def test_update_policy(self, service, sample_policy):
        service.add_policy(sample_policy)
        updated = service.update_policy("procurement.spend", {"description": "New desc"})
        assert updated is not None
        assert updated.description == "New desc"

    def test_update_nonexistent_policy(self, service):
        assert service.update_policy("nonexistent.ns", {"description": "x"}) is None

    def test_remove_policy(self, service, sample_policy):
        service.add_policy(sample_policy)
        assert service.remove_policy("procurement.spend") is True
        assert service.get_policy("procurement.spend") is None

    def test_remove_nonexistent_policy(self, service):
        assert service.remove_policy("nonexistent.ns") is False


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Test cross-domain conflict detection between policies."""

    def test_detect_conflict_overlapping_conditions(self, service):
        # Policy A: procurement domain
        policy_a = FederatedPolicy(
            name="Procurement Speed",
            domain_id="procurement",
            namespace="procurement.speed",
            rules=[
                FederatedPolicyRule(
                    name="fast_delivery",
                    condition={"action_type": "purchase", "emergency": True},
                    constraint={"max_delivery_days": 3, "allow_air_freight": True},
                    message="Emergency purchases require fast delivery",
                ),
            ],
        )
        service.add_policy(policy_a)

        # Policy B: sustainability domain — overlapping condition keys, conflicting constraints
        policy_b = FederatedPolicy(
            name="Carbon Limits",
            domain_id="sustainability",
            namespace="sustainability.carbon",
            rules=[
                FederatedPolicyRule(
                    name="no_air_freight",
                    condition={"action_type": "purchase", "emergency": True},
                    constraint={"max_delivery_days": 14, "allow_air_freight": False},
                    message="Air freight exceeds carbon budget",
                ),
            ],
        )
        conflicts = service.detect_conflicts(policy_b)
        assert len(conflicts) >= 1
        # The contradictory boolean (True vs False for allow_air_freight) should be detected
        assert any(c.conflict_type == ConflictType.CONTRADICTORY for c in conflicts)

    def test_no_conflict_same_domain(self, service):
        policy_a = FederatedPolicy(
            name="Policy A",
            domain_id="procurement",
            namespace="procurement.a",
            rules=[FederatedPolicyRule(
                name="r1",
                condition={"action_type": "purchase"},
                constraint={"max_amount": 100000},
            )],
        )
        service.add_policy(policy_a)

        policy_b = FederatedPolicy(
            name="Policy B",
            domain_id="procurement",
            namespace="procurement.b",
            rules=[FederatedPolicyRule(
                name="r2",
                condition={"action_type": "purchase"},
                constraint={"max_amount": 50000},
            )],
        )
        # Same domain should not conflict
        conflicts = service.detect_conflicts(policy_b)
        assert len(conflicts) == 0


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------

class TestConflictResolution:
    """Test conflict resolution and unresolved listing."""

    def test_resolve_conflict(self, service):
        # Create a conflict manually
        policy_a = FederatedPolicy(
            name="Proc Speed", domain_id="procurement", namespace="proc.speed",
            rules=[FederatedPolicyRule(
                name="r1",
                condition={"type": "purchase"},
                constraint={"fast": True},
            )],
        )
        service.add_policy(policy_a)

        policy_b = FederatedPolicy(
            name="Green Limit", domain_id="sustainability", namespace="sus.limit",
            rules=[FederatedPolicyRule(
                name="r2",
                condition={"type": "purchase"},
                constraint={"fast": False},
            )],
        )
        conflicts = service.detect_conflicts(policy_b)
        assert len(conflicts) >= 1

        conflict_id = str(conflicts[0].conflict_id)
        resolved = service.resolve_conflict(conflict_id, "Prioritize sustainability", "admin")
        assert resolved is not None
        assert resolved.resolution == "Prioritize sustainability"
        assert resolved.resolved_by == "admin"
        assert resolved.resolved_at is not None

    def test_resolve_nonexistent_conflict(self, service):
        assert service.resolve_conflict("nonexistent-id", "resolution") is None

    def test_get_unresolved_conflicts(self, service):
        # Initially empty
        assert service.get_unresolved_conflicts() == []


# ---------------------------------------------------------------------------
# CSL conversion
# ---------------------------------------------------------------------------

class TestCSLConversion:
    """Test conversion to CSL policy format."""

    def test_get_csl_policies_empty(self, service):
        result = service.get_csl_policies()
        # May return [] if CSL service not importable or no policies
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    """Test audit logging."""

    def test_audit_log_records_domain_creation(self, service):
        domain = GovernanceDomain(domain_id="test", display_name="Test")
        service.register_domain(domain)
        log = service.get_audit_log()
        assert len(log) >= 1
        assert any(e.event_type == GovernanceEventType.DOMAIN_CREATED for e in log)

    def test_audit_log_records_policy_registration(self, service, sample_policy):
        service.add_policy(sample_policy)
        log = service.get_audit_log()
        assert any(e.event_type == GovernanceEventType.POLICY_REGISTERED for e in log)

    def test_audit_log_filter_by_domain(self, service):
        service.register_domain(GovernanceDomain(domain_id="d1", display_name="D1"))
        service.register_domain(GovernanceDomain(domain_id="d2", display_name="D2"))
        log = service.get_audit_log(domain_id="d1")
        assert all("d1" in e.affected_domains for e in log)

    def test_audit_log_filter_by_event_type(self, service, sample_policy):
        service.register_domain(GovernanceDomain(domain_id="procurement", display_name="P"))
        service.add_policy(sample_policy)
        log = service.get_audit_log(event_type=GovernanceEventType.POLICY_REGISTERED)
        assert all(e.event_type == GovernanceEventType.POLICY_REGISTERED for e in log)
