"""Trace-to-Eval Loop for CARF.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Captures workflow trace events (failures, low-confidence cases, human
overrides, Guardian rejections) and stores them as structured regression
cases for continuous evaluation improvement.

Phase 18E+ — Operational Intelligence.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("carf.trace_eval")

# Default storage path — can be overridden via env
_DEFAULT_STORE_PATH = Path("data/trace_eval_regressions.jsonl")


@dataclass
class RegressionCase:
    """A single regression case captured from a workflow trace."""

    case_id: str
    trace_id: str
    captured_at: str
    trigger: str  # e.g., "guardian_rejection", "low_confidence", "human_override"
    domain: str | None
    user_input: str
    proposed_action: dict[str, Any] | None
    guardian_verdict: str | None
    confidence: float | None
    evaluation_scores: dict[str, Any] | None
    reflector_attempts: int = 0
    final_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "trace_id": self.trace_id,
            "captured_at": self.captured_at,
            "trigger": self.trigger,
            "domain": self.domain,
            "user_input": self.user_input,
            "proposed_action": self.proposed_action,
            "guardian_verdict": self.guardian_verdict,
            "confidence": self.confidence,
            "evaluation_scores": self.evaluation_scores,
            "reflector_attempts": self.reflector_attempts,
            "final_response": self.final_response,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RegressionCase":
        return cls(
            case_id=d["case_id"],
            trace_id=d["trace_id"],
            captured_at=d["captured_at"],
            trigger=d["trigger"],
            domain=d.get("domain"),
            user_input=d["user_input"],
            proposed_action=d.get("proposed_action"),
            guardian_verdict=d.get("guardian_verdict"),
            confidence=d.get("confidence"),
            evaluation_scores=d.get("evaluation_scores"),
            reflector_attempts=d.get("reflector_attempts", 0),
            final_response=d.get("final_response"),
        )


class TraceEvalLoop:
    """Bounded, persistent capture of workflow regression cases.

    Cases are written to a JSONL file for durability and can be loaded
    back for analysis, test generation, or retraining data.
    """

    def __init__(
        self,
        store_path: Path | None = None,
        memory_buffer_size: int = 100,
    ) -> None:
        self.store_path = store_path or _DEFAULT_STORE_PATH
        self.memory_buffer: deque[RegressionCase] = deque(maxlen=memory_buffer_size)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing cases from disk into memory buffer."""
        if not self.store_path.exists():
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        case = RegressionCase.from_dict(json.loads(line))
                        self.memory_buffer.append(case)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as exc:
            logger.warning("Failed to load existing regression cases: %s", exc)

    def capture(
        self,
        trace_id: str,
        trigger: str,
        state: Any,
    ) -> RegressionCase:
        """Capture a regression case from workflow state.

        Args:
            trace_id: The workflow trace identifier
            trigger: Reason for capture (guardian_rejection, low_confidence, etc.)
            state: EpistemicState (or any object with relevant attributes)
        """
        case = RegressionCase(
            case_id=str(uuid.uuid4())[:8],
            trace_id=trace_id,
            captured_at=datetime.now(timezone.utc).isoformat(),
            trigger=trigger,
            domain=getattr(state, "domain", None),
            user_input=getattr(state, "user_input", "") or "",
            proposed_action=getattr(state, "proposed_action", None),
            guardian_verdict=getattr(state, "guardian_verdict", None),
            confidence=getattr(state, "confidence", None),
            evaluation_scores=getattr(state, "evaluation_scores", None),
            reflector_attempts=getattr(state, "reflector_count", 0),
            final_response=getattr(state, "final_response", None),
        )

        self.memory_buffer.append(case)
        self._append_to_disk(case)
        logger.info(
            "Captured regression case %s (trigger=%s, domain=%s)",
            case.case_id,
            trigger,
            case.domain,
        )
        return case

    def _append_to_disk(self, case: RegressionCase) -> None:
        """Append a single case to the JSONL store."""
        try:
            with open(self.store_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(case.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist regression case: %s", exc)

    def get_cases(
        self,
        trigger: str | None = None,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[RegressionCase]:
        """Retrieve captured cases with optional filtering."""
        cases = list(self.memory_buffer)
        if trigger:
            cases = [c for c in cases if c.trigger == trigger]
        if domain:
            cases = [c for c in cases if c.domain == domain]
        return cases[-limit:]

    def stats(self) -> dict[str, Any]:
        """Return summary statistics of captured cases."""
        total = len(self.memory_buffer)
        triggers: dict[str, int] = {}
        domains: dict[str, int] = {}
        for case in self.memory_buffer:
            triggers[case.trigger] = triggers.get(case.trigger, 0) + 1
            if case.domain:
                domains[case.domain] = domains.get(case.domain, 0) + 1

        return {
            "total_cases": total,
            "by_trigger": triggers,
            "by_domain": domains,
            "store_path": str(self.store_path),
        }

    def export_for_tests(self, output_path: Path | None = None) -> Path:
        """Export cases as a Python test fixture file.

        Each case becomes a pytest parametrize entry for regression testing.
        """
        if output_path is None:
            output_path = Path("tests/eval/trace_regression_cases.py")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cases = list(self.memory_buffer)

        lines = [
            '# Auto-generated regression cases from trace-to-eval loop',
            '# Run: pytest tests/eval/ -v',
            '',
            'import pytest',
            '',
            'TRACE_REGRESSION_CASES = [',
        ]
        for case in cases:
            lines.append(f'    # {case.case_id} — {case.trigger} ({case.domain})')
            lines.append(f'    {{')
            lines.append(f'        "case_id": {repr(case.case_id)},')
            lines.append(f'        "user_input": {repr(case.user_input[:200])},')
            lines.append(f'        "trigger": {repr(case.trigger)},')
            lines.append(f'        "domain": {repr(case.domain)},')
            lines.append(f'        "confidence": {case.confidence},')
            lines.append(f'    }},')
        lines.append(']')
        lines.append('')
        lines.append('@pytest.mark.parametrize("case", TRACE_REGRESSION_CASES)')
        lines.append('def test_regression_case_not_regressing(case):')
        lines.append('    """Smoke test: every captured case must have required fields."""')
        lines.append('    assert case["case_id"]')
        lines.append('    assert case["user_input"]')
        lines.append('    assert case["trigger"]')

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Exported %d regression cases to %s", len(cases), output_path)
        return output_path


# Singleton
_loop_instance: TraceEvalLoop | None = None


def get_trace_eval_loop() -> TraceEvalLoop:
    """Get or create the singleton trace-to-eval loop."""
    global _loop_instance
    if _loop_instance is None:
        _loop_instance = TraceEvalLoop()
    return _loop_instance
