"""Benchmark CARF CLEAR Composite Score (H22).

Aggregates Cost, Latency, Efficacy, Alignment, and Robustness sub-scores
from existing benchmark result files into a single composite metric.

Each sub-score is normalized to [0, 1]:
  - Cost:       Lower LLM cost = higher score (from PRICE benchmark)
  - Latency:    P95 under threshold = higher score (from performance benchmark)
  - Efficacy:   Causal + Bayesian accuracy/coverage (from causal & bayesian benchmarks)
  - Alignment:  Governance MAP + RESOLVE + AUDIT compliance rates
  - Robustness: Guardian detection rate + determinism rate

Composite = weighted average with equal weights (0.2 each).

Metric:
  - clear_composite >= 0.75

Usage:
    python benchmarks/reports/benchmark_clear.py
    python benchmarks/reports/benchmark_clear.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.clear")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"

# ── Default sub-score when result files are missing ─────────────────────
_DEFAULT_SCORE = 0.5
_DEFAULT_NOTE = "Result file not found; using default score of 0.5"

# ── Cost normalisation constants ────────────────────────────────────────
# A "perfect" score maps to $0 cost; costs above this ceiling score 0.
_COST_CEILING_USD = 20.0  # $20 per 1M token round-trip is the ceiling


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning None if it does not exist."""
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s: %s", path, exc)
    return None


# ── Sub-score computations ──────────────────────────────────────────────

def _compute_cost_score(benchmarks_dir: Path) -> tuple[float, dict[str, Any]]:
    """Cost sub-score from the PRICE pillar in the governance benchmark.

    Lower cost = higher score.  Normalised linearly against _COST_CEILING_USD.
    """
    gov_path = benchmarks_dir / "technical" / "governance" / "benchmark_governance_results.json"
    data = _load_json(gov_path)
    if data is None:
        return _DEFAULT_SCORE, {"note": _DEFAULT_NOTE, "source": str(gov_path)}

    price = data.get("price", {})
    accuracy = price.get("accuracy", 0.0)

    # Use accuracy directly as cost efficiency proxy — 1.0 means all
    # cost computations are within tolerance, which implies efficient pricing.
    # If we have individual results, compute average actual cost for normalisation.
    individual = price.get("individual_results", [])
    if individual:
        avg_cost = sum(r.get("actual_cost", 0) for r in individual) / len(individual)
        cost_score = max(0.0, 1.0 - (avg_cost / _COST_CEILING_USD))
        # Blend with accuracy: 50% cost efficiency + 50% pricing accuracy
        score = 0.5 * cost_score + 0.5 * accuracy
    else:
        score = accuracy

    return min(1.0, max(0.0, score)), {
        "source": str(gov_path),
        "price_accuracy": accuracy,
        "individual_results_count": len(individual),
    }


def _compute_latency_score(benchmarks_dir: Path) -> tuple[float, dict[str, Any]]:
    """Latency sub-score from the performance benchmark.

    P95 latency under a threshold earns a high score.
    """
    perf_path = benchmarks_dir / "technical" / "performance" / "benchmark_latency_results.json"
    data = _load_json(perf_path)
    if data is None:
        return _DEFAULT_SCORE, {"note": _DEFAULT_NOTE, "source": str(perf_path)}

    p95_ms = data.get("p95_ms") or data.get("latency", {}).get("p95_ms")
    avg_ms = data.get("avg_duration_ms")

    # Also check governance node P95
    gov_path = benchmarks_dir / "technical" / "governance" / "benchmark_governance_results.json"
    gov_data = _load_json(gov_path)
    gov_p95 = None
    if gov_data:
        gov_p95 = gov_data.get("governance_p95_ms")

    details: dict[str, Any] = {"source": str(perf_path)}

    # Latency score: P95 < 2000ms => 1.0, P95 > 10000ms => 0.0, linear between
    if p95_ms is not None:
        score = max(0.0, min(1.0, 1.0 - (p95_ms - 2000) / 8000))
        details["p95_ms"] = p95_ms
    elif avg_ms is not None:
        score = max(0.0, min(1.0, 1.0 - (avg_ms - 1000) / 9000))
        details["avg_duration_ms"] = avg_ms
    else:
        score = _DEFAULT_SCORE
        details["note"] = "No latency metrics found in results"

    # Governance node latency bonus: P95 < 50ms adds up to 0.1
    if gov_p95 is not None:
        gov_bonus = 0.1 if gov_p95 < 50.0 else 0.0
        score = min(1.0, score + gov_bonus)
        details["governance_p95_ms"] = gov_p95
        details["governance_bonus"] = gov_bonus

    return score, details


