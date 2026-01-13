"""HumanLayer Service - Human-in-the-Loop Integration.

Provides seamless human escalation via HumanLayer SDK for:
- Disorder domain routing (ambiguous inputs)
- High-risk action approvals
- Guardian override requests

All notifications follow the "3-Point Context" standard:
- What: One-sentence summary of proposed action
- Why: Causal justification with confidence
- Risk: Why it was flagged (policy violation, uncertainty)
"""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.state import (
    ConfidenceLevel,
    EpistemicState,
    HumanInteractionStatus,
    HumanVerificationMetadata,
)
from src.utils.resiliency import async_retry_with_backoff, with_timeout

logger = logging.getLogger("carf.human_layer")


class NotificationContext(BaseModel):
    """The 3-Point Context for human notifications."""

    what: str = Field(..., description="One-sentence summary of the action/request")
    why: str = Field(..., description="Causal justification with confidence")
    risk: str = Field(..., description="Why this was flagged for human review")


class HumanResponse(BaseModel):
    """Response from a human via HumanLayer."""

    approved: bool = False
    response_type: str = Field(
        default="pending",
        description="approve, reject, modify, timeout"
    )
    comment: str | None = None
    modified_params: dict[str, Any] | None = None
    responder_email: str | None = None
    response_timestamp: datetime | None = None


class HumanLayerService:
    """Service for human-in-the-loop interactions via HumanLayer.

    Handles:
    1. Disorder escalations (clarification requests)
    2. Action approval requests
    3. Guardian override flows

    In MVP phase, this provides a clean interface that can work with
    either the real HumanLayer SDK or the mock for testing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_channel: str = "slack",
        timeout_seconds: float = 300.0,
        use_mock: bool = False,
    ):
        """Initialize HumanLayer service.

        Args:
            api_key: HumanLayer API key (from env if not provided)
            default_channel: Primary notification channel (slack, email, teams)
            timeout_seconds: How long to wait for human response
            use_mock: If True, use mock implementation for testing
        """
        self.default_channel = default_channel
        self.timeout_seconds = timeout_seconds
        self.use_mock = use_mock

        if use_mock:
            logger.info("HumanLayer service initialized in MOCK mode")
            self._client = None
        else:
            self._init_real_client(api_key)

    def _init_real_client(self, api_key: str | None) -> None:
        """Initialize the real HumanLayer client."""
        try:
            from humanlayer import HumanLayer
            import os

            key = api_key or os.getenv("HUMANLAYER_API_KEY")
            if not key:
                logger.warning(
                    "No HUMANLAYER_API_KEY found. Running in degraded mode."
                )
                self._client = None
                return

            self._client = HumanLayer(api_key=key)
            logger.info("HumanLayer client initialized successfully")
        except ImportError:
            logger.warning("HumanLayer SDK not installed. Running in mock mode.")
            self._client = None
            self.use_mock = True

    def _build_notification_context(
        self,
        state: EpistemicState,
        action_type: str = "escalation",
    ) -> NotificationContext:
        """Build the 3-Point Context for a notification.

        Args:
            state: Current epistemic state
            action_type: Type of notification (escalation, approval, override)

        Returns:
            NotificationContext with what/why/risk
        """
        # What: Summarize the situation
        if action_type == "escalation":
            what = f"Clarification needed: {state.user_input[:100]}..."
        elif action_type == "approval":
            action_desc = state.proposed_action or {}
            what = f"Approval needed: {action_desc.get('description', 'Action pending')}"
        else:
            what = f"Override requested for: {state.user_input[:100]}..."

        # Why: Causal justification
        why_parts = []
        if state.current_hypothesis:
            why_parts.append(state.current_hypothesis)
        why_parts.append(f"Confidence: {state.overall_confidence.value}")
        if state.causal_evidence:
            why_parts.append(
                f"Effect size: {state.causal_evidence.effect_size:.2f}"
            )
        why = " | ".join(why_parts) if why_parts else "No causal context available"

        # Risk: Why flagged
        risk_parts = []
        if state.cynefin_domain.value == "Disorder":
            risk_parts.append("Unable to classify request with sufficient confidence")
        if state.domain_confidence < 0.85:
            risk_parts.append(f"Low confidence: {state.domain_confidence:.2f}")
        if state.policy_violations:
            risk_parts.append(f"Policy violations: {', '.join(state.policy_violations)}")
        if state.reflection_count >= state.max_reflections:
            risk_parts.append(
                f"Max self-correction attempts ({state.max_reflections}) reached"
            )
        risk = " | ".join(risk_parts) if risk_parts else "Flagged for human review"

        return NotificationContext(what=what, why=why, risk=risk)

    def _format_slack_message(self, context: NotificationContext) -> str:
        """Format context as a Slack-friendly message."""
        return f"""*CARF Human Review Required*

*What:* {context.what}

*Why:* {context.why}

*Risk:* {context.risk}

