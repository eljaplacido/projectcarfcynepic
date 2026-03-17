# Contributing to CARF

Thank you for your interest in contributing to CARF (Complex-Adaptive Reasoning Fabric)! This document provides guidelines for contributing to the project.

## Developer Certificate of Origin

All contributions to this project must be accompanied by a
Developer Certificate of Origin (DCO) sign-off. By adding a
`Signed-off-by` line to your commit messages, you certify that:

1. The contribution is your original work, or you have the right
   to submit it.
2. You grant Cisuregen the rights described in the project LICENSE
   (BSL 1.1 Section 5).
3. You understand your contribution will be publicly available
   under the BSL 1.1 terms.

To sign off, add `-s` to your git commit:

```bash
git commit -s -m "Add feature X"
```

This produces:

```
Signed-off-by: Your Name <your.email@example.com>
```

Pull requests without DCO sign-off will not be merged.

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome contributors of all backgrounds and experience levels.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for React cockpit)
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/projectcarf.git
   cd projectcarf
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev,dashboard,kafka]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (or use CARF_TEST_MODE=1 for offline testing)
   ```

5. **Run tests**
   ```bash
   pytest tests/ -v
   ```

6. **Start the development servers**
   ```bash
   # Backend API
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

   # React Cockpit (in separate terminal)
   cd carf-cockpit
   npm install
   npm run dev
   ```

## Project Structure

```
projectcarf/
├── src/
│   ├── core/           # Schemas, state, LLM utilities, deployment profiles
│   ├── services/       # 30+ services (causal, bayesian, governance, monitoring, etc.)
│   ├── workflows/      # LangGraph orchestration (graph.py, router.py, guardian.py)
│   ├── api/routers/    # 17 FastAPI routers (80+ endpoints)
│   ├── mcp/            # MCP server (18 cognitive tools)
│   └── main.py         # FastAPI entry point
├── carf-cockpit/       # React Platform Cockpit (59 components, 4 views)
├── tests/              # 1,365+ tests (unit, integration, e2e, deepeval)
├── benchmarks/         # 45 hypotheses (H0-H45) + realism gate
├── docs/               # 40+ architecture docs
├── demo/               # 17 demo scenarios and data
├── models/             # Trained models (DistilBERT + 5 CausalForest)
└── config/             # Policies, federated policies, governance boards
```

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear reproduction steps
4. Include environment details (OS, Python version, etc.)

### Submitting Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below

3. **Write tests** for new functionality
   ```bash
   pytest tests/ -v --cov=src
   ```

4. **Run linting**
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "feat: add new causal estimator for time series"
   ```

6. **Push and create a PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Use Pydantic v2 for data models
- Write docstrings for public APIs
- Keep functions focused and small

```python
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    """Result of a causal analysis.

    Attributes:
        effect: Estimated causal effect
        confidence_interval: 95% CI bounds
        p_value: Statistical significance
    """
    effect: float
    confidence_interval: tuple[float, float]
    p_value: float | None = None
```

### TypeScript (React Cockpit)

- Use TypeScript strict mode
- Define interfaces for all props and state
- Use React functional components with hooks
- Follow the existing component structure

```typescript
interface CausalResultProps {
    result: CausalAnalysisResult | null;
    onViewMethodology?: () => void;
}

const CausalResult: React.FC<CausalResultProps> = ({ result, onViewMethodology }) => {
    // ...
};
```

### Testing

- Write unit tests for all new functionality
- Use `pytest` for Python tests
- Use `CARF_TEST_MODE=1` for offline testing
- Aim for meaningful coverage, not 100%

```python
def test_causal_effect_estimation():
    """Test that causal effect is estimated correctly."""
    engine = CausalInferenceEngine()
    result = engine.analyze(test_data)

    assert result.effect is not None
    assert -1 <= result.effect <= 1
```

## Areas for Contribution

### Good First Issues

- Documentation improvements
- Adding type hints to existing code
- Writing additional unit tests
- UI/UX polish for React cockpit

### Feature Development

- Scalable inference modes (Phase 18E: configurable MCMC/variational/cached)
- Multi-agent collaborative causal discovery (Phase 18F)
- New causal estimators (instrumental variables, regression discontinuity)
- Additional Bayesian models
- Enhanced visualization components

### Architecture

- Multi-tenant workspace support with governance isolation
- Kubernetes deployment manifests
- Federated causal learning across deployments
- Performance optimizations

### Safety & Monitoring

- Enhanced drift detection algorithms
- Advanced bias auditing (intersection of domain + quality + verdicts)
- Automated compliance mapping (regulation text → CSL rules)
- Benchmark data realism improvements

### Key References for Contributors

- **AGENTS.md** — Antipatterns AP-1 through AP-10, SRR model, coding standards
- **docs/CARF_RSI_ANALYSIS.md** — RSI alignment requirements
- **docs/EVALUATION_FRAMEWORK.md** — Quality metrics and benchmark requirements (45 hypotheses)
- **docs/FUTURE_ROADMAP.md** — Research-informed roadmap with academic references

## Documentation

- Update relevant docs when changing functionality
- Add docstrings to new Python functions
- Update README for user-facing changes
- Add JSDoc comments to TypeScript functions

## Review Process

1. All PRs require at least one review
2. CI checks must pass (tests, linting)
3. Breaking changes need discussion
4. Large features may require RFC document

## Getting Help

- Open a GitHub Discussion for questions
- Review existing documentation in `/docs`
- Check the README for common setup issues

## License

By contributing, you agree that your contributions will be licensed under the project's [BSL 1.1 License](LICENSE). You may be asked to sign a [Contributor License Agreement (CLA)](CLA.md).

---

Thank you for contributing to CARF! Your efforts help advance transparent, explainable AI decision-making.
