# CYNEPIC Architecture 0.5 - Current Status

**Last Updated**: 2026-01-22
**Phase**: Production Release Enhancement (Phase 11+)
**Overall Status**: Ready for GitHub Release

---

## Test Coverage

```
Total Tests: 365 passing
Overall Coverage: 64%
Python Lines: 4,000+ lines
React Components: 29 components
```

## Feature Completion Matrix

### Core Infrastructure

| Feature | Status | Coverage | Notes |
|---------|--------|----------|-------|
| FastAPI Backend | Complete | 44% | 40+ endpoints, full CRUD |
| LangGraph Orchestration | Complete | 56% | StateGraph with conditional routing |
| Cynefin Router | Complete | 59% | DistilBERT + entropy classification |
| Causal Engine | Complete | 26% | DoWhy integration, LLM fallback |
| Bayesian Engine | Complete | 30% | PyMC integration, LLM fallback |
| Guardian Layer | Complete | 63% | OPA + policy enforcement |
| Human Layer | Complete | 28% | HumanLayer SDK integration |

### React Frontend (carf-cockpit)

| Component | Status | Notes |
|-----------|--------|-------|
| DashboardLayout | Complete | Three-view architecture (Analyst/Executive/Developer) |
| CynefinRouter | Complete | Full transparency on classification + method impact |
| CausalDAG | Complete | React Flow visualization |
| BayesianPanel | Complete | Uncertainty quantification display |
| GuardianPanel | Complete | Policy status and verdicts |
| SimulationArena | Complete | Enhanced with method toggles and benchmarks |
| ExecutiveKPIPanel | Complete | KPI dashboard with filtering and summary |
| EscalationModal | Complete | Channel config, trigger explanation, manual review |
| DataOnboardingWizard | Complete | Sample data, auto-suggestions, guided flow |
| DeveloperView | Complete | System state, logs, architecture layers |
| IntelligentChatTab | Complete | Slash commands, context awareness |
| SetupWizard | Complete | LLM provider configuration |

### API Endpoints

| Category | Endpoints | Status |
|----------|-----------|--------|
| Health & Config | 4 | Complete |
| Query Processing | 2 | Complete |
| Dataset Management | 4 | Complete |
| Scenario Management | 3 | Complete |
| Simulation | 2 | Complete (duplicates removed) |
| Chat & Explanations | 7 | Complete |
| Developer Tools | 3 | Complete |
| Human-in-the-Loop | 3 | Complete |
| Benchmarking | 3 | Complete |

---

## Recent Improvements (2026-01-22)

### Backend Fixes
1. Removed duplicate `/simulations/run` and `/simulations/compare` endpoints
2. Fixed test failures in `test_api.py` (camelCase alignment)
3. Fixed `test_log_rotation` and `test_get_state` in developer tests
4. Removed debug print statements from main.py
5. Updated docstring to reflect CYNEPIC branding

### Frontend Enhancements

#### Executive View
- New `ExecutiveKPIPanel` component with:
  - Filterable KPI cards by category (confidence, quality, compliance, performance)
  - Status indicators and trend arrows
  - Executive summary text generation
  - Drill-down capability to analyst view

#### Human-in-the-Loop
- Enhanced `EscalationModal` with:
  - Trigger explanation panel (why was this escalated?)
  - Notification channel configuration (Slack, Email, Teams, Webhook)
  - Manual intervention request option (always available)
  - Impact preview when toggling methods

#### Cynefin Transparency
- Enhanced `CynefinRouter` with:
  - "How does this affect analysis?" expandable section
  - Method impact configuration for each domain
  - Primary/secondary methods display
  - Guardian policies applied per domain
  - Data requirements and uncertainty handling

#### Simulation Arena
- Enhanced with:
  - Analysis method toggles (Causal, Bayesian, Guardian)
  - Confidence threshold slider
  - Benchmark comparison dropdown (Industry, Historical, Custom)
  - Impact preview when methods disabled
  - Re-run with modified methods button

#### Data Onboarding
- Enhanced `DataOnboardingWizard` with:
  - Sample datasets for first-time users (Churn, Healthcare, Marketing)
  - Auto-detected variable suggestions
  - One-click "Apply all suggestions" button
  - Better guidance and tips

---

## Architecture Layers

```
Layer 1: Cynefin Router (Complexity Classification)
├── DistilBERT classifier + entropy calculation
├── Domain scores visualization
├── Method impact transparency
└── Key indicators extraction

Layer 2: Causal-Bayesian Mesh
├── Complicated → DoWhy/EconML causal inference
├── Complex → PyMC Bayesian inference
├── Clear → Deterministic rules
└── Chaotic → Circuit breaker

Layer 3: Guardian (Policy Enforcement)
├── OPA policy evaluation
├── Risk level assessment
├── Human escalation triggers
└── Audit trail logging

Layer 4: Human Layer (Escalation)
├── 3-Point Context notifications
├── Channel configuration
├── Manual intervention requests
└── Resolution tracking
```

---

## Configuration

### Required Environment Variables
```bash
LLM_PROVIDER=deepseek       # or "openai"
DEEPSEEK_API_KEY=sk-...     # Required if using DeepSeek
```

### Optional Environment Variables
```bash
OPENAI_API_KEY=sk-...       # If using OpenAI
HUMANLAYER_API_KEY=hl-...   # For human escalation
LANGSMITH_API_KEY=ls-...    # For tracing
NEO4J_URI=bolt://localhost:7687
KAFKA_ENABLED=false
OPA_ENABLED=false
```

---

## Running the System

### Backend
```bash
cd projectcarf
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev,dashboard]"
python -m src.main
```

### Frontend (React)
```bash
cd carf-cockpit
npm install
npm run dev
```

### Tests
```bash
pytest tests/ -v --cov=src
```

---

## Known Limitations

1. **Causal/Bayesian Engines**: Currently use LLM simulation when DoWhy/PyMC not available
2. **Neo4j Integration**: Connection pool exists but queries need real database
3. **Kafka Audit**: Infrastructure ready but not persisting to real Kafka
4. **Streamlit Dashboard**: 0% test coverage (deprecated in favor of React)

---

## Historical Decisions

### 2026-01-22
- **Phase 10 (Usability Polish)**: Implemented on-the-fly API key configuration.
  - Added `SettingsModal` for dynamic LLM provider switching.
  - Implemented backend hot-reload of LLM clients (`/config/update`).
  - Backend schema alignment and duplicate endpoint cleanup.
  - Enhanced all major frontend components for transparency and UX.

### 2026-01-21
- Production Release Enhancements (Phase A-K) completed
- SetupWizard, Simulation endpoints, EscalationModal, Benchmarking

### 2026-01-20
- Socratic Questioning Flow with Panel Highlighting
- Created questioningFlow.ts config

### 2026-01-17
- Phase 9 Testing Complete (43 tests)
- Phase 8 Scenario Sync Complete
- Phase 7 Backend Services Complete

---

## File Structure

```
projectcarf/
├── src/
│   ├── main.py              # FastAPI entry (1400+ lines)
│   ├── core/                # State schemas, LLM config
│   ├── services/            # 14 services
│   ├── workflows/           # LangGraph nodes
│   └── dashboard/           # Streamlit (legacy)
├── carf-cockpit/
│   └── src/
│       ├── components/carf/ # 29 React components
│       ├── services/        # API client
│       └── types/           # TypeScript types
├── tests/
│   └── unit/               # 20+ test files
└── docs/                   # Documentation
```
