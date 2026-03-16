# CYNEPIC Future Roadmap

> Last Updated: 2026-03-16
> Informed by: [`research.md`](../research.md) (neurosymbolic scaling research), [`docs/CARF_RSI_ANALYSIS.md`](CARF_RSI_ANALYSIS.md) (RSI architecture analysis)

## Vision

To become the standard architecture for **Epistemic AI Agent** systems — where AI knows what it doesn't know, improves through Supervised Recursive Refinement (SRR), and maintains formal safety guarantees at enterprise scale.

---

## Phase 18: SRR Hardening & Operational Intelligence (18A-D Complete)

Closes the 4 gaps identified by the RSI architecture analysis. Implements operational monitoring across all platform views.

### 18A: Drift Detection Service ✅
- `DriftDetector` service with KL-divergence monitoring over rolling windows
- Baseline established from first 100 observations, checks every 50 queries
- `/monitoring/drift` API endpoint + Developer View MonitoringPanel
- Benchmark H40: ≥90% sensitivity for >5% routing shift
- **Research basis:** RSI Analysis §9 Gap #1; research.md §6.6

### 18B: Automated Bias Auditing ✅
- `BiasAuditor` service with chi-squared domain distribution test
- Quality score disparity and Guardian verdict approval rate analysis
- `/monitoring/bias-audit` API endpoint + Governance View MonitoringPanel
- Benchmark H41: ≥90% bias detection accuracy
- **Research basis:** RSI Analysis §7d; research.md §6.3

### 18C: Plateau Detection in Retraining ✅
- `RouterRetrainingService.check_convergence()` with epsilon threshold
- Detects plateau (3+ consecutive epochs <0.5% improvement), regression, and productive improvement
- `/monitoring/convergence` API endpoint
- Benchmark H42: ≥90% plateau detection accuracy
- **Research basis:** RSI Analysis §7c

### 18D: ChimeraOracle StateGraph Integration ✅
- `chimera_fast_path_node` wired into LangGraph StateGraph
- Guardian enforcement on fast-path outputs (closes AP-7, AP-10)
- EvaluationService scoring at chimera node
- Fallback to full causal_analyst on low reliability
- Benchmark H43: 100% Guardian enforcement rate
- **Research basis:** RSI Analysis §9 Gap #4; research.md §1.3

### 18E: Scalable Inference Strategy
- Configurable inference modes: `full` (MCMC), `approximate` (variational), `cached` (pre-computed)
- Mode selection tied to deployment profiles (research/staging/production)
- Posterior distribution caching for repeated query patterns
- **Research basis:** research.md §1.1.3, §2.1, §5.1

### 18F: Research — Multi-Agent Collaborative Discovery
- Agent specialization for variable subsets in high-dimensional causal discovery
- Collaborative graph structure voting via consensus
- Distributed hypothesis testing across agent pool
- **Research basis:** research.md §1.2, §4.1; BCD Nets [3]

---

## Short-Term Goals (v0.6 — v0.8)

### 1. Advanced Simulation Arena
- **DAG Builder**: Drag-and-drop interface for constructing causal DAGs via ReactFlow
- **Batch Mode**: 100+ parallel scenario execution (asyncio optimization)
- **Export**: PDF/PPTX simulation reports with causal DAGs, confidence intervals, and audit trail
- **Counterfactual Playground**: Interactive Pearl Level-3 reasoning via the Phase 17 counterfactual engine

### 2. Federated Causal Learning
- Learn causal structures across deployments (e.g., factory sites) without sharing raw data
- Privacy-preserving via differential privacy or secure aggregation
- Federated Graph Learning module with governance compliance (GDPR Art. 22)
- **Research basis:** research.md §3.3; Federated Learning & EU AI Act [10]

### 3. Enhanced Guardian — Governance-as-a-Service (GaaS)
- **Compliance Templates**: Pre-built OPA policies for GDPR, EU AI Act, HIPAA, SOX
- **Dynamic Policy Updates**: Hot-swap policy bundles without service downtime
- **Multi-Tenant Isolation**: Policy namespacing for enterprise-scale deployments
- **Adaptive Trust Scoring**: Agent-level trust scores based on historical compliance
- **Research basis:** research.md §1.2 (GaaS concepts), §3.3, §3.5

