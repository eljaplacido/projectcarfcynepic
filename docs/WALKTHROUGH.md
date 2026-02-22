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

## Data Feasibility Guide

Understanding which analysis types work best with your data is essential for reliable results.

### Quantitative / Tabular Data (Best Fit)

CARF's causal and Bayesian engines are purpose-built for structured, quantitative data:

| Analysis | Data Requirements | Minimum Rows | Key Columns |
|----------|-------------------|--------------|-------------|
| **Causal (DoWhy)** | CSV/JSON with treatment + outcome | ~50+ | Treatment (binary/continuous), Outcome (numeric), Covariates |
| **Bayesian (PyMC)** | Observations or counts | ~20+ | Parameter of interest, priors |
| **Fast Oracle (ChimeraOracle)** | Pre-trained on scenario data | Trained model required | Same as causal |
| **Deep Analysis** | Same as causal, larger preferred | ~100+ | Same as causal |
| **Sensitivity Check** | Same as causal | ~50+ | Same as causal |

**ChimeraOracle Auto-Activation**: When a scenario has a pre-trained CausalForestDML model, the pipeline automatically uses it for sub-millisecond predictions — no `use_fast_oracle` flag needed. Falls back to full DoWhy analysis if no trained model exists.

### Qualitative / Document Data (Semantic Analysis)

For non-tabular data (reports, documents, mixed media), CARF leverages semantic understanding through:

- **Natural language queries**: The LLM layer interprets qualitative questions and routes them through the Cynefin framework
- **Semantic classification**: Queries about policies, strategies, or qualitative relationships are routed to appropriate domains
- **Chat-guided analysis**: The AI chat helps users formulate quantifiable hypotheses from qualitative observations

**Important**: Causal effect estimation and Bayesian inference require numeric data. When working with qualitative data, the platform guides you toward formulating testable hypotheses and identifying measurable proxies.

### What to Expect Per Domain

| Cynefin Domain | Data Type | What You Get |
|----------------|-----------|-------------|
| **Clear** | Any | Deterministic lookup, rule-based response |
| **Complicated** | Tabular (numeric) | Full causal DAG, effect estimates, refutation tests, confidence intervals |
| **Complex** | Tabular or observations | Bayesian belief updates, uncertainty decomposition, probe recommendations |
| **Chaotic** | Any | Emergency protocol, human escalation |
| **Disorder** | Any | Human review required |

---

## Feedback System

CARF includes a persistent feedback loop for continuous improvement:

- **Quality Ratings**: Rate analysis results 1-5 stars
- **Domain Overrides**: Correct Cynefin domain classifications to improve routing
- **Issue Reports**: Flag problems for investigation
- **Improvement Suggestions**: Propose enhancements

All feedback is persisted to SQLite (`var/carf_feedback.db`) and available for downstream learning pipelines. Domain overrides can be exported for Router retraining.

---

## Benchmark Testing Guide

CARF includes a comprehensive benchmark suite to validate every component and compare CARF against raw LLM baselines. The benchmarks test 9 falsifiable hypotheses (H1-H9).

### Prerequisites

Ensure the backend API is running:
```bash
python -m uvicorn src.main:app --reload --port 8000
```

### Technical Benchmarks

#### 1. Router Classification Benchmark (H1-related)

Tests Cynefin domain routing accuracy against 456 labeled queries.

```bash
# Generate the test set (one-time)
python benchmarks/technical/router/generate_test_set.py

# Run the benchmark
python benchmarks/technical/router/benchmark_router.py
python benchmarks/technical/router/benchmark_router.py -o results/router_results.json
```

**Pass Criteria:** F1 >= 0.85, ECE < 0.10
**Metrics:** Overall accuracy, weighted F1, per-domain accuracy, confusion matrix, latency P50/P95/P99

**What to look for:**
- Per-domain accuracy: Clear and Complicated should be highest, Disorder lowest
- ECE (Expected Calibration Error): Measures whether confidence scores match actual accuracy
- Confusion matrix: Reveals systematic misclassification patterns

#### 2. Causal Inference Benchmark (H1)

Tests DoWhy/EconML causal effect estimation against 3 synthetic data-generating processes.

```bash
python benchmarks/technical/causal/benchmark_causal.py
python benchmarks/technical/causal/benchmark_causal.py -o results/causal_results.json
```

