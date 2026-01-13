"""Unit tests for the Cynefin Router."""

import pytest

from src.core.state import CynefinDomain, EpistemicState
from src.workflows.router import CynefinRouter, DomainClassification


class TestDomainClassification:
    """Tests for DomainClassification schema."""

    def test_valid_classification(self):
        """Test creating a valid classification."""
        classification = DomainClassification(
            domain=CynefinDomain.COMPLICATED,
            confidence=0.92,
            reasoning="Multiple factors require analysis",
            key_indicators=["root cause", "optimization"],
        )
        assert classification.domain == CynefinDomain.COMPLICATED
        assert classification.confidence == 0.92

    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            DomainClassification(
                domain=CynefinDomain.CLEAR,
                confidence=1.5,
                reasoning="Test",
            )

        with pytest.raises(ValueError):
            DomainClassification(
                domain=CynefinDomain.CLEAR,
                confidence=-0.1,
                reasoning="Test",
            )


class TestCynefinRouter:
    """Tests for the CynefinRouter."""

    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        return CynefinRouter(
            confidence_threshold=0.85,
            entropy_threshold_chaotic=0.9,
        )

    def test_router_initialization(self, router):
        """Test router initializes with correct parameters."""
        assert router.confidence_threshold == 0.85
        assert router.entropy_threshold_chaotic == 0.9

    def test_entropy_calculation_base(self, router):
        """Test base entropy for normal text."""
        entropy = router._calculate_entropy("What is the status of order 123?", {})
        assert 0 <= entropy <= 1
        assert entropy < 0.5  # Normal query should have low entropy

    def test_entropy_calculation_crisis_keywords(self, router):
        """Test entropy increases with crisis keywords."""
        normal_entropy = router._calculate_entropy("Check status", {})
        crisis_entropy = router._calculate_entropy(
            "EMERGENCY: System is down! Critical failure!", {}
        )
        assert crisis_entropy > normal_entropy

    def test_entropy_calculation_uncertainty(self, router):
        """Test entropy increases with uncertainty language."""
        certain = router._calculate_entropy("The answer is 42", {})
        uncertain = router._calculate_entropy(
            "Maybe it could possibly be unknown", {}
        )
        assert uncertain > certain

    def test_entropy_context_stability(self, router):
        """Test context can reduce entropy."""
        base_entropy = router._calculate_entropy("Process request", {})
        stable_entropy = router._calculate_entropy(
            "Process request",
            {"historical_pattern_known": True, "system_stable": True},
        )
        assert stable_entropy < base_entropy

    def test_confidence_level_high(self, router):
        """Test high confidence level mapping."""
        from src.core.state import ConfidenceLevel
        assert router._determine_confidence_level(0.95) == ConfidenceLevel.HIGH
        assert router._determine_confidence_level(0.85) == ConfidenceLevel.HIGH

    def test_confidence_level_medium(self, router):
        """Test medium confidence level mapping."""
        from src.core.state import ConfidenceLevel
        assert router._determine_confidence_level(0.7) == ConfidenceLevel.MEDIUM
        assert router._determine_confidence_level(0.6) == ConfidenceLevel.MEDIUM

    def test_confidence_level_low(self, router):
        """Test low confidence level mapping."""
        from src.core.state import ConfidenceLevel
        assert router._determine_confidence_level(0.5) == ConfidenceLevel.LOW
        assert router._determine_confidence_level(0.3) == ConfidenceLevel.LOW


class TestRouterHighEntropy:
    """Tests for high-entropy (Chaotic) routing."""

    @pytest.fixture
    def router(self):
        return CynefinRouter(entropy_threshold_chaotic=0.9)

    @pytest.mark.asyncio
    async def test_high_entropy_routes_to_chaotic(self, router):
        """Test that very high entropy triggers Chaotic classification."""
        state = EpistemicState(
            user_input="EMERGENCY CRITICAL URGENT: System crash failure alert warning immediately!"
        )

        # This should trigger chaotic due to high entropy
        result = await router.classify(state)

        # High entropy should trigger chaotic
        assert result.domain_entropy >= 0.8
        # Either Chaotic from entropy or Disorder from confidence
        assert result.cynefin_domain in [CynefinDomain.CHAOTIC, CynefinDomain.DISORDER]
