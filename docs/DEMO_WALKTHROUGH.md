# CARF Research Demo Walkthrough

This guide walks through running the full demo stack locally with Neo4j, Kafka, OPA, and the Streamlit cockpit.

## 1. Start the Stack

```bash
docker compose up --build
```

Services:
- CARF API: http://localhost:8000
- Streamlit Cockpit: http://localhost:8501
- Neo4j Browser: http://localhost:7474
- OPA: http://localhost:8181
- Kafka (host): localhost:29092

## 2. Seed Demo Data

Seed Neo4j and publish a demo Kafka event:

```bash
docker compose --profile demo run --rm seed
```

## 3. Run a Live Query

Use the Streamlit cockpit or curl:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @demo/payloads/causal_estimation.json
```

Demo payloads:
- `demo/payloads/causal_estimation.json` (discount -> churn causal estimate)
- `demo/payloads/bayesian_inference.json` (conversion belief update)

## 4. Explore the Cockpit

In Streamlit:
- Pick a scenario from the header dropdown (e.g., Renewable Energy ROI).
- Click a suggested query to populate the input, then run **Analyze**.
- Run a live `/query` call from the UI and review the reasoning chain.

Bring your data (small CSV):
- Upload CSV in the Data Sources panel, then map columns and apply dataset selection.
- Keep datasets at or below 5000 rows.
- Uploaded datasets are stored locally under `var/` (bind-mounted in compose).

## 5. Optional: OPA Policy Check

Enable OPA in `.env`:

```bash
OPA_ENABLED=true
OPA_URL=http://localhost:8181
OPA_POLICY_PATH=/v1/data/carf/guardian/allow
```

See `docs/OPA_POLICY.md` for the sample policy.
