"""Benchmark the CARF Cynefin Router against a labeled test set.

Evaluates classification accuracy, weighted F1, confusion matrix,
per-domain accuracy, Expected Calibration Error (ECE), and latency.

Usage:
    python benchmarks/technical/router/benchmark_router.py
    python benchmarks/technical/router/benchmark_router.py --max-queries 50
    python benchmarks/technical/router/benchmark_router.py --balanced --max-queries 100
    python benchmarks/technical/router/benchmark_router.py --domain complicated
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.router")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

DOMAIN_LABELS = ["Clear", "Complicated", "Complex", "Chaotic", "Disorder"]


def load_test_set(
    path: Path,
    max_queries: int | None = None,
    balanced: bool = False,
    domain_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load a JSONL test set with optional balanced sampling or domain filtering.

    Args:
        path: Path to the JSONL test set.
        max_queries: Maximum total queries to return.
        balanced: If True, sample equal queries per domain (prevents bias
                  toward over-represented domains when using --max-queries).
        domain_filter: If set, only include queries from this domain.
    """
    all_entries: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if "query" in entry and "domain" in entry:
                all_entries.append(entry)

    # Optional domain filter
    if domain_filter:
        norm = domain_filter.strip().lower()
        all_entries = [e for e in all_entries if e["domain"].strip().lower() == norm]

    # Balanced sampling: equal queries per domain
    if balanced and max_queries:
        domain_buckets: dict[str, list[dict]] = defaultdict(list)
        for e in all_entries:
            domain_buckets[normalize_domain(e["domain"])].append(e)
        n_domains = len(domain_buckets) or 1
        per_domain = max(1, max_queries // n_domains)
        entries: list[dict[str, Any]] = []
        for domain in DOMAIN_LABELS:
            bucket = domain_buckets.get(domain, [])
            entries.extend(bucket[:per_domain])
        return entries[:max_queries]

    if max_queries:
        all_entries = all_entries[:max_queries]
    return all_entries


def normalize_domain(label: str) -> str:
    """Normalize domain label to title-case."""
    mapping = {d.lower(): d for d in DOMAIN_LABELS}
    return mapping.get(label.strip().lower(), label.strip().title())


def compute_ece(
    confidences: list[float], accuracies: list[bool], n_bins: int = 10
) -> tuple[float, list[dict]]:
    """Compute Expected Calibration Error."""
    import numpy as np

    if not confidences:
        return 0.0, []

    conf_arr = np.array(confidences, dtype=np.float64)
    acc_arr = np.array(accuracies, dtype=np.float64)
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)

    ece = 0.0
    total = len(conf_arr)
    bin_stats: list[dict] = []

    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (conf_arr >= lo) & (conf_arr <= hi if i == n_bins - 1 else conf_arr < hi)
        bin_count = int(mask.sum())
        if bin_count == 0:
            bin_stats.append({"bin": f"[{lo:.1f}, {hi:.1f})", "count": 0})
            continue
        mean_conf = float(conf_arr[mask].mean())
        mean_acc = float(acc_arr[mask].mean())
        gap = abs(mean_acc - mean_conf)
        ece += (bin_count / total) * gap
        bin_stats.append({
            "bin": f"[{lo:.1f}, {hi:.1f})",
            "count": bin_count,
            "mean_confidence": round(mean_conf, 4),
            "mean_accuracy": round(mean_acc, 4),
            "gap": round(gap, 4),
        })

    return round(float(ece), 6), bin_stats


async def run_single_query(query: str, ground_truth: str, index: int, total: int) -> dict:
    """Route a single query and record the result."""
    from src.core.state import EpistemicState
    from src.workflows.router import cynefin_router_node

    result: dict[str, Any] = {
        "query": query,
        "ground_truth": ground_truth,
        "predicted": None,
        "confidence": 0.0,
        "correct": False,
        "latency_ms": 0.0,
        "error": None,
    }

    try:
        state = EpistemicState(user_input=query)
        t0 = time.perf_counter()
        updated = await cynefin_router_node(state)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        predicted = updated.cynefin_domain.value
        result["predicted"] = predicted
        result["confidence"] = round(updated.domain_confidence, 4)
        result["correct"] = normalize_domain(predicted) == normalize_domain(ground_truth)
        result["latency_ms"] = round(elapsed_ms, 2)
    except Exception as exc:
        result["error"] = str(exc)
        result["predicted"] = "ERROR"

    status = "OK" if result["correct"] else ("ERR" if result["error"] else "MISS")
    logger.info(
        f"  [{index:>4}/{total}] {status}  pred={str(result['predicted']):<14} "
        f"true={ground_truth:<14} conf={result['confidence']:.2f}  "
        f"latency={result['latency_ms']:>8.1f}ms"
    )
    return result


