# OPA Policy Quick Start

This demo uses Open Policy Agent (OPA) as an optional Guardian check. Policies are evaluated against the payload sent from the Guardian.

## Sample Policy

File: `config/opa/guardian.rego`

```rego
package carf.guardian

default allow = true

deny_reason["high_amount"] {
    amount := input.proposed_action.amount
    amount > 100000
}

deny_reason["unsafe_action"] {
    input.proposed_action.action_type == "delete_data"
}

allow {
    count(deny_reason) == 0
}
```

## Running OPA Locally

```bash
opa run --server \
  --set=decision_logs.console=true \
  --addr=0.0.0.0:8181 \
  config/opa/guardian.rego
```

## CARF Configuration

Set these in `.env`:

```bash
OPA_ENABLED=true
OPA_URL=http://localhost:8181
OPA_POLICY_PATH=/v1/data/carf/guardian/allow
OPA_TIMEOUT_SECONDS=5
```

## Expected Input Shape

OPA receives a JSON payload with an `input` key. Example:

```json
{
  "input": {
    "session_id": "123",
    "cynefin_domain": "Complicated",
    "domain_confidence": 0.92,
    "domain_entropy": 0.3,
    "proposed_action": {
      "action_type": "allocate",
      "amount": 125000
    },
    "guardian_verdict": "requires_escalation",
    "policy_violations": ["Amount exceeds limit"]
  }
}
```

OPA returns:

```json
{ "result": true }
```

If `result` is false, the Guardian rejects the action.
