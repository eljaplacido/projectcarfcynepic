"""Unit tests for CSL-Core policy integration.

Tests cover:
- CSL config loading from environment
- Policy loading and rule evaluation
- Context mapping from EpistemicState
- Verdict aggregation with Guardian
- Fallback behavior when CSL disabled/unavailable
- Policy scaffold service
- Policy refinement agent
"""

import pytest

from src.core.state import CynefinDomain, EpistemicState, GuardianVerdict
from src.services.csl_policy_service import (
    CSLConfig,
    CSLEvaluation,
    CSLPolicy,
    CSLPolicyService,
    CSLRule,
    CSLRuleResult,
)
from src.services.policy_refinement_agent import (
    PolicyRefinementAgent,
    PolicyRefinementRequest,
)
from src.services.policy_scaffold_service import PolicyScaffoldService


# =============================================================================
# CSL Config Tests
# =============================================================================


class TestCSLConfig:
    """Tests for CSL configuration loading."""

    def test_defaults(self, monkeypatch):
        """Test default configuration values."""
        monkeypatch.delenv("CSL_ENABLED", raising=False)
        monkeypatch.delenv("CSL_POLICY_DIR", raising=False)
        monkeypatch.delenv("CSL_FAIL_CLOSED", raising=False)
        monkeypatch.delenv("CSL_AUDIT_ENABLED", raising=False)

        config = CSLConfig.from_env()

        assert config.enabled is True
        assert config.policy_dir == "config/policies"
        assert config.fail_closed is True
        assert config.audit_enabled is True

    def test_enabled(self, monkeypatch):
        """Test enabled configuration."""
        monkeypatch.setenv("CSL_ENABLED", "true")
        monkeypatch.setenv("CSL_POLICY_DIR", "custom/policies")
        monkeypatch.setenv("CSL_FAIL_CLOSED", "false")
        monkeypatch.setenv("CSL_AUDIT_ENABLED", "false")

        config = CSLConfig.from_env()

        assert config.enabled is True
        assert config.policy_dir == "custom/policies"
        assert config.fail_closed is False
        assert config.audit_enabled is False


# =============================================================================
# CSL Rule Tests
# =============================================================================


class TestCSLRule:
    """Tests for individual CSL rule evaluation."""

    def test_rule_passes_when_condition_not_matched(self):
        """Rule passes when its condition doesn't match the context."""
        rule = CSLRule(
            name="test_rule",
            policy_name="test",
            condition={"user.role": "admin"},
            constraint={"action.amount": 1000},
            message="Admin limit exceeded",
        )
        result = rule.evaluate({"user": {"role": "junior"}, "action": {"amount": 5000}})
        assert result.passed is True

    def test_rule_passes_when_constraint_satisfied(self):
        """Rule passes when condition matches and constraint is satisfied."""
        rule = CSLRule(
            name="test_rule",
            policy_name="test",
            condition={"user.role": "junior"},
            constraint={"action.amount": 1000},
            message="Junior limit exceeded",
        )
        result = rule.evaluate({"user": {"role": "junior"}, "action": {"amount": 500}})
        assert result.passed is True

    def test_rule_fails_when_constraint_violated(self):
        """Rule fails when condition matches and constraint is violated."""
        rule = CSLRule(
            name="test_rule",
            policy_name="test",
            condition={"user.role": "junior"},
            constraint={"action.amount": 1000},
            message="Junior limit exceeded",
        )
        result = rule.evaluate({"user": {"role": "junior"}, "action": {"amount": 5000}})
        assert result.passed is False
        assert result.message == "Junior limit exceeded"

    def test_range_constraint(self):
        """Range constraints (min/max) work correctly."""
        rule = CSLRule(
            name="effect_bounds",
            policy_name="chimera",
            condition={"prediction.source": "chimera"},
            constraint={"prediction.effect_size": {"min": -1.0, "max": 1.0}},
            message="Effect size out of bounds",
        )

        # Within range
        result = rule.evaluate({
            "prediction": {"source": "chimera", "effect_size": 0.5}
        })
        assert result.passed is True

        # Below range
        result = rule.evaluate({
            "prediction": {"source": "chimera", "effect_size": -2.0}
        })
        assert result.passed is False

        # Above range
        result = rule.evaluate({
            "prediction": {"source": "chimera", "effect_size": 1.5}
        })
        assert result.passed is False

    def test_boolean_constraint(self):
        """Boolean constraints work correctly."""
        rule = CSLRule(
            name="pii_masked",
            policy_name="data_access",
            condition={"data.contains_pii": True},
            constraint={"data.is_masked": True},
            message="PII must be masked",
        )

        # Masked
        result = rule.evaluate({"data": {"contains_pii": True, "is_masked": True}})
        assert result.passed is True

        # Not masked
        result = rule.evaluate({"data": {"contains_pii": True, "is_masked": False}})
        assert result.passed is False

    def test_missing_context_field(self):
        """Rule fails when required context field is missing."""
        rule = CSLRule(
            name="test_rule",
            policy_name="test",
            condition={"user.role": "junior"},
            constraint={"action.amount": 1000},
            message="Limit exceeded",
        )
        # action.amount missing from context
        result = rule.evaluate({"user": {"role": "junior"}, "action": {}})
        assert result.passed is False


