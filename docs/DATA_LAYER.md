# CARF Data Layer Architecture: Comprehensive Deep Dive (v2.0 with HumanLayer)

## Executive Overview

The CARF data layer maintains four distinct data domains: causal, epistemic, symbolic, and operational. With HumanLayer integration, the operational domain gains a first-class human verification record. CARF is interactive by design: it reasons, proposes actions, and asks for permission. The data architecture must support this bidirectional flow where human decisions become part of the system's causal history.

---

## 2. Data Layer Architecture

### 2.5 Kafka: The Immutable Audit Trail and Human Verification

Kafka audit logging is available in the demo stack. Every decision must leave a receipt. Kafka ensures immutability. With HumanLayer, these receipts include the context of human authorization.

```python
# Producer: CARF writes decision events
from confluent_kafka import Producer

# ... standard event setup ...

event = {
    "event_type": "agent_decision",
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "agent_type": "CausalAnalyst",
    "reasoning_chain": { ... },  # Router -> Causal -> Guardian

    # HumanLayer integration
    "human_verification_metadata": {
        "requires_approval": True,
        "human_layer_id": "hl_req_abc123",
        "approver_email": "manager@enterprise.com",
        "approval_channel": "slack",
        "approval_timestamp": "2025-01-15T10:35:00Z",
        "human_comment": "Approved exception due to urgent grid demand."
    },

    "final_action": {
        "action_type": "allocate",
        "parameters": {"supplier_id": "xyz", "amount": 500000}
    }
}

producer.produce("carf_decisions", value=json.dumps(event).encode())
producer.flush()
```

---

## 3. Context and Memory Management

### 3.1 The Epistemic State Machine

The `EpistemicState` tracks human interaction context.

```python
from pydantic import BaseModel, Field
from src.core.state import HumanInteractionStatus

class EpistemicState(BaseModel):
    # ... standard fields: session_id, cynefin_domain, etc. ...

    # HumanLayer context
    human_interaction_status: HumanInteractionStatus = Field(
        default=HumanInteractionStatus.IDLE
    )
    last_human_feedback: str | None = None
    human_override_instructions: str | None = None
```

---

## 8. UIX Considerations

### 8.1 Dashboard vs. Operational Channels

CARF distinguishes between analysis and action channels.

- The Cockpit (Streamlit): Slow thinking. Visualize causal DAGs, debug posteriors, trace logs.
- The Communication Channel (HumanLayer): Fast thinking. Approvals, clarifications, and notifications.
 - Dataset Registry (local): UI-driven CSV onboarding stored in `var/` for demo use.

### 8.2 Rejection Clarity and Interactive Resolution

When the Guardian blocks an action, the UX must be constructive:

- Standard UI: "Error: Policy Violation."
- CARF with HumanLayer: Trigger an interactive resolution flow via HumanLayer.

Example flow:

1. Guardian blocks action "Invest $600k" (Policy limit: $500k).
2. HumanLayer sends a Slack card to the Budget Officer.
3. Options: Reject, Approve One-Time Exception, Modify Amount.
4. User selects "Approve One-Time Exception."
5. HumanLayer calls `guardian.override_policy(token=...)` and the workflow proceeds.

---

## Summary: Implementation Checklist

### Phase 1: MVP (Weeks 1-4)

- [x] Infrastructure setup (Docker Compose)
- [x] Neo4j causal graph for a single use case (async persistence service)
- [ ] PostgreSQL epistemic state storage
- [x] Full Cynefin router (Clear, Complicated, Complex, Chaotic, Disorder)
- [x] HumanLayer integration for approvals and Disorder routing (mock fallback)
- [x] Web API (FastAPI)

### Phase 2: Add Bayesian Uncertainty and Guardian (Weeks 5-8)

- [ ] Redis caching
- [ ] TimescaleDB observations
- [x] Guardian layer with YAML policies (OPA optional integration available)
- [ ] HumanLayer advanced flows for modify/exception handling

### Phase 3: The Dashboard (Weeks 9-12)

- [x] Streamlit Cockpit for causal graph visualization (demo-ready)
- [x] Active Inference agent (LLM-based, PyMC planned)
- [x] Kafka event sourcing scaffolding with HumanLayer receipt logging
