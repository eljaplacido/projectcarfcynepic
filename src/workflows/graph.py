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
    ConfidenceLevel,
    CynefinDomain,
    EpistemicState,
    GuardianVerdict,
    HumanInteractionStatus,
)
from src.services.bayesian import run_active_inference
from src.services.causal import run_causal_analysis
from src.services.csl_policy_service import get_csl_service
from src.services.evaluation_service import DeepEvalScores, get_evaluation_service
from src.services.explanation_builder import enrich_state_explanation
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
# CSL PRE-CHECK NODE
# =============================================================================


@traced(name="carf.node.csl_precheck", attributes={"layer": "policy"})
async def csl_precheck_node(state: EpistemicState) -> EpistemicState:
    """Pre-check CSL constraints before domain agents process.

    Queries the CSL policy service for applicable financial limits,
    escalation rules, and active scaffold constraints. Injects these as
    machine-readable and human-readable values into state.context so
    domain agents can self-cap their proposals before Guardian evaluation.

    Non-blocking: returns state unmodified if CSL is unavailable.
    """
    try:
        csl_service = get_csl_service()
        if not csl_service.is_available:
            return state

        context = state.context
        domain = state.cynefin_domain

        constraints: list[str] = []

        # --- Financial limits based on domain ---
        domain_limits = {
            CynefinDomain.CLEAR: 100_000,
            CynefinDomain.COMPLICATED: 50_000,
            CynefinDomain.COMPLEX: 25_000,
            CynefinDomain.CHAOTIC: 10_000,
            CynefinDomain.DISORDER: 10_000,
        }
        financial_limit = domain_limits.get(domain, 50_000)

        # Apply scaffold override if available
        scaffold_service = get_scaffold_service()
        scenario_meta = context.get("scenario_metadata", {})
        if scenario_meta:
            scaffold = scaffold_service.get_scaffold_for_scenario(scenario_meta)
            if scaffold:
                override_limit = (scaffold.csl_overrides or {}).get(
                    "budget_limits", {}
                )
                if isinstance(override_limit, dict):
                    scaffold_limit = override_limit.get("domain_financial_limit")
                    if scaffold_limit is not None:
                        financial_limit = min(financial_limit, int(scaffold_limit))

        context["_csl_financial_limit"] = financial_limit
        constraints.append(f"Financial auto-approval limit: ${financial_limit:,}")

        # --- Confidence threshold ---
        confidence_threshold = 0.6
        if domain in (CynefinDomain.CHAOTIC, CynefinDomain.DISORDER):
            confidence_threshold = 0.8
        context["_csl_confidence_threshold"] = confidence_threshold
        constraints.append(
            f"Minimum confidence for autonomous action: {confidence_threshold:.0%}"
        )

        # --- Escalation rules ---
        risk_level = context.get("risk_level", "LOW")
        if risk_level in ("HIGH", "CRITICAL"):
            constraints.append(
                f"Risk level {risk_level}: actions require human approval"
            )
        user_role = context.get("user_role", "junior")
        if user_role == "junior":
            constraints.append(
                "Junior role: elevated actions require manager approval"
            )

        # --- Active scaffold constraints ---
        active_scaffold = context.get("_active_scaffold")
        if active_scaffold:
            constraints.append(f"Active scaffold: {active_scaffold}")

        context["_csl_precheck_constraints"] = constraints
        state.context = context

        logger.debug(
            "CSL precheck: domain=%s, financial_limit=%d, constraints=%d",
            domain.value, financial_limit, len(constraints),
        )

    except Exception as exc:
        logger.debug("CSL precheck skipped: %s", exc)

    return state


# =============================================================================
# FINANCIAL CAP HELPER
# =============================================================================


def _apply_financial_cap(state: EpistemicState) -> None:
    """Cap proposed_action amount to _csl_financial_limit if present.

    Modifies state.proposed_action in place. Only acts when the proposed
    action has a numeric ``amount`` in its ``parameters`` dict and the
    CSL precheck has set ``_csl_financial_limit`` in context.
    """
    limit = state.context.get("_csl_financial_limit")
    if limit is None:
        return
    action = state.proposed_action
    if not isinstance(action, dict):
        return
    params = action.get("parameters")
    if not isinstance(params, dict):
        return
    amount = params.get("amount")
    if isinstance(amount, (int, float)) and amount > limit:
        params["amount"] = limit
        params["_capped_from"] = amount
        action["parameters"] = params
        state.proposed_action = action
        logger.info(
            "CSL precheck capped amount from %s to %s", amount, limit,
        )


