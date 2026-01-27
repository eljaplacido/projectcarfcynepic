# Project CARF: CYNEPIC Architecture 0.5
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/b50309cd-0f03-4424-ad49-72cdc796ff14" />
**Complexity-Adaptive & Context-Aware Reasoning Fabric** - A research grade Architectural Blueprint & Decision Intelligence Simulation for more reliable and transparent data-driven decision making and Agentic AI Systems, combining complexity & context adaptability, causal inference, bayesian methods to quantify uncertainty & complexity
and epistemic awareness. 

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://react.dev/)

<img width="2752" height="1536" alt="CARF architecture" src="https://github.com/user-attachments/assets/46631f78-1c72-43a2-aee3-c37c61cddb9c" />

## Overview

Modern AI systems often act as black boxes, producing confident-sounding outputs without clarifying their reasoning, certainty level, or the nature of the problem they're addressing. This creates a **"trust gap"**: users cannot easily distinguish whether an AI answer is based on solid causal evidence, a probabilistic inference, or a simple guess.

**CYNEPIC (CYNefin-EPIstemic Cockpit)** solves this by enforcing **epistemic awareness**. The system explicitly classifies every query by its inherent complexity using the [Cynefin Framework](https://en.wikipedia.org/wiki/Cynefin_framework), then routes it to the appropriate analytical engine—ensuring the right tool is used for the right problem.

| Problem Type | Analysis Method | Example |
|--------------|-----------------|----------|
| **Clear** (Obvious) | Rule lookup | "What is the capital of France?" |
| **Complicated** (Knowable) | Causal Inference (DoWhy) | "Does offering a discount reduce churn?" |
| **Complex** (Emergent) | Bayesian Inference (PyMC) | "What is the likely conversion rate?" |
| **Chaotic** (Crisis) | Circuit Breaker | System alert, require human action |
| **Disorder** (Ambiguous) | Human Escalation | Input is unclear or contradictory |

All outputs are filtered through a **Guardian Layer** that enforces organizational policies (e.g., "require human approval for decisions affecting >$1M budget") and logs an audit trail for compliance (e.g., EU AI Act).

### Key Features

- **Cynefin-based Routing**: Automatic classification of query complexity.
- **Causal Inference Engine**: Discover DAGs, estimate effects, and run refutation tests via DoWhy/EconML.
- **Bayesian Exploration**: Quantify uncertainty and update beliefs with new evidence via PyMC.
- **Guardian Policy Layer**: Human-in-the-loop enforcement, Slack/Email notifications, and full audit trails.
- **Three-View Dashboard**: Tailored views for Analysts, Developers, and Executives.

### Data & Analytical Flows in CARF architecture 

<img width="2752" height="1536" alt="Dataflow blueprint" src="https://github.com/user-attachments/assets/e0eecb39-5813-4b83-9a42-0e735ba0dee8" />

### User interface samples

<img width="1920" height="1833" alt="Data onboarding" src="https://github.com/user-attachments/assets/02563ff0-db92-4565-ad8b-b40d7d6ef7d3" />
<img width="1527" height="1158" alt="Simulation1" src="https://github.com/user-attachments/assets/9c44d7d5-55e3-481a-a495-4ecbab5ed3e7" />
<img width="3096" height="1779" alt="Frontpage" src="https://github.com/user-attachments/assets/e8f18a22-1280-46e5-83b6-6473cb244a55" />
<img width="366" height="1170" alt="Explanations" src="https://github.com/user-attachments/assets/95b7e1ad-b35e-4491-9872-c94a2fb021bc" />
<img width="2409" height="1671" alt="Executive" src="https://github.com/user-attachments/assets/ed0b07b9-ac62-4d64-a7f1-8bdf48b9bd39" />


## Quick Start

### Option 1: Local Development (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/projectcarf.git
cd projectcarf

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start the API server
python -m src.main

# In a new terminal, start the React cockpit
cd carf-cockpit
npm install
npm run dev
```

### Option 2: Docker Compose (Full Stack)

```bash
# Start all services (API, Dashboard, Neo4j, Kafka, OPA)
docker compose up --build

# With demo data seeding
docker compose --profile demo up --build
```

**Services:**
- API: http://localhost:8000
- React Cockpit: http://localhost:5175
- Neo4j Browser: http://localhost:7474
- OPA: http://localhost:8181

### Option 3: Test Mode (No API Keys Required)

```bash
# Set test mode to use offline stubs

# Linux/macOS:
export CARF_TEST_MODE=1

# Windows PowerShell:
$env:CARF_TEST_MODE="1"

# Run with mocked LLM responses
python -m src.main
```

## Configuration

Create a `.env` file in the project root:

```bash
# Required: LLM Provider
LLM_PROVIDER=deepseek          # or "openai"
DEEPSEEK_API_KEY=sk-...        # Your DeepSeek API key
# OPENAI_API_KEY=sk-...        # If using OpenAI

# Optional: Human-in-the-Loop
HUMANLAYER_API_KEY=hl-...      # For Slack/Email approvals

# Optional: Observability
LANGSMITH_API_KEY=ls-...       # For LangSmith tracing

# Optional: Data Storage
CARF_DATA_DIR=./var            # Dataset storage location

# Optional: Services
NEO4J_URI=bolt://localhost:7687
KAFKA_ENABLED=false
OPA_ENABLED=false
```

## Core Architecture

```
Query -> Cynefin Router -> [Clear | Complicated | Complex | Chaotic | Disorder]
  Clear        -> Deterministic Runner (lookup)
  Complicated  -> Causal Inference Engine (DoWhy/EconML)
  Complex      -> Bayesian Active Inference (PyMC)
  Chaotic      -> Circuit Breaker (emergency stop)
  Disorder     -> Human Escalation

All paths -> Guardian (policy check) -> [Approve | Reject | Escalate to Human]
```

### Cynefin Domains

| Domain | Description | Handler | Use Case |
|--------|-------------|---------|----------|
| Clear | Cause-effect obvious | Deterministic automation | Standard procedures |
| Complicated | Requires expert analysis | Causal inference engine | Impact estimation |
| Complex | Emergent, probe required | Bayesian active inference | Uncertainty exploration |
| Chaotic | Crisis mode | Circuit breaker | Emergency response |
| Disorder | Cannot classify | Human escalation | Ambiguous inputs |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/query` | POST | Process query through CARF pipeline |
| `/domains` | GET | List Cynefin domains |
| `/scenarios` | GET | List demo scenarios |
| `/scenarios/{id}` | GET | Fetch scenario payload |
| `/datasets` | POST | Upload dataset to registry |
| `/datasets` | GET | List stored datasets |
| `/datasets/{id}/preview` | GET | Preview dataset rows |

### Example API Calls

**Simple Query:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did our costs increase by 15%?"}'
```

**Causal Analysis:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Estimate impact of discount on churn",
    "causal_estimation": {
      "treatment": "discount",
      "outcome": "churn",
      "covariates": ["region", "tenure"],
      "data": [
        {"discount": 0.1, "churn": 0, "region": "NA", "tenure": 12},
        {"discount": 0.0, "churn": 1, "region": "EU", "tenure": 3}
      ]
    }
  }'
```

**Bayesian Inference:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Update belief on conversion rate",
    "bayesian_inference": {
      "successes": 42,
      "trials": 100
    }
  }'
