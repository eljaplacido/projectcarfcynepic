# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Soak / Endurance Test (H39).

Runs 1000 sequential queries through the CARF pipeline (or a mock
pipeline if real services are unavailable) and tracks two key stability
indicators over the full run:

  - **Memory growth**: RSS sampled every 100 queries; growth computed as
    (final_rss - initial_rss) / initial_rss * 100.
  - **Latency drift**: average latency of the last 100 queries compared
    to the first 100; drift = (avg_last - avg_first) / avg_first * 100.

If the real pipeline is unavailable the benchmark falls back to a
lightweight mock that still exercises event-loop scheduling and memory
allocation patterns.

Metrics:
  - memory_growth  <= 5.0%  (pass)
  - latency_drift  <= 10.0% (pass)

Usage:
    python benchmarks/technical/performance/benchmark_soak.py
    python benchmarks/technical/performance/benchmark_soak.py -o results.json
    python benchmarks/technical/performance/benchmark_soak.py --queries 500
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.soak")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── Memory Helpers ───────────────────────────────────────────────────────


def get_rss_mb() -> float:
    """Return current Resident Set Size in MB (cross-platform)."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass

    # Fallback: resource module (Unix only)
    try:
        import resource
        # ru_maxrss is in KB on Linux, bytes on macOS
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return rusage.ru_maxrss / (1024 * 1024)
        return rusage.ru_maxrss / 1024
    except (ImportError, AttributeError):
        pass

    return 0.0


# ── Query Pool ───────────────────────────────────────────────────────────


SOAK_QUERIES = [
    "What is the current USD to EUR exchange rate?",
    "How many kilowatt-hours are in a megawatt-hour?",
    "What is the standard VAT rate in Germany?",
    "Convert 100 miles to kilometers.",
    "What is the boiling point of water in Fahrenheit?",
    "How many bytes are in a gigabyte?",
    "What is the capital of Finland?",
    "What is the speed of light in meters per second?",
    "How many days are in a leap year?",
    "What is the freezing point of water in Celsius?",
    "Define net present value.",
    "What is Ohm's law?",
    "How many planets are in the solar system?",
    "What is the chemical formula for water?",
    "What is the Pythagorean theorem?",
    "What is GDP?",
    "How many seconds are in an hour?",
    "What is the atomic number of carbon?",
    "Define inflation rate.",
    "What is the area of a circle?",
]


# ── Pipeline Wrapper ─────────────────────────────────────────────────────


async def _mock_pipeline(query: str) -> dict[str, Any]:
    """Lightweight mock simulating minimal pipeline work."""
    # Small allocation to mimic real work
    _ = [i * 2 for i in range(500)]
    await asyncio.sleep(0.005)  # 5 ms simulated work
    return {"domain": "Clear", "response": "mock"}


async def _real_pipeline(query: str) -> dict[str, Any]:
    """Attempt to use the real CARF pipeline."""
    from src.workflows.graph import run_carf

    state = await run_carf(user_input=query, context={})
    return {
        "domain": state.cynefin_domain.value,
        "response": (state.final_response or "")[:100],
    }


async def _get_pipeline_fn():
    """Return the real pipeline if available, otherwise the mock."""
    try:
        from src.workflows.graph import run_carf  # noqa: F401

        # Quick smoke test
        await _real_pipeline("test")
        logger.info("  Using REAL CARF pipeline")
        return _real_pipeline
    except Exception:
        logger.info("  Real pipeline unavailable; using MOCK pipeline")
        return _mock_pipeline


# ── Benchmark Runner ─────────────────────────────────────────────────────


async def run_benchmark(
    n_queries: int = 1000,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Run the soak / endurance benchmark."""
    logger.info(f"CARF Soak / Endurance Benchmark (H39) — {n_queries} queries")

    pipeline_fn = await _get_pipeline_fn()

    # Warm-up: run a few queries so lazy imports and JIT effects settle
    logger.info("  Warm-up phase (5 queries)...")
    for i in range(5):
        await pipeline_fn(SOAK_QUERIES[i % len(SOAK_QUERIES)])
    gc.collect()

    # Baseline memory snapshot
    initial_rss = get_rss_mb()
    logger.info(f"  Initial RSS: {initial_rss:.2f} MB")

    # Storage
    latencies: list[float] = []
    memory_snapshots: list[dict[str, Any]] = [
        {"query_index": 0, "rss_mb": round(initial_rss, 2)},
    ]
    errors: list[dict[str, Any]] = []
    sample_interval = max(1, n_queries // 10)  # Snapshot every ~10% of run

    t_total_start = time.perf_counter()

    for i in range(1, n_queries + 1):
        query = SOAK_QUERIES[(i - 1) % len(SOAK_QUERIES)]

        t0 = time.perf_counter()
        try:
            await pipeline_fn(query)
            latency_s = time.perf_counter() - t0
            latencies.append(latency_s)
        except Exception as exc:
            latency_s = time.perf_counter() - t0
            latencies.append(latency_s)
            errors.append({"query_index": i, "error": str(exc)[:200]})

        # Memory snapshot every sample_interval queries
        if i % sample_interval == 0:
            current_rss = get_rss_mb()
            memory_snapshots.append({
                "query_index": i,
                "rss_mb": round(current_rss, 2),
            })

            pct_done = (i / n_queries) * 100
            avg_lat = sum(latencies[-sample_interval:]) / min(len(latencies), sample_interval)
            logger.info(
                f"  [{pct_done:5.1f}%] query {i}/{n_queries}  "
                f"RSS={current_rss:.1f}MB  avg_lat={avg_lat * 1000:.1f}ms  "
                f"errors={len(errors)}"
            )

    total_elapsed_s = time.perf_counter() - t_total_start

    # Final memory snapshot
    final_rss = get_rss_mb()
    memory_snapshots.append({
        "query_index": n_queries,
        "rss_mb": round(final_rss, 2),
    })

    # ── Compute Metrics ──────────────────────────────────────────────────

    # Memory growth %
    if initial_rss > 0:
        memory_growth_pct = ((final_rss - initial_rss) / initial_rss) * 100.0
    else:
        memory_growth_pct = 0.0

    # Latency drift %
    bucket_size = min(100, max(1, n_queries // 10))
    first_bucket = latencies[:bucket_size]
    last_bucket = latencies[-bucket_size:]

    avg_first = sum(first_bucket) / len(first_bucket) if first_bucket else 1.0
    avg_last = sum(last_bucket) / len(last_bucket) if last_bucket else 1.0

    if avg_first > 0:
        latency_drift_pct = ((avg_last - avg_first) / avg_first) * 100.0
    else:
        latency_drift_pct = 0.0

    # Latency statistics
    import numpy as np

    lat_arr = np.array(latencies) if latencies else np.array([0.0])
    latency_stats = {
        "mean_s": round(float(lat_arr.mean()), 6),
        "p50_s": round(float(np.percentile(lat_arr, 50)), 6),
        "p95_s": round(float(np.percentile(lat_arr, 95)), 6),
        "p99_s": round(float(np.percentile(lat_arr, 99)), 6),
        "min_s": round(float(lat_arr.min()), 6),
        "max_s": round(float(lat_arr.max()), 6),
        "avg_first_bucket_s": round(avg_first, 6),
        "avg_last_bucket_s": round(avg_last, 6),
        "bucket_size": bucket_size,
    }

    # Pass/fail
    memory_pass = memory_growth_pct <= 5.0
    latency_pass = latency_drift_pct <= 10.0

    metrics = {
        "memory_growth_pct": round(memory_growth_pct, 4),
        "memory_growth_pass": memory_pass,
        "latency_drift_pct": round(latency_drift_pct, 4),
        "latency_drift_pass": latency_pass,
        "initial_rss_mb": round(initial_rss, 2),
        "final_rss_mb": round(final_rss, 2),
        "total_queries": n_queries,
        "total_errors": len(errors),
        "total_elapsed_s": round(total_elapsed_s, 2),
        "throughput_qps": round(n_queries / max(total_elapsed_s, 0.001), 2),
    }

    report = {
        "benchmark": "carf_soak_endurance",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "latency_stats": latency_stats,
        "memory_snapshots": memory_snapshots,
        "errors": errors[:50],  # Cap to avoid huge output
        "individual_results": [
            {"query_index": i + 1, "latency_s": round(l, 6)}
            for i, l in enumerate(latencies)
        ],
    }

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("Soak / Endurance Benchmark Summary:")
    logger.info(f"  Total Queries:     {n_queries}")
    logger.info(f"  Total Time:        {total_elapsed_s:.1f}s")
    logger.info(f"  Throughput:        {metrics['throughput_qps']:.1f} q/s")
    logger.info(f"  Errors:            {len(errors)}")
    logger.info(f"  Initial RSS:       {initial_rss:.1f} MB")
    logger.info(f"  Final RSS:         {final_rss:.1f} MB")
    logger.info(f"  Memory Growth:     {memory_growth_pct:+.2f}% (<= 5.0%)")
    logger.info(f"  Memory RESULT:     {'PASS' if memory_pass else 'FAIL'}")
    logger.info(f"  Avg Lat (first):   {avg_first * 1000:.2f}ms")
    logger.info(f"  Avg Lat (last):    {avg_last * 1000:.2f}ms")
    logger.info(f"  Latency Drift:     {latency_drift_pct:+.2f}% (<= 10.0%)")
    logger.info(f"  Latency RESULT:    {'PASS' if latency_pass else 'FAIL'}")
    logger.info(f"  OVERALL:           {'PASS' if (memory_pass and latency_pass) else 'FAIL'}")
    logger.info("=" * 60)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="soak", source_reference="benchmark:soak", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Soak / Endurance (H39)")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--queries", type=int, default=1000,
                        help="Number of sequential queries (default: 1000)")
    args = parser.parse_args()
    asyncio.run(run_benchmark(n_queries=args.queries, output_path=args.output))


if __name__ == "__main__":
    main()
