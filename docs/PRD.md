# CARF Neuro-Symbolic-Causal System Blueprint (v2.0 with HumanLayer)

## Executive Summary: The Epistemological Transition to Agentic Systems

The trajectory of artificial intelligence is navigating a critical inflection point, transitioning from the "Generative Era" dominated by the probabilistic fluency of large language models to the "Agentic Era," where systems must execute autonomously in high-stakes, dynamic environments. This shift exposes a foundational epistemological deficit in current models: they excel at linguistic pattern matching but lack the structural reasoning needed to navigate causality, quantify uncertainty, and adhere to operational constraints in the physical world.

The prevailing transformer architecture operates on correlation, not causation. In domains such as supply chain logistics, financial risk management, and ecological engineering, conflating correlation with causation is a systemic risk that can yield brittle or hazardous outcomes.

This document presents the Complex-Adaptive Reasoning Fabric (CARF), a research-grade cognitive architecture that bridges the "trust gap." CARF enforces epistemic awareness: it explicitly distinguishes what it knows, what it infers, and what it does not know. By synthesizing the Cynefin framework, Bayesian inference, and causal inference, and by integrating HumanLayer for human-in-the-loop governance, CARF provides defensible, auditable, and collaborative agentic reasoning.

---

## 1. Theoretical Foundations: The Ontology of Robust Decision Making

CARF rejects the one-size-fits-all treatment of problems as text-completion tasks. Instead, it uses a context-aware ontology to decide which cognitive tool to use.

### 1.1 The Cynefin Framework as a Computational Meta-Operating System

Cynefin is operationalized as a meta-router that classifies incoming signals by entropy, causality, and stability:

- Clear (Ordered): Cause and effect are self-evident. Route to deterministic automation (RPA).
- Complicated (Analysis Required): Cause and effect require expert analysis. Route to causal inference engines (DoWhy/EconML).
- Complex (Emergent): Cause and effect are coherent only in retrospect. Route to Bayesian active inference agents.
- Chaotic (Unstable): The system is in crisis. Route to a circuit breaker for stabilization.
- Disorder (Unclear): Confidence below threshold. Route to HumanLayer for clarification or approval.

### 1.2 Bayesian Uncertainty and Active Inference

In the Complex domain, the system faces epistemic uncertainty. CARF uses Bayesian belief networks and active inference. Active inference minimizes variational free energy (surprise) and prioritizes information gain to prevent confident hallucinations.

### 1.3 Causal Inference: The Logic of Consequences

Safe action requires distinguishing correlation (P(Y|X)) from causation (P(Y|do(X))). CARF integrates structural causal models (DAGs) and uses refutation tests (e.g., placebo treatments) to validate reasoning.

---

## 2. Architectural Vision: The 4-Layer Cognitive Stack

The CARF architecture prevents the collapse of reasoning modes by separating concerns into four layers.

### Layer 1: Sense-Making Gateway (Router)

- Function: Decide how a problem should be solved.
- Mechanisms:
  - Signal entropy checks for volatility.
  - LLM classifier maps to Cynefin domain.
  - Ambiguity detection routes low-confidence inputs to HumanLayer.
- Action: The router calls HumanLayer for approvals or clarification when needed.

### Layer 2: Cognitive Mesh (Solvers)

LangGraph orchestrates a mesh of specialized agents:

- Deterministic Automation Agent (Clear)
- Causal Analyst Agent (Complicated)
- Active Inference Agent (Complex)
- Circuit Breaker Agent (Chaotic)

### Layer 3: Reasoning Services (Memory and Oracle)

- Causal Service: Neo4j graph database hosting DAGs
- Bayesian Service: Priors and posteriors
- Symbolic Service: Knowledge graph for ontological consistency

### Layer 4: Verifiable Action Layer (Guardian)

- Function: Enforce policy constraints.
- Mechanisms:
  - Guardian uses YAML policy checks; optional OPA integration is available for the demo stack.
  - High-risk actions trigger HumanLayer approval gates.

---

## 3. Detailed Technical Architecture

### 3.1 Backend Orchestration: LangGraph with HumanLayer

LangGraph manages cyclic, stateful workflows. A dedicated `human_escalation` node handles human-in-the-loop scenarios.

#### 3.1.2 Graph Topology (Updated)