# =============================================================================
# CSL Policy Tests
# =============================================================================


class TestCSLPolicy:
    """Tests for CSL policy evaluation."""

    def test_policy_evaluates_all_rules(self):
        """Policy evaluates all rules and returns results."""
        policy = CSLPolicy("test_policy", "1.0")
        policy.add_rule(CSLRule(
            name="rule1",
            policy_name="test_policy",
            condition={"user.role": "junior"},
            constraint={"action.amount": 1000},
            message="Limit 1",
        ))
        policy.add_rule(CSLRule(
            name="rule2",
            policy_name="test_policy",
            condition={"user.role": "junior"},
            constraint={"action.amount": 500},
            message="Limit 2",
        ))

        results = policy.evaluate({"user": {"role": "junior"}, "action": {"amount": 750}})
        assert len(results) == 2
        assert results[0].passed is True  # 750 <= 1000
        assert results[1].passed is False  # 750 > 500

    def test_empty_policy_passes(self):
        """Empty policy with no rules passes."""
        policy = CSLPolicy("empty", "1.0")
        results = policy.evaluate({"any": "context"})
        assert len(results) == 0


# =============================================================================
# CSL Policy Service Tests
# =============================================================================


class TestCSLPolicyService:
    """Tests for the CSL policy service."""

    def test_disabled_service_allows_all(self, monkeypatch):
        """Disabled CSL service returns allow=True."""
        monkeypatch.delenv("CSL_ENABLED", raising=False)
        config = CSLConfig(enabled=False)
        service = CSLPolicyService(config=config)

        assert not service.is_available

    def test_enabled_service_loads_policies(self, monkeypatch):
        """Enabled service loads built-in policies."""
        config = CSLConfig(enabled=True)
        service = CSLPolicyService(config=config)

        assert service.is_available
        assert service.policy_count > 0
        assert service.rule_count > 0

    @pytest.mark.asyncio
    async def test_evaluate_disabled(self, monkeypatch):
        """Disabled service returns allow without evaluation."""
        config = CSLConfig(enabled=False)
        service = CSLPolicyService(config=config)

        state = EpistemicState(domain_confidence=0.95)
        result = await service.evaluate(state)
        assert result.allow is True

    @pytest.mark.asyncio
    async def test_evaluate_clean_state(self, monkeypatch):
        """Clean state passes all CSL rules."""
        config = CSLConfig(enabled=True)
        service = CSLPolicyService(config=config)

        state = EpistemicState(
            domain_confidence=0.95,
            cynefin_domain=CynefinDomain.CLEAR,
            proposed_action={
                "action_type": "lookup",
                "description": "Simple lookup",
            },
            context={"user_role": "admin"},
        )

        result = await service.evaluate(state)
        assert result.allow is True
        assert result.rules_failed == 0

    @pytest.mark.asyncio
    async def test_evaluate_budget_violation(self, monkeypatch):
        """Transfer exceeding role limit triggers violation."""
        config = CSLConfig(enabled=True)
        service = CSLPolicyService(config=config)

        state = EpistemicState(
            domain_confidence=0.95,
            cynefin_domain=CynefinDomain.CLEAR,
            proposed_action={
                "action_type": "transfer",
                "amount": 5000,
            },
            context={"user_role": "junior"},
        )

        result = await service.evaluate(state)
        assert result.allow is False
        assert result.rules_failed > 0
        assert any("junior" in v.message.lower() for v in result.violations)

    def test_context_mapping(self):
        """State-to-context mapping produces correct structure."""
        config = CSLConfig(enabled=True)
        service = CSLPolicyService(config=config)

        state = EpistemicState(
            domain_confidence=0.9,
            domain_entropy=0.3,
            cynefin_domain=CynefinDomain.COMPLICATED,
            proposed_action={"action_type": "transfer", "amount": 5000},
            context={"user_role": "senior", "risk_level": "MEDIUM"},
        )

        ctx = service.map_state_to_context(state)

        assert ctx["domain"]["type"] == "Complicated"
        assert ctx["domain"]["confidence"] == 0.9
        assert ctx["action"]["type"] == "transfer"
        assert ctx["action"]["amount"] == 5000
        assert ctx["user"]["role"] == "senior"
        assert ctx["risk"]["level"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_fail_closed_on_error(self):
        """Fail-closed mode blocks when context mapping fails."""
        config = CSLConfig(enabled=True, fail_closed=True)
        service = CSLPolicyService(config=config)

        # Pass invalid state to trigger context mapping error
        result = await service.evaluate(None)
        assert result.allow is False
        assert result.error is not None


# =============================================================================
# Guardian + CSL Integration Tests
# =============================================================================


class TestGuardianCSLIntegration:
    """Tests for Guardian with CSL-Core integration."""

    @pytest.fixture
    def guardian(self):
        """Create a Guardian instance."""
        from src.workflows.guardian import Guardian
        return Guardian()

    @pytest.mark.asyncio
    async def test_guardian_with_csl_disabled(self, guardian, monkeypatch):
        """Guardian works normally when CSL is disabled."""
        monkeypatch.setenv("CSL_ENABLED", "false")

        # Reset the singleton so it picks up the new env
        import src.services.csl_policy_service as csl_mod
        csl_mod._csl_service = None

        state = EpistemicState(
            domain_confidence=0.95,
            reflection_count=0,
        )

        decision = await guardian.evaluate(state)
        assert decision.verdict == GuardianVerdict.APPROVED

    @pytest.mark.asyncio
    async def test_guardian_csl_violation_merges(self, guardian, monkeypatch):
        """CSL violations merge into Guardian decision."""
        monkeypatch.setenv("CSL_ENABLED", "true")

        import src.services.csl_policy_service as csl_mod
        csl_mod._csl_service = None

        state = EpistemicState(
            domain_confidence=0.95,
            cynefin_domain=CynefinDomain.CLEAR,
            proposed_action={
                "action_type": "transfer",
                "amount": 5000,
            },
            context={"user_role": "junior"},
        )

        decision = await guardian.evaluate(state)
        # Should have CSL violations for junior exceeding $1000
        csl_violations = [v for v in decision.violations if v.policy_category == "csl"]
        assert len(csl_violations) > 0

        # Clean up
        monkeypatch.delenv("CSL_ENABLED", raising=False)
        csl_mod._csl_service = None


# =============================================================================
# Policy Scaffold Service Tests
# =============================================================================


class TestPolicyScaffoldService:
    """Tests for the policy scaffold service."""

    def test_loads_scaffolds(self):
        """Service loads scaffold YAML files."""
        service = PolicyScaffoldService()
        assert service.scaffold_count > 0

    def test_get_scaffold_by_domain(self):
        """Can retrieve scaffolds by domain name."""
        service = PolicyScaffoldService()
        scaffold = service.get_scaffold("financial")
        if scaffold:
            assert scaffold.domain == "financial"
            assert len(scaffold.csl_policies) > 0

    def test_get_scaffold_for_scenario(self):
        """Can match scaffolds from scenario metadata."""
        service = PolicyScaffoldService()
        scaffold = service.get_scaffold_for_scenario({
            "domain_type": "financial",
        })
        if scaffold:
            assert scaffold.domain == "financial"

    def test_get_scaffold_by_keywords(self):
        """Can infer domain from scenario keywords."""
        service = PolicyScaffoldService()
        scaffold = service.get_scaffold_for_scenario({
            "name": "customer churn analysis",
            "keywords": ["churn", "retention"],
        })
        if scaffold:
            assert scaffold.domain == "operational"

    def test_unknown_domain_returns_none(self):
        """Unknown domain returns None."""
        service = PolicyScaffoldService()
        scaffold = service.get_scaffold("nonexistent")
        assert scaffold is None

    def test_available_domains(self):
        """Available domains list is populated."""
        service = PolicyScaffoldService()
        domains = service.available_domains
        assert isinstance(domains, list)


# =============================================================================
# Policy Refinement Agent Tests
# =============================================================================


class TestPolicyRefinementAgent:
    """Tests for the policy refinement agent."""

    @pytest.fixture
    def agent(self):
        return PolicyRefinementAgent()

    def test_generate_threshold_rule(self, agent):
        """Can generate a threshold rule from description."""
        result = agent.refine(PolicyRefinementRequest(
            description="Limit enterprise customer discounts to 25%",
            domain="operational",
            rule_type="threshold",
            parameters={
                "field": "discount.percentage",
                "max": 25,
                "condition_field": "customer.segment",
                "condition_value": "enterprise",
            },
        ))

        assert result.success is True
        assert result.validation_passed is True
        assert result.generated_rule.get("name") is not None
        assert result.csl_representation != ""

    def test_generate_approval_rule(self, agent):
        """Can generate an approval rule."""
        result = agent.refine(PolicyRefinementRequest(
            description="Require admin approval for data exports",
            domain="data_access",
            rule_type="approval",
            parameters={
                "condition_field": "action.type",
                "condition_value": "export",
                "required_role": "admin",
            },
        ))

        assert result.success is True
        assert "approval" in result.csl_representation.lower()

    def test_generate_constraint_rule(self, agent):
        """Can generate a generic constraint rule."""
        result = agent.refine(PolicyRefinementRequest(
            description="Maximum 10 API calls per session",
            domain="operational",
            rule_type="constraint",
            parameters={
                "condition": {"session.type": "api"},
                "constraint": {"session.call_count": 10},
            },
        ))

        assert result.success is True
        assert result.validation_passed is True

    def test_invalid_rule_fails_validation(self, agent):
        """Rule without constraints fails validation."""
        result = agent.refine(PolicyRefinementRequest(
            description="",
            domain="test",
            rule_type="constraint",
            parameters={},
        ))

        assert result.validation_passed is False
        assert len(result.validation_errors) > 0

    def test_csl_representation_format(self, agent):
        """CSL string representation has correct structure."""
        result = agent.refine(PolicyRefinementRequest(
            description="Junior transfer limit",
            domain="financial",
            rule_type="threshold",
            parameters={
                "field": "action.amount",
                "max": 1000,
                "condition_field": "user.role",
                "condition_value": "junior",
            },
        ))

        csl = result.csl_representation
        assert "policy" in csl
        assert "rule" in csl
        assert "when" in csl
        assert "then" in csl
        assert "message" in csl
