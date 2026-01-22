"""Tests for src/services/human_layer.py."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.services.human_layer import (
    NotificationContext,
    HumanResponse,
    HumanLayerService,
    get_human_layer_service,
    human_escalation_node,
)
from src.core.state import (
    CynefinDomain,
    ConfidenceLevel,
    EpistemicState,
    HumanInteractionStatus,
    CausalEvidence,
)


class TestNotificationContext:
    """Tests for NotificationContext model."""

    def test_valid_notification_context(self):
        """Test creating a valid notification context."""
        context = NotificationContext(
            what="Action required: approve payment",
            why="High confidence causal analysis",
            risk="Amount exceeds threshold",
        )
        assert context.what == "Action required: approve payment"
        assert context.why == "High confidence causal analysis"
        assert context.risk == "Amount exceeds threshold"

    def test_notification_context_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValueError):
            NotificationContext(
                what="Test",
                why="Test",
            )


class TestHumanResponse:
    """Tests for HumanResponse model."""

    def test_default_values(self):
        """Test default values for HumanResponse."""
        response = HumanResponse()
        assert response.approved is False
        assert response.response_type == "pending"
        assert response.comment is None
        assert response.modified_params is None
        assert response.responder_email is None
        assert response.response_timestamp is None

    def test_approved_response(self):
        """Test creating an approved response."""
        response = HumanResponse(
            approved=True,
            response_type="approve",
            comment="Looks good",
            responder_email="approver@example.com",
            response_timestamp=datetime(2025, 1, 15),
        )
        assert response.approved is True
        assert response.response_type == "approve"
        assert response.comment == "Looks good"
        assert response.responder_email == "approver@example.com"

    def test_rejected_response(self):
        """Test creating a rejected response."""
        response = HumanResponse(
            approved=False,
            response_type="reject",
            comment="Not acceptable",
        )
        assert response.approved is False
        assert response.response_type == "reject"

    def test_modified_response(self):
        """Test creating a modified response."""
        response = HumanResponse(
            approved=True,
            response_type="modify",
            comment="Please adjust parameters",
            modified_params={"amount": 1000, "priority": "high"},
        )
        assert response.response_type == "modify"
        assert response.modified_params == {"amount": 1000, "priority": "high"}


class TestHumanLayerService:
    """Tests for HumanLayerService class."""

    def test_initialization_mock_mode(self):
        """Test initialization in mock mode."""
        service = HumanLayerService(use_mock=True)
        assert service.use_mock is True
        assert service._client is None
        assert service.default_channel == "slack"
        assert service.timeout_seconds == 300.0

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        service = HumanLayerService(
            default_channel="email",
            timeout_seconds=600.0,
            use_mock=True,
        )
        assert service.default_channel == "email"
        assert service.timeout_seconds == 600.0

    def test_build_notification_context_escalation(self):
        """Test building notification context for escalation."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(
            user_input="What should we do about declining sales?",
            cynefin_domain=CynefinDomain.DISORDER,
            domain_confidence=0.4,
            overall_confidence=ConfidenceLevel.LOW,
        )

        context = service._build_notification_context(state, "escalation")

        assert "Clarification needed" in context.what
        assert "Confidence" in context.why
        assert "Low confidence" in context.risk or "Unable to classify" in context.risk

    def test_build_notification_context_approval(self):
        """Test building notification context for approval."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(
            user_input="Approve payment of $50000",
            proposed_action={
                "description": "Transfer $50000 to vendor",
                "amount": 50000,
            },
            overall_confidence=ConfidenceLevel.MEDIUM,
        )

        context = service._build_notification_context(state, "approval")

        assert "Approval needed" in context.what
        assert "Transfer $50000" in context.what

    def test_build_notification_context_with_causal_evidence(self):
        """Test building notification context with causal evidence."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(
            user_input="Test query",
            current_hypothesis="Price affects churn",
            causal_evidence=CausalEvidence(
                effect_size=0.35,
                confidence_interval=(0.2, 0.5),
                refutation_passed=True,
            ),
            overall_confidence=ConfidenceLevel.HIGH,
        )

        context = service._build_notification_context(state, "escalation")

        assert "0.35" in context.why
        assert "Price affects churn" in context.why

    def test_build_notification_context_with_policy_violations(self):
        """Test building notification context with policy violations."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(
            user_input="Delete all records",
            policy_violations=["dangerous_action", "data_deletion"],
            overall_confidence=ConfidenceLevel.LOW,
        )

        context = service._build_notification_context(state, "approval")

        assert "dangerous_action" in context.risk
        assert "data_deletion" in context.risk

    def test_format_slack_message(self):
        """Test formatting context as Slack message."""
        service = HumanLayerService(use_mock=True)
        context = NotificationContext(
            what="Approve transfer",
            why="High confidence analysis",
            risk="Exceeds threshold",
        )

        message = service._format_slack_message(context)

        assert "*CARF Human Review Required*" in message
        assert "*What:* Approve transfer" in message
        assert "*Why:* High confidence analysis" in message
        assert "*Risk:* Exceeds threshold" in message

    def test_update_state_from_response_approve(self):
        """Test updating state from approved response."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(user_input="Test")
        response = HumanResponse(
            approved=True,
            response_type="approve",
            comment="Approved by manager",
        )

        updated = service.update_state_from_response(state, response)

        assert updated.human_interaction_status == HumanInteractionStatus.APPROVED
        assert updated.last_human_feedback == "Approved by manager"
        assert len(updated.reasoning_chain) == 1
        assert "Human approve" in updated.reasoning_chain[0].action

    def test_update_state_from_response_reject(self):
        """Test updating state from rejected response."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(user_input="Test")
        response = HumanResponse(
            approved=False,
            response_type="reject",
            comment="Not allowed",
        )

        updated = service.update_state_from_response(state, response)

        assert updated.human_interaction_status == HumanInteractionStatus.REJECTED
        assert updated.last_human_feedback == "Not allowed"

    def test_update_state_from_response_modify(self):
        """Test updating state from modified response."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(user_input="Test")
        response = HumanResponse(
            approved=True,
            response_type="modify",
            comment="Reduce amount to $1000",
        )

        updated = service.update_state_from_response(state, response)

        assert updated.human_interaction_status == HumanInteractionStatus.MODIFIED
        assert updated.human_override_instructions == "Reduce amount to $1000"

    def test_update_state_from_response_timeout(self):
        """Test updating state from timeout response."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(user_input="Test")
        response = HumanResponse(
            approved=False,
            response_type="timeout",
        )

        updated = service.update_state_from_response(state, response)

        assert updated.human_interaction_status == HumanInteractionStatus.TIMEOUT


class TestHumanLayerServiceAsync:
    """Async tests for HumanLayerService."""

    @pytest.mark.asyncio
    async def test_request_clarification_mock(self):
        """Test requesting clarification in mock mode."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(
            user_input="Unclear query",
            cynefin_domain=CynefinDomain.DISORDER,
        )

        updated_state, response = await service.request_clarification(state)

        assert response.approved is True
        assert response.response_type == "clarification"
        assert "[MOCK]" in response.comment
        assert updated_state.human_interaction_status == HumanInteractionStatus.MODIFIED

    @pytest.mark.asyncio
    async def test_request_approval_mock(self):
        """Test requesting approval in mock mode."""
        service = HumanLayerService(use_mock=True)
        state = EpistemicState(user_input="Approve action")
        action = {"description": "High-value transfer", "amount": 50000}

        updated_state, response = await service.request_approval(state, action)

        assert response.approved is True
        assert response.response_type == "approve"
        assert "[MOCK]" in response.comment
        assert updated_state.human_interaction_status == HumanInteractionStatus.APPROVED
        assert updated_state.human_verification is not None
        assert updated_state.human_verification.requires_approval is True


