# CARF Development Reference

> Last Updated: 2026-03-16
> Current Phase: Phase 17 Complete → Phase 18 Designed (SRR Hardening & Operational Intelligence)

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
  pyproject.toml              # Project dependencies and config
  research.md                 # Neurosymbolic scaling research (33 academic references)
  CURRENT_STATUS.md           # Project status tracker (Phase 18 design)
  DEV_REFERENCE.md            # This file
  AGENTS.md                   # Agent architecture docs + SRR model + antipatterns

  carf-cockpit/               # React Platform Cockpit (Vite + TypeScript + Tailwind)
    src/
      components/carf/        # 58 React components (4-view architecture)
      __tests__/              # Frontend test suite (26 test files, 235+ tests)
      services/               # API client + Firebase config (apiService.ts, firebaseConfig.ts)
      hooks/                  # 5 custom hooks (useAuth, useTheme, useCarfApi, etc.)
      types/                  # TypeScript type definitions (incl. Phase 17 interfaces)

  demo/
    data/                     # 8 sample datasets (scope3, supply_chain, pricing, etc.)
    payloads/                 # 10 demo request payloads
    scenarios.json            # Scenario registry (10 scenarios across all 5 Cynefin domains)

  config/
    agents.yaml               # Agent configurations
    policies.yaml             # Guardian policies (immutable — requires human review)
    prompts.yaml              # LLM prompts
    policies/                 # 5 CSL formal policy files (35 rules)
    federated_policies/       # 6 domain-owner YAML policies
    governance_boards/        # 4 compliance board templates (EU AI Act, CSRD, etc.)
    policy_scaffolds/         # 5 policy scaffold templates
    opa/                      # OPA Rego rules

  docs/                       # 40+ architecture docs
    PHASE17_ARCHITECTURE.md   # Causal world model, NeSy, H-Neuron
    CARF_RSI_ANALYSIS.md      # RSI safety analysis (SRR model)
    FUTURE_ROADMAP.md         # Research-informed roadmap (Phase 18+)
    INTELLECTUAL_PROPERTY.md  # IP registry
    INTEGRATION_GUIDE.md      # REST, event-driven, batch, ERP patterns
    EVALUATION_FRAMEWORK.md   # DeepEval quality metrics
    LLM_AGENTIC_STRATEGY.md  # LLM usage by layer
    SELF_HEALING_ARCHITECTURE.md  # Self-correction + escalation
    archive/                  # Legacy docs

  src/
    core/
      state.py                # EpistemicState + CounterfactualEvidence + NeurosymbolicEvidence
      llm.py                  # Multi-provider LLM (DeepSeek, OpenAI, Anthropic, Google GenAI)
      database.py             # SQLite/PostgreSQL factory (Cloud SQL support, Phase 17)
      deployment_profile.py   # research/staging/production profiles
      governance_models.py    # 15 Pydantic governance models
    api/
      auth.py                 # Firebase JWT middleware (Phase 17)
      middleware.py           # Profile-aware security (auth, rate limiting, size limits)
      routers/                # 16 API routers (80+ endpoints)
    services/                 # 30+ services
      causal.py               # Causal Inference Engine (DoWhy/EconML)
      bayesian.py             # Bayesian Active Inference (PyMC)
      causal_world_model.py   # SCMs, do-calculus, forward simulation (Phase 17)
      counterfactual_engine.py # Pearl Level-3 counterfactuals (Phase 17)
      neurosymbolic_engine.py # LLM + forward-chaining + shortcut detection (Phase 17)
      h_neuron_interceptor.py # Hallucination sentinel (Phase 17)
      chimera_oracle.py       # CausalForestDML fast predictions (<100ms)
      smart_reflector.py      # Hybrid heuristic + LLM self-correction
      governance_service.py   # MAP-PRICE-RESOLVE orchestrator
      rag_service.py          # 3-layer NeSy-augmented RAG (vector + graph + symbolic)
      agent_memory.py         # Persistent cross-session memory (reflexion-weighted)
      experience_buffer.py    # Semantic memory (sentence-transformers + TF-IDF)
      # ... 20+ additional services
    workflows/
      router.py               # Cynefin router (DistilBERT + LLM + entropy + causal boost)
      guardian.py             # Multi-layer policy engine (YAML + CSL-Core + OPA)
      graph.py                # LangGraph StateGraph orchestration
    mcp/                      # MCP server (7 modules, 18 cognitive tools)
    utils/                    # Telemetry, resiliency, caching, currency

  tests/
    unit/                     # 55+ unit test files (980+ tests)
    e2e/                      # End-to-end gold standard tests
    integration/              # API flow + Neo4j integration tests
    deepeval/                 # LLM output quality evaluation (8 test files)
    eval/                     # Workflow integration tests
    mocks/                    # Mock HumanLayer, Neo4j, etc.

  benchmarks/                 # Technical & use-case benchmarks (H0-H39)
    technical/                # 30+ benchmark scripts across 9 categories
    baselines/                # Raw LLM baseline + hallucination scale
    reports/                  # Unified report gen + realism gate + evidence gate CLI

  models/                     # Trained models
    router_distilbert/        # DistilBERT classifier + checkpoints
    *.pkl                     # 5 CausalForest models

  tla_specs/                  # TLA+ formal verification (StateGraph, EscalationProtocol)
  .agent/skills/              # 12 agent skills (causal, query, guardian, etc.)
  scripts/                    # 13 scripts (training, generation, migration, seeding)
