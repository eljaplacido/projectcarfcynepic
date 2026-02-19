"""Simulation arena endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.models import DataGenerationRequest, RealismAssessmentRequest
from src.services.dataset_store import get_dataset_store
from src.services.simulation import (
    EnhancedSimulationResult,
    ScenarioConfig,
    ScenarioRealismScore,
    SimulationComparison,
    SimulationResult,
    assess_scenario_realism,
    get_simulation_service,
)

logger = logging.getLogger("carf")
router = APIRouter()


@router.post("/simulations/run", response_model=list[SimulationResult], tags=["Simulation"])
async def run_simulations(
    scenarios: list[ScenarioConfig],
    context: dict[str, Any] | None = None,
):
    """Run multiple what-if scenario simulations."""
    sim_service = get_simulation_service()

    try:
        results = await sim_service.run_multiple_scenarios(scenarios, context)
        return results
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation execution failed: {str(e)}"
        )


@router.post("/simulations/compare", response_model=SimulationComparison, tags=["Simulation"])
async def compare_simulations(scenario_ids: list[str]):
    """Compare multiple simulation results."""
    sim_service = get_simulation_service()

    try:
        comparison = await sim_service.compare_scenarios(scenario_ids)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/simulations/{scenario_id}/status", response_model=SimulationResult, tags=["Simulation"])
async def get_simulation_status(scenario_id: str):
    """Get the current status of a simulation."""
    sim_service = get_simulation_service()
    result = sim_service.get_simulation_status(scenario_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {scenario_id}"
        )

    return result


@router.post("/simulations/{scenario_id}/rerun", response_model=SimulationResult, tags=["Simulation"])
async def rerun_simulation(
    scenario_id: str,
    config: ScenarioConfig,
    context: dict[str, Any] | None = None,
):
    """Invalidate cache and re-run a scenario with updated parameters."""
    sim_service = get_simulation_service()

    try:
        result = await sim_service.invalidate_and_rerun(scenario_id, config, context)
        return result
    except Exception as e:
        logger.error(f"Re-run failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Re-run failed: {str(e)}"
        )


@router.get("/simulations/generators", tags=["Simulation"])
async def list_data_generators():
    """List available realistic data generators."""
    sim_service = get_simulation_service()
    return sim_service.list_available_generators()


@router.post("/simulations/generate", tags=["Simulation"])
async def generate_simulation_data(request: DataGenerationRequest):
    """Generate realistic simulation data with known causal structure."""
    sim_service = get_simulation_service()
    df = sim_service.generate_scenario_data(
        scenario_type=request.scenario_type,
        n_samples=request.n_samples,
        seed=request.seed,
    )

    if df is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario type: {request.scenario_type}"
        )

    return {
        "scenario_type": request.scenario_type,
        "n_samples": len(df),
        "columns": list(df.columns),
        "sample_data": df.head(5).to_dict(orient="records"),
        "data_summary": {
            col: {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique()),
            }
            for col in df.columns
        },
    }


@router.post("/simulations/assess-realism", response_model=ScenarioRealismScore, tags=["Simulation"])
async def assess_scenario_data_realism(request: RealismAssessmentRequest):
    """Assess the realism and quality of simulation/scenario data."""
    import pandas as pd

    dataset_store = get_dataset_store()

    try:
        dataset_info = dataset_store.get_dataset(request.dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {request.dataset_id}"
        )

    try:
        df = pd.read_csv(dataset_info.storage_path)
        realism = assess_scenario_realism(
            df=df,
            treatment_col=request.treatment_col,
            outcome_col=request.outcome_col,
            covariates=request.covariates,
        )
        return realism
    except Exception as e:
        logger.error(f"Realism assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment failed: {str(e)}"
        )


@router.post("/simulations/run-transparent", response_model=EnhancedSimulationResult, tags=["Simulation"])
async def run_simulation_with_transparency(
    config: ScenarioConfig,
    treatment_col: str | None = None,
    outcome_col: str | None = None,
    covariates: list[str] | None = None,
    context: dict[str, Any] | None = None,
):
    """Run simulation with full transparency and reliability reporting."""
    import pandas as pd

    sim_service = get_simulation_service()
    dataset_store = get_dataset_store()

    df = None
    if config.baseline_dataset_id:
        try:
            dataset_info = dataset_store.get_dataset(config.baseline_dataset_id)
            df = pd.read_csv(dataset_info.storage_path)
        except KeyError:
            logger.warning(f"Dataset not found: {config.baseline_dataset_id}")
        except Exception as e:
            logger.warning(f"Could not load dataset for realism assessment: {e}")

    try:
        result = await sim_service.run_scenario_with_transparency(
            config=config,
            data=df,
            treatment_col=treatment_col,
            outcome_col=outcome_col,
            covariates=covariates,
            context=context,
        )
        return result
    except Exception as e:
        logger.error(f"Transparent simulation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}"
        )


@router.get("/sessions/{session_id}/lineage", tags=["Simulation"])
async def get_session_lineage(session_id: str):
    """Get the lineage tree for an analysis session."""
    from src.services.neo4j_service import get_neo4j_service

    neo4j = get_neo4j_service()

    try:
        lineage = await neo4j.get_session_lineage(session_id)
        return lineage
    except Exception as e:
        logger.error(f"Lineage query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve lineage: {str(e)}"
        )
