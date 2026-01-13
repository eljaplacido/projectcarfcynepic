# Project Structure Best Practices

## 1. Optimized Project Initialization Prompt

This prompt requests production-grade patterns such as Pydantic type safety, MECE folder structure, and dual-memory architecture.

Role: You are a senior AI architect specializing in production-grade agentic systems.

Task: Initialize a Python-based agentic AI project structure.

Framework and Standards:

- Use LangGraph or CrewAI as the orchestration layer.
- Enforce type safety: All agent states and tool inputs must use Pydantic BaseModel.
- Enforce reliability: Include the tenacity library and create retry/circuit breaker utilities.

Directory Structure Requirements (MECE):

- `src/core/`: Base agent classes and state definitions
- `src/tools/`: Custom tools with docstrings, type hints, and Pydantic schemas
- `src/config/`: YAML configuration for agent definitions and prompts
- `tests/`: Static analysis and LLM-as-a-judge evaluation harness

Memory Architecture:

- Scaffold a dual-memory system: short-term (Redis/in-memory) and long-term (vector DB/SQL)

Output:

1. Generate the folder tree.
2. Create `pyproject.toml` using uv or poetry.
3. Draft `src/core/state.py` using Pydantic.
4. Draft an `AGENTS.md` file template for AI-specific operational details.

---

## 2. Detailed Code Repository Structure

Successful production systems decouple agent definitions (YAML/config) from agent logic (Python). Recommended universal structure:

```
my-production-agent/
  .github/workflows/       # CI/CD pipelines
  config/                  # Declarative definitions
    agents.yaml            # Roles, goals, backstories
    tasks.yaml             # Task descriptions and outputs
    prompts.yaml           # System prompts and guardrails
  src/
    main.py                # Entry point
    core/                  # Core architecture
      state.py             # Pydantic state schemas
      memory.py            # Redis/vector DB connectors
      orchestration.py     # Graph or crew definitions
    tools/                 # Tool implementations
      __init__.py
      web_search.py        # Callable with type hints and docstrings
      data_analysis.py
    utils/                 # Reliability and observability
      telemetry.py         # Tracing setup
      resiliency.py        # Retry/circuit breaker decorators
  tests/
    unit/                  # Tool logic tests
    eval/                  # LLM-as-a-judge scenarios
  .env.example
  pyproject.toml           # Dependencies (Pydantic, Tenacity, LangGraph)
  AGENTS.md                # Operational context for AI agents
  README.md                # Human-readable documentation
```

---

## 3. Documentation Structure Strategy

Dual-audience documentation separates human onboarding from AI operating context.

### A. README.md (For Humans)

- Focus on the what and why.
- Include an architecture diagram (sequential vs handoff).
- Installation and configuration steps.
- Observability and tracing guidance.

### B. AGENTS.md (For AI Context)

- Testing commands (exact)
- Linting rules
- Required environment variables
- Immutable core files (do not touch)

---

## Summary of Changes to Your Approach

- Add `AGENTS.md` as a standard artifact.
- Enforce Pydantic-native state management.
- Request reliability scaffolding (retry and circuit breaker) at initialization.