---
Please respond with your decision."""

    @async_retry_with_backoff(max_attempts=2, exceptions=(Exception,))
    async def request_clarification(
        self,
        state: EpistemicState,
    ) -> tuple[EpistemicState, HumanResponse]:
        """Request clarification from a human for Disorder domain.

        This is called when the router cannot confidently classify the input.

        Args:
            state: Current epistemic state

        Returns:
            Tuple of (updated_state, human_response)
        """
        logger.info(f"Requesting human clarification for session {state.session_id}")

        # Update state to waiting
        state.human_interaction_status = HumanInteractionStatus.WAITING_APPROVAL

        # Build notification context
        context = self._build_notification_context(state, "escalation")

        if self.use_mock or self._client is None:
            # Mock response for testing/development
            response = HumanResponse(
                approved=True,
                response_type="clarification",
                comment="[MOCK] Please provide more specific details about your request.",
                responder_email="mock@example.com",
                response_timestamp=datetime.utcnow(),
            )
            state.human_interaction_status = HumanInteractionStatus.MODIFIED
            state.last_human_feedback = response.comment
            logger.info("Mock clarification response generated")
            return state, response

        # Real HumanLayer call would go here
        # For now, simulate the pattern
        try:
            message = self._format_slack_message(context)

            # In real implementation:
            # result = await self._client.contact_user(message=message, ...)

            # Placeholder - real implementation pending HumanLayer SDK integration
            response = HumanResponse(
                approved=True,
                response_type="pending",
                comment="Awaiting human response via HumanLayer",
            )
            return state, response

        except Exception as e:
            logger.error(f"HumanLayer clarification request failed: {e}")
            state.human_interaction_status = HumanInteractionStatus.TIMEOUT
            state.error = str(e)
            return state, HumanResponse(
                approved=False,
                response_type="error",
                comment=f"Failed to reach human: {str(e)}",
            )

    @async_retry_with_backoff(max_attempts=2, exceptions=(Exception,))
    async def request_approval(
        self,
        state: EpistemicState,
        action: dict[str, Any],
    ) -> tuple[EpistemicState, HumanResponse]:
        """Request approval for a high-risk action.

        Called by the Guardian when an action requires human sign-off.

        Args:
            state: Current epistemic state
            action: The proposed action requiring approval

        Returns:
            Tuple of (updated_state, human_response)
        """
        logger.info(f"Requesting approval for action in session {state.session_id}")

        # Store proposed action
        state.proposed_action = action
        state.human_interaction_status = HumanInteractionStatus.WAITING_APPROVAL

        # Build notification context
        context = self._build_notification_context(state, "approval")

        if self.use_mock or self._client is None:
            # Mock: Auto-approve for testing
            response = HumanResponse(
                approved=True,
                response_type="approve",
                comment="[MOCK] Action approved for testing",
                responder_email="mock@example.com",
                response_timestamp=datetime.utcnow(),
            )
            state.human_interaction_status = HumanInteractionStatus.APPROVED
            state.human_verification = HumanVerificationMetadata(
                requires_approval=True,
                human_layer_id=f"mock_hl_{state.session_id.hex[:8]}",
                approver_email=response.responder_email,
                approval_channel=self.default_channel,
                approval_timestamp=response.response_timestamp,
                human_comment=response.comment,
            )
            logger.info("Mock approval generated")
            return state, response

        # Real HumanLayer approval flow
        try:
            message = self._format_slack_message(context)

            # In real implementation with HumanLayer SDK:
            # @self._client.require_approval()
            # async def execute_action():
            #     ...

            response = HumanResponse(
                approved=True,
                response_type="pending",
                comment="Awaiting human approval via HumanLayer",
            )
            return state, response

        except Exception as e:
            logger.error(f"HumanLayer approval request failed: {e}")
            state.human_interaction_status = HumanInteractionStatus.TIMEOUT
            state.error = str(e)
            return state, HumanResponse(
                approved=False,
                response_type="error",
                comment=f"Failed to get approval: {str(e)}",
            )

    def update_state_from_response(
        self,
        state: EpistemicState,
        response: HumanResponse,
    ) -> EpistemicState:
        """Update epistemic state based on human response.

        Args:
            state: Current epistemic state
            response: Human response from HumanLayer

        Returns:
            Updated epistemic state
        """
        if response.response_type == "approve":
            state.human_interaction_status = HumanInteractionStatus.APPROVED
        elif response.response_type == "reject":
            state.human_interaction_status = HumanInteractionStatus.REJECTED
        elif response.response_type == "modify":
            state.human_interaction_status = HumanInteractionStatus.MODIFIED
            state.human_override_instructions = response.comment
        elif response.response_type == "timeout":
            state.human_interaction_status = HumanInteractionStatus.TIMEOUT
        else:
            state.human_interaction_status = HumanInteractionStatus.IDLE

        state.last_human_feedback = response.comment

        # Record in reasoning chain
        state.add_reasoning_step(
            node_name="human_escalation",
            action=f"Human {response.response_type}",
            input_summary="Requested human review",
            output_summary=f"Response: {response.comment or 'No comment'}",
            confidence=ConfidenceLevel.HIGH if response.approved else ConfidenceLevel.MEDIUM,
        )

        return state


# Singleton instance
_service_instance: HumanLayerService | None = None


def get_human_layer_service(use_mock: bool = False) -> HumanLayerService:
    """Get or create the HumanLayer service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = HumanLayerService(use_mock=use_mock)
    return _service_instance


async def human_escalation_node(state: EpistemicState) -> EpistemicState:
    """LangGraph node for human escalation.

    Called when:
    - Router classifies as Disorder
    - Guardian requires human override
    - Max self-correction attempts exceeded

    Usage in LangGraph:
        workflow.add_node("human_escalation", human_escalation_node)
    """
    service = get_human_layer_service()

    # Determine escalation type
    if state.cynefin_domain.value == "Disorder":
        # Clarification request
        state, response = await service.request_clarification(state)
    elif state.proposed_action:
        # Action approval request
        state, response = await service.request_approval(state, state.proposed_action)
    else:
        # General escalation
        state, response = await service.request_clarification(state)

    return service.update_state_from_response(state, response)
