# CARF Development Reference

> Last Updated: 2026-02-21
> Current Phase: Phase 15 - CYNEPIC UIX Rehaul Complete

## Quick Start

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Or PowerShell
.\.venv\Scripts\python.exe -m <command>

# Run tests
.\.venv\Scripts\python.exe -m pytest tests/unit/ -v

# Run full test suite with env
python -c "from dotenv import load_dotenv; load_dotenv(); import subprocess; subprocess.run(['python', '-m', 'pytest', 'tests/unit/', '-v'])"

# Run the CARF test script
.\.venv\Scripts\python.exe scripts/test_carf.py
```

---

## Project Structure

```
projectcarf/
  .venv/                      # Virtual environment (Python 3.13)
  .env                        # Environment configuration (DO NOT COMMIT)
  .env.example                # Environment template
  .gitignore                  # Git ignore rules
  pyproject.toml              # Project dependencies and config
  CURRENT_STATUS.md           # Project status tracker
  DEV_REFERENCE.md            # This file
  AGENTS.md                   # Agent architecture docs

  carf-cockpit/               # React Platform Cockpit (Vite + TypeScript + Tailwind)
    src/
      components/carf/        # 47 React components (incl. MarkdownRenderer, AgentFlowChart)
      __tests__/              # Frontend test suite (17 test files, 201 tests)
      services/               # API client layer (apiService.ts)
      hooks/                  # Custom React hooks (useProactiveHighlight, useVisualizationConfig, etc.)
      types/                  # TypeScript type definitions

  demo/
    data/                     # 8 sample datasets (scope3, supply_chain, pricing, etc.)
    payloads/                 # 10 demo request payloads
    scenarios.json            # Scenario registry (10 scenarios across all 5 Cynefin domains)

  config/
    agents.yaml               # Agent configurations
    policies.yaml             # Guardian policies
    prompts.yaml              # LLM prompts

  docs/
    PRD.md                    # Product requirements
    DATA_LAYER.md             # Data architecture
    UI_UIX_VISION_REACT.md    # React architecture vision
    WALKTHROUGH.md            # Full testing walkthrough
    DEMO_WALKTHROUGH.md       # Demo walkthrough
    DEV_PRACTICES_AND_LIVING_DOCS.md
    CARF_UIX_INTERACTION_GUIDELINES.md
    archive/                  # Legacy docs (Streamlit UI, etc.)

  src/
    core/
      state.py                # EpistemicState, CynefinDomain, etc.
      llm.py                  # LLM configuration (DeepSeek/OpenAI)
    api/routers/              # 12 modularized API routers (incl. feedback, CSL)
    services/                 # 16 services
      causal.py               # Causal Inference Engine
      bayesian.py             # Bayesian Active Inference
      human_layer.py          # Human-in-the-loop service
      chimera_oracle.py       # ChimeraOracle (fast causal predictions)
      visualization_engine.py # Visualization config per Cynefin domain
      dataset_store.py        # Local dataset registry (SQLite + JSON)
      neo4j_service.py        # Neo4j graph persistence
      kafka_audit.py          # Kafka audit trail
    workflows/
      router.py               # Cynefin domain classifier
      guardian.py             # Policy enforcement layer
      graph.py                # LangGraph workflow
    mcp/                      # MCP server (15 cognitive tools)
    utils/
      resiliency.py           # Retry, circuit breaker utils
    main.py                   # FastAPI application

  tests/
    unit/                     # 27 unit test files
    e2e/                      # End-to-end tests (gold standard scenarios)
    integration/              # API flow integration tests
    deepeval/                 # LLM output quality evaluation (8 test files)
    eval/                     # Workflow integration tests
    mocks/                    # Mock HumanLayer, Neo4j, etc.

  benchmarks/                 # Technical & use-case benchmarks (H1-H9)
    technical/                # Router, causal, bayesian, guardian, performance, chimera
    use_cases/                # End-to-end industry scenarios
    baselines/                # Raw LLM baseline comparison
    reports/                  # Unified report generation

  tla_specs/                  # TLA+ formal verification (StateGraph, EscalationProtocol)

  scripts/                    # Demo seed scripts, data generation, test scripts
