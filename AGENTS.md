# AGENTS.md - AI Coding Context for CARF

> Purpose: Operational context for AI coding assistants to safely modify the CARF codebase.

---

## Project Overview

CARF (Complex-Adaptive Reasoning Fabric) is a neuro-symbolic-causal agentic system.

Core Architecture: 6-layer cognitive stack
1. Router (Layer 1): Cynefin classification → routes to appropriate solver
2. Cognitive Mesh (Layer 2): LangGraph agents (Deterministic, Causal, Bayesian, Circuit Breaker)
3. Causal World Model (Layer 3): SCMs, counterfactual engine, neurosymbolic reasoning, H-Neuron sentinel
4. Reasoning Services (Layer 4): Neo4j (causal graphs), Experience Buffer (semantic memory), Agent Memory (persistent), RAG (3-layer retrieval)
5. Guardian (Layer 5): Policy enforcement (YAML + CSL-Core + OPA), HumanLayer approval gates
6. Auth & Cloud (Layer 6): Firebase JWT, Cloud SQL, per-user history

---

## Critical Rules

### DO NOT TOUCH (Immutable Core)
- `src/core/state.py` - EpistemicState schema is the contract for all agents
- `config/policies.yaml` - Safety policies require human review
- Any file in `.github/workflows/` - CI/CD changes need human approval

### ALWAYS DO
- Update `CURRENT_STATUS.md` before starting any feature work
- Run `pytest tests/` before committing
- Include Pydantic schemas for all new tools
- Wrap external API calls in tenacity retry decorators
- Log all state transitions for audit trail

### EXPLAINABILITY REQUIREMENTS
- Every analytical result MUST link to its data source
- Confidence scores MUST be decomposable (show what contributes)
- All panels MUST answer: "Why this?" + "How confident?" + "Based on what?"
- Drill-down capability MUST be available for all insights

---

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run only unit tests
pytest tests/unit/ -v

# Type checking
mypy src/ --strict

# Linting
ruff check src/ tests/
ruff format src/ tests/
```

---

## Environment Variables

Required:
```
LLM_PROVIDER=deepseek           # or "openai"
DEEPSEEK_API_KEY=               # DeepSeek API key (or OPENAI_API_KEY)
```

Optional:
```
OPENAI_API_KEY=                 # OpenAI fallback
HUMANLAYER_API_KEY=             # Human-in-the-loop
LANGSMITH_API_KEY=              # Tracing
CARF_TEST_MODE=1                # Offline LLM stubs for tests
CARF_API_URL=http://localhost:8000  # React Cockpit -> API target
CARF_DATA_DIR=./var             # Dataset registry storage (optional)
CARF_PROFILE=research           # Deployment profile: research | staging | production
CARF_API_KEY=                   # API key for staging/production auth
CARF_CORS_ORIGINS=              # Comma-separated CORS origins (overrides profile default)
CARF_MEMORY_DIR=data/memory     # Persistent agent memory storage
CARF_EMBEDDINGS_DIR=data/embeddings  # Numpy embedding cache
```

Phase 3/4 (optional):
```
NEO4J_URI=                      # bolt://localhost:7687
NEO4J_USERNAME=
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j

KAFKA_ENABLED=false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=carf_decisions
KAFKA_CLIENT_ID=carf

OPA_ENABLED=false
OPA_URL=http://localhost:8181
OPA_POLICY_PATH=/v1/data/carf/guardian/allow
OPA_TIMEOUT_SECONDS=5
```

---

## Code Style Standards

### Pydantic Models
All data structures must use Pydantic `BaseModel`:
```python
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    """Input schema for my_tool."""
    query: str = Field(..., description="The search query")
    limit: int = Field(default=10, ge=1, le=100)
```

### Tenacity Retry Pattern
External calls must use retry decorators:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def call_external_api():
    ...
```

### LangGraph Nodes
All graph nodes must accept and return `EpistemicState`:
```python
def my_node(state: EpistemicState) -> EpistemicState:
    state.add_reasoning_step(
        node_name="my_node",
        action="Performed analysis",
        input_summary="...",
        output_summary="...",
    )
    return state
```