```

---

## 🚀 Get Started: Test the Platform

> [!TIP]
> The platform is **ready to test** with built-in demo scenarios or your own data. No complex setup needed—just start the servers and explore.

### Option A: Run a Pre-Built Demo Scenario

CYNEPIC includes pre-built scenarios that cover the main analytical domains:

| Scenario | Analysis Type | What It Tests |
|----------|---------------|---------------|
| **Scope 3 Attribution** | Causal | Supplier sustainability impact estimation |
| **Discount vs Churn** | Causal | Effect estimation w/ refutation tests |
| **Conversion Belief** | Bayesian | Prior/posterior belief updates |
| **Supply Chain Resilience** | Causal | Full E2E with custom data (see Option B) |

**To run a demo:**
1. Open the React dashboard: `http://localhost:5175`
2. Select a scenario card from the list.
3. Click a suggested query to run the analysis.
4. Explore the **Cynefin classification**, **Causal DAG**, and **Guardian Panel**.

See [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) for a step-by-step guide.

### Option B: Onboard Your Own Data

Bring your own CSV to run causal analysis:

1. **Generate Sample Data** (optional): `python generate_chain_data.py` to create `supply_chain_resilience.csv`.
2. **Open Data Onboarding**: In the dashboard, click "Upload your own data".
3. **Map Variables**: Identify the **Treatment** (e.g., `climate_stress_index`), **Outcome** (e.g., `disruption_risk_percent`), and **Confounders**.
4. **Run Analysis**: The platform will automatically classify the query, build a causal model, and display results.

