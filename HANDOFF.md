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

## Status (Updated 2026-02-04)

### Tests
- **437 tests passing** (3 skipped), 64% coverage
- All unit tests, eval tests, and workflow tests operational

### Recent Improvements
- Enhanced simulation service with 4 data generators and scenario realism assessment
- Added TransparencyPanel for reliability, agents, EU AI Act compliance, and config
- Added comprehensive walkthroughs (Quick Demo, Analyst, Executive, Contributor, Production)
- Enhanced AI chat guidance for data onboarding and configuration
- Created central WALKTHROUGH.md documentation
- Fixed TypeScript lint errors and unused variable warnings
- Added context-aware Guardian policies with Cynefin domain thresholds

### Docker Setup (Recommended)
```bash
docker-compose up -d
# Services: app (8000), cockpit (5175), neo4j (7474), kafka (9092), opa (8181)
```

### React Cockpit (Primary UI)
Located at `carf-cockpit/` - modern React dashboard with:
- Analyst View: Full causal/Bayesian analysis panels
- Developer View: Real-time logs, execution timeline, architecture visualization
- Executive View: KPI dashboard with context-aware metrics

## Environment Variables (.env)
```bash
# LLM Configuration (use DeepSeek for cost efficiency)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key

# Alternative: OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key

# Router Configuration
ROUTER_MODE=llm              # or distilbert
ROUTER_MODEL_PATH=models/router_distilbert

# Optional Services
HUMANLAYER_API_KEY=          # Human-in-the-loop
NEO4J_URI=bolt://localhost:7687
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Quick Test
```bash
# Test scope3 causal analysis
python -c "
import requests
response = requests.post('http://localhost:8000/query', json={
    'query': 'What is the causal effect of supplier_program on scope3_emissions?',
    'context': {'domain_hint': 'complicated'},
    'causal_estimation': {
        'treatment': 'supplier_program',
        'outcome': 'scope3_emissions',
        'csv_path': 'demo/data/scope3_emissions.csv'
    }
}, timeout=120)
print('Effect:', response.json().get('causalResult', {}).get('effect'))
"
```

## Documentation
- `docs/WALKTHROUGH.md` - **Complete walkthrough guide** (Analyst, Developer, Executive views)
- `docs/QUICKSTART.md` - Quick start guide
- `docs/DEMO_WALKTHROUGH.md` - Demo scenario walkthrough
- `docs/ROUTER_TRAINING.md` - Router training and domain adaptation
- `docs/LLM_AGENTIC_STRATEGY.md` - Model selection and guardrails
- `docs/DATA_LAYER.md` - Dataset management
- `docs/SECURITY_GUIDELINES.md` - Security best practices

## Next Steps
1. Start docker services: `docker-compose up -d`
2. Access React cockpit: http://localhost:5175
3. Run a demo scenario (scope3_attribution recommended)
4. Check Developer View for real-time analysis progress
