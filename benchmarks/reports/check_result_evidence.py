# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Validate benchmark result evidence quality for CI or release gating.

Usage:
    python benchmarks/reports/check_result_evidence.py
    python benchmarks/reports/check_result_evidence.py --results-dir benchmarks --min-evidence-score 75
    python benchmarks/reports/check_result_evidence.py --strict-manifest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from benchmarks.reports.generate_report import load_results
from benchmarks.reports.realism import (
    REQUIRED_MANIFEST_FIELDS,
    evaluate_evidence_gate,
    evaluate_manifest_completeness_gate,
    validate_manifest_completeness,
    validate_result_evidence,
)


DEFAULT_MANIFEST_PATH = Path(__file__).parent / "realism_manifest.json"


def _load_raw_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return raw if isinstance(raw, list) else []


def run_check(
    results_dir: Path,
    min_evidence_score: float,
    min_strong_ratio: float,
    max_low_evidence_sources: int,
    manifest_path: Path,
    strict_manifest: bool,
    min_completeness_ratio: float,
) -> dict[str, Any]:
    results, source_files = load_results(results_dir)
    evidence = validate_result_evidence(results, source_files)
    gate = evaluate_evidence_gate(
        evidence,
        min_evidence_score=min_evidence_score,
        min_strong_ratio=min_strong_ratio,
        max_low_evidence_sources=max_low_evidence_sources,
    )

    raw_manifest = _load_raw_manifest(manifest_path)
    completeness = validate_manifest_completeness(raw_manifest)
    manifest_gate = evaluate_manifest_completeness_gate(
        completeness,
        min_completeness_ratio=min_completeness_ratio,
        forbid_unknown_grades=True,
    )

    overall_passed = gate.get("passed", False)
    if strict_manifest:
        overall_passed = overall_passed and manifest_gate.get("passed", False)

    return {
        "results_dir": str(results_dir),
        "manifest_path": str(manifest_path),
        "loaded_sources": sorted(list(results.keys())),
        "evidence": evidence,
        "gate": gate,
        "manifest_completeness": completeness,
        "manifest_gate": manifest_gate,
        "strict_manifest": strict_manifest,
        "overall_passed": overall_passed,
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
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to realism_manifest.json",
    )
    parser.add_argument(
        "--strict-manifest",
        action="store_true",
        help=(
            "Fail when manifest entries are missing required evidence-grading fields "
            f"({', '.join(REQUIRED_MANIFEST_FIELDS)})."
        ),
    )
    parser.add_argument(
        "--min-completeness-ratio",
        type=float,
        default=1.0,
        help="Minimum manifest completeness ratio when --strict-manifest is set (default 1.0).",
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
        manifest_path=args.manifest,
        strict_manifest=args.strict_manifest,
        min_completeness_ratio=args.min_completeness_ratio,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = report["evidence"]
    gate = report["gate"]
    completeness = report["manifest_completeness"]
    manifest_gate = report["manifest_gate"]

    print("Benchmark Result Evidence Check")
    print("=" * 50)
    print(f"Loaded sources: {len(report['loaded_sources'])}")
    print(f"Evidence score avg: {evidence.get('evidence_score_avg', 0.0):.2f}")
    print(f"Strong evidence ratio: {evidence.get('strong_evidence_ratio', 0.0):.1%}")
    print(f"Low-evidence sources: {len(evidence.get('low_evidence_sources', []))}")
    print(f"Artifact gate: {'PASS' if gate.get('passed') else 'FAIL'}")
    if gate.get("reasons"):
        print("Artifact gate reasons:")
        for reason in gate["reasons"]:
            print(f" - {reason}")

    print("")
    print("Manifest Completeness")
    print("-" * 50)
    print(f"Entries: {completeness.get('total_entries', 0)}")
    print(f"Complete: {completeness.get('complete_entries', 0)}")
    print(f"Completeness ratio: {completeness.get('completeness_ratio', 0.0):.1%}")
    grade_counts = completeness.get("grade_counts", {})
    if grade_counts:
        grade_summary = ", ".join(f"{k}={v}" for k, v in sorted(grade_counts.items()))
        print(f"Grade distribution: {grade_summary}")
    if args.strict_manifest:
        print(f"Manifest gate (strict): {'PASS' if manifest_gate.get('passed') else 'FAIL'}")
        if manifest_gate.get("reasons"):
            print("Manifest gate reasons:")
            for reason in manifest_gate["reasons"]:
                print(f" - {reason}")
    else:
        print("Manifest gate: skipped (use --strict-manifest to enforce)")

    print("")
    print(f"Overall: {'PASS' if report['overall_passed'] else 'FAIL'}")

    return 0 if report["overall_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