```

---

## Architecture Overview

```
User Query → Memory Augmentation → Router (+ memory hints) → RAG Context (3-layer) →
  [Domain Agent] → H-Neuron Gate → Guardian (YAML + CSL + OPA) →
    [APPROVED] → Governance (MAP-PRICE-RESOLVE) → END
    [REJECTED] → Reflector (heuristic + LLM repair, max 2 retries) → Router
    [ESCALATE] → HumanLayer (3-point context) → END

Domain Routing:
  Clear        → Deterministic Runner
  Complicated  → Causal Inference Engine (DoWhy/EconML) [+ ChimeraOracle fast-path]
  Complex      → Bayesian Active Inference (PyMC)
  Chaotic      → Circuit Breaker → Human Escalation
  Disorder     → Human Escalation

Phase 17 Cognitive Layers:
  Causal World Model  → SCMs, do-calculus, forward simulation, counterfactuals
  Neurosymbolic Engine → LLM fact extraction + forward-chaining + shortcut detection
  H-Neuron Sentinel    → Hallucination detection via weighted signal fusion

Persistence: Neo4j (causal graphs), Cloud SQL (history), Agent Memory (JSONL), Kafka (audit)
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

# Optional — LLM
OPENAI_API_KEY=sk-...          # OpenAI fallback
HUMANLAYER_API_KEY=hl_...      # Human-in-the-loop
LANGSMITH_API_KEY=ls-...       # Tracing

# Optional — Deployment
CARF_PROFILE=research          # research | staging | production
CARF_API_KEY=                  # API key for staging/production auth
CARF_CORS_ORIGINS=             # Comma-separated CORS origins
CARF_DATA_DIR=./var            # Dataset registry storage
CARF_MEMORY_DIR=data/memory    # Persistent agent memory storage
CARF_EMBEDDINGS_DIR=data/embeddings  # Embedding cache

# Optional — Infrastructure
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
KAFKA_ENABLED=false
OPA_ENABLED=false

# Phase 17 — Auth & Cloud
DATABASE_URL=postgresql://...  # Cloud SQL (omit for local SQLite)
GOOGLE_APPLICATION_CREDENTIALS=...  # Cloud Run ADC
H_NEURON_ENABLED=true          # Enable H-Neuron hallucination sentinel
VITE_FIREBASE_API_KEY=...      # Firebase auth (frontend)

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

The React Cockpit includes 58 components: four-view architecture (Analyst/Executive/Developer/Governance),
Cynefin domain visualizations (all 5 domains with Plotly.js charts), simulation arena with
benchmarking, data onboarding wizard, feedback collection, Firebase auth (AuthGuard + LoginPage),
and MCP server integration. 235+ frontend tests across 26 test files.

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
- [x] React Cockpit (58 components, four-view architecture)
- [x] Explainability drill-down modals for all analytical results
- [x] Confidence decomposition and zones
- [x] Data Onboarding Wizard with sample datasets
- [x] ChimeraOracle fast causal predictions
- [x] CSL-Core policy engine integration (35 rules, 5 categories)
- [x] MCP server (18 cognitive tools)
- [x] Cynefin domain visualizations (all 5 domains with Plotly.js)
- [x] Feedback API (closed-loop learning with domain overrides)
- [x] Benchmark suite (39 hypotheses, 10 categories, realism + evidence gates)
- [x] TLA+ formal verification specs

### Phase 12-16 - Governance, Benchmarks, UIX Rehaul (Complete)
- [x] MAP-PRICE-RESOLVE governance framework (18 endpoints)
- [x] Governance View (4-tab layout: Spec Map, Cost, Policy, Compliance)
- [x] Currency-aware financial enforcement in Guardian + CSL
- [x] Smart Reflector (hybrid heuristic + LLM repair)
- [x] Experience Buffer (sentence-transformer + TF-IDF semantic memory)
- [x] Router Retraining pipeline (feedback extraction + JSONL export)
- [x] 39 benchmark hypotheses (Grade A+: 39/39 passing)
- [x] Evidence gate CLI for CI/release quality checks
- [x] Comprehensive UIX rehaul (actionability, explainability, view differentiation)

