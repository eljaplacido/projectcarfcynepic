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

### 5. Chat with CARF
- Use the chat panel for follow-up questions
- Try slash commands: `/help`, `/history`, `/analyze`
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

## Key Features Demonstrated

- **AI Act Transparency**: Explainable results with confidence levels
- **Causal Reasoning**: DAG discovery and effect estimation
- **Uncertainty Quantification**: Bayesian belief updates
- **Human-in-the-Loop**: Guardian policy enforcement
- **Developer Visibility**: Full execution trace and state inspection
