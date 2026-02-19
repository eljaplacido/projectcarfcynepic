"""Benchmark CARF end-to-end latency and memory usage.

Metrics:
  - Per-domain avg/p50/p95/p99 latency
  - CARF vs raw LLM latency ratio (H6)
  - Memory RSS growth over N queries (H9) with tracemalloc profiling
  - Concurrent request throughput

Usage:
    python benchmarks/technical/performance/benchmark_latency.py
    python benchmarks/technical/performance/benchmark_latency.py -o results.json
    python benchmarks/technical/performance/benchmark_latency.py --queries 100
    python benchmarks/technical/performance/benchmark_latency.py --concurrency 5
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
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.latency")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Data Helpers ─────────────────────────────────────────────────────────


def _build_causal_data(
    n: int, ate: float, base: float, noise: float, seed: int
) -> list[dict[str, float]]:
    """Build a simple causal dataset with confounded treatment assignment.

    Uses 200+ rows so DoWhy's backdoor estimator converges reliably.
    """
    rng = np.random.default_rng(seed)
    X1 = rng.normal(0, 1, n)
    X2 = rng.normal(0, 1, n)
    prop = 1 / (1 + np.exp(-(0.5 * X1 - 0.3 * X2)))
    T = rng.binomial(1, prop, n).astype(float)
    Y = base + ate * T + 1.5 * X1 + 0.5 * X2 + rng.normal(0, noise, n)
    return [
        {"treatment": float(T[i]), "outcome": round(float(Y[i]), 2),
         "X1": round(float(X1[i]), 4), "X2": round(float(X2[i]), 4)}
        for i in range(n)
    ]


# ── Sample Queries per Domain ────────────────────────────────────────────
# Complex queries include bayesian_inference context so the Active Inference
# Engine receives proper data and doesn't fail with "No data provided".
# This reflects realistic pipeline usage where context is always attached.

SAMPLE_QUERIES: dict[str, list[dict[str, Any]]] = {
    "Clear": [
        {"query": "What is the current USD to EUR exchange rate?"},
        {"query": "How many kilowatt-hours are in a megawatt-hour?"},
        {"query": "What is the standard VAT rate in Germany?"},
        {"query": "Convert 100 miles to kilometers"},
    ],
    "Complicated": [
        {"query": "How does increasing marketing spend affect quarterly revenue?",
         "context": {"industry": "marketing", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome", "covariates": ["X1", "X2"],
             "data": _build_causal_data(n=200, ate=150.0, base=500.0, noise=50.0, seed=10)}}},
        {"query": "What is the causal effect of employee training hours on productivity?",
         "context": {"industry": "hr", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome", "covariates": ["X1", "X2"],
             "data": _build_causal_data(n=200, ate=12.0, base=40.0, noise=5.0, seed=20)}}},
        {"query": "Does supplier diversification reduce supply chain disruption frequency?",
         "context": {"industry": "supply_chain", "causal_estimation": {
             "treatment": "treatment", "outcome": "outcome", "covariates": ["X1", "X2"],
             "data": _build_causal_data(n=200, ate=-2.0, base=5.0, noise=1.0, seed=30)}}},
    ],
    "Complex": [
        {"query": "Should we enter the Asian market given uncertain regulatory changes?",
         "context": {"industry": "fintech", "bayesian_inference": {
             "observations": np.round(np.random.default_rng(90).normal(0.08, 0.15, 30), 4).tolist()}}},
        {"query": "What strategy should we adopt for climate adaptation in agriculture?",
         "context": {"industry": "agriculture", "bayesian_inference": {
             "observations": np.round(np.random.default_rng(91).normal(4.5, 0.8, 25), 4).tolist()}}},
        {"query": "How should we allocate R&D budget under technological uncertainty?",
         "context": {"industry": "technology", "bayesian_inference": {
             "observations": np.round(np.random.default_rng(92).normal(0.12, 0.05, 20), 4).tolist()}}},
    ],
    "Chaotic": [
        {"query": "CRITICAL: Fraud detected in 3 regions simultaneously, losses mounting"},
        {"query": "URGENT: Infrastructure cascade failure across primary data centers"},
    ],
    "Disorder": [
        {"query": "Do something about the thing with the stuff"},
        {"query": "Maybe we should or maybe not, what do you think about everything?"},
    ],
}


def get_rss_mb() -> float:
    """Get current RSS in MB (cross-platform)."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def _clear_caches() -> None:
    """Clear LRU caches and run garbage collection to prevent memory accumulation."""
    try:
        from src.core.llm import get_chat_model
        get_chat_model.cache_clear()
    except Exception:
        pass
    gc.collect()


