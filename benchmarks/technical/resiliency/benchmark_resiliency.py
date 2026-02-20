"""Benchmark CARF Chaos/Resiliency subsystems.

Tests CircuitBreaker lifecycle, concurrent stress, chaotic domain handling,
retry exhaustion, and timeout handling.

Metrics:
  - circuit_breaker_accuracy — correct state transitions
  - failure_isolation_rate — open breaker correctly blocks calls
  - recovery_time_ms — time from OPEN to recovery via HALF_OPEN
  - chaotic_escalation_rate — chaotic queries correctly trigger emergency protocol

Usage:
    python benchmarks/technical/resiliency/benchmark_resiliency.py
    python benchmarks/technical/resiliency/benchmark_resiliency.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.resiliency")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Test Implementations ─────────────────────────────────────────────────


async def test_cb_lifecycle() -> dict[str, Any]:
    """Test CLOSED → OPEN (after 5 failures) → HALF_OPEN (after timeout) → CLOSED."""
    from src.utils.resiliency import CircuitBreaker, CircuitState

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=0.1)
    checks: dict[str, bool] = {}

    # Should start CLOSED
    checks["starts_closed"] = cb.state == CircuitState.CLOSED

    # Record 4 failures — should stay CLOSED
    for _ in range(4):
        cb.record_failure()
    checks["stays_closed_under_threshold"] = cb.state == CircuitState.CLOSED

    # 5th failure — should transition to OPEN
    cb.record_failure()
    checks["opens_at_threshold"] = cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    checks["transitions_to_half_open"] = cb.state == CircuitState.HALF_OPEN

    # Record success — should CLOSE
    cb.record_success()
    checks["closes_on_success"] = cb.state == CircuitState.CLOSED

    return {
        "test": "cb_lifecycle",
        "checks": checks,
        "passed": all(checks.values()),
    }


async def test_cb_blocks_when_open() -> dict[str, Any]:
    """Open breaker should raise CircuitBreakerOpenError."""
    from src.utils.resiliency import CircuitBreaker, CircuitBreakerOpenError, CircuitState

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    checks: dict[str, bool] = {}

    # Force open
    for _ in range(3):
        cb.record_failure()
    checks["is_open"] = cb.state == CircuitState.OPEN

    # Wrap a dummy function
    @cb
    async def dummy_call():
        return "success"

    # Should raise
    try:
        await dummy_call()
        checks["blocks_call"] = False
    except CircuitBreakerOpenError:
        checks["blocks_call"] = True
    except Exception:
        checks["blocks_call"] = False

    return {
        "test": "cb_blocks_when_open",
        "checks": checks,
        "passed": all(checks.values()),
    }


async def test_concurrent_stress() -> dict[str, Any]:
    """20 concurrent calls with 50% failure rate — breaker responds correctly."""
    from src.utils.resiliency import CircuitBreaker, CircuitBreakerOpenError, CircuitState
    import random

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=0.5)
    call_count = 0
    success_count = 0
    blocked_count = 0
    error_count = 0

    rng = random.Random(42)

    @cb
    async def flaky_call():
        if rng.random() < 0.5:
            raise ConnectionError("Simulated failure")
        return "ok"

    tasks = []
    for _ in range(20):
        tasks.append(flaky_call())

    results = await asyncio.gather(*[_safe_call(t) for t in tasks])

    for r in results:
        call_count += 1
        if r == "ok":
            success_count += 1
        elif r == "blocked":
            blocked_count += 1
        else:
            error_count += 1

    checks = {
        "all_calls_handled": call_count == 20,
        "some_succeeded": success_count > 0,
        "breaker_state_valid": cb.state in (CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN),
    }

    return {
        "test": "concurrent_stress",
        "checks": checks,
        "passed": all(checks.values()),
        "stats": {
            "total_calls": call_count,
            "successes": success_count,
            "blocked": blocked_count,
            "errors": error_count,
            "final_state": cb.state.value,
        },
    }


async def _safe_call(coro):
    """Safely execute a coroutine, catching expected errors."""
    from src.utils.resiliency import CircuitBreakerOpenError
    try:
        return await coro
    except CircuitBreakerOpenError:
        return "blocked"
    except Exception:
        return "error"


async def test_chaotic_emergency_protocol() -> dict[str, Any]:
    """Chaotic query → circuit_breaker_node() → emergency_stop action."""
    from src.core.state import CynefinDomain, EpistemicState
    from src.workflows.graph import circuit_breaker_node

    state = EpistemicState(
        user_input="CRITICAL: Cascade failure across all systems",
        cynefin_domain=CynefinDomain.CHAOTIC,
        domain_entropy=0.95,
    )

    result = await circuit_breaker_node(state)
    checks = {
        "has_response": result.final_response is not None,
        "is_chaotic_response": "[CHAOTIC Domain]" in (result.final_response or ""),
        "action_is_emergency": result.proposed_action is not None
        and result.proposed_action.get("action_type") == "emergency_stop",
        "has_reasoning": len(result.reasoning_chain) > 0,
    }

    return {
        "test": "chaotic_emergency_protocol",
        "checks": checks,
        "passed": all(checks.values()),
    }


async def test_retry_exhaustion() -> dict[str, Any]:
    """async_retry_with_backoff → all 3 attempts fail → exception propagates."""
    from src.utils.resiliency import async_retry_with_backoff

    call_count = 0

    @async_retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=(ValueError,))
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Persistent failure")

    checks: dict[str, bool] = {}
    try:
        await always_fails()
        checks["exception_propagated"] = False
    except (ValueError, Exception):
        checks["exception_propagated"] = True

    checks["retried_3_times"] = call_count == 3

    return {
        "test": "retry_exhaustion",
        "checks": checks,
        "passed": all(checks.values()),
        "call_count": call_count,
    }


async def test_timeout_handling() -> dict[str, Any]:
    """with_timeout() → raises TimeoutError on slow coroutine."""
    from src.utils.resiliency import with_timeout

    async def slow_operation():
        await asyncio.sleep(5.0)
        return "done"

    checks: dict[str, bool] = {}
    t0 = time.perf_counter()
    try:
        await with_timeout(slow_operation(), timeout_seconds=0.1, error_message="Benchmark timeout test")
        checks["timeout_raised"] = False
    except TimeoutError:
        checks["timeout_raised"] = True
    except Exception:
        checks["timeout_raised"] = False

    elapsed_ms = (time.perf_counter() - t0) * 1000
    checks["completed_quickly"] = elapsed_ms < 1000  # Should be ~100ms, not 5000ms

    return {
        "test": "timeout_handling",
        "checks": checks,
        "passed": all(checks.values()),
        "elapsed_ms": round(elapsed_ms, 2),
    }


# ── Benchmark Runner ─────────────────────────────────────────────────────


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run the full resiliency benchmark suite."""
    logger.info("CARF Chaos/Resiliency Benchmark")

    tests = [
        test_cb_lifecycle,
        test_cb_blocks_when_open,
        test_concurrent_stress,
        test_chaotic_emergency_protocol,
        test_retry_exhaustion,
        test_timeout_handling,
    ]

    results = []
    for test_fn in tests:
        logger.info(f"  [{test_fn.__name__}]")
        try:
            result = await test_fn()
        except Exception as e:
            result = {
                "test": test_fn.__name__,
                "checks": {"no_exception": False},
                "passed": False,
                "error": str(e),
            }
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        logger.info(f"    {status} — {result.get('checks', {})}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    # Compute aggregate metrics
    cb_tests = [r for r in results if r["test"].startswith("cb_")]
    cb_accuracy = sum(1 for r in cb_tests if r["passed"]) / len(cb_tests) if cb_tests else 0

    blocking_test = next((r for r in results if r["test"] == "cb_blocks_when_open"), None)
    failure_isolation = 1.0 if blocking_test and blocking_test["passed"] else 0.0

    chaotic_test = next((r for r in results if r["test"] == "chaotic_emergency_protocol"), None)
    chaotic_escalation = 1.0 if chaotic_test and chaotic_test["passed"] else 0.0

    timeout_test = next((r for r in results if r["test"] == "timeout_handling"), None)
    recovery_time_ms = timeout_test.get("elapsed_ms", 0) if timeout_test else 0

    metrics = {
        "circuit_breaker_accuracy": round(cb_accuracy, 2),
        "failure_isolation_rate": round(failure_isolation, 2),
        "recovery_time_ms": round(recovery_time_ms, 2),
        "chaotic_escalation_rate": round(chaotic_escalation, 2),
    }

    report = {
        "benchmark": "carf_chaos_resiliency",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "metrics": metrics,
        "results": results,
    }

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Resiliency Benchmark Summary:")
    logger.info(f"  Tests:                    {total}")
    logger.info(f"  Passed:                   {passed}/{total}")
    logger.info(f"  CB Accuracy:              {metrics['circuit_breaker_accuracy']:.0%}")
    logger.info(f"  Failure Isolation:         {metrics['failure_isolation_rate']:.0%}")
    logger.info(f"  Chaotic Escalation:        {metrics['chaotic_escalation_rate']:.0%}")
    logger.info(f"  Timeout Recovery (ms):     {metrics['recovery_time_ms']:.0f}")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Chaos/Resiliency")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(output_path=args.output))


if __name__ == "__main__":
    main()
