---
description: Run comprehensive test suite with coverage and linting for Project CARF
---

# CARF Test Runner Skill

## Purpose
Validate codebase integrity before committing changes. Executes pytest with coverage, runs linting, and reports results.

## When to Use
- Before any commit or PR
- After implementing new features
- After modifying existing code
- As part of CI verification

## Prerequisites
- Virtual environment activated: `.venv\Scripts\activate`
- Dependencies installed: `pip install -e ".[dev]"`

## Execution Steps

### 1. Run Backend Tests
```bash
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

**Expected Output:**
- 323+ tests passing (280 existing + 43 new Phase 9 tests)
- Coverage report showing ~64% coverage
- No test failures

**New Phase 9 Tests:**
- `tests/unit/test_explanations.py` - 12 tests for ExplanationService
- `tests/unit/test_chat.py` - 15 tests for ChatService
- `tests/unit/test_file_analyzer.py` - 16 tests for FileAnalyzer

**If Tests Fail:**
1. Note the failing test name and error message
2. Check if it's a flaky test (re-run once)
3. If persistent, investigate the failing test file

### 2. Run Linting
```bash
.venv\Scripts\python -m ruff check src/ tests/
```

**Expected Output:**
- No linting errors
- If errors found, they must be fixed before commit

**Auto-fix Linting:**
```bash
.venv\Scripts\python -m ruff check src/ tests/ --fix
.venv\Scripts\python -m ruff format src/ tests/
```

### 3. Run Frontend Type Check (if React cockpit modified)
```bash
cd carf-cockpit
npm run build
```

**Expected Output:**
- TypeScript compilation succeeds
- Vite build completes without errors

## Success Criteria
| Check | Criteria |
|-------|----------|
| Backend Tests | All tests green (280+) |
| Coverage | ≥60% |
| Ruff Lint | 0 errors |
| TypeScript | Build passes |

## Troubleshooting

### Common Issues

**"No module named 'src'"**
- Ensure you're running from project root
- Ensure package is installed: `pip install -e .`

**Import errors in tests**
- Check `CARF_TEST_MODE=1` is set in `tests/conftest.py`
- LLM stubs are loaded for offline testing

**TypeScript errors**
- Run `npm install` in `carf-cockpit/`
- Check for missing type definitions
