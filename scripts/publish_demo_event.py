"""Publish a demo audit event to Kafka."""

import os

from dotenv import load_dotenv

from src.core.state import ConfidenceLevel, CynefinDomain, EpistemicState, GuardianVerdict
from src.services.kafka_audit import log_state_to_kafka


def main() -> None:
    load_dotenv()

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap:
        print("Set KAFKA_BOOTSTRAP_SERVERS before running this script.")
        return

    os.environ.setdefault("KAFKA_ENABLED", "true")

    state = EpistemicState(
        cynefin_domain=CynefinDomain.COMPLICATED,
        domain_confidence=0.9,
        domain_entropy=0.3,
        guardian_verdict=GuardianVerdict.APPROVED,
        final_response="Demo response",
    )
    state.add_reasoning_step(
        node_name="demo",
        action="Seeded demo event",
        input_summary="demo input",
        output_summary="demo output",
        confidence=ConfidenceLevel.HIGH,
    )

    log_state_to_kafka(state)
    print("Published demo audit event.")


if __name__ == "__main__":
    main()
