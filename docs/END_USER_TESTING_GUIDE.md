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

## 6) Benchmark Validation

Run the benchmark suite to validate that all CARF components meet their pass criteria. These benchmarks map directly to the platform's use cases and user stories.

### Quick Run (All Benchmarks)
```bash
curl -X POST http://localhost:8000/benchmarks/run-all
```

### Technical Benchmarks

| Benchmark | Command | User Story | Pass Criteria |
|-----------|---------|------------|---------------|
| Router Classification | `python benchmarks/technical/router/benchmark_router.py` | US-1: Accurate domain routing | F1 >= 0.85, ECE < 0.10 |
| Causal Engine | `python benchmarks/technical/causal/benchmark_causal.py` | US-2: Reliable effect estimation | ATE MSE < 0.5 |
| Bayesian Engine | `python benchmarks/technical/bayesian/benchmark_bayesian.py` | US-3: Calibrated uncertainty | Coverage >= 90% |
| Guardian Policy | `python benchmarks/technical/guardian/benchmark_guardian.py` | US-4: Policy enforcement | 100% detection, < 5% FPR |
| Performance | `python benchmarks/technical/performance/benchmark_latency.py` | US-5: Responsive analysis | P95 < 10s |
| ChimeraOracle | `python benchmarks/technical/chimera/benchmark_oracle.py` | US-6: Fast predictions | >= 10x speed, < 20% loss |

### End-to-End Use Case Benchmarks

Tests full CARF pipeline vs raw LLM across 6 industry scenarios:

```bash
python benchmarks/use_cases/benchmark_e2e.py
```

| Industry | Use Case | What's Validated |
|----------|----------|-----------------|
| Supply Chain | Disruption risk analysis | Causal effect + correct domain routing |
| Financial Risk | Discount impact on churn | Effect estimation + Guardian compliance |
| Sustainability | Scope 3 emissions attribution | Data provenance + causal reasoning |
| Critical Infra | Grid voltage stability | Circuit breaker activation + escalation |
| Healthcare | Treatment protocol uncertainty | Bayesian inference + uncertainty tracking |
| Energy | Renewable investment ROI | Multi-estimator consistency |

### Generating the Comparison Report

Aggregates all results and tests 9 falsifiable hypotheses (H1-H9):

```bash
python benchmarks/reports/generate_report.py --output results/report.json
```

See `benchmarks/README.md` and `docs/WALKTHROUGH.md` (Benchmark Testing Guide section) for detailed instructions and interpretation guidance.
