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
  src/
    core/               # Base classes, state schemas (NO external deps)
    services/           # External integrations (Neo4j, HumanLayer, Kafka, OPA)
    workflows/          # LangGraph definitions (the wiring)
    tools/              # Atomic tools (Pydantic schemas required)
    utils/              # Telemetry, resiliency decorators
    dashboard/          # Streamlit Epistemic Cockpit
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

## Current Phase: Phase 4 - Research Demo

In scope:
- Full Cynefin router and cognitive mesh
- Neo4j persistence + query utilities
- DoWhy/EconML and PyMC optional inference paths
- Streamlit Epistemic Cockpit
- Kafka audit trail (optional)
- OPA Guardian integration (optional)
- Docker Compose demo stack + seed scripts

Out of scope:
- Production autoscaling and Kubernetes
- Enterprise-grade observability beyond demo

---

## Commit Protocol

1. Atomic commits: One feature per commit
2. Always include updates to `AGENTS.md` if agent logic changes
3. Format: `type(scope): description`
   - `feat(router)`: Add entropy-based classification
   - `fix(guardian)`: Handle edge case in policy check
   - `docs(agents)`: Update testing commands
