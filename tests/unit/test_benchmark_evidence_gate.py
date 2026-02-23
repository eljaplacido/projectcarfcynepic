"""Tests for benchmark evidence gate helpers."""

from benchmarks.reports.realism import evaluate_evidence_gate


def test_evidence_gate_passes_when_thresholds_met():
    evidence = {
        "evidence_score_avg": 82.0,
        "strong_evidence_ratio": 0.9,
        "low_evidence_sources": [],
    }
    gate = evaluate_evidence_gate(
        evidence,
        min_evidence_score=70.0,
        min_strong_ratio=0.8,
        max_low_evidence_sources=0,
    )
    assert gate["passed"] is True
    assert gate["reasons"] == []


def test_evidence_gate_fails_with_multiple_reasons():
    evidence = {
        "evidence_score_avg": 40.0,
        "strong_evidence_ratio": 0.3,
        "low_evidence_sources": ["router", "causal"],
    }
    gate = evaluate_evidence_gate(
        evidence,
        min_evidence_score=70.0,
        min_strong_ratio=0.8,
        max_low_evidence_sources=0,
    )
    assert gate["passed"] is False
    assert len(gate["reasons"]) >= 3