---

## Directory Structure (MECE)

```
projectcarf/
  carf-cockpit/           # React Platform Cockpit (Vite + TypeScript + Tailwind)
    src/
      components/carf/    # Core UI components (44 implemented)
        BayesianPanel.tsx, CausalAnalysisCard.tsx, CausalDAG.tsx,
        CynefinRouter.tsx, DashboardHeader.tsx, DashboardLayout.tsx,
        ExecutionTrace.tsx, GuardianPanel.tsx, QueryInput.tsx,
        ResponsePanel.tsx, SimulationArena.tsx, PolicyEditorModal.tsx,
        EscalationModal.tsx, FloatingChatTab.tsx, OnboardingOverlay.tsx,
        DataOnboardingWizard.tsx, ConversationalResponse.tsx,
        WalkthroughManager.tsx, MethodologyModal.tsx,
        ExecutiveSummaryPanel.tsx, AgentsInvolvedPanel.tsx,
        FeedbackPanel.tsx, DomainVisualization.tsx, ...
      __tests__/          # Frontend test suite (5 test files)
      services/           # API client layer
      hooks/              # Custom React hooks
      types/              # TypeScript type definitions
  src/
    core/               # Base classes, state schemas, deployment profiles (NO external deps)
      state.py              # EpistemicState (immutable contract) + CounterfactualEvidence + NeurosymbolicEvidence
      llm.py                # Multi-provider LLM abstraction (DeepSeek, OpenAI, Anthropic, Google GenAI)
      database.py           # SQLite/PostgreSQL connection factory (Cloud SQL support)
      deployment_profile.py # CARF_PROFILE env → ProfileConfig (research/staging/production)
      governance_models.py  # 15 Pydantic governance models
    services/           # 30+ services — analytical engines, memory, governance, policy
      causal_world_model.py    # SCMs with do-calculus, forward simulation, OLS learning (Phase 17)
      counterfactual_engine.py # Pearl Level-3 counterfactual reasoning (Phase 17)
      neurosymbolic_engine.py  # LLM fact extraction + forward-chaining + shortcut detection (Phase 17)
      h_neuron_interceptor.py  # Hallucination detection via weighted signal fusion (Phase 17)
      embedding_engine.py      # Shared singleton for dense embeddings (all-MiniLM-L6-v2) + TF-IDF fallback
      agent_memory.py          # Persistent vector memory (dense + TF-IDF, reflexion-weighted)
      rag_service.py           # 3-layer NeSy-augmented RAG (vector + graph + symbolic, RRF fusion)
      experience_buffer.py     # Semantic memory (delegates to embedding engine)
      smart_reflector.py       # Hybrid heuristic + LLM repair for Guardian rejections
      chimera_oracle.py        # CausalForestDML fast predictions (<100ms)
      governance_service.py    # MAP-PRICE-RESOLVE orchestrator
      # ... 20+ additional services
    workflows/          # LangGraph definitions (the wiring)
      graph.py              # StateGraph: router → rag_context → [domain] → guardian → governance
      router.py             # Cynefin router with memory hint soft signals + causal language boost
      guardian.py            # Multi-layer policy engine (YAML + CSL-Core + OPA)
    api/                # FastAPI routers + library.py (notebook API)
      auth.py               # Firebase JWT middleware (Phase 17)
      middleware.py          # Profile-aware security (auth, rate limiting, size limits)
      routers/              # 16 API router modules (80+ endpoints)
    mcp/tools/          # MCP tool modules (7 modules, 18 cognitive tools)
    utils/              # Telemetry, resiliency, caching, currency
  config/               # YAML config, OPA, CSL, federated policies, governance boards
  docs/                 # 40+ architecture docs, walkthroughs, research
  tests/
    unit/               # 55+ unit test files
    e2e/                # End-to-end gold standard tests
    integration/        # API flow integration tests
    deepeval/           # LLM output quality evaluation (8 test files)
    eval/               # LLM-as-a-judge scenarios
    mocks/              # Mock HumanLayer, Neo4j, etc.
  benchmarks/           # Technical & use-case benchmarks (H0-H39 + realism gate)
    technical/          # 30+ benchmark scripts across 9 categories
    baselines/          # Raw LLM baseline comparison
    reports/            # Unified report generation + evidence gate CLI
  tla_specs/            # TLA+ formal verification (StateGraph, EscalationProtocol)
  models/               # Trained models (DistilBERT router, 5 CausalForest models)
  demo/                 # 17 sample datasets and payloads
  .agent/skills/        # 12 agent skills (causal, query, guardian, etc.)
  scripts/              # 13 scripts (training, generation, migration, seeding)
  research.md           # Neurosymbolic scaling research (33 references)
  CURRENT_STATUS.md     # Living task/status doc
  AGENTS.md             # This file
  DEV_REFERENCE.md      # Developer quick-start reference
  HANDOFF.md            # Handoff documentation
  pyproject.toml        # Dependencies
```

