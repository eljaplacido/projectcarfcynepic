"""CARF Library API — use CARF cognitive services in notebooks and data pipelines.

Thin wrappers over existing services for notebook-friendly use. Each function
instantiates the singleton service, calls the appropriate method, and returns
a plain dict (JSON-serializable for notebook display).

Usage:
    from src.api.library import classify_query, run_causal, check_guardian, run_pipeline

    result = await classify_query("Why did costs increase 15%?")
    print(result["domain"], result["confidence"])

    pipeline_result = await run_pipeline("Does training improve productivity?")
    print(pipeline_result["response"])
"""

from __future__ import annotations

from typing import Any


async def classify_query(
    query: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a query into a Cynefin domain.

    Args:
        query: Natural language query to classify
        context: Optional additional context

    Returns:
        Dict with domain, confidence, entropy, probabilities
    """
    from src.core.state import EpistemicState
    from src.workflows.router import cynefin_router_node

    state = EpistemicState(
        user_input=query,
        context=context or {},
    )
    result_state = await cynefin_router_node(state)
    return {
        "domain": result_state.cynefin_domain.value,
        "confidence": result_state.domain_confidence,
        "entropy": result_state.domain_entropy,
        "probabilities": result_state.domain_scores or {},
    }


async def run_causal(
    query: str,
    data: Any | None = None,
    treatment: str | None = None,
    outcome: str | None = None,
    covariates: list[str] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run causal inference analysis.

    Args:
        query: Causal question
        data: Optional pandas DataFrame or list of dicts
        treatment: Treatment variable name
        outcome: Outcome variable name
        covariates: List of covariate names
        context: Optional additional context

    Returns:
        Dict with effect estimate, p_value, refutation results
    """
    from src.core.state import EpistemicState
    from src.services.causal import run_causal_analysis

    ctx = context or {}
    if data is not None:
        # Convert DataFrame to list of dicts if needed
        if hasattr(data, "to_dict"):
            data_list = data.to_dict("records")
        else:
            data_list = list(data)

        ctx["causal_estimation"] = {
            "treatment": treatment or "treatment",
            "outcome": outcome or "outcome",
            "covariates": covariates or [],
            "data": data_list,
        }

    state = EpistemicState(user_input=query, context=ctx)
    result_state = await run_causal_analysis(state)

    evidence = result_state.causal_evidence
    if evidence:
        return {
            "effect_estimate": evidence.effect_size,
            "confidence_interval": evidence.confidence_interval,
            "p_value": evidence.p_value,
            "refutation_passed": evidence.refutation_passed,
            "interpretation": evidence.interpretation,
            "response": result_state.final_response,
        }

    return {
        "effect_estimate": None,
        "error": "No causal evidence produced",
        "response": result_state.final_response,
    }


async def run_bayesian(
    query: str,
    observations: list[float] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run Bayesian active inference analysis.

    Args:
        query: Analysis question
        observations: Optional observation data
        context: Optional additional context

    Returns:
        Dict with posterior, uncertainty, probes
    """
    from src.core.state import EpistemicState
    from src.services.bayesian import run_active_inference

    ctx = context or {}
    if observations:
        ctx["bayesian_inference"] = {"observations": observations}

    state = EpistemicState(user_input=query, context=ctx)
    result_state = await run_active_inference(state)

    evidence = result_state.bayesian_evidence
    if evidence:
        return {
            "posterior_mean": evidence.posterior_mean,
            "posterior_std": evidence.posterior_std,
            "epistemic_uncertainty": evidence.epistemic_uncertainty,
            "aleatoric_uncertainty": evidence.aleatoric_uncertainty,
            "response": result_state.final_response,
        }

    return {
        "posterior_mean": None,
        "error": "No Bayesian evidence produced",
        "response": result_state.final_response,
    }


async def check_guardian(
    proposed_action: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check a proposed action against CARF Guardian policies.

    Args:
        proposed_action: The action to validate
        context: Optional context for policy evaluation

    Returns:
        Dict with verdict, violations, policies_passed
    """
    from src.core.state import EpistemicState
    from src.workflows.guardian import guardian_node

    state = EpistemicState(
        user_input="Guardian check via library API",
        proposed_action=proposed_action,
        context=context or {},
    )

    result_state = await guardian_node(state)

    return {
        "verdict": result_state.guardian_verdict.value if result_state.guardian_verdict else "unknown",
        "violations": result_state.policy_violations or [],
        "response": result_state.final_response,
    }


async def run_pipeline(
    query: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full CARF cognitive pipeline.

    Args:
        query: Natural language query
        context: Optional context

    Returns:
        Complete result dict with domain, response, evidence, verdict
    """
    from src.workflows.graph import run_carf

    state = await run_carf(user_input=query, context=context)

    result: dict[str, Any] = {
        "domain": state.cynefin_domain.value,
        "domain_confidence": state.domain_confidence,
        "response": state.final_response,
        "session_id": str(state.session_id),
    }

    if state.guardian_verdict:
        result["guardian_verdict"] = state.guardian_verdict.value

    if state.causal_evidence:
        result["causal_effect"] = state.causal_evidence.effect_size
        result["refutation_passed"] = state.causal_evidence.refutation_passed

    if state.bayesian_evidence:
        result["posterior_mean"] = state.bayesian_evidence.posterior_mean
        result["epistemic_uncertainty"] = state.bayesian_evidence.epistemic_uncertainty

    if state.proposed_action:
        result["proposed_action"] = state.proposed_action

    result["reasoning_steps"] = len(state.reasoning_chain)

    return result


async def query_memory(
    query: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """Search the experience buffer for similar past analyses.

    Args:
        query: Query to search for
        top_k: Number of results

    Returns:
        Dict with similar matches and buffer statistics
    """
    from src.services.experience_buffer import get_experience_buffer

    buffer = get_experience_buffer()
    similar = buffer.find_similar(query, top_k=top_k)

    return {
        "matches": [
            {
                "query": entry.query,
                "domain": entry.domain,
                "confidence": entry.domain_confidence,
                "similarity": round(score, 4),
            }
            for entry, score in similar
        ],
        "buffer_size": buffer.size,
    }
