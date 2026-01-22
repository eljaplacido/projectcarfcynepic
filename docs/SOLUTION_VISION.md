# Solution Vision: Complex-Adaptive Reasoning Fabric (CARF)

**Version:** 2.0 (Target State)  
**Date:** 2026-01-16  
**Status:** Living Document

---

## 1. Executive Summary & Vision

**CARF** is a production-grade **Neuro-Symbolic-Causal** agentic system designed to bridge the "trust gap" in modern AI. As the industry transitions from generative text models to autonomous agents, CARF addresses the fundamental epistemic deficit of LLMs: their inability to distinguish knowing from guessing, causation from correlation, and policy from preference.

**The Vision:** To create an "Epistemic Cockpit"—a unified decision-support platform that acts not just as a chatbot, but as a reasoning partner that can audit its own logic, verify causality, and operate safely within complex, high-stakes environments (e.g., supply chain, finance, critical infrastructure).

---

## 2. Solution Architecture

The solution is architected as a **4-Layer Cognitive Stack**, enforcing separation of concerns between routing, reasoning, memory, and verification.

### High-Level Diagram

```mermaid
graph TD
    User[User / External System] --> IO[Input/Output Gateway]
    IO --> L1[Layer 1: Sense-Making Router]
    
    subgraph "Layer 2: Cognitive Mesh (The Agents)"
        L1 -- "Clear" --> AgentRule[Deterministic Automation]
        L1 -- "Complicated" --> AgentCausal[Causal Analyst (DoWhy)]
        L1 -- "Complex" --> AgentBayes[Bayesian Explorer (PyMC)]
        L1 -- "Chaotic" --> AgentSafe[Circuit Breaker]
        L1 -- "Disorder" --> AgentHuman[Human Escalation]
    end
    
    subgraph "Layer 3: Reasoning Services (State & Memory)"
        AgentCausal <--> DB_Graph[(Neo4j: Causal DAGs)]
        AgentBayes <--> DB_Prob[(Probabilistic Store)]
        AllAgents <--> DB_Audit[(Kafka/Audit Log)]
    end
    
    subgraph "Layer 4: Verifiable Action (The Guardian)"
        AgentRule --> Guardian
        AgentCausal --> Guardian
        AgentBayes --> Guardian
        Guardian{Policy Check} -- "Approved" --> Action[Execute Action]
        Guardian -- "Rejected" --> Reflector[Self-Correction Loop]
        Guardian -- "High Risk" --> Human[HumanLayer Approval]
    end
```

### Key Architectural Components

1.  **Frontend (The Cockpit)**: A responsive, React-based Single Page Application (SPA) providing role-based views.
2.  **Backend (The Engine)**: Python/FastAPI serving the LangGraph orchestration layer.
3.  **Data Layer**:
    *   **Neo4j**: Storing structural causal models (DAGs).
    *   **Vector Store**: For semantic context and memory.
    *   **Audit Log**: Immutable record of decisions and reasoning paths.

---

## 3. Detailed Feature Specifications

### 3.1 Neuro-Symbolic Core
*   **Cynefin Routing**: Automatically classifies queries into Clear, Complicated, Complex, Chaotic, or Disorder domains based on entropy and semantic analysis.
*   **Epistemic Markers**: Every system response is tagged with confidence levels and reasoning mode (e.g., "Inferred via Causal Discovery" vs. "Retrieved from Policy").

### 3.2 Causal Inference Engine
*   **DAG Discovery**: Algorithms (PC, FCI) to discover causal structures from observational data.
*   **Effect Estimation**: Quantifying impact (Average Treatment Effect) using DoWhy/EconML.
*   **Refutation Testing**: "Stress testing" conclusions by introducing placebo treatments or random common causes to verify robustness.

### 3.3 Bayesian Active Inference
*   **Belief Updating**: maintaining probabilistic distributions for uncertain variables.
*   **Active Probing**: Generating "safe-to-fail" experiments to reduce uncertainty (Information Gain).

