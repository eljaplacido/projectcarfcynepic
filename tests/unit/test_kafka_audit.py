"""Unit tests for Kafka audit event generation."""

from datetime import datetime

from src.core.state import (
    CynefinDomain,
    EpistemicState,
    GuardianVerdict,
    HumanVerificationMetadata,
)
from src.services.kafka_audit import KafkaAuditEvent


def test_kafka_audit_event_from_state_basic():
    state = EpistemicState(
        cynefin_domain=CynefinDomain.CLEAR,
        domain_confidence=0.9,
        domain_entropy=0.1,
        guardian_verdict=GuardianVerdict.APPROVED,
        final_response="OK",
    )

    event = KafkaAuditEvent.from_state(state)

    assert event.schema_version == "1.0"
    assert event.event_type == "agent_decision"
    assert event.session_id == str(state.session_id)
    assert event.cynefin_domain == "Clear"
    assert event.guardian_verdict == "approved"
    assert event.final_response == "OK"
    assert isinstance(event.timestamp, datetime)


def test_kafka_audit_event_includes_human_verification():
    state = EpistemicState()
    state.human_verification = HumanVerificationMetadata(
        requires_approval=True,
        approver_email="reviewer@example.com",
    )

    event = KafkaAuditEvent.from_state(state)

    assert event.human_verification is not None
    assert event.human_verification["requires_approval"] is True
    assert event.human_verification["approver_email"] == "reviewer@example.com"
