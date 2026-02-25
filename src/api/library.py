# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
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

from datetime import UTC
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


def get_system_capabilities() -> dict[str, Any]:
    """Return a summary of the CARF system's available capabilities.

    Useful for notebooks and integrations to discover what
    analysis modes, services, and benchmarks are available.

    Returns:
        Dict describing available domains, services, and benchmarks.
    """
    capabilities: dict[str, Any] = {
        "cynefin_domains": [
            {"domain": "Clear", "agent": "deterministic_runner", "description": "Deterministic lookup operations"},
            {"domain": "Complicated", "agent": "causal_analyst", "description": "Causal inference analysis"},
            {"domain": "Complex", "agent": "bayesian_explorer", "description": "Bayesian active inference"},
            {"domain": "Chaotic", "agent": "circuit_breaker", "description": "Emergency stabilization"},
            {"domain": "Disorder", "agent": "human_escalation", "description": "Human-in-the-loop"},
        ],
        "services": {
            "causal_inference": True,
            "bayesian_inference": True,
            "guardian_policy_engine": True,
            "csl_policies": True,
            "opa_policies": True,
            "explanation_builder": True,
            "embedding_engine": True,
            "rag_retrieval": True,
            "agent_memory": True,
            "governance_map_price_resolve": True,
        },
        "library_functions": [
            "classify_query", "run_causal", "run_bayesian",
            "check_guardian", "run_pipeline", "query_memory",
            "export_reproducibility_artifact", "get_system_capabilities",
            "run_benchmark_suite",
        ],
        "benchmarks": [
            {"id": "counterbench", "hypothesis": "H17", "description": "Counterfactual reasoning accuracy"},
            {"id": "xai", "hypothesis": "H27", "description": "Explainability quality (fidelity, stability, simplicity)"},
            {"id": "tau_bench", "hypothesis": "H18", "description": "Policy-guided agent compliance"},
        ],
    }

    # Check optional service availability
    try:
        from src.services.embedding_engine import get_embedding_engine
        engine = get_embedding_engine()
        capabilities["services"]["embedding_engine_dense"] = engine._dense_available
    except Exception:
        capabilities["services"]["embedding_engine_dense"] = False

    return capabilities


async def run_benchmark_suite(
    benchmark_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run one or more benchmarks and return combined results.

    Args:
        benchmark_ids: List of benchmark IDs to run. If None, runs all.
            Available: 'counterbench', 'xai', 'tau_bench'

    Returns:
        Dict with results per benchmark and overall summary.
    """
    available = {
        "counterbench": "benchmarks.technical.causal.benchmark_counterbench",
        "xai": "benchmarks.technical.compliance.benchmark_xai",
        "tau_bench": "benchmarks.technical.governance.benchmark_tau_bench",
    }

    if benchmark_ids is None:
        benchmark_ids = list(available.keys())

    results: dict[str, Any] = {}
    for bid in benchmark_ids:
        if bid not in available:
            results[bid] = {"error": f"Unknown benchmark: {bid}"}
            continue

        try:
            import importlib
            module = importlib.import_module(available[bid])
            report = await module.run_benchmark()
            results[bid] = {
                "status": "completed",
                "metrics": report.get("metrics", {}),
                "passed": report.get("metrics", {}).get("passed", False),
            }
        except Exception as exc:
            results[bid] = {"status": "error", "error": str(exc)}

    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total = len(results)

    return {
        "benchmarks_run": benchmark_ids,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "grade": "A" if passed_count == total else "B" if passed_count >= total - 1 else "C",
        },
    }


def export_reproducibility_artifact(
    state_or_result: Any,
    include_data: bool = False,
) -> dict[str, Any]:
    """Package an EpistemicState or pipeline result into a reproducibility artifact.

    Creates a JSON-serializable artifact containing:
    - Input parameters (query, context)
    - Analysis configuration
    - Evidence results
    - Environment metadata (Python version, CARF version)
    - Reasoning chain for audit

    Args:
        state_or_result: An EpistemicState object or pipeline result dict.
        include_data: If True, includes raw data in the artifact.

    Returns:
        JSON-serializable dict containing the full reproducibility artifact.
    """
    import platform
    import sys
    from datetime import datetime

    artifact: dict[str, Any] = {
        "artifact_type": "carf_reproducibility",
        "exported_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "carf_test_mode": __import__("os").environ.get("CARF_TEST_MODE", "0"),
        },
    }

    if isinstance(state_or_result, dict):
        # Pipeline result dict
        artifact["input"] = {
            "query": state_or_result.get("user_input", state_or_result.get("query", "")),
        }
        artifact["results"] = {
            k: v for k, v in state_or_result.items()
            if k not in ("user_input", "query")
        }
    else:
        # EpistemicState object
        artifact["input"] = {
            "query": getattr(state_or_result, "user_input", ""),
            "session_id": str(getattr(state_or_result, "session_id", "")),
        }

        # Context (optionally with data)
        context = getattr(state_or_result, "context", {}) or {}
        if not include_data:
            context = {
                k: v for k, v in context.items()
                if k != "causal_estimation" or not isinstance(v, dict) or "data" not in v
            }
        artifact["context"] = context

        # Domain classification
        domain = getattr(state_or_result, "cynefin_domain", None)
        artifact["classification"] = {
            "domain": domain.value if hasattr(domain, "value") else str(domain),
            "confidence": getattr(state_or_result, "domain_confidence", 0.0),
            "entropy": getattr(state_or_result, "domain_entropy", 0.0),
        }

        # Evidence
        causal = getattr(state_or_result, "causal_evidence", None)
        if causal:
            artifact["causal_evidence"] = {
                "effect_size": getattr(causal, "effect_size", None),
                "confidence_interval": getattr(causal, "confidence_interval", None),
                "refutation_passed": getattr(causal, "refutation_passed", None),
                "p_value": getattr(causal, "p_value", None),
                "treatment": getattr(causal, "treatment", ""),
                "outcome": getattr(causal, "outcome", ""),
            }

        bayesian = getattr(state_or_result, "bayesian_evidence", None)
        if bayesian:
            artifact["bayesian_evidence"] = {
                "posterior_mean": getattr(bayesian, "posterior_mean", None),
                "credible_interval": getattr(bayesian, "credible_interval", None),
                "epistemic_uncertainty": getattr(bayesian, "epistemic_uncertainty", None),
            }

        # Guardian verdict
        verdict = getattr(state_or_result, "guardian_verdict", None)
        if verdict:
            artifact["guardian"] = {
                "verdict": verdict.value if hasattr(verdict, "value") else str(verdict),
                "violations": getattr(state_or_result, "policy_violations", []),
            }

        # Reasoning chain
        chain = getattr(state_or_result, "reasoning_chain", [])
        if chain:
            artifact["reasoning_chain"] = [
                {
                    "node": getattr(step, "node_name", ""),
                    "action": getattr(step, "action", ""),
                    "output": getattr(step, "output_summary", ""),
                    "confidence": getattr(step, "confidence", ""),
                    "duration_ms": getattr(step, "duration_ms", 0),
                }
                for step in chain
            ]

        artifact["final_response"] = getattr(state_or_result, "final_response", None)

    return artifact


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
