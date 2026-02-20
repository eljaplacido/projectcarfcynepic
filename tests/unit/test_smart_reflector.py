"""Tests for SmartReflectorService."""

import os
import pytest
from unittest.mock import patch

from src.services.smart_reflector import (
    SmartReflectorService,
    RepairResult,
    RepairStrategy,
    get_smart_reflector,
)
from src.core.state import EpistemicState, GuardianVerdict


@pytest.fixture
def reflector():
    """Create a fresh SmartReflectorService for testing."""
    return SmartReflectorService()


@pytest.fixture
def budget_state():
    """State with budget violation."""
    return EpistemicState(
        user_input="Budget test",
        proposed_action={"action_type": "invest", "amount": 150000, "parameters": {"monthly": 12500}},
        policy_violations=["Budget exceeded: 150000 > 100000"],
        guardian_verdict=GuardianVerdict.REJECTED,
    )


class TestHeuristicRepair:
    """Tests for heuristic repair strategies."""

    def test_heuristic_repair_budget(self, reflector):
        """Budget violation → 0.8x reduction."""
        action = {"action_type": "invest", "amount": 150000}
        result = reflector._try_heuristic_repair(action, ["Budget exceeded: 150000 > 100000"])

        assert result is not None
        assert result.strategy_used == RepairStrategy.HEURISTIC
        assert result.repaired_action["amount"] == 150000 * 0.8
        assert "Budget exceeded" in result.violations_addressed[0]

    def test_heuristic_repair_threshold(self, reflector):
        """Threshold violation → 0.9x reduction."""
        action = {"action_type": "adjust", "effect_size": 0.95}
        result = reflector._try_heuristic_repair(action, ["Threshold exceeded for effect_size"])

        assert result is not None
        assert result.repaired_action["effect_size"] == pytest.approx(0.95 * 0.9)

    def test_heuristic_repair_approval(self, reflector):
        """Approval violation → requires_human_review flag."""
        action = {"action_type": "deploy"}
        result = reflector._try_heuristic_repair(action, ["Missing approval for deployment"])

        assert result is not None
        assert result.repaired_action["requires_human_review"] is True
        assert "review_reason" in result.repaired_action

    def test_heuristic_returns_none_for_unknown(self, reflector):
        """Unknown violation type → None (no heuristic matches)."""
        action = {"action_type": "transfer", "region": "us-east-1"}
        result = reflector._try_heuristic_repair(action, ["Data residency requires EU storage"])

        assert result is None

    def test_heuristic_handles_nested_params(self, reflector):
        """Budget repair handles nested dict values."""
        action = {"amount": 100, "parameters": {"monthly": 50.0}}
        result = reflector._try_heuristic_repair(action, ["Budget exceeded"])

        assert result is not None
        assert result.repaired_action["parameters"]["monthly"] == pytest.approx(50.0 * 0.8)


class TestHybridRepair:
    """Tests for hybrid strategy."""

    @pytest.mark.asyncio
    async def test_hybrid_uses_heuristic_when_sufficient(self, reflector, budget_state):
        """High-confidence heuristic should skip LLM."""
        result = await reflector.repair(budget_state)

        assert result.strategy_used == RepairStrategy.HEURISTIC
        assert result.confidence >= 0.7
        assert result.repaired_action["amount"] < 150000

    @pytest.mark.asyncio
    async def test_hybrid_falls_back_to_llm(self, reflector):
        """Unknown violation triggers LLM fallback."""
        state = EpistemicState(
            user_input="Unknown violation test",
            proposed_action={"action_type": "transfer", "value": 100},
            policy_violations=["Data residency requires EU storage"],
        )

        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            result = await reflector.repair(state)

        # Should use LLM since heuristic returns None
        assert result.strategy_used == RepairStrategy.LLM
        assert "test_stub" in result.repair_explanation


class TestRepairResultStructure:
    """Tests for RepairResult field validation."""

    def test_repair_result_structure(self):
        """RepairResult fields are valid."""
        result = RepairResult(
            strategy_used=RepairStrategy.HEURISTIC,
            original_action={"a": 1},
            repaired_action={"a": 0.8},
            repair_explanation="Reduced a by 20%",
            confidence=0.85,
            violations_addressed=["Budget exceeded"],
            violations_remaining=[],
        )
        assert 0 <= result.confidence <= 1
        assert isinstance(result.violations_addressed, list)
        assert isinstance(result.violations_remaining, list)

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(Exception):
            RepairResult(
                strategy_used=RepairStrategy.HEURISTIC,
                original_action={},
                repaired_action={},
                repair_explanation="test",
                confidence=1.5,
            )


class TestNoViolations:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_no_violations_returns_unchanged(self, reflector):
        """No violations → return original action unchanged."""
        state = EpistemicState(
            user_input="Clean state",
            proposed_action={"action_type": "lookup"},
            policy_violations=[],
        )
        result = await reflector.repair(state)

        assert result.confidence == 1.0
        assert result.repaired_action == {"action_type": "lookup"}

    @pytest.mark.asyncio
    async def test_no_action_handles_gracefully(self, reflector):
        """No proposed_action → returns empty dict unchanged."""
        state = EpistemicState(
            user_input="No action",
            policy_violations=["Some violation"],
        )
        result = await reflector.repair(state)
        assert isinstance(result.repaired_action, dict)


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_pattern(self):
        """get_smart_reflector returns same instance."""
        import src.services.smart_reflector as mod
        mod._smart_reflector = None

        s1 = get_smart_reflector()
        s2 = get_smart_reflector()
        assert s1 is s2

        mod._smart_reflector = None