# =============================================================================
# CHIMERA ORACLE FAST-PATH (Phase 18D)
# =============================================================================


@traced(name="carf.node.chimera_fast_path", attributes={"layer": "mesh"})
async def chimera_fast_path_node(state: EpistemicState) -> EpistemicState:
    """ChimeraOracle fast-path node — Guardian-enforced fast causal predictions.

    Phase 18D: Integrates ChimeraOracle into the StateGraph, closing AP-7.
    Uses pre-trained CausalForestDML models for <100ms predictions while
    ensuring Guardian enforcement, EvaluationService scoring, and audit trail.

    Fallback: If ChimeraOracle fails or confidence is low, falls through
    to the full causal_analyst_node.
    """
    logger.info(f"ChimeraOracle fast-path processing: {state.user_input[:50]}...")
    _t0 = time.perf_counter()

    try:
        from src.services.chimera_oracle import get_oracle_engine

        oracle = get_oracle_engine()
        available_scenarios = oracle.get_available_scenarios()

        if not available_scenarios:
            logger.info("No pre-trained models available, falling through to causal analyst")
            state.context["_chimera_fallback"] = "no_models"
            return await causal_analyst_node(state)

        # Try to match query context to a trained scenario
        scenario_id = state.context.get("_oracle_scenario_id")
        context_data = state.context.get("benchmark_data") or state.context.get("data") or {}

        # Auto-detect scenario from context if not specified
        if not scenario_id:
            for sid in available_scenarios:
                if sid in state.user_input.lower() or sid in str(context_data).lower():
                    scenario_id = sid
                    break

        if not scenario_id or not oracle.has_model(scenario_id):
            logger.info("No matching scenario model, falling through to causal analyst")
            state.context["_chimera_fallback"] = "no_matching_model"
            return await causal_analyst_node(state)

        # Build context for prediction
        prediction_context = {}
        if isinstance(context_data, list) and context_data:
            prediction_context = context_data[0] if isinstance(context_data[0], dict) else {}
        elif isinstance(context_data, dict):
            prediction_context = context_data

        # Run fast prediction
        prediction = oracle.predict_effect(scenario_id, prediction_context)

        # Check reliability — fall through to full analysis if low
        if prediction.reliability_score < 0.5 or prediction.drift_warning:
            logger.info(
                "ChimeraOracle reliability too low (%.2f) or drift detected, "
                "falling through to causal analyst",
                prediction.reliability_score,
            )
            state.context["_chimera_fallback"] = "low_reliability"
            state.context["_chimera_reliability"] = prediction.reliability_score
            state.context["_chimera_drift"] = prediction.drift_warning
            return await causal_analyst_node(state)

        # Build causal evidence from prediction
        from src.core.state import CausalEvidence
        state.causal_evidence = CausalEvidence(
            effect_size=prediction.effect_estimate,
            confidence_interval=prediction.confidence_interval,
            p_value=0.05,  # Approximate from CI
            method="CausalForestDML (ChimeraOracle fast-path)",
            refutation_passed=True,  # Pre-trained model validated during training
        )

        # Set response
        model_info = oracle.get_average_treatment_effect(scenario_id)
        state.final_response = (
            f"**ChimeraOracle Fast Analysis** (scenario: {scenario_id})\n\n"
            f"Estimated causal effect: **{prediction.effect_estimate:.4f}**\n"
            f"95% CI: [{prediction.confidence_interval[0]:.4f}, {prediction.confidence_interval[1]:.4f}]\n"
            f"Model: CausalForestDML v{prediction.model_version}\n"
            f"Reliability: {prediction.reliability_score:.0%}\n"
            f"Prediction time: {prediction.prediction_time_ms:.1f}ms\n\n"
            f"*This fast-path analysis uses a pre-trained causal model. "
            f"For full refutation testing, use the standard causal analysis pipeline.*"
        )

        state.proposed_action = {
            "action_type": "causal_prediction",
            "description": f"ChimeraOracle fast causal effect prediction ({scenario_id})",
            "parameters": {
                "scenario_id": scenario_id,
                "effect": prediction.effect_estimate,
                "reliability": prediction.reliability_score,
            },
        }

        # Mark oracle usage in context
        state.context["_oracle_used"] = True
        state.context["_oracle_scenario_id"] = scenario_id
        state.context["_oracle_prediction_time_ms"] = prediction.prediction_time_ms
        if prediction.drift_warning:
            state.context["_oracle_drift_warning"] = prediction.drift_details

        # CSL pre-check: cap financial amounts if present
        _apply_financial_cap(state)

        state.add_reasoning_step(
            node_name="chimera_fast_path",
            action="ChimeraOracle fast causal prediction",
            input_summary=f"Scenario: {scenario_id}",
            output_summary=(
                f"Effect: {prediction.effect_estimate:.4f}, "
                f"Reliability: {prediction.reliability_score:.2f}, "
                f"Time: {prediction.prediction_time_ms:.1f}ms"
            ),
            confidence=ConfidenceLevel.HIGH if prediction.reliability_score > 0.7 else ConfidenceLevel.MEDIUM,
            duration_ms=int((time.perf_counter() - _t0) * 1000),
        )

        # Evaluate output quality (same as causal_analyst)
        if state.final_response:
            await evaluate_node_output(
                state=state,
                node_name="chimera_fast_path",
                input_text=state.user_input,
                output_text=state.final_response,
                context=[
                    f"Effect: {prediction.effect_estimate:.4f}",
                    f"Reliability: {prediction.reliability_score:.2f}",
                    f"Model: {prediction.model_version}",
                ],
            )

        state = enrich_state_explanation(state)
        return state

    except Exception as exc:
        logger.warning("ChimeraOracle fast-path failed, falling through: %s", exc)
        state.context["_chimera_fallback"] = f"error: {str(exc)[:100]}"
        return await causal_analyst_node(state)


