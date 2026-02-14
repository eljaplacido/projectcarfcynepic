"""Developer tools and benchmarking endpoints."""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.models import BenchmarkMetadata, BenchmarkResult
from src.services.developer import DeveloperState, get_developer_service
from src.workflows.graph import run_carf

logger = logging.getLogger("carf")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS_DIR = PROJECT_ROOT / "demo" / "benchmarks"

router = APIRouter()


@router.get("/developer/state", response_model=DeveloperState, tags=["Developer"])
async def get_developer_state():
    """Get current system state for developer view."""
    dev_service = get_developer_service()
    return dev_service.get_state()


@router.get("/developer/logs", tags=["Developer"])
async def get_developer_logs(
    layer: str | None = None,
    level: str | None = None,
    limit: int = 100,
):
    """Get filtered log entries."""
    dev_service = get_developer_service()
    logs = dev_service.get_logs(layer=layer, level=level, limit=limit)
    return {"logs": [log.model_dump() for log in logs]}


@router.websocket("/developer/ws")
async def developer_websocket(websocket: WebSocket):
    """WebSocket for real-time log streaming."""
    await websocket.accept()
    dev_service = get_developer_service()
    dev_service.add_ws_connection(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        dev_service.remove_ws_connection(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        dev_service.remove_ws_connection(websocket)


@router.get("/benchmarks", tags=["Benchmarking"])
async def list_benchmarks() -> list[BenchmarkMetadata]:
    """List all available benchmark datasets."""
    benchmarks = []

    if not BENCHMARKS_DIR.exists():
        return benchmarks

    for file in BENCHMARKS_DIR.glob("*.json"):
        try:
            with open(file) as f:
                data = json.load(f)
                benchmarks.append(
                    BenchmarkMetadata(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"],
                        domain=data["domain"],
                        expected_classification=data["expected_classification"],
                        query=data["query"],
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to load benchmark {file}: {e}")

    return benchmarks


@router.get("/benchmarks/{benchmark_id}", tags=["Benchmarking"])
async def get_benchmark(benchmark_id: str) -> dict:
    """Get full benchmark details including data."""
    file_path = BENCHMARKS_DIR / f"{benchmark_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    with open(file_path) as f:
        return json.load(f)


@router.post("/benchmarks/{benchmark_id}/run", tags=["Benchmarking"])
async def run_benchmark(benchmark_id: str) -> BenchmarkResult:
    """Run a benchmark and compare results against expected values."""
    file_path = BENCHMARKS_DIR / f"{benchmark_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    with open(file_path) as f:
        benchmark = json.load(f)

    expected_range = benchmark["expected_results"]["effect_range"]
    expected_confidence = benchmark["expected_results"]["confidence_min"]
    expected_direction = benchmark["validation_criteria"]["effect_direction"]

    context: dict[str, Any] = {}
    if "data" in benchmark:
        context["benchmark_data"] = benchmark["data"]
    if "dataset_selection" in benchmark:
        context["dataset_selection"] = benchmark["dataset_selection"]

    try:
        final_state = await run_carf(
            user_input=benchmark["query"],
            context=context,
        )
    except ValueError as exc:
        return BenchmarkResult(
            benchmark_id=benchmark_id,
            passed=False,
            message=f"Engine error: {exc}",
        )

    actual_effect = None
    actual_confidence = final_state.domain_confidence

    if final_state.proposed_action:
        actual_effect = final_state.proposed_action.get("effect_size")

    effect_in_range = (
        actual_effect is not None
        and expected_range[0] <= actual_effect <= expected_range[1]
    )
    confidence_met = actual_confidence >= expected_confidence

    direction_match = None
    if actual_effect is not None:
        direction_match = (
            (actual_effect < 0 and expected_direction == "negative")
            or (actual_effect > 0 and expected_direction == "positive")
            or (actual_effect == 0 and expected_direction == "neutral")
        )

    passed = effect_in_range and confidence_met and bool(direction_match)

    return BenchmarkResult(
        benchmark_id=benchmark_id,
        passed=passed,
        actual_effect=actual_effect,
        expected_range=expected_range,
        actual_confidence=actual_confidence,
        expected_confidence_min=expected_confidence,
        effect_direction_match=direction_match,
        message="Benchmark passed" if passed else "Benchmark failed validation criteria",
    )
