# Development Guidelines and Save Point Protocol

## 1. Living Documentation Protocol

Documentation is the source of truth for CARF. Keep it current as you work.

### 1.1 Update-First Rule

Before writing code for a new feature, update `AGENTS.md` or `CURRENT_STATUS.md`.

Why: If the coding agent crashes mid-task, the next agent can resume quickly.

### 1.2 CURRENT_STATUS.md

Maintain a root-level file that tracks the immediate state:

- Current Phase
- Active Task
- Recent Decisions
- Next Steps

---

## 2. Directory Structure (MECE Standard)

```
src/
  core/         # Base classes, AgentState, interfaces (no external deps)
  services/     # Concrete implementations (Neo4j, HumanLayer)
  workflows/    # LangGraph definitions (the wiring)
  tools/        # Atomic tools (must have Pydantic schemas)
config/         # YAML configuration (prompts, policies)
docs/           # Architecture, ADRs, user guides
tests/          # Pytest suite
  unit/         # Fast logic tests
  integration/  # Workflow/graph tests
  e2e/          # Full containerized tests
.github/        # CI/CD workflows
```

---

## 3. Testing Standards (QA Protocol)

### 3.1 Causal Refutation Test

Every new agent capability must include a test that verifies safe failure behavior.

Requirement: Create a test case where `confounder=True`. The agent must return a lower confidence score or refuse the prediction.

### 3.2 HumanLayer Mocks

Do not call the real HumanLayer API during unit tests. Use `tests/mocks/mock_human_layer.py` to simulate:

- Approve (happy path)
- Reject (error handling)
- Timeout or no response

### 3.3 LLM-as-a-Judge

For integration tests, use a simple judge pattern rather than manual review.

- Location: `tests/eval/judge_fixtures.py`
- Logic: Causal agent output must include keywords like "Confidence Interval" and "Refutation Passed".

---

## 4. DevOps and CI/CD Guidelines

### 4.1 Containerization (Docker)

- Single source of truth: `docker-compose.yml` defines the full stack.
- Local vs prod: Use `.env` to switch configurations.
- Never hardcode connection strings in Python files.

### 4.2 CI Pipeline (GitHub Actions)

Quality gates:

- Static analysis: `ruff` and `mypy --strict` before tests.
- Unit tests: `pytest tests/unit`
- Refutation checks: targeted causal validity tests

### 4.3 Deployment Strategy

- MVP: Direct deployment via Docker Compose.
- Future: Blue/Green deployment using Kubernetes (Phase 3).

---

## 5. Git and Commit Protocol

- Atomic commits: One feature, one commit.
- Docs sync: include updates to `CURRENT_STATUS.md` when agent logic changes.
