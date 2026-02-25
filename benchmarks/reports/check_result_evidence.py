# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Validate benchmark result evidence quality for CI or release gating.

Usage:
    python benchmarks/reports/check_result_evidence.py
    python benchmarks/reports/check_result_evidence.py --results-dir benchmarks --min-evidence-score 75
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from benchmarks.reports.generate_report import load_results
from benchmarks.reports.realism import evaluate_evidence_gate, validate_result_evidence


def run_check(
    results_dir: Path,
    min_evidence_score: float,
    min_strong_ratio: float,
    max_low_evidence_sources: int,
) -> dict[str, Any]:
    results, source_files = load_results(results_dir)
    evidence = validate_result_evidence(results, source_files)
    gate = evaluate_evidence_gate(
        evidence,
        min_evidence_score=min_evidence_score,
        min_strong_ratio=min_strong_ratio,
        max_low_evidence_sources=max_low_evidence_sources,
    )
    return {
        "results_dir": str(results_dir),
        "loaded_sources": sorted(list(results.keys())),
        "evidence": evidence,
        "gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check benchmark result evidence quality gate")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Root directory containing benchmark result files",
    )
    parser.add_argument(
        "--min-evidence-score",
        type=float,
        default=70.0,
        help="Minimum average evidence score (0-100)",
    )
    parser.add_argument(
        "--min-strong-ratio",
        type=float,
        default=0.8,
        help="Minimum ratio of strong-evidence result sources (0-1)",
    )
    parser.add_argument(
        "--max-low-evidence-sources",
        type=int,
        default=0,
        help="Maximum allowed number of low-evidence result sources",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file path",
    )
    args = parser.parse_args()

    report = run_check(
        results_dir=args.results_dir,
        min_evidence_score=args.min_evidence_score,
        min_strong_ratio=args.min_strong_ratio,
        max_low_evidence_sources=args.max_low_evidence_sources,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = report["evidence"]
    gate = report["gate"]
    print("Benchmark Result Evidence Check")
    print("=" * 50)
    print(f"Loaded sources: {len(report['loaded_sources'])}")
    print(f"Evidence score avg: {evidence.get('evidence_score_avg', 0.0):.2f}")
    print(f"Strong evidence ratio: {evidence.get('strong_evidence_ratio', 0.0):.1%}")
    print(f"Low-evidence sources: {len(evidence.get('low_evidence_sources', []))}")
    print(f"Gate: {'PASS' if gate.get('passed') else 'FAIL'}")
    if gate.get("reasons"):
        print("Reasons:")
        for reason in gate["reasons"]:
            print(f" - {reason}")

    return 0 if gate.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