```

---

## Architecture Overview

```
User Query -> Cynefin Router -> Domain -> Solver -> Guardian -> [Approved | Rejected | Escalate]

Clear        -> Deterministic Runner
Complicated -> Causal Inference Engine
Complex     -> Bayesian Active Inference
Chaotic     -> Circuit Breaker
Disorder    -> HumanLayer Escalation

Optional persistence: Neo4j for causal graphs and analysis history
```

---

## Key Components

### 1. EpistemicState (`src/core/state.py`)
Central state object passed through the workflow:
```python
@dataclass
class EpistemicState:
    session_id: UUID
    cynefin_domain: CynefinDomain  # Clear | Complicated | Complex | Chaotic | Disorder
    domain_confidence: float       # 0.0-1.0
    domain_entropy: float          # Measure of uncertainty
    user_input: str
    reasoning_chain: list[ReasoningStep]
    causal_evidence: CausalEvidence | None
    guardian_verdict: GuardianVerdict | None
    # ... more fields
```

### 2. Causal Inference Engine (`src/services/causal.py`)
LLM-assisted causal reasoning:
```python
engine = CausalInferenceEngine()
result, graph = await engine.analyze("Why did costs increase?")

# result: CausalAnalysisResult
#   - hypothesis: CausalHypothesis (treatment -> outcome)
#   - effect_estimate: float
#   - confidence_interval: (float, float)
#   - passed_refutation: bool

# graph: CausalGraph
#   - nodes: list[CausalVariable]
#   - edges: list[(cause, effect)]
```

### 3. Neo4j Service (`src/services/neo4j_service.py`)
Persistent causal graph storage:
```python
from src.services import get_neo4j_service

neo4j = get_neo4j_service()
await neo4j.connect()

# Save graph
await neo4j.save_causal_graph(graph, session_id="abc123")

# Save full analysis
await neo4j.save_analysis_result(result, graph, session_id, query)

# Query historical
analyses = await neo4j.find_similar_analyses("price", "churn", limit=5)

# Find causal paths
paths = await neo4j.get_causal_path("marketing_spend", "revenue")

# Health check
status = await neo4j.health_check()
```

### 4. Guardian Layer (`src/workflows/guardian.py`)
Policy enforcement before actions execute:
```python
guardian = Guardian()
decision = guardian.evaluate(state)
# decision.verdict: APPROVED | REJECTED | REQUIRES_ESCALATION
# decision.violations: list[PolicyViolation]
```

### 5. Dataset Registry (`src/services/dataset_store.py`)
Local dataset storage for the research demo:
```python
from src.services.dataset_store import get_dataset_store

store = get_dataset_store()
metadata = store.create_dataset(
    name="demo",
    description="sample",
    data=[{"x": 1, "y": 2}],
)

rows = store.load_preview(metadata.dataset_id, limit=5)
```

Testing note: `DatasetStore(storage_mode="memory")` uses in-memory storage to
avoid filesystem restrictions in CI or locked-down Windows environments.

---

## Environment Variables

```bash
# Required
LLM_PROVIDER=deepseek          # or "openai"
DEEPSEEK_API_KEY=sk-...        # DeepSeek API key

# Neo4j (Phase 3)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Optional
HUMANLAYER_API_KEY=hl_...      # Human-in-the-loop
LANGSMITH_API_KEY=ls-...       # Tracing
CARF_DATA_DIR=./var            # Dataset registry storage (optional)

# Kafka (Phase 3)
KAFKA_ENABLED=false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=carf_decisions
KAFKA_CLIENT_ID=carf

# OPA (Guardian Policy)
OPA_ENABLED=false
OPA_URL=http://localhost:8181
OPA_POLICY_PATH=/v1/data/carf/guardian/allow
OPA_TIMEOUT_SECONDS=5

Kafka audit events include `schema_version` and `event_id` fields (see `src/services/kafka_audit.py`).

OPA sample policy: `config/opa/guardian.rego` (see `docs/OPA_POLICY.md`).

