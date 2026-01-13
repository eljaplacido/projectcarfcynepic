"""Mock HumanLayer implementation for testing.

Use this module to simulate human responses without hitting the real HumanLayer API.
See DEV_PRACTICES_AND_LIVING_DOCS.md for testing standards.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class MockHumanResponse(Enum):
    """Predefined human responses for testing scenarios."""

    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    TIMEOUT = "timeout"


@dataclass
class MockApprovalResult:
    """Mock result from a human approval request."""

    approved: bool
    approval_id: str = field(default_factory=lambda: f"mock_hl_{uuid4().hex[:8]}")
    approver_email: str = "test@example.com"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    comment: str | None = None
    modified_params: dict[str, Any] | None = None


class MockHumanLayer:
    """Mock HumanLayer client for unit testing.

    Usage:
        # Test approval flow
        mock_hl = MockHumanLayer(default_response=MockHumanResponse.APPROVE)
        result = await mock_hl.require_approval(action="allocate_funds", params={...})
        assert result.approved

        # Test rejection flow
        mock_hl = MockHumanLayer(default_response=MockHumanResponse.REJECT)
        result = await mock_hl.require_approval(action="allocate_funds", params={...})
        assert not result.approved

        # Test timeout scenario
        mock_hl = MockHumanLayer(default_response=MockHumanResponse.TIMEOUT, timeout_seconds=0.1)
    """

    def __init__(
        self,
        default_response: MockHumanResponse = MockHumanResponse.APPROVE,
        timeout_seconds: float = 300.0,
        modified_params: dict[str, Any] | None = None,
    ):
        """Initialize mock HumanLayer.

        Args:
            default_response: The response to return for all approval requests
            timeout_seconds: Simulated timeout (use 0 to simulate immediate timeout)
            modified_params: Parameters to return when response is MODIFY
        """
        self.default_response = default_response
        self.timeout_seconds = timeout_seconds
        self.modified_params = modified_params or {}

        # Track all requests for assertion in tests
        self.request_history: list[dict[str, Any]] = []

    async def require_approval(
        self,
        action: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> MockApprovalResult:
        """Simulate a human approval request.

        Args:
            action: The action being requested
            params: Parameters for the action
            context: Additional context for the human reviewer

        Returns:
            MockApprovalResult with the configured response
        """
        # Record the request
        request_record = {
            "timestamp": datetime.utcnow(),
            "action": action,
            "params": params,
            "context": context,
        }
        self.request_history.append(request_record)

        # Simulate response based on configuration
        if self.default_response == MockHumanResponse.TIMEOUT:
            # Simulate timeout - in real code this would raise
            return MockApprovalResult(
                approved=False,
                comment="Request timed out - no human response",
            )

        if self.default_response == MockHumanResponse.REJECT:
            return MockApprovalResult(
                approved=False,
                comment="Rejected by mock human reviewer",
            )

        if self.default_response == MockHumanResponse.MODIFY:
            return MockApprovalResult(
                approved=True,
                comment="Approved with modifications",
                modified_params=self.modified_params,
            )

        # Default: APPROVE
        return MockApprovalResult(
            approved=True,
            comment="Approved by mock human reviewer",
        )

    async def contact_user(
        self,
        message: str,
        channel: str = "slack",
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Simulate contacting a user for clarification.

        Args:
            message: Message to send to the user
            channel: Communication channel (slack, email, teams)
            priority: Message priority

        Returns:
            Mock response from the user
        """
        request_record = {
            "timestamp": datetime.utcnow(),
            "type": "contact_user",
            "message": message,
            "channel": channel,
            "priority": priority,
        }
        self.request_history.append(request_record)

        if self.default_response == MockHumanResponse.TIMEOUT:
            return {
                "status": "timeout",
                "response": None,
            }

        return {
            "status": "received",
            "response": "Mock user response: Acknowledged",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset(self) -> None:
        """Reset the mock state for a new test."""
        self.request_history.clear()

    def assert_approval_requested(
        self,
        action: str | None = None,
        times: int | None = None,
    ) -> None:
        """Assert that approval was requested.

        Args:
            action: Specific action to check for (optional)
            times: Expected number of requests (optional)

        Raises:
            AssertionError: If the assertion fails
        """
        approval_requests = [
            r for r in self.request_history if "action" in r
        ]

        if action:
            approval_requests = [
                r for r in approval_requests if r["action"] == action
            ]

        if times is not None:
            assert len(approval_requests) == times, (
                f"Expected {times} approval requests for {action or 'any action'}, "
                f"got {len(approval_requests)}"
            )
        else:
            assert len(approval_requests) > 0, (
                f"Expected at least one approval request for {action or 'any action'}"
            )
