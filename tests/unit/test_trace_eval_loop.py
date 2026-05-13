"""Tests for trace-to-eval loop and OpenTelemetry tracing.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.trace_eval_loop import RegressionCase, TraceEvalLoop


class TestRegressionCase:
    def test_roundtrip(self):
        case = RegressionCase(
            case_id="abc123",
            trace_id="trace-1",
            captured_at="2026-01-01T00:00:00+00:00",
            trigger="guardian_rejection",
            domain="complicated",
            user_input="test query",
            proposed_action={"action_type": "test"},
            guardian_verdict="REJECTED",
            confidence=0.85,
            evaluation_scores={"hallucination_risk": 0.1},
            reflector_attempts=1,
            final_response="test response",
        )
        d = case.to_dict()
        restored = RegressionCase.from_dict(d)
        assert restored.case_id == case.case_id
        assert restored.trigger == case.trigger
        assert restored.domain == case.domain


class TestTraceEvalLoop:
    def test_capture_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"
            loop = TraceEvalLoop(store_path=store, memory_buffer_size=10)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test input"
                proposed_action = {"action_type": "test"}
                guardian_verdict = "REJECTED"
                confidence = 0.75
                evaluation_scores = None
                reflector_count = 1
                final_response = "response"

            case = loop.capture("trace-1", "guardian_rejection", FakeState())
            assert case.case_id is not None
            assert case.trigger == "guardian_rejection"

            cases = loop.get_cases(trigger="guardian_rejection")
            assert len(cases) == 1
            assert cases[0].domain == "complicated"

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"
            loop = TraceEvalLoop(store_path=store, memory_buffer_size=10)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test"
                proposed_action = None
                guardian_verdict = None
                confidence = None
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop.capture("t1", "guardian_rejection", FakeState())
            loop.capture("t2", "chaotic_domain_activation", FakeState())

            stats = loop.stats()
            assert stats["total_cases"] == 2
            assert stats["by_trigger"]["guardian_rejection"] == 1
            assert stats["by_trigger"]["chaotic_domain_activation"] == 1
            assert stats["by_domain"]["complicated"] == 2

    def test_filtering(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"
            loop = TraceEvalLoop(store_path=store, memory_buffer_size=10)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test"
                proposed_action = None
                guardian_verdict = None
                confidence = None
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop.capture("t1", "guardian_rejection", FakeState())

            class FakeState2:
                session_id = "sess-2"
                domain = "chaotic"
                user_input = "test2"
                proposed_action = None
                guardian_verdict = None
                confidence = None
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop.capture("t2", "chaotic_domain_activation", FakeState2())

            assert len(loop.get_cases(trigger="guardian_rejection")) == 1
            assert len(loop.get_cases(domain="chaotic")) == 1
            assert len(loop.get_cases(trigger="nonexistent")) == 0

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"

            # Create loop, capture, destroy
            loop1 = TraceEvalLoop(store_path=store, memory_buffer_size=10)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test"
                proposed_action = None
                guardian_verdict = None
                confidence = None
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop1.capture("t1", "guardian_rejection", FakeState())

            # Create new loop, verify it loads from disk
            loop2 = TraceEvalLoop(store_path=store, memory_buffer_size=10)
            assert len(loop2.memory_buffer) == 1

    def test_export_for_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"
            loop = TraceEvalLoop(store_path=store, memory_buffer_size=10)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test input"
                proposed_action = None
                guardian_verdict = None
                confidence = 0.5
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop.capture("t1", "guardian_rejection", FakeState())
            out = Path(tmpdir) / "test_cases.py"
            loop.export_for_tests(output_path=out)
            assert out.exists()
            content = out.read_text()
            assert "TRACE_REGRESSION_CASES" in content
            assert "guardian_rejection" in content

    def test_lru_eviction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = Path(tmpdir) / "regressions.jsonl"
            loop = TraceEvalLoop(store_path=store, memory_buffer_size=2)

            class FakeState:
                session_id = "sess-1"
                domain = "complicated"
                user_input = "test"
                proposed_action = None
                guardian_verdict = None
                confidence = None
                evaluation_scores = None
                reflector_count = 0
                final_response = None

            loop.capture("t1", "trigger1", FakeState())
            loop.capture("t2", "trigger2", FakeState())
            loop.capture("t3", "trigger3", FakeState())

            assert len(loop.memory_buffer) == 2
            assert loop.memory_buffer[0].trigger == "trigger2"
            assert loop.memory_buffer[1].trigger == "trigger3"
