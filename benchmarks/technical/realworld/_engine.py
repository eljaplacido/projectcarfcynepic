# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Shared helper to run CARF's causal engine for real-world benchmarks (R2)."""

from __future__ import annotations

from typing import Any


async def carf_ate(
    data_records: list[dict[str, Any]],
    treatment: str,
    outcome: str,
    covariates: list[str],
) -> dict[str, Any]:
    """Run CARF's causal engine on tabular data and return its ATE + robustness metadata."""
    from src.services.causal import (
        CausalEstimationConfig,
        CausalHypothesis,
        CausalInferenceEngine,
    )

    engine = CausalInferenceEngine(neo4j_service=None)
    hypothesis = CausalHypothesis(
        treatment=treatment,
        outcome=outcome,
        mechanism=f"Real-data effect of {treatment} on {outcome}",
        confounders=covariates,
    )
    config = CausalEstimationConfig(
        data=data_records,
        treatment=treatment,
        outcome=outcome,
        covariates=covariates,
        method_name="backdoor.linear_regression",
    )
    result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
    return {
        "effect": float(result.effect_estimate),
        "confidence_interval": [
            float(result.confidence_interval[0]),
            float(result.confidence_interval[1]),
        ],
        "robust": bool(result.robust),
        "e_value": result.e_value,
        "refutation_status": result.refutation_status,
    }