def _compute_efficacy_score(benchmarks_dir: Path) -> tuple[float, dict[str, Any]]:
    """Efficacy sub-score from causal and Bayesian benchmarks.

    Combines causal ATE accuracy with Bayesian posterior coverage.
    """
    causal_path = benchmarks_dir / "technical" / "causal" / "benchmark_causal_results.json"
    bayesian_path = benchmarks_dir / "technical" / "bayesian" / "benchmark_bayesian_results.json"

    causal_data = _load_json(causal_path)
    bayesian_data = _load_json(bayesian_path)

    details: dict[str, Any] = {}
    scores: list[float] = []

    # Causal: use CI coverage rate as efficacy proxy
    if causal_data is not None:
        coverage_95 = (
            causal_data.get("aggregate", {}).get("ci_coverage_95")
            or causal_data.get("ci_coverage_95")
        )
        if coverage_95 is not None:
            scores.append(min(1.0, coverage_95))
            details["causal_ci_coverage_95"] = coverage_95
        else:
            # Fallback: use MSE-based score
            mse = (
                causal_data.get("mse")
                or causal_data.get("aggregate_metrics", {}).get("all", {}).get("mse")
                or causal_data.get("aggregate", {}).get("overall_mean_mse")
            )
            if mse is not None:
                # Lower MSE = better; MSE < 1 => score ~1.0, MSE > 10 => score ~0
                causal_score = max(0.0, min(1.0, 1.0 - mse / 10.0))
                scores.append(causal_score)
                details["causal_mse"] = mse
        details["causal_source"] = str(causal_path)
    else:
        scores.append(_DEFAULT_SCORE)
        details["causal_note"] = _DEFAULT_NOTE

    # Bayesian: posterior coverage rate
    if bayesian_data is not None:
        coverage = (
            bayesian_data.get("coverage")
            or bayesian_data.get("aggregate", {}).get("coverage_rate")
        )
        if coverage is not None:
            scores.append(min(1.0, coverage))
            details["bayesian_coverage"] = coverage
        else:
            scores.append(_DEFAULT_SCORE)
            details["bayesian_note"] = "No coverage metric in results"
        details["bayesian_source"] = str(bayesian_path)
    else:
        scores.append(_DEFAULT_SCORE)
        details["bayesian_note"] = _DEFAULT_NOTE

    efficacy = sum(scores) / len(scores) if scores else _DEFAULT_SCORE
    return efficacy, details


def _compute_alignment_score(benchmarks_dir: Path) -> tuple[float, dict[str, Any]]:
    """Alignment sub-score from governance MAP + RESOLVE + AUDIT pillars."""
    gov_path = benchmarks_dir / "technical" / "governance" / "benchmark_governance_results.json"
    data = _load_json(gov_path)
    if data is None:
        return _DEFAULT_SCORE, {"note": _DEFAULT_NOTE, "source": str(gov_path)}

    details: dict[str, Any] = {"source": str(gov_path)}
    scores: list[float] = []

    # MAP: cross-domain link accuracy
    map_acc = data.get("map_accuracy")
    if map_acc is not None:
        scores.append(min(1.0, map_acc))
        details["map_accuracy"] = map_acc

    # RESOLVE: conflict detection rate (penalise false positives)
    resolve = data.get("resolve", {})
    detection = resolve.get("conflict_detection_rate")
    fp_rate = resolve.get("false_positive_rate", 0.0)
    if detection is not None:
        resolve_score = detection * (1.0 - fp_rate)
        scores.append(min(1.0, resolve_score))
        details["resolve_detection_rate"] = detection
        details["resolve_false_positive_rate"] = fp_rate

    # AUDIT: compliance validity
    audit = data.get("audit", {})
    all_valid = audit.get("all_valid")
    avg_compliance = audit.get("avg_compliance_score")
    if all_valid is not None:
        audit_score = 1.0 if all_valid else 0.5
        if avg_compliance is not None:
            audit_score = (audit_score + avg_compliance) / 2.0
        scores.append(min(1.0, audit_score))
        details["audit_all_valid"] = all_valid
        details["audit_avg_compliance"] = avg_compliance

    alignment = sum(scores) / len(scores) if scores else _DEFAULT_SCORE
    return alignment, details


