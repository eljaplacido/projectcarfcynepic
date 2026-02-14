"""Shared FastAPI dependencies and helper functions.

Extracted from src/main.py so that multiple routers can reuse them.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.api.models import QueryRequest, ScenarioMetadata
from src.services.dataset_store import DatasetMetadata

logger = logging.getLogger("carf")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