---

## Cynefin Domain Routing Logic

| Domain | Confidence | Entropy | Route To |
|--------|------------|---------|----------|
| Clear | > 0.95 | < 0.2 | `deterministic_runner` |
| Complicated | > 0.85 | < 0.5 | `causal_analyst` |
| Complex | > 0.7 | 0.5-0.8 | `bayesian_explorer` |
| Chaotic | Any | > 0.9 | `circuit_breaker` |
| Disorder | < 0.85 | Any | `human_escalation` |

---

## LLM Usage Guidelines

- Router: LLM or distilled model for Cynefin classification; entropy gate; low confidence → Disorder/Human.
- Context assembly & planning: LLM for query rewriting, context synthesis, solver selection; keep prompts structured; respect budgets.
- Domain agents: Causal/Bayesian/deterministic cores remain non-LLM; LLM only for hypotheses/narration; Guardian decisions stay symbolic/OPA.
- Guardian: LLM may explain decisions; policy verdicts are deterministic.
- Reflector: LLM may assist self-correction with bounded retries; escalate after limit.
- HumanLayer: LLM can craft 3-point context (what/why/risk); no auto-approval.
- Model selection: choose cheap vs. strong per cost/latency/risk; prefer local/distilled for privacy/offline; log model choice.
- Safety: enforce Pydantic schemas; retries with backoff; redact PII; deterministic guardrails for execution.

---

## HumanLayer Integration Pattern

When the system needs human approval:
```python
from humanlayer import HumanLayer

hl = HumanLayer()

@hl.require_approval()
async def high_risk_action(params: dict) -> dict:
    """This action requires human approval via Slack/Email."""
    return result
```

The "3-Point Context" for notifications:
1. What: One-sentence summary of proposed action
2. Why: Causal justification with confidence
3. Risk: Why it was flagged (policy violation, high uncertainty)

---

## Supervised Recursive Refinement (SRR) Model

CARF implements **Supervised Recursive Refinement** — a safety-first approach to system self-improvement where improvement loops exist but are bounded by formal invariants, policy enforcement, and human oversight at every layer.

**Key SRR Properties:**
- Self-correction bounded by `max_reflections` (default: 2) and Guardian enforcement
- Meta-learning through memory systems with deliberately small influence (0.03 weight)
- Self-modification requires human triggering and produces non-destructive suggestions
- Multi-agent improvement flows through structured critic-worker architecture
- Safety containment uses independent, deterministic, formally verified mechanisms (TLA+)
- System CANNOT modify its own architecture, policies, or core logic autonomously

**Reference:** See [`docs/CARF_RSI_ANALYSIS.md`](docs/CARF_RSI_ANALYSIS.md) for the complete RSI alignment assessment.

---

## Current Phase: Phase 18A-D Implemented — SRR Hardening & Operational Intelligence

### Data Flow (Phase D):
```
Entry → Memory Augmentation → Router (+ memory hints) → RAG Context →
[Domain Agent] → Guardian → [Governance (+ RAG triple feed)] → END
```

