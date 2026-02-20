# Project CARF: CYNEPIC Architecture 0.5
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/b50309cd-0f03-4424-ad49-72cdc796ff14" />
**Complexity-Adaptive & Context-Aware Reasoning Fabric** - A research grade Architectural Blueprint & Decision Intelligence Simulation for more reliable and transparent data-driven decision making and Agentic AI Systems, combining complexity & context adaptability, causal inference, bayesian methods to quantify uncertainty & complexity
and epistemic awareness. 

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: BSL 1.1](https://img.shields.io/badge/License-BSL%201.1-red.svg)](LICENSE)
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

- **Cynefin-based Routing**: Automatic classification of query complexity across 5 domains.
- **Causal Inference Engine**: Discover DAGs, estimate effects, and run refutation tests via DoWhy/EconML.
- **Bayesian Exploration**: Quantify uncertainty and update beliefs with new evidence via PyMC.
- **Guardian Policy Layer**: Multi-layer enforcement (YAML + CSL-Core + OPA), human-in-the-loop, and audit trails.
- **ChimeraOracle Fast Predictions**: Pre-trained CausalForestDML models for <100ms causal effect scoring.
- **What-If Simulation Framework**: Multi-scenario comparison with 6 built-in realistic data generators.
- **CSL-Core Policy Verification**: Formal, deterministic policy rules with fail-closed safety.
- **Policy Scaffolding & Refinement**: Auto-generate domain-specific policies with adaptive refinement agents.
- **Three-View Dashboard**: Tailored views for Analysts, Developers, and Executives.
- **Dark/Light Theme**: Full dark mode support with system preference detection.
- **Actionable Insights**: Persona-specific recommendations, action items with effort badges, and analysis roadmaps.
- **Smart Reflector**: Hybrid heuristic + LLM self-correction for policy violations with observability.
- **Experience Buffer**: Semantic memory using sentence-transformers (all-MiniLM-L6-v2) with TF-IDF fallback for similar past analysis retrieval and domain pattern tracking.
- **Library API**: Notebook-friendly wrappers (`from src.api.library import classify_query, run_pipeline`).
- **Agent Transparency**: Track LLM usage, latency, cost, and quality scores across workflows.
- **Multi-Source Data Loading**: Load data from JSON, CSV, APIs, or Neo4j with automatic quality assessment.
- **Streaming Query Mode**: Server-sent events for real-time progressive responses.
- **EU AI Act Compliance**: Built-in compliance reporting and audit trail generation.
- **Data Lineage Tracking**: Full provenance chain for audit and reproducibility.
- **Router Retraining Pipeline**: Extract domain override feedback for DistilBERT fine-tuning.
- **MCP Server**: 18 cognitive tools exposed via Model Context Protocol for agentic AI integration.

### Data & Analytical Flows in CARF architecture 

<img width="2752" height="1536" alt="Dataflow blueprint" src="https://github.com/user-attachments/assets/e0eecb39-5813-4b83-9a42-0e735ba0dee8" />

### User Interface — React Cockpit (CARF Cockpit)

---

## Benchmark Results

CARF is evaluated against **9 falsifiable hypotheses** across 8 benchmark categories, using synthetic data with known ground truth and a raw LLM baseline (same model, no pipeline) for comparison. All benchmarks use fixed random seeds for full reproducibility.

### Overall Grade: A — 8/9 Hypotheses Passed

| # | Hypothesis | Measured | Threshold | Result |
|---|-----------|----------|-----------|--------|
| H1 | **Causal Accuracy** — DoWhy ATE vs raw LLM | MSE ratio **0.0009** (1,138x more accurate) | ≤ 0.5 | **PASS** |
| H2 | **Bayesian Calibration** — posterior coverage | **100%** (8/8 scenarios well-calibrated) | ≥ 90% | **PASS** |
| H3 | **Violation Detection** — Guardian catches all violations | **67%** detection (1 CSL rule gap), 0% false positives | 100% | FAIL |
| H4 | **Determinism** — same input → same Guardian decision | **100%** (5x repetitions) | ≥ 100% | **PASS** |
| H5 | **EU AI Act Compliance** — Art. 9, 12, 13, 14 | **100%** | ≥ 90% | **PASS** |
| H6 | **Latency Overhead** — CARF vs raw LLM | **3.5x** (9.3s avg vs 2.65s baseline) | ≤ 5x | **PASS** |
| H7 | **Hallucination Reduction** — grounded data queries | **100% reduction** (0% vs 6.7% baseline) | ≥ 40% | **PASS** |
| H8 | **ChimeraOracle Speedup** — Oracle vs full DoWhy | **32.7x faster, 3.4% accuracy loss** | ≥ 10x speed, <20% loss | **PASS** |
| H9 | Memory stability over 500+ queries | **0.2% RSS growth** | ≤ 10% | **PASS** |
| H10 | **Reflector Self-Correction** — repair rate for known violations | **80%** (4/5 scenarios) | ≥ 80% | **PASS** |
| H11 | **Resiliency** — circuit breaker accuracy & failure isolation | **100%** (6/6 tests) | ≥ 95% | **PASS** |

> Full machine-readable results: [`benchmarks/reports/unified_report.json`](benchmarks/reports/unified_report.json) | E2E: 11/13 scenarios (84.6%) | Text summary: [`benchmarks/reports/unified_report.txt`](benchmarks/reports/unified_report.txt)

### Indicated Use Cases

Based on the benchmark evidence, CARF is particularly suited for:

| Use Case | Why CARF Helps | Supporting Evidence |
|----------|---------------|---------------------|
| **Causal Decision Support** — supply chain, marketing attribution, policy evaluation | Separates cause from correlation with statistical rigor | H1: 1,138x more accurate causal estimates than raw LLM |
| **Risk Quantification Under Uncertainty** — investment, insurance, clinical trials, grid capacity | Calibrated posteriors with epistemic/aleatoric decomposition | H2: 100% calibrated across 8 Bayesian scenarios |
| **Regulated AI Systems** — EU AI Act, financial audit, healthcare decision support | Deterministic, compliant, and fully auditable | H4–H5: 100% determinism and compliance; H3: 67% violation detection (CSL rule gap) |
| **Strategic Analysis** — market entry, R&D allocation, scenario planning | Cynefin routing ensures the right analytical method per problem type | Router: 98% accuracy, F1 = 0.98 across 5 domains |

### Benchmark Data Sources & Methodology

All evaluation data is **synthetic with known ground truth**, enabling objective measurement. No proprietary or third-party datasets are required to reproduce results.

| Category | Description | Details |
|----------|-------------|---------|
| Causal (Synthetic) | 3 DGPs with known ATEs (linear, nonlinear, null) | n=500 each, confounded via logistic propensity scores. True ATEs: 3.0, 2.5, 0.0 |
| Causal (Industry) | 5 sector-specific DGPs with realistic confounding | Supply chain (n=500, ATE=−8.5 days), Healthcare (n=800), Marketing (n=600), Sustainability (n=400), Education (n=700) |
| Causal (Heterogeneous) | 1 DGP with age-dependent treatment effects | n=800, subgroup ATEs: young=4.0, middle=8.0, senior=12.0 |
| Bayesian (Normal) | 4 continuous-observation scenarios | Market returns (n=50), Crop yields (n=40), Supply chain lead times (n=60), Energy demand (n=80) |
| Bayesian (Binomial) | 4 success/trial count scenarios | Tech migration (45 trials), Drug trial (120 trials), Insurance (200 policies), Conversion (500 visitors) |
| Router | 456-query labeled test set across 5 Cynefin domains | Clear (101), Complicated (102), Complex (101), Chaotic (50), Disorder (102). Causal language boost for 100% Complicated accuracy |
| E2E Use Cases | 13 end-to-end scenarios with 420 data rows | Numpy-generated industry data across 7 sectors, causal_estimation auto-wiring |
| Baselines | Raw LLM (same model, no pipeline) on identical data | Router (50 balanced), causal ATE (8 DGPs), hallucination (5 test cases) |

**Methodology:** DoWhy for causal estimation with refutation tests, PyMC for Bayesian posterior inference, balanced Cynefin domain sampling for router evaluation. Baselines use the same LLM model (DeepSeek) without the CARF pipeline. All benchmark scripts and data generators are in [`benchmarks/`](benchmarks/).

---

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

# Optional: CSL-Core Policy Engine
CSL_ENABLED=false              # Enable formal policy verification
CSL_POLICY_DIR=config/policies # Directory for CSL policy files
CSL_FAIL_CLOSED=true           # Fail-closed on CSL errors (recommended)
```

## Library Usage (Notebooks & Data Pipelines)

CARF services can be used directly in Jupyter notebooks or Python scripts:

```python
from src.api.library import classify_query, run_causal, run_bayesian, run_pipeline, query_memory

# Classify a query
result = await classify_query("Why did costs increase 15%?")
print(result["domain"], result["confidence"])

# Run full pipeline
pipeline = await run_pipeline("Does supplier diversification reduce disruptions?")
print(pipeline["response"])

# Search past analyses
similar = await query_memory("supply chain risk")
print(similar["matches"])
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
  Reject -> Smart Reflector (hybrid heuristic + LLM repair) -> Retry

All results -> Experience Buffer (sentence-transformer semantic memory for similar query retrieval)
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

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/query` | POST | Process query through CARF pipeline |
| `/query/transparent` | POST | Query with full transparency metrics |
| `/domains` | GET | List Cynefin domains |
| `/scenarios` | GET | List demo scenarios |
| `/scenarios/{id}` | GET | Fetch scenario payload |
| `/datasets` | POST | Upload dataset to registry |
| `/datasets` | GET | List stored datasets |
| `/datasets/{id}/preview` | GET | Preview dataset rows |

### Insights & Transparency Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/insights/generate` | POST | Generate persona-based insights |
| `/insights/enhanced` | POST | Enhanced insights with action items and roadmap |
| `/insights/types` | GET | List available insight types |
| `/experience/similar` | GET | Find similar past analyses (semantic memory) |
| `/experience/patterns` | GET | Aggregated domain-level patterns |
| `/transparency/reliability` | POST | Assess analysis reliability |
| `/transparency/agents` | GET | Get agent registry info |
| `/guardian/status` | GET | Get compliance status |
| `/guardian/policies` | GET | List configured policies |
| `/feedback/retraining-readiness` | GET | Check Router retraining readiness |

### Agent Tracking Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workflow/start` | POST | Start workflow tracking |
| `/workflow/complete` | POST | Complete workflow and aggregate metrics |
| `/workflow/trace/{id}` | GET | Get full execution trace |
| `/workflow/recent` | GET | Get recent workflow traces |
| `/agents/stats` | GET | Get agent performance statistics |
| `/agents/comparison` | GET | Get agent comparison data |

### Data Loading Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/data/load/json` | POST | Load JSON data with quality assessment |
| `/data/load/csv` | POST | Load CSV data with quality assessment |
| `/data/{id}` | GET | Retrieve loaded data by ID |
| `/data/quality/levels` | GET | Get available quality levels |
| `/data/detect-schema` | POST | Auto-detect schema from uploaded data |
| `/data/cache` | DELETE | Clear data cache |

### Simulation & What-If Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/simulations/run` | POST | Run what-if scenario simulation |
| `/simulations/compare` | POST | Compare multiple simulation results |
| `/simulations/{id}/status` | GET | Get simulation status |
| `/simulations/{id}/rerun` | POST | Rerun a simulation |
| `/simulations/generators` | GET | List available data generators |
| `/simulations/generate` | POST | Generate synthetic data with causal structure |
| `/simulations/assess-realism` | POST | Assess scenario realism score |
| `/simulations/run-transparent` | POST | Enhanced simulation with transparency |

### ChimeraOracle (Fast Predictions) Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oracle/models` | GET | List trained oracle models |
| `/oracle/train` | POST | Train CausalForestDML model on scenario data |
| `/oracle/predict` | POST | Fast causal prediction (<100ms) |
| `/oracle/models/{id}` | GET | Get model metadata for scenario |

### Visualization & Configuration Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/visualization-config` | GET | Combined domain + context visualization config |
| `/config/visualization` | GET | Context-aware visualization settings |
| `/config/status` | GET | System configuration status |
| `/config/validate` | POST | Validate configuration |
| `/router/config` | GET/PUT/PATCH | Manage Cynefin Router configuration |
| `/guardian/config` | GET/PUT/PATCH | Manage Guardian policy configuration |

### Advanced Query Modes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query/stream` | POST | Streaming query with server-sent events |
| `/query/fast` | POST | Fast query mode via Chimera Oracle |
| `/chat` | POST | Chat interface with Socratic mode |

### Escalation & Compliance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/escalations` | GET | List pending human escalations |
| `/escalations/{id}` | GET | Get escalation details |
| `/escalations/{id}/resolve` | POST | Resolve an escalation |
| `/transparency/compliance` | POST | EU AI Act compliance report |
| `/transparency/data-quality` | POST | Assess data quality |
| `/transparency/guardian` | POST | Guardian decision transparency |
| `/sessions/{id}/lineage` | GET | Data lineage and provenance tracking |

### Developer & Diagnostics Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/developer/state` | GET | Full system state dump |
| `/developer/logs` | GET | Filtered log entries (layer, level, limit) |
| `/developer/ws` | WebSocket | Live log streaming |
| `/analyze` | POST | File analysis for CSV/JSON |
| `/agent/suggest-improvements` | POST | Automated improvement suggestions |
| `/explain` | POST | Generate explanations for analyses |
| `/explain/{domain}/{element}` | GET | Domain-specific element explanations |
| `/benchmarks/run-all` | POST | Run all benchmark suites |
| `/feedback` | POST | Submit analysis feedback |
| `/summary/executive` | POST | Generate executive summary |

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

1. **Generate Sample Data** (optional): `python scripts/generate_chain_data.py` to create `supply_chain_resilience.csv`.
2. **Open Data Onboarding**: In the dashboard, click "Upload your own data".
3. **Map Variables**: Identify the **Treatment** (e.g., `climate_stress_index`), **Outcome** (e.g., `disruption_risk_percent`), and **Confounders**.
4. **Run Analysis**: The platform will automatically classify the query, build a causal model, and display results.

See [docs/END_USER_TESTING_GUIDE.md](docs/END_USER_TESTING_GUIDE.md) for detailed instructions.

---

## Project Structure

```
projectcarf/
├── src/
│   ├── core/           # State schemas (EpistemicState), LLM config
│   ├── services/       # Causal, Bayesian, Simulation, Transparency, ChimeraOracle,
│   │                   # CSL Policy, Policy Scaffolding, Chat, Insights, Explanations
│   ├── workflows/      # LangGraph graph, Guardian, Cynefin Router
│   ├── utils/          # Telemetry, caching, circuit breaker, resiliency
│   └── main.py         # FastAPI entry point (60+ endpoints)
│   ├── api/            # FastAPI routers (modularized endpoints)
├── carf-cockpit/       # React (Vite + TypeScript) dashboard
├── config/
│   ├── agents.yaml     # Agent configurations
│   ├── policies.yaml   # Guardian YAML policies
│   ├── policies/       # CSL-Core formal policy definitions
│   └── policy_scaffolds/ # Domain-specific policy templates
├── demo/               # Demo scenarios and sample data
├── tests/
│   ├── unit/           # 35 unit test files
│   ├── deepeval/       # LLM quality evaluation tests
│   ├── e2e/            # End-to-end gold standard tests
│   └── integration/    # API flow integration tests
├── benchmarks/         # Technical & use-case benchmarks (H1-H9 hypotheses)
├── tla_specs/          # TLA+ formal verification specs
├── scripts/            # Training, data generation, evaluation scripts
├── docs/               # 27 documentation files
└── docker-compose.yml  # Full stack deployment
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run manual test suite
python scripts/test_carf.py

# Type checking
mypy src/ --strict

# Linting
ruff check src/ tests/
```

### LLM Quality Evaluation (DeepEval)

CARF includes comprehensive LLM output quality evaluation using [DeepEval](https://github.com/confident-ai/deepeval):

```bash
# Install with evaluation dependencies
pip install -e ".[dev,evaluation]"

# Run DeepEval tests
pytest tests/deepeval/ -v

# Run with DeepEval CLI (parallel execution)
deepeval test run tests/deepeval/ -n 4
```

**Quality Metrics Evaluated:**
- **Relevancy Score**: How well responses address user queries
- **Hallucination Risk**: Detection of fabricated content
- **Reasoning Depth**: Quality of reasoning and justification
- **UIX Compliance**: Adherence to transparency standards (Why? How confident? Based on what?)

See [Evaluation Framework Documentation](docs/EVALUATION_FRAMEWORK.md) for details.

## Dashboard Views

### Analyst View
- Query input with intelligent suggestions
- Simulation controls (sliders)
- Cynefin classification with domain scores and entropy
- Bayesian belief state with distribution chart
- Causal DAG visualization
- Guardian policy check with approval workflow
- **Transparency Panel** with agent reliability and data quality
- **Insights Panel** with actionable recommendations

### Developer View
- Execution trace timeline
- Performance metrics (latency, tokens, cost)
- DAG structure explorer
- State snapshots (JSON)
- **Agent Comparison Panel** with LLM performance tracking
- **Data Flow Visualization**
- Live log streaming via WebSocket
- DeepEval quality metrics integration
- **Domain-Specific Views** for all 5 Cynefin domains:
  - Clear: Decision checklist with step tracking
  - Complicated: Expert analysis with causal effect summary
  - Complex: Uncertainty exploration with epistemic/aleatoric breakdown
  - Chaotic: Circuit breaker with rapid response controls
  - Disorder: Clarification prompts with human escalation

### Executive View
- Expected impact hero card
- **Dynamic KPI Dashboard** (0-10 scoring with real data)
- Proposed action summary
- Policy compliance overview
- **Actionable Insights** for decision-makers
- Export and share functionality

### Data Visualization
- **PlotlyChart** unified wrapper supporting waterfall, radar, sankey, and gauge charts
- **CynefinVizConfig** backend-driven domain-specific visualization strategy
- **Context-adaptive charts**: color schemes, chart types, and interaction modes adapt per Cynefin domain and business context (sustainability, financial, operational, risk)
- **useVisualizationConfig** React hook with caching and offline fallbacks

### Theme Support
- **Dark/Light Mode Toggle** in header
- System preference detection
- Persistent theme preference (localStorage)

## Documentation

### Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes
- [Complete Walkthrough](docs/WALKTHROUGH.md) - Comprehensive guide for all user types (Analyst, Developer, Executive)
- [Demo Walkthrough](docs/DEMO_WALKTHROUGH.md) - Step-by-step demo scenarios
- [End-User Testing Guide](docs/END_USER_TESTING_GUIDE.md) - Validate the demo flow and integrations

### Architecture & Design
- [PRD and Blueprint](docs/PRD.md) - Product requirements
- [Data Layer](docs/DATA_LAYER.md) - Data architecture
- [UI/UX Guidelines](docs/CARF_UIX_INTERACTION_GUIDELINES.md) - Design system
- [LLM Agentic Strategy](docs/LLM_AGENTIC_STRATEGY.md) - LLM roles, guardrails, model selection
- [Self-Healing Architecture](docs/SELF_HEALING_ARCHITECTURE.md) - Reflection, human escalation, adaptive recovery
- [End-to-End Context Flow](docs/END_TO_END_CONTEXT_FLOW.md) - State propagation and memory/audit integration

### Operations & Integration
- [OPA Policy](docs/OPA_POLICY.md) - Enterprise policy setup
- [Security Guidelines](docs/SECURITY_GUIDELINES.md) - Release readiness checklist
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

Business Source License 1.1 (BSL) - see [LICENSE](LICENSE) for details.
For production use, see [COMMERCIAL_LICENSE](COMMERCIAL_LICENSE.md).


## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - Workflow orchestration
- [DoWhy](https://github.com/py-why/dowhy) - Causal inference
- [PyMC](https://github.com/pymc-devs/pymc) - Bayesian modeling
- [HumanLayer](https://humanlayer.dev/) - Human-in-the-loop SDK
