# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark realism, reliability, and feasibility validation helpers.

This module adds a second quality layer on top of hypothesis pass/fail:
1. Realism: how closely benchmark datasets mirror production complexity
2. Reliability: reproducibility + baseline comparability + stress rigor
3. Feasibility: practical run cost and automation maturity
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BenchmarkRealismSpec(BaseModel):
    """Validation spec for one benchmark result source."""

    benchmark_id: str = Field(..., description="Key used by generate_report.py result loading")
    category: str = Field(..., description="Benchmark category, e.g. core, security, ux")
    dataset_profile: str = Field(
        ...,
        pattern="^(synthetic|hybrid|real)$",
        description="Data origin profile",
    )
    rows: int = Field(..., ge=1, description="Typical number of rows/samples used")
    scenarios: int = Field(..., ge=1, description="Number of distinct benchmark scenarios/cases")
    temporal_slices: int = Field(1, ge=1, description="Distinct time windows or temporal partitions")
    stress_levels: int = Field(1, ge=1, description="Distinct stress/load levels tested")
    adversarial_cases: int = Field(0, ge=0, description="Count of adversarial/red-team cases")
    confounding_strength: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Expected confounding realism in data generation",
    )
    missingness_coverage: bool = Field(
        False, description="Whether missing/noisy data behavior is exercised"
    )
    label_noise_coverage: bool = Field(
        False, description="Whether label/output noise is explicitly tested"
    )
    seed_reproducible: bool = Field(
        True, description="Whether benchmark is deterministic under controlled seed(s)"
    )
    baseline_comparator: bool = Field(
        True, description="Whether raw/baseline comparator exists for contextual scoring"
    )
    production_proxy_validated: bool = Field(
        False,
        description="Whether data assumptions were calibrated against production-like patterns",
    )
    runtime_budget_minutes: int = Field(
        60, ge=1, description="Expected runtime budget for routine validation execution"
    )
    automated_run: bool = Field(
        True, description="Whether benchmark is automatable in CI/nightly workflows"
    )
    source_reference: str = Field(
        "", description="Dataset/protocol provenance note"
    )


class ResultEvidenceSignals(BaseModel):
    """Evidence quality signals extracted from a benchmark result artifact."""

    benchmark_id: str
    file_path: str = ""
    has_timestamp: bool = False
    has_config: bool = False
    has_dataset_context: bool = False
    has_sample_context: bool = False
    has_provenance: bool = False
    evidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    missing_signals: list[str] = Field(default_factory=list)


def _collect_key_paths(payload: Any, prefix: str = "") -> list[str]:
    """Collect flattened key paths from nested dict/list payloads."""
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_name = str(key).lower()
            path = f"{prefix}.{key_name}" if prefix else key_name
            paths.append(path)
            paths.extend(_collect_key_paths(value, path))
    elif isinstance(payload, list):
        for item in payload:
            paths.extend(_collect_key_paths(item, prefix))
    return paths


