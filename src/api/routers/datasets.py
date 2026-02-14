"""Dataset and scenario endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from src.api.deps import _load_scenario_payload, _load_scenarios, _metadata_to_payload
from src.api.models import (
    DatasetCreateRequest,
    DatasetCreateResponse,
    DatasetListResponse,
    DatasetPreviewResponse,
    ScenarioDetailResponse,
    ScenarioListResponse,
    ScenarioLoadRequest,
)
from src.services.dataset_store import get_dataset_store

logger = logging.getLogger("carf")
router = APIRouter()


@router.post("/datasets", response_model=DatasetCreateResponse)
async def create_dataset(request: DatasetCreateRequest):
    """Create a dataset in the local registry."""
    store = get_dataset_store()
    try:
        metadata = store.create_dataset(
            name=request.name,
            description=request.description,
            data=request.data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetCreateResponse(**_metadata_to_payload(metadata))


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets():
    """List datasets from the local registry."""
    store = get_dataset_store()
    datasets = [
        DatasetCreateResponse(**_metadata_to_payload(metadata))
        for metadata in store.list_datasets()
    ]
    return DatasetListResponse(datasets=datasets)


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(dataset_id: str, limit: int = 10):
    """Preview dataset rows."""
    store = get_dataset_store()
    try:
        rows = store.load_preview(dataset_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetPreviewResponse(dataset_id=dataset_id, rows=rows)


@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios():
    """List demo scenarios for the UI."""
    scenarios = _load_scenarios()
    return ScenarioListResponse(scenarios=scenarios)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario(scenario_id: str):
    """Fetch a scenario payload by ID."""
    scenarios = _load_scenarios()
    scenario_map = {scenario.id: scenario for scenario in scenarios}
    scenario = scenario_map.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    payload = _load_scenario_payload(scenario.payload_path)
    return ScenarioDetailResponse(scenario=scenario, payload=payload)


@router.post("/scenarios/load")
async def load_scenario(request: ScenarioLoadRequest):
    """Load a scenario by ID (POST version for compatibility)."""
    scenarios = _load_scenarios()
    scenario_map = {scenario.id: scenario for scenario in scenarios}
    scenario = scenario_map.get(request.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    payload = _load_scenario_payload(scenario.payload_path)
    return {
        "scenario_id": request.scenario_id,
        "message": "Scenario loaded",
        "scenario": scenario.model_dump(),
        "payload": payload,
    }