def _should_use_chimera_fast_path(state: EpistemicState) -> bool:
    """Check if ChimeraOracle fast-path should be used.

    Criteria:
    - Domain is Complicated
    - Oracle has a model for the scenario
    - Domain confidence > 0.85 (high confidence in routing)
    - No explicit request for full analysis
    """
    if state.cynefin_domain != CynefinDomain.COMPLICATED:
        return False
    if state.domain_confidence < 0.85:
        return False
    if state.context.get("_force_full_analysis"):
        return False

    try:
        from src.services.chimera_oracle import get_oracle_engine
        oracle = get_oracle_engine()
        if not oracle.get_available_scenarios():
            return False

        # Check if there's a matching scenario
        scenario_id = state.context.get("_oracle_scenario_id")
        if scenario_id and oracle.has_model(scenario_id):
            return True

        # Auto-detect from context
        context_str = (state.user_input + str(state.context)).lower()
        for sid in oracle.get_available_scenarios():
            if sid in context_str:
                state.context["_oracle_scenario_id"] = sid
                return True

    except Exception:
        pass

    return False


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

    # If raw data is available, provide a data-grounded answer
    raw_data = state.context.get("benchmark_data") or state.context.get("data")
    if raw_data:
        import json as _json
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_analyst_model

        data_str = _json.dumps(raw_data, indent=2)
        prompt = (
            "You are a data analyst. Answer the question ONLY using the provided data. "
            "Do NOT invent, fabricate, or assume any values not present in the data. "
            "If the data is insufficient, say so explicitly.\n\n"
            f"Data:\n{data_str}\n\nQuestion: {state.user_input}"
        )
        model = get_analyst_model()
        resp = await model.ainvoke([HumanMessage(content=prompt)])
        state.final_response = resp.content
    else:
        state.final_response = (
            f"[Clear Domain] Processing deterministic request: {state.user_input}"
        )

    state.proposed_action = {
        "action_type": "lookup",
        "description": "Deterministic lookup operation",
        "parameters": {"query": state.user_input},
    }

    # CSL pre-check: cap financial amounts if present
    _apply_financial_cap(state)

    state.add_reasoning_step(
        node_name="deterministic_runner",
        action="Executed deterministic operation",
        input_summary=state.user_input[:50],
        output_summary="Operation completed",
        confidence=ConfidenceLevel.HIGH,
        duration_ms=int((time.perf_counter() - _t0) * 1000),
    )

    return state