**Pass Criteria:** ATE MSE < 0.5 (IHDP dataset standard)
**Metrics:** ATE MSE, bias, CI coverage, refutation pass rate

**What to look for:**
- Linear DGP (true ATE=3.0): Should produce ATE close to 3.0
- Nonlinear DGP (true ATE=2.5): Tests robustness to model misspecification
- Null effect DGP (true ATE=0.0): Should NOT find a significant effect

#### 3. Bayesian Inference Benchmark (H2)

Tests PyMC posterior calibration across 3 scenario types.

```bash
python benchmarks/technical/bayesian/benchmark_bayesian.py
python benchmarks/technical/bayesian/benchmark_bayesian.py -o results/bayesian_results.json
```

**Pass Criteria:** Coverage >= 90%
**Metrics:** Posterior presence, uncertainty bounds, probe count, response quality

**What to look for:**
- `posterior_present`: Should be `true` for all scenarios
- `uncertainty_bounded`: Credible intervals should be finite and ordered
- `uncertainty_tracked`: Epistemic and aleatoric uncertainty separated

#### 4. Guardian Policy Benchmark (H3, H4)

Tests CSL/OPA policy enforcement: violation detection and determinism.

```bash
python benchmarks/technical/guardian/benchmark_guardian.py
python benchmarks/technical/guardian/benchmark_guardian.py -o results/guardian_results.json
```

**Pass Criteria:** 100% detection rate, < 5% FPR, 100% determinism
**Metrics:** Detection rate, false positive rate, determinism rate (5 runs per case)

**What to look for:**
- 3 violation cases: `budget_exceeded`, `unauthorized_high_risk`, `low_confidence_action` — all must be detected
- 2 legitimate cases: `safe_lookup`, `authorized_causal` — should NOT trigger violations
- Determinism: Same input must produce same output across all 5 runs

#### 5. Performance/Latency Benchmark (H6, H9)

Tests P50/P95/P99 latency and memory stability across domains.

```bash
python benchmarks/technical/performance/benchmark_latency.py
python benchmarks/technical/performance/benchmark_latency.py --queries 100
python benchmarks/technical/performance/benchmark_latency.py -o results/latency_results.json
```

**Pass Criteria:** P95 < 10s, memory stable over 500+ queries
**Metrics:** Per-domain P50/P95/P99, RSS memory growth

**What to look for:**
- Clear domain should be fastest (< 1s)
- Complicated domain (DoWhy): expect 2-5s
- Complex domain (PyMC): expect 3-8s
- Memory RSS should not grow unboundedly over iterations

#### 6. ChimeraOracle Benchmark (H8)

Tests fast CausalForestDML prediction speed vs full DoWhy pipeline.

```bash
python benchmarks/technical/chimera/benchmark_oracle.py
python benchmarks/technical/chimera/benchmark_oracle.py -o results/oracle_results.json
```

**Pass Criteria:** Speed ratio >= 10x, accuracy loss < 20%
**Metrics:** Speed ratio (DoWhy time / Oracle time), accuracy loss percentage

**What to look for:**
- Oracle auto-trains if no model exists (first run will include training time)
- Speed ratio: Oracle should be 10-100x faster than DoWhy
- Accuracy loss: |Oracle ATE - DoWhy ATE| / |DoWhy ATE| should be < 20%

### Use Case Benchmarks (End-to-End)

Runs CARF pipeline and raw LLM baseline side-by-side across 6 industries.

```bash
# Run all use case scenarios
python benchmarks/use_cases/benchmark_e2e.py

# Run specific scenarios
python benchmarks/use_cases/benchmark_e2e.py --scenarios supply_chain,finance

# Save results
python benchmarks/use_cases/benchmark_e2e.py --output results/e2e_results.json
```

**Industries covered:**

| Industry | Domain | Query Example |
|----------|--------|---------------|
| Supply Chain | Complicated | Supplier diversification effect on disruption |
| Financial Risk | Complicated | Discount impact on customer churn |
| Sustainability | Complicated | Scope 3 emissions attribution |
| Critical Infrastructure | Chaotic | Grid voltage stability |
| Healthcare | Complex | Treatment protocol uncertainty |
| Energy | Complicated | Renewable energy ROI |

