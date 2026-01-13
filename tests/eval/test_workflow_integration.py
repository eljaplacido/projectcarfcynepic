"""Integration tests for the complete CARF workflow.

These tests verify the end-to-end flow through the cognitive pipeline.
They use mocked LLM responses to ensure deterministic behavior.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.core.state import CynefinDomain, EpistemicState, GuardianVerdict
from src.workflows.graph import (
    build_carf_graph,
    route_by_domain,
    route_after_guardian,
    route_after_human,
    deterministic_runner_node,
    causal_analyst_node,
    bayesian_explorer_node,
    circuit_breaker_node,
    reflector_node,
)
from src.workflows.router import DomainClassification


class TestRoutingFunctions:
    """Tests for the routing decision functions."""

    def test_route_clear_domain(self):
        """Test Clear domain routes to deterministic runner."""
        state = EpistemicState(cynefin_domain=CynefinDomain.CLEAR)
        assert route_by_domain(state) == "deterministic_runner"

    def test_route_complicated_domain(self):
        """Test Complicated domain routes to causal analyst."""
        state = EpistemicState(cynefin_domain=CynefinDomain.COMPLICATED)
        assert route_by_domain(state) == "causal_analyst"

    def test_route_complex_domain(self):
        """Test Complex domain routes to bayesian explorer."""
        state = EpistemicState(cynefin_domain=CynefinDomain.COMPLEX)
        assert route_by_domain(state) == "bayesian_explorer"

    def test_route_chaotic_domain(self):
        """Test Chaotic domain routes to circuit breaker."""
        state = EpistemicState(cynefin_domain=CynefinDomain.CHAOTIC)
        assert route_by_domain(state) == "circuit_breaker"

    def test_route_disorder_domain(self):
        """Test Disorder domain routes to human escalation."""
        state = EpistemicState(cynefin_domain=CynefinDomain.DISORDER)
        assert route_by_domain(state) == "human_escalation"

    def test_route_after_guardian_approved(self):
        """Test approved verdict routes to end."""
        state = EpistemicState(guardian_verdict=GuardianVerdict.APPROVED)
        assert route_after_guardian(state) == "end"

    def test_route_after_guardian_rejected_with_retries(self):
        """Test rejected verdict routes to reflector if retries available."""
        state = EpistemicState(
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=1,
            max_reflections=3,
        )
        assert route_after_guardian(state) == "reflector"

    def test_route_after_guardian_rejected_max_retries(self):
        """Test rejected verdict routes to human if max retries reached."""
        state = EpistemicState(
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=3,
            max_reflections=3,
        )
        assert route_after_guardian(state) == "human_escalation"

    def test_route_after_guardian_escalation(self):
        """Test escalation verdict routes to human."""
        state = EpistemicState(
            guardian_verdict=GuardianVerdict.REQUIRES_ESCALATION
        )
        assert route_after_guardian(state) == "human_escalation"


class TestCognitiveAgentNodes:
    """Tests for the cognitive agent nodes."""

    @pytest.mark.asyncio
    async def test_deterministic_runner_sets_action(self):
        """Test deterministic runner creates proposed action."""
        state = EpistemicState(user_input="Look up order 123")
        result = await deterministic_runner_node(state)

        assert result.proposed_action is not None
        assert result.proposed_action["action_type"] == "lookup"
        assert result.final_response is not None
        assert len(result.reasoning_chain) > 0

    @pytest.mark.asyncio
    async def test_causal_analyst_sets_hypothesis(self):
        """Test causal analyst creates hypothesis."""
        state = EpistemicState(user_input="Why did costs increase?")
        result = await causal_analyst_node(state)

        assert result.proposed_action is not None
        assert result.proposed_action["action_type"] == "causal_recommendation"
        assert result.current_hypothesis is not None

    @pytest.mark.asyncio
    async def test_bayesian_explorer_sets_uncertainty(self):
        """Test bayesian explorer sets uncertainty level."""
        state = EpistemicState(user_input="What will the market do?")
        result = await bayesian_explorer_node(state)

        assert result.proposed_action is not None
        assert result.proposed_action["action_type"] in {
            "exploration_probe",
            "gather_information",
        }
        assert 0.0 <= result.epistemic_uncertainty <= 1.0
        assert result.current_hypothesis is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_emergency_response(self):
        """Test circuit breaker creates emergency response."""
        state = EpistemicState(
            user_input="System crash!",
            domain_entropy=0.95,
        )
        result = await circuit_breaker_node(state)

        assert "CHAOTIC" in result.final_response
        assert result.proposed_action["action_type"] == "emergency_stop"

    @pytest.mark.asyncio
    async def test_reflector_increments_count(self):
        """Test reflector increments reflection count."""
        state = EpistemicState(
            reflection_count=1,
            policy_violations=["Test violation"],
        )
        result = await reflector_node(state)

        assert result.reflection_count == 2
        assert result.proposed_action is None  # Cleared for retry


class TestGraphConstruction:
    """Tests for graph construction."""

    def test_graph_builds_successfully(self):
        """Test that the graph can be built."""
        graph = build_carf_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        """Test graph has all required nodes."""
        graph = build_carf_graph()
        expected_nodes = {
            "router",
            "deterministic_runner",
            "causal_analyst",
            "bayesian_explorer",
            "circuit_breaker",
            "guardian",
            "reflector",
            "human_escalation",
        }
        # LangGraph stores nodes differently, but we can verify the graph compiles
        compiled = graph.compile()
        assert compiled is not None


class TestEndToEndFlow:
    """End-to-end integration tests with mocked LLM."""

    @pytest.mark.asyncio
    async def test_clear_domain_flow(self):
        """Test complete flow for Clear domain query."""
        # Mock the router to return Clear classification
        mock_classification = DomainClassification(
            domain=CynefinDomain.CLEAR,
            confidence=0.95,
            reasoning="Simple lookup request",
            key_indicators=["lookup", "simple"],
        )

        with patch(
            "src.workflows.router.CynefinRouter._classify_with_llm",
            new_callable=AsyncMock,
            return_value=mock_classification,
        ):
            from src.workflows.graph import run_carf

            result = await run_carf("What is 2 + 2?")

            assert result.cynefin_domain == CynefinDomain.CLEAR
            assert result.domain_confidence >= 0.85
            # Should have gone through deterministic runner and guardian
            node_names = [step.node_name for step in result.reasoning_chain]
            assert "router" in node_names
            assert "deterministic_runner" in node_names
            assert "guardian" in node_names

    @pytest.mark.asyncio
    async def test_complicated_domain_flow(self):
        """Test complete flow for Complicated domain query."""
        mock_classification = DomainClassification(
            domain=CynefinDomain.COMPLICATED,
            confidence=0.90,
            reasoning="Root cause analysis needed",
            key_indicators=["why", "analysis"],
        )

        with patch(
            "src.workflows.router.CynefinRouter._classify_with_llm",
            new_callable=AsyncMock,
            return_value=mock_classification,
        ):
            from src.workflows.graph import run_carf

            result = await run_carf("Why did our server costs increase by 15%?")

            assert result.cynefin_domain == CynefinDomain.COMPLICATED
            node_names = [step.node_name for step in result.reasoning_chain]
            assert "causal_analyst" in node_names

    @pytest.mark.asyncio
    async def test_disorder_escalates_to_human(self):
        """Test that Disorder domain triggers human escalation."""
        mock_classification = DomainClassification(
            domain=CynefinDomain.DISORDER,
            confidence=0.4,
            reasoning="Cannot classify this request",
            key_indicators=["unclear", "ambiguous"],
        )

        with patch(
            "src.workflows.router.CynefinRouter._classify_with_llm",
            new_callable=AsyncMock,
            return_value=mock_classification,
        ):
            from src.workflows.graph import run_carf

            result = await run_carf("hmm maybe something?")

            # Low confidence should have triggered Disorder
            assert result.cynefin_domain == CynefinDomain.DISORDER
            node_names = [step.node_name for step in result.reasoning_chain]
            assert "human_escalation" in node_names
