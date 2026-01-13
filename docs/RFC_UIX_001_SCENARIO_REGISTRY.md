# RFC UIX-001: Demo Scenario Registry

## Summary

Introduce a scenario registry so the UI can discover demo scenarios from the
backend (no hardcoded payloads in Streamlit). The registry returns metadata and
payload content for demo runs.

## Motivation

- Ensure the UI is always synced with backend demo assets.
- Keep demo scenarios versioned alongside the API and data stack.
- Make the Streamlit cockpit a true client of backend state.

## Scope

In scope:
- Scenario metadata file in `demo/scenarios.json`.
- FastAPI endpoints to list scenarios and fetch scenario payloads.
- Streamlit scenario selector that preloads query + optional configs.

Out of scope:
- Scenario authoring UI.
- Multi-tenant scenario catalogs.

## API Changes

New endpoints:
- `GET /scenarios`
  - Returns list of scenario metadata.
- `GET /scenarios/{scenario_id}`
  - Returns metadata + payload JSON.

## Data Model

Scenario metadata:
```
{
  "id": "causal_discount_churn",
  "name": "Discount vs Churn",
  "description": "Estimate causal impact of discount on churn.",
  "payload_path": "demo/payloads/causal_estimation.json"
}
```

## UI Changes

Streamlit:
- Add a scenario selector in the Run a Query panel.
- On selection, prefill:
  - query text
  - causal_estimation or bayesian_inference JSON

## Testing

- Manual: select scenario, run analysis, verify reasoning chain.
- API: call `/scenarios` and `/scenarios/{id}`.

## Rollout

- Backward compatible; no existing endpoint changes.
- Scenario registry file is optional; API returns empty list if missing.
