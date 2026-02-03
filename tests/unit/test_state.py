"""Unit tests for core state schemas."""

import pytest
from uuid import UUID

from src.core.state import (
    CynefinDomain,
    EpistemicState,
    GuardianVerdict,
    HumanInteractionStatus,
    ConfidenceLevel,
)


class TestCynefinDomain:
    """Tests for Cynefin domain classification."""

    def test_domain_values(self):
        """Verify all Cynefin domains are defined."""
        assert CynefinDomain.CLEAR.value == "Clear"
        assert CynefinDomain.COMPLICATED.value == "Complicated"
        assert CynefinDomain.COMPLEX.value == "Complex"
        assert CynefinDomain.CHAOTIC.value == "Chaotic"
        assert CynefinDomain.DISORDER.value == "Disorder"

    def test_domain_count(self):
        """Ensure exactly 5 domains exist."""
        assert len(CynefinDomain) == 5


class TestEpistemicState:
    """Tests for the EpistemicState Pydantic model."""

    def test_default_initialization(self):
        """Test that EpistemicState initializes with sensible defaults."""
        state = EpistemicState()

        assert isinstance(state.session_id, UUID)
        assert state.cynefin_domain == CynefinDomain.DISORDER
        assert state.domain_confidence == 0.0
        assert state.human_interaction_status == HumanInteractionStatus.IDLE
        assert state.reflection_count == 0
        assert state.max_reflections == 2

    def test_initialization_with_values(self):
        """Test initialization with custom values."""
        state = EpistemicState(
            user_input="Analyze supplier cost increase",
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.92,
        )

        assert state.user_input == "Analyze supplier cost increase"
        assert state.cynefin_domain == CynefinDomain.COMPLICATED
        assert state.domain_confidence == 0.92

    def test_confidence_bounds(self):
        """Test that confidence values are bounded [0, 1]."""
        # Valid bounds
        state = EpistemicState(domain_confidence=0.0)
        assert state.domain_confidence == 0.0

        state = EpistemicState(domain_confidence=1.0)
        assert state.domain_confidence == 1.0

        # Invalid bounds should raise
        with pytest.raises(ValueError):
            EpistemicState(domain_confidence=-0.1)

        with pytest.raises(ValueError):
            EpistemicState(domain_confidence=1.1)

    def test_add_reasoning_step(self):
        """Test adding steps to the reasoning chain."""
        state = EpistemicState()
        assert len(state.reasoning_chain) == 0

        state.add_reasoning_step(
            node_name="router",
            action="Classified input as Complicated",
            input_summary="User query about costs",
            output_summary="Domain: Complicated, Confidence: 0.92",
            confidence=ConfidenceLevel.HIGH,
        )

        assert len(state.reasoning_chain) == 1
        step = state.reasoning_chain[0]
        assert step.node_name == "router"
        assert step.action == "Classified input as Complicated"
        assert step.confidence == ConfidenceLevel.HIGH

    def test_should_escalate_disorder(self):
        """Test that Disorder domain triggers escalation."""
        state = EpistemicState(cynefin_domain=CynefinDomain.DISORDER)
        assert state.should_escalate_to_human() is True

    def test_should_escalate_low_confidence(self):
        """Test that low confidence triggers escalation."""
        state = EpistemicState(
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.5,  # Below 0.85 threshold
        )
        assert state.should_escalate_to_human() is True

    def test_should_escalate_max_reflections(self):
        """Test that exceeding max reflections triggers escalation."""
        state = EpistemicState(
            cynefin_domain=CynefinDomain.COMPLICATED,
            domain_confidence=0.95,
            reflection_count=3,
            max_reflections=3,
        )
        assert state.should_escalate_to_human() is True

    def test_should_escalate_guardian_requires(self):
        """Test that Guardian requiring escalation is respected."""
        state = EpistemicState(
            cynefin_domain=CynefinDomain.CLEAR,
            domain_confidence=0.99,
            guardian_verdict=GuardianVerdict.REQUIRES_ESCALATION,
        )
        assert state.should_escalate_to_human() is True

    def test_no_escalation_clear_high_confidence(self):
        """Test that Clear domain with high confidence doesn't escalate."""
        state = EpistemicState(
            cynefin_domain=CynefinDomain.CLEAR,
            domain_confidence=0.98,
            guardian_verdict=GuardianVerdict.APPROVED,
        )
        assert state.should_escalate_to_human() is False

    def test_json_serialization(self):
        """Test that state can be serialized to JSON."""
        state = EpistemicState(
            user_input="Test query",
            cynefin_domain=CynefinDomain.COMPLICATED,
        )

        json_str = state.model_dump_json()
        assert "Test query" in json_str
        assert "Complicated" in json_str

        # Deserialize and verify
        restored = EpistemicState.model_validate_json(json_str)
        assert restored.user_input == state.user_input
        assert restored.cynefin_domain == state.cynefin_domain
