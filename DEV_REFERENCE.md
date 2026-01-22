# CARF Development Reference

> Last Updated: 2026-01-16
> Current Phase: Phase 5 Complete - Phase 6 (Enhanced UIX & Explainability) Starting

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
.\.venv\Scripts\python.exe test_carf.py
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
  test_carf.py                # Integration test script
  CURRENT_STATUS.md           # Project status tracker
  DEV_REFERENCE.md            # This file
  AGENTS.md                   # Agent architecture docs

  demo/
    data/                     # Sample datasets
    payloads/                 # Demo request payloads
    scenarios.json            # Scenario registry for UI

  config/
    agents.yaml               # Agent configurations
    policies.yaml             # Guardian policies
    prompts.yaml              # LLM prompts

  docs/
    PRD.md                    # Product requirements
    DATA_LAYER.md             # Data architecture
    UI_UIX_CURRENT_STREAMLIT.md  # Current Streamlit implementation
    UI_UIX_VISION_REACT.md       # Future React architecture vision
    DEV_PRACTICES_AND_LIVING_DOCS.md
    CARF_UIX_INTERACTION_GUIDELINES.md

  src/
    core/
      state.py                # EpistemicState, CynefinDomain, etc.
      llm.py                  # LLM configuration (DeepSeek/OpenAI)
    dashboard/
      app.py                  # Streamlit Epistemic Cockpit
    services/
      causal.py               # Causal Inference Engine
      bayesian.py             # Bayesian Active Inference
      human_layer.py          # Human-in-the-loop service
      dataset_store.py        # Local dataset registry (SQLite + JSON)
      neo4j_service.py        # Neo4j graph persistence
      kafka_audit.py          # Kafka audit trail
    workflows/
      router.py               # Cynefin domain classifier
      guardian.py             # Policy enforcement layer
      graph.py                # LangGraph workflow
    utils/
      resiliency.py           # Retry, circuit breaker utils
    main.py                   # FastAPI application

  tests/
    unit/
      test_state.py
      test_router.py
      test_guardian.py
      test_dataset_store.py   # Dataset registry tests
      test_neo4j_service.py   # Neo4j tests
    eval/
      test_workflow_integration.py
    mocks/
      mock_human_layer.py
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

## Streamlit Cockpit

```bash
pip install -e ".[dashboard]"
streamlit run src/dashboard/app.py
```

Cockpit features include demo scenarios, dataset upload/selection, causal graph lookup,
reasoning chain inspection, and Kafka audit previews.

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

| ID | Name | Description |
|---|---|---|
| `scope3_attribution` | Scope 3 Attribution | Causal analysis of supplier sustainability programs |
| `causal_discount_churn` | Discount vs Churn | Causal effect of discount offers on customer churn |
| `bayesian_conversion_rate` | Conversion Belief Update | Bayesian inference on website conversion rates |

### How to Use Scenarios

**Via Dashboard (UI):**
1. Launch dashboard: `streamlit run src/dashboard/app.py`
2. Select a scenario from the dropdown in the header
3. Enter a query (or use suggested query)
4. Click "Analyze" to run the full analysis pipeline
5. View real results in Cynefin, Causal, Bayesian, and Guardian panels

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

Streamlit runs on `http://localhost:8501`.
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
python test_carf.py
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
- [x] Streamlit Dashboard (Epistemic Cockpit)
- [x] Kafka Audit Trail

### Phase 4 - Research Demo UIX (Complete)
- [x] Scenario registry + UI selector
- [x] Dataset registry + CSV onboarding
- [x] Response badges (domain, verdict, confidence)
- [x] Color-coded confidence indicators (green/yellow/red)
- [x] Improved reasoning chain display with expandable steps

---

## Next Development Steps (Phase 6 - Enhanced UIX & Explainability)

**Explainability & Transparency:**
- Drill-down modals for all analytical results
- Confidence decomposition (data/model/validation sources)
- Data provenance links from results to source data
- "Why not?" alternative Cynefin paths

**Enhanced React Components:**
- `OnboardingOverlay.tsx` - First-run scenario discovery
- `DataOnboardingWizard.tsx` - 5-step data upload flow
- `ConversationalResponse.tsx` - Dialog with confidence zones
- `FloatingChatTab.tsx` - Persistent bottom-right chat
- `WalkthroughManager.tsx` - Multi-track guided tours

**Release Readiness:**
- LICENSE, SECURITY.md, CONTRIBUTING.md
- GitHub Actions CI workflow
- Demo GIF and live deployment

**Reference**: See `docs/CARF UI Development.md` and `docs/UI_UIX_VISION_REACT.md` for detailed specifications.

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

## Files Changed This Session (2026-01-11)

### Modified Files
- `src/dashboard/app.py` - Response badges, color-coded confidence, improved reasoning chain
- `docs/UI_UIX_VISION_REACT.md` - Added implementation status checkboxes, marked Phase 4 complete
- `CURRENT_STATUS.md` - Updated Phase 4 to complete, added 2026-01-11 session log
- `DEV_REFERENCE.md` - Updated Phase 4 status, next steps for Phase 5

## Files Changed Previous Session (2026-01-10)

### New Files
- `src/services/dataset_store.py` - Local dataset registry (SQLite + JSON)
- `tests/unit/test_dataset_store.py` - Dataset registry tests
- `demo/scenarios.json` - Scenario registry
- `docs/RFC_UIX_001_SCENARIO_REGISTRY.md` - UIX chunk RFC
- `docs/RFC_UIX_002_DATA_ONBOARDING.md` - UIX chunk RFC

### Modified Files
- `src/main.py` - Dataset/scenario endpoints, dataset selection handling
- `src/services/causal.py` - Dataset ID support for causal estimation
- `src/dashboard/app.py` - Scenario selector + data onboarding UI
- `docs/UI_UIX_VISION_REACT.md` - UIX plan aligned with implemented features
- `README.md` - Updated endpoints and data onboarding notes
- `CURRENT_STATUS.md` - Updated Phase 4 UIX progress

---

## Contact/Resume Context

To resume this session:
1. Open this project in Claude Code
2. Reference this file: `DEV_REFERENCE.md`
3. Check `CURRENT_STATUS.md` for latest status
4. Run tests to verify: `.\.venv\Scripts\python.exe -m pytest tests/unit/ -v`