### 3.4 The Guardian (Safety & Policy)
*   **Deterministic Guardrails**: Policies defined in OPA/YAML that strictly forbid unsafe actions.
*   **Human-in-the-Loop**: Seamless escalation to humans via Slack/Email for high-stakes approvals or disambiguation.
*   **Self-Healing**: A "Reflector" loop that attempts to self-correct plans rejected by the Guardian before giving up.

---

## 4. User Experience (UI/UX) Vision

The user interface is termed the **Epistemic Cockpit**. It transforms the "black box" of AI into a "glass box" of reasoning.

### 4.1 Technology Stack
*   **Framework**: React (Vite) + TypeScript.
*   **Styling**: Tailwind CSS + shadcn/ui for a premium, clean aesthetic.
*   **Visualization**: ReactFlow (Interactive DAGs) + Recharts (Probabilistic Distributions).

### 4.2 Application Modes (Personas)

#### A. The Analyst View (End-User)
*   **Goal**: Decision support and execution.
*   **Key Features**:
    *   **Natural Language Query**: "Why is churn increasing?"
    *   **Scenario Builder**: Sliders to adjust variables (Treatment) and see predicted outcomes (Effect).
    *   **Approval Inbox**: Notification center for reviewing agent-proposed actions.
    *   **Visual Reasoning**: Live view of the active Causal DAG with highlighted paths.

#### B. The Engineer View (Developer)
*   **Goal**: Debugging and optimization.
*   **Key Features**:
    *   **Execution Trace**: Vertical timeline of LangGraph steps (Router -> Agent -> Guardian).
    *   **State Inspector**: Full JSON view of the agent state at each step.
    *   **Performance Metrics**: Latency breakdown per node.
    *   **Policy Debugger**: See exactly which policy rule triggered a rejection.

#### C. The Executive View (Stakeholder)
*   **Goal**: Trust and alignment.
*   **Key Features**:
    *   **KPI Dashboard**: High-level metrics monitored by the system.
    *   **Compliance Scorecard**: % of decisions requiring human intervention.
    *   **Impact Attribution**: "System saved $X via causal optimization."

### 4.3 Design Aesthetics
*   **Theme**: "Cyber-Physical Control Center". Dark mode by default, high-contrast accent colors for various Cynefin domains (e.g., Green=Clear, Orange=Complex, Red=Chaotic).
*   **Interactivity**: Everything is clickable. Clicking a node in a DAG shows its marginal probability distribution.
*   **Motion**: Smooth layout transitions (Framer Motion) when switching between reasoning modes.

---

## 5. Backend & Data Implementations

### 5.1 Backend Services
*   **API**: FastAPI (Python 3.11+) exposing REST endpoints for Query, Scenario, and History.
*   **Orchestrator**: LangGraph for stateful, cyclic multi-agent workflows.
*   **Human Layer**: Methods for suspending execution while waiting for asynchronous human feedback.

### 5.2 Database Features
*   **Graph Database (Neo4j)**:
    *   Stores `Nodes` (Variables) and `Relationships` (Causal Links).
    *   Supports versioning of Causal Models (DAG evolution over time).
*   **Dataset Registry (File/S3)**:
    *   Storage for observational datasets (CSV/Parquet).
    *   Metadata tagging (Timeframe, Source, Quality).
*   **Audit Store**:
    *   Full traceability of "Who requested what, how did we decide, who approved it."

---

## 6. Security & Governance Features
*   **RBAC**: Role-Based Access Control for viewing sensitive scenarios.
*   **PII Sanity**: Automatic deterministic filtering of PII before sending context to LLMs.
*   **Circuit Breakers**: Hard-stop mechanisms for "Chaotic" domains or detected hallucinations.

## 7. Roadmap to Vision
1.  **Platform UIX**: Migration from Streamlit to React/Vite Cockpit.
2.  **Multi-Tenancy**: Org-level workspaces.
3.  **Federated Learning**: Learning causal structures across multiple isolated datasets.
