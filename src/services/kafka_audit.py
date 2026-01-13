"""Kafka audit trail service for CARF."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.core.state import EpistemicState
from src.utils.resiliency import retry_with_backoff

logger = logging.getLogger("carf.kafka")


class KafkaConfig(BaseModel):
    """Kafka configuration for audit logging."""

    bootstrap_servers: str = Field(default="")
    topic: str = Field(default="carf_decisions")
    client_id: str = Field(default="carf")
    enabled: bool = Field(default=False)

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        """Load Kafka configuration from environment variables."""
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
        enabled_env = os.getenv("KAFKA_ENABLED")
        enabled = (
            enabled_env.lower() == "true"
            if enabled_env is not None
            else bool(bootstrap_servers)
        )

        return cls(
            bootstrap_servers=bootstrap_servers,
            topic=os.getenv("KAFKA_TOPIC", "carf_decisions"),
            client_id=os.getenv("KAFKA_CLIENT_ID", "carf"),
            enabled=enabled,
        )


class KafkaAuditEvent(BaseModel):
    """Audit event payload for Kafka."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = Field(default="1.0")
    event_type: str = Field(default="agent_decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    cynefin_domain: str
    domain_confidence: float
    domain_entropy: float
    guardian_verdict: str | None
    reasoning_chain: list[dict[str, Any]]
    human_verification: dict[str, Any] | None = None
    final_action: dict[str, Any] | None = None
    final_response: str | None = None

    @classmethod
    def from_state(cls, state: EpistemicState) -> "KafkaAuditEvent":
        """Build an audit event from EpistemicState."""
        reasoning_chain = [
            {
                "node": step.node_name,
                "action": step.action,
                "confidence": step.confidence.value,
                "timestamp": step.timestamp.isoformat(),
            }
            for step in state.reasoning_chain
        ]

        human_verification = (
            state.human_verification.model_dump()
            if state.human_verification is not None
            else None
        )

        return cls(
            session_id=str(state.session_id),
            cynefin_domain=state.cynefin_domain.value,
            domain_confidence=state.domain_confidence,
            domain_entropy=state.domain_entropy,
            guardian_verdict=state.guardian_verdict.value
            if state.guardian_verdict
            else None,
            reasoning_chain=reasoning_chain,
            human_verification=human_verification,
            final_action=state.final_action,
            final_response=state.final_response,
        )


class KafkaAuditService:
    """Service for publishing audit events to Kafka."""

    def __init__(self, config: KafkaConfig | None = None) -> None:
        self.config = config or KafkaConfig.from_env()
        self._producer = None

        if not self.config.enabled:
            logger.info("Kafka audit disabled (KAFKA_ENABLED=false)")
            return

        if not self.config.bootstrap_servers:
            logger.warning("Kafka bootstrap servers not configured")
            return

        try:
            from confluent_kafka import Producer  # type: ignore
        except ImportError:
            logger.warning("confluent-kafka not installed, audit logging disabled")
            return

        self._producer = Producer(
            {
                "bootstrap.servers": self.config.bootstrap_servers,
                "client.id": self.config.client_id,
            }
        )
        logger.info("Kafka audit producer initialized")

    @retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    def _produce(self, payload: str) -> None:
        """Send a serialized payload to Kafka."""
        if not self._producer:
            return

        self._producer.produce(self.config.topic, payload.encode("utf-8"))
        self._producer.flush(5)

    def log_state(self, state: EpistemicState) -> None:
        """Publish an audit event for the given state."""
        if not self._producer:
            return

        event = KafkaAuditEvent.from_state(state)
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=True)
        self._produce(payload)


_kafka_audit_instance: KafkaAuditService | None = None


def get_kafka_audit_service() -> KafkaAuditService:
    """Get or create the Kafka audit service singleton."""
    global _kafka_audit_instance
    if _kafka_audit_instance is None:
        _kafka_audit_instance = KafkaAuditService()
    return _kafka_audit_instance


def log_state_to_kafka(state: EpistemicState) -> None:
    """Convenience wrapper to log state if Kafka is configured."""
    service = get_kafka_audit_service()
    service.log_state(state)