def validate_result_evidence(
    results: dict[str, Any],
    result_files: dict[str, str],
) -> dict[str, Any]:
    """Assess whether loaded result artifacts contain provenance-grade evidence."""
    entries: list[ResultEvidenceSignals] = []
    timestamp_tokens = ("timestamp", "generated_at", "created_at", "completed_at", "updated_at")
    config_tokens = ("config", "params", "settings", "benchmark_config", "runtime")
    dataset_tokens = ("dataset", "data_source", "data_profile", "domain_path", "input_schema")
    sample_tokens = ("rows", "samples", "scenarios", "queries", "cases", "n_", "count", "records")
    provenance_tokens = (
        "source_reference",
        "provenance",
        "dataset_version",
        "lineage",
        "source_url",
        "benchmark_id",
        "methodology",
    )

    for benchmark_id, payload in results.items():
        key_paths = _collect_key_paths(payload)
        has_timestamp = any(any(token in kp for token in timestamp_tokens) for kp in key_paths)
        has_config = any(any(token in kp for token in config_tokens) for kp in key_paths)
        has_dataset_context = any(any(token in kp for token in dataset_tokens) for kp in key_paths)
        has_sample_context = any(any(token in kp for token in sample_tokens) for kp in key_paths)
        has_provenance = any(any(token in kp for token in provenance_tokens) for kp in key_paths)

        missing_signals = []
        if not has_timestamp:
            missing_signals.append("timestamp")
        if not has_config:
            missing_signals.append("config")
        if not has_dataset_context:
            missing_signals.append("dataset_context")
        if not has_sample_context:
            missing_signals.append("sample_context")
        if not has_provenance:
            missing_signals.append("provenance")

        score = 0.0
        score += 20.0 if has_timestamp else 0.0
        score += 20.0 if has_config else 0.0
        score += 20.0 if has_dataset_context else 0.0
        score += 20.0 if has_sample_context else 0.0
        score += 20.0 if has_provenance else 0.0

        entries.append(
            ResultEvidenceSignals(
                benchmark_id=benchmark_id,
                file_path=result_files.get(benchmark_id, ""),
                has_timestamp=has_timestamp,
                has_config=has_config,
                has_dataset_context=has_dataset_context,
                has_sample_context=has_sample_context,
                has_provenance=has_provenance,
                evidence_score=round(score, 2),
                missing_signals=missing_signals,
            )
        )

    evidence_score_avg = round(
        sum(e.evidence_score for e in entries) / max(len(entries), 1),
        2,
    )
    strong_evidence_ratio = round(
        sum(1 for e in entries if e.evidence_score >= 70.0) / max(len(entries), 1),
        3,
    )
    low_evidence_sources = sorted([e.benchmark_id for e in entries if e.evidence_score < 70.0])

    return {
        "status": "ok",
        "evidence_score_avg": evidence_score_avg,
        "strong_evidence_ratio": strong_evidence_ratio,
        "low_evidence_sources": low_evidence_sources,
        "entries": [e.model_dump() for e in entries],
    }


def evaluate_evidence_gate(
    evidence: dict[str, Any],
    min_evidence_score: float = 70.0,
    min_strong_ratio: float = 0.8,
    max_low_evidence_sources: int = 0,
) -> dict[str, Any]:
    """Evaluate whether result-artifact evidence is sufficient for CI gating."""
    avg = float(evidence.get("evidence_score_avg", 0.0))
    strong_ratio = float(evidence.get("strong_evidence_ratio", 0.0))
    low_sources = evidence.get("low_evidence_sources", [])
    low_count = len(low_sources) if isinstance(low_sources, list) else 0

    reasons: list[str] = []
    if avg < min_evidence_score:
        reasons.append(
            f"Average evidence score {avg:.2f} below threshold {min_evidence_score:.2f}."
        )
    if strong_ratio < min_strong_ratio:
        reasons.append(
            f"Strong evidence ratio {strong_ratio:.3f} below threshold {min_strong_ratio:.3f}."
        )
    if low_count > max_low_evidence_sources:
        reasons.append(
            f"Low-evidence sources {low_count} exceeds allowed max {max_low_evidence_sources}."
        )

    return {
        "passed": len(reasons) == 0,
        "reasons": reasons,
        "thresholds": {
            "min_evidence_score": min_evidence_score,
            "min_strong_ratio": min_strong_ratio,
            "max_low_evidence_sources": max_low_evidence_sources,
        },
        "observed": {
            "evidence_score_avg": avg,
            "strong_evidence_ratio": strong_ratio,
            "low_evidence_source_count": low_count,
        },
    }


def _profile_weight(dataset_profile: str) -> float:
    if dataset_profile == "real":
        return 1.0
    if dataset_profile == "hybrid":
        return 0.8
    return 0.55


