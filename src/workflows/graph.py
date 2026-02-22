"""CARF LangGraph Workflow - The Cognitive Spine.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

This module defines the complete LangGraph StateGraph that orchestrates
the 4-layer cognitive architecture:

1. Router → Classifies into Cynefin domains
2. Cognitive Mesh → Domain-specific agents
3. Guardian → Policy enforcement
4. Human Escalation → HumanLayer integration
5. Governance → Orchestration Governance (Phase 16, optional)

Flow:
    Entry → Router → [Domain Agent] → Guardian → [Approved? → Governance? → END]
                                              → [Rejected? → Reflector → Router]
                                              → [Escalate? → Human → Router]
            → [Disorder? → Human → Router]
"""

import logging
import os
import time
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
from src.services.csl_policy_service import get_csl_service
from src.services.evaluation_service import get_evaluation_service, DeepEvalScores
from src.services.human_layer import human_escalation_node
from src.services.kafka_audit import log_state_to_kafka
from src.services.policy_scaffold_service import get_scaffold_service
from src.utils.telemetry import traced
from src.workflows.guardian import guardian_node
from src.workflows.router import cynefin_router_node

logger = logging.getLogger("carf.graph")


# =============================================================================
# EVALUATION INTEGRATION
# =============================================================================


async def evaluate_node_output(
    state: EpistemicState,
    node_name: str,
    input_text: str,
    output_text: str,
    context: list[str] | None = None,
) -> DeepEvalScores | None:
    """Evaluate LLM output quality at a workflow node.

    This integrates DeepEval metrics into the workflow for:
    - Quality scoring at each decision point
    - Hallucination detection before user presentation
    - UIX compliance verification
    - Audit trail enrichment

    Args:
        state: Current epistemic state
        node_name: Name of the node being evaluated
        input_text: The input to the node
        output_text: The output to evaluate
        context: Optional context for hallucination detection

    Returns:
        DeepEvalScores if evaluation successful, None otherwise
    """
    try:
        eval_service = get_evaluation_service()
        scores = await eval_service.evaluate_response(
            input=input_text,
            output=output_text,
            context=context or []
        )

        # Store scores in state for transparency
        if not hasattr(state, 'evaluation_scores') or state.evaluation_scores is None:
            state.evaluation_scores = {}
        state.evaluation_scores[node_name] = {
            "relevancy_score": scores.relevancy_score,
            "hallucination_risk": scores.hallucination_risk,
            "reasoning_depth": scores.reasoning_depth,
            "uix_compliance": scores.uix_compliance,
            "task_completion": scores.task_completion,
            "evaluated_at": scores.evaluated_at.isoformat() if scores.evaluated_at else None,
        }

        # Log quality metrics
        logger.info(
            f"[{node_name}] Quality scores - "
            f"Relevancy: {scores.relevancy_score:.2f}, "
            f"Hallucination: {scores.hallucination_risk:.2f}, "
            f"Reasoning: {scores.reasoning_depth:.2f}, "
            f"UIX: {scores.uix_compliance:.2f}"
        )

        # Quality gate: flag for human review if hallucination risk high
        if scores.hallucination_risk > 0.3:
            logger.warning(
                f"[{node_name}] High hallucination risk ({scores.hallucination_risk:.2f}) - "
                "flagging for review"
            )
            state.context["quality_warning"] = f"High hallucination risk at {node_name}"

        return scores

    except Exception as e:
        logger.warning(f"Evaluation failed for {node_name}: {e}")
        return None


# =============================================================================
# CSL CONTEXT INJECTION
# =============================================================================


