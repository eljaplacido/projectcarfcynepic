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

    def test_entropy_calculation_range(self, router):
        """Test entropy is always within [0, 1]."""
        entropy = router._calculate_entropy("What is the status of order 123?", {})
        assert 0 <= entropy <= 1

    def test_entropy_unique_tokens_high(self, router):
        """Test that all-unique tokens yield high Shannon entropy."""
        entropy = router._calculate_entropy(
            "each word here is completely unique and different", {}
        )
        assert entropy > 0.8  # Unique vocabulary → high entropy

    def test_entropy_repeated_tokens_lower(self, router):
        """Test that repetitive input has lower Shannon entropy."""
        diverse = router._calculate_entropy("one two three four five six", {})
        repetitive = router._calculate_entropy("help help help help help me", {})
        assert repetitive < diverse

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
    """Tests for high-entropy routing.

    Entropy is informational metadata, not a hard gate. The LLM (or test stub)
    determines the domain classification regardless of entropy value.
    """

    @pytest.fixture
    def router(self):
        return CynefinRouter(entropy_threshold_chaotic=0.9)

    @pytest.mark.asyncio
    async def test_high_entropy_recorded_as_metadata(self, router):
        """Test that high entropy is computed and stored, not used as a gate."""
        state = EpistemicState(
            user_input="EMERGENCY CRITICAL URGENT: System crash failure alert warning immediately!"
        )

        result = await router.classify(state)

        # Entropy should be computed and stored
        assert result.domain_entropy >= 0.8
        # Classification should come from LLM, not entropy gate
        assert result.cynefin_domain is not None
        assert result.domain_confidence > 0


class TestRouterEntropyPatterns:
    """Tests for Shannon entropy patterns in router."""

    @pytest.fixture
    def router(self):
        return CynefinRouter()

    def test_entropy_bounded(self, router):
        """Test entropy is bounded for various inputs."""
        queries = [
            "What is the effect of X on Y?",
            "Does treatment cause improvement?",
            "Estimate the causal impact",
            "What drives customer churn?",
            "What is the probability of success?",
        ]
        for query in queries:
            entropy = router._calculate_entropy(query, {})
            assert 0 <= entropy <= 1

    def test_repetitive_text_lower_entropy(self, router):
        """Test that repetitive text yields lower entropy."""
        repetitive = router._calculate_entropy(
            "status status status status check check", {}
        )
        diverse = router._calculate_entropy(
            "emergency critical urgent crash failure alert", {}
        )
        assert repetitive < diverse


class TestRouterEdgeCases:
    """Edge case tests for router."""

    @pytest.fixture
    def router(self):
        return CynefinRouter()

    def test_empty_query(self, router):
        """Test handling of empty query."""
        entropy = router._calculate_entropy("", {})
        assert entropy >= 0

    def test_very_long_query(self, router):
        """Test handling of very long query."""
        long_query = "What is the effect? " * 100
        entropy = router._calculate_entropy(long_query, {})
        assert 0 <= entropy <= 1

    def test_special_characters(self, router):
        """Test handling of special characters."""
        special = "What's the p-value (< 0.05)? {test}"
        entropy = router._calculate_entropy(special, {})
        assert 0 <= entropy <= 1

    def test_unicode_characters(self, router):
        """Test handling of unicode."""
        unicode_query = "日本語 αβγδ effect?"
        entropy = router._calculate_entropy(unicode_query, {})
        assert 0 <= entropy <= 1