def score_realism(spec: BenchmarkRealismSpec) -> float:
    """Compute realism score (0-100)."""
    score = 0.0
    score += _profile_weight(spec.dataset_profile) * 22.0
    score += min(spec.rows / 2000.0, 1.0) * 16.0
    score += min(spec.scenarios / 30.0, 1.0) * 16.0
    score += min(spec.temporal_slices / 6.0, 1.0) * 10.0
    score += min(spec.adversarial_cases / 50.0, 1.0) * 10.0
    score += min(spec.stress_levels / 6.0, 1.0) * 8.0
    score += spec.confounding_strength * 8.0
    score += 5.0 if spec.missingness_coverage else 0.0
    score += 5.0 if spec.label_noise_coverage else 0.0
    return round(min(score, 100.0), 2)


def score_reliability(spec: BenchmarkRealismSpec) -> float:
    """Compute reliability score (0-100)."""
    score = 0.0
    score += 30.0 if spec.seed_reproducible else 0.0
    score += 22.0 if spec.baseline_comparator else 0.0
    score += min(spec.stress_levels / 6.0, 1.0) * 14.0
    score += min(spec.scenarios / 30.0, 1.0) * 14.0
    score += 12.0 if spec.production_proxy_validated else 0.0
    score += 8.0 if spec.missingness_coverage else 0.0
    return round(min(score, 100.0), 2)


def score_feasibility(spec: BenchmarkRealismSpec) -> float:
    """Compute feasibility score (0-100)."""
    score = 0.0
    score += 40.0 if spec.automated_run else 0.0
    if spec.runtime_budget_minutes <= 30:
        score += 32.0
    elif spec.runtime_budget_minutes <= 60:
        score += 24.0
    elif spec.runtime_budget_minutes <= 120:
        score += 16.0
    else:
        score += 8.0
    score += min(spec.scenarios / 30.0, 1.0) * 16.0
    score += min(spec.stress_levels / 6.0, 1.0) * 12.0
    return round(min(score, 100.0), 2)


