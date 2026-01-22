# Phase 7: Conversational Intelligence & AI Act Transparency [COMPLETED]

> **Note**: This implementation plan is now completed. See `CURRENT_STATUS.md` for the latest system state.

## Executive Summary

Transform the CARF Platform Cockpit into an **LLM-powered conversational interface** with full **explainability**, **Developer View transparency**, and **AI Act compliance**. Key themes:

1. **Dialog-Flow Query Experience** - Replace textarea with conversational interface
2. **LLM-Powered Guidance Chat** - Platform help, tutorials, result interpretation
3. **Component Explainability** - Why-based explanations for all panels
4. **Developer View / Live Cockpit** - Real-time workflow visualization for transparency
5. **Authentic Demo Data** - 100% realistic simulated data with data generation tools
6. **Updated Skills** - Reflect new capabilities in `.agent/skills`

---

## 1. Dialog-Flow Query Input

### Current State
[QueryInput.tsx](file:///c:/Users/35845/Desktop/DIGICISU/projectcarf/carf-cockpit/src/components/carf/QueryInput.tsx) - Simple textarea with suggested queries.

### Proposed Changes

#### [MODIFY] ConversationalQueryFlow.tsx
Replace `QueryInput` with conversational dialog flow:

```
┌─────────────────────────────────────────────┐
│ 🤖 What would you like to analyze?          │
│ ─────────────────────────────────────────── │
│ ┌─────────────────────────────────────────┐ │
│ │ User types: "Why did costs increase?"  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ 🤖 I'll analyze that. First, let me        │
│    understand the context:                  │
│                                             │
│ ┌───────────────┐ ┌───────────────┐        │
│ │ 📊 Use loaded │ │ 📁 Upload new │        │
│ │    scenario   │ │    dataset    │        │
│ └───────────────┘ └───────────────┘        │
│                                             │
│ 🤖 Which variables should I focus on?      │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│ │ Revenue  │ │ Costs    │ │ Region   │     │
│ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────┘
```

**Key Features:**
- Multi-turn dialog before analysis
- Context gathering (dataset, variables, hypothesis)
- Clarifying questions for ambiguous queries
- Step-by-step refinement

---

## 2. LLM-Powered Guidance Chat

### Current State
[FloatingChatTab.tsx](file:///c:/Users/35845/Desktop/DIGICISU/projectcarf/carf-cockpit/src/components/carf/FloatingChatTab.tsx) - Basic message display, no LLM intelligence.

### Proposed Enhancement

#### [MODIFY] IntelligentChatTab.tsx
Transform into multi-purpose assistant:

| Intent | Behavior |
|--------|----------|
| **Platform Help** | "How do I upload data?" → Guide to DataOnboardingWizard |
| **Tutorials** | "Show me how causal analysis works" → Launch walkthrough track |
| **Documentation** | "What is Cynefin?" → Inline explanation with links |
| **Result Interpretation** | "What does 0.42 effect size mean?" → Contextual explanation |
| **Improvement Suggestions** | "How can I improve this analysis?" → Data quality, confounders |

### 2.1 Slash Commands

| Command | Action |
|---------|--------|
| `/question` | Socratic mode - AI asks probing questions to improve analysis |
| `/query` | Execute analysis query and return structured answer |
| `/analysis` | Display snapshot of last analysis with key metrics |
| `/history` | Open analysis history sidebar |
| `/help` | Show available commands and platform guide |

**Implementation:**
```typescript
const SLASH_COMMANDS: Record<string, SlashCommand> = {
  '/question': {
    description: 'Improve your analysis through guided questions',
    handler: startSocraticMode,
  },
  '/query': {
    description: 'Run analysis on your question',
    handler: executeQuery,
  },
  '/analysis': {
    description: 'View last analysis snapshot',
    handler: showAnalysisSnapshot,
  },
  '/history': {
    description: 'Browse past analyses',
    handler: openHistoryPanel,
  },
};
```

### 2.2 Socratic Questioning Mode (`/question`) with UI Highlighting

When user types `/question`, the system uses Socratic method to:

1. **Data Onboarding** - Step-by-step questions for uploading and understanding data
2. **Context Specification** - Gather domain knowledge and use case details
3. **Quantify Uncertainty** - "Your confidence is 72%. What additional data would increase certainty?"
4. **Probe Complexity** - "I see 3 confounders identified. Are there industry-specific factors not captured?"
5. **Challenge Assumptions** - "The causal direction assumes X→Y. Could Y→X also be plausible?"
6. **Suggest Improvements** - "Adding 50 more samples could reduce epistemic uncertainty by ~8%"

#### UI Component Highlighting During Questioning

> [!IMPORTANT]
> As the system asks questions, relevant UI components are **highlighted** to guide user attention and provide "hand-holding" in chat format.

**Example Flow:**

```
┌─────────────────────────────────────────────────┐
│ 🤔 Socratic Mode (Step 1/5)                     │
│ ─────────────────────────────────────────────── │
│                                                 │
│ 💬 Let's set up your analysis step-by-step.     │
│                                                 │
│ Step 1: Upload Your Data                       │
│ What data would you like to analyze?           │
│                                                 │
└─────────────────────────────────────────────────┘
        ↓ UI highlights Dataset Upload area
┌─────────────────────────────────────────────────┐
│ 📁 Dataset Upload  ⚡ PULSING GLOW              │
│ ┌──────────────────────────────────────────┐   │
│ │ Drop CSV here or click to browse         │   │
│ └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

[User uploads data]

┌─────────────────────────────────────────────────┐
│ 🤔 Socratic Mode (Step 2/5)                     │
│ ─────────────────────────────────────────────── │
│                                                 │
│ ✅ Great! I see 500 rows with 12 variables.     │
│                                                 │
│ Step 2: Define Your Question                   │
│ What relationship are you trying to discover?  │
│                                                 │
└─────────────────────────────────────────────────┘
        ↓ UI highlights Query Input
┌─────────────────────────────────────────────────┐
│ Query Input  ⚡ PULSING GLOW                     │
│ ┌──────────────────────────────────────────┐   │
│ │ e.g., "Does X cause Y?"                  │   │
│ └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

[User types query]

┌─────────────────────────────────────────────────┐
│ 🤔 Socratic Mode (Step 3/5)                     │
│ ─────────────────────────────────────────────── │
│                                                 │
│ Step 3: Specify Known Confounders              │
│ Are there variables that might confound this   │
│ relationship? (e.g., seasonality, market        │
│ conditions)                                     │
│                                                 │
│ ┌──────────────────────────────────────────┐   │
│ │ Type confounders or click "Auto-detect"  │   │
│ └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
        ↓ UI highlights Causal DAG panel
┌─────────────────────────────────────────────────┐
│ Causal DAG  ⚡ PULSING GLOW                      │
│ Click nodes to mark as confounders...          │
└─────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
interface QuestioningStep {
  step: number;
  totalSteps: number;
  question: string;
  highlightComponent: 'dataset-upload' | 'query-input' | 'causal-dag' | 
                      'bayesian-panel' | 'scenario-selector';
  helperText?: string;
  suggestedActions?: string[];
}

const QUESTIONING_FLOW: QuestioningStep[] = [
  {
    step: 1,
    totalSteps: 5,
    question: "What data would you like to analyze?",
    highlightComponent: 'dataset-upload',
    helperText: "Upload a CSV file or select an existing scenario",
    suggestedActions: ["Upload CSV", "Browse scenarios"]
  },
  {
    step: 2,
    totalSteps: 5,
    question: "What relationship are you trying to discover?",
    highlightComponent: 'query-input',
    helperText: "Examples: 'Does X cause Y?', 'What drives metric Z?'",
  },
  {
    step: 3,
    totalSteps: 5,
    question: "Are there known confounding variables?",
    highlightComponent: 'causal-dag',
    helperText: "Variables that affect both treatment and outcome",
    suggestedActions: ["Auto-detect", "Manually specify", "Skip"]
  },
  // ... more steps
];
```

**CSS for Highlighting:**
```css
.component-highlighted {
  animation: pulse-glow 2s ease-in-out infinite;
  border: 2px solid var(--accent-primary);
  box-shadow: 0 0 20px rgba(var(--accent-primary-rgb), 0.4);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 20px rgba(var(--accent-primary-rgb), 0.4); }
  50% { box-shadow: 0 0 30px rgba(var(--accent-primary-rgb), 0.8); }
}
```

---

## 2.3 Analysis History

#### [NEW] AnalysisHistoryPanel.tsx

**Current Problem:** Users have no way to view past analyses.

**Solution:** Persist analysis sessions with searchable history:

```
┌──────────────────────────────────────────────────┐
│ 📚 Analysis History                    [🔍 Filter]│
├──────────────────────────────────────────────────┤
│                                                   │
│ ┌─────────────────────────────────────────────┐  │
│ │ 🕐 Today, 14:32                              │  │
│ │ "What drives Scope 3 emissions?"             │  │
│ │ Domain: Complicated | Confidence: 87%        │  │
│ │ Effect: -0.42 | Refutations: 4/5 ✓          │  │
│ │ [View] [Compare] [Rerun]                    │  │
│ └─────────────────────────────────────────────┘  │
│                                                   │
│ ┌─────────────────────────────────────────────┐  │
│ │ 🕐 Yesterday, 09:15                          │  │
│ │ "Does discount reduce churn?"                │  │
│ │ Domain: Complicated | Confidence: 91%        │  │
│ │ Effect: 0.18 | Refutations: 5/5 ✓           │  │
│ │ [View] [Compare] [Rerun]                    │  │
│ └─────────────────────────────────────────────┘  │
│                                                   │
│ [Load More...]                                   │
└──────────────────────────────────────────────────┘
```

**Features:**
| Feature | Description |
|---------|-------------|
| **Persistence** | Store in localStorage (demo) or API (production) |
| **Search** | Filter by query text, domain, date |
| **Compare** | Side-by-side comparison of two analyses |
| **Rerun** | Re-execute with same parameters |
| **Export** | Download as JSON for audit trail |

**Data Schema:**
```typescript
interface AnalysisSession {
  id: string;
  timestamp: Date;
  query: string;
  scenarioId?: string;
  domain: CynefinDomain;
  confidence: number;
  result: QueryResponse;
  duration: number;  // ms
  tags?: string[];
}

// Storage
const useAnalysisHistory = () => {
  const [history, setHistory] = useState<AnalysisSession[]>([]);
  
  const saveAnalysis = (session: AnalysisSession) => {
    const updated = [session, ...history].slice(0, 100); // Keep last 100
    localStorage.setItem('carf-history', JSON.stringify(updated));
    setHistory(updated);
  };
  
  return { history, saveAnalysis };
};
```

---

## 3. Component Explainability

### 3.1 CynefinRouter Explainability

#### [MODIFY] CynefinRouter.tsx
Add "Why this classification?" section:

```typescript
interface CynefinExplanation {
  domain: CynefinDomain;
  keyIndicators: string[];     // ["High variance in query terms", "Multiple causal hypotheses"]
  alternativeDomains: {
    domain: CynefinDomain;
    confidence: number;
    reason: string;           // "Why NOT this domain"
  }[];
  decisionPath: string;       // Human-readable classification rationale
}
```

**UI Addition:**
```
┌─────────────────────────────────────┐
│ Domain: Complicated (87%)           │
│ ─────────────────────────────────── │
│ 📖 Why this classification?         │
│                                     │
│ Key indicators:                     │
│ • Multiple measurable variables     │
│ • Clear cause-effect hypothesis     │
│ • Quantitative data available       │
│                                     │
│ Why not Complex?                    │
│ • No emergent patterns detected     │
│ • Low system interdependency        │
└─────────────────────────────────────┘
```

### 3.2 Bayesian Panel Explainability

#### [MODIFY] BayesianPanel.tsx
Add uncertainty interpretation:

```
┌─────────────────────────────────────┐
│ Uncertainty Breakdown               │
│ ─────────────────────────────────── │
│ 📊 Why this matters:                │
│                                     │
│ Epistemic (19%): Model doesn't have │
│ enough data. Collecting 30 more     │
│ supplier records would reduce this. │
│                                     │
│ Aleatoric (12%): Natural randomness │
│ in supplier behavior. Cannot reduce │
│ with more data.                     │
│                                     │
│ 💡 Recommended Probe:               │
│ "Survey manufacturing suppliers on  │
│  sustainability practices"          │
└─────────────────────────────────────┘
```

### 3.3 Causal DAG Explainability

#### [MODIFY] CausalDAG.tsx
Add node/edge click explanations:

```typescript
interface DAGNodeExplanation {
  role: 'treatment' | 'outcome' | 'confounder' | 'mediator';
  whyIncluded: string;        // "Domain knowledge suggests this causes..."
  dataEvidence: string;       // "Correlation: 0.67, p<0.001"
  canIntervene: boolean;      // User actionable?
  whatIf: string;             // "Changing this by 10% would..."
}
```

---

## 4. Developer View / Live Cockpit

### Current State
**No Developer View exists.** DashboardLayout has single 3-6-3 grid.

### Proposed Architecture

#### [NEW] DeveloperView.tsx
AI Act-compliant transparency cockpit:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔧 DEVELOPER VIEW - Live Cockpit                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────── ARCHITECTURE LAYERS ───────────────────┐          │
│ │                                                        │          │
│ │  [Layer 1: Router]  →  [Layer 2: Mesh]  →  [Layer 3]  │          │
│ │       ↓                    ↓                  ↓        │          │
│ │  Classification      Domain Agent       Reasoning     │          │
│ │  "Complicated"       "Causal Analyst"   "DoWhy/EconML"│          │
│ │                                                        │          │
│ │  [Layer 4: Guardian]  →  [HumanLayer]                 │          │
│ │       ↓                       ↓                        │          │
│ │  Policy: PASS            Not Required                  │          │
│ │                                                        │          │
│ └────────────────────────────────────────────────────────┘          │
│                                                                     │
│ ┌─────────────── EXECUTION TRACE ────────────────────────┐          │
│ │ ⏱️ 0.0s  Router received query                         │          │
│ │ ⏱️ 0.2s  LLM classification: Complicated (0.87)        │          │
│ │ ⏱️ 0.3s  Routed to: causal_analyst_node               │          │
│ │ ⏱️ 0.8s  DAG discovered: 5 nodes, 6 edges             │          │
│ │ ⏱️ 2.1s  DoWhy estimation: effect=-0.42               │          │
│ │ ⏱️ 2.4s  Refutation tests: 4/5 passed                 │          │
│ │ ⏱️ 2.5s  Guardian evaluation: APPROVED                │          │
│ │ ✅ 2.6s  Response generated                            │          │
│ └────────────────────────────────────────────────────────┘          │
│                                                                     │
│ ┌─── AUDIT LOG ───┐  ┌─── STATE INSPECTOR ───┐                     │
│ │ [Filter ▼] [📥] │  │ EpistemicState        │                     │
│ │ 14:32:01 INFO   │  │ ├─ cynefin_domain     │                     │
│ │ 14:32:02 DEBUG  │  │ ├─ domain_confidence  │                     │
│ │ 14:32:03 INFO   │  │ ├─ causal_evidence    │                     │
│ └─────────────────┘  └───────────────────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Panels:**
| Panel | Purpose | AI Act Compliance |
|-------|---------|-------------------|
| Architecture Flow | Visualize 4-layer stack | Art. 13 - Transparency |
| Execution Trace | Time-stamped step log | Art. 12 - Record-keeping |
| State Inspector | EpistemicState browser | Art. 14 - Human oversight |
| Audit Log | Filterable decision log | Art. 12 - Traceability |

---

## 5. Data Walkthroughs & Generation

### [NEW] GuidedDataWalkthrough.tsx
Step-by-step "Input Your Data" experience:

```
Step 1/5: Define Your Question
┌─────────────────────────────────────┐
│ What business question do you have? │
│ ┌─────────────────────────────────┐ │
│ │ "Does X cause Y?"               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 💡 Examples:                        │
│ • Does training reduce turnover?   │
│ • Do discounts increase revenue?   │
└─────────────────────────────────────┘

Step 2/5: Upload Your Data
Step 3/5: Define Variables
Step 4/5: Specify Domain Knowledge
Step 5/5: Review & Analyze
```

### [NEW] DataGenerationWizard.tsx
Generate test data with parameters:

| Parameter | Description |
|-----------|-------------|
| Dataset Size | 100 - 10,000 rows |
| Variables | Select treatment, outcome, confounders |
| Effect Size | True causal effect to simulate |
| Noise Level | Aleatoric uncertainty |
| Confounding Strength | How much confounders bias estimates |

---

## 6. Authentic Demo Data

### Current State
[mockData.ts](file:///c:/Users/35845/Desktop/DIGICISU/projectcarf/carf-cockpit/src/services/mockData.ts) - 5 scenarios with hardcoded values.

### Proposed Enhancements

#### [MODIFY] demo/payloads/*.json
Flesh out each scenario with:

| Scenario | Rows | Variables | Authentic Source |
|----------|------|-----------|------------------|
| `scope3_attribution` | 247 | 8 | CDP-style supplier emissions |
| `causal_discount_churn` | 1,000 | 12 | Telecom churn simulation |
| `grid_stability` | 500 | 15 | Power grid frequency data |
| `marketing_budget` | 365 | 10 | Marketing mix modeling |
| `risk_exposure` | 200 | 20 | Financial risk factors |

#### [NEW] demo/generators/
Python scripts to regenerate demo data:

```python
# generate_scope3_data.py
def generate_scope3_dataset(
    n_suppliers: int = 247,
    treatment_effect: float = -0.42,
    confounding_strength: float = 0.3,
    seed: int = 42
) -> pd.DataFrame:
    """Generate realistic Scope 3 emissions data."""
```

---

## 7. Updated Agent Skills

### [MODIFY] .agent/skills/

#### New Skills Required

| Skill | Purpose |
|-------|---------|
| `conversational_query` | Handle multi-turn dialog flow |
| `explainability_generator` | Generate why-explanations for panels |
| `developer_view_tracer` | Format execution traces for Developer View |
| `data_generator` | Generate test datasets with parameters |

#### Updated Skills

| Skill | Update |
|-------|--------|
| `component_generator` | Add explainability section template |
| `query_processor` | Add dialog context handling |
| `documentation_updater` | Include Developer View documentation |

---

## 8. View Mode Architecture

### [MODIFY] DashboardLayout.tsx

```typescript
type ViewMode = 'analyst' | 'developer' | 'executive';

// Tab switching in header
<TabGroup value={viewMode} onChange={setViewMode}>
  <Tab value="analyst">Analyst View</Tab>
  <Tab value="developer">Developer View</Tab>
  <Tab value="executive">Executive View</Tab>
</TabGroup>

// Conditional rendering
{viewMode === 'developer' && <DeveloperView {...props} />}
{viewMode === 'analyst' && <AnalystView {...props} />}
{viewMode === 'executive' && <ExecutiveView {...props} />}
```

---

## 9. Blueprint-Derived Enhancements

Based on the CARF Strategic Blueprint ("Third Wave of Enterprise AI"), the following advanced features should be incorporated:

### 9.1 Counterfactual "Do" Slider

**From Blueprint:** "Each node has a slider. When a user drags the 'Interest Rate' slider, the entire graph animates to show the counterfactual propagation."

#### [MODIFY] CausalDAG.tsx
Add intervention sliders to DAG nodes:

```typescript
interface NodeWithIntervention extends DAGNode {
  interventionSlider?: {
    min: number;
    max: number;
    unit: string;
    current: number;
  };
  onIntervene: (newValue: number) => void;
}
```

**Behavior:** As user drags slider, call backend `/what-if` endpoint → animate downstream nodes with updated effect sizes.

### 9.2 Value-Suppressing Uncertainty Palette

**From Blueprint:** "Use color schemes that 'grey out' or desaturate data points where confidence is low."

**Implementation:**
```css
/* Low confidence = desaturated */
.metric-card[data-confidence="low"] {
  opacity: 0.6;
  filter: grayscale(30%);
  border-left: 3px solid var(--confidence-low);
}

.metric-card[data-confidence="high"] {
  opacity: 1;
  filter: none;
  border-left: 3px solid var(--confidence-high);
}
```

Apply to: All numeric displays, DAG edges, recommendation cards.

### 9.3 Fan Charts for Bayesian Predictions

**From Blueprint:** "For time-series predictions, use Fan Charts that show widening bands of probability over time."

#### [MODIFY] BayesianPanel.tsx
Add Recharts-based fan chart:

```
      │     ╱────────╲     90% CI
Prob  │   ╱   ╱────╲   ╲   50% CI
      │ ╱   ╱  ───   ╲   ╲  Mean
      │╱   ╱          ╲   ╲
      ├────────────────────────
           Time → Future
```

### 9.4 Semantic Circuit Breaker Display

**From Blueprint:** "If the agent's reasoning trace shifts towards a 'Prohibited Cluster', the circuit breaker trips."

#### [NEW] Developer View → CircuitBreakerPanel.tsx

```
┌─────────────────────────────────────────┐
│ 🔌 Circuit Breaker Status        [SAFE] │
├─────────────────────────────────────────┤
│                                         │
│  Vector Space Monitor:                  │
│  ┌─────────────────────────────┐        │
│  │      ○ Safe Zone            │        │
│  │    ●───────○ Current        │        │
│  │      ⛔ Prohibited          │        │
│  └─────────────────────────────┘        │
│                                         │
│  Distance to boundary: 0.34             │
│  Risk level: LOW                        │
└─────────────────────────────────────────┘
```

### 9.5 Active Inference Metrics (EFE Display)

**From Blueprint:** "Expected Free Energy $G(\pi)$ = Pragmatic Value + Epistemic Value"

#### [NEW] Developer View → ActiveInferencePanel.tsx

| Metric | Description | Display |
|--------|-------------|---------|
| **EFE Score** | Lower = better policy | Gauge: 0-1 |
| **Pragmatic Value** | Goal alignment | Progress bar |
| **Epistemic Value** | Information gain | Progress bar |
| **Belief State Entropy** | Agent confusion | Heat indicator |

### 9.6 Audit Tape Session Replay

**From Blueprint:** "Audit Tape Session Replay" in Enterprise tier.

#### [NEW] Developer View → SessionReplayPanel.tsx

- Record all state transitions as timeline
- Scrub through execution with playhead
- Jump to any moment, inspect EpistemicState
- Export as JSON for compliance audit

### 9.7 Epistemic vs Aleatoric Gauge

**From Blueprint:** "A specialized widget that separates 'Model Uncertainty' from 'Data Uncertainty'."

#### [MODIFY] Multiple panels, add UncertaintyGauge component:

```
┌────────────────────────────────┐
│ Uncertainty Breakdown          │
│                                │
│ Epistemic (Can reduce):  ████░░░ 42%
│ ↳ Add 50 more samples to reduce by ~15%
│                                │
│ Aleatoric (Cannot reduce): ██░░░░░ 18%
│ ↳ Natural variance in system
│                                │
│ Total Uncertainty:       █████░ 60%
└────────────────────────────────┘
```

---

## 10. UIX Enhancements (2026-01-19)

> [!IMPORTANT]
> Additional UIX improvements to enhance decision-support, explainability, and "glassbox" transparency.

### 10.1 Right-Click Explainability & Visual Affordances

**Problem:** UI elements (DAG nodes, metrics, refutation tests) lack obvious interaction hints. Right-click context menus don't provide explanations.

**Solutions:**
- Add hover effects (pulsing borders, subtle glow) to all interactive elements
- Show ℹ️ icons on hover indicating clickable items
- Implement right-click context menus with "Explain this...", "View distribution", "Show causal paths"
- Add dismissible onboarding tooltip: "💡 Right-click any element for details"

### 10.2 Refutation Test Drill-Down

**Problem:** Refutation tests show only pass/fail + p-values without explanatory context.

**Solutions:**
- Expandable cards for each test with plain-language explanations
- "What this tests" + "Why it passed/failed" + "Recommendation" sections
- Visual comparison (original vs. placebo effect)
- Aggregate "Causal Confidence" indicator combining all test results

### 10.3 Scenario Simulation Arena

**Purpose:** Enable what-if analysis with side-by-side scenario comparisons.

> [!NOTE]
> Models and analysis should **dynamically update** when scenarios or context change. This is not a static comparison—the causal models re-run in the background when intervention parameters are adjusted.

**Features:**
| Feature | Description |
|---------|-------------|
| Multi-Scenario Config | Create 2-5 alternative intervention strategies |
| Intervention Sliders | Adjust treatment variables with real-time model updates |
| Parallel Simulation | Run all scenarios simultaneously for comparison |
| Benchmark Metrics Table | Compare KPIs across scenarios with 🏆 highlights |
| Outcome Trajectories | Time-series visualization of projected outcomes |
| Sensitivity Analysis | See how outcomes change across parameter ranges |
| Save & Share | Persist scenarios for team review |

**API Requirements:**
```typescript
// New endpoints needed
POST /simulations/run          // Run multiple scenario simulations
POST /simulations/compare      // Get comparison metrics
GET  /simulations/{id}/status  // Check background simulation status
WS   /simulations/stream       // WebSocket for real-time updates

// Types
interface ScenarioConfig {
  id: string;
  name: string;
  interventions: Intervention[];
  baselineDatasetId: string;
}

interface SimulationResult {
  scenarioId: string;
  effectEstimate: number;
  confidence: number;
  metrics: Record<string, number>;
  updatedAt: string;  // Tracks when model was last re-run
}
```

### 10.4 Executive View Redesign

**Current Gap:** Executive view lacks KPI-focused visualizations and decision context.

**Proposed Layout:**
1. **KPI Cards** - Confidence, Risk Level, Decision Status, Timeline
2. **Executive Summary** - Plain-language 3-paragraph summary of findings
3. **Decision Impact Cards** - Upside/Downside comparison with business context
4. **Visual Gauges** - Causal confidence, policy compliance, data quality

### 10.5 Developer View Transparency

**Current Gap:** Developer view is too similar to Analyst view. Should expose system internals.

**New Panels:**
1. **Agentic Workflow Pipeline** - Visual flow of Router → Agent → Guardian steps
2. **Step-by-Step Execution Log** - Timestamped detailed log with drill-down
3. **System Backlogs** - Pending/completed/failed task queues
4. **Feedback Console** - Allow users to provide feedback on model accuracy
5. **JSON State Inspector** - Deep EpistemicState browser with export

### 10.6 Semantic Data Map

**Purpose:** Provide intuitive visualization of user data relationships and quality.

**Components:**
1. **Variable Relationship Graph** - Network view of data correlations
2. **Data Quality Heatmap** - Completeness, variance, outliers per variable
3. **Domain Context Panel** - Applied domain knowledge and suggested variables

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] ConversationalQueryFlow component
- [ ] IntelligentChatTab with LLM integration
- [ ] View mode tabs in header

### Week 2: Explainability
- [ ] CynefinRouter explainability panel
- [ ] BayesianPanel uncertainty breakdown
- [ ] CausalDAG node/edge explanations

### Week 3: Developer View
- [ ] Architecture flow visualization
- [ ] Enhanced execution trace
- [ ] State inspector panel
- [ ] Audit log with filtering

### Week 4: Data & Polish
- [ ] Authentic demo data generation
- [ ] GuidedDataWalkthrough
- [ ] DataGenerationWizard
- [ ] Updated skills documentation

### Week 5: UIX Enhancements
- [ ] Right-click context menus and visual affordances
- [ ] Refutation test drill-down with explanations
- [ ] Scenario Simulation Arena (multi-scenario what-if)
- [ ] Executive View KPI dashboard redesign
- [ ] Developer View transparency panels
- [ ] Semantic data map visualization

---

## Verification Plan

### Browser Testing
1. Submit query → verify dialog flow activates
2. Click chat → ask "How do I interpret this?" → verify LLM response
3. Click CynefinRouter → verify "Why?" explanation appears
4. Switch to Developer View → verify architecture visualization
5. Generate test data → verify complete analysis flow

### AI Act Compliance Checklist
- [ ] Art. 12: Record-keeping (Execution trace persisted)
- [ ] Art. 13: Transparency (All decisions explained)
- [ ] Art. 14: Human oversight (Guardian/HumanLayer visible)

---

## Appendix A: Backend/Frontend Alignment Matrix

### Existing API Endpoints (Ready to Use)

| Endpoint | Purpose | Phase 7 Feature |
|----------|---------|-----------------|
| `POST /query` | Main analysis | `/query` command, dialog flow |
| `GET /scenarios` | Demo scenarios | Scenario selector |
| `GET /datasets` | Dataset list | Data upload flow |
| `POST /datasets` | Create dataset | Data generation |
| `GET /health` | System status | Developer View status |
| `GET /domains` | Cynefin domains | Router explainability |

### API Gaps (Planned for Phase 7)

| Endpoint | Purpose | Priority | Status |
|----------|---------|----------|--------|
| `POST /what-if` | Counterfactual simulation | HIGH | ⚠️ NOT IMPLEMENTED |
| `POST /simulations/run` | Run multi-scenario simulations | HIGH | ⚠️ NOT IMPLEMENTED |
| `POST /simulations/compare` | Get scenario comparison metrics | HIGH | ⚠️ NOT IMPLEMENTED |
| `GET /simulations/{id}/status` | Check background simulation status | HIGH | ⚠️ NOT IMPLEMENTED |
| `WS /simulations/stream` | WebSocket for real-time updates | HIGH | ⚠️ NOT IMPLEMENTED |
| `GET /sessions` | Analysis history list | HIGH | ⚠️ NOT IMPLEMENTED |
| `POST /sessions` | Save analysis session | HIGH | ⚠️ NOT IMPLEMENTED |
| `GET /sessions/{id}` | Retrieve past session | MEDIUM | ⚠️ NOT IMPLEMENTED |
| `POST /generate-dataset` | Create test data | MEDIUM | ⚠️ NOT IMPLEMENTED |
| `GET /audit-log` | Compliance audit trail | LOW | ⚠️ NOT IMPLEMENTED |

### Frontend Types (carf.ts) - Already Aligned ✅

| Type | Backend Equivalent | Status |
|------|-------------------|--------|
| `BayesianBeliefState.epistemicUncertainty` | `BayesianResult.epistemic_uncertainty` | ✅ Aligned |
| `BayesianBeliefState.aleatoricUncertainty` | `BayesianResult.aleatoric_uncertainty` | ✅ Aligned |
| `BayesianBeliefState.recommendedProbe` | `BayesianResult.recommended_probe` | ✅ Aligned |
| `QueryResponse.domainEntropy` | `QueryResponse.domain_entropy` | ✅ Aligned |
| `ReasoningStep` | `ReasoningStep` | ✅ Aligned |

### Types Needed for Phase 7

```typescript
// Analysis History (add to carf.ts)
export interface AnalysisSession {
  id: string;
  timestamp: string;
  query: string;
  scenarioId?: string;
  domain: CynefinDomain;
  confidence: number;
  result: QueryResponse;
  duration: number;
  tags?: string[];
}

// Slash Commands
export type SlashCommand = '/question' | '/query' | '/analysis' | '/history' | '/help';

// Counterfactual Intervention
export interface InterventionRequest {
  nodeId: string;
  newValue: number;
  dag: CausalDAG;
}

// Developer View
export interface ExecutionTraceStep extends ReasoningStep {
  timestamp: string;
  duration_ms: number;
  layer: 'router' | 'mesh' | 'services' | 'guardian';
}
```

---

## Appendix B: Skills Inventory (12 Total)

| Skill | Purpose | Phase |
|-------|---------|-------|
| `test_runner` | Execute tests | Phase 6 |
| `dev_server` | Manage servers | Phase 6 |
| `documentation_updater` | Sync docs | Phase 6 |
| `component_generator` | Create React components | Phase 6 |
| `query_processor` | CARF pipeline | Phase 6 |
| `guardian_policy_check` | OPA policies | Phase 6 |
| `scenario_manager` | Demo scenarios | Phase 6 |
| `causal_analysis` | DoWhy/EconML | Phase 6 |
| `conversational_query` | Slash commands, Socratic mode | **Phase 7** |
| `explainability_generator` | Why explanations | **Phase 7** |
| `developer_view_tracer` | Execution traces | **Phase 7** |
| `data_generator` | Test datasets | **Phase 7** |

---

## Appendix C: MCP / Tooling Recommendations

### Current State
- `.agent/skills/` - 12 skills defined ✅
- `.agent/workflows/` - **MISSING** ⚠️
- MCP server configs - **NOT CONFIGURED** ⚠️

### Recommended Additions

#### 1. Workflow Definitions
Create `.agent/workflows/` with:

| Workflow | Purpose |
|----------|---------|
| `test-and-lint.md` | Run pytest, ruff, mypy, npm build |
| `dev-server.md` | Start FastAPI + Vite dev servers |
| `deploy-demo.md` | Build and deploy to demo environment |
| `generate-scenarios.md` | Regenerate demo data |

#### 2. MCP Server Integration (Recommended)

| MCP Server | Purpose | Priority |
|------------|---------|----------|
| **Memory MCP** | Persist conversation context across sessions | HIGH |
| **Neo4j MCP** | Direct graph queries from agent | MEDIUM |
| **Filesystem MCP** | Safe file access with audit | LOW |

**Memory MCP Config (Planned):**
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-memory"]
    }
  }
}
```

#### 3. Context Management Improvements

| Enhancement | Benefit |
|-------------|---------|
| **Session persistence** | Resume analysis across conversations |
| **Scenario snapshots** | Save/restore demo states |
| **Agent memory layer** | Track decisions across tasks |

#### 4. Architecture Robustness

| Gap | Recommendation |
|-----|----------------|
| No rate limiting | Add FastAPI rate limiter middleware |
| No request validation middleware | Add Pydantic validation at API boundary |
| No health check for dependencies | Extend `/health` to check Neo4j, LLM |
| No graceful degradation | Add fallback when LLM unavailable |

#### 5. Scalability Considerations

| Current | Improvement |
|---------|-------------|
| In-memory dataset store | Add Redis or SQLite backend |
| Synchronous LLM calls | Add async with queue (Celery/RQ) |
| Single-instance | Add load balancer readiness |

---

## Appendix D: Test Coverage Matrix

### Backend Tests (15 files, ~280 tests)

| Module | Test File | Coverage | Status |
|--------|-----------|----------|--------|
| `src/main.py` | `test_api.py` | API endpoints | ✅ |
| `src/services/bayesian.py` | `test_bayesian.py` | Inference | ✅ |
| `src/services/causal.py` | `test_causal.py` | DoWhy/EconML | ✅ |
| `src/workflows/graph.py` | `test_graph.py` | LangGraph | ✅ |
| `src/workflows/router.py` | `test_router.py` | Cynefin | ✅ |
| `src/services/guardian.py` | `test_guardian.py` | Policies | ✅ |
| `src/services/human_layer.py` | `test_human_layer.py` | Escalation | ✅ |
| `src/services/llm.py` | `test_llm.py` | LLM calls | ✅ |
| `src/core/state.py` | `test_state.py` | EpistemicState | ✅ |
| `src/services/neo4j_service.py` | `test_neo4j_service.py` | Graph DB | ✅ |
| `src/services/opa_service.py` | `test_opa_service.py` | OPA | ✅ |
| `src/services/kafka_audit.py` | `test_kafka_audit.py` | Audit | ✅ |
| `src/services/resiliency.py` | `test_resiliency.py` | Retry | ✅ |
| `src/services/dataset_store.py` | `test_dataset_store.py` | Datasets | ✅ |
| Dashboard utils | `test_dashboard_utils.py` | Streamlit | ✅ |

### Frontend Tests (0 files - NEEDS WORK)

| Component | Test Needed | Priority |
|-----------|-------------|----------|
| `DashboardLayout.tsx` | Integration test | HIGH |
| `QueryInput.tsx` | Unit test (input handling) | HIGH |
| `CausalDAG.tsx` | Snapshot + interaction | HIGH |
| `BayesianPanel.tsx` | Uncertainty display | MEDIUM |
| `CynefinRouter.tsx` | Domain badge rendering | MEDIUM |
| `FloatingChatTab.tsx` | Message handling | MEDIUM |
| `ExecutionTrace.tsx` | Step rendering | LOW |
| `GuardianPanel.tsx` | Policy display | LOW |

**Recommended Test Setup:**
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

### Phase 7 Test Requirements

| Feature | Backend Test | Frontend Test |
|---------|--------------|---------------|
| Slash commands | - | `IntelligentChatTab.test.tsx` |
| Socratic mode | - | `SocraticFlow.test.tsx` |
| Analysis history | `test_sessions.py` (NEW) | `AnalysisHistoryPanel.test.tsx` |
| Developer View | - | `DeveloperView.test.tsx` |
| Counterfactual slider | `test_whatif.py` (NEW) | `CausalDAG.intervention.test.tsx` |

---

## Appendix E: Backend-Frontend Component Alignment

| Backend Schema | Frontend Type | Component | Aligned? |
|----------------|---------------|-----------|----------|
| `QueryResponse` | `QueryResponse` | `DashboardLayout` | ✅ |
| `CausalResult` | `CausalAnalysisResult` | `CausalDAG`, `CausalAnalysisCard` | ✅ |
| `BayesianResult` | `BayesianBeliefState` | `BayesianPanel` | ✅ |
| `GuardianResult` | `GuardianDecision` | `GuardianPanel` | ✅ |
| `ReasoningStep` | `ReasoningStep` | `ExecutionTrace` | ✅ |
| `CynefinDomain` | `CynefinDomain` | `CynefinRouter` | ✅ |
| `ScenarioMetadata` | `ScenarioMetadata` | `DashboardHeader` | ✅ |
| - | `AnalysisSession` (NEW) | `AnalysisHistoryPanel` (NEW) | ⚠️ Planned |
| - | `ExecutionTraceStep` (NEW) | `DeveloperView` (NEW) | ⚠️ Planned |
