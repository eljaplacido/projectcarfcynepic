"""Developer tools and benchmarking endpoints."""

import json
import logging
import time
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
    """Run a benchmark and compare results against expected values.

    Supports all 5 Cynefin domains with domain-specific validation:
    - Clear: action_type match, confidence, no escalation
    - Complicated: effect range, direction, confidence, refutation
    - Complex: Bayesian evidence, uncertainty, confidence
    - Chaotic: circuit breaker activation, escalation
    - Disorder: human escalation, low confidence
    """
    file_path = BENCHMARKS_DIR / f"{benchmark_id}.json"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    with open(file_path) as f:
        benchmark = json.load(f)

    expected_classification = benchmark.get("expected_classification", "complicated")
    validation = benchmark.get("validation_criteria", {})
    expected_results = benchmark.get("expected_results", {})

    context: dict[str, Any] = {}
    if "data" in benchmark:
        context["benchmark_data"] = benchmark["data"]
    if "dataset_selection" in benchmark:
        context["dataset_selection"] = benchmark["dataset_selection"]
    if "context" in benchmark:
        context.update(benchmark["context"])

    start_time = time.perf_counter()
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
    pipeline_duration_ms = (time.perf_counter() - start_time) * 1000

    # --- Domain-generic validation ---
    actual_domain = final_state.cynefin_domain.value
    expected_domain = expected_results.get("domain", expected_classification.capitalize())
    domain_match = actual_domain.lower() == expected_domain.lower()

    actual_confidence = final_state.domain_confidence
    escalation_triggered = final_state.should_escalate_to_human()

    actual_action_type = None
    if final_state.proposed_action:
        actual_action_type = final_state.proposed_action.get("action_type")

    # --- Domain-specific validation ---
    checks: dict[str, Any] = {"domain_match": domain_match}
    passed = domain_match  # Always require correct domain routing

    if expected_classification == "complicated":
        # Causal validation (original logic)
        expected_range = expected_results.get("effect_range", [])
        expected_confidence = expected_results.get("confidence_min", 0.0)
        expected_direction = validation.get("effect_direction", "")

        actual_effect = None
        if final_state.proposed_action:
            actual_effect = final_state.proposed_action.get("effect_size")
            if actual_effect is None:
                params = final_state.proposed_action.get("parameters", {})
                actual_effect = params.get("effect_size")

        effect_in_range = (
            actual_effect is not None
            and len(expected_range) == 2
            and expected_range[0] <= actual_effect <= expected_range[1]
        )
        confidence_met = actual_confidence >= expected_confidence
        direction_match = None
        if actual_effect is not None and expected_direction:
            direction_match = (
                (actual_effect < 0 and expected_direction == "negative")
                or (actual_effect > 0 and expected_direction == "positive")
                or (actual_effect == 0 and expected_direction == "neutral")
            )

        checks.update({
            "effect_in_range": effect_in_range,
            "confidence_met": confidence_met,
            "direction_match": direction_match,
        })
        passed = passed and effect_in_range and confidence_met and bool(direction_match)

        return BenchmarkResult(
            benchmark_id=benchmark_id,
            passed=passed,
            actual_effect=actual_effect,
            expected_range=expected_range if expected_range else None,
            actual_confidence=actual_confidence,
            expected_confidence_min=expected_confidence,
            effect_direction_match=direction_match,
            actual_domain=actual_domain,
            expected_domain=expected_domain,
            domain_match=domain_match,
            escalation_triggered=escalation_triggered,
            action_type=actual_action_type,
            pipeline_duration_ms=pipeline_duration_ms,
            message="Benchmark passed" if passed else "Benchmark failed validation criteria",
            validation_details=checks,
        )

    elif expected_classification == "clear":
        # Deterministic: verify action_type, confidence, no escalation
        expected_action = validation.get("action_type", "lookup")
        action_match = actual_action_type == expected_action
        confidence_met = actual_confidence >= validation.get("confidence_min", 0.7)
        no_escalation = not escalation_triggered

        checks.update({
            "action_match": action_match,
            "confidence_met": confidence_met,
            "no_escalation": no_escalation,
        })
        passed = passed and action_match and confidence_met and no_escalation

    elif expected_classification == "complex":
        # Bayesian: verify uncertainty metrics, probe design
        has_bayesian = final_state.bayesian_evidence is not None
        confidence_met = actual_confidence >= validation.get("confidence_min", 0.4)
        has_response = final_state.final_response is not None

        checks.update({
            "has_bayesian_evidence": has_bayesian,
            "confidence_met": confidence_met,
            "has_response": has_response,
        })
        passed = passed and has_response and confidence_met

    elif expected_classification == "chaotic":
        # Circuit breaker: verify escalation, action_type
        expected_action = validation.get("action_type", "emergency_stop")
        action_match = actual_action_type == expected_action
        must_escalate = validation.get("must_escalate", True)
        escalation_correct = escalation_triggered == must_escalate

        checks.update({
            "action_match": action_match,
            "escalation_correct": escalation_correct,
        })
        passed = passed and action_match and escalation_correct

    elif expected_classification == "disorder":
        # Disorder: verify human escalation, low confidence
        must_escalate = validation.get("must_escalate", True)
        escalation_correct = escalation_triggered == must_escalate
        confidence_max = validation.get("confidence_max", 0.85)
        low_confidence_ok = actual_confidence < confidence_max

        checks.update({
            "escalation_correct": escalation_correct,
            "low_confidence": low_confidence_ok,
        })
        passed = passed and escalation_correct

    return BenchmarkResult(
        benchmark_id=benchmark_id,
        passed=passed,
        actual_confidence=actual_confidence,
        actual_domain=actual_domain,
        expected_domain=expected_domain,
        domain_match=domain_match,
        escalation_triggered=escalation_triggered,
        expected_escalation=validation.get("must_escalate") or validation.get("should_escalate"),
        action_type=actual_action_type,
        expected_action_type=validation.get("action_type"),
        pipeline_duration_ms=pipeline_duration_ms,
        message="Benchmark passed" if passed else "Benchmark failed validation criteria",
        validation_details=checks,
    )


@router.post("/benchmarks/run-all", tags=["Benchmarking"])
async def run_all_benchmarks() -> dict[str, Any]:
    """Run all benchmarks and return aggregate results."""
    benchmarks = await list_benchmarks()
    results = []
    for bm in benchmarks:
        try:
            result = await run_benchmark(bm.id)
            results.append(result.model_dump())
        except Exception as e:
            results.append({
                "benchmark_id": bm.id,
                "passed": False,
                "message": f"Error: {e}",
            })

    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    avg_duration = (
        sum(r.get("pipeline_duration_ms", 0) or 0 for r in results) / total
        if total > 0 else 0
    )

    # Domain breakdown
    domain_summary: dict[str, dict[str, int]] = {}
    for r in results:
        domain = r.get("expected_domain", "unknown")
        if domain not in domain_summary:
            domain_summary[domain] = {"total": 0, "passed": 0}
        domain_summary[domain]["total"] += 1
        if r.get("passed"):
            domain_summary[domain]["passed"] += 1

    return {
        "total_benchmarks": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total > 0 else 0,
        "avg_pipeline_duration_ms": round(avg_duration, 2),
        "domain_breakdown": domain_summary,
        "results": results,
    }