**What to look for per scenario:**
- **Domain classification**: Does CARF route to the expected Cynefin domain?
- **Causal evidence**: Are treatment effects detected with correct direction?
- **Policy compliance**: Does Guardian catch violations in risky scenarios?
- **LLM comparison**: How does raw LLM reasoning compare to CARF's structured approach?

### Raw LLM Baseline

Runs queries through a raw LLM without CARF pipeline for comparison.

```bash
python benchmarks/baselines/raw_llm_baseline.py --test-set benchmarks/technical/router/test_set.jsonl
```

### Generating the Unified Report

Aggregates all benchmark results and tests the 9 falsifiable hypotheses.

```bash
python benchmarks/reports/generate_report.py
python benchmarks/reports/generate_report.py --results-dir benchmarks/results
python benchmarks/reports/generate_report.py --output report.json
```

**The 9 Hypotheses Tested:**

| ID | Claim | Pass Criteria |
|----|-------|---------------|
| H1 | CARF DoWhy achieves >= 50% lower ATE MSE than raw LLM | MSE ratio < 0.5 |
| H2 | Bayesian posterior coverage >= 90% vs LLM ~60-70% | Coverage >= 0.9 |
| H3 | Guardian achieves 100% violation detection | Detection rate = 1.0 |
| H4 | Guardian 100% deterministic across runs | Determinism = 1.0 |
| H5 | EU AI Act compliance >= 90% vs LLM < 30% | Compliance >= 0.9 |
| H6 | CARF 2-5x slower but quality compensates | Latency within bounds |
| H7 | Hallucination reduction >= 40% | Reduction rate >= 0.4 |
| H8 | ChimeraOracle >= 10x faster, < 20% accuracy loss | Speed >= 10x | **PASS** |
| H9 | Memory stable over 500+ queries | RSS growth bounded |

### Running All Benchmarks at Once

```bash
# Via API (backend must be running)
curl -X POST http://localhost:8000/benchmarks/run-all

# Or run each script sequentially
python benchmarks/technical/router/benchmark_router.py -o results/router.json && \
python benchmarks/technical/causal/benchmark_causal.py -o results/causal.json && \
python benchmarks/technical/bayesian/benchmark_bayesian.py -o results/bayesian.json && \
python benchmarks/technical/guardian/benchmark_guardian.py -o results/guardian.json && \
python benchmarks/technical/performance/benchmark_latency.py -o results/latency.json && \
python benchmarks/technical/chimera/benchmark_oracle.py -o results/oracle.json && \
python benchmarks/use_cases/benchmark_e2e.py -o results/e2e.json && \
python benchmarks/reports/generate_report.py --results-dir results -o results/report.json
```

### Interpreting Benchmark Results in the UI

Benchmark results surface in the CARF Cockpit in several places:

1. **Simulation Arena**: Compare two analysis sessions against contextual benchmarks derived from your actual data (not generic numbers)
2. **Developer View → Evaluation Metrics**: See per-step quality scores (Relevancy, Hallucination Risk, Reasoning Depth)
3. **Executive Dashboard**: Aggregate quality KPIs and compliance scores
4. **Guardian Panel**: Policy enforcement results match the Guardian benchmark criteria

---

## TLA+ Formal Verification

CARF includes TLA+ specifications for formal verification of workflow invariants.

### StateGraph Specification

Verifies the core LangGraph workflow properties:
- **Liveness**: Every request terminates
- **Safety**: No domain agent runs without Router classification
- **Bounded reflections**: Self-correction limited to MaxReflections=2
- **Guardian invariant**: No final response without Guardian check

```bash
# Run with TLC model checker (requires TLA+ toolbox)
java -jar tla2tools.jar -config tla_specs/StateGraph.cfg tla_specs/StateGraph.tla
```

### Escalation Protocol Specification

Verifies human-in-the-loop escalation behavior:
- Chaotic/Disorder domains always escalate
- Low-confidence queries trigger escalation
- No escalation is silently dropped
- All pending escalations resolve within bounded time

```bash
java -jar tla2tools.jar -config tla_specs/EscalationProtocol.cfg tla_specs/EscalationProtocol.tla
```

See `tla_specs/README.md` for detailed TLC configuration and concept mapping.

---

## Actionable Insights & Roadmaps

CARF generates persona-specific action items and analysis roadmaps alongside standard insights.

### How It Works

After any analysis, the `/insights/enhanced` endpoint returns three types of intelligence:

1. **Insights** — Standard analytical observations (existing)
2. **Action Items** — Concrete next steps with effort estimates
3. **Roadmap** — Sequenced analysis plan with dependencies

### Action Items

Each action item includes:
- **Title and description**: What to do and why
- **Effort badge**: `quick` (green), `medium` (yellow), or `deep` (orange)
- **Category**: `data_quality`, `model_improvement`, `risk_mitigation`, or `exploration`
- **API endpoint** (optional): Pre-wired endpoint for one-click execution

**Persona-specific actions:**

| Persona | Example Actions |
|---------|----------------|
| **Analyst** | Run sensitivity analysis, review confounders, improve data quality |
| **Developer** | Train ChimeraOracle, optimize cache, set up monitoring |
| **Executive** | Assess business impact, approve pilot programs, schedule quarterly reviews |

### Roadmap

The roadmap provides a sequenced analysis plan:
- Steps are ordered with dependency tracking
- Each step shows estimated time
- Dependencies ensure logical ordering (e.g., "collect more data" before "re-run analysis")

### Using in the UI

In the React Cockpit, the InsightsPanel now has three tabs:
1. **Insights** — Standard analytical observations
2. **Action Items** — Clickable cards with effort badges
3. **Roadmap** — Vertical stepper with time estimates

### Using via API

```bash
curl -X POST http://localhost:8000/insights/enhanced \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "analyst",
    "domain": "complicated",
    "domain_confidence": 0.85,
    "has_causal_result": true,
    "causal_effect": -0.15,
    "refutation_pass_rate": 0.6,
    "sample_size": 200
  }'
```

---

## Smart Self-Correction (Reflector)

When the Guardian rejects a proposed action, the Smart Reflector automatically attempts to repair the action to comply with policies.

### How It Works

The reflector uses a **hybrid strategy**:

1. **Heuristic repair** (fast): Pattern-matching rules for known violation types
   - Budget violations → reduce amount by 20%
   - Threshold violations → reduce value by 10%
   - Approval violations → flag for human review
2. **LLM repair** (fallback): When heuristics don't match, the LLM generates a contextual repair with explanation

### Repair Flow

```
Guardian REJECTS action
    ↓
Smart Reflector attempts heuristic repair
    ↓ (if heuristic confidence < 0.7 or unknown violation)
Falls back to LLM-based contextual repair
    ↓
Repaired action returned to workflow
    ↓
Guardian re-evaluates
```

### Observability

Each repair includes:
- `strategy_used`: Which repair method was applied (heuristic/llm/hybrid)
- `repair_explanation`: Human-readable explanation of what was changed
- `confidence`: How confident the reflector is in the repair (0-1)
- `violations_addressed` / `violations_remaining`: Track what was fixed

### MCP Tool

External agents can use the reflector via MCP:
```
Tool: reflector_repair
Input: { proposed_action, violations, context }
Output: { repaired_action, strategy_used, explanation, confidence }
```

---

## Experience Memory

CARF maintains a semantic memory of past analyses to improve future queries.

### How It Works

The Experience Buffer uses sentence-transformers (all-MiniLM-L6-v2) for dense semantic embeddings, with automatic TF-IDF fallback when sentence-transformers is not installed. This provides:

- **Context augmentation**: Similar past results inform current analysis
- **Domain patterns**: Aggregated statistics per Cynefin domain
- **Learning over time**: The buffer grows as more queries are processed

### Querying Past Experiences

**Via API:**
```bash
# Find similar past analyses
curl "http://localhost:8000/experience/similar?query=supply+chain+risk&top_k=3"

# Get domain-level patterns
curl "http://localhost:8000/experience/patterns"
```

**Via MCP:**
```
Tool: query_experience_buffer
Input: { query: "supply chain risk", top_k: 3 }

Tool: experience_buffer_patterns
Input: {}
```

### What Gets Stored

Each completed analysis stores:
- Query text, domain classification, confidence
- Response summary (first 200 chars)
- Causal effect, Bayesian posterior, Guardian verdict
- Timestamp and session ID

### In the UI

The Developer view includes an **Experience Buffer Panel** showing similar past queries and domain patterns, refreshable on demand.

---

## Using CARF in Notebooks

The Library API provides notebook-friendly wrappers for all CARF cognitive services.

### Quick Start