# Testing
CARF_TEST_MODE=1               # Use deterministic offline LLM stubs
```

---

## API Payload Notes

`/query` accepts optional statistical configs:

- `causal_estimation`: DoWhy/EconML config (treatment/outcome/covariates + data)
- `bayesian_inference`: PyMC config (observations or successes/trials)
- `dataset_selection`: dataset registry mapping (dataset_id + column roles)

Limits: `causal_estimation.data` up to 5000 rows, `bayesian_inference.observations` up to 10000 values.

---

## React Cockpit (carf-cockpit)

```bash
cd carf-cockpit
npm install
npm run dev
# Opens at http://localhost:5175
```

The React Cockpit includes 44 components: three-view architecture (Analyst/Executive/Developer),
Cynefin domain visualizations (all 5 domains with Plotly.js charts), simulation arena with
benchmarking, data onboarding wizard, feedback collection, and MCP server integration.

## Demo Seeding

```bash
python scripts/seed_demo.py
python scripts/publish_demo_event.py
```

Demo payloads live in `demo/payloads/`.
`seed_demo.py` forces `CARF_TEST_MODE=1` to avoid API keys.

---

## Simulated Use Cases

The platform includes pre-configured **demo scenarios** that run real analysis workflows with simulated data - no mockups or hardcoded values.

### Available Scenarios

| ID | Name | Domain | Description |
|---|---|---|---|
| `scope3_attribution` | Scope 3 Attribution | Complicated | Causal analysis of supplier sustainability programs |
| `causal_discount_churn` | Discount vs Churn | Complicated | Causal effect of discount offers on customer churn |
| `bayesian_conversion_rate` | Conversion Belief Update | Complex | Bayesian inference on website conversion rates |
| `renewable_energy_roi` | Renewable Energy ROI | Complicated | ROI from renewable energy investments across facilities |
| `shipping_carbon_footprint` | Shipping Mode Analysis | Complicated | Shipping mode changes and carbon footprint impact |
| `supply_chain_resilience` | Supply Chain Resilience | Complicated | Climate stress impact on supply chain disruption risk |
| `pricing_optimization` | Pricing Strategy | Complicated | Causal impact of price changes on sales volume |
| `market_adoption` | Market Adoption | Complex | Bayesian uncertainty in new product market adoption |
| `crisis_response` | Crisis Response | Chaotic | Critical supplier failure requiring immediate stabilization |
| `data_lookup` | Inventory Lookup | Clear | Simple deterministic inventory and product queries |

### How to Use Scenarios

**Via React Cockpit (UI):**
1. Launch cockpit: `cd carf-cockpit && npm run dev` (opens at http://localhost:5175)
2. Select a scenario from the Data Onboarding Wizard or header dropdown
3. Enter a query (or use suggested query)
4. Click "Analyze" to run the full analysis pipeline
5. View real results in Cynefin, Causal, Bayesian, and Guardian panels
6. Switch views (Analyst / Executive / Developer) for different perspectives

**Via API:**
```bash
# Get available scenarios
curl http://localhost:8000/scenarios

# Get scenario payload
curl http://localhost:8000/scenarios/scope3_attribution

# Run analysis with scenario payload
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d @demo/payloads/scope3_attribution.json
```

### Adding New Scenarios

1. Create payload JSON in `demo/payloads/`
2. Register in `demo/scenarios.json`
3. Include `query`, `context`, and optionally `causal_estimation` / `bayesian_inference` configs

---

## Docker Compose Demo Stack

```bash
docker compose up --build
docker compose --profile demo run --rm seed
```

React Cockpit runs on `http://localhost:5175`, FastAPI on `http://localhost:8000`.
Kafka is exposed on `localhost:29092` for host clients.
Dataset registry storage lives under `./var` (bind-mounted in compose).

---

## Testing

```bash
# All unit tests (see output for counts; one known flaky test noted below)
.\.venv\Scripts\python.exe -m pytest tests/unit/ -v

# Neo4j tests only
.\.venv\Scripts\python.exe -m pytest tests/unit/test_neo4j_service.py -v

# With coverage
.\.venv\Scripts\python.exe -m pytest tests/unit/ --cov=src --cov-report=term-missing

# Integration tests (requires API keys)
python scripts/test_carf.py
```