async def run_benchmark(
    test_set_path: Path,
    output_path: Path,
    max_queries: int | None = None,
    balanced: bool = False,
    domain_filter: str | None = None,
) -> dict[str, Any]:
    """Execute the full router benchmark."""
    import numpy as np
    from sklearn.metrics import confusion_matrix, f1_score

    entries = load_test_set(test_set_path, max_queries, balanced, domain_filter)
    total = len(entries)
    if total == 0:
        logger.error("No test entries loaded — check test set path and filters.")
        return {"error": "no_entries"}
    logger.info(f"Router Benchmark: {total} queries from {test_set_path}")

    results: list[dict] = []
    for idx, entry in enumerate(entries, start=1):
        res = await run_single_query(
            entry["query"], normalize_domain(entry["domain"]), idx, total
        )
        results.append(res)

    y_true = [normalize_domain(r["ground_truth"]) for r in results]
    y_pred = [normalize_domain(r["predicted"]) if r["predicted"] != "ERROR" else "ERROR" for r in results]
    correct_flags = [r["correct"] for r in results]
    confidences = [r["confidence"] for r in results]
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]

    overall_accuracy = round(sum(correct_flags) / len(correct_flags), 4) if correct_flags else 0.0
    all_labels = sorted(set(y_true) | set(y_pred))
    weighted_f1 = round(float(f1_score(y_true, y_pred, labels=all_labels, average="weighted", zero_division=0)), 4)

    cm_labels = sorted(set(DOMAIN_LABELS) | set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=cm_labels)

    per_domain: dict[str, dict] = {}
    domain_groups: dict[str, list[bool]] = defaultdict(list)
    domain_latencies: dict[str, list[float]] = defaultdict(list)
    for r, true_label, is_correct in zip(results, y_true, correct_flags):
        domain_groups[true_label].append(is_correct)
        if r["latency_ms"] > 0:
            domain_latencies[true_label].append(r["latency_ms"])
    for domain in DOMAIN_LABELS:
        group = domain_groups.get(domain, [])
        d_lats = domain_latencies.get(domain, [])
        d_arr = np.array(d_lats) if d_lats else np.array([0.0])
        per_domain[domain] = {
            "count": len(group),
            "correct": sum(group),
            "accuracy": round(sum(group) / len(group), 4) if group else None,
            "latency": {
                "mean_ms": round(float(d_arr.mean()), 2),
                "median_ms": round(float(np.median(d_arr)), 2),
                "p95_ms": round(float(np.percentile(d_arr, 95)), 2),
            } if d_lats else None,
        }

    ece_value, ece_bins = compute_ece(confidences, correct_flags)

    lat_arr = np.array(latencies) if latencies else np.array([0.0])
    latency_stats = {
        "mean_ms": round(float(lat_arr.mean()), 2),
        "median_ms": round(float(np.median(lat_arr)), 2),
        "p95_ms": round(float(np.percentile(lat_arr, 95)), 2),
        "p99_ms": round(float(np.percentile(lat_arr, 99)), 2),
    } if latencies else {}

    output: dict[str, Any] = {
        "benchmark": "cynefin_router",
        "total_queries": total,
        "error_count": sum(1 for r in results if r["error"]),
        "overall_accuracy": overall_accuracy,
        "weighted_f1": weighted_f1,
        "expected_calibration_error": ece_value,
        "ece_bins": ece_bins,
        "per_domain_accuracy": per_domain,
        "confusion_matrix": {"labels": cm_labels, "matrix": cm.tolist()},
        "latency": latency_stats,
        "individual_results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2, default=str)

    logger.info(f"\nResults: {output_path}")
    logger.info(f"Accuracy: {overall_accuracy:.4f} | F1: {weighted_f1:.4f} | ECE: {ece_value:.6f}")
    for d in DOMAIN_LABELS:
        info = per_domain[d]
        acc = f"{info['accuracy']:.4f}" if info["accuracy"] is not None else "N/A"
        logger.info(f"  {d:<14} {info['count']:>4} queries, accuracy={acc}")

    return output


def main():
    default_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Benchmark CARF Cynefin Router")
    parser.add_argument("--test-set", type=Path, default=default_dir / "test_set.jsonl")
    parser.add_argument("--output", type=Path, default=default_dir / "benchmark_router_results.json")
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument(
        "--balanced", action="store_true",
        help="Sample equal queries per domain (prevents bias toward over-represented domains)",
    )
    parser.add_argument(
        "--domain", type=str, default=None,
        help="Filter to a single Cynefin domain (clear, complicated, complex, chaotic, disorder)",
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(
        args.test_set, args.output, args.max_queries, args.balanced, args.domain
    ))


if __name__ == "__main__":
    main()
