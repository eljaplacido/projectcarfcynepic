# CARF Research Demo Walkthrough

A step-by-step guide for demonstrating CARF's capabilities.

## Quick Start (React Cockpit)

```bash
# Terminal 1: Start backend
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
python -m uvicorn src.main:app --reload --port 8000

# Terminal 2: Start React frontend
cd carf-cockpit
npm run dev
```

**Access:**
- **React Cockpit**: http://localhost:5175
- **API Docs**: http://localhost:8000/docs

## Demo Scenarios

| Scenario | Domain | Demo Focus |
|----------|--------|------------|
| Scope 3 Attribution | Complicated | Causal DAG, supplier impact |
| Discount vs Churn | Complicated | Effect estimation, refutation |
| Renewable Energy ROI | Complicated | Investment analysis |
| Conversion Belief | Complex | Bayesian inference |
| Shipping Carbon | Complicated | Mode emissions comparison |

## Walkthrough Steps

### 1. Select a Scenario
- Open React cockpit at http://localhost:5175
- Click a scenario card (e.g., "Scope 3 Attribution")
- See welcome message and suggested queries

### 2. Submit a Query
- Click a suggested query or type your own
- Watch the progress indicator during analysis
- Results display in the main panel

### 3. Explore Results
- **Cynefin Panel**: Domain classification with confidence
- **Causal DAG**: Interactive graph with treatment/outcome nodes
- **Causal Analysis**: Effect estimate, p-value, refutation tests
- **Bayesian Panel**: Prior/posterior distributions
- **Guardian Panel**: Policy checks and verdict

### 4. Use Developer View
- Switch to Developer view mode (tab at top)
- View execution trace timeline
- Inspect architecture flow and state

### 5. Deep Analysis & Sensitivity
- After results load, click **"Deep Analysis"** to re-run with multiple estimators (linear regression, propensity score matching, PS stratification) and heterogeneous treatment effects
- Click **"Sensitivity Check"** to run 3 refutation tests (placebo, random common cause, data subset) with per-test p-values

### 6. Configure Policies
- In the Guardian panel, click **"Configure"** to open the Policy Editor
- Browse 5 built-in CSL policies (35 rules total)
- Add rules via natural language (e.g., "Block transfers over $5000")
- Test policies against sample context to see pass/fail results

### 7. Simulation Arena
- Run at least 2 queries to build history
- Open the Simulation Arena to compare sessions side-by-side
- Benchmarks are derived from your actual data (not generic)
- Follow the 4-step Simulation Guide

### 8. Executive Summary
- Type `/summary` in the chat for a plain-English summary
- Or click the amber **"Executive Summary"** button on any result
- Shows: key finding, confidence, risk assessment, recommendation

### 9. Chat with CARF
- Use the chat panel for follow-up questions
- Try slash commands: `/help`, `/history`, `/analyze`, `/summary`
- Socratic mode asks clarifying questions

## Docker Full Stack (Optional)

```bash
docker compose up --build
docker compose --profile demo run --rm seed
```

Services: API (8000), React Cockpit (5175), Neo4j (7474), OPA (8181)

## API Examples

```bash
# Simple query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What causes customer churn?"}'

# Causal analysis
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @demo/payloads/causal_estimation.json

# Chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Explain the results"}]}'
```

### 10. Data Feasibility Guidance
- CARF communicates clearly which analysis is feasible per data type
- **Tabular/quantitative data**: Full causal inference (DoWhy), Bayesian analysis (PyMC), fast Oracle predictions
- **Qualitative/document data**: Semantic routing, chat-guided hypothesis formulation, domain classification
- The Data Onboarding Wizard (5-step flow) validates data suitability before analysis begins
- ChimeraOracle auto-activates when a pre-trained model exists for the scenario

### 11. Feedback Loop
- Rate analysis quality (1-5 stars) via the Feedback panel
- Correct domain classifications to improve Router accuracy
- All feedback is persisted to SQLite for continuous improvement
- Export domain overrides for Router retraining: `GET /feedback/domain-overrides`

### 12. Benchmark Testing

CARF includes 6 technical benchmarks and end-to-end use case benchmarks for validation.

**Quick benchmark demo (API must be running):**

```bash
# Run all benchmarks via API
curl -X POST http://localhost:8000/benchmarks/run-all

# Run individual technical benchmarks
python benchmarks/technical/router/benchmark_router.py       # Router classification accuracy
python benchmarks/technical/causal/benchmark_causal.py       # Causal effect estimation
python benchmarks/technical/bayesian/benchmark_bayesian.py   # Bayesian posterior calibration
python benchmarks/technical/guardian/benchmark_guardian.py    # Policy enforcement
python benchmarks/technical/performance/benchmark_latency.py # Latency profiling
python benchmarks/technical/chimera/benchmark_oracle.py      # Oracle vs DoWhy speed

# End-to-end use case benchmarks (6 industries)
python benchmarks/use_cases/benchmark_e2e.py

# Generate unified comparison report (H1-H9 hypotheses)
python benchmarks/reports/generate_report.py
```

**Benchmarks connect to use cases:**

| Use Case | Benchmark | Hypothesis |
|----------|-----------|------------|
| Scope 3 Attribution | Causal benchmark (ATE accuracy) | H1: >= 50% lower MSE |
| Market Uncertainty | Bayesian benchmark (posterior coverage) | H2: >= 90% coverage |
| Budget Compliance | Guardian benchmark (violation detection) | H3: 100% detection |
| All scenarios | Performance benchmark (latency) | H6: 2-5x slower, quality compensates |
| Fast predictions | ChimeraOracle benchmark (speed) | H8: >= 10x faster |

See `benchmarks/README.md` for complete instructions and `docs/WALKTHROUGH.md` for detailed testing guide.

## Key Features Demonstrated

- **AI Act Transparency**: Explainable results with confidence levels
- **Causal Reasoning**: DAG discovery and effect estimation
- **Deep Analysis**: Multi-estimator validation and heterogeneous treatment effects
- **Sensitivity Testing**: Placebo, random common cause, and data subset refutation
- **Uncertainty Quantification**: Bayesian belief updates
- **Human-in-the-Loop**: Guardian policy enforcement
- **CSL Policy Management**: Non-programmatic constraint editing via Policy Editor
- **Executive Summaries**: Plain-English findings via `/summary` command
- **Simulation Arena**: Side-by-side session comparison with contextual benchmarks
- **Agent Transparency**: Reliability scores and category-coded agent cards
- **Developer Visibility**: Full execution trace, CSL audit logs, and state inspection
- **Persistent Feedback**: SQLite-backed feedback store with domain override export
- **ChimeraOracle Auto-Activation**: Fast predictions when trained models are available
- **Configurable Regions**: CSL region validation configurable via `CSL_APPROVED_REGIONS` env var
- **Data Feasibility**: Clear guidance on what data types suit each analysis method
- **Benchmark Suite**: 6 technical benchmarks + end-to-end use case benchmarks testing 9 falsifiable hypotheses (H1-H9)
- **TLA+ Formal Verification**: StateGraph and EscalationProtocol formally verified with TLC model checker