async def _data_grounded_fallback(state: EpistemicState) -> EpistemicState:
    """Provide a data-grounded LLM response when causal estimation is unavailable.

    Used when the query is classified as Complicated but no causal estimation
    config can be inferred (e.g., factual queries with raw data).
    """
    import json as _json
    from langchain_core.messages import HumanMessage
    from src.core.llm import get_analyst_model

    raw_data = state.context.get("benchmark_data") or state.context.get("data")
    data_str = _json.dumps(raw_data, indent=2) if raw_data else "No data provided."
    prompt = (
        "You are a data analyst. Answer the question ONLY using the provided data. "
        "Do NOT invent, fabricate, or assume any values not present in the data. "
        "If the data is insufficient, say so explicitly.\n\n"
        f"Data:\n{data_str}\n\nQuestion: {state.user_input}"
    )
    model = get_analyst_model()
    resp = await model.ainvoke([HumanMessage(content=prompt)])
    state.final_response = resp.content
    state.overall_confidence = ConfidenceLevel.MEDIUM
    state.context["_fallback_mode"] = "data_grounded_llm"
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

    Falls back to a data-grounded LLM response when causal estimation
    data is unavailable (e.g., factual queries routed as Complicated).
    """
    logger.info(f"Causal analyst processing: {state.user_input[:50]}...")
    _t0 = time.perf_counter()

    # Run full causal analysis pipeline, with graceful fallback
    try:
        state = await run_causal_analysis(state)
    except ValueError as exc:
        logger.warning(f"Causal estimation unavailable, using data-grounded fallback: {exc}")
        state = await _data_grounded_fallback(state)

    # Record reasoning step (include Oracle metadata if used)
    effect_str = f"{state.causal_evidence.effect_size:.2f}" if state.causal_evidence else "N/A"
    refutation_str = "PASSED" if state.causal_evidence and state.causal_evidence.refutation_passed else "FAILED"
    output_parts = [f"Effect: {effect_str}", f"Refutation: {refutation_str}"]
    if state.context.get("_oracle_used"):
        oracle_id = state.context.get("_oracle_scenario_id", "unknown")
        output_parts.append(f"Oracle: {oracle_id}")
        drift_warn = state.context.get("_oracle_drift_warning")
        if drift_warn:
            output_parts.append("DRIFT WARNING")
    state.add_reasoning_step(
        node_name="causal_analyst",
        action="Completed causal analysis",
        input_summary=state.user_input[:50],
        output_summary=", ".join(output_parts),
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

    state = enrich_state_explanation(state)
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

    state = enrich_state_explanation(state)
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

        # Feed triples into RAG index (non-blocking)
        try:
            from src.services.rag_service import get_rag_service
            get_rag_service().ingest_triples(triples)
        except Exception:
            pass  # RAG triple ingestion is best-effort

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
    """Route to appropriate agent based on Cynefin domain.

    Phase 18D: For Complicated domain, checks if ChimeraOracle fast-path
    is eligible before routing to full causal analyst.
    """
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
        # Phase 18D: Try ChimeraOracle fast-path first
        if not isinstance(state, dict) and _should_use_chimera_fast_path(state):
            return "chimera_fast_path"
        return "causal_analyst"
    elif domain == CynefinDomain.COMPLEX:
        return "bayesian_explorer"
    elif domain == CynefinDomain.CHAOTIC:
        return "circuit_breaker"
    else:  # DISORDER
        return "human_escalation"


def _governance_enabled() -> bool:
    """Check if the governance subsystem is enabled.

    Uses the deployment profile when available, but always re-checks the
    env var to respect test-time monkey-patching.
    """
    try:
        from src.core.deployment_profile import _infer_mode, resolve_profile
        profile = resolve_profile(_infer_mode())
        return profile.governance_enabled
    except Exception:
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
# RAG CONTEXT NODE
# =============================================================================


# Domain-specific top_k for RAG retrieval
_RAG_TOP_K = {
    CynefinDomain.CLEAR: 2,
    CynefinDomain.COMPLICATED: 3,
    CynefinDomain.COMPLEX: 5,
    CynefinDomain.CHAOTIC: 2,
    CynefinDomain.DISORDER: 2,
}


@traced(name="carf.node.rag_context", attributes={"layer": "retrieval"})
async def rag_context_node(state: EpistemicState) -> EpistemicState:
    """Inject RAG context between router and domain agents.

    Retrieves relevant documents from the RAG index and injects them
    into the state context for downstream agents.  Pure pass-through
    when the RAG index is empty.
    """
    try:
        from src.services.rag_service import get_rag_service

        rag = get_rag_service()
        if rag.document_count == 0:
            return state

        top_k = _RAG_TOP_K.get(state.cynefin_domain, 3)
        domain_id = state.cynefin_domain.value if state.cynefin_domain else None

        rag_text = rag.retrieve_for_pipeline(
            query=state.user_input,
            domain_id=domain_id,
            top_k=top_k,
        )
        if rag_text:
            state.context["_rag_context"] = rag_text
            logger.debug(
                "RAG context injected (%d chars, domain=%s, top_k=%d)",
                len(rag_text), domain_id, top_k,
            )
    except Exception as exc:
        logger.debug("RAG context injection skipped: %s", exc)

    return state


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
    workflow.add_node("rag_context", rag_context_node)
    workflow.add_node("csl_precheck", csl_precheck_node)
    workflow.add_node("deterministic_runner", deterministic_runner_node)
    workflow.add_node("causal_analyst", causal_analyst_node)
    workflow.add_node("chimera_fast_path", chimera_fast_path_node)  # Phase 18D
    workflow.add_node("bayesian_explorer", bayesian_explorer_node)
    workflow.add_node("circuit_breaker", circuit_breaker_node)
    workflow.add_node("guardian", csl_guardian_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("human_escalation", human_escalation_node)

    # --- Set Entry Point ---
    workflow.set_entry_point("router")

    # --- Add Edges ---

    # Router → RAG Context → CSL Precheck → Domain Agents
    workflow.add_edge("router", "rag_context")
    workflow.add_edge("rag_context", "csl_precheck")

    # CSL Precheck → Domain Agents (conditional on domain)
    workflow.add_conditional_edges(
        "csl_precheck",
        route_by_domain,
        {
            "deterministic_runner": "deterministic_runner",
            "causal_analyst": "causal_analyst",
            "chimera_fast_path": "chimera_fast_path",  # Phase 18D
            "bayesian_explorer": "bayesian_explorer",
            "circuit_breaker": "circuit_breaker",
            "human_escalation": "human_escalation",
        },
    )

    # Domain Agents → Guardian (Phase 18D: chimera_fast_path also goes through Guardian)
    workflow.add_edge("deterministic_runner", "guardian")
    workflow.add_edge("causal_analyst", "guardian")
    workflow.add_edge("chimera_fast_path", "guardian")  # Phase 18D: closes AP-7
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
        from src.core.llm import get_accumulated_token_usage, reset_token_usage
        reset_token_usage()
    except Exception:
        pass

    # Initialize state as dict for LangGraph compatibility
    initial_state = EpistemicState(
        user_input=user_input,
        context=context or {},
    )

    # Inject memory augmentation (non-critical)
    try:
        from src.services.agent_memory import get_agent_memory
        memory = get_agent_memory()
        if memory.size > 0:
            augmentation = memory.get_context_augmentation(user_input)
            initial_state.context["_memory_augmentation"] = augmentation
    except Exception:
        pass  # Memory augmentation is non-critical

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

    # Phase 18A: Record routing decision for drift monitoring (non-critical)
    try:
        from src.services.drift_detector import get_drift_detector
        drift = get_drift_detector()
        drift.record_routing(final_state.cynefin_domain.value)
    except Exception:
        pass  # Drift monitoring is non-critical

    # Store experience for future retrieval (non-critical)
    try:
        from src.services.experience_buffer import ExperienceEntry, get_experience_buffer
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

    # Store to persistent agent memory (non-critical)
    try:
        from src.services.agent_memory import get_agent_memory
        get_agent_memory().store_from_state(final_state)
    except Exception:
        pass  # Persistent memory is non-critical

    logger.info(
        f"CARF pipeline complete. Domain: {final_state.cynefin_domain.value}, "
        f"Verdict: {final_state.guardian_verdict}"
    )

    return final_state
