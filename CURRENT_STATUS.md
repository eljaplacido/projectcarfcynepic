# CARF Project Status

## Current Phase: Phase 4 - Research Demo UIX Alignment

## Active Task: Colab router training notebook + initial model training

### Status: COMPLETE - Colab notebook added; training run pending

---

## Recent Decisions
- 2026-01-13: Colab notebook added for router training run
- 2026-01-13: Start Colab notebook for router training run
- 2026-01-13: Added guided walkthrough UX and interpretability expanders in dashboard
- 2026-01-13: Added router training scripts, optional deps, and distilbert mode toggle
- 2026-01-13: Started router training guide for DistilBERT + domain adaptation
- 2026-01-12: Suggested query buttons now populate the Analyze input in Streamlit cockpit
- 2026-01-12: Added security and end-user testing guidance docs for release readiness
- 2026-01-12: Rebuilt Bayesian Belief State panel with Streamlit-native components
- 2026-01-12: Started codebase-wide review for security/maturity ahead of GitHub release
- 2026-01-12: Rebuilt dashboard cards (Causal Analysis, Guardian Policy, Execution Trace) with Streamlit-native layout
- 2026-01-12: Started UIX debug pass to replace HTML blocks with Streamlit-native components for dashboard cards
- 2026-01-11: UIX Phase 4 polish complete - response badges, color-coded confidence, improved reasoning chain
- 2026-01-11: Documentation aligned across UI_UIX.md, CURRENT_STATUS.md, DEV_REFERENCE.md
- 2026-01-09: Initialized Phase 1 MVP setup
- 2026-01-09: Completed Phase 1 scaffolding
- 2026-01-09: Switched to DeepSeek LLM for cost efficiency
- 2026-01-09: Implemented Causal Inference Engine
- 2026-01-09: Implemented Bayesian Active Inference Engine
- Architecture: 4-layer cognitive stack fully operational
- LLM Provider: DeepSeek (deepseek-chat) via OpenAI-compatible API
- 2026-01-10: Fixed CausalVariable role validation (added mediator/collider)
- 2026-01-10: Fixed Windows console Unicode encoding issues
- 2026-01-10: Created DEV_REFERENCE.md (development guide)
- 2026-01-10: Completed documentation cleanup (formatting and encoding)
- 2026-01-10: Tests failing without DEEPSEEK_API_KEY; adding offline test stubs
- 2026-01-10: Offline LLM stubs added; test suite passes without API keys
- 2026-01-10: Added DoWhy/EconML and PyMC integration paths (optional)
- 2026-01-10: Added Streamlit cockpit skeleton
- 2026-01-10: Added Kafka audit trail scaffolding and pipeline hook
- 2026-01-10: Added DoWhy/EconML and PyMC optional inference configs and fallbacks
- 2026-01-10: Added test-mode LLM stubs and updated tests to pass offline
- 2026-01-10: Added API payload support for statistical configs with size guardrails
- 2026-01-10: Added optional OPA Guardian integration path
- 2026-01-10: Wired Streamlit cockpit to Neo4j health/lookup placeholders
- 2026-01-10: Added Kafka audit schema versioning and unit tests
- 2026-01-10: Added API payload examples and size limits documentation
- 2026-01-10: Added OPA policy sample and config docs
- 2026-01-10: Wired Streamlit cockpit to Neo4j graph/path lookups and Kafka event fetch
- 2026-01-10: Added Docker Compose stack and app Dockerfile for demo deployment
- 2026-01-10: Streamlit cockpit now calls `/query` and displays reasoning chain
- 2026-01-10: Added demo datasets and seed scripts for Neo4j/Kafka
- 2026-01-10: Added Streamlit service + demo seed profile to docker-compose
- 2026-01-10: Added demo walkthrough documentation
- 2026-01-10: Fixed Kafka audit JSON serialization (datetime) and Compose warning cleanup
- 2026-01-10: Fixed OPA policy allow rule to avoid unsafe var errors at startup
- 2026-01-10: Updated UI_UIX plan to align with Streamlit cockpit and bring-your-data flow
- 2026-01-10: Added scenario registry + API endpoints for demo payloads
- 2026-01-10: Added dataset registry (SQLite + JSON) and dataset selection API
- 2026-01-10: Streamlit cockpit wired for scenarios and data onboarding
- 2026-01-10: Docker Compose now mounts dataset registry storage (`var/`)

---

## Completed Steps

### Phase 1 - Foundation
- [x] Project scaffolding (MECE structure)
- [x] Core state schemas (EpistemicState)
- [x] Config YAML templates
- [x] Resiliency utilities
- [x] Cynefin Router (LLM classification)
- [x] HumanLayer Service
- [x] Guardian Layer (policy enforcement)
- [x] LangGraph Workflow

### Phase 2 - Cognitive Engines
- [x] DeepSeek LLM integration (`src/core/llm.py`)
- [x] Causal Inference Engine (`src/services/causal.py`)
  - Causal structure discovery (DAG)
  - Effect estimation with confidence intervals
  - Refutation test framework