def inject_csl_context(state: EpistemicState) -> EpistemicState:
    """Inject CSL-Core context into the state before Guardian evaluation.

    Adds user role, session metadata, and domain-specific scaffold context
    so that CSL policy rules have full context for evaluation.

    This runs synchronously as it only modifies the state dict.
    """
    csl_service = get_csl_service()
    if not csl_service.is_available:
        return state

    context = state.context

    # Ensure CSL-relevant metadata is in context
    if "user_role" not in context:
        context["user_role"] = context.get("role", "junior")

    if "risk_level" not in context:
        # Derive risk level from domain and confidence
        if state.cynefin_domain == CynefinDomain.CHAOTIC:
            context["risk_level"] = "CRITICAL"
        elif state.cynefin_domain == CynefinDomain.DISORDER:
            context["risk_level"] = "HIGH"
        elif state.domain_confidence < 0.5:
            context["risk_level"] = "HIGH"
        elif state.domain_confidence < 0.7:
            context["risk_level"] = "MEDIUM"
        else:
            context["risk_level"] = "LOW"

    # Inject prediction metadata from causal/bayesian evidence
    if state.causal_evidence:
        context["prediction_source"] = "causal"
        context["prediction_effect_size"] = state.causal_evidence.effect_size
        context["refutation_passed"] = state.causal_evidence.refutation_passed
        context["is_actionable"] = True

    if state.bayesian_evidence:
        if "prediction_source" not in context:
            context["prediction_source"] = "bayesian"
        context["prediction_effect_size"] = context.get(
            "prediction_effect_size", state.bayesian_evidence.posterior_mean
        )

    # Apply domain-specific scaffold if available
    scaffold_service = get_scaffold_service()
    scenario_meta = context.get("scenario_metadata", {})
    if scenario_meta:
        scaffold = scaffold_service.get_scaffold_for_scenario(scenario_meta)
        if scaffold:
            context["_active_scaffold"] = scaffold.name
            context["_scaffold_domain"] = scaffold.domain

    state.context = context
    return state


async def csl_guardian_node(state: EpistemicState) -> EpistemicState:
    """Guardian node with CSL context injection.

    Wraps the standard Guardian node by first injecting CSL context,
    then running the Guardian evaluation (which includes CSL + OPA).
    """
    state = inject_csl_context(state)
    return await guardian_node(state)


# =============================================================================
# COGNITIVE MESH AGENTS
# =============================================================================


@traced(name="carf.node.deterministic_runner", attributes={"layer": "mesh"})
async def deterministic_runner_node(state: EpistemicState) -> EpistemicState:
    """Clear domain handler - executes deterministic operations.

    Handles simple, deterministic queries where cause-effect is obvious.
    """
    logger.info(f"Deterministic runner processing: {state.user_input[:50]}...")
    _t0 = time.perf_counter()

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
        duration_ms=int((time.perf_counter() - _t0) * 1000),
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
    5. Evaluate output quality (DeepEval)
    """
    logger.info(f"Causal analyst processing: {state.user_input[:50]}...")
    _t0 = time.perf_counter()

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
        duration_ms=int((time.perf_counter() - _t0) * 1000),
    )

    # Evaluate causal output quality
    if state.final_response:
        context = [
            f"Treatment effect: {effect_str}",
            f"Refutation status: {refutation_str}",
            f"Confidence: {state.overall_confidence}",
        ]
        await evaluate_node_output(
            state=state,
            node_name="causal_analyst",
            input_text=state.user_input,
            output_text=state.final_response,
            context=context,
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
    5. Evaluate output quality (DeepEval)
    """
    logger.info(f"Bayesian explorer processing: {state.user_input[:50]}...")
    _t0 = time.perf_counter()

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
        duration_ms=int((time.perf_counter() - _t0) * 1000),
    )

    # Evaluate Bayesian output quality
    if state.final_response:
        context = [
            f"Epistemic uncertainty: {state.epistemic_uncertainty:.0%}",
            f"Hypothesis: {state.current_hypothesis or 'N/A'}",
            f"Confidence: {state.overall_confidence}",
        ]
        await evaluate_node_output(
            state=state,
            node_name="bayesian_explorer",
            input_text=state.user_input,
            output_text=state.final_response,
            context=context,
        )

    return state


@traced(name="carf.node.circuit_breaker", attributes={"layer": "mesh"})
async def circuit_breaker_node(state: EpistemicState) -> EpistemicState:
    """Chaotic domain handler - emergency stabilization.

    This always triggers human escalation for crisis management.
    """
    logger.info(f"CIRCUIT BREAKER ACTIVATED for session {state.session_id}")
    _t0 = time.perf_counter()

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
        duration_ms=int((time.perf_counter() - _t0) * 1000),
    )

    return state


