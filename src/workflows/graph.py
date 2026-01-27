"""CARF LangGraph Workflow - The Cognitive Spine.

This module defines the complete LangGraph StateGraph that orchestrates
the 4-layer cognitive architecture:

1. Router → Classifies into Cynefin domains
2. Cognitive Mesh → Domain-specific agents
3. Guardian → Policy enforcement
4. Human Escalation → HumanLayer integration

Flow:
    Entry → Router → [Domain Agent] → Guardian → [Approved? → END]
                                              → [Rejected? → Reflector → Router]
                                              → [Escalate? → Human → Router]
            → [Disorder? → Human → Router]
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from src.core.state import (
    CynefinDomain,
    EpistemicState,
    GuardianVerdict,
    HumanInteractionStatus,
    ConfidenceLevel,
)
from src.services.bayesian import run_active_inference
from src.services.causal import run_causal_analysis
from src.services.human_layer import human_escalation_node
from src.services.kafka_audit import log_state_to_kafka
from src.utils.telemetry import traced
from src.workflows.guardian import guardian_node
from src.workflows.router import cynefin_router_node

logger = logging.getLogger("carf.graph")


# =============================================================================
# COGNITIVE MESH AGENTS
# =============================================================================


@traced(name="carf.node.deterministic_runner", attributes={"layer": "mesh"})
async def deterministic_runner_node(state: EpistemicState) -> EpistemicState:
    """Clear domain handler - executes deterministic operations.

    Handles simple, deterministic queries where cause-effect is obvious.
    """
    logger.info(f"Deterministic runner processing: {state.user_input[:50]}...")

    state.final_response = (
        f"[Clear Domain] Processing deterministic request: {state.user_input}"
    )
    state.proposed_action = {
        "action_type": "lookup",
        "description": "Deterministic lookup operation",
        "parameters": {"query": state.user_input},
    }

    state.add_reasoning_step(
        node_name="deterministic_runner",
        action="Executed deterministic operation",
        input_summary=state.user_input[:50],
        output_summary="Operation completed",
        confidence=ConfidenceLevel.HIGH,
    )

    return state


@traced(name="carf.node.causal_analyst", attributes={"layer": "mesh"})
async def causal_analyst_node(state: EpistemicState) -> EpistemicState:
    """Complicated domain handler - performs causal analysis.

    Uses the Causal Inference Engine to:
    1. Discover causal structure (DAG)
    2. Estimate causal effects
    3. Run refutation tests
    4. Generate interpretable conclusions
    """
    logger.info(f"Causal analyst processing: {state.user_input[:50]}...")

    # Run full causal analysis pipeline
    state = await run_causal_analysis(state)

    # Record reasoning step
    effect_str = f"{state.causal_evidence.effect_size:.2f}" if state.causal_evidence else "N/A"
    refutation_str = "PASSED" if state.causal_evidence and state.causal_evidence.refutation_passed else "FAILED"
    state.add_reasoning_step(
        node_name="causal_analyst",
        action="Completed causal analysis",
        input_summary=state.user_input[:50],
        output_summary=f"Effect: {effect_str}, Refutation: {refutation_str}",
        confidence=state.overall_confidence,
    )

    return state


@traced(name="carf.node.bayesian_explorer", attributes={"layer": "mesh"})
async def bayesian_explorer_node(state: EpistemicState) -> EpistemicState:
    """Complex domain handler - navigates uncertainty via Active Inference.

    Uses the Bayesian Active Inference Engine to:
    1. Establish prior beliefs about the situation
    2. Design safe-to-fail probes to reduce uncertainty
    3. Update beliefs based on analysis
    4. Recommend next steps for exploration
    """
    logger.info(f"Bayesian explorer processing: {state.user_input[:50]}...")

    # Run Active Inference pipeline
    state = await run_active_inference(state)

    # Record reasoning step
    state.add_reasoning_step(
        node_name="bayesian_explorer",
        action="Completed Bayesian exploration",
        input_summary=state.user_input[:50],
        output_summary=(
            f"Uncertainty: {state.epistemic_uncertainty:.0%}, "
            f"Hypothesis: {state.current_hypothesis[:50] if state.current_hypothesis else 'N/A'}..."
        ),
        confidence=state.overall_confidence,
    )

    return state


@traced(name="carf.node.circuit_breaker", attributes={"layer": "mesh"})
async def circuit_breaker_node(state: EpistemicState) -> EpistemicState:
    """Chaotic domain handler - emergency stabilization.

    This always triggers human escalation for crisis management.
    """
    logger.info(f"CIRCUIT BREAKER ACTIVATED for session {state.session_id}")

    state.final_response = (
        "[CHAOTIC Domain] Emergency protocol activated. "
        "System stabilization required. Human intervention mandatory."
    )
    state.proposed_action = {
        "action_type": "emergency_stop",
        "description": "Circuit breaker - halt all operations",
        "parameters": {"reason": "Chaotic domain detected"},
    }

    state.add_reasoning_step(
        node_name="circuit_breaker",
        action="EMERGENCY: Circuit breaker activated",
        input_summary=f"High entropy: {state.domain_entropy:.2f}",
        output_summary="All operations halted, human escalation required",
        confidence=ConfidenceLevel.HIGH,
    )

    return state


@traced(name="carf.node.reflector", attributes={"layer": "mesh"})
async def reflector_node(state: EpistemicState) -> EpistemicState:
    """Self-correction node - attempts to fix rejected actions.

    Called when Guardian rejects an action. Feeds the violation reasons back
    into the context so the domain agent can adapt its approach.
    """
    logger.info(f"Reflector attempting self-correction (attempt {state.reflection_count + 1})")

    state.reflection_count += 1

    violations = state.policy_violations or []

    # Feed rejection reasons into context so the domain agent can adapt
    rejections = state.context.get("guardian_rejections", [])
    rejections.append({
        "attempt": state.reflection_count,
        "violations": violations,
    })
    state.context["guardian_rejections"] = rejections

    state.add_reasoning_step(
        node_name="reflector",
        action=f"Self-correction attempt {state.reflection_count}",
        input_summary=f"Violations: {violations}",
        output_summary=f"Feeding {len(violations)} violation(s) back to domain agent for retry",
        confidence=ConfidenceLevel.MEDIUM,
    )

    # Clear the proposed action for re-routing
    state.proposed_action = None
    state.guardian_verdict = None

    return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================


def route_by_domain(state: EpistemicState | dict) -> str:
    """Route to appropriate agent based on Cynefin domain."""
    # Handle both dict and EpistemicState
    if isinstance(state, dict):
        domain = state.get("cynefin_domain", CynefinDomain.DISORDER)
        if isinstance(domain, str):
            domain = CynefinDomain(domain)
    else:
        domain = state.cynefin_domain

    if domain == CynefinDomain.CLEAR:
        return "deterministic_runner"
    elif domain == CynefinDomain.COMPLICATED:
        return "causal_analyst"
    elif domain == CynefinDomain.COMPLEX:
        return "bayesian_explorer"
    elif domain == CynefinDomain.CHAOTIC:
        return "circuit_breaker"
    else:  # DISORDER
        return "human_escalation"


def route_after_guardian(
    state: EpistemicState | dict,
) -> Literal["end", "reflector", "human_escalation"]:
    """Route based on Guardian verdict."""
    # Handle both dict and EpistemicState
    if isinstance(state, dict):
        verdict = state.get("guardian_verdict")
        if isinstance(verdict, str):
            verdict = GuardianVerdict(verdict)
        reflection_count = state.get("reflection_count", 0)
        max_reflections = state.get("max_reflections", 2)
    else:
        verdict = state.guardian_verdict
        reflection_count = state.reflection_count
        max_reflections = state.max_reflections

    if verdict == GuardianVerdict.APPROVED:
        return "end"
    elif verdict == GuardianVerdict.REJECTED:
        # Check if we've exceeded reflection limit
        if reflection_count >= max_reflections:
            return "human_escalation"
        return "reflector"
    else:  # REQUIRES_ESCALATION
        return "human_escalation"


def route_after_human(state: EpistemicState | dict) -> Literal["router", "end"]:
    """Route based on human response."""
    # Handle both dict and EpistemicState
    if isinstance(state, dict):
        status = state.get("human_interaction_status", HumanInteractionStatus.IDLE)
        if isinstance(status, str):
            status = HumanInteractionStatus(status)
    else:
        status = state.human_interaction_status

    if status == HumanInteractionStatus.APPROVED:
        return "end"
    elif status == HumanInteractionStatus.REJECTED:
        return "end"  # User rejected - end workflow
    elif status == HumanInteractionStatus.MODIFIED:
        return "router"  # Re-process with human guidance
    else:  # TIMEOUT or other
        return "end"


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def build_carf_graph() -> StateGraph:
    """Build the complete CARF workflow graph.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Initialize graph with EpistemicState as the state schema
    workflow = StateGraph(EpistemicState)

    # --- Add Nodes ---
    workflow.add_node("router", cynefin_router_node)
    workflow.add_node("deterministic_runner", deterministic_runner_node)
    workflow.add_node("causal_analyst", causal_analyst_node)
    workflow.add_node("bayesian_explorer", bayesian_explorer_node)
    workflow.add_node("circuit_breaker", circuit_breaker_node)
    workflow.add_node("guardian", guardian_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("human_escalation", human_escalation_node)

    # --- Set Entry Point ---
    workflow.set_entry_point("router")

    # --- Add Edges ---

    # Router → Domain Agents (conditional)
    workflow.add_conditional_edges(
        "router",
        route_by_domain,
        {
            "deterministic_runner": "deterministic_runner",
            "causal_analyst": "causal_analyst",
            "bayesian_explorer": "bayesian_explorer",
            "circuit_breaker": "circuit_breaker",
            "human_escalation": "human_escalation",
        },
    )

    # Domain Agents → Guardian
    workflow.add_edge("deterministic_runner", "guardian")
    workflow.add_edge("causal_analyst", "guardian")
    workflow.add_edge("bayesian_explorer", "guardian")
    workflow.add_edge("circuit_breaker", "human_escalation")  # Chaotic always escalates

    # Guardian → End/Reflector/Human (conditional)
    workflow.add_conditional_edges(
        "guardian",
        route_after_guardian,
        {
            "end": END,
            "reflector": "reflector",
            "human_escalation": "human_escalation",
        },
    )

    # Reflector → Router (for retry)
    workflow.add_edge("reflector", "router")

    # Human Escalation → Router/End (conditional)
    workflow.add_conditional_edges(
        "human_escalation",
        route_after_human,
        {
            "router": "router",
            "end": END,
        },
    )

    return workflow


def compile_carf_graph():
    """Build and compile the CARF graph for execution.

    Returns:
        Compiled graph ready for invocation
    """
    workflow = build_carf_graph()
    return workflow.compile()


# Create compiled graph singleton
_compiled_graph = None


def get_carf_graph():
    """Get the compiled CARF graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_carf_graph()
    return _compiled_graph


@traced(name="carf.pipeline.run_carf")
async def run_carf(
    user_input: str,
    context: dict | None = None,
) -> EpistemicState:
    """Run the CARF cognitive pipeline on an input.

    This is the main entry point for processing queries through CARF.

    Args:
        user_input: The user's query or request
        context: Optional additional context

    Returns:
        Final EpistemicState with results

    Usage:
        result = await run_carf("Why did our costs increase 15%?")
        print(result.final_response)
        print(result.cynefin_domain)
    """
    graph = get_carf_graph()

    # Initialize state as dict for LangGraph compatibility
    initial_state = EpistemicState(
        user_input=user_input,
        context=context or {},
    )

    # Run the graph
    logger.info(f"Starting CARF pipeline for: {user_input[:50]}...")
    result = await graph.ainvoke(initial_state)

    # LangGraph returns dict - convert back to EpistemicState
    if isinstance(result, dict):
        final_state = EpistemicState(**result)
    else:
        final_state = result

    # Record domain and verdict as span attributes for observability
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("cynefin_domain", final_state.cynefin_domain.value)
            if final_state.guardian_verdict:
                span.set_attribute("guardian_verdict", final_state.guardian_verdict.value)
    except Exception:
        pass  # OTel not available — non-critical

    try:
        await log_state_to_kafka(final_state)
    except Exception as exc:
        logger.warning(f"Kafka audit logging failed: {exc}")

    logger.info(
        f"CARF pipeline complete. Domain: {final_state.cynefin_domain.value}, "
        f"Verdict: {final_state.guardian_verdict}"
    )

    return final_state
