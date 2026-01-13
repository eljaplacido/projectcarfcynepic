# CARF Project Handoff Document

## Project Overview
**CARF (Complex-Adaptive Reasoning Fabric)** is a Neuro-Symbolic-Causal Agentic System with epistemic awareness. It implements a "Two-Speed Cognitive Model" using Cynefin framework for decision routing.

## Project Structure

```
projectcarf/
├── src/
│   ├── main.py              # FastAPI backend (port 8000)
│   ├── __init__.py          # Package version
│   ├── core/
│   │   ├── state.py         # EpistemicState, CynefinDomain models
│   │   └── __init__.py
│   ├── dashboard/
│   │   └── app.py           # Streamlit dashboard UI
│   ├── services/
│   │   ├── __init__.py      # Service exports
│   │   ├── bayesian.py      # Bayesian/Active Inference engine
│   │   ├── causal.py        # DoWhy/EconML causal inference
│   │   ├── dataset_store.py # Dataset registry
│   │   ├── human_layer.py   # Human-in-the-loop service
│   │   ├── kafka_audit.py   # Audit trail service
│   │   ├── neo4j_service.py # Graph database service
│   │   └── opa_service.py   # Policy service
│   ├── utils/
│   │   └── resiliency.py    # Retry/resilience utilities
│   ├── workflows/
│   │   ├── graph.py         # LangGraph workflow
│   │   ├── router.py        # Cynefin domain router
│   │   └── guardian.py      # Policy guardian
│   └── tools/
│       └── __init__.py
├── config/
│   ├── agents.yaml          # Agent definitions
│   ├── policies.yaml        # Guardian policies
│   └── prompts.yaml         # Prompt templates
├── demo/
│   ├── scenarios.json       # Demo scenario registry
│   └── payloads/
│       ├── causal_estimation.json
│       ├── bayesian_inference.json
│       ├── scope3_attribution.json
│       ├── renewable_energy_roi.json
│       └── shipping_carbon.json
├── tests/
│   ├── unit/
│   │   ├── test_state.py
│   │   ├── test_router.py
│   │   ├── test_guardian.py
│   │   └── test_neo4j_service.py
│   └── mocks/
│       └── mock_human_layer.py
├── pyproject.toml           # Dependencies & build config
├── .env                     # Environment variables (API keys)
└── .venv/                   # Virtual environment
```

## How to Run

### 1. Start the FastAPI Backend
```bash
cd C:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Query endpoint: POST http://localhost:8000/query

### 2. Start the Streamlit Dashboard
```bash
cd C:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\activate
set CARF_API_URL=http://localhost:8000
python -m streamlit run src/dashboard/app.py --server.port 8501
```

The dashboard will be available at: http://localhost:8501

## Key Components

### Dashboard Views (src/dashboard/app.py)
1. **End-User View**: Query input, simulation controls, Cynefin classification, Bayesian belief state, Causal DAG, Guardian policy checks
2. **Developer View**: Execution trace, DAG structure, state snapshots, raw JSON
3. **Executive View**: KPIs, expected impact, risk level, policy compliance summary

### Cynefin Domains (5 domains)
- **Clear**: Deterministic, best practice responses
- **Complicated**: Expert analysis with causal inference
- **Complex**: Emergent patterns, Bayesian probing
- **Chaotic**: Crisis mode, circuit breaker
- **Disorder**: Human escalation required

### API Endpoints
- `GET /health` - Health check
- `POST /query` - Process query through CARF pipeline
- `GET /scenarios` - List demo scenarios
- `GET /scenarios/{id}` - Get scenario details
- `POST /datasets` - Create dataset
- `GET /datasets` - List datasets
- `GET /domains` - List Cynefin domains

## Environment Variables (.env)
Required:
- `OPENAI_API_KEY` - For LLM features

Optional:
- `HUMANLAYER_API_KEY` - For human-in-the-loop escalation
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - For graph database
- `KAFKA_BOOTSTRAP_SERVERS` - For audit trail

## Demo Walkthrough

1. Start both backend and dashboard
2. In the dashboard, select a scenario from the dropdown (e.g., "Scope 3 Attribution")
3. Enter a query like: "Which suppliers have the highest emissions reduction potential?"
4. Click "Analyze" to process through the CARF pipeline
5. View the results:
   - Left panel: Cynefin classification, Bayesian belief state
   - Center panel: Causal DAG, causal analysis results, Guardian policy checks
   - Right panel: Execution trace

## Status
- All core files are in place
- Dependencies installed in .venv
- Demo scenarios configured
- Dashboard UI complete with three views
- Ready for testing

## Known Issues (from last session)

1. **Port 8000 may be in use** - If you get "address already in use" error:
   ```bash
   # Find process using port 8000
   netstat -ano | findstr :8000
   # Kill the process (replace PID with actual number)
   taskkill /PID <PID> /F
   ```
   Or use a different port: `--port 8001`

2. **OPENAI_API_KEY not set** - The .env file needs a valid OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
   Without this, LLM-based classification and analysis will fail.

## Next Steps
1. Verify OpenAI API key in .env
2. Start backend server
3. Start Streamlit dashboard
4. Run through a demo scenario walkthrough
