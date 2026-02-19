"""ChimeraOracle tools for MCP.

Wraps ChimeraOracleEngine to expose fast causal predictions, model
training, and model management to any MCP-connected AI agent.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.chimera_oracle import get_oracle_engine


@mcp.tool()
async def oracle_predict(
    scenario_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Fast causal effect prediction using a pre-trained CausalForestDML model.

    Provides sub-100ms predictions when a model has been trained for the
    scenario. Includes drift detection and uncertainty quantification.

    Args:
        scenario_id: Which trained model to use (e.g. "scope3_attribution")
        context: Feature values matching the model's effect modifiers
    """
    engine = get_oracle_engine()
    prediction = engine.predict_effect(scenario_id, context)
    return {
        "effect": prediction.effect_estimate,
        "confidence_interval": list(prediction.confidence_interval),
        "reliability": prediction.reliability_score,
        "drift_detected": prediction.drift_warning,
        "drift_details": prediction.drift_details,
        "latency_ms": prediction.prediction_time_ms,
    }


@mcp.tool()
async def oracle_train(
    scenario_id: str,
    csv_path: str,
    treatment: str,
    outcome: str,
    covariates: list[str] | None = None,
    effect_modifiers: list[str] | None = None,
    n_estimators: int = 100,
) -> dict[str, Any]:
    """Train a CausalForestDML model on scenario data.

    Creates a fast prediction model that can be queried via oracle_predict.
    Training data must be a CSV file with treatment, outcome, and feature columns.

    Args:
        scenario_id: Unique identifier for this scenario model
        csv_path: Path to training data CSV
        treatment: Name of treatment variable column (binary)
        outcome: Name of outcome variable column
        covariates: Confounding adjustment variables
        effect_modifiers: Variables for heterogeneous effects
        n_estimators: Number of trees in the causal forest (default 100)
    """
    engine = get_oracle_engine()
    result = await engine.train_on_scenario(
        scenario_id=scenario_id,
        csv_path=csv_path,
        treatment=treatment,
        outcome=outcome,
        covariates=covariates,
        effect_modifiers=effect_modifiers,
        n_estimators=n_estimators,
    )
    return {
        "scenario_id": scenario_id,
        "model_version": result.model_version,
        "ate": result.average_treatment_effect,
        "ate_std": result.effect_std,
        "n_samples": result.n_samples,
        "cv_score": result.cross_validation_score,
    }


@mcp.tool()
async def oracle_list_models() -> list[dict[str, Any]]:
    """List all trained ChimeraOracle models with summary metadata.

    Returns scenario IDs, average treatment effects, and model availability.
    """
    engine = get_oracle_engine()
    return engine.get_all_models_summary()


@mcp.tool()
async def oracle_model_info(scenario_id: str) -> dict[str, Any]:
    """Get detailed model information including version history.

    Args:
        scenario_id: Scenario identifier to look up
    """
    engine = get_oracle_engine()
    return engine.get_model_info(scenario_id)