### Known Test Issues
- Tests run in offline mode via `CARF_TEST_MODE=1` in `tests/conftest.py`

---

## Phase Status

### Phase 1 - Foundation
- [x] Project scaffolding
- [x] EpistemicState schema
- [x] Config YAML templates
- [x] Resiliency utilities
- [x] Cynefin Router
- [x] HumanLayer Service
- [x] Guardian Layer
- [x] LangGraph Workflow

### Phase 2 - Cognitive Engines
- [x] DeepSeek LLM integration
- [x] Causal Inference Engine
- [x] Bayesian Active Inference
- [x] Test notebook

### Phase 3 - Persistence & Infrastructure (Complete)
- [x] Neo4j Integration - Complete
  - Async driver with connection pooling
  - CausalGraph persistence
  - CausalAnalysisResult persistence
  - Historical analysis queries
  - Causal path finding
  - Health check endpoint
- [x] Virtual environment setup
- [x] DoWhy/EconML integration (optional path + fallback)
- [x] PyMC integration (optional path + fallback)
- [x] Streamlit Dashboard (deprecated — replaced by React Cockpit)
- [x] Kafka Audit Trail

### Phase 4 - Research Demo UIX (Complete)
- [x] Scenario registry + UI selector
- [x] Dataset registry + CSV onboarding
- [x] Response badges (domain, verdict, confidence)
- [x] Color-coded confidence indicators (green/yellow/red)
- [x] Improved reasoning chain display with expandable steps

---

### Phase 5-11 - UIX, Explainability, CHIMEPIC (Complete)
- [x] React Cockpit (44 components, three-view architecture)
- [x] Explainability drill-down modals for all analytical results
- [x] Confidence decomposition and zones
- [x] Data Onboarding Wizard with sample datasets
- [x] ConversationalResponse with confidence zones
- [x] FloatingChatTab, WalkthroughManager, OnboardingOverlay
- [x] ChimeraOracle fast causal predictions
- [x] CSL-Core policy engine integration
- [x] MCP server (15 cognitive tools)
- [x] Cynefin domain visualizations (all 5 domains with Plotly.js)
- [x] Feedback API (closed-loop learning)
- [x] Benchmark suite (6 technical + use case benchmarks)
- [x] TLA+ formal verification specs

## Remaining Gaps (Phase 12+)

- ChimeraOracle not yet wired into LangGraph StateGraph (standalone API only)
- LightRAG / Vector Store (no implementation — semantic search missing)
- Guardian currency-aware comparisons ($50K USD ≠ ¥50K JPY)
- Router retraining pipeline from feedback data
- GitHub Actions CI workflow
- Demo GIF and live deployment

**Reference**: See `docs/UI_UIX_VISION_REACT.md` for React architecture specifications.

---

## Code Conventions

- Type hints: Required for all functions
- Async: All I/O operations are async
- Pydantic: Used for data validation
- Logging: `logging.getLogger("carf.<module>")`
- Singletons: Use `get_<service>()` pattern for services

---

## Useful Commands

```bash
# Lint
.\.venv\Scripts\python.exe -m ruff check src/

# Type check
.\.venv\Scripts\python.exe -m mypy src/

# Format
.\.venv\Scripts\python.exe -m ruff format src/

# Run API server
.\.venv\Scripts\python.exe -m src.main
```

---

## Recent Changes (2026-02-17)

- Documentation alignment pass: fixed 42+ stale references across all docs
- Frontend safety fixes: optional chaining on deep property access in AnalysisHistoryPanel, ConversationalResponse
- SimulationArena hooks order fix (React Rules of Hooks compliance)
- Benchmark suite integration into all walkthrough and evaluation docs
- AGENTS.md antipattern documentation (AP-1 through AP-8)

---

## Contact/Resume Context

To resume this session:
1. Open this project in Claude Code
2. Reference this file: `DEV_REFERENCE.md`
3. Check `CURRENT_STATUS.md` for latest status
4. Run tests to verify: `.\.venv\Scripts\python.exe -m pytest tests/unit/ -v`