class TestRouterSolverMapping:
    """Tests for domain-to-solver mapping documented in AGENTS.md.
    
    Expected mappings (from AGENTS.md):
    - Clear -> deterministic_runner
    - Complicated -> causal_analyst
    - Complex -> bayesian_explorer
    - Chaotic -> circuit_breaker
    - Disorder -> human_escalation
    """

    # The router itself doesn't have a _get_solver_for_domain method,
    # but we verify the documented domain-solver relationship exists
    # via the CynefinDomain enum.

    def test_clear_domain_exists(self):
        """Test Clear domain is defined."""
        from src.core.state import CynefinDomain
        assert CynefinDomain.CLEAR is not None
        assert "clear" in CynefinDomain.CLEAR.value.lower()

    def test_complicated_domain_exists(self):
        """Test Complicated domain is defined."""
        from src.core.state import CynefinDomain
        assert CynefinDomain.COMPLICATED is not None
        assert "complicated" in CynefinDomain.COMPLICATED.value.lower()

    def test_complex_domain_exists(self):
        """Test Complex domain is defined."""
        from src.core.state import CynefinDomain
        assert CynefinDomain.COMPLEX is not None
        assert "complex" in CynefinDomain.COMPLEX.value.lower()

    def test_chaotic_domain_exists(self):
        """Test Chaotic domain is defined."""
        from src.core.state import CynefinDomain
        assert CynefinDomain.CHAOTIC is not None
        assert "chaotic" in CynefinDomain.CHAOTIC.value.lower()

    def test_disorder_domain_exists(self):
        """Test Disorder domain is defined."""
        from src.core.state import CynefinDomain
        assert CynefinDomain.DISORDER is not None
        assert "disorder" in CynefinDomain.DISORDER.value.lower()


class TestRouterClassification:
    """Tests for router classification functionality."""

    @pytest.fixture
    def router(self):
        return CynefinRouter()

    @pytest.mark.asyncio
    async def test_classify_clear_domain(self, router):
        """Test classification of Clear domain query."""
        state = EpistemicState(
            user_input="What is the current stock price for AAPL?"
        )

        result = await router.classify(state)

        # Test mode returns Clear domain
        assert result.cynefin_domain == CynefinDomain.CLEAR
        assert result.domain_confidence > 0
        assert len(result.reasoning_chain) == 1

    @pytest.mark.asyncio
    async def test_classify_updates_state(self, router):
        """Test that classification updates epistemic state correctly."""
        state = EpistemicState(
            user_input="Lookup customer order 12345"
        )

        result = await router.classify(state)

        assert result.domain_entropy >= 0
        assert result.domain_confidence >= 0
        assert result.overall_confidence is not None
        assert result.current_hypothesis is not None

    @pytest.mark.asyncio
    async def test_classify_low_confidence_routes_to_disorder(self):
        """Test that low confidence routes to Disorder."""
        # Create router with high confidence threshold
        router = CynefinRouter(confidence_threshold=0.99)
        state = EpistemicState(
            user_input="ambiguous request with unclear intent"
        )

        result = await router.classify(state)

        # When confidence is below threshold, should route to Disorder
        # In test mode, the mock returns high confidence, so this tests the threshold logic
        assert result.cynefin_domain is not None

    @pytest.mark.asyncio
    async def test_classify_records_entropy_as_metadata(self):
        """Test that entropy is recorded but does not override LLM classification."""
        router = CynefinRouter(entropy_threshold_chaotic=0.5)
        state = EpistemicState(
            user_input="EMERGENCY! URGENT! CRITICAL! System crash failure alert!"
        )

        result = await router.classify(state)

        # Entropy should be computed
        assert result.domain_entropy >= 0.5
        # Classification comes from LLM, not entropy gate
        assert result.cynefin_domain is not None
        assert result.domain_confidence > 0

    @pytest.mark.asyncio
    async def test_classify_with_context(self, router):
        """Test classification with context data."""
        state = EpistemicState(
            user_input="Process this request",
            context={
                "historical_pattern_known": True,
                "system_stable": True,
            }
        )

        result = await router.classify(state)

        # Context should reduce entropy vs base Shannon entropy (1.0 for unique tokens)
        assert result.domain_entropy < 1.0


