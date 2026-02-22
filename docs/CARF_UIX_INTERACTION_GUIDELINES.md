# CARF UIX and Interaction Design Standards

## 1. Interaction Philosophy

CARF operates at two cognitive speeds. The UI must reflect this separation to avoid overload.

### 1.1 Fast Thinking (Operational Channel)

- Tool: HumanLayer (Slack/Teams/Email)
- Goal: Rapid, binary decisions (Approve/Reject) or quick steering
- Principle: "Don't make me think." Users should not need a dashboard for routine approvals.
- Latency: Push-based (system notifies user)

### 1.2 Slow Thinking (Analytical Cockpit)

- Tool: Streamlit or React dashboard
- Goal: Deep audit, causal graph inspection, system debugging
- Principle: "Show your work." Radical transparency of uncertainty and causal logic
- Latency: Pull-based (user logs in to investigate)

---

## 2. HumanLayer (HITL) Standards

All notifications sent via HumanLayer must include the "3-Point Context":

1. What: One-sentence summary of the proposed action
2. Why: Causal justification with confidence
3. Risk: Why it was flagged (policy violation or uncertainty)

### 2.1 Notification Card Template

Every `human_layer.require_approval()` payload must contain:

- What: "Approval needed: Allocate $150k to Supplier X for lithium procurement."
- Why: "Projected impact: reduces Scope 3 emissions by 12% (confidence: high)."
- Risk: "Flagged by policy: transaction exceeds auto-approval limit of $100k."

### 2.2 Interactive Elements

Use interactive buttons rather than dead-end text:

- Approve -> triggers `action_execute()`
- Reject -> triggers `action_abort()`
- Modify -> opens a modal to edit parameters
- Audit -> links to the relevant graph node in the cockpit

---

## 3. Epistemic Cockpit Standards

### 3.1 Visualizing Uncertainty

- Never display a single number for predictions.
- Always display a confidence interval (e.g., "ROI: 10% - 14%").

Color coding:

- Green: High confidence (posterior variance < threshold)
- Yellow: Medium confidence (gathering data)
- Red: Low confidence (high entropy or disorder)

### 3.2 Causal Graphs

- Graphs must be interactive.
- Clicking a node highlights its Markov blanket (parents, children, parents of children).
- Edges must show effect size and refutation status (Pass/Fail).

---

## 4. Phase 6 Explainability Standards

> Every analytical result must be **traceable, transparent, and explainable**.

### 4.1 Core Principles

Every panel in the cockpit must answer:
1. **"Why this?"** — What led to this conclusion
2. **"How confident?"** — Decomposed confidence sources (data/model/validation)
3. **"Based on what?"** — Link to source data and methodology

### 4.2 Drill-Down Requirements

All analytical outputs must support drill-down:
- **Effect Estimates** → Show data source, method, sample size, refutation status
- **Confidence Scores** → Show component breakdown (not just a single number)
- **Guardian Verdicts** → Show policy rule text and threshold values
- **Cynefin Classification** → Show alternative domain scores and entropy

### 4.3 Transparency Components

| Component | Purpose |
|-----------|---------|
| `MethodologyModal` | Drill-down for any analytical result |
| `ConfidenceDecomposition` | Stacked bar showing confidence sources |
| `DataProvenanceLink` | Inline link back to source data rows |
| `MarkdownRenderer` | Shared markdown with GFM tables, internal panel links |
| `TransparencyPanel` | Data modal, flowchart lineage, quality drill-downs with baselines |
| `useProactiveHighlight` | Auto-highlights relevant panels based on query results |

### 4.4 Drill-Down Patterns (UIX Rehaul)

All quality metrics now support inline drill-downs:
- **Quality Score Bars** — Click to expand with industry baselines and plain-English interpretation
- **Reliability Factors** — Cynefin-domain-aware explanations (e.g., "In complex domains, expect wider uncertainty bands")
- **Confidence Badges** — Hover for tooltip explaining high/medium/low in the ExecutionTrace
- **Guardian Policies** — Each policy shows contextual description and what configuration controls it

### 4.5 Section Header Naming Convention

Headers should be function-centric (what the user gets) not method-centric (how it works):
- "Cause & Effect Map" (not "Causal DAG")
- "Impact Analysis" (not "Causal Analysis Results")
- "Uncertainty & Belief Update" (not "Bayesian Panel")
- "Safety & Compliance Check" (not "Guardian Panel")
- "Decision Audit Trail" (not "Execution Trace")
- "How Robust Is This Finding?" (not "Sensitivity Analysis")

### 4.4 Conversational Questioning

Responses should be grouped by confidence level:
- 🟢 **High Confidence**: Strong evidence, actionable
- 🟡 **Medium Confidence**: Moderate evidence, possible confounders
- 🔴 **Needs More Information**: Specific gaps identified with suggested follow-ups
