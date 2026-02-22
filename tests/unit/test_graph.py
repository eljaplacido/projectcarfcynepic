"""Tests for src/workflows/graph.py."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.workflows.graph import (
    deterministic_runner_node,
    circuit_breaker_node,
    reflector_node,
    route_by_domain,
    route_after_guardian,
    route_after_human,
    build_carf_graph,
    compile_carf_graph,
    get_carf_graph,
)
from src.core.state import (
    CynefinDomain,
    ConfidenceLevel,
    EpistemicState,
    GuardianVerdict,
    HumanInteractionStatus,
)


class TestDeterministicRunnerNode:
    """Tests for deterministic_runner_node."""

    @pytest.mark.asyncio
    async def test_processes_clear_domain(self):
        """Test deterministic runner processes Clear domain queries."""
        state = EpistemicState(
            user_input="What is the status of order 12345?",
            cynefin_domain=CynefinDomain.CLEAR,
        )

        result = await deterministic_runner_node(state)

        assert "[Clear Domain]" in result.final_response
        assert result.proposed_action is not None
        assert result.proposed_action["action_type"] == "lookup"
        assert len(result.reasoning_chain) == 1
        assert result.reasoning_chain[0].node_name == "deterministic_runner"

    @pytest.mark.asyncio
    async def test_adds_reasoning_step(self):
        """Test that deterministic runner adds reasoning step."""
        state = EpistemicState(user_input="Simple lookup query")

        result = await deterministic_runner_node(state)

        assert len(result.reasoning_chain) == 1
        step = result.reasoning_chain[0]
        assert step.node_name == "deterministic_runner"
        assert step.confidence == ConfidenceLevel.HIGH


class TestCircuitBreakerNode:
    """Tests for circuit_breaker_node."""

    @pytest.mark.asyncio
    async def test_activates_emergency_protocol(self):
        """Test circuit breaker activates emergency protocol."""
        state = EpistemicState(
            user_input="EMERGENCY: System critical failure!",
            cynefin_domain=CynefinDomain.CHAOTIC,
            domain_entropy=0.95,
        )

        result = await circuit_breaker_node(state)

        assert "[CHAOTIC Domain]" in result.final_response
        assert "Emergency protocol" in result.final_response
        assert result.proposed_action["action_type"] == "emergency_stop"

    @pytest.mark.asyncio
    async def test_adds_high_confidence_reasoning(self):
        """Test circuit breaker adds reasoning with high confidence."""
        state = EpistemicState(
            user_input="Crisis situation",
            domain_entropy=0.9,
        )

        result = await circuit_breaker_node(state)

        assert len(result.reasoning_chain) == 1
        step = result.reasoning_chain[0]
        assert step.node_name == "circuit_breaker"
        assert "EMERGENCY" in step.action
        assert step.confidence == ConfidenceLevel.HIGH


class TestReflectorNode:
    """Tests for reflector_node."""

    @pytest.mark.asyncio
    async def test_increments_reflection_count(self):
        """Test reflector increments reflection count."""
        state = EpistemicState(
            user_input="Test query",
            reflection_count=0,
        )

        result = await reflector_node(state)

        assert result.reflection_count == 1

    @pytest.mark.asyncio
    async def test_repairs_proposed_action(self):
        """Test reflector repairs or clears proposed action for retry."""
        state = EpistemicState(
            user_input="Test query",
            proposed_action={"action": "rejected_action"},
            guardian_verdict=GuardianVerdict.REJECTED,
            policy_violations=["test_violation"],
        )

        result = await reflector_node(state)

        # Smart reflector either repairs the action or clears it
        # Guardian verdict is always reset for re-evaluation
        assert result.guardian_verdict is None

    @pytest.mark.asyncio
    async def test_adds_reasoning_step(self):
        """Test reflector adds reasoning step."""
        state = EpistemicState(
            user_input="Test query",
            reflection_count=1,
        )

        result = await reflector_node(state)

        assert len(result.reasoning_chain) == 1
        step = result.reasoning_chain[0]
        assert step.node_name == "reflector"
        assert "Self-correction" in step.action


class TestRouteByDomain:
    """Tests for route_by_domain function."""

    def test_clear_routes_to_deterministic(self):
        """Test Clear domain routes to deterministic runner."""
        state = EpistemicState(
            user_input="Test",
            cynefin_domain=CynefinDomain.CLEAR,
        )
        assert route_by_domain(state) == "deterministic_runner"

    def test_complicated_routes_to_causal(self):
        """Test Complicated domain routes to causal analyst."""
        state = EpistemicState(
            user_input="Test",
            cynefin_domain=CynefinDomain.COMPLICATED,
        )
        assert route_by_domain(state) == "causal_analyst"

    def test_complex_routes_to_bayesian(self):
        """Test Complex domain routes to bayesian explorer."""
        state = EpistemicState(
            user_input="Test",
            cynefin_domain=CynefinDomain.COMPLEX,
        )
        assert route_by_domain(state) == "bayesian_explorer"

    def test_chaotic_routes_to_circuit_breaker(self):
        """Test Chaotic domain routes to circuit breaker."""
        state = EpistemicState(
            user_input="Test",
            cynefin_domain=CynefinDomain.CHAOTIC,
        )
        assert route_by_domain(state) == "circuit_breaker"

    def test_disorder_routes_to_human(self):
        """Test Disorder domain routes to human escalation."""
        state = EpistemicState(
            user_input="Test",
            cynefin_domain=CynefinDomain.DISORDER,
        )
        assert route_by_domain(state) == "human_escalation"

    def test_dict_input_with_string_domain(self):
        """Test routing with dict input and string domain."""
        state_dict = {"cynefin_domain": "Clear", "user_input": "Test"}
        assert route_by_domain(state_dict) == "deterministic_runner"

    def test_dict_input_with_enum_domain(self):
        """Test routing with dict input and enum domain."""
        state_dict = {"cynefin_domain": CynefinDomain.COMPLICATED, "user_input": "Test"}
        assert route_by_domain(state_dict) == "causal_analyst"

    def test_dict_input_default_disorder(self):
        """Test routing with dict input defaults to disorder."""
        state_dict = {"user_input": "Test"}
        assert route_by_domain(state_dict) == "human_escalation"


class TestRouteAfterGuardian:
    """Tests for route_after_guardian function."""

    def test_approved_routes_to_end(self, monkeypatch):
        """Test approved verdict routes to end."""
        monkeypatch.delenv("GOVERNANCE_ENABLED", raising=False)
        state = EpistemicState(
            user_input="Test",
            guardian_verdict=GuardianVerdict.APPROVED,
        )
        assert route_after_guardian(state) == "end"

    def test_rejected_routes_to_reflector(self):
        """Test rejected verdict routes to reflector if under limit."""
        state = EpistemicState(
            user_input="Test",
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=1,
            max_reflections=3,
        )
        assert route_after_guardian(state) == "reflector"

    def test_rejected_at_max_reflections_routes_to_human(self):
        """Test rejected at max reflections routes to human."""
        state = EpistemicState(
            user_input="Test",
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=3,
            max_reflections=3,
        )
        assert route_after_guardian(state) == "human_escalation"

    def test_escalation_routes_to_human(self):
        """Test requires_escalation routes to human."""
        state = EpistemicState(
            user_input="Test",
            guardian_verdict=GuardianVerdict.REQUIRES_ESCALATION,
        )
        assert route_after_guardian(state) == "human_escalation"

    def test_approved_routes_to_governance_when_enabled(self, monkeypatch):
        """Test approved verdict routes to governance when enabled."""
        monkeypatch.setenv("GOVERNANCE_ENABLED", "true")
        state = EpistemicState(
            user_input="Test",
            guardian_verdict=GuardianVerdict.APPROVED,
        )
        assert route_after_guardian(state) == "governance"

    def test_dict_input_approved(self, monkeypatch):
        """Test routing with dict input for approved verdict."""
        monkeypatch.delenv("GOVERNANCE_ENABLED", raising=False)
        state_dict = {
            "guardian_verdict": GuardianVerdict.APPROVED,
            "reflection_count": 0,
            "max_reflections": 3,
        }
        assert route_after_guardian(state_dict) == "end"

    def test_dict_input_rejected(self):
        """Test routing with dict input for rejected verdict."""
        state_dict = {
            "guardian_verdict": GuardianVerdict.REJECTED,
            "reflection_count": 0,
            "max_reflections": 3,
        }
        assert route_after_guardian(state_dict) == "reflector"


class TestRouteAfterHuman:
    """Tests for route_after_human function."""

    def test_approved_routes_to_end(self):
        """Test approved status routes to end."""
        state = EpistemicState(
            user_input="Test",
            human_interaction_status=HumanInteractionStatus.APPROVED,
        )
        assert route_after_human(state) == "end"

    def test_rejected_routes_to_end(self):
        """Test rejected status routes to end."""
        state = EpistemicState(
            user_input="Test",
            human_interaction_status=HumanInteractionStatus.REJECTED,
        )
        assert route_after_human(state) == "end"

    def test_modified_routes_to_router(self):
        """Test modified status routes to router for reprocessing."""
        state = EpistemicState(
            user_input="Test",
            human_interaction_status=HumanInteractionStatus.MODIFIED,
        )
        assert route_after_human(state) == "router"

    def test_timeout_routes_to_end(self):
        """Test timeout status routes to end."""
        state = EpistemicState(
            user_input="Test",
            human_interaction_status=HumanInteractionStatus.TIMEOUT,
        )
        assert route_after_human(state) == "end"

    def test_idle_routes_to_end(self):
        """Test idle status routes to end."""
        state = EpistemicState(
            user_input="Test",
            human_interaction_status=HumanInteractionStatus.IDLE,
        )
        assert route_after_human(state) == "end"

    def test_dict_input_approved(self):
        """Test routing with dict input for approved status."""
        state_dict = {"human_interaction_status": HumanInteractionStatus.APPROVED}
        assert route_after_human(state_dict) == "end"

    def test_dict_input_modified(self):
        """Test routing with dict input for modified status."""
        state_dict = {"human_interaction_status": HumanInteractionStatus.MODIFIED}
        assert route_after_human(state_dict) == "router"


class TestReflectorSmartRepair:
    """Tests for smart reflector integration in reflector_node."""

    @pytest.mark.asyncio
    async def test_reflector_uses_smart_repair(self):
        """Test that reflector_node uses SmartReflectorService for budget violations."""
        state = EpistemicState(
            user_input="Test smart repair",
            proposed_action={"action_type": "invest", "amount": 150000},
            policy_violations=["Budget exceeded: 150000 > 100000"],
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=0,
        )

        result = await reflector_node(state)

        # Smart reflector should have repaired the action
        assert result.proposed_action is not None
        assert result.proposed_action["amount"] < 150000
        assert result.context.get("action_was_repaired") is True
        assert result.context.get("repair_strategy") is not None

    @pytest.mark.asyncio
    async def test_reflector_records_strategy_in_context(self):
        """Repair strategy should be recorded in context for observability."""
        state = EpistemicState(
            user_input="Test observability",
            proposed_action={"action_type": "adjust", "margin": 15.0},
            policy_violations=["Threshold exceeded for margin"],
            guardian_verdict=GuardianVerdict.REJECTED,
            reflection_count=0,
        )

        result = await reflector_node(state)

        assert "repair_strategy" in result.context
        assert result.context["repair_strategy"] in ("heuristic", "llm", "hybrid")


class TestBuildCarfGraph:
    """Tests for build_carf_graph function."""

    def test_builds_valid_graph(self):
        """Test building a valid CARF graph."""
        workflow = build_carf_graph()

        # Check nodes are added
        assert "router" in workflow.nodes
        assert "deterministic_runner" in workflow.nodes
        assert "causal_analyst" in workflow.nodes
        assert "bayesian_explorer" in workflow.nodes
        assert "circuit_breaker" in workflow.nodes
        assert "guardian" in workflow.nodes
        assert "reflector" in workflow.nodes
        assert "human_escalation" in workflow.nodes


class TestCompileCarfGraph:
    """Tests for compile_carf_graph function."""

    def test_compiles_graph(self):
        """Test compiling the CARF graph."""
        compiled = compile_carf_graph()
        assert compiled is not None


class TestGetCarfGraph:
    """Tests for get_carf_graph singleton."""

    def test_returns_compiled_graph(self):
        """Test get_carf_graph returns a compiled graph."""
        # Reset singleton
        import src.workflows.graph as graph_module
        graph_module._compiled_graph = None

        graph = get_carf_graph()
        assert graph is not None

        # Reset for other tests
        graph_module._compiled_graph = None

    def test_singleton_returns_same_instance(self):
        """Test singleton returns the same instance."""
        import src.workflows.graph as graph_module
        graph_module._compiled_graph = None

        graph1 = get_carf_graph()
        graph2 = get_carf_graph()

        assert graph1 is graph2

        graph_module._compiled_graph = None