async def measure_single_query(
    query: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run a single CARF pipeline query and measure latency."""
    from src.workflows.graph import run_carf

    t0 = time.perf_counter()
    try:
        final_state = await run_carf(user_input=query, context=context or {})
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "query": query[:80],
            "domain": final_state.cynefin_domain.value,
            "latency_ms": round(elapsed_ms, 2),
            "confidence": round(final_state.domain_confidence, 4),
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "query": query[:80],
            "domain": "ERROR",
            "latency_ms": round(elapsed_ms, 2),
            "confidence": 0.0,
            "error": str(exc),
        }


async def _run_concurrent_batch(
    batch: list[tuple[str, dict[str, Any] | None]],
) -> list[dict[str, Any]]:
    """Run a batch of queries concurrently and return results."""
    tasks = [measure_single_query(q, ctx) for q, ctx in batch]
    return await asyncio.gather(*tasks)


async def run_benchmark(
    n_queries: int = 50,
    output_path: str | None = None,
    concurrency: int = 1,
) -> dict[str, Any]:
    """Run latency, memory, and throughput benchmarks."""
    logger.info(f"CARF Performance Benchmark ({n_queries} queries, concurrency={concurrency})")

    # Build query list (cycle through domains)
    queries: list[tuple[str, str, dict[str, Any] | None]] = []
    for domain, domain_items in SAMPLE_QUERIES.items():
        per_domain = max(1, n_queries // len(SAMPLE_QUERIES))
        for i in range(per_domain):
            item = domain_items[i % len(domain_items)]
            queries.append((domain, item["query"], item.get("context")))
    queries = queries[:n_queries]

    # Start tracemalloc for detailed memory profiling
    tracemalloc.start()
    rss_before = get_rss_mb()
    tm_start_current, tm_start_peak = tracemalloc.get_traced_memory()

    results: list[dict] = []
    domain_latencies: dict[str, list[float]] = {}
    memory_snapshots: list[dict] = []

    for i, (expected_domain, query, context) in enumerate(queries, 1):
        res = await measure_single_query(query, context)
        results.append(res)

        actual_domain = res["domain"]
        domain_latencies.setdefault(actual_domain, []).append(res["latency_ms"])

        # Record memory snapshot every 5 queries for growth curve analysis
        if i % 5 == 0:
            tm_current, tm_peak = tracemalloc.get_traced_memory()
            memory_snapshots.append({
                "query_index": i,
                "rss_mb": round(get_rss_mb(), 2),
                "tracemalloc_current_mb": round(tm_current / (1024 * 1024), 2),
                "tracemalloc_peak_mb": round(tm_peak / (1024 * 1024), 2),
            })

        # Clear caches every 10 iterations to prevent LRU accumulation
        if i % 10 == 0:
            _clear_caches()
            logger.info(f"  Progress: {i}/{len(queries)}")

    rss_after = get_rss_mb()
    tm_end_current, tm_end_peak = tracemalloc.get_traced_memory()

    # Top memory allocators (useful for debugging memory growth)
    top_stats = tracemalloc.take_snapshot().statistics("lineno")[:10]
    top_allocators = [
        {"file": str(s.traceback), "size_kb": round(s.size / 1024, 1)} for s in top_stats
    ]
    tracemalloc.stop()

    memory_growth_pct = ((rss_after - rss_before) / max(rss_before, 1)) * 100

    # Concurrent throughput test (if concurrency > 1)
    throughput_stats: dict[str, Any] = {}
    if concurrency > 1 and len(queries) >= concurrency:
        logger.info(f"\n  Running throughput test (concurrency={concurrency})...")
        batch = [(q, ctx) for _, q, ctx in queries[:concurrency]]
        t0 = time.perf_counter()
        concurrent_results = await _run_concurrent_batch(batch)
        elapsed = time.perf_counter() - t0
        success_count = sum(1 for r in concurrent_results if r["error"] is None)
        throughput_stats = {
            "concurrency": concurrency,
            "batch_size": len(batch),
            "wall_time_s": round(elapsed, 2),
            "successful": success_count,
            "throughput_qps": round(success_count / max(elapsed, 0.001), 2),
        }
        logger.info(f"  Throughput: {throughput_stats['throughput_qps']:.1f} queries/sec")

    # Compute latency stats
    all_latencies = [r["latency_ms"] for r in results if r["error"] is None]
    lat_arr = np.array(all_latencies) if all_latencies else np.array([0.0])

    per_domain_stats = {}
    for domain, lats in domain_latencies.items():
        arr = np.array(lats)
        per_domain_stats[domain] = {
            "count": len(lats),
            "mean_ms": round(float(arr.mean()), 2),
            "median_ms": round(float(np.median(arr)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
        }

    report = {
        "benchmark": "carf_performance",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_queries": len(queries),
        "successful": len(all_latencies),
        "error_count": len(results) - len(all_latencies),
        "avg_duration_ms": round(float(lat_arr.mean()), 2),
        "median_duration_ms": round(float(np.median(lat_arr)), 2),
        "p95_duration_ms": round(float(np.percentile(lat_arr, 95)), 2),
        "p99_duration_ms": round(float(np.percentile(lat_arr, 99)), 2),
        "per_domain": per_domain_stats,
        "memory": {
            "rss_before_mb": round(rss_before, 2),
            "rss_after_mb": round(rss_after, 2),
            "memory_growth_pct": round(memory_growth_pct, 2),
            "tracemalloc_peak_mb": round(tm_end_peak / (1024 * 1024), 2),
            "top_allocators": top_allocators,
            "snapshots": memory_snapshots,
        },
        "memory_growth_pct": round(memory_growth_pct, 2),
        "throughput": throughput_stats,
        "individual_results": results,
    }

    logger.info(f"\n  Avg Latency:   {report['avg_duration_ms']:.0f}ms")
    logger.info(f"  P95 Latency:   {report['p95_duration_ms']:.0f}ms")
    logger.info(f"  Memory Growth: {memory_growth_pct:.1f}%")
    logger.info(f"  Errors:        {report['error_count']}/{report['total_queries']}")
    for d, stats in per_domain_stats.items():
        logger.info(f"    {d:<14} {stats['count']:>3} queries, mean={stats['mean_ms']:.0f}ms, p95={stats['p95_ms']:.0f}ms")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info(f"Results: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF Performance")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument(
        "--concurrency", type=int, default=1,
        help="Number of concurrent queries for throughput test",
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(
        n_queries=args.queries, output_path=args.output, concurrency=args.concurrency
    ))


if __name__ == "__main__":
    main()
