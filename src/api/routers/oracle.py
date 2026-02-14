"""ChimeraOracle endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from src.api.models import (
    OracleModelInfo,
    OraclePredictRequest,
    OraclePredictResponse,
    OracleTrainRequest,
    OracleTrainResponse,
)

logger = logging.getLogger("carf")
router = APIRouter(tags=["ChimeraOracle"])


@router.get("/oracle/models")
async def list_oracle_models() -> list[OracleModelInfo]:
    """List all trained ChimeraOracle models."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    models = []
    for scenario_id in engine.get_available_scenarios():
        stats = engine.get_average_treatment_effect(scenario_id)
        models.append(
            OracleModelInfo(
                scenario_id=scenario_id,
                average_treatment_effect=stats["ate"],
                effect_std=stats["std"],
                n_samples=stats["n_samples"],
            )
        )
    return models


@router.post("/oracle/train")
async def train_oracle_model(request: OracleTrainRequest) -> OracleTrainResponse:
    """Train a CausalForestDML model on scenario data."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()
    result = await engine.train_on_scenario(
        scenario_id=request.scenario_id,
        csv_path=request.csv_path,
        treatment=request.treatment,
        outcome=request.outcome,
        covariates=request.covariates,
        effect_modifiers=request.effect_modifiers,
        n_estimators=request.n_estimators,
    )

    return OracleTrainResponse(
        status=result.status,
        n_samples=result.n_samples,
        model_path=result.model_path,
        average_treatment_effect=result.average_treatment_effect,
        effect_std=result.effect_std,
        error=result.error,
    )


@router.post("/oracle/predict")
async def predict_oracle_effect(request: OraclePredictRequest) -> OraclePredictResponse:
    """Fast causal effect prediction using a trained model."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()

    if not engine.has_model(request.scenario_id):
        raise HTTPException(
            status_code=404,
            detail=f"No trained model for scenario: {request.scenario_id}. Train first with /oracle/train"
        )

    prediction = engine.predict_effect(request.scenario_id, request.context)

    return OraclePredictResponse(
        effect_estimate=prediction.effect_estimate,
        confidence_interval=prediction.confidence_interval,
        feature_importance=prediction.feature_importance,
        used_model=prediction.used_model,
        prediction_time_ms=prediction.prediction_time_ms,
    )


@router.get("/oracle/models/{scenario_id}")
async def get_oracle_model(scenario_id: str) -> OracleModelInfo:
    """Get details about a specific trained model."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()

    if not engine.has_model(scenario_id):
        raise HTTPException(status_code=404, detail=f"Model not found: {scenario_id}")

    stats = engine.get_average_treatment_effect(scenario_id)
    return OracleModelInfo(
        scenario_id=scenario_id,
        average_treatment_effect=stats["ate"],
        effect_std=stats["std"],
        n_samples=stats["n_samples"],
    )