See [docs/END_USER_TESTING_GUIDE.md](docs/END_USER_TESTING_GUIDE.md) for detailed instructions.

---

## Project Structure

```
projectcarf/
├── src/
│   ├── core/           # State schemas, LLM config
│   ├── services/       # Causal, Bayesian, HumanLayer
│   ├── workflows/      # LangGraph nodes and graph
│   ├── utils/          # Telemetry, caching, resiliency
│   └── main.py         # FastAPI entry point
├── carf-cockpit/       # React (Vite + TypeScript) dashboard
├── config/             # YAML configs (policies, prompts)
├── demo/               # Demo scenarios and sample data
├── tests/              # Unit and integration tests
├── docs/               # Documentation
└── docker-compose.yml  # Full stack deployment
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run manual test suite
python test_carf.py

# Type checking
mypy src/ --strict

# Linting
ruff check src/ tests/
```

## Dashboard Views

### End-User View
- Query input with suggested queries
- Simulation controls (sliders)
- Cynefin classification with domain scores
- Bayesian belief state with distribution chart
- Causal DAG visualization
- Guardian policy check with approval workflow

### Developer View
- Execution trace timeline
- Performance metrics
- DAG structure explorer
- State snapshots (JSON)

### Executive View
- Expected impact hero card
- KPI dashboard
- Proposed action summary
- Policy compliance overview

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes
- [PRD and Blueprint](docs/PRD.md) - Product requirements
- [Data Layer](docs/DATA_LAYER.md) - Data architecture
- [UI/UX Guidelines](docs/CARF_UIX_INTERACTION_GUIDELINES.md) - Design system
- [OPA Policy](docs/OPA_POLICY.md) - Enterprise policy setup
- [Demo Walkthrough](docs/DEMO_WALKTHROUGH.md) - Step-by-step demo
- [End-User Testing Guide](docs/END_USER_TESTING_GUIDE.md) - Validate the demo flow and integrations
- [Security Guidelines](docs/SECURITY_GUIDELINES.md) - Release readiness checklist
- [LLM Agentic Strategy](docs/LLM_AGENTIC_STRATEGY.md) - LLM roles, guardrails, model selection
- [Self-Healing Architecture](docs/SELF_HEALING_ARCHITECTURE.md) - Reflection, human escalation, adaptive recovery
- [End-to-End Context Flow](docs/END_TO_END_CONTEXT_FLOW.md) - State propagation and memory/audit integration
- [Integration Guide](docs/INTEGRATION_GUIDE.md) - Enterprise integration patterns (ERP, Cloud)
- [Future Roadmap](docs/FUTURE_ROADMAP.md) - Development path and vision

## For Contributors

We welcome contributions! Please review the following guides based on your interest:

| I want to... | Start here |
|--------------|------------|
| **Add a new demo use case** | [docs/RFC_UIX_001_SCENARIO_REGISTRY.md](docs/RFC_UIX_001_SCENARIO_REGISTRY.md) - How to add new scenarios to the registry. |
| **Integrate CYNEPIC with another system** (ERP, Cloud) | [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) - API usage, data ingestion patterns, security. |
| **Test the platform demos end-to-end** | [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) and [docs/END_USER_TESTING_GUIDE.md](docs/END_USER_TESTING_GUIDE.md) |
| **Understand the future vision** | [docs/FUTURE_ROADMAP.md](docs/FUTURE_ROADMAP.md) - Planned features and areas for improvement. |
| **Review contribution guidelines** | [CONTRIBUTING.md](CONTRIBUTING.md) - Code standards, commit messages, PR process. |

### Quick Contribution Steps

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and run tests: `pytest tests/ -v`
4. Commit with a descriptive message: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Open a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - Workflow orchestration
- [DoWhy](https://github.com/py-why/dowhy) - Causal inference
- [PyMC](https://github.com/pymc-devs/pymc) - Bayesian modeling
- [HumanLayer](https://humanlayer.dev/) - Human-in-the-loop SDK