@traced(name="carf.node.reflector", attributes={"layer": "mesh"})
async def reflector_node(state: EpistemicState) -> EpistemicState:
    """Self-correction node - attempts to fix rejected actions.

    Called when Guardian rejects an action. Uses SmartReflectorService for
    hybrid heuristic + LLM repair, then feeds violation reasons back into
    context if repair fails.

    Auto-repair strategies (via SmartReflectorService):
    - budget_exceeded: Reduce proposed values by 20%
    - threshold_exceeded: Apply 10% safety margin
    - missing_approval: Flag for human review instead of full escalation
    - Unknown violations: LLM-based contextual repair (hybrid mode)
    """
    logger.info(f"Reflector attempting self-correction (attempt {state.reflection_count + 1})")
    _t0 = time.perf_counter()

    state.reflection_count += 1

    violations = state.policy_violations or []
    original_action = state.proposed_action

    # Store original action for transparency
    if original_action and not state.context.get("original_action"):
        state.context["original_action"] = original_action

    # Use SmartReflectorService for repair
    repair_attempted = False
    repair_successful = False
    repair_details: list[str] = []
    repair_strategy = "none"

    if original_action and isinstance(original_action, dict) and violations:
        try:
            from src.services.smart_reflector import get_smart_reflector
            reflector = get_smart_reflector()
            repair_result = await reflector.repair(state)

            repair_strategy = repair_result.strategy_used.value
            state.context["repair_strategy"] = repair_strategy

            if repair_result.confidence > 0 and repair_result.repaired_action != original_action:
                state.proposed_action = repair_result.repaired_action
                state.context["action_was_repaired"] = True
                state.context["repair_details"] = [repair_result.repair_explanation]
                repair_details = [repair_result.repair_explanation]
                repair_attempted = True
                repair_successful = True
                logger.info(f"Smart repair applied ({repair_strategy}): {repair_result.repair_explanation}")
            elif repair_result.violations_remaining:
                repair_attempted = repair_result.confidence > 0
                repair_details = [repair_result.repair_explanation]
        except Exception as e:
            logger.warning(f"SmartReflector failed, skipping repair: {e}")

    # Feed rejection reasons into context so the domain agent can adapt
    rejections = state.context.get("guardian_rejections", [])
    rejections.append({
        "attempt": state.reflection_count,
        "violations": violations,
        "repair_attempted": repair_attempted,
        "repair_successful": repair_successful,
        "repair_details": repair_details,
        "repair_strategy": repair_strategy,
    })
    state.context["guardian_rejections"] = rejections

    state.add_reasoning_step(
        node_name="reflector",
        action=f"Self-correction attempt {state.reflection_count}",
        input_summary=f"Violations: {violations}",
        output_summary=(
            f"Smart repair ({repair_strategy}) {'succeeded' if repair_successful else 'not attempted'}: {repair_details}"
            if repair_attempted else
            f"Feeding {len(violations)} violation(s) back to domain agent for retry"
        ),
        confidence=ConfidenceLevel.MEDIUM if repair_successful else ConfidenceLevel.LOW,
        duration_ms=int((time.perf_counter() - _t0) * 1000),
    )

    # Only clear proposed action if repair wasn't attempted or failed
    if not repair_successful:
        state.proposed_action = None
    state.guardian_verdict = None

    return state


# =============================================================================
# GOVERNANCE NODE (Phase 16 — Optional, feature-flagged)
# =============================================================================