- [x] Bayesian Active Inference (`src/services/bayesian.py`)
  - Prior belief establishment
  - Probe design for uncertainty reduction
  - Belief updating
- [x] Test notebook (`modeltraining/test.ipynb`)

### Phase 3 - Persistence & Infrastructure (In Progress)
- [x] Neo4j Integration (`src/services/neo4j_service.py`)
  - Async Neo4j driver with connection pooling
  - CausalGraph persistence (nodes + edges)
  - CausalAnalysisResult persistence with session tracking
  - Historical analysis queries
  - Causal path finding between variables
  - Variable neighbor discovery (Markov blanket)
  - Health check endpoint
- [x] Integration with CausalInferenceEngine
  - Optional Neo4j persistence on analysis
  - Historical analysis lookup
- [x] Unit tests for Neo4j service
- [x] DoWhy/EconML integration (optional path + fallback)
- [x] PyMC integration (optional path + fallback)
- [x] Streamlit Dashboard (Epistemic cockpit)
- [x] Kafka Audit Trail (schema versioning + workflow hook)
- [x] OPA policy sample + optional integration

### Phase 4 - Research Demo UIX (Complete)
- [x] Scenario registry + API endpoints
- [x] Dataset registry + dataset selection API
- [x] Streamlit cockpit onboarding (scenarios + CSV upload)
- [x] UI polish: response badges (domain, verdict, confidence)
- [x] UI polish: color-coded confidence indicators (green/yellow/red)
- [x] UI polish: improved reasoning chain display with expandable steps
- [x] UI polish: styled response panel with visual hierarchy

---

## LLM Agentic Vision
- Current: Router uses DeepSeek LLM (prompt-based) with entropy/confidence gate.
- Planned: DistilBERT router option for cost/privacy; policy-based model tiering (cheap vs. strong).
- LLM assist only where safe: context assembly, planning, narration, reflection guidance, HumanLayer messaging.
- Deterministic cores stay non-LLM: Guardian, causal/Bayesian engines, circuit-breaker actions.
- Self-healing: reflector loop with bounded retries; escalate to HumanLayer on repeated failures or low confidence.

---

## Next Steps (Phase 5 - Platform UIX)
1. Dataset registry enhancements (tags, search, richer previews)
2. Org-level workspace model for multi-tenant support
3. Use-case templates per business unit
4. React cockpit for high-fidelity visualization
5. HumanLayer approval UI integration

## Phase 4 Release Readiness
- [x] UIX polish complete
- [ ] Docker-based smoke tests for demo stack
- [ ] Expand sample datasets and playbook use cases
- [ ] Document extension points for new tools/solvers
- [ ] Prepare release checklist (license, badges, screenshots)

---

## Session Save Point (2026-01-11 - Evening Session)

### Latest Session Summary (2026-01-11 ~18:30)

**Major UIX Overhaul Completed:**

