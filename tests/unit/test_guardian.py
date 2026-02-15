"""Unit tests for the Guardian layer."""

import pytest

from src.core.state import CynefinDomain, EpistemicState, GuardianVerdict
from src.workflows.guardian import Guardian, PolicyEngine, PolicyViolation


class TestPolicyEngine:
    """Tests for the PolicyEngine."""

    @pytest.fixture
    def engine(self):
        """Create a policy engine with default policies."""
        return PolicyEngine()

    def test_financial_limit_below(self, engine):
        """Test amount below limit passes."""
        violations = engine.check_financial_limit(50000)
        assert violations == []

    def test_financial_limit_above(self, engine):
        """Test amount above limit triggers violation."""
        violations = engine.check_financial_limit(150000)
        assert len(violations) == 1
        assert violations[0].policy_name == "auto_approval_limit"
        assert violations[0].severity == "high"

    def test_financial_limit_exact(self, engine):
        """Test exact limit passes."""
        violations = engine.check_financial_limit(100000)
        assert violations == []

    def test_financial_limit_currency_mismatch(self, engine):
        """Test currency mismatch is flagged as violation."""
        violations = engine.check_financial_limit(50000, currency="JPY")
        assert len(violations) == 1
        assert violations[0].policy_name == "currency_mismatch"
        assert violations[0].severity == "medium"

    def test_always_escalate_delete(self, engine):
        """Test delete_data triggers escalation."""
        violation = engine.check_always_escalate("delete_data")
        assert violation is not None
        assert "mandatory" in violation.description.lower()

    def test_always_escalate_normal_action(self, engine):
        """Test normal actions pass."""
        violation = engine.check_always_escalate("lookup")
        assert violation is None

    def test_reflection_limit_below(self, engine):
        """Test reflection count below limit passes."""
        violation = engine.check_reflection_limit(1)
        assert violation is None

    def test_reflection_limit_reached(self, engine):
        """Test reflection count at limit triggers violation."""
        violation = engine.check_reflection_limit(3)
        assert violation is not None
        assert "reflection" in violation.description.lower()

    def test_confidence_threshold_high(self, engine):
        """Test high confidence passes."""
        violation = engine.check_confidence_threshold(0.95)
        assert violation is None

    def test_confidence_threshold_low(self, engine):
        """Test low confidence triggers violation."""
        violation = engine.check_confidence_threshold(0.5)
        assert violation is not None
        assert "confidence" in violation.description.lower()


class TestGuardian:
    """Tests for the Guardian."""

    @pytest.fixture
    def guardian(self):
        """Create a Guardian instance."""
        return Guardian()

    @pytest.mark.asyncio
    async def test_approve_clean_state(self, guardian, monkeypatch):
        """Test clean state gets approved."""
        monkeypatch.setenv("CSL_ENABLED", "false")
        import src.services.csl_policy_service as csl_mod
        csl_mod._csl_service = None

        state = EpistemicState(
            domain_confidence=0.95,
            reflection_count=0,
        )

        decision = await guardian.evaluate(state)
        assert decision.verdict == GuardianVerdict.APPROVED
        assert len(decision.violations) == 0
        assert decision.risk_level == "low"

    @pytest.mark.asyncio
    async def test_reject_low_confidence(self, guardian):
        """Test low confidence triggers rejection/escalation.

        With context-aware policies, confidence thresholds vary by domain:
        - Clear: 0.95, Complicated: 0.85, Complex: 0.70, Chaotic: 0.50, Disorder: 0.0
        Testing with Complicated domain (threshold 0.85) and confidence 0.5.
        """
        state = EpistemicState(
            cynefin_domain=CynefinDomain.COMPLICATED,  # Threshold: 0.85
            domain_confidence=0.5,  # Below 0.85 threshold
            reflection_count=0,
        )

        decision = await guardian.evaluate(state)
        # Low confidence should require escalation
        assert decision.verdict in [
            GuardianVerdict.REJECTED,
            GuardianVerdict.REQUIRES_ESCALATION,
        ]
        assert len(decision.violations) > 0

    @pytest.mark.asyncio
    async def test_escalate_high_amount(self, guardian):
        """Test high transaction amount requires escalation."""
        state = EpistemicState(
            domain_confidence=0.95,
            proposed_action={
                "action_type": "transfer",
                "amount": 150000,
                "currency": "USD",
            },
        )

        decision = await guardian.evaluate(state)
        assert decision.verdict == GuardianVerdict.REQUIRES_ESCALATION
        assert any("auto_approval_limit" in v.policy_name for v in decision.violations)

    @pytest.mark.asyncio
    async def test_escalate_dangerous_action(self, guardian):
        """Test dangerous action types require escalation."""
        state = EpistemicState(
            domain_confidence=0.95,
            proposed_action={
                "action_type": "delete_data",
            },
        )

        decision = await guardian.evaluate(state)
        assert decision.verdict == GuardianVerdict.REQUIRES_ESCALATION

    @pytest.mark.asyncio
    async def test_escalate_max_reflections(self, guardian):
        """Test max reflections triggers escalation."""
        state = EpistemicState(
            domain_confidence=0.95,
            reflection_count=3,
        )

        decision = await guardian.evaluate(state)
        assert decision.verdict == GuardianVerdict.REQUIRES_ESCALATION

    @pytest.mark.asyncio
    async def test_check_updates_state(self, guardian):
        """Test check method updates the epistemic state."""
        state = EpistemicState(
            domain_confidence=0.95,
            reflection_count=0,
        )

        result = await guardian.check(state)

        assert result.guardian_verdict is not None
        assert len(result.reasoning_chain) > 0
        assert result.reasoning_chain[-1].node_name == "guardian"
