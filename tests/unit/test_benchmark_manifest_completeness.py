# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for benchmark manifest completeness and evidence-grade validation.

Backs the --strict-manifest gate added to check_result_evidence.py and the
SOTA improvement roadmap's P0 (evidence hardening) deliverable.
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.reports.realism import (
    REQUIRED_MANIFEST_FIELDS,
    BenchmarkRealismSpec,
    evaluate_manifest_completeness_gate,
    validate_manifest_completeness,
)


_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "reports" / "realism_manifest.json"


def _full_entry(**overrides) -> dict:
    base = {
        "benchmark_id": "demo",
        "category": "core",
        "dataset_profile": "hybrid",
        "rows": 100,
        "scenarios": 50,
        "seed_reproducible": True,
        "baseline_comparator": True,
        "automated_run": True,
        "source_reference": "demo corpus",
        "data_source": "benchmarks/demo/data.json",
        "ground_truth_type": "rule_based",
        "llm_provider": "deepseek/v3.1",
        "seed": 42,
        "uses_mock": False,
        "uses_fallback": False,
        "sample_size": 50,
        "evidence_grade": "validated",
        "repro_command": "python benchmarks/demo/run.py",
    }
    base.update(overrides)
    return base


def test_completeness_passes_when_all_required_fields_present():
    completeness = validate_manifest_completeness([_full_entry()])
    assert completeness["completeness_ratio"] == 1.0
    assert completeness["incomplete_entries"] == []
    assert completeness["grade_counts"] == {"validated": 1}

    gate = evaluate_manifest_completeness_gate(completeness)
    assert gate["passed"] is True
    assert gate["reasons"] == []


def test_completeness_reports_missing_fields_per_entry():
    incomplete = _full_entry(benchmark_id="missing_seed")
    incomplete.pop("seed")
    incomplete.pop("repro_command")

    completeness = validate_manifest_completeness([_full_entry(), incomplete])

    assert completeness["completeness_ratio"] == 0.5
    assert len(completeness["incomplete_entries"]) == 1
    bad_entry = completeness["incomplete_entries"][0]
    assert bad_entry["benchmark_id"] == "missing_seed"
    assert set(bad_entry["missing_fields"]) == {"seed", "repro_command"}


def test_strict_gate_fails_when_required_fields_missing():
    incomplete = _full_entry(benchmark_id="bad")
    incomplete.pop("evidence_grade")

    completeness = validate_manifest_completeness([incomplete])
    gate = evaluate_manifest_completeness_gate(completeness, min_completeness_ratio=1.0)

    assert gate["passed"] is False
    assert any("evidence_grade" in r for r in gate["reasons"])


def test_unknown_evidence_grade_is_flagged():
    rogue = _full_entry(benchmark_id="rogue", evidence_grade="totally_fine_trust_me")
    completeness = validate_manifest_completeness([rogue])

    assert "rogue" in completeness["unknown_grade_entries"]
    gate = evaluate_manifest_completeness_gate(completeness, forbid_unknown_grades=True)
    assert gate["passed"] is False
    assert any("unrecognised evidence_grade" in r for r in gate["reasons"])


def test_empty_string_counts_as_missing():
    bad = _full_entry(data_source="   ")
    completeness = validate_manifest_completeness([bad])
    assert completeness["completeness_ratio"] == 0.0
    assert "data_source" in completeness["incomplete_entries"][0]["missing_fields"]


def test_required_fields_constant_matches_schema():
    """Guard rail: the constant the CLI gate uses should not silently drift
    from the JSON Schema under benchmarks/reports/."""
    schema_path = _MANIFEST_PATH.with_name("benchmark_manifest.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_required = tuple(schema["$defs"]["manifestEntry"]["required"])
    assert schema_required == REQUIRED_MANIFEST_FIELDS


def test_real_manifest_is_fully_graded():
    """Every entry in the shipped manifest must carry an evidence_grade and
    pass the completeness gate. Adding new entries without grades should
    break this test."""
    raw = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    completeness = validate_manifest_completeness(raw)
    gate = evaluate_manifest_completeness_gate(completeness)

    assert gate["passed"], (
        f"realism_manifest.json failed strict completeness gate: {gate['reasons']}"
    )
    # Sanity: all five grades may not be in use yet, but at least 'validated'
    # and one weaker grade should be present so reports can distinguish them.
    grades_used = set(completeness["grade_counts"].keys())
    assert "validated" in grades_used or "synthetic-only" in grades_used
    assert len(grades_used) >= 2


def test_spec_round_trips_with_evidence_fields():
    """BenchmarkRealismSpec should accept the new evidence-grade fields and
    leave the original realism scoring inputs unchanged."""
    spec = BenchmarkRealismSpec(**_full_entry())
    assert spec.evidence_grade == "validated"
    assert spec.uses_mock is False
    assert spec.seed == 42
    # Original scoring fields unaffected
    assert spec.rows == 100
    assert spec.scenarios == 50