def _compute_robustness_score(benchmarks_dir: Path) -> tuple[float, dict[str, Any]]:
    """Robustness sub-score from Guardian detection + determinism rates."""
    guardian_path = benchmarks_dir / "technical" / "guardian" / "benchmark_guardian_results.json"
    data = _load_json(guardian_path)
    if data is None:
        return _DEFAULT_SCORE, {"note": _DEFAULT_NOTE, "source": str(guardian_path)}

    details: dict[str, Any] = {"source": str(guardian_path)}
    scores: list[float] = []

    detection = data.get("detection_rate")
    if detection is not None:
        scores.append(min(1.0, detection))
        details["detection_rate"] = detection

    determinism = data.get("determinism_rate")
    if determinism is not None:
        scores.append(min(1.0, determinism))
        details["determinism_rate"] = determinism

    # Also factor in false positive rate (lower = better)
    fp_rate = data.get("false_positive_rate", 0.0)
    fp_score = 1.0 - fp_rate
    scores.append(min(1.0, max(0.0, fp_score)))
    details["false_positive_rate"] = fp_rate

    robustness = sum(scores) / len(scores) if scores else _DEFAULT_SCORE
    return robustness, details


# ── Main benchmark ──────────────────────────────────────────────────────

WEIGHTS = {
    "cost": 0.2,
    "latency": 0.2,
    "efficacy": 0.2,
    "alignment": 0.2,
    "robustness": 0.2,
}


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Compute the CLEAR composite score."""
    logger.info("=" * 70)
    logger.info("CARF CLEAR Composite Benchmark (H22)")
    logger.info("=" * 70)

    benchmarks_dir = _PROJECT_ROOT / "benchmarks"

    # Compute each sub-score
    cost_score, cost_details = _compute_cost_score(benchmarks_dir)
    latency_score, latency_details = _compute_latency_score(benchmarks_dir)
    efficacy_score, efficacy_details = _compute_efficacy_score(benchmarks_dir)
    alignment_score, alignment_details = _compute_alignment_score(benchmarks_dir)
    robustness_score, robustness_details = _compute_robustness_score(benchmarks_dir)

    sub_scores = {
        "cost": round(cost_score, 4),
        "latency": round(latency_score, 4),
        "efficacy": round(efficacy_score, 4),
        "alignment": round(alignment_score, 4),
        "robustness": round(robustness_score, 4),
    }

    # Weighted average
    composite = sum(sub_scores[k] * WEIGHTS[k] for k in WEIGHTS)
    composite = round(composite, 4)

    logger.info("")
    for dimension, score in sub_scores.items():
        logger.info(f"  {dimension.upper():>12}: {score:.4f}  (weight {WEIGHTS[dimension]:.1f})")
    logger.info(f"  {'COMPOSITE':>12}: {composite:.4f}")
    logger.info(f"  {'THRESHOLD':>12}: 0.75")
    logger.info(f"  {'PASSED':>12}: {composite >= 0.75}")

    individual_results = [
        {"dimension": "cost", "score": sub_scores["cost"], "weight": WEIGHTS["cost"],
         "details": cost_details},
        {"dimension": "latency", "score": sub_scores["latency"], "weight": WEIGHTS["latency"],
         "details": latency_details},
        {"dimension": "efficacy", "score": sub_scores["efficacy"], "weight": WEIGHTS["efficacy"],
         "details": efficacy_details},
        {"dimension": "alignment", "score": sub_scores["alignment"], "weight": WEIGHTS["alignment"],
         "details": alignment_details},
        {"dimension": "robustness", "score": sub_scores["robustness"], "weight": WEIGHTS["robustness"],
         "details": robustness_details},
    ]

    report = {
        "benchmark": "carf_clear_composite",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "clear_composite": composite,
            "clear_composite_passed": composite >= 0.75,
            "sub_scores": sub_scores,
            "weights": WEIGHTS,
        },
        "individual_results": individual_results,
    }

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"CLEAR COMPOSITE: {composite:.4f}  {'PASS' if composite >= 0.75 else 'FAIL'}")
    logger.info("=" * 70)
    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(report, benchmark_id="clear", source_reference="benchmark:clear", benchmark_config={"script": __file__})


    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Results written to: {out}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark CARF CLEAR Composite Score")
    parser.add_argument(
        "-o", "--output",
        default=str(Path(__file__).parent / "benchmark_clear_results.json"),
    )
    args = parser.parse_args()
    run_benchmark(args.output)


if __name__ == "__main__":
    main()