### Implemented (Phase 18A-D):
- **ChimeraOracle LangGraph Integration** ✅ — `chimera_fast_path_node` in StateGraph with Guardian enforcement (AP-7/AP-10 closed)
- **Drift Detection Service** ✅ — KL-divergence monitoring, `/monitoring/drift` API, Developer View integration
- **Plateau Detection** ✅ — Convergence monitoring with regression alerts, `/monitoring/convergence` API
- **Bias Auditing** ✅ — Chi-squared fairness tests, `/monitoring/bias-audit` API, Governance View integration
- **Monitoring Panel** ✅ — 3-tab React component in Developer + Governance views, 3 Executive KPI cards
- **Benchmarks H40-H43** ✅ — Drift sensitivity, bias accuracy, plateau detection, Guardian enforcement

### Remaining Work (Phase 18E-F):
- **Scalable Inference** (P2) — Configurable inference modes (full MCMC / approximate / cached)
- **Multi-Agent Discovery** (P3) — Collaborative causal discovery for high-dimensional variables
- **CI/CD** — GitHub Actions workflow for automated testing

### CSL-Core Policy Engine
- **Role:** Primary policy enforcement layer for all CARF agent actions
- **Engine:** Built-in Python evaluator (CSL-Core Z3 optional)
- **Integration:** CSLToolGuard wraps workflow nodes (causal_analyst, bayesian_explorer) with policy checks
- **Modes:** `enforce` (block on violation) | `log-only` (audit trail only)
- **Audit:** Bounded deque (maxlen=1000) per AP-4, Kafka audit integration for CSL fields
- **API:** Full CRUD via `/csl/*` endpoints, natural language rule creation supported

### Benchmark Suite
- **Technical benchmarks**: Core + governance + causal deep validation + competitive + security + compliance + sustainability + UX + industry + performance/resilience
- **Use case benchmarks**: End-to-end scenarios across 6 industries (supply chain, financial risk, sustainability, critical infra, healthcare, energy)
- **39 falsifiable hypotheses** (H0-H39): CARF vs raw LLM + governance + robustness comparisons
- **Realism validation gate**: realism, reliability, feasibility, provenance, production-proxy ratios, and absolute readiness index
- **Evidence gate CLI**: `python benchmarks/reports/check_result_evidence.py` for CI/release result-artifact quality checks
- **Reports**: Unified comparison report generation
- **Location**: `benchmarks/` directory with `benchmarks/README.md` for full instructions

### Completed (Phases 1-17):
- Full Cynefin router and cognitive mesh (DistilBERT + Shannon entropy + causal language boost)
- Neo4j persistence + query utilities
- DoWhy/EconML and PyMC optional inference paths
- React Cockpit (58 components, four-view architecture, 26 test files, 235 tests)
- Explainability drill-downs for all analytical results
- Data Onboarding Wizard with 10 demo scenarios across all 5 Cynefin domains
- ChimeraOracle fast causal predictions (standalone API — **Phase 18 integrates into StateGraph**)
- CSL-Core policy engine (35 rules across 5 policy categories)
- MCP server (18 cognitive tools for agentic AI integration)
- Cynefin domain visualizations (Plotly.js: waterfall, radar, sankey, gauge)
- Feedback API (closed-loop learning with domain overrides)
- Benchmark suite (39 hypotheses across 10 categories + realism quality gate + evidence gate CLI)
- Governance semantic graph endpoint + cockpit semantic graph tab
- Currency-aware financial enforcement in Guardian + CSL
- TLA+ formal verification specs (StateGraph, EscalationProtocol)
- Kafka audit trail (optional) + OPA Guardian (optional)
- Docker Compose demo stack + seed scripts
- Smart Reflector (hybrid heuristic + LLM repair for policy violations)
- Experience Buffer (sentence-transformer + TF-IDF semantic memory)
- Library API (notebook-friendly wrappers for all CARF services)
- Router Retraining pipeline (feedback extraction + JSONL export)
- Actionable Insights with persona-specific action items and roadmaps
- MAP-PRICE-RESOLVE governance framework (18 endpoints, 4-tab Governance View)
- Phase 17: Causal World Model (SCMs, do-calculus, forward simulation, OLS learning)
- Phase 17: Counterfactual Engine (Pearl Level-3, scenario comparison, but-for attribution)
- Phase 17: Neurosymbolic Engine (LLM fact extraction + forward-chaining + shortcut detection)
- Phase 17: H-Neuron Sentinel (hallucination detection via weighted signal fusion)
- Phase 17: 3-layer NeSy-augmented RAG (vector + graph + symbolic, RRF fusion)
- Phase 17: Firebase Auth + Cloud SQL + per-user analysis history
- Data Layer Coherence: Shared Embedding Engine, Deployment Profiles, Memory→Router pipeline, RAG→Pipeline, Governance-RAG coherence, Security middleware