@traced(name="carf.node.governance", attributes={"layer": "governance"})
async def governance_node(state: EpistemicState) -> EpistemicState:
    """Orchestration Governance node — MAP-PRICE-RESOLVE.

    Feature-flagged: only added to the graph when GOVERNANCE_ENABLED=true.
    Non-blocking: failures are caught and logged, never breaking the pipeline.

    1. MAP: Extract cross-domain impacts → populate state.session_triples
    2. PRICE: Compute cost breakdown → populate state.cost_breakdown
    3. RESOLVE: Detect policy conflicts → store in state.context
    """
    _t0 = time.perf_counter()

    try:
        from src.services.governance_service import get_governance_service
        gov = get_governance_service()

        # 1. MAP — Extract semantic triples
        triples = gov.map_impacts(state)
        state.session_triples = triples

        # 2. PRICE — Compute cost breakdown
        token_usage = state.context.get("_llm_token_usage", {})
        input_tokens = token_usage.get("input", 0)
        output_tokens = token_usage.get("output", 0)
        compute_ms = (time.perf_counter() - _t0) * 1000  # approx pipeline time
        state.cost_breakdown = gov.compute_cost(
            state, input_tokens, output_tokens, compute_ms
        )

        # 3. RESOLVE — Detect policy conflicts
        conflicts = gov.resolve_tensions(state)
        if conflicts:
            state.context["governance_conflicts"] = [
                {"id": str(c.conflict_id), "type": c.conflict_type.value,
                 "severity": c.severity.value, "description": c.description}
                for c in conflicts
            ]

        # Persist triples to graph (non-blocking)
        try:
            from src.services.governance_graph_service import get_governance_graph_service
            graph_service = get_governance_graph_service()
            if graph_service.is_available:
                await graph_service.save_triples_batch(triples)
        except Exception:
            pass  # Graph persistence is best-effort

        _duration = int((time.perf_counter() - _t0) * 1000)
        state.add_reasoning_step(
            node_name="governance",
            action="Orchestration Governance (MAP-PRICE-RESOLVE)",
            input_summary=f"Domains detected: {len(set(t.domain_source for t in triples))}",
            output_summary=(
                f"Triples: {len(triples)}, "
                f"Cost: ${state.cost_breakdown.total_cost:.4f}, "
                f"Conflicts: {len(conflicts)}"
            ),
            confidence=ConfidenceLevel.HIGH,
            duration_ms=_duration,
        )

        logger.info(
            f"Governance node complete: {len(triples)} triples, "
            f"${state.cost_breakdown.total_cost:.4f} cost, "
            f"{len(conflicts)} conflicts ({_duration}ms)"
        )

    except Exception as exc:
        logger.warning(f"Governance node failed (non-blocking): {exc}")
        state.add_reasoning_step(
            node_name="governance",
            action="Governance node failed (non-blocking)",
            input_summary="N/A",
            output_summary=f"Error: {str(exc)[:100]}",
            confidence=ConfidenceLevel.LOW,
            duration_ms=int((time.perf_counter() - _t0) * 1000),
        )

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


def _governance_enabled() -> bool:
    """Check if the governance subsystem is enabled."""
    return os.getenv("GOVERNANCE_ENABLED", "false").lower() == "true"


def route_after_guardian(
    state: EpistemicState | dict,
) -> Literal["end", "governance", "reflector", "human_escalation"]:
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
        # Route to governance node if enabled, otherwise END
        if _governance_enabled():
            return "governance"
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
    workflow.add_node("guardian", csl_guardian_node)
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

    # Governance node (Phase 16 — optional, feature-flagged)
    if _governance_enabled():
        workflow.add_node("governance", governance_node)

    # Guardian → End/Governance/Reflector/Human (conditional)
    guardian_routes: dict[str, str] = {
        "end": END,
        "reflector": "reflector",
        "human_escalation": "human_escalation",
    }
    if _governance_enabled():
        guardian_routes["governance"] = "governance"

    workflow.add_conditional_edges(
        "guardian",
        route_after_guardian,
        guardian_routes,
    )

    # Governance → END
    if _governance_enabled():
        workflow.add_edge("governance", END)

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

    # Reset token tracking for this run (Phase 16 — PRICE pillar)
    try:
        from src.core.llm import reset_token_usage, get_accumulated_token_usage
        reset_token_usage()
    except Exception:
        pass

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

    # Store accumulated token usage in context for governance node (Phase 16)
    try:
        from src.core.llm import get_accumulated_token_usage
        token_usage = get_accumulated_token_usage()
        if token_usage["input"] > 0 or token_usage["output"] > 0:
            final_state.context["_llm_token_usage"] = token_usage
    except Exception:
        pass

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

    # Store experience for future retrieval (non-critical)
    try:
        from src.services.experience_buffer import get_experience_buffer, ExperienceEntry
        buffer = get_experience_buffer()
        buffer.add(ExperienceEntry(
            query=user_input,
            domain=final_state.cynefin_domain.value,
            domain_confidence=final_state.domain_confidence,
            response_summary=(final_state.final_response or "")[:200],
            causal_effect=final_state.causal_evidence.effect_size if final_state.causal_evidence else None,
            guardian_verdict=final_state.guardian_verdict.value if final_state.guardian_verdict else None,
            session_id=str(final_state.session_id),
        ))
    except Exception:
        pass  # Experience buffer is non-critical

    logger.info(
        f"CARF pipeline complete. Domain: {final_state.cynefin_domain.value}, "
        f"Verdict: {final_state.guardian_verdict}"
    )

    return final_state