```python
# Simplified LangGraph Definition for CARF with HumanLayer
workflow = StateGraph(AgentState)

# Node Definitions
workflow.add_node("router", cynefin_router_node)
workflow.add_node("causal_analyst", causal_agent_node)
workflow.add_node("bayesian_explorer", active_inference_node)
workflow.add_node("deterministic_runner", rpa_script_node)
workflow.add_node("guardian", symbolic_guardian_node)
workflow.add_node("reflector", self_correction_node)
workflow.add_node("human_escalation", human_layer_node)  # HumanLayer Integration

# Entry Point
workflow.set_entry_point("router")

# Conditional Routing based on Cynefin Domain
workflow.add_conditional_edges(
    "router",
    lambda state: state["cynefin_domain"],
    {
        "Complicated": "causal_analyst",
        "Complex": "bayesian_explorer",
        "Clear": "deterministic_runner",
        "Chaotic": "circuit_breaker",
        "Disorder": "human_escalation",
    }
)

# The Guardian Check
workflow.add_edge("causal_analyst", "guardian")
workflow.add_edge("bayesian_explorer", "guardian")
workflow.add_edge("deterministic_runner", "guardian")
workflow.add_edge("circuit_breaker", "human_escalation")

# Conditional Edge based on Guardian Verdict
def check_guardian_and_retries(state):
    if state["guardian_verdict"] == "approved":
        return "approved"
    if state["guardian_verdict"] == "rejected":
        if state["reflection_count"] >= state["max_reflections"]:
            return "escalate"  # Too many failures, ask human
        return "rejected"
    return "escalate"

workflow.add_conditional_edges(
    "guardian",
    check_guardian_and_retries,
    {
        "approved": END,
        "rejected": "reflector",
        "escalate": "human_escalation",
    }
)

# Human Escalation Logic
workflow.add_edge("reflector", "router")
workflow.add_conditional_edges(
    "human_escalation",
    route_after_human,  # Routes by HumanInteractionStatus
    {
        "router": "router",
        "end": END,
    }
)
```

### 3.2 The Causal Inference Engine (PyWhy Integration)

Discovery via causal-learn, estimation via DoWhy, refutation via placebo tests.

### 3.3 Frontend Architecture: The Epistemic Cockpit and Multi-Channel Feedback

CARF distinguishes between deep analysis and operational agility.

- The Epistemic Cockpit (Streamlit/React): Deep-dive verification, DAG visualization, posterior inspection (Streamlit cockpit available).
- Multi-Channel Feedback (HumanLayer): Approvals, clarifications, and notifications via Slack/Email/Teams.

Example approval flow:

1. Agent proposes action (e.g., "Shed 5MW load").
2. HumanLayer sends an interactive notification to Slack.
3. User chooses Approve, Reject, or Modify.
4. Response is injected back into the workflow.

### 3.4 Observability and Evaluation

- LangSmith tracing logs every step in the reasoning chain.
- Root signal evaluators score logical validity.
- HumanLayer metadata is captured in state; Kafka audit logging is available in the demo stack.

---

### 3.5 LLM Agentic Architecture

- Router: LLM (DeepSeek) or distilled model for Cynefin classification; entropy + confidence gate; fallback to Disorder/Human.
- Context assembly: LLM for query rewriting and context synthesis; deterministic filters for PII/policy.
- Planning: LLM for solver selection and task decomposition; constrained schemas and budgets.
- Domain agents:
  - Causal: DoWhy/EconML as source of truth; LLM assist for hypotheses/narration only.
  - Bayesian: PyMC/statistical core; LLM assist for probe design/narration.
  - Deterministic: Non-LLM; optional LLM for phrasing only.
  - Circuit breaker: Runbooks/rules; LLM for incident summaries; execution gated by policy/human.
- Guardian: Policy decisions remain symbolic/OPA/YAML; LLM may explain or suggest compliant alternatives.
- Reflector: LLM-guided self-correction with bounded retries; escalates after limit.
- HumanLayer: LLM for 3-point context (what/why/risk) in approvals; no auto-approval.
- Model selection: policy-based (cost/latency/risk); tiers (local/distilled vs. stronger); log model choice; prefer local for privacy/offline.
## 4. Implementation Roadmap and Strategy

### Phase 1: Foundation (Months 1-3)

- Deploy LangGraph with Cynefin router.
- Integrate HumanLayer for Disorder routing and approvals.
- Hire systems architect.

### Phase 2: Discovery and the Brain (Months 4-9)

- Implement PyWhy causal discovery.
- Deploy priority proof-of-concepts.

### Phase 3: The Guardian and Verification (Months 10-15)

- Implement OPA constraints (optional integration now available).
- Ensure HumanLayer approvals generate signed receipts and are persisted to the audit log (planned).

### Phase 4: Scaling and the Mesh (Months 16-24)

- Scale active inference agents and self-healing loops.