```python
from src.api.library import classify_query, run_causal, run_pipeline, query_memory

# Classify a query
result = await classify_query("Why did costs increase 15%?")
print(result["domain"], result["confidence"])

# Run full pipeline
result = await run_pipeline("Does supplier program reduce emissions?")
print(result["response"])

# Run causal analysis with DataFrame
import pandas as pd
df = pd.read_csv("my_data.csv")
result = await run_causal(
    "Does X cause Y?",
    data=df,
    treatment="X",
    outcome="Y",
    covariates=["Z1", "Z2"]
)
print(result["effect_size"], result["confidence_interval"])

# Check Guardian policies
result = await check_guardian({"action_type": "invest", "amount": 50000})
print(result["verdict"])

# Query experience memory
result = await query_memory("supply chain risk", top_k=3)
print(result["similar_count"])
```

### Available Functions

| Function | Purpose |
|----------|---------|
| `classify_query(query)` | Cynefin domain classification |
| `run_causal(query, data, ...)` | Causal inference with DoWhy |
| `run_bayesian(query, observations, ...)` | Bayesian inference with PyMC |
| `check_guardian(proposed_action)` | Policy compliance check |
| `run_pipeline(query)` | Full CARF pipeline end-to-end |
| `query_memory(query, top_k)` | Similar past analyses |

All functions return plain dicts (JSON-serializable) for easy notebook display.

---

## Router Retraining from Feedback

Domain override feedback from users can be used to improve the Cynefin Router's classification accuracy.

### How It Works

1. **Collect feedback**: Users correct domain classifications via the Feedback panel
2. **Check readiness**: The system tracks override counts per domain
3. **Export training data**: Overrides are exported as JSONL for DistilBERT fine-tuning

### Checking Readiness

```bash
curl http://localhost:8000/feedback/retraining-readiness
```

Returns:
```json
{
  "total_overrides": 45,
  "domain_distribution": {"complicated": 20, "complex": 15, "clear": 10},
  "ready_for_retraining": true,
  "recommendation": "Sufficient overrides collected. Ready for retraining."
}
```

### Exporting Training Data

```bash
python scripts/retrain_router_from_feedback.py --output training_data.jsonl
python scripts/retrain_router_from_feedback.py --dry-run  # Preview without writing
```

The script validates training data (minimum samples per domain, contradiction detection) before export.

---

## UIX Rehaul Changes (Phase 15)

The following UI improvements affect the walkthrough experience:

### Renamed Sections
Panel headers have been renamed from method-centric to function-centric:
- "Causal DAG" is now "Cause & Effect Map"
- "Causal Analysis Results" is now "Impact Analysis"
- "Bayesian Panel" is now "Uncertainty & Belief Update"
- "Guardian Panel" is now "Safety & Compliance Check"
- "Execution Trace" is now "Decision Audit Trail"

### New Walkthrough Tracks
Three new guided tours are available in the walkthrough manager:
1. **Causal Analysis Deep Dive** — DAG exploration, effect interpretation, refutations, sensitivity
2. **Running Simulations** — What-if parameters, multi-variable simulator, scenario comparison
3. **Developer Debugging** — Architecture overview, agent flow, timeline, evaluation metrics

### Key Interaction Changes
- **Chat responses** now render proper markdown (bold, tables, code blocks, links)
- **Confidence badges** in the execution trace have hover tooltips explaining what high/medium/low means
- **Quality metrics** are clickable — expand to show industry baselines and plain-English interpretation
- **"Ask Follow-Up"** button on causal results generates a contextual question and sends it to chat
- **What-If Simulator** supports multiple parameters (treatment + confounders) instead of single slider
- **Sensitivity Plot** shows colored Robust/Fragile zones with plain English interpretation
- **Executive view** has adaptive chart types (Cards/Bar/Pie) and structured action items

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **PRD**: `docs/PRD.md`
- **Architecture**: `docs/SOLUTION_VISION.md`
- **LLM Strategy**: `docs/LLM_AGENTIC_STRATEGY.md`
- **Router Training**: `docs/ROUTER_TRAINING.md`
- **Data Layer**: `docs/DATA_LAYER.md`
- **Evaluation Framework**: `docs/EVALUATION_FRAMEWORK.md`
- **Benchmark Suite**: `benchmarks/README.md`

---

*CARF - Complex-Adaptive Reasoning Fabric*
*Transparent AI for Decision-Making Under Uncertainty*
