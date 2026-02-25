# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for shared benchmark metadata/provenance helpers."""

from benchmarks import finalize_benchmark_report


def test_finalize_benchmark_report_adds_required_evidence_fields():
    payload = {"total_scenarios": 12, "rows": 480}
    finalized = finalize_benchmark_report(
        payload,
        benchmark_id="demo_benchmark",
        source_reference="dataset:demo_v1",
        benchmark_config={"seed": 42},
    )

    assert finalized["benchmark_id"] == "demo_benchmark"
    assert "generated_at" in finalized
    assert "benchmark_config" in finalized
    assert "dataset_context" in finalized
    assert "sample_context" in finalized
    assert "source_reference" in finalized
    assert "provenance" in finalized

    assert finalized["benchmark_config"]["seed"] == 42
    assert finalized["sample_context"]["total_scenarios"] == 12
    assert finalized["sample_context"]["rows"] == 480
    assert finalized["source_reference"] == "dataset:demo_v1"