1. **Light Theme Implementation**
   - Switched from dark to light theme matching flow-visualizer reference
   - White cards (#FFFFFF) on light background (#F8FAFC)
   - Updated all color tokens and CSS styles

2. **Three View Modes Fully Implemented**
   - **End-User View**: 3-6-3 column layout (Query/Controls | DAG/Analysis/Guardian | Execution Trace)
   - **Developer View**: Query sidebar + Performance stats + 4 debug tabs
   - **Executive View**: Query sidebar + Hero card + KPI cards + Action buttons

3. **Fixed Streamlit Duplicate Key Errors**
   - Added `key_prefix` parameter to `render_query_input()` and `render_simulation_controls()`
   - All widgets now have unique keys per tab (enduser_, developer_, executive_)

4. **Scenario Selector Added**
   - Dropdown in header fetches scenarios from `/scenarios` API
   - Loads scenario payloads for causal/bayesian configs
   - Three demo scenarios ready:
     - `scope3_attribution` - Supplier emissions analysis
     - `causal_discount_churn` - Causal estimation
     - `bayesian_conversion_rate` - Bayesian inference

5. **Backend Integration**
   - Dashboard calls `/scenarios` and `/query` APIs
   - Results stored in `st.session_state["analysis_result"]`
   - Domain/confidence updates displayed in UI

**Files Modified:**
- `src/dashboard/app.py` - Complete refactor (~1500 lines)
- `demo/scenarios.json` - Added Scope 3 scenario
- `demo/payloads/scope3_attribution.json` - New scenario payload

**How to Resume:**
```bash
cd C:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
.venv\Scripts\python -m streamlit run src/dashboard/app.py --server.port 8501
```

**Reference Screenshots:** `debugging_screenshots/`
- `end-user-view.png`
- `developerview.png`
- `executiveview.png`

**Next Steps:**
- Test full analysis pipeline with all scenarios
- Fine-tune UI components to match screenshots exactly
- Add real-time result display from API responses
- Expand demo scenarios and sample data

---

### Previous Session Summary (2026-01-11 - Morning)
- Added response badges to Streamlit cockpit (domain, verdict, confidence)
- Added color-coded confidence indicators (green/yellow/red per UIX guidelines)
- Added improved reasoning chain display with expandable steps
- Added styled response panel with visual hierarchy
- Updated UI_UIX.md with implementation status checkboxes
- Updated CURRENT_STATUS.md to mark Phase 4 UIX complete
- Documentation aligned across all docs files

### Summary of Changes (2026-01-10)
- Added DoWhy/EconML optional path in `src/services/causal.py` using context keys `causal_estimation`/`causal_data`.
- Added PyMC optional path in `src/services/bayesian.py` using context keys `bayesian_inference`/`bayesian_data`.
- Added Streamlit cockpit skeleton in `src/dashboard/app.py`.
- Added Kafka audit trail service in `src/services/kafka_audit.py` and optional logging hook in `src/workflows/graph.py`.
- Added optional deps/env vars for dashboard/Kafka and updated docs.
- Added offline LLM test stubs and test fixture; tests now run without API keys.
- Fixed OPA policy allow rule to avoid unsafe var errors at startup.
- Refreshed UI_UIX plan to align with Streamlit cockpit and demo/user data flows.
- Added dataset registry (SQLite + JSON) with API endpoints.
- Added scenario registry endpoints backed by `demo/scenarios.json`.
- Updated Streamlit cockpit for scenarios and CSV onboarding.
- Added RFCs for UIX chunk delivery (scenario registry + data onboarding).
- Persisted dataset registry storage via docker-compose volume.

### Environment/Config Notes
- Optional env vars: `KAFKA_ENABLED`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`, `KAFKA_CLIENT_ID`.
- Optional test flag: `CARF_TEST_MODE=1` (enabled in `tests/conftest.py`).
- Streamlit optional dependency: `carf[dashboard]`.
- Kafka optional dependency: `carf[kafka]`.

### Tests
- `.\.venv\Scripts\python.exe -m pytest tests/ -v` (73 passed).

---

## LLM Configuration

```
Provider: DeepSeek
Model: deepseek-chat (DeepSeek-V3)
Base URL: https://api.deepseek.com
Cost: ~$0.14/1M input tokens, ~$0.28/1M output tokens
```

To switch providers, edit `.env`:
```bash
LLM_PROVIDER=deepseek  # or "openai"
DEEPSEEK_API_KEY=sk-...
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/query` | POST | Process query through CARF pipeline |
| `/domains` | GET | List Cynefin domains |

---

## Architecture (Phase 2)

```
User Query -> Router -> Domain -> Solver -> Guardian -> [Approved | Rejected | Escalate to HumanLayer]

Clear        -> Deterministic Runner
Complicated -> Causal Inference Engine
Complex     -> Bayesian Active Inference
Chaotic     -> Circuit Breaker
Disorder    -> HumanLayer Escalation
```

---

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Environment is already configured (.env file)

# Run the test notebook
cd modeltraining
jupyter notebook test.ipynb

# Or run the API server
python -m src.main

# Test with curl
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did our costs increase by 15%?"}'
```

---

## Session Log
| Timestamp | Action | Agent/Human |
|-----------|--------|-------------|
| 2026-01-11 | Phase 4 UIX polish complete (badges, confidence, reasoning chain) | AI Architect |
| 2026-01-11 | Documentation alignment across docs files | AI Architect |
| 2026-01-09 | Phase 1 initialization started | AI Architect |
| 2026-01-09 | Project scaffolding completed | AI Architect |
| 2026-01-09 | Phase 1 MVP complete | AI Architect |
| 2026-01-09 | DeepSeek LLM configured | AI Architect |
| 2026-01-09 | Causal Inference Engine implemented | AI Architect |
| 2026-01-09 | Bayesian Active Inference implemented | AI Architect |
| 2026-01-09 | Test notebook created | AI Architect |
| 2026-01-09 | Phase 2 Complete | AI Architect |
| 2026-01-10 | Fixed CausalVariable role validation | AI Architect |
| 2026-01-10 | Fixed Windows console Unicode encoding issues | AI Architect |
| 2026-01-10 | All 5 test suites passing | AI Architect |
| 2026-01-10 | Phase 3 started: Neo4j integration | AI Architect |
| 2026-01-10 | Neo4j service implemented with async driver | AI Architect |
| 2026-01-10 | CausalGraph persistence (nodes, edges, analyses) | AI Architect |
| 2026-01-10 | Integrated Neo4j with CausalInferenceEngine | AI Architect |
| 2026-01-10 | Added unit tests for Neo4j service | AI Architect |
| 2026-01-10 | Created Python virtual environment (.venv) | AI Architect |
| 2026-01-10 | Added .gitignore | AI Architect |
| 2026-01-10 | Created DEV_REFERENCE.md (development guide) | AI Architect |
| 2026-01-10 | Documentation review and cleanup started | AI Architect |
| 2026-01-10 | Added scenario registry + dataset registry | AI Architect |
| 2026-01-10 | Streamlit cockpit updated for scenarios and CSV onboarding | AI Architect |