### Phase 17 - Causal World Model, NeSy Engine, Auth & Cloud (Complete)
- [x] CausalWorldModel — SCMs with do-calculus, forward simulation, OLS learning
- [x] CounterfactualEngine — Pearl Level-3 reasoning, scenario comparison, attribution
- [x] NeurosymbolicEngine — LLM fact extraction + forward-chaining + shortcut detection
- [x] H-Neuron Sentinel — Hallucination detection via weighted signal fusion
- [x] 3-layer NeSy-augmented RAG (vector + graph + symbolic, RRF fusion)
- [x] Firebase Auth + Cloud SQL + per-user analysis history
- [x] 60+ new Phase 17 tests

## Phase 18 (SRR Hardening & Operational Intelligence)

> Derived from [`research.md`](research.md) + [`docs/CARF_RSI_ANALYSIS.md`](docs/CARF_RSI_ANALYSIS.md)

- [x] **P0**: ChimeraOracle StateGraph integration — `chimera_fast_path_node` with Guardian enforcement (AP-7, AP-10 closed)
- [x] **P1**: Drift detection — `DriftDetector` service, `/monitoring/drift` API, Developer View
- [x] **P1**: Plateau detection — `RouterRetrainingService.check_convergence()`, `/monitoring/convergence` API
- [x] **P2**: Bias auditing — `BiasAuditor` service, `/monitoring/bias-audit` API, Governance View
- [x] **Benchmarks H40-H43**: Drift sensitivity, bias accuracy, plateau detection, fast-path Guardian
- [x] **MonitoringPanel**: 3-tab React component in Developer + Governance views, 3 Executive KPI cards
- [ ] **P2**: Scalable inference modes (full/approximate/cached) — Phase 18E designed
- [ ] **P3**: Multi-agent collaborative causal discovery — Phase 18F designed
- [ ] GitHub Actions CI workflow

**Testing**: `pytest tests/unit/test_phase18_improvements.py tests/unit/test_monitoring_api.py -v`
**Benchmarks**: `python benchmarks/technical/monitoring/benchmark_drift_detection.py`
**Reference**: See `CURRENT_STATUS.md` for full details. See `docs/FUTURE_ROADMAP.md` for roadmap.

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

## Recent Changes (2026-03-16)

- **Phase 18 Implementation**: SRR Hardening — 4 RSI gaps closed (drift detection, bias auditing, plateau detection, ChimeraOracle integration)
- **New services**: `drift_detector.py`, `bias_auditor.py`, `chimera_fast_path_node` in graph.py, plateau detection in router_retraining_service.py
- **New API**: `/monitoring/*` (7 endpoints — drift, bias, convergence, unified status)
- **New frontend**: MonitoringPanel (3-tab), integrated into Developer + Governance views, 3 Executive KPI cards
- **New benchmarks**: H40-H43 with realistic enterprise datasets (drift, bias, plateau, Guardian enforcement)
- **New tests**: 50+ backend tests, 8+ frontend tests, zero regressions on 1,130+ existing tests
- **Documentation**: All central docs updated — AGENTS.md, CURRENT_STATUS.md, DEV_REFERENCE.md, INTELLECTUAL_PROPERTY.md, EVALUATION_FRAMEWORK.md, CARF_RSI_ANALYSIS.md, FUTURE_ROADMAP.md, SOLUTION_VISION.md, END_TO_END_CONTEXT_FLOW.md, SELF_HEALING_ARCHITECTURE.md, INTEGRATION_GUIDE.md, LLM_AGENTIC_STRATEGY.md

### Previous (2026-03-14)
- Phase 17 complete: Causal World Model, NeSy Engine, H-Neuron Sentinel, Firebase Auth, Cloud SQL
- 60+ new tests, doc reorganization, Dockerfile updated

### Previous (2026-02-22)
- Phase 16 complete: MAP-PRICE-RESOLVE governance, benchmark suite expansion to 39 hypotheses
- Evidence gate CLI, realism quality gate, currency-aware financial enforcement

---

## Contact/Resume Context

To resume this session:
1. Open this project in Claude Code
2. Reference this file: `DEV_REFERENCE.md`
3. Check `CURRENT_STATUS.md` for latest status
4. Run tests to verify: `.\.venv\Scripts\python.exe -m pytest tests/unit/ -v`
