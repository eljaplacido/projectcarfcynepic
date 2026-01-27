# End-User Testing Guide (Demo and Integrations)

Use this guide to run an end-to-end demo, view visualizations, and test with
your own data and integrations.

## 1) Start the Services
```bash
cd C:\Users\35845\Desktop\DIGICISU\projectcarf

# API (Terminal 1)
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# React Cockpit (Terminal 2)
cd carf-cockpit
npm install
npm run dev
```

Open the cockpit at `http://localhost:5175`.

## 2) Run the End-to-End Demo
1. Select a scenario from the top dropdown, e.g. "Renewable Energy ROI".
2. Click a suggested query (it will populate the Analyze input) or enter your own.
3. Click **Analyze** and watch the panels update:
   - Cynefin Classification
   - Causal DAG
   - Causal Analysis Results
   - Guardian Policy Check
   - Execution Trace
   - Bayesian Belief State

## 3) Test with Your Own Data
Upload a dataset to the local registry:
```bash
curl -X POST http://localhost:8000/datasets \
  -H "Content-Type: application/json" \
  -d @demo/payloads/causal_estimation.json
```

Then run a query with dataset selection:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Estimate the impact of treatment on outcome",
    "dataset_selection": {
      "dataset_id": "<paste_dataset_id>",
      "treatment": "treatment",
      "outcome": "outcome",
      "covariates": ["confounder_a", "confounder_b"],
      "effect_modifiers": []
    }
  }'
```

## 4) Integrations (Optional)
- Neo4j: set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- Kafka: set `KAFKA_ENABLED=true`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`
- OPA: set `OPA_ENABLED=true`, `OPA_URL`, `OPA_POLICY_PATH`

Restart the API after changing environment variables.

## 5) Offline Testing
To run without external LLM calls:
```bash
set CARF_TEST_MODE=1
```
This enables deterministic stub responses for routing and analysis.