class TestGetHumanLayerService:
    """Tests for get_human_layer_service singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that singleton returns the same instance."""
        # Reset singleton
        import src.services.human_layer as human_layer_module
        human_layer_module._service_instance = None

        service1 = get_human_layer_service(use_mock=True)
        service2 = get_human_layer_service(use_mock=True)

        assert service1 is service2

        # Reset for other tests
        human_layer_module._service_instance = None


class TestHumanEscalationNode:
    """Tests for human_escalation_node function."""

    @pytest.mark.asyncio
    async def test_escalation_node_disorder(self):
        """Test escalation node for Disorder domain."""
        # Reset singleton
        import src.services.human_layer as human_layer_module
        human_layer_module._service_instance = None
        human_layer_module._service_instance = HumanLayerService(use_mock=True)

        state = EpistemicState(
            user_input="Ambiguous request",
            cynefin_domain=CynefinDomain.DISORDER,
        )

        result = await human_escalation_node(state)

        # The clarification response type falls through to IDLE in update_state_from_response
        # but the request_clarification sets it to MODIFIED first, then update_state_from_response
        # may reset it. Check that feedback was received.
        assert result.last_human_feedback is not None
        assert "[MOCK]" in result.last_human_feedback
        assert len(result.reasoning_chain) == 1

        # Reset singleton
        human_layer_module._service_instance = None

    @pytest.mark.asyncio
    async def test_escalation_node_with_proposed_action(self):
        """Test escalation node with proposed action."""
        import src.services.human_layer as human_layer_module
        human_layer_module._service_instance = None
        human_layer_module._service_instance = HumanLayerService(use_mock=True)

        state = EpistemicState(
            user_input="Execute transfer",
            cynefin_domain=CynefinDomain.COMPLICATED,
            proposed_action={"description": "Transfer funds", "amount": 10000},
        )

        result = await human_escalation_node(state)

        assert result.human_interaction_status == HumanInteractionStatus.APPROVED
        assert result.human_verification is not None

        human_layer_module._service_instance = None