### Out of Scope:
- Production autoscaling and Kubernetes
- Enterprise-grade observability beyond demo

---

## Antipatterns — Mandatory Avoidance List

These antipatterns have caused real bugs and regressions in this project. Every AI coding agent and human contributor MUST check against this list before submitting code.

### AP-1: No Hardcoded Analytical Values

**Problem**: Hardcoded numbers in analytical engines undermine the platform's core value proposition (epistemic rigor).

```python
# BAD — previously caused the 0.7/0.3 epistemic/aleatoric split bug
epistemic_uncertainty = uncertainty * 0.7
aleatoric_uncertainty = uncertainty * 0.3
confidence_interval = (posterior - 0.15, posterior + 0.15)

# GOOD — derive from actual statistical computation
epistemic_uncertainty = float(np.std(posterior_samples))
aleatoric_uncertainty = float(np.mean(sample_variances))
ci_width = 0.05 + 0.30 * shannon_entropy  # entropy-adaptive
confidence_interval = (posterior - ci_width, posterior + ci_width)
```

**Rule**: If a number appears in an analytical formula, it MUST either be:
1. A configurable parameter (Pydantic model field with default)
2. Derived from data (computed from samples, posteriors, etc.)
3. A well-known mathematical constant (pi, e, etc.)

### AP-2: No Mock Data in Production Paths

**Problem**: `console.log` as a placeholder for API calls, hardcoded fallback arrays displayed as "real" results.

```typescript
// BAD — feedback goes nowhere, user thinks it was submitted
console.log('[CYNEPIC Feedback]', feedbackData);
alert('Thank you!');

// GOOD — call real API, handle failure gracefully
submitFeedback(feedbackData)
    .then(() => alert('Feedback recorded.'))
    .catch(() => alert('Feedback saved locally. Backend unavailable.'));
```

**Rule**: Every user-facing interaction MUST connect to a real backend endpoint. If the endpoint doesn't exist yet, create it. If data is simulated, label it explicitly as "Simulated Data" in the UI.

### AP-3: No Blocking I/O in Async Functions

**Problem**: Synchronous I/O inside `async def` blocks the event loop, causing request timeouts.

```python
# BAD — blocks the entire event loop
async def check_policy(state):
    response = urllib.request.urlopen(opa_url)  # SYNC!
    producer.flush()  # SYNC!

# GOOD — offload to thread or use async library
async def check_policy(state):
    response = await asyncio.to_thread(urllib.request.urlopen, opa_url)
    await asyncio.to_thread(producer.flush, 5)
    # OR: use httpx/aiohttp for native async
```

**Rule**: All I/O inside `async def` MUST be non-blocking. Use `asyncio.to_thread()` as minimum mitigation, prefer native async libraries (httpx, aiokafka).

### AP-4: No Unbounded Collections

**Problem**: Appending to `list` without bounds causes memory exhaustion in long-running processes.

```python
# BAD — grows without limit
self._logs: list[LogEntry] = []
self._logs.append(entry)  # OOM after hours of operation

# GOOD — bounded deque auto-evicts oldest
from collections import deque
self._logs: deque[LogEntry] = deque(maxlen=500)
self._logs.append(entry)  # safe forever
```

**Rule**: Every in-memory collection that grows over time MUST use `deque(maxlen=N)` or implement periodic flush/rotation.

### AP-5: No Currency-Blind Financial Comparisons

