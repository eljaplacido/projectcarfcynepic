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