### 4. LLM-as-a-Judge Quality Gating
- Separate, stronger LLM (e.g., Claude) grades primary agent reasoning
- Cross-validated against DeepEval scores for consistency
- Automatic escalation on judge disagreement
- Integrates with H-Neuron sentinel for hallucination triangulation

### 5. Operational Intelligence Dashboard
- Real-time drift monitoring (from 18A)
- Bias audit reports (from 18B)
- Retraining convergence curves (from 18C)
- Cost intelligence trends (from existing PRICE service)
- System health topology (dependency graph with status indicators)

---

## Medium-Term Goals (v0.9 — v1.0)

### 1. Neuro-Symbolic Core 2.0
- Replace standard routing with **Active Inference** loop (Minimize Free Energy)
- Dynamic resource allocation based on query complexity cost estimation
- BCD Nets integration for scalable variational Bayesian causal discovery
- Hardware-aware inference scheduling (GPU vs CPU path selection)
- **Research basis:** research.md §1.1.2 (BCD Nets [3]), §5.3

### 2. Multi-Modal Context Ingestion
- PDF contracts → causal variable extraction via document processor
- Image evidence → feature extraction for causal models
- IoT sensor streams → time-series causal discovery
- All modalities flow through EpistemicState with provenance tracking

### 3. Scalable Compliance Engine
- Automated compliance mapping: regulation text → CSL rules (LLM-assisted)
- Formal verification of policy set consistency (Z3 SAT solving at scale)
- Cross-regulation conflict detection (e.g., GDPR vs SOX retention requirements)
- **Research basis:** research.md §3.3; EU AI Act compliance [9]

### 4. Enterprise Graph Intelligence
- Neo4j-backed causal knowledge graph with cross-session learning
- Automatic DAG merging from multiple analyses
- Organizational knowledge accumulation with version control
- Graph-based impact analysis for policy changes

---

## Long-Term Vision (v1.0+)

### 1. Autonomous Experimental Design
- Agentic systems that proactively design interventions to reduce causal uncertainty
- Integration with the What-If Simulation Framework for hypothesis generation
- Automated A/B test design from causal models
- **Research basis:** research.md §4.4

### 2. Distributed Policy Orchestration
- Multi-agent frameworks to manage and resolve conflicts across multi-domain policies
- Real-time policy negotiation between organizational units
- Consensus-based conflict resolution with audit trail
- **Research basis:** research.md §4.4

### 3. Quantum-Enhanced Methods (Research Track)
- Quantum-accelerated Bayesian sampling for high-dimensional posteriors
- Quantum annealing for causal DAG search optimization
- Hybrid classical-quantum inference pipeline
- **Research basis:** research.md §1.3 (Future Directions)

### 4. Causal Foundation Models
- Domain-specific causal priors learned from enterprise data
- Transfer learning across causal graphs in related domains
- Integration with existing LLM foundation models for causal chain-of-thought
- **Research basis:** research.md §1.3 (Future Directions)

---

## Research Alignment Matrix

| Research Recommendation | Roadmap Component | Timeline |
|---|---|---|
| Layered causal analysis (fast + rigorous) | 18D ChimeraOracle integration | Phase 18 |
| Augmented governance (LLM + symbolic) | GaaS (Short-term §3) | v0.6-0.8 |
| Continuous evaluation | 18A-C Drift/Bias/Plateau | Phase 18 |
| Multi-agent causal discovery | 18F + NeSy Core 2.0 | v0.9-1.0 |
| Scalable Bayesian inference | 18E + Active Inference | v0.9-1.0 |
| Federated learning | Federated Causal Learning | v0.6-0.8 |
| Formal policy verification | Scalable Compliance Engine | v0.9-1.0 |
| Hardware-accelerated inference | NeSy Core 2.0 | v0.9-1.0 |
| Privacy-preserving analytics | Federated Learning + GDPR | v0.6-0.8 |

---

## How to Contribute

We welcome RFCs (Requests for Comments)!
1. Check `issues` for "Good First Issue"
2. Review [`CONTRIBUTING.md`](../CONTRIBUTING.md)
3. See [`docs/CARF_RSI_ANALYSIS.md`](CARF_RSI_ANALYSIS.md) for safety alignment requirements
4. All contributions must pass the benchmark suite (39 hypotheses) and realism quality gate