**Problem**: Comparing monetary values without currency context leads to incorrect policy decisions.

```python
# BAD — $50,000 USD and ¥50,000 JPY treated identically
if amount > threshold:
    return "VIOLATION"

# GOOD — currency-aware comparison
if normalize_to_base_currency(amount, currency) > threshold_in_base:
    return "VIOLATION"
```

**Rule**: All financial comparisons MUST include currency context. Guardian policies with monetary thresholds MUST specify currency.

### AP-6: No Silent Null Returns in UI Components

**Problem**: React components returning `null` for valid domain states cause invisible blank panels.

```tsx
// BAD — user sees nothing, thinks UI is broken
case 'complicated':
case 'complex':
    return null;

// GOOD — every valid state has a dedicated view
case 'complicated':
    return <ComplicatedDomainView causalResult={causalResult} />;
case 'complex':
    return <ComplexDomainView bayesianResult={bayesianResult} />;
```

**Rule**: Every valid Cynefin domain MUST have a dedicated view component. `null` is only acceptable for truly invalid states (null domain, processing state).

### AP-7: No Isolated Services in the Cognitive Mesh

**Problem**: Analytical services accessible only via standalone REST endpoints bypass the LangGraph workflow, losing traceability and Guardian enforcement.

```python
# BAD — ChimeraOracle only reachable via /oracle/predict, not in workflow
@router.post("/oracle/predict")
async def predict(request): ...

# GOOD — integrate into StateGraph as optional fast-path node
graph.add_node("chimera_fast_path", chimera_oracle_node)
graph.add_conditional_edges("router", route_with_oracle_option)
```

**Rule**: Every analytical capability MUST be accessible through the LangGraph workflow graph, even if also exposed via direct API. This ensures Guardian enforcement, audit trail, and evaluation at every step.

### AP-8: No Test Mode Leaking into Production Responses

**Problem**: `CARF_TEST_MODE=1` stubs can leak into production if environment isn't properly managed.

**Rule**: Test mode stubs MUST be:
1. Clearly labeled in response metadata: `"mode": "test_stub"`
2. Never cached alongside real responses
3. Logged with warning level: `logger.warning("Using test stub for ...")`

### AP-9: No Unmonitored Feedback Loops

**Problem**: Self-improvement feedback loops (memory → router hints, feedback → retraining) without monitoring can cause silent drift, bias amplification, or plateau-induced overfitting.

**Rule**: Every feedback loop in the system MUST have:
1. A **drift metric** tracking distributional change over time (e.g., routing domain distribution)
2. A **bound** limiting maximum influence (e.g., memory hint weight ≤ 0.03)
3. A **convergence check** detecting diminishing returns in retraining cycles
4. An **audit trail** logging all feedback-driven changes for human review

**Context**: The RSI analysis identified 3 unmonitored feedback loops: memory→router, feedback→retraining, and evaluation→memory quality scores. Small influence weights (0.03) mitigate but do not eliminate drift risk.

### AP-10: No Analytical Service Without Guardian Enforcement

**Problem**: Analytical services accessible only via standalone REST endpoints bypass the LangGraph workflow, losing traceability, Guardian enforcement, and evaluation scoring. This is a generalization of AP-7.

**Rule**: Every service that produces analytical conclusions (causal effects, Bayesian posteriors, counterfactuals, predictions) MUST:
1. Be reachable through the LangGraph StateGraph (even if also exposed via direct API)
2. Have its output evaluated by the EvaluationService (hallucination, relevancy, UIX)
3. Pass through Guardian policy enforcement before delivery to the user
4. Log a complete audit trail including data provenance and model version

**Reference**: research.md §2.3 (System Integration Heterogeneity), RSI Analysis §5 (Tool Use)

---

## Commit Protocol

1. Atomic commits: One feature per commit
2. Always include updates to `AGENTS.md` if agent logic changes
3. Format: `type(scope): description`
   - `feat(router)`: Add entropy-based classification
   - `fix(guardian)`: Handle edge case in policy check
   - `docs(agents)`: Update testing commands
