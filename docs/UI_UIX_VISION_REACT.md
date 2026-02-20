# CARF Epistemic Cockpit — UI/UX Component Documentation v2

A comprehensive technical breakdown of the CARF (Causal Analysis and Reasoning Framework) UI/UX system, integrating the **Two-Speed Cognitive Model** with component architecture and user story mapping.

---

## Table of Contents

1. [Core Interaction Philosophy](#core-interaction-philosophy)
2. [Architecture Overview](#architecture-overview)
3. [User Story Mapping](#user-story-mapping)
4. [Core Components](#core-components)
   - [DashboardHeader](#dashboardheader)
   - [QueryInput](#queryinput)
   - [CynefinRouter](#cynefinrouter)
   - [CausalDAG](#causaldag)
   - [BayesianPanel](#bayesianpanel)
   - [CausalAnalysisCard](#causalanalysiscard)
   - [GuardianPanel](#guardianpanel)
   - [ExecutionTrace](#executiontrace)
5. [View Mode Components](#view-mode-components)
   - [DeveloperDebugView](#developerdebugview)
   - [ExecutiveSummaryView](#executivesummaryview)
6. [Control Components](#control-components)
   - [SimulationControls](#simulationcontrols)
7. [HumanLayer Integration](#humanlayer-integration)
8. [UX Standards & Design Principles](#ux-standards--design-principles)
9. [Data Flow](#data-flow)
10. [Design System Tokens](#design-system-tokens)
11. [Animation Patterns](#animation-patterns)
12. [Implementation Status](#implementation-status)

---

## Core Interaction Philosophy

### Two-Speed Cognitive Model

The CARF UI follows a **dual-channel model** that respects different cognitive modes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TWO-SPEED COGNITIVE MODEL                            │
├─────────────────────────────────┬───────────────────────────────────────────┤
│     🚀 FAST THINKING            │      🔬 SLOW THINKING                     │
│     (Operational Channel)       │      (Analytical Cockpit)                 │
├─────────────────────────────────┼───────────────────────────────────────────┤
│ Tool: HumanLayer                │ Tool: React Epistemic Cockpit             │
│       (Slack/Teams/Email)       │       (Web Dashboard)                     │
├─────────────────────────────────┼───────────────────────────────────────────┤
│ Goal: Quick binary decisions    │ Goal: Deep audit, causal inspection,      │
│       (Approve/Reject)          │       system debugging                    │
├─────────────────────────────────┼───────────────────────────────────────────┤
│ Principle: "Don't make me       │ Principle: "Show your work" —             │
│ think" — no dashboard needed    │ transparency of uncertainty               │
│ for routine approvals           │ and causal logic                          │
├─────────────────────────────────┼───────────────────────────────────────────┤
│ Latency: Push-based             │ Latency: Pull-based                       │
│ (system notifies user)          │ (user logs in to investigate)             │
├─────────────────────────────────┼───────────────────────────────────────────┤
│ Components:                     │ Components:                               │
│ • 3-Point Context Card          │ • Causal Graph Visualization              │
│ • Approve/Reject/Modify buttons │ • Bayesian Belief States                  │
│ • Audit deep link               │ • Query Interface                         │
│                                 │ • Execution Trace                         │
│                                 │ • Audit Trail                             │
└─────────────────────────────────┴───────────────────────────────────────────┘
```

### Channel Selection Logic

| Scenario | Channel | Rationale |
|----------|---------|-----------|
| Routine approval within policy | Fast (HumanLayer) | Minimal cognitive load |
| Policy threshold exceeded | Fast → Slow link | Quick action + audit option |
| Causal reasoning verification | Slow (Cockpit) | Requires deep inspection |
| Incident investigation | Slow (Cockpit) | Full audit trail needed |
| Historical analysis comparison | Slow (Cockpit) | Exploratory workflow |

---

## Architecture Overview

### System Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Index.tsx (Page)                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         DashboardHeader                                 │ │
│  │  Logo | Scenario Selector | Session ID | Theme Toggle | User Avatar    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │           View Mode Tabs (End-User | Developer | Executive)            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────┐  ┌────────────────────────┐  ┌──────────────────────────┐   │
│  │ LEFT COL   │  │     CENTER COLUMN       │  │     RIGHT COLUMN        │   │
│  │ (3 cols)   │  │       (6 cols)          │  │       (3 cols)          │   │
│  │            │  │                         │  │                         │   │
│  │ QueryInput │  │ CausalDAG               │  │ Progress Steps          │   │
│  │ Simulation │  │ (Interactive Graph)     │  │ (Step-by-step reveal)   │   │
│  │ Controls   │  │                         │  │                         │   │
│  │            │  │ CausalAnalysisCard      │  │ ExecutionTrace          │   │
│  │ Cynefin    │  │ (Effect + Refutations)  │  │ (Timeline + Receipt)    │   │
│  │ Router     │  │                         │  │                         │   │
│  │            │  │ GuardianPanel           │  │                         │   │
│  │ Bayesian   │  │ (Policy + Approval)     │  │                         │   │
│  │ Panel      │  │                         │  │                         │   │
│  └────────────┘  └────────────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Visibility Flow (Step-by-Step Reveal)

Components are revealed sequentially based on `currentStep`, creating a narrative flow:

| Step | Components Revealed | Delay | User Experience |
|------|---------------------|-------|-----------------|
| 0    | QueryInput (always visible) | — | User enters question |
| 1    | CynefinRouter | 400ms | "What kind of problem is this?" |
| 2    | CausalDAG | 600ms | "What are the causal relationships?" |
| 3    | BayesianPanel, CausalAnalysisCard | 1200ms | "What does the data tell us?" |
| 4    | GuardianPanel | 800ms | "Should we act on this?" |
| 5    | ExecutionTrace, Debug/Executive Views | 500ms | "Full audit trail available" |

**Total animation time:** ~3.5 seconds for full reveal

---

## User Story Mapping

### Story 1: Operations Manager — Quick Approval Flow

> "As an operations manager, I need to quickly approve/reject high-value transactions"

**Maps to:** HumanLayer Fast-Thinking Channel + GuardianPanel

```
┌─────────────────────────────────────────────────────────────────────┐
│                    3-POINT CONTEXT NOTIFICATION                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📌 WHAT: Increase Q3 Marketing Budget by $2.5M                    │
│                                                                     │
│  🔍 WHY:  Causal model shows +18.5M revenue impact                 │
│           Confidence: 87% (High)                                    │
│                                                                     │
│  ⚠️ RISK: Amount exceeds standard threshold ($500K)                │
│           Policy: budget_threshold v2.1                             │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  [✅ Approve]  [❌ Reject]  [✏️ Modify]  [🔗 Audit]                │
└─────────────────────────────────────────────────────────────────────┘
```

**Component mapping:**
- `GuardianPanel.proposedAction` → WHAT section
- `CausalAnalysisCard.effect` + `BayesianPanel.confidenceLevel` → WHY section
- `GuardianPanel.policies[failed]` → RISK section
- Action buttons → HumanLayer integration

---

### Story 2: Data Scientist — Reasoning Chain Verification

> "As a data scientist, I need to verify causal reasoning chains and inspect uncertainty"

**Maps to:** Epistemic Cockpit — Query Interface + BayesianPanel + ExecutionTrace

**Workflow:**
1. Submit query via `QueryInput`
2. Inspect `CynefinRouter` for problem classification
3. Explore `CausalDAG` for relationship structure
4. Verify `BayesianPanel` for uncertainty decomposition
5. Review `ExecutionTrace` for reasoning steps

**Key UI requirement:** Full transparency of uncertainty and confidence intervals

---

### Story 3: Analyst — Causal Relationship Exploration

> "As an analyst, I need to explore causal relationships in historical data"

**Maps to:** Epistemic Cockpit — CausalDAG + CausalAnalysisCard

**Component features used:**
- Interactive node selection in `CausalDAG`
- Markov blanket highlighting (parents, children, co-parents)
- Edge annotations with effect sizes
- Refutation test results in `CausalAnalysisCard`

---

### Story 4: Auditor — Decision Traceability

> "As an auditor, I need to trace decision history and verify compliance"

**Maps to:** Epistemic Cockpit — ExecutionTrace + Audit Trail

**Component features used:**
- `ExecutionTrace.receiptId` for unique decision identifier
- Step-by-step inputs/outputs in collapsible panels
- JSON export for evidence preservation
- LangSmith deep link for external audit

---

### Story 5: Decision-Maker — Policy Override Investigation

> "As a decision-maker, I need to understand why an action was blocked and resolve it"

**Maps to:** HumanLayer → Cockpit Audit Link → GuardianPanel

**Flow:**
```
[HumanLayer Notification] 
    → User clicks "Audit" 
    → Deep link to Cockpit 
    → GuardianPanel.policies shows violation details
    → User reviews CausalDAG + BayesianPanel for context
    → Returns to HumanLayer for Approve/Reject/Modify
```

---

### Story 6: Researcher — Historical Comparison

> "As a researcher, I need to compare similar causal analyses"

**Maps to:** Epistemic Cockpit — Recent Analyses Panel (DeveloperDebugView)

**Component features used:**
- Session-based scenario loading
- Historical analysis lookup
- Similar analysis discovery by treatment/outcome

---

## Core Components

### DashboardHeader

**Location:** `src/components/carf/DashboardHeader.tsx`

**Purpose:** Global navigation bar with branding, scenario selection, session tracking, and user controls.

#### Props Interface

```typescript
interface DashboardHeaderProps {
  selectedScenario: string;        // Current scenario ID
  onScenarioChange: (id: string) => void;  // Callback when scenario changes
  sessionId: string;               // Unique session identifier
}
```

#### Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [⬡] CARF Epistemic Cockpit v1.0.0 | [Scenario ▼] [●Session] | ☀🔔⚙👤│
└─────────────────────────────────────────────────────────────────────┘
```

#### Key Features

| Feature | Implementation | User Story |
|---------|----------------|------------|
| **Logo** | Gradient hexagon icon (`Hexagon` from lucide-react) | Branding |
| **Theme Toggle** | Local state with `classList.toggle('dark')` | Accessibility |
| **Scenario Selector** | Radix Select with emoji icons + domain badges | Story 3, 6 |
| **Session Indicator** | Pulsing green dot + truncated session ID | Story 4 |
| **Notification Bell** | Ghost button with destructive dot indicator | Story 1 |

#### Styling Tokens

- `glass-strong` — Frosted glass background effect
- `text-gradient` — Primary gradient text for title
- `bg-gradient-to-br from-primary to-accent` — Logo/avatar backgrounds

---

### QueryInput

**Location:** `src/components/carf/QueryInput.tsx`

**Purpose:** Primary user input for submitting analysis queries. Supports the "Pull-based" slow-thinking channel.

#### Props Interface

```typescript
interface QueryInputProps {
  onSubmit: (query: string) => void;  // Callback with query text
  suggestedQueries: string[];          // Array of preset suggestions
  isProcessing: boolean;               // Disables input during analysis
}
```

#### Structure

```
┌─────────────────────────────────────────────────┐
│ [Textarea: "Ask a question about your data..."] │
│                                    [📎] [Send] │
├─────────────────────────────────────────────────┤
│ SUGGESTED QUERIES                               │
│ [Why did churn rise?] [Revenue impact?] [...]  │
└─────────────────────────────────────────────────┘
```

#### Key Features

| Feature | Implementation | User Story |
|---------|----------------|------------|
| **Submit on Enter** | `handleKeyDown` checks `!e.shiftKey` | Story 2 |
| **Loading State** | Button shows `Sparkles` icon + "Analyzing..." | UX feedback |
| **Clickable Suggestions** | Badges populate textarea on click | Story 2, 3 |
| **Attachment Button** | Placeholder for context/estimation JSON | Story 2 |

#### Keyboard Handling

```typescript
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
};
```

---

### CynefinRouter

**Location:** `src/components/carf/CynefinRouter.tsx`

**Purpose:** Classifies the problem domain according to Cynefin framework and routes to appropriate solver. Critical for determining which reasoning approach to apply.

#### Props Interface

```typescript
interface CynefinRouterProps {
  classification: CynefinClassification;  // Domain classification data
  isVisible: boolean;                     // Controls render
}
```

#### Data Structure

```typescript
interface CynefinClassification {
  domain: 'clear' | 'complicated' | 'complex' | 'chaotic';
  confidence: number;      // 0-1
  entropy: number;         // 0-1 signal entropy
  solver: string;          // e.g., "BayesianInference", "AgenticSearch"
  reasoning: string;       // Explanation text
  scores: Record<CynefinDomain, number>;  // Per-domain probability scores
}
```

#### Visual Design

```
┌─────────────────────────────────────────────────┐
│ 🧭 Cynefin Classification         [COMPLICATED] │
├─────────────────────────────────────────────────┤
│ Expert analysis - Sense, Analyze, Respond       │
│                                                 │
│ Signal Entropy  ████████░░░░  0.64              │
│ Confidence      ████████████  87%               │
│                                                 │
│ 🛤️ Routed to: BayesianInference                │
│                                                 │
│ ▼ View domain scores                            │
│   Clear        ██░░░░░░░░  15%                  │
│   Complicated  ████████░░  64%                  │
│   Complex      ████░░░░░░  18%                  │
│   Chaotic      █░░░░░░░░░  3%                   │
│                                                 │
│ 🧠 High-dimensional correlations detected...    │
└─────────────────────────────────────────────────┘
```

#### Domain Configuration (with semantic colors)

```typescript
const domainConfig: Record<CynefinDomain, DomainConfig> = {
  clear: {
    label: 'Clear',
    color: 'text-cynefin-clear',      // Green
    bgColor: 'bg-cynefin-clear',
    description: 'Best practice - Sense, Categorize, Respond',
  },
  complicated: {
    label: 'Complicated',
    color: 'text-cynefin-complicated', // Blue
    bgColor: 'bg-cynefin-complicated',
    description: 'Expert analysis - Sense, Analyze, Respond',
  },
  complex: {
    label: 'Complex',
    color: 'text-cynefin-complex',     // Purple
    bgColor: 'bg-cynefin-complex',
    description: 'Emergent practice - Probe, Sense, Respond',
  },
  chaotic: {
    label: 'Chaotic',
    color: 'text-cynefin-chaotic',     // Red
    bgColor: 'bg-cynefin-chaotic',
    description: 'Novel practice - Act, Sense, Respond',
  },
};
```

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 2 | Domain classification transparency |
| Story 3 | Solver routing explanation |

---

### CausalDAG

**Location:** `src/components/carf/CausalDAG.tsx`

**Purpose:** Interactive Directed Acyclic Graph visualization for causal relationships. Implements the **Causal Graph Standards** from UIX guidelines.

#### Props Interface

```typescript
interface CausalDAGProps {
  dag: CausalDAGType;                    // Graph data
  isVisible: boolean;                    // Controls render
  onNodeClick?: (node: DAGNode) => void; // Node selection callback
}
```

#### Data Structures

```typescript
interface DAGNode {
  id: string;
  label: string;
  type: 'variable' | 'confounder' | 'intervention' | 'outcome';
  x: number;       // Position
  y: number;
  value?: number;  // Optional metric
  unit?: string;
}

interface DAGEdge {
  id: string;
  source: string;      // Node ID
  target: string;      // Node ID
  effectSize: number;  // Causal effect magnitude
  pValue: number;      // Statistical significance
  validated: boolean;  // Refutation status (Pass/Fail)
  confounders?: string[];  // Affecting confounders
}

interface CausalDAGType {
  nodes: DAGNode[];
  edges: DAGEdge[];
  backdoorPaths: string[][];  // Paths requiring adjustment
}
```

#### Visual Elements (per UIX Guidelines)

| Element | Shape | Color Token | Interaction |
|---------|-------|-------------|-------------|
| Variable | Circle | `chart-1` | Click to select |
| Confounder | Diamond | `chart-4` | Toggle visibility |
| Intervention | Hexagon | `chart-2` | Highlight treatment |
| Outcome | Circle (larger) | `chart-3` | Target variable |
| Validated Edge | Solid line | `chart-1` | Hover for details |
| Pending Edge | Dashed line | `muted-foreground` | Needs validation |

#### Causal Graph Standards Implementation

From `CARF_UIX_INTERACTION_GUIDELINES.md`:

> "Graphs must be interactive. Clicking a node highlights its Markov blanket (parents, children, parents of children). Edges show effect size and refutation status."

```
┌────────────────────────────────────────────────────────────┐
│ 🌳 Causal DAG                      [−] [100%] [+] [⛶]    │
├────────────────────────────────────────────────────────────┤
│ [Toggle] Show Confounders    [Toggle] Highlight Backdoors │
├────────────────────────────────────────────────────────────┤
│                                                            │
│        ◇ Seasonality                                       │
│           ↘ (+0.15)                                        │
│    ⬡ Investment ──(+0.42)──▶ ● Revenue                    │
│           ↗ (-0.08)              ↑                         │
│        ◇ Market              (+0.22)                       │
│          Conditions ─────────────┘                         │
│                                                            │
│                                    6 nodes · 8 edges       │
├────────────────────────────────────────────────────────────┤
│ ● Variable  ◆ Confounder  ⬡ Intervention  ● Outcome       │
│ ── Validated (Pass)  - - Pending/Failed                    │
└────────────────────────────────────────────────────────────┘
```

#### Interaction Controls

| Control | Purpose | Implementation |
|---------|---------|----------------|
| Zoom ±  | Scale graph view | `setZoom(z => Math.min(2, z + 0.1))` |
| Reset   | Return to 100% | `setZoom(1)` |
| Show Confounders | Toggle confounder visibility | `showConfounders` state |
| Highlight Backdoors | Show adjustment paths | `showBackdoorPaths` state |

#### Edge Tooltip Content

```tsx
<TooltipContent>
  <p>Effect: {edge.effectSize.toFixed(3)}</p>
  <p>p-value: {edge.pValue.toFixed(4)}</p>
  <p>Validated: {edge.validated ? "Yes ✓" : "Pending"}</p>
  {edge.confounders && <p>Confounders: {edge.confounders.join(', ')}</p>}
</TooltipContent>
```

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 3 | Interactive graph exploration |
| Story 2 | Effect size + refutation status |
| Story 5 | Causal path understanding for policy override |

---

### BayesianPanel

**Location:** `src/components/carf/BayesianPanel.tsx`

**Purpose:** Visualizes Bayesian belief states with prior/posterior distributions and uncertainty decomposition. Implements **Uncertainty Visualization** standards.

#### Props Interface

```typescript
interface BayesianPanelProps {
  beliefStates: BayesianBeliefState[];  // Array of belief states
  isVisible: boolean;
}
```

#### Data Structure

```typescript
interface BayesianBeliefState {
  variable: string;
  priorMean: number;
  priorStd: number;
  posteriorMean: number;
  posteriorStd: number;
  confidenceLevel: 'high' | 'medium' | 'low';
  interpretation: string;
  epistemicUncertainty: number;  // 0-1 (reducible)
  aleatoricUncertainty: number;  // 0-1 (irreducible)
  totalUncertainty: number;      // 0-1
  observations: Array<{ time: string; value: number }>;
}
```

#### Uncertainty Visualization Standards

From `CARF_UIX_INTERACTION_GUIDELINES.md`:

> "Never display single numbers for predictions. Always show confidence intervals (e.g., 'ROI: 10% - 14%')"

**Color coding for confidence:**

| Level | Color Token | Threshold | Meaning |
|-------|-------------|-----------|---------|
| 🟢 High | `confidence-high` | Variance < threshold | Strong evidence |
| 🟡 Medium | `confidence-medium` | Gathering data | Moderate evidence |
| 🔴 Low | `confidence-low` | High entropy/disorder | Weak evidence |

#### Visual Layout

```
┌───────────────────────────────────────────────────────────┐
│ 📊 Bayesian Belief State              [Variable ▼]       │
├───────────────────────────────────────────────────────────┤
│                                                           │
│      ╭──────╮                                             │
│     ╱        ╲   ← Prior (dashed, faded)                  │
│    ╱    ╭────╲───╮                                        │
│   ╱    ╱      ╲   ╲  ← Posterior (solid, primary)         │
│  ╱    ╱        ╲   ╲                                      │
│ ─────╱──────────╲───╲───────────                          │
│              ↑ Mean reference line                         │
│                                                           │
│        - - Prior    ── Posterior                          │
│                                                           │
│ ┌─────────────┐  ┌─────────────┐                          │
│ │ Post. Mean  │  │   95% CI    │  ← ALWAYS show interval  │
│ │   142.50    │  │ [128, 157]  │                          │
│ │  ±8.25 std  │  │             │                          │
│ └─────────────┘  └─────────────┘                          │
│                                                           │
│ UNCERTAINTY DECOMPOSITION                                 │
│ Epistemic  ██████░░░░   42%   (reducible with data)      │
│ Aleatoric  ████░░░░░░   28%   (irreducible noise)        │
│ ─────────────────────────────                             │
│ Total      ████████░░   58%                               │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 🟡 Medium Confidence                                 │   │
│ │ Evidence moderately supports revenue hypothesis     │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                           │
│ 📈 Belief Evolution (sparkline)                           │
│ ─╲_╱───╲╱─────────── t                                    │
└───────────────────────────────────────────────────────────┘
```

#### Distribution Generation

```typescript
function generateDistributionData(mean: number, std: number, prefix: string) {
  const data = [];
  const range = std * 4;
  const step = range / 50;
  for (let x = mean - range; x <= mean + range; x += step) {
    const z = (x - mean) / std;
    const y = Math.exp(-0.5 * z * z) / (std * Math.sqrt(2 * Math.PI));
    data.push({ x, [prefix]: y });
  }
  return data;
}
```

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 2 | Uncertainty decomposition (epistemic vs aleatoric) |
| Story 5 | Confidence level for override decision |

---

### CausalAnalysisCard

**Location:** `src/components/carf/CausalAnalysisCard.tsx`

**Purpose:** Displays causal effect estimates with refutation tests and confounder analysis. Provides the "WHY" in the 3-Point Context model.

#### Props Interface

```typescript
interface CausalAnalysisCardProps {
  result: CausalAnalysisResult;
  isVisible: boolean;
}
```

#### Data Structure

```typescript
interface CausalAnalysisResult {
  effect: number;                // Point estimate
  unit: string;                  // e.g., "million USD"
  pValue: number;
  confidenceInterval: [number, number];  // ALWAYS show interval
  description: string;
  refutationsPassed: number;
  refutationsTotal: number;
  refutationDetails: Array<{
    name: string;
    passed: boolean;
    pValue: number;
  }>;
  confoundersControlled: Array<{
    name: string;
    controlled: boolean;
  }>;
  evidenceBase: string;
  metaAnalysis: boolean;
  studies: number;
}
```

#### Refutation Tests (Scientific Rigor)

| Test | Purpose |
|------|---------|
| Placebo Treatment | Verify effect isn't spurious |
| Random Common Cause | Test for confounding |
| Data Subset | Validate across subpopulations |
| Unobserved Confounder | Sensitivity analysis |
| Bootstrap | Statistical robustness |

#### Visual Layout

```
┌───────────────────────────────────────────────────────────┐
│ 🧪 Causal Analysis Results        [4/5 Refutations Passed]│
├───────────────────────────────────────────────────────────┤
│                                                           │
│             ┌─────────────────────────────┐               │
│             │   CAUSAL EFFECT ESTIMATE    │               │
│             │         +18.5               │               │
│             │       million USD           │               │
│             │    p-value: 0.0023          │               │
│             └─────────────────────────────┘               │
│                                                           │
│ 95% Confidence Interval                                   │
│ [12.3]━━━━━━━━━━━│━━━━━━━━━━[24.7]                         │
│                  ↑ point estimate                         │
│                                                           │
│ [Causal description: "Investment causes revenue..."]      │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 🧫 Refutation Tests                    4/5 passed ▼ │   │
│ ├─────────────────────────────────────────────────────┤   │
│ │ ✅ Placebo Treatment       p=0.823                   │   │
│ │ ✅ Random Common Cause     p=0.912                   │   │
│ │ ✅ Data Subset             p=0.876                   │   │
│ │ ✅ Unobserved Confounder   p=0.654                   │   │
│ │ ❌ Bootstrap Refute        p=0.043  ← failed!        │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 📚 Evidence: Historical investment analysis         │   │
│ │    Meta-analysis: Yes · Studies: 12                 │   │
│ └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 2 | Refutation test details |
| Story 3 | Confounder control status |
| Story 1 | Effect estimate for WHY context |

---

### GuardianPanel

**Location:** `src/components/carf/GuardianPanel.tsx`

**Purpose:** Policy gate for human-in-the-loop approval. Primary component for **Fast-Thinking** channel integration.

#### Props Interface

```typescript
interface GuardianPanelProps {
  decision: GuardianDecision;
  isVisible: boolean;
  onApprove?: () => void;                    // triggers action_execute()
  onReject?: (reason: string) => void;       // triggers action_abort()
  onRequestClarification?: () => void;       // opens slow-thinking channel
}
```

#### Data Structure

```typescript
interface GuardianDecision {
  overallStatus: 'pass' | 'fail' | 'pending';
  proposedAction: {
    type: string;          // e.g., "increase_investment"
    target: string;        // e.g., "Marketing Budget - Q3"
    amount: number;
    unit: string;
    expectedEffect: string;  // e.g., "+12% revenue uplift"
  };
  policies: Array<{
    id: string;
    name: string;
    description: string;
    status: PolicyStatus;
    version: string;
    details?: string;
  }>;
  requiresHumanApproval: boolean;
}
```

#### Interactive Resolution Flow

From `DATA_LAYER.md`:

> When Guardian blocks an action:
> 1. Policy violation detected (e.g., "Invest $600k" exceeds $500k limit)
> 2. HumanLayer sends Slack card to authorized user
> 3. Options: Reject, Approve One-Time Exception, Modify Amount
> 4. User selection triggers workflow continuation
> 5. Audit link connects back to cockpit for traceability

#### Visual Layout

```
┌───────────────────────────────────────────────────────────┐
│ 🛡️ Guardian Policy Check                          [PASS] │
├───────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 🎯 PROPOSED ACTION (WHAT)                           │   │
│ │    Increase Investment                              │   │
│ │    Marketing Budget - Q3 Campaign                   │   │
│ │                                                     │   │
│ │    Amount            Expected Effect (WHY)          │   │
│ │    2.5M USD          ⚡ +12% revenue uplift         │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                           │
│ ✅ 4 passed  ❌ 0 failed  ⏳ 1 pending (RISK indicators) │
│                                                           │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ ✅ Budget Threshold         v2.1                   ▼ │  │
│ │    Amount within approved limits                     │  │
│ └──────────────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ ⏳ Final Approval           v1.0                   ▼ │  │
│ │    Awaiting stakeholder sign-off                     │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 🛡️ Human-in-the-loop required.                      │   │
│ │    This action requires your explicit approval.      │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                           │
│ ─────────────────────────────────────────────────────────  │
│ [    ✅ Approve    ] [💬 Clarify] [    ❌ Reject    ]     │
└───────────────────────────────────────────────────────────┘
```

#### Action Button Mapping

| Button | Triggers | Channel |
|--------|----------|---------|
| Approve | `onApprove()` → `action_execute()` | Fast |
| Clarify | `onRequestClarification()` → Opens cockpit context | Fast → Slow |
| Reject | Shows reason input → `onReject(reason)` → `action_abort()` | Fast |

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 1 | Full approval workflow |
| Story 5 | Policy details for override decision |

---

### ExecutionTrace

**Location:** `src/components/carf/ExecutionTrace.tsx`

**Purpose:** Timeline view of analysis execution steps. Provides complete audit trail for **Story 4**.

#### Props Interface

```typescript
interface ExecutionTraceProps {
  trace: ExecutionTraceType;
  isVisible: boolean;
}
```

#### Data Structure

```typescript
interface ExecutionTrace {
  receiptId: string;       // Unique decision identifier
  sessionId: string;       // Session context
  totalDuration: number;   // ms
  langsmithUrl: string;    // External audit link
  steps: ExecutionStep[];
}

interface ExecutionStep {
  id: string;
  node: string;           // Step name (e.g., "CynefinRouter")
  status: 'success' | 'warning' | 'error' | 'pending';
  duration: number;       // ms
  timestamp: string;      // ISO date
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
}
```

#### Visual Layout

```
┌───────────────────────────────────────────────────────────┐
│ 📊 Execution Trace                              [2.34s]   │
├───────────────────────────────────────────────────────────┤
│ Receipt ID                                                │
│ rcp_abc123def456...                              [📋]    │
│                                                           │
│ ✅ 5  ⚠️ 1  ❌ 0   6 steps total                          │
│                                                           │
│  ●─ QueryParser                            120ms    ▼    │
│  │    └─ { query: "...", parsed: {...} }                  │
│  │                                                        │
│  ●─ CynefinRouter                          340ms    ▼    │
│  │    └─ { domain: "complicated", solver: "..." }         │
│  │                                                        │
│  ●─ CausalAnalyst                          890ms    ▼    │
│  │                                                        │
│  ●─ BayesianUpdater                        450ms    ▼    │
│  │                                                        │
│  ⚠─ Guardian                               380ms    ▼    │
│  │    └─ { warning: "Policy threshold exceeded" }         │
│  │                                                        │
│  ●─ ResponseFormatter                      160ms    ▼    │
│                                                           │
│ ─────────────────────────────────────────────────────────  │
│ [   📥 Export JSON   ] [   🔗 View in LangSmith   ]      │
│                                                           │
│ Session: sess_demo_abc123                                 │
└───────────────────────────────────────────────────────────┘
```

#### Audit Features

| Feature | Implementation |
|---------|----------------|
| Copy Receipt ID | `navigator.clipboard.writeText(trace.receiptId)` |
| Export JSON | Download full trace as `.json` file |
| LangSmith Link | External deep link for detailed trace view |
| Step Expansion | Collapsible panels show inputs/outputs |

#### User Story Mapping

| Story | Feature Used |
|-------|--------------|
| Story 4 | Full audit trail with inputs/outputs |
| Story 2 | Reasoning chain verification |

---

## View Mode Components

### DeveloperDebugView

**Location:** `src/components/carf/DeveloperDebugView.tsx`

**Purpose:** Technical deep-dive for data scientists and developers. Implements **Story 2** and **Story 6**.

#### Key Features

| Feature | Description |
|---------|-------------|
| **Raw JSON Viewer** | Full scenario data as formatted JSON |
| **Performance Metrics** | Execution time, step durations, memory usage |
| **System State** | Current simulation parameters, active solvers |
| **Session History** | Recent analyses for comparison (Story 6) |
| **Copy/Export** | Quick access to data for debugging |

---

### ExecutiveSummaryView

**Location:** `src/components/carf/ExecutiveSummaryView.tsx`

**Purpose:** High-level KPI dashboard for decision-makers. Simplified version of **Story 1** workflow.

#### Key Features

| Feature | Description |
|---------|-------------|
| **Key Metrics Cards** | Effect size, confidence, risk level (traffic light) |
| **Recommendation Summary** | Plain-language action description |
| **Quick Actions** | Simplified Approve/Reject (no details) |
| **Trend Indicators** | Visual status badges |

---

## Control Components

### SimulationControls

**Location:** `src/components/carf/SimulationControls.tsx`

**Purpose:** Parameter adjustment for dynamic simulation mode. Enables "what-if" analysis.

#### Props Interface

```typescript
interface SimulationControlsProps {
  params: SimulationParams;
  onChange: (params: SimulationParams) => void;
  onReset: () => void;
  disabled: boolean;
}
```

#### Parameters

| Parameter | Type | Range | Default | Purpose |
|-----------|------|-------|---------|---------|
| `investmentMultiplier` | number | 0.5 - 2.0 | 1.0 | Scale investment amounts |
| `confidenceThreshold` | number | 0.5 - 0.99 | 0.95 | Minimum confidence required |
| `uncertaintyTolerance` | number | 0.1 - 0.5 | 0.3 | Acceptable uncertainty level |
| `policyStrictness` | enum | low/medium/high | medium | Policy enforcement level |

---

## HumanLayer Integration

### 3-Point Context Model

Every approval request (fast-thinking channel) includes structured context:

```typescript
interface HumanLayerNotification {
  what: string;      // One-sentence summary of proposed action
  why: string;       // Causal justification with confidence level
  risk: string;      // Why it was flagged (policy or uncertainty)
  actions: {
    approve: () => void;    // triggers action_execute()
    reject: () => void;     // triggers action_abort()
    modify: () => void;     // opens parameter editor modal
    audit: string;          // deep link to cockpit session
  };
}
```

### Channel Bridging

```
┌────────────────────────────────────────────────────────────────────┐
│                        CHANNEL FLOW                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [CARF System] → Policy Violation Detected                         │
│        │                                                            │
│        ▼                                                            │
│  ┌─────────────┐                                                    │
│  │ HumanLayer  │ ← Push notification (Slack/Teams/Email)           │
│  │ Fast Channel│                                                    │
│  └──────┬──────┘                                                    │
│         │                                                           │
│    ┌────┴────┬──────────┬──────────┐                                │
│    ▼         ▼          ▼          ▼                                │
│ [Approve] [Reject]  [Modify]   [Audit]                              │
│    │         │          │          │                                │
│    │         │          │          ▼                                │
│    │         │          │    ┌───────────┐                          │
│    │         │          │    │ Cockpit   │ ← Pull (user navigates)  │
│    │         │          │    │ Slow      │                          │
│    │         │          │    │ Channel   │                          │
│    │         │          │    └─────┬─────┘                          │
│    │         │          │          │                                │
│    ▼         ▼          ▼          ▼                                │
│  ┌──────────────────────────────────────┐                           │
│  │         Workflow Continues           │                           │
│  │   (with human decision injected)     │                           │
│  └──────────────────────────────────────┘                           │
└────────────────────────────────────────────────────────────────────┘
```

---

## UX Standards & Design Principles

### Uncertainty Visualization (MANDATORY)

From `CARF_UIX_INTERACTION_GUIDELINES.md`:

> "Never display single numbers for predictions. Always show confidence intervals."

**Implementation checklist:**

- [ ] All predictions show ranges, not point estimates alone
- [ ] 95% confidence intervals displayed prominently
- [ ] Color-coded confidence levels (Green/Yellow/Red)
- [ ] Uncertainty decomposition (epistemic vs aleatoric) visible

### Causal Graph Standards (MANDATORY)

From `CARF_UIX_INTERACTION_GUIDELINES.md`:

> "Graphs must be interactive. Clicking a node highlights its Markov blanket."

**Implementation checklist:**

- [ ] Node click selects and highlights related nodes
- [ ] Parents, children, and co-parents visually distinguished
- [ ] Edges show effect size on hover/always
- [ ] Refutation status (Pass/Fail) indicated on edges
- [ ] Confounder toggle available

### Typography

- **Headers:** System UI font stack (Inter, SF Pro, etc.)
- **Monospace:** For IDs, timestamps, JSON (`font-mono`)
- **Body:** Readable at small sizes for dense information display

### Color Semantics

| Purpose | Token | Usage |
|---------|-------|-------|
| Success/Pass | `status-success` | Green indicators, approved policies |
| Warning/Pending | `status-warning` | Yellow alerts, pending items |
| Error/Fail | `status-error` | Red alerts, failed policies |
| Confidence High | `confidence-high` | Green confidence badges |
| Confidence Medium | `confidence-medium` | Yellow confidence badges |
| Confidence Low | `confidence-low` | Red confidence badges |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Index.tsx                                 │
│                                                                      │
│   ┌──────────────────┐    ┌─────────────────────────────────┐       │
│   │  User Input       │───▶│       carfService.ts            │       │
│   │  (QueryInput)     │    │                                 │       │
│   └──────────────────┘    │  runAnalysis(request, onProgress)│       │
│                            │         │                        │       │
│                            │         ▼                        │       │
│   ┌──────────────────┐    │  ┌─────────────────────────┐    │       │
│   │  State Updates    │◀──│  │  Mock Data / API Call   │    │       │
│   │                   │    │  │  (Backend-ready)        │    │       │
│   │  - currentStep    │    │  └─────────────────────────┘    │       │
│   │  - scenario       │    │                                 │       │
│   │  - isProcessing   │    │  Returns: { scenario,          │       │
│   └──────────────────┘    │            executionTimeMs }    │       │
│           │                └─────────────────────────────────┘       │
│           ▼                                                          │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │                   Component Props Flow                      │     │
│   │                                                             │     │
│   │   CynefinRouter ◀── scenario.cynefin                       │     │
│   │   CausalDAG     ◀── scenario.dag                           │     │
│   │   BayesianPanel ◀── scenario.beliefStates                  │     │
│   │   CausalAnalysis◀── scenario.causalResult                  │     │
│   │   GuardianPanel ◀── scenario.guardian                      │     │
│   │   ExecutionTrace◀── scenario.trace                         │     │
│   └───────────────────────────────────────────────────────────┘     │
│                                                                      │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │                   HumanLayer Integration                    │     │
│   │                                                             │     │
│   │   GuardianPanel.onApprove  ──▶  HumanLayer.approve()       │     │
│   │   GuardianPanel.onReject   ──▶  HumanLayer.reject()        │     │
│   │   GuardianPanel.onClarify  ──▶  Deep link to session       │     │
│   └───────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---
  as
## Design System Tokens

### Color Tokens (HSL Format)

| Token | Purpose | Light Mode | Dark Mode |
|-------|---------|------------|-----------|
| `--primary` | Brand, CTAs | `262 83% 58%` | `262 83% 65%` |
| `--accent` | Highlights | `280 85% 65%` | `280 85% 70%` |
| `--background` | Page bg | `260 15% 98%` | `260 15% 8%` |
| `--card` | Card bg | `260 15% 100%` | `260 15% 12%` |
| `--muted-foreground` | Secondary text | `260 5% 45%` | `260 5% 60%` |

### Semantic Status Colors

| Token | Purpose | Value |
|-------|---------|-------|
| `--status-success` | Pass, approved | Green (HSL) |
| `--status-warning` | Pending, caution | Amber (HSL) |
| `--status-error` | Fail, rejected | Red (HSL) |
| `--status-pending` | In progress | Blue (HSL) |

### Cynefin Domain Colors

| Domain | Token | Semantic Meaning |
|--------|-------|------------------|
| Clear | `--cynefin-clear` | Known knowns (Green) |
| Complicated | `--cynefin-complicated` | Known unknowns (Blue) |
| Complex | `--cynefin-complex` | Unknown unknowns (Purple) |
| Chaotic | `--cynefin-chaotic` | Unknowable (Red) |

### Confidence Level Colors

| Level | Token | Threshold |
|-------|-------|-----------|
| High | `--confidence-high` | Posterior variance < 0.1 |
| Medium | `--confidence-medium` | 0.1 ≤ variance < 0.3 |
| Low | `--confidence-low` | variance ≥ 0.3 |

---

## Animation Patterns

### Entry Animations

```css
.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Loading States

| Animation | Usage | CSS Class |
|-----------|-------|-----------|
| Pulse | Initializing states | `animate-pulse` |
| Spin | Active processing | `animate-spin` |
| Fade-in | Component reveal | `animate-fade-in` |

### Step Reveal Timing

```typescript
const stepDelays = [400, 600, 1200, 800, 500];  // ms per step
```

| Step | Component | Delay | Total | Cognitive Purpose |
|------|-----------|-------|-------|-------------------|
| 1 | CynefinRouter | 400ms | 400ms | "What kind of problem?" |
| 2 | CausalDAG | 600ms | 1000ms | "What relationships?" |
| 3 | BayesianPanel | 1200ms | 2200ms | "What does data say?" |
| 4 | GuardianPanel | 800ms | 3000ms | "Should we act?" |
| 5 | ExecutionTrace | 500ms | 3500ms | "Full audit available" |

---

## InsightsPanel (Enhanced)

**Location:** `src/components/carf/InsightsPanel.tsx`

**Purpose:** Displays analytical insights, actionable next steps, and sequenced roadmaps per persona. Enhanced in Phase 13 with Action Items and Roadmap subsections.

### Props Interface

```typescript
interface InsightsPanelProps {
  persona: string;
  domain: string;
  domainConfidence: number;
  hasCausalResult: boolean;
  causalEffect: number | null;
  refutationPassRate: number | null;
  sampleSize: number | null;
}
```

### Data Structures

```typescript
interface ActionItem {
  id: string;
  title: string;
  description: string;
  effort: 'quick' | 'medium' | 'deep';
  category: 'data_quality' | 'model_improvement' | 'risk_mitigation' | 'exploration';
  api_endpoint: string | null;
  api_payload: Record<string, unknown> | null;
}

interface RoadmapItem {
  step: number;
  title: string;
  description: string;
  depends_on: number[];
  estimated_time: string;
}

interface EnhancedInsightsResponse {
  persona: string;
  insights: Insight[];
  action_items: ActionItem[];
  roadmap: RoadmapItem[];
  total_count: number;
  generated_at: string;
}
```

### Visual Layout

```
┌───────────────────────────────────────────────────────────┐
│ 💡 Insights & Actions                                     │
├───────────────────────────────────────────────────────────┤
│ [Insights] [Action Items] [Roadmap]   ← Tab navigation    │
│                                                           │
│ ── Action Items Tab ──                                    │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 🔬 Run sensitivity analysis           [quick] 🟢    │   │
│ │ Low refutation pass rate detected...                │   │
│ └─────────────────────────────────────────────────────┘   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ 📊 Upload additional data             [medium] 🟡   │   │
│ │ Sample size below recommended threshold...          │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                           │
│ ── Roadmap Tab ──                                         │
│ ① Validate data quality                    ~30 min        │
│ │  Check for missing values and outliers                  │
│ ②─┤ Run sensitivity analysis               ~1 hour       │
│ │  Multiple estimator comparison                          │
│ ③─┤ Collect additional data                ~1 week        │
│    Increase sample size for robustness                    │
└───────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| **Tabbed navigation** | Three tabs: Insights, Action Items, Roadmap |
| **Effort badges** | Color-coded: quick (green), medium (yellow), deep (orange) |
| **API endpoint linking** | Action items can include pre-wired API call payloads |
| **Dependency tracking** | Roadmap steps show `depends_on` relationships |
| **Persona filtering** | Actions tailored to analyst/developer/executive |
| **Graceful fallback** | Falls back to `/insights/generate` if enhanced endpoint unavailable |

### Fetch Logic

```typescript
// Try enhanced endpoint first
const enhanced = await fetch('/insights/enhanced', { method: 'POST', body: context });
if (enhanced.ok) {
  // Use action_items + roadmap + insights
} else {
  // Fall back to standard insights
  const standard = await fetch('/insights/generate', { method: 'POST', body: context });
}
```

---

## Implementation Status

### Current Phase: Phase 5 - React Platform Cockpit Development

**Status**: 📋 Implementation Plan Complete, Ready for Development

**Timeline**: 17-24 days (3-4 weeks)

### 10-Phase Development Plan

1. **Phase 1: Foundation & Layout** (2-3 days)
   - Vite + React + TypeScript setup
   - Tailwind CSS + shadcn/ui configuration
   - Dashboard shell with 3-6-3 grid layout
   - CARF design system (purple #7C3AED, green #10B981)

2. **Phase 2: Query Input & Scenario Registry** (2 days)
   - Query input component with auto-resize
   - Scenario selector with 5 demo scenarios
   - Suggested queries as clickable badges
   - Optional guided walkthrough

3. **Phase 3: Cynefin Router & Classification** (1-2 days)
   - Domain classification display
   - Confidence meter and entropy indicator
   - Solver recommendation
   - Domain scores accordion

4. **Phase 4: Interactive Causal DAG** (3-4 days)
   - react-flow integration
   - Custom node types (variable, confounder, intervention, outcome)
   - Edge annotations with effect sizes
   - Markov blanket highlighting on node click
   - Zoom/pan controls with backdoor path toggle

5. **Phase 5: Causal Analysis Results** (2 days)
   - Effect estimate card with CI visualization
   - Refutation test accordion (5 tests)
   - Confounder control section
   - Evidence base metadata

6. **Phase 6: Bayesian Panel** (2-3 days)
   - Prior/Posterior distribution charts (Recharts)
   - Belief stats table with credible intervals
   - Uncertainty decomposition (epistemic vs. aleatoric)
   - Confidence level badges
   - Probe recommendations

7. **Phase 7: Guardian Panel** (2 days)
   - Verdict badges (approved/rejected/pending)
   - 3-Point Context Card (What/Why/Risk)
   - Policy violation cards with severity
   - Approval action buttons (mock, ready for HumanLayer)

8. **Phase 8: Execution Trace** (2 days)
   - Vertical timeline with workflow steps
   - Collapsible step cards with JSON inputs/outputs
   - Session ID display with copy button
   - Export trace as JSON

9. **Phase 9: Response & Summary Panel** (1-2 days)
   - Response badges (domain, verdict, confidence)
   - Markdown-formatted main response
   - Confidence indicator (color-coded)
   - Key insights and next steps

10. **Phase 10: Mock Data & API Layer** (2-3 days)
    - TypeScript type definitions for all CARF entities
    - Mock service layer with realistic responses
    - 5 complete scenario payloads
   - React Query hooks for API calls
    - Environment toggle: `VITE_USE_MOCK_DATA=true|false`

### Backend API Alignment ✅

**Verified Compatibility** (2026-01-15):
- 8 API endpoints fully implemented
- 73+ unit tests passing
- Complete response schemas match React type definitions:
  - `QueryResponse` with causal/bayesian/guardian results
  - `CausalResult` with effect, CI, refutations
  - `BayesianResult` with uncertainties and probes
  - `GuardianResult` with verdict and violations
- Mock data layer mirrors backend structure

### Implementation Artifacts

- **Plan**: `REACT_IMPLEMENTATION_PLAN.md` (comprehensive 10-phase guide)
- **Backend Status**: All dependencies verified, tests passing
- **Design Reference**: Streamlit cockpit light theme

## Implementation Status

### ✅ Completed (Streamlit Epistemic Cockpit v2.0)

The dashboard has been fully refactored to a modern UI/UX following the target design specifications.

| Component | Status | Implementation Notes |
|-----------|--------|----------------------|
| DashboardHeader | ✅ | Logo, version badge, session indicator with pulse animation |
| ViewModeTabs | ✅ | End-User / Developer / Executive toggle buttons |
| QueryInput | ✅ | Textarea with suggested queries that populate input on click |
| SimulationControls | ✅ | Investment multiplier, confidence threshold, uncertainty tolerance, policy strictness |
| CynefinRouter | ✅ | Domain badge (Clear/Complicated/Complex/Chaotic), entropy + confidence bars, solver routing |
| CausalDAG | ✅ | Interactive Graphviz chart with node types (Variable, Confounder, Intervention, Outcome), legend |
| BayesianPanel | ✅ | Altair distribution chart, posterior mean/CI stats, uncertainty decomposition (epistemic/aleatoric/total) |
| CausalAnalysisCard | ✅ | Effect estimate, p-value, confidence interval slider, refutation tests, confounder list, evidence base |
| GuardianPanel | ✅ | Proposed action card, policy checklist with status icons, HITL warning, Approve/Clarify/Reject buttons |
| ExecutionTrace | ✅ | Receipt ID, step timeline with status dots, duration, Export JSON / LangSmith buttons |
| SystemStatus | ✅ | Developer view with JSON status display |

### Design System Implementation

| Token Category | Status | Details |
|----------------|--------|---------|
| Color Palette | ✅ | Primary (#7C3AED), Accent (#10B981), Dark backgrounds, semantic status colors |
| Cynefin Colors | ✅ | Clear (green), Complicated (blue), Complex (purple), Chaotic (red) |
| Confidence Colors | ✅ | High (green), Medium (amber), Low (red) |
| Typography | ✅ | Inter font family, monospace for IDs/timestamps |
| Card Components | ✅ | Dark glass cards with subtle borders |
| Progress Bars | ✅ | Custom progress bars with colored fills |
| Badges | ✅ | Status badges (primary, success, warning, error, info) |
| Timeline | ✅ | Vertical timeline with status dots |
| Animations | ✅ | Pulse animation on session indicator |

### Three-Column Layout

```
┌────────────────┬──────────────────────┬────────────────┐
│   LEFT (3)     │     CENTER (6)       │   RIGHT (3)    │
├────────────────┼──────────────────────┼────────────────┤
│ QueryInput     │ CausalDAG            │ ExecutionTrace │
│ SimControls    │ CausalAnalysisCard   │ SystemStatus*  │
│ CynefinRouter  │ GuardianPanel        │                │
│ BayesianPanel  │                      │                │
└────────────────┴──────────────────────┴────────────────┘
* SystemStatus only visible in Developer view mode
```

### 🔄 Future Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| Markov Blanket Highlighting | High | Click node → highlight parents, children, co-parents |
| HumanLayer Slack Integration | High | Real push notifications via HumanLayer SDK |
| Neo4j Graph Persistence | Medium | Load/save sessions from graph database |
| Kafka Audit Trail | Medium | Real-time event streaming |
| Edge Effect Size Annotations | Medium | Always-visible effect sizes on graph |
| Historical Analysis Search | Low | Query by treatment/outcome variables |
| React Migration | Low | Full React/Next.js implementation for production |

---

## File Structure (Current - Streamlit)

```
src/
└── dashboard/
    ├── __init__.py
    └── app.py                       # Main Streamlit dashboard with all components
```

### Component Functions in app.py

| Function | Purpose |
|----------|---------|
| `render_dashboard_header()` | Logo, title, version, session badge |
| `render_view_mode_tabs()` | End-User / Developer / Executive tabs |
| `render_query_input()` | Query textarea + Analyze button + suggestions |
| `render_simulation_controls()` | Slider controls for simulation parameters |
| `render_cynefin_classification()` | Domain classification panel |
| `render_bayesian_belief_state()` | Uncertainty visualization |
| `render_causal_dag()` | Graphviz DAG with legend |
| `render_causal_analysis_results()` | Effect estimate + refutations |
| `render_guardian_policy_check()` | Policy checks + approval buttons |
| `render_execution_trace()` | Timeline + export buttons |
| `render_system_status()` | Developer system status JSON |

### Future File Structure (React Migration)

```
src/
├── components/
│   └── carf/
│       ├── DashboardHeader.tsx      # Global navigation
│       ├── QueryInput.tsx           # Query submission
│       ├── CynefinRouter.tsx        # Domain classification
│       ├── CausalDAG.tsx            # Interactive graph
│       ├── BayesianPanel.tsx        # Uncertainty visualization
│       ├── CausalAnalysisCard.tsx   # Effect estimates
│       ├── GuardianPanel.tsx        # Policy + approval
│       ├── ExecutionTrace.tsx       # Audit timeline
│       ├── DeveloperDebugView.tsx   # Technical debug
│       ├── ExecutiveSummaryView.tsx # Executive KPIs
│       └── SimulationControls.tsx   # Parameter adjustment
├── data/
│   └── mockData.ts                  # Mock scenarios (S3AE, BCX, TEH)
├── services/
│   └── carfService.ts               # Backend-ready API layer
└── pages/
    └── Index.tsx                    # Main dashboard orchestration
```

---

## Quick Reference: User Story → Component Mapping

| User Story | Primary Components | Channel |
|------------|-------------------|---------|
| 1. Quick Approve/Reject | GuardianPanel, HumanLayer | Fast |
| 2. Verify Reasoning | QueryInput, BayesianPanel, ExecutionTrace | Slow |
| 3. Explore Causal Relationships | CausalDAG, CausalAnalysisCard | Slow |
| 4. Audit Trail | ExecutionTrace, DeveloperDebugView | Slow |
| 5. Policy Override Investigation | GuardianPanel → CausalDAG → BayesianPanel | Fast → Slow |
| 6. Compare Historical Analyses | DeveloperDebugView (session history) | Slow |

---

## Phase 6: Enhanced UIX & Explainability Components

> **Status**: Planning Complete — Implementation Ready  
> **Reference**: See `critical_analysis.md` for full rationale

### New Component Requirements

| Component | Purpose | Complexity |
|-----------|---------|------------|
| `OnboardingOverlay.tsx` | First-run scenario discovery with cards | Medium |
| `DataOnboardingWizard.tsx` | 5-step guided data upload flow | High |
| `ConversationalResponse.tsx` | Dialog-style results with confidence zones | High |
| `FloatingChatTab.tsx` | Persistent chat in bottom-right corner | Medium |
| `WalkthroughManager.tsx` | Multi-track guided tour system | High |
| `MethodologyModal.tsx` | Drill-down transparency for any result | Medium |
| `ConfidenceDecomposition.tsx` | Stacked bar showing data/model/validation | Medium |
| `SuggestedQuestions.tsx` | Clickable follow-up question cards | Low |
| `DataProvenanceLink.tsx` | Inline link to source data rows | Low |
| `SpotlightOverlay.tsx` | Element highlighting for tours | Medium |

### Explainability Principles

Every panel must answer:
1. **Why this?** — What led to this conclusion
2. **How confident?** — Decomposed confidence sources
3. **Based on what?** — Link to source data/methodology

### Walkthrough Tracks

| Track | Target | Duration |
|-------|--------|----------|
| 🎯 Quick Demo | Evaluators | 2-3 min |
| 📊 Analyst Onboarding | Data Scientists | 5-7 min |
| 🔧 Contributor Guide | Developers | 10-15 min |
| 🏢 Production Path | Enterprise | 5-10 min |

### Transparency Enhancements

| Element | Current | Enhanced |
|---------|---------|----------|
| Effect estimate | Number + CI | + [View Methodology] link |
| Confidence score | Color badge | Decomposed bar |
| Guardian verdict | Pass/Fail | + Policy rule text |
| Cynefin domain | Badge | + Alternative scores |

---

*Generated for CARF Epistemic Cockpit v2.1.0*
*Phase 6: Enhanced UIX & Explainability*
