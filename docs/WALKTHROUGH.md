# CARF Complete Walkthrough Guide

This comprehensive guide walks you through every feature of the Complex-Adaptive Reasoning Fabric (CARF) platform, from first-time setup to advanced analysis techniques.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Quick Demo Track](#quick-demo-track)
3. [Analyst Walkthrough](#analyst-walkthrough)
4. [Developer Walkthrough](#developer-walkthrough)
5. [Executive Walkthrough](#executive-walkthrough)
6. [Using Your Own Data](#using-your-own-data)
7. [Configuring LLM Providers](#configuring-llm-providers)
8. [Available Demo Scenarios](#available-demo-scenarios)
9. [Understanding Results](#understanding-results)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/projectcarf.git
cd projectcarf

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev,causal,bayesian]"

# Install frontend
cd carf-cockpit
npm install
```

### Starting the Platform

**Terminal 1 - Backend API:**
```bash
cd projectcarf
python -m uvicorn src.main:app --reload --port 8000
```

**Terminal 2 - React Cockpit:**
```bash
cd projectcarf/carf-cockpit
npm run dev
```

**Access Points:**
- React Dashboard: http://localhost:5175
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Quick Demo Track

*Duration: ~2 minutes*

This track demonstrates CARF's core capabilities with pre-built scenarios.

### Step 1: Open the Dashboard

Navigate to http://localhost:5175. You'll see the Welcome overlay with scenario options.

### Step 2: Select a Scenario

Click any scenario card (e.g., "Scope 3 Attribution") to load pre-configured data and suggested queries.

### Step 3: Review the Query

The query input is pre-populated with a suggested question. You can:
- Use the suggested query as-is
- Modify the query text
- Click alternative suggested queries below

### Step 4: Run Analysis

Click "Send" to submit your query. Watch the progress indicator as CARF:
1. Routes the query to the appropriate Cynefin domain
2. Executes causal or Bayesian analysis
3. Runs refutation tests
4. Validates against Guardian policies

### Step 5: Explore Results

Review the analysis across multiple panels:
- **Cynefin Router**: Domain classification and confidence
- **Causal DAG**: Interactive graph of causal relationships
- **Causal Analysis**: Effect estimates and refutation tests
- **Guardian**: Policy compliance check

---

## Analyst Walkthrough

*Duration: ~5 minutes*

For users who want to analyze their own data and understand results in depth.

### Analyst View Features

Switch to Analyst view using the view toggle at the top of the dashboard.

#### 1. Query Input Panel

- **Natural language queries**: Type questions like "What is the effect of marketing spend on sales?"
- **Suggested queries**: Click pre-built queries tailored to your scenario
- **Conversational flow**: Follow guided questions to refine your analysis

#### 2. Cynefin Classification

The router classifies your query into one of five domains:

| Domain | Meaning | Analysis Type |
|--------|---------|---------------|
| **Clear** | Known cause-effect, deterministic | Lookup/Rule-based |
| **Complicated** | Experts can analyze, predictable | Causal Inference (DoWhy) |
| **Complex** | Emergent patterns, uncertain | Bayesian Inference (PyMC) |
| **Chaotic** | Act first, stabilize | Circuit Breaker |
| **Disorder** | Cannot classify | Human Escalation |

#### 3. Causal Analysis Results

For "Complicated" domain queries:

- **Average Treatment Effect (ATE)**: The estimated causal impact
- **Confidence Interval**: Range of plausible effect values
- **P-value**: Statistical significance
- **Refutation Tests**: Validation of causal assumptions
  - Placebo treatment test
  - Random common cause
  - Data subset validation
  - Bootstrap sensitivity

#### 4. Bayesian Belief Panel

For "Complex" domain queries:

- **Prior Distribution**: Initial beliefs before data
- **Posterior Distribution**: Updated beliefs after data
- **Credible Intervals**: 95% probability range
- **Uncertainty Decomposition**: Sources of uncertainty

#### 5. Causal DAG Viewer

Interactive directed acyclic graph showing:
- **Treatment nodes** (blue): Variables you can intervene on
- **Outcome nodes** (green): What you measure
- **Confounder nodes** (orange): Variables affecting both
- **Covariate nodes** (gray): Control variables

Click any node for detailed explanation and sensitivity analysis.

#### 6. Intervention Simulator

Simulate "what-if" scenarios:
1. Select a treatment variable
2. Adjust the intervention level
3. See predicted outcome changes
4. Review confidence in predictions

#### 7. Deep Analysis & Sensitivity Check

After an initial analysis, use action buttons for deeper investigation:

- **Deep Analysis**: Re-runs causal estimation with multiple alternative estimators (linear regression, propensity score matching, PS stratification) and computes heterogeneous treatment effects (CATE) across subgroups. Results show cross-method consistency and which subpopulations are most affected.

- **Sensitivity Check**: Runs three additional refutation tests beyond the standard set:
  1. **Placebo Treatment** — shuffles the treatment randomly to verify the effect disappears
  2. **Random Common Cause** — adds a random confounder to check estimate stability
  3. **Data Subset Validation** — tests whether the effect holds on an 80% subsample

  Returns per-test results with p-values and an overall robustness assessment.

Both buttons show progress messages in the loading indicator while running.

#### 8. Simulation Arena

Compare two analysis sessions side-by-side:

1. Run at least two queries to build analysis history
2. Open the Simulation Arena from the toolbar
3. Review the **Simulation Guide** (4-step walkthrough) at the top

**Contextual Benchmarks**: Instead of generic benchmarks, the arena derives benchmarks from your actual causal effect:
- **Measured Baseline** — the actual effect size from your analysis
- **Min Detectable Effect** — 10% of measured (smallest meaningful difference)
- **Strong Effect (2x)** — double the measured effect (ambitious target)

Compare treatment effects, p-values, and confidence intervals across scenarios.

#### 9. Agents Involved

View all AI agents that participated in your analysis:

- Each agent card shows: **name**, **category** (causal/bayesian/guardian/oracle/router), and **reliability score**
- Category colors: blue (causal/bayesian), green (guardian), amber (oracle), purple (router)
- Reliability scores default to 85% and are enriched with live tracker statistics when available
- Full dark theme support for all agent cards

#### 10. Executive Summary

Get a plain-English summary for decision-makers:

**Option A — Chat Command:**
Type `/summary` in the chat panel. CARF synthesizes the current analysis into a formatted summary with key finding, confidence level, risk assessment, and recommended action.

**Option B — Response Panel Button:**
Click the amber "Executive Summary" button below any analysis result. A collapsible panel shows:
- **Key Finding**: Human-readable interpretation of the causal effect
- **Confidence**: Derived from domain confidence, refutation pass rate, and Bayesian uncertainty
- **Risk Assessment**: Checks for policy violations, failed robustness, high uncertainty
- **Recommendation**: Action guidance based on Guardian verdict and domain type
- **Plain Explanation**: Narrative paragraph combining all findings

---

## Developer Walkthrough

*Duration: ~10 minutes*

For users who want to understand the system architecture and extend CARF.

### Developer View Features

Switch to Developer view to see:

#### 1. Execution Trace Timeline

Real-time visualization of the analysis pipeline:
- Router classification step
- Domain solver execution
- Reasoning service calls
- Guardian policy checks

Each step shows:
- Duration in milliseconds
- Input/output data
- Confidence level
- Status (completed/in_progress/pending)

#### 2. Architecture Flow Diagram

Interactive visualization of CARF's cognitive stack:

```
Query → Cynefin Router → Domain Solver → Guardian → Response
              ↓               ↓              ↓
         [LLM + ML]      [DoWhy/PyMC]   [Policy Engine]
```

#### 3. Data Layer Inspector

Explore the three data tiers:

- **Structured Data**: Datasets, schema detection, column types
- **Semantic Layer**: Neo4j causal knowledge graph
- **Operational Layer**: Kafka audit trail, OPA policy decisions

#### 4. Live Log Stream

Real-time backend logs with filtering:
- Router decisions
- LLM API calls
- Analysis progress
- Policy evaluations

#### 5. State Inspector

View the current EpistemicState:
```json
{
  "session_id": "...",
  "cynefin_domain": "complicated",
  "domain_confidence": 0.87,
  "entropy": 0.42,
  "reasoning_chain": [...],
  "guardian_verdict": "approved"
}
```

#### 6. CSL Tool Guard & Audit

View CSL policy enforcement in the execution trace:

- **CSLToolGuard** wraps workflow nodes with real-time policy checks
- Two modes: **enforce** (blocks on violation) and **log-only** (audit only)
- Bounded audit log (max 1,000 entries) tracks every policy evaluation
- Kafka audit events now include CSL fields: `csl_rules_checked`, `csl_rules_failed`, `csl_engine`, `csl_latency_ms`, `csl_violations`

#### 7. CSL API Endpoints

Test policies directly via the API:

```bash
# Check engine status
curl http://localhost:8000/csl/status

# List all policies
curl http://localhost:8000/csl/policies

# Get specific policy
curl http://localhost:8000/csl/policies/budget_limits

# Add a rule
curl -X POST http://localhost:8000/csl/policies/budget_limits/rules \
  -H "Content-Type: application/json" \
  -d '{"rule_name": "test_limit", "condition": {"user.role": "intern"}, "constraint": {"action.amount": {"op": "<=", "value": 100}}, "message": "Interns limited to $100"}'

# Test-evaluate a policy
curl -X POST http://localhost:8000/csl/evaluate \
  -H "Content-Type: application/json" \
  -d '{"context": {"user.role": "junior", "action.type": "transfer", "action.amount": 5000}}'

# Hot-reload policies
curl -X POST http://localhost:8000/csl/reload
```

### Key Code Locations

| Component | Path |
|-----------|------|
| Cynefin Router | `src/workflows/router.py` |
| Causal Service | `src/services/causal.py` |
| Bayesian Service | `src/services/bayesian.py` |
| Guardian Layer | `src/workflows/guardian.py` |
| Graph Orchestration | `src/workflows/graph.py` |
| CSL Policy Service | `src/services/csl_policy_service.py` |
| CSL Tool Guard | `src/services/csl_tool_guard.py` |
| CSL API Router | `src/api/routers/csl.py` |
| Executive Summary | `src/api/routers/transparency.py` |
| API Entry Point | `src/main.py` |
| React Components | `carf-cockpit/src/components/carf/` |
| Policy Editor | `carf-cockpit/src/components/carf/PolicyEditorModal.tsx` |
| Policy Files | `config/policies/*.csl` |

---

## Executive Walkthrough

*Duration: ~3 minutes*

For decision-makers who need high-level insights and actionable recommendations.

### Executive View Features

Switch to Executive view for a streamlined decision-support interface.

#### 1. Key Performance Indicators

Dashboard of critical metrics:

- **Total Impact**: Aggregate effect of recommended interventions
- **Confidence Level**: Overall reliability of analysis
- **Risk Score**: Composite risk assessment
- **Policy Compliance**: Guardian approval status

#### 2. Proposed Actions

AI-recommended actions ranked by expected impact:

| Priority | Action | Expected Impact | Confidence | Status |
|----------|--------|-----------------|------------|--------|
| 1 | Expand supplier program in EU | -45 tCO2e | High | Approved |
| 2 | Target large suppliers | -30 tCO2e | Medium | Pending Review |

Each action includes:
- Causal backing (not just correlation)
- Confidence interval
- Required approvals

#### 3. Risk & Compliance Summary

Guardian policy evaluation:
- Which policies were checked
- Pass/fail status
- Required escalations
- Auto-applied remediations

#### 3a. CSL Policy Editor

Click **"Configure"** in the Guardian panel to open the full-screen Policy Editor:

- **Left sidebar**: Lists all CSL policies (budget_limits, action_gates, chimera_guards, data_access, cross_cutting) with rule counts
- **Main area**: Displays rules for the selected policy as readable cards showing when-condition and then-constraint
- **Add Rule**: Type a natural language description (e.g., "Block transfers over $5000 for junior users") and the system parses it into a structured rule
- **Test Policy**: Evaluate the selected policy against a sample context to see pass/fail results with violation details
- **Reload**: Hot-reload policies from the backend without restart
- **Status bar**: Shows engine name, total policy count, and total rule count

CSL (Constraint Specification Language) policies enforce guardrails non-programmatically. The 5 built-in policies cover:

| Policy | Rules | Purpose |
|--------|-------|---------|
| budget_limits | 9 | Financial action limits by role and domain |
| action_gates | 8 | Approval requirements for high-risk actions |
| chimera_guards | 7 | Prediction safety bounds for ChimeraOracle |
| data_access | 6 | PII, encryption, and data residency rules |
| cross_cutting | 5 | Cross-domain rules spanning multiple areas |

#### 4. Transparency Indicators

EU AI Act compliance features:
- Explainability score
- Data provenance
- Human oversight status
- Audit trail link

#### 5. Escalation Queue

Pending items requiring human review:
- High-impact decisions above threshold
- Low-confidence recommendations
- Policy constraint violations

---

## Using Your Own Data

### Step 1: Prepare Your Data

**Supported Formats:**
- CSV files (up to 5,000 rows)
- JSON data arrays

**Required Structure:**
```csv
treatment_variable,outcome_variable,covariate1,covariate2
1,100,A,50
0,80,B,45
1,120,A,55
...
```

### Step 2: Upload Data

**Option A: Dashboard Upload**
1. Click "Upload Your Own Data" on the dashboard
2. Drag and drop your CSV file
3. Review auto-detected schema

**Option B: Chat Command**
1. Type `/analyze` in the chat panel
2. Follow the guided upload process

**Option C: API Upload**
```bash
curl -X POST http://localhost:8000/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_data",
    "data": [{"treatment": 1, "outcome": 100, "region": "EU"}]
  }'
```

### Step 3: Configure Variables

The Data Onboarding Wizard guides you through:

1. **Treatment Variable**: The intervention you want to study
   - Examples: `received_discount`, `marketing_spend`, `supplier_program`
   - Must be binary (0/1) or continuous

2. **Outcome Variable**: What you want to measure
   - Examples: `churned`, `sales`, `emissions`
   - Usually continuous

3. **Covariates**: Control variables
   - Examples: `region`, `age`, `customer_segment`
   - Help control for confounding

### Step 4: Select Analysis Type

- **Causal Analysis**: For "What is the effect of X on Y?" questions
  - Uses DoWhy + EconML
  - Requires treatment/outcome structure

- **Bayesian Inference**: For "Update my belief about parameter θ" questions
  - Uses PyMC
  - Works with observations or success/trial counts

### Step 5: Run Your Query

Type a natural language question:
- "What is the impact of discounts on customer churn?"
- "How does marketing spend affect sales?"
- "Update my belief about the conversion rate"

---

## Configuring LLM Providers

CARF uses LLMs for query routing, explanations, and chat. The statistical analysis (DoWhy, PyMC) runs independently.

### Option 1: DeepSeek (Recommended)

1. Create account at https://platform.deepseek.com
2. Generate an API key
3. In CARF, click Settings (⚙️)
4. Select "DeepSeek" provider
5. Enter your API key

**Cost:** ~$0.01 per analysis

### Option 2: OpenAI

1. Create account at https://platform.openai.com
2. Go to API keys section
3. Create a new secret key
4. In CARF Settings, select "OpenAI"
5. Enter your API key

### Option 3: Test Mode (No API)

For offline demos:
```bash
export CARF_TEST_MODE=1
python -m uvicorn src.main:app --reload
```

Uses pre-defined responses and mock routing.

---

## Available Demo Scenarios

| Scenario | Domain | Analysis Type | Description |
|----------|--------|---------------|-------------|
| **Scope 3 Attribution** | Complicated | Causal | Supplier program impact on emissions |
| **Discount vs Churn** | Complicated | Causal | Discount effect on customer retention |
| **Renewable Energy ROI** | Complicated | Causal | Solar investment returns |
| **Conversion Belief** | Complex | Bayesian | Belief update on conversion rates |
| **Shipping Carbon** | Complicated | Causal | Transport mode emissions comparison |

### Loading a Scenario

**Via Dashboard:**
1. Click scenario card
2. Review suggested queries
3. Click or modify query
4. Press Send

**Via API:**
```bash
# List scenarios
curl http://localhost:8000/scenarios

# Load specific scenario
curl http://localhost:8000/scenarios/scope3_attribution
```

---

## Understanding Results

### Causal Analysis Output

```json
{
  "effect_size": -71.2,
  "effect_interpretation": "Supplier program reduces emissions by 71.2 tCO2e on average",
  "confidence_interval": [-85.1, -57.3],
  "p_value": 0.001,
  "statistical_significance": "highly significant",
  "refutation_tests": {
    "placebo_treatment": "passed",
    "random_common_cause": "passed",
    "data_subset": "passed",
    "bootstrap": "passed"
  },
  "robustness_score": 4/4
}
```

### Bayesian Analysis Output

```json
{
  "posterior_mean": 0.42,
  "credible_interval_95": [0.35, 0.49],
  "prior": "Beta(2, 2)",
  "posterior": "Beta(44, 60)",
  "uncertainty_reduction": 0.65
}
```

### Guardian Decision

```json
{
  "verdict": "approved",
  "risk_level": "low",
  "policies_checked": ["budget_limit", "regional_compliance"],
  "policies_passed": 2,
  "escalation_required": false
}
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -e ".[dev,causal,bayesian]" --force-reinstall

# Check port availability
lsof -i :8000
```

### Frontend Connection Error

```bash
# Ensure backend is running first
curl http://localhost:8000/health

# Start frontend
cd carf-cockpit
npm install
npm run dev
```

### LLM Errors

```bash
# Verify API key is set
echo $DEEPSEEK_API_KEY

# Use test mode for demos
export CARF_TEST_MODE=1
```

### Analysis Failures

1. Check data format (CSV with headers)
2. Verify treatment is binary or continuous
3. Ensure outcome is numeric
4. Check for missing values

### Chat Not Responding

1. Verify LLM provider is configured
2. Check API key validity
3. Try test mode: `CARF_TEST_MODE=1`

### CSL Policy Issues

```bash
# Verify all policy files parse correctly
python scripts/verify_policies.py

# Check CSL engine status
curl http://localhost:8000/csl/status

# Disable CSL if causing issues
export CSL_ENABLED=false
```

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **PRD**: `docs/PRD.md`
- **Architecture**: `docs/SOLUTION_VISION.md`
- **LLM Strategy**: `docs/LLM_AGENTIC_STRATEGY.md`
- **Router Training**: `docs/ROUTER_TRAINING.md`

---

*CARF - Complex-Adaptive Reasoning Fabric*
*Transparent AI for Decision-Making Under Uncertainty*
