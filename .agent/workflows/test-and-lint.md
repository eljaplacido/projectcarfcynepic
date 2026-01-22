---
description: Run all tests and linting for CARF project
---

# Test and Lint Workflow

Run this workflow before committing changes.

// turbo-all

## Steps

1. Run Python linting:
```bash
ruff check src/ tests/
```

2. Run Python type checking:
```bash
mypy src/ --strict
```

3. Run all backend tests:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

4. Run frontend TypeScript build:
```bash
cd carf-cockpit && npm run build
```

5. (Optional) Run frontend tests when available:
```bash
cd carf-cockpit && npm test
```

## Success Criteria
- All tests pass
- No linting errors
- TypeScript build succeeds
- Coverage above 60%
