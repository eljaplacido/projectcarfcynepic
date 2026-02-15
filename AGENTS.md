# AGENTS.md - AI Coding Context for CARF

> Purpose: Operational context for AI coding assistants to safely modify the CARF codebase.

---

## Project Overview

CARF (Complex-Adaptive Reasoning Fabric) is a neuro-symbolic-causal agentic system.

Core Architecture: 4-layer cognitive stack
1. Router (Layer 1): Cynefin classification -> routes to appropriate solver
2. Cognitive Mesh (Layer 2): LangGraph agents (Deterministic, Causal, Bayesian, Circuit Breaker)
3. Reasoning Services (Layer 3): Neo4j (causal graphs), Redis (memory), Bayesian inference
4. Guardian (Layer 4): Policy enforcement, HumanLayer approval gates, optional OPA

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

### EXPLAINABILITY REQUIREMENTS (Phase 6)
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
CARF_API_URL=http://localhost:8000  # Streamlit -> API target
CARF_DATA_DIR=./var             # Dataset registry storage (optional)
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
      components/carf/    # Core UI components (10 implemented)
        BayesianPanel.tsx
        CausalAnalysisCard.tsx
        CausalDAG.tsx
        CynefinRouter.tsx
        DashboardHeader.tsx
        DashboardLayout.tsx
        ExecutionTrace.tsx
        GuardianPanel.tsx
        QueryInput.tsx
        ResponsePanel.tsx
      services/           # API client layer
      types/              # TypeScript type definitions
  src/
    core/               # Base classes, state schemas (NO external deps)
    services/           # External integrations (Neo4j, HumanLayer, Kafka, OPA)
    workflows/          # LangGraph definitions (the wiring)
    tools/              # Atomic tools (Pydantic schemas required)
    utils/              # Telemetry, resiliency decorators
    dashboard/          # Streamlit Epistemic Cockpit (legacy)
  config/               # YAML config and OPA policy
    opa/
  docs/                 # Architecture docs, walkthroughs
  tests/
    unit/               # Tool logic tests
    eval/               # LLM-as-a-judge scenarios
    mocks/              # Mock HumanLayer, Neo4j, etc.
  demo/                 # Sample datasets and payloads
  var/                  # Local dataset registry storage (gitignored)
  scripts/              # Demo seed scripts
  CURRENT_STATUS.md     # Living task/status doc
  AGENTS.md             # This file
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

## Current Phase: Phase 6 - Enhanced UIX & Explainability

### In Scope (Phase 6):
- **Explainability & Transparency**
  - Drill-down modals for all analytical results
  - Confidence decomposition (data/model/validation components)
  - Data provenance links from results to source rows
  - "Why not?" alternative path visibility

- **Enhanced UIX Components** (React Cockpit - `carf-cockpit/`)
  - `OnboardingOverlay.tsx` - First-run scenario selection
  - `DataOnboardingWizard.tsx` - 5-step data upload flow
  - `ConversationalResponse.tsx` - Dialog-based results with confidence zones
  - `FloatingChatTab.tsx` - Bottom-right persistent chat
  - `WalkthroughManager.tsx` - Multi-track guided tours
  - `MethodologyModal.tsx` - Transparency drill-downs

- **Interactive Walkthrough**
  - Quick Demo track (2-3 min)
  - Analyst Onboarding track (5-7 min)
  - Contributor Guide track (10-15 min)
  - Production Deployment track (5-10 min)

### CSL-Core Policy Engine
- **Role:** Primary policy enforcement layer for all CARF agent actions
- **Engine:** Built-in Python evaluator (CSL-Core Z3 optional)
- **Integration:** CSLToolGuard wraps workflow nodes (causal_analyst, bayesian_explorer) with policy checks
- **Modes:** `enforce` (block on violation) | `log-only` (audit trail only)
- **Audit:** Bounded deque (maxlen=1000) per AP-4, Kafka audit integration for CSL fields
- **API:** Full CRUD via `/csl/*` endpoints, natural language rule creation supported

### Completed (Phases 1-5):
- Full Cynefin router and cognitive mesh
- Neo4j persistence + query utilities
- DoWhy/EconML and PyMC optional inference paths
- Streamlit Epistemic Cockpit
- React Cockpit foundation (10 core components)
- Kafka audit trail (optional)
- OPA Guardian integration (optional)
- Docker Compose demo stack + seed scripts

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

---

## Commit Protocol

1. Atomic commits: One feature per commit
2. Always include updates to `AGENTS.md` if agent logic changes
3. Format: `type(scope): description`
   - `feat(router)`: Add entropy-based classification
   - `fix(guardian)`: Handle edge case in policy check
   - `docs(agents)`: Update testing commands
