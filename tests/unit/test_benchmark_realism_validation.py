# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Unit tests for benchmark realism and evidence validation."""

from benchmarks.reports.realism import (
    BenchmarkRealismSpec,
    summarize_realism,
    validate_result_evidence,
)


def _high_fidelity_spec() -> BenchmarkRealismSpec:
    return BenchmarkRealismSpec(
        benchmark_id="router",
        category="core",
        dataset_profile="real",
        rows=5000,
        scenarios=80,
        temporal_slices=6,
        stress_levels=6,
        adversarial_cases=60,
        confounding_strength=0.8,
        missingness_coverage=True,
        label_noise_coverage=True,
        seed_reproducible=True,
        baseline_comparator=True,
        production_proxy_validated=True,
        runtime_budget_minutes=25,
        automated_run=True,
        source_reference="production-mirrored cynefin benchmark corpus v2",
    )


def test_evidence_validation_strong_signals():
    results = {
        "router": {
            "generated_at": "2026-02-22T12:00:00Z",
            "benchmark_config": {"seed": 42, "provider": "deepseek"},
            "dataset": {"name": "cynefin_eval", "version": "v2"},
            "total_scenarios": 80,
            "source_reference": "internal benchmark catalog",
        }
    }
    evidence = validate_result_evidence(results, {"router": "benchmarks/router.json"})
    assert evidence["evidence_score_avg"] >= 80.0
    assert evidence["strong_evidence_ratio"] == 1.0


def test_summarize_realism_fails_on_low_evidence():
    specs = [_high_fidelity_spec()]
    weak_results = {"router": {"value": 1}}
    weak_evidence = validate_result_evidence(weak_results, {"router": "benchmarks/router.json"})

    summary = summarize_realism(specs, ["router"], weak_evidence)

    assert summary["quality_gate_passed"] is False
    assert summary["evidence_score_avg"] < 65.0
    assert any("evidence score" in reason.lower() for reason in summary["quality_gate_reasons"])
