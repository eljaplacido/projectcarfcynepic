"""Bayesian active inference tools for MCP.

Wraps ActiveInferenceEngine to expose belief exploration and PyMC
inference to any MCP-connected AI agent.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.bayesian import BayesianInferenceConfig, get_bayesian_engine


@mcp.tool()
async def bayesian_explore(
    query: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full Active Inference exploration: establish priors, design probes, update beliefs.

    Handles Complex domain queries by establishing prior beliefs, identifying
    high-uncertainty areas, designing probes to reduce uncertainty, and
    updating beliefs based on evidence.

    Args:
        query: The complex situation to explore (e.g. "How will AI affect hiring?")
        context: Additional context. Include "bayesian_inference" key with
                 observations/binomial data for real posterior updates.
    """
    engine = get_bayesian_engine()
    result = await engine.explore(query, context)
    return {
        "initial_belief": {
            "hypothesis": result.initial_belief.hypothesis,
            "prior": result.initial_belief.prior,
            "posterior": result.initial_belief.posterior,
        },
        "updated_belief": {
            "hypothesis": result.updated_belief.hypothesis,
            "prior": result.updated_belief.prior,
            "posterior": result.updated_belief.posterior,
        },
        "probes": [
            {
                "description": p.description,
                "expected_info_gain": p.expected_info_gain,
                "risk_level": p.risk_level,
                "cost_estimate": p.cost_estimate,
            }
            for p in result.probes_designed
        ],
        "recommended_probe": (
            result.recommended_probe.description if result.recommended_probe else None
        ),
        "uncertainty_before": result.uncertainty_before,
        "uncertainty_after": result.uncertainty_after,
        "epistemic_uncertainty": result.epistemic_uncertainty,
        "aleatoric_uncertainty": result.aleatoric_uncertainty,
        "interpretation": result.interpretation,
    }


@mcp.tool()
async def bayesian_run_inference(
    observations: list[float] | None = None,
    successes: int | None = None,
    trials: int | None = None,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> dict[str, Any]:
    """Run PyMC Bayesian inference on provided data.

    Supports two modes:
    - Binomial: provide successes and trials for proportion estimation
    - Observations: provide a list of numeric observations for mean estimation

    Args:
        observations: List of numeric observations (for mean estimation)
        successes: Number of successes (for binomial inference)
        trials: Number of trials (for binomial inference)
        prior_alpha: Beta prior alpha parameter (default 1.0)
        prior_beta: Beta prior beta parameter (default 1.0)
    """
    engine = get_bayesian_engine()
    config = BayesianInferenceConfig(
        observations=observations,
        successes=successes,
        trials=trials,
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
    )
    result = engine._run_pymc_inference(config)
    return {
        "posterior_mean": result.posterior_mean,
        "credible_interval": list(result.credible_interval),
        "posterior_std": result.posterior_std,
        "epistemic_uncertainty": result.epistemic_uncertainty,
        "aleatoric_uncertainty": result.aleatoric_uncertainty,
        "n_samples": result.n_samples,
    }