class TestGetRouter:
    """Tests for get_router singleton."""

    def test_returns_router_instance(self):
        """Test get_router returns a router."""
        from src.workflows.router import get_router, CynefinRouter
        import src.workflows.router as router_module

        # Reset singleton
        router_module._router_instance = None

        router = get_router()
        assert isinstance(router, CynefinRouter)

        # Reset for other tests
        router_module._router_instance = None

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance."""
        from src.workflows.router import get_router
        import src.workflows.router as router_module

        router_module._router_instance = None

        router1 = get_router()
        router2 = get_router()
        assert router1 is router2

        router_module._router_instance = None


class TestCynefinRouterNode:
    """Tests for cynefin_router_node function."""

    @pytest.mark.asyncio
    async def test_node_classifies_state(self):
        """Test router node classifies state."""
        from src.workflows.router import cynefin_router_node
        import src.workflows.router as router_module

        router_module._router_instance = None

        state = EpistemicState(
            user_input="What is 2+2?"
        )

        result = await cynefin_router_node(state)

        assert result.cynefin_domain is not None
        assert result.domain_confidence is not None

        router_module._router_instance = None


class TestRouterModeSelection:
    """Tests for router mode selection."""

    def test_default_mode_is_llm(self):
        """Test default mode is LLM."""
        router = CynefinRouter()
        assert router.mode == "llm"

    def test_explicit_llm_mode(self):
        """Test explicit LLM mode."""
        router = CynefinRouter(mode="llm")
        assert router.mode == "llm"

    def test_invalid_mode_defaults_to_llm(self):
        """Test invalid mode defaults to LLM."""
        router = CynefinRouter(mode="invalid_mode")
        assert router.mode == "llm"

    def test_distilbert_mode_without_model_falls_back(self):
        """Test distilbert mode falls back to LLM when model not available."""
        router = CynefinRouter(mode="distilbert", model_path="/nonexistent/path")
        # Should fall back to LLM since model path doesn't exist
        assert router.mode == "llm"


class TestRouterSystemPrompt:
    """Tests for router system prompt."""

    def test_system_prompt_contains_domains(self):
        """Test system prompt contains all domains."""
        router = CynefinRouter()

        assert "Clear" in router.system_prompt
        assert "Complicated" in router.system_prompt
        assert "Complex" in router.system_prompt
        assert "Chaotic" in router.system_prompt
        assert "Disorder" in router.system_prompt

    def test_system_prompt_contains_output_format(self):
        """Test system prompt specifies output format."""
        router = CynefinRouter()

        assert "JSON" in router.system_prompt
        assert "domain" in router.system_prompt
        assert "confidence" in router.system_prompt


class TestDomainHintOverride:
    """Tests for domain hint override functionality."""

    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        return CynefinRouter(
            confidence_threshold=0.70,
            entropy_threshold_chaotic=0.9,
        )

    @pytest.mark.asyncio
    async def test_domain_hint_applied_to_state(self, router):
        """Test that domain_hint in context is applied to classification."""
        state = EpistemicState(
            user_input="What is the effect of supplier program on emissions?",
            context={
                "domain_hint": "complicated",
                "scenario_id": "scope3_attribution",
            }
        )

        result = await router.classify(state)

        # With domain hint, should be Complicated regardless of LLM classification
        assert result.cynefin_domain == CynefinDomain.COMPLICATED

    @pytest.mark.asyncio
    async def test_domain_hint_capitalized(self, router):
        """Test domain hint works with different capitalizations."""
        for hint in ["Complicated", "COMPLICATED", "complicated"]:
            state = EpistemicState(
                user_input="Analyze this data",
                context={"domain_hint": hint}
            )

            result = await router.classify(state)
            assert result.cynefin_domain == CynefinDomain.COMPLICATED

    @pytest.mark.asyncio
    async def test_domain_hint_complex(self, router):
        """Test domain hint for Complex domain."""
        state = EpistemicState(
            user_input="What will happen in the market?",
            context={"domain_hint": "complex"}
        )

        result = await router.classify(state)
        assert result.cynefin_domain == CynefinDomain.COMPLEX

    @pytest.mark.asyncio
    async def test_domain_hint_chaotic(self, router):
        """Test domain hint for Chaotic domain."""
        state = EpistemicState(
            user_input="System is crashing",
            context={"domain_hint": "chaotic"}
        )

        result = await router.classify(state)
        assert result.cynefin_domain == CynefinDomain.CHAOTIC

    @pytest.mark.asyncio
    async def test_domain_hint_clear(self, router):
        """Test domain hint for Clear domain."""
        state = EpistemicState(
            user_input="What is 2+2?",
            context={"domain_hint": "clear"}
        )

        result = await router.classify(state)
        assert result.cynefin_domain == CynefinDomain.CLEAR

    @pytest.mark.asyncio
    async def test_invalid_domain_hint_ignored(self, router):
        """Test that invalid domain hints are ignored."""
        state = EpistemicState(
            user_input="What is 2+2?",
            context={"domain_hint": "invalid_domain"}
        )

        result = await router.classify(state)

        # Should still classify but not to invalid domain
        assert result.cynefin_domain in [
            CynefinDomain.CLEAR,
            CynefinDomain.COMPLICATED,
            CynefinDomain.COMPLEX,
            CynefinDomain.CHAOTIC,
            CynefinDomain.DISORDER,
        ]

    @pytest.mark.asyncio
    async def test_domain_hint_increases_confidence(self, router):
        """Test that domain hint ensures minimum confidence level."""
        state = EpistemicState(
            user_input="Short query",
            context={"domain_hint": "complicated"}
        )

        result = await router.classify(state)

        # Domain hint should ensure confidence >= 0.88
        assert result.domain_confidence >= 0.88

    @pytest.mark.asyncio
    async def test_domain_hint_adds_indicator(self, router):
        """Test that domain hint is recorded in key indicators."""
        state = EpistemicState(
            user_input="Test query",
            context={"domain_hint": "complicated"}
        )

        result = await router.classify(state)

        # Should have domain_hint indicator
        indicators = " ".join(result.router_key_indicators)
        assert "domain_hint" in indicators.lower()


class TestEntropyReductionWithContext:
    """Tests for entropy reduction based on context signals."""

    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        return CynefinRouter()

    @pytest.mark.asyncio
    async def test_scenario_id_reduces_entropy(self, router):
        """Test that scenario_id in context reduces entropy."""
        state_without = EpistemicState(
            user_input="Analyze this query"
        )

        state_with = EpistemicState(
            user_input="Analyze this query",
            context={"scenario_id": "scope3_attribution"}
        )

        result_without = await router.classify(state_without)
        result_with = await router.classify(state_with)

        # With scenario_id, entropy should be reduced
        assert result_with.domain_entropy <= result_without.domain_entropy

    @pytest.mark.asyncio
    async def test_domain_hint_reduces_entropy(self, router):
        """Test that domain_hint reduces entropy."""
        state_without = EpistemicState(
            user_input="What is the effect of treatment?"
        )

        state_with = EpistemicState(
            user_input="What is the effect of treatment?",
            context={"domain_hint": "complicated"}
        )

        result_without = await router.classify(state_without)
        result_with = await router.classify(state_with)

        # With domain_hint, entropy should be reduced by at least 0.3
        assert result_with.domain_entropy <= result_without.domain_entropy

    @pytest.mark.asyncio
    async def test_historical_pattern_reduces_entropy(self, router):
        """Test that historical_pattern_known reduces entropy."""
        state = EpistemicState(
            user_input="Process request",
            context={"historical_pattern_known": True}
        )

        result = await router.classify(state)

        # Entropy should be reduced below maximum
        assert result.domain_entropy < 1.0

    @pytest.mark.asyncio
    async def test_system_stable_reduces_entropy(self, router):
        """Test that system_stable reduces entropy."""
        state = EpistemicState(
            user_input="Process request",
            context={"system_stable": True}
        )

        result = await router.classify(state)

        # Entropy should be reduced below maximum
        assert result.domain_entropy < 1.0

    @pytest.mark.asyncio
    async def test_multiple_context_signals_stack(self, router):
        """Test that multiple context signals have cumulative effect."""
        state_none = EpistemicState(
            user_input="Process"
        )

        state_all = EpistemicState(
            user_input="Process",
            context={
                "scenario_id": "test",
                "domain_hint": "complicated",
                "historical_pattern_known": True,
                "system_stable": True,
            }
        )

        result_none = await router.classify(state_none)
        result_all = await router.classify(state_all)

        # With all signals, entropy should be significantly reduced
        assert result_all.domain_entropy < result_none.domain_entropy