def load_realism_manifest(path: Path) -> list[BenchmarkRealismSpec]:
    """Load realism manifest from JSON."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    specs: list[BenchmarkRealismSpec] = []
    for item in raw:
        try:
            specs.append(BenchmarkRealismSpec(**item))
        except Exception:
            continue
    return specs


def summarize_realism(
    specs: list[BenchmarkRealismSpec],
    result_keys: list[str],
    result_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize realism/reliability/feasibility against loaded result keys."""
    if not specs:
        return {
            "status": "missing_manifest",
            "coverage_ratio": 0.0,
            "realism_score_avg": 0.0,
            "reliability_score_avg": 0.0,
            "feasibility_score_avg": 0.0,
            "quality_gate_passed": False,
            "details": "No realism manifest found.",
        }

    by_id = {s.benchmark_id: s for s in specs}
    covered_specs = [by_id[k] for k in result_keys if k in by_id]
    missing_manifest_for_results = sorted([k for k in result_keys if k not in by_id])
    missing_results_for_manifest = sorted([k for k in by_id if k not in result_keys])

    if covered_specs:
        realism_scores = [score_realism(s) for s in covered_specs]
        reliability_scores = [score_reliability(s) for s in covered_specs]
        feasibility_scores = [score_feasibility(s) for s in covered_specs]
    else:
        realism_scores = []
        reliability_scores = []
        feasibility_scores = []

    coverage_ratio = round(len(covered_specs) / max(len(result_keys), 1), 3)
    realism_avg = round(sum(realism_scores) / max(len(realism_scores), 1), 2)
    reliability_avg = round(sum(reliability_scores) / max(len(reliability_scores), 1), 2)
    feasibility_avg = round(sum(feasibility_scores) / max(len(feasibility_scores), 1), 2)
    production_proxy_ratio = round(
        sum(1 for s in covered_specs if s.production_proxy_validated) / max(len(covered_specs), 1),
        3,
    )
    provenance_ratio = round(
        sum(1 for s in covered_specs if s.source_reference.strip()) / max(len(covered_specs), 1),
        3,
    )
    baseline_ratio = round(
        sum(1 for s in covered_specs if s.baseline_comparator) / max(len(covered_specs), 1),
        3,
    )
    synthetic_ratio = round(
        sum(1 for s in covered_specs if s.dataset_profile == "synthetic") / max(len(covered_specs), 1),
        3,
    )

    category_scores: dict[str, dict[str, float]] = {}
    for spec in covered_specs:
        bucket = category_scores.setdefault(
            spec.category,
            {"realism": 0.0, "reliability": 0.0, "feasibility": 0.0, "count": 0.0},
        )
        bucket["realism"] += score_realism(spec)
        bucket["reliability"] += score_reliability(spec)
        bucket["feasibility"] += score_feasibility(spec)
        bucket["count"] += 1.0

    for _cat, bucket in category_scores.items():
        count = max(bucket["count"], 1.0)
        bucket["realism"] = round(bucket["realism"] / count, 2)
        bucket["reliability"] = round(bucket["reliability"] / count, 2)
        bucket["feasibility"] = round(bucket["feasibility"] / count, 2)
        bucket["count"] = int(count)

    absolute_readiness_index = round(
        (realism_avg * 0.35)
        + (reliability_avg * 0.35)
        + (feasibility_avg * 0.2)
        + ((coverage_ratio * 100.0) * 0.1),
        2,
    )

    evidence_score_avg = (
        float(result_evidence.get("evidence_score_avg", 0.0))
        if isinstance(result_evidence, dict)
        else 0.0
    )
    strong_evidence_ratio = (
        float(result_evidence.get("strong_evidence_ratio", 0.0))
        if isinstance(result_evidence, dict)
        else 0.0
    )
    low_evidence_sources = (
        result_evidence.get("low_evidence_sources", [])
        if isinstance(result_evidence, dict)
        else []
    )

    quality_gate_reasons: list[str] = []
    if coverage_ratio < 0.8:
        quality_gate_reasons.append("Result/manifest coverage below 80%.")
    if realism_avg < 65.0:
        quality_gate_reasons.append("Realism score below 65/100.")
    if reliability_avg < 70.0:
        quality_gate_reasons.append("Reliability score below 70/100.")
    if feasibility_avg < 60.0:
        quality_gate_reasons.append("Feasibility score below 60/100.")
    if provenance_ratio < 0.95:
        quality_gate_reasons.append("Dataset provenance references below 95% coverage.")
    if production_proxy_ratio < 0.8:
        quality_gate_reasons.append("Production-proxy validation below 80% of covered benchmarks.")
    if synthetic_ratio > 0.6:
        quality_gate_reasons.append("Synthetic-only benchmark share exceeds 60%.")
    if absolute_readiness_index < 70.0:
        quality_gate_reasons.append("Absolute readiness index below 70/100.")
    if evidence_score_avg < 65.0:
        quality_gate_reasons.append("Result artifact evidence score below 65/100.")
    if strong_evidence_ratio < 0.7:
        quality_gate_reasons.append("Less than 70% of loaded result sources have strong evidence.")

    quality_gate_passed = len(quality_gate_reasons) == 0

    return {
        "status": "ok",
        "coverage_ratio": coverage_ratio,
        "realism_score_avg": realism_avg,
        "reliability_score_avg": reliability_avg,
        "feasibility_score_avg": feasibility_avg,
        "absolute_readiness_index": absolute_readiness_index,
        "production_proxy_ratio": production_proxy_ratio,
        "provenance_ratio": provenance_ratio,
        "baseline_comparator_ratio": baseline_ratio,
        "synthetic_profile_ratio": synthetic_ratio,
        "evidence_score_avg": round(evidence_score_avg, 2),
        "strong_evidence_ratio": round(strong_evidence_ratio, 3),
        "low_evidence_sources": low_evidence_sources,
        "quality_gate_passed": quality_gate_passed,
        "quality_gate_reasons": quality_gate_reasons,
        "covered_specs": len(covered_specs),
        "loaded_result_sources": len(result_keys),
        "missing_manifest_for_results": missing_manifest_for_results,
        "missing_results_for_manifest": missing_results_for_manifest,
        "category_scores": category_scores,
    }
