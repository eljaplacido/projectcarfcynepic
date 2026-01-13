"""CARF Main Entry Point.

This module initializes the CARF system and provides the main execution loop.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.core.state import CynefinDomain, EpistemicState, GuardianVerdict
from src.services.bayesian import BayesianInferenceConfig
from src.services.causal import CausalEstimationConfig
from src.services.dataset_store import DatasetMetadata, get_dataset_store
from src.workflows.graph import run_carf

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("carf")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("CARF System Starting...")
    logger.info("Phase 1 MVP - Cognitive Spine Active")

    # Validate required environment
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - LLM features will fail")

    yield
    logger.info("CARF System Shutting Down...")


app = FastAPI(
    title="CARF API",
    description="Complex-Adaptive Reasoning Fabric - Neuro-Symbolic-Causal Agentic System",
    version="0.1.0",
    lifespan=lifespan,
)


class DatasetSelection(BaseModel):
    """Selection mapping for a stored dataset."""

    dataset_id: str = Field(..., description="Dataset registry ID")
    treatment: str = Field(..., description="Treatment column name")
    outcome: str = Field(..., description="Outcome column name")
    covariates: list[str] = Field(default_factory=list)
    effect_modifiers: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    """Input request for CARF processing."""

    query: str = Field(..., min_length=1, description="The query to process")
    context: dict | None = Field(default=None, description="Additional context")
    causal_estimation: CausalEstimationConfig | None = Field(
        default=None,
        description="Optional DoWhy/EconML estimation config",
    )
    bayesian_inference: BayesianInferenceConfig | None = Field(
        default=None,
        description="Optional PyMC inference config",
    )
    dataset_selection: DatasetSelection | None = Field(
        default=None,
        description="Optional dataset selection for causal estimation",
    )


class DatasetCreateRequest(BaseModel):
    """Dataset upload payload for the registry."""

    name: str = Field(..., min_length=1, description="Dataset name")
    description: str | None = Field(default=None, description="Dataset description")
    data: list[dict[str, Any]] | dict[str, list[Any]] = Field(
        ..., description="Rows as list of objects or columns as dict of lists"
    )


class DatasetCreateResponse(BaseModel):
    """Response for dataset creation."""

    dataset_id: str
    name: str
    description: str | None
    created_at: str
    row_count: int
    column_names: list[str]


class DatasetListResponse(BaseModel):
    """List datasets response."""

    datasets: list[DatasetCreateResponse]


class DatasetPreviewResponse(BaseModel):
    """Preview rows for a dataset."""

    dataset_id: str
    rows: list[dict[str, Any]]


class ScenarioMetadata(BaseModel):
    """Demo scenario metadata."""

    id: str
    name: str
    description: str
    payload_path: str


class ScenarioListResponse(BaseModel):
    """List demo scenarios."""

    scenarios: list[ScenarioMetadata]


class ScenarioDetailResponse(BaseModel):
    """Scenario details including payload."""

    scenario: ScenarioMetadata
    payload: dict[str, Any]


def _validate_payload_limits(request: QueryRequest) -> None:
    """Guardrails for payload sizes in the research demo."""
    if request.dataset_selection and request.causal_estimation:
        raise HTTPException(
            status_code=400,
            detail="Provide either dataset_selection or causal_estimation, not both",
        )

    if request.causal_estimation and request.causal_estimation.data is not None:
        data = request.causal_estimation.data
        if isinstance(data, list) and len(data) > 5000:
            raise HTTPException(
                status_code=400,
                detail="causal_estimation.data exceeds 5000 rows",
            )
        if isinstance(data, dict):
            longest = max((len(values) for values in data.values()), default=0)
            if longest > 5000:
                raise HTTPException(
                    status_code=400,
                    detail="causal_estimation.data exceeds 5000 rows",
                )

    if request.bayesian_inference and request.bayesian_inference.observations:
        if len(request.bayesian_inference.observations) > 10000:
            raise HTTPException(
                status_code=400,
                detail="bayesian_inference.observations exceeds 10000 values",
            )


class ReasoningStep(BaseModel):
    """A step in the reasoning chain."""

    node: str
    action: str
    confidence: str


class QueryResponse(BaseModel):
    """Response from CARF processing."""

    session_id: str
    domain: CynefinDomain
    domain_confidence: float
    guardian_verdict: GuardianVerdict | None
    response: str | None
    requires_human: bool
    reasoning_chain: list[ReasoningStep]
    error: str | None = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "phase": "MVP",
        "version": "0.1.0",
        "components": {
            "router": "active",
            "guardian": "active",
            "human_layer": "mock" if not os.getenv("HUMANLAYER_API_KEY") else "active",
        },
    }


@app.post("/datasets", response_model=DatasetCreateResponse)
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


@app.get("/datasets", response_model=DatasetListResponse)
async def list_datasets():
    """List datasets from the local registry."""
    store = get_dataset_store()
    datasets = [
        DatasetCreateResponse(**_metadata_to_payload(metadata))
        for metadata in store.list_datasets()
    ]
    return DatasetListResponse(datasets=datasets)


@app.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
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


@app.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios():
    """List demo scenarios for the UI."""
    scenarios = _load_scenarios()
    return ScenarioListResponse(scenarios=scenarios)


@app.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario(scenario_id: str):
    """Fetch a scenario payload by ID."""
    scenarios = _load_scenarios()
    scenario_map = {scenario.id: scenario for scenario in scenarios}
    scenario = scenario_map.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    payload = _load_scenario_payload(scenario.payload_path)
    return ScenarioDetailResponse(scenario=scenario, payload=payload)


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query through the CARF cognitive pipeline.

    The query flows through:
    1. Cynefin Router - classifies into domain (Clear/Complicated/Complex/Chaotic/Disorder)
    2. Domain Agent - processes based on classification
    3. Guardian - policy check
    4. Human Escalation - if needed

    Returns the final state with reasoning chain for audit.
    """
    try:
        _validate_payload_limits(request)

        context = dict(request.context or {})
        if request.dataset_selection:
            store = get_dataset_store()
            try:
                store.get_dataset(request.dataset_selection.dataset_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

            context["dataset_selection"] = request.dataset_selection.model_dump()
            context["causal_estimation"] = CausalEstimationConfig(
                dataset_id=request.dataset_selection.dataset_id,
                treatment=request.dataset_selection.treatment,
                outcome=request.dataset_selection.outcome,
                covariates=request.dataset_selection.covariates,
                effect_modifiers=request.dataset_selection.effect_modifiers,
            ).model_dump()
        elif request.causal_estimation:
            context["causal_estimation"] = request.causal_estimation.model_dump()

        if request.bayesian_inference:
            context["bayesian_inference"] = request.bayesian_inference.model_dump()

        # Run the full CARF pipeline
        final_state = await run_carf(
            user_input=request.query,
            context=context,
        )

        # Build reasoning chain for response
        reasoning_chain = [
            ReasoningStep(
                node=step.node_name,
                action=step.action,
                confidence=step.confidence.value,
            )
            for step in final_state.reasoning_chain
        ]

        return QueryResponse(
            session_id=str(final_state.session_id),
            domain=final_state.cynefin_domain,
            domain_confidence=final_state.domain_confidence,
            guardian_verdict=final_state.guardian_verdict,
            response=final_state.final_response,
            requires_human=final_state.should_escalate_to_human(),
            reasoning_chain=reasoning_chain,
            error=final_state.error,
        )

    except Exception as e:
        logger.error(f"CARF pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"CARF processing failed: {str(e)}",
        )


def _metadata_to_payload(metadata: DatasetMetadata) -> dict[str, Any]:
    """Serialize dataset metadata for API responses."""
    return {
        "dataset_id": metadata.dataset_id,
        "name": metadata.name,
        "description": metadata.description,
        "created_at": metadata.created_at,
        "row_count": metadata.row_count,
        "column_names": metadata.column_names,
    }


def _load_scenarios() -> list[ScenarioMetadata]:
    """Load demo scenarios from the registry file."""
    registry_path = PROJECT_ROOT / "demo" / "scenarios.json"
    if not registry_path.exists():
        return []

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse scenarios registry: %s", exc)
        return []

    scenarios = []
    for item in data:
        try:
            scenarios.append(ScenarioMetadata(**item))
        except Exception as exc:
            logger.warning("Skipping invalid scenario entry: %s", exc)
    return scenarios


def _load_scenario_payload(payload_path: str) -> dict[str, Any]:
    """Load scenario payload JSON from disk."""
    path = PROJECT_ROOT / payload_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Scenario payload not found")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid scenario payload") from exc


@app.get("/domains")
async def list_domains():
    """List all Cynefin domains and their descriptions."""
    return {
        "domains": [
            {
                "name": "Clear",
                "description": "Cause-effect obvious. Deterministic automation.",
                "route": "deterministic_runner",
            },
            {
                "name": "Complicated",
                "description": "Requires expert analysis. Causal inference.",
                "route": "causal_analyst",
            },
            {
                "name": "Complex",
                "description": "Emergent causality. Bayesian probing.",
                "route": "bayesian_explorer",
            },
            {
                "name": "Chaotic",
                "description": "Crisis mode. Circuit breaker.",
                "route": "circuit_breaker",
            },
            {
                "name": "Disorder",
                "description": "Cannot classify. Human escalation.",
                "route": "human_escalation",
            },
        ]
    }


def main():
    """Main entry point for CLI execution."""
    import uvicorn

    logger.info("Starting CARF in development mode...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
