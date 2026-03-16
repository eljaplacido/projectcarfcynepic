# CARF/CYNEPIC Intellectual Property Documentation

**Version:** 1.1
**Date:** 2026-03-16
**Owner:** Cisuregen  
**License:** Business Source License 1.1 (BSL)  
**Copyright:** © 2026 Cisuregen. All rights reserved.

---

## Purpose

This document serves as the **definitive intellectual property registry** for the CARF (Complex-Adaptive Reasoning Fabric) / CYNEPIC (CYNefin-EPIstemic Cockpit) platform. It provides:

1. A complete **end-to-end solution description** sufficient to reconstruct the system
2. An exhaustive **classification of every component** as Cisuregen proprietary IP, integration layer IP, or third-party dependency
3. The **legal IP protection framework** governing the project

> [!IMPORTANT]
> All original code, architecture, configuration, and documentation in this repository are the intellectual property of **Cisuregen**, licensed under the **Business Source License 1.1** (BSL). On February 19, 2030, the license auto-converts to Apache License 2.0.

---

## Table of Contents

- [1. Solution Overview](#1-solution-overview)
- [2. IP Protection Framework](#2-ip-protection-framework)
- [3. Proprietary IP — Tier 1: Core Innovation (Crown Jewels)](#3-proprietary-ip--tier-1-core-innovation-crown-jewels)
- [4. Proprietary IP — Tier 2: Differentiating Assets](#4-proprietary-ip--tier-2-differentiating-assets)
- [5. Proprietary IP — Tier 3: Supporting Assets](#5-proprietary-ip--tier-3-supporting-assets)
- [6. Integration Layer IP](#6-integration-layer-ip)
- [7. Third-Party Dependencies (NOT Cisuregen IP)](#7-third-party-dependencies-not-cisuregen-ip)
- [8. Runtime Service Dependencies (NOT Cisuregen IP)](#8-runtime-service-dependencies-not-cisuregen-ip)
- [9. External Concepts & Frameworks Referenced (NOT Cisuregen IP)](#9-external-concepts--frameworks-referenced-not-cisuregen-ip)
- [10. Complete File-Level IP Map](#10-complete-file-level-ip-map)
- [11. End-to-End Solution Reconstruction Guide](#11-end-to-end-solution-reconstruction-guide)
- [12. IP Summary Statistics](#12-ip-summary-statistics)

---

## 1. Solution Overview

CARF is a production-grade **Neuro-Symbolic-Causal** agentic platform that bridges the "trust gap" in AI decision-making. The platform classifies every query by inherent complexity using the Cynefin Framework, routes it to the appropriate analytical engine, and enforces organizational policies before allowing execution.

### Architecture: 4-Layer Cognitive Stack

```
Layer 1 — Sense-Making Router (Cynefin Router)
    └─ Classifies query complexity across 5 domains
    
Layer 2 — Cognitive Mesh (Domain-Specific Engines)
    ├─ Clear         → Deterministic Automation
    ├─ Complicated   → Causal Inference (DoWhy/EconML)
    ├─ Complex       → Bayesian Active Inference (PyMC)
    ├─ Chaotic       → Circuit Breaker
    └─ Disorder      → Human Escalation (HumanLayer)

Layer 3 — Reasoning Services (State & Memory)
    ├─ EpistemicState (context propagation)
    ├─ Experience Buffer (semantic memory)
    ├─ Agent Memory (cross-session persistence)
    ├─ Neo4j (causal DAG storage)
    └─ Kafka (audit trail)

Layer 4 — Verifiable Action (The Guardian)
    ├─ Policy Check (YAML + CSL + OPA)
    ├─ Smart Reflector (self-correction)
    └─ Human-in-the-Loop (HumanLayer escalation)
```

### Product Names (Cisuregen Trademarks)

| Name | Description |
|------|-------------|
| **CARF** | Complex-Adaptive Reasoning Fabric — the core framework |
| **CYNEPIC** | CYNefin-EPIstemic Cockpit — the dashboard/product brand |
| **Cisuregen** | The parent company/entity |

---

## 2. IP Protection Framework

### License: Business Source License 1.1

| Attribute | Value |
|-----------|-------|
| **Licensor** | Cisuregen |
| **Licensed Work** | CARF — Complex-Adaptive Reasoning Fabric |
| **Copyright** | © 2026 Cisuregen |
| **Change Date** | February 19, 2030 |
| **Change License** | Apache License, Version 2.0 |
| **Commercial Contact** | licensing@cisuregen.com |

### What the BSL Permits

| Use | Permitted? |
|-----|-----------|
| Development & Testing | ✅ Free |
| Personal Use | ✅ Free |
| Academic Research | ✅ Free |
| Non-Commercial Distribution | ✅ Free (under BSL) |
| Production Use | ❌ Requires Commercial License |
| Hosted/SaaS Offering | ❌ Requires Commercial License |
| Embedding in Commercial Products | ❌ Requires Commercial License |

### Legal Documents

| Document | Path | Purpose |
|----------|------|---------|
| **Primary License** | [`LICENSE`](../LICENSE) | BSL 1.1 full terms |
| **Commercial Terms** | [`COMMERCIAL_LICENSE.md`](../COMMERCIAL_LICENSE.md) | Production use licensing |
| **Contributor Agreement** | [`CLA.md`](../CLA.md) | IP assignment for contributions |
| **Third-Party Attribution** | [`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) | Dependency license summary |
| **NOTICE File** | [`NOTICE`](../NOTICE) | Third-party copyright attributions |
| **Security Policy** | [`SECURITY.md`](../SECURITY.md) | Vulnerability reporting scope |

### Copyright Header

All Cisuregen-authored source files carry:
```
# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
```

---

## 3. Proprietary IP — Tier 1: Core Innovation (Crown Jewels)

> [!CAUTION]
> These components represent Cisuregen's highest-value intellectual property. They embody novel architectural patterns, algorithms, and workflows that are extremely difficult to replicate and form the primary competitive moat.

### 3.1 Cynefin Router — Epistemic Complexity Classifier

| Property | Value |
|----------|-------|
| **File** | [`src/workflows/router.py`](../src/workflows/router.py) |
| **IP Classification** | 🔴 **Cisuregen Proprietary** |
| **LOC** | ~617 |

**What it is:** A dual-mode query complexity classifier that combines LLM-based semantic analysis with a DistilBERT neural classifier, augmented by Shannon entropy calculations. It classifies every input into one of 5 Cynefin domains (Clear, Complicated, Complex, Chaotic, Disorder).

**What makes it novel:**
- Hybrid classification approach (LLM + DistilBERT + entropy scoring)
- Data-structure hint detection (identifies tabular data parameters for downstream engines)
- Domain confidence scoring with entropy analysis
- Feedback-driven retraining pipeline for continuous improvement
- Pattern-matched domain routing with configurable thresholds

**IP Scope:** The entire classification process, the specific combination of entropy analysis → domain classification → engine selection, and the retraining workflow are Cisuregen's proprietary methods.

---

### 3.2 Guardian Layer — Context-Aware Policy Engine

| Property | Value |
|----------|-------|
| **File** | [`src/workflows/guardian.py`](../src/workflows/guardian.py) |
| **IP Classification** | 🔴 **Cisuregen Proprietary** |
| **LOC** | ~841 |

**What it is:** A multi-source policy enforcement engine that evaluates every system action against organizational policies before execution. It uses domain-adjusted thresholds, risk decomposition, and multi-layer evaluation (YAML → CSL → OPA).

**What makes it novel:**
- Context-aware policy thresholds that adjust based on the classified Cynefin domain
- Risk decomposition into severity levels (low, medium, high, critical)
- Multi-source policy evaluation cascade (YAML rules → CSL formal verification → OPA/Rego)
- Currency-aware financial guardrails with FX normalization
- Deterministic, auditable decision trail for every evaluation
- Fail-closed safety design (blocks on evaluation failure)

**IP Scope:** The specific architecture of context-aware, multi-source policy gating with domain-adjusted thresholds and deterministic audit trail generation.

---

### 3.3 LangGraph Orchestration — The Reasoning Fabric

| Property | Value |
|----------|-------|
| **File** | [`src/workflows/graph.py`](../src/workflows/graph.py) |
| **IP Classification** | 🔴 **Cisuregen Proprietary** |
| **LOC** | ~680 |

**What it is:** The stateful workflow graph that wires together the Cynefin Router → Domain-Specific Engines → Guardian → Smart Reflector into a self-correcting cognitive loop. This is the "fabric" that makes CARF work.

**What makes it novel:**
- Specific wiring of epistemic routing → domain engines → policy gating → reflection
- Self-correcting loop (Guardian rejection → Reflector repair → retry)
- CSL-Core context injection before Guardian evaluation
- Governance node integration at <1ms P95 latency
- State propagation via EpistemicState across all nodes

**IP Scope:** The specific stateful graph architecture, the node arrangement, and the self-correcting feedback loop.

---

### 3.4 EpistemicState — Unified Decision Context

| Property | Value |
|----------|-------|
| **File** | [`src/core/state.py`](../src/core/state.py) |
| **IP Classification** | 🔴 **Cisuregen Proprietary** |
| **LOC** | ~300 |

**What it is:** The central state schema that carries epistemic context (confidence levels, reasoning mode, data quality, audit trail) through every stage of the processing pipeline. It translates unstructured queries into structured hypotheses.

**What makes it novel:**
- Epistemic markers (confidence, reasoning mode, evidence tracking)
- Context propagation through the entire workflow graph
- Structured hypothesis formulation from unstructured text
- Integrated data quality assessment

---

## 4. Proprietary IP — Tier 2: Differentiating Assets

> [!IMPORTANT]
> These components provide strong competitive differentiation. They implement sophisticated analytical capabilities that combine multiple disciplines (statistics, causal inference, Bayesian methods, NLP) in novel ways.

### 4.1 Causal Inference Engine

| Property | Value |
|----------|-------|
| **File** | [`src/services/causal.py`](../src/services/causal.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** (uses third-party libraries DoWhy/EconML internally) |
| **LOC** | ~1,006 |

**What Cisuregen owns:** The orchestration that combines LLM-assisted causal discovery with DoWhy/EconML statistical validation, the specific DAG discovery workflow, refutation testing methodology, and confidence assessment framework.

**What Cisuregen does NOT own:** The DoWhy library (Microsoft, MIT), the EconML library (Microsoft, MIT), the causal-learn library (CMU, Apache 2.0).

---

### 4.2 Bayesian Active Inference Engine

| Property | Value |
|----------|-------|
| **File** | [`src/services/bayesian.py`](../src/services/bayesian.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** (uses third-party library PyMC internally) |
| **LOC** | ~730 |

**What Cisuregen owns:** The epistemic/aleatoric uncertainty decomposition workflow, the exploration probe generation, the belief updating interface, and the integration with the Cynefin Complex domain routing.

**What Cisuregen does NOT own:** The PyMC library (PyMC team, Apache 2.0), the ArviZ library (ArviZ team, Apache 2.0).

---

### 4.3 Transparency & Compliance Service

| Property | Value |
|----------|-------|
| **File** | [`src/services/transparency.py`](../src/services/transparency.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~1,036 |

**What Cisuregen owns:** EU AI Act compliance engine, agent chain-of-thought tracing, reliability assessment framework, DeepEval quality metrics integration, data quality assessment, and data lineage tracking.

---

### 4.4 Simulation & What-If Engine

| Property | Value |
|----------|-------|
| **File** | [`src/services/simulation.py`](../src/services/simulation.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~1,437 |

**What Cisuregen owns:** 6 realistic data generators with known causal structure, realism assessment scoring, multi-scenario comparison framework, and intervention simulation.

---

### 4.5 Smart Reflector — Self-Correction Service

| Property | Value |
|----------|-------|
| **File** | [`src/services/smart_reflector.py`](../src/services/smart_reflector.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~300 |

**What Cisuregen owns:** The hybrid heuristic + LLM repair workflow for policy violations, the observability integration, and the retry/escalation logic.

---

### 4.6 Governance Service Suite (MAP-PRICE-RESOLVE)

| Property | Value |
|----------|-------|
| **Files** | [`governance_service.py`](../src/services/governance_service.py), [`governance_graph_service.py`](../src/services/governance_graph_service.py), [`governance_board_service.py`](../src/services/governance_board_service.py), [`governance_export_service.py`](../src/services/governance_export_service.py), [`federated_policy_service.py`](../src/services/federated_policy_service.py), [`cost_intelligence_service.py`](../src/services/cost_intelligence_service.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **Combined LOC** | ~3,000+ |

**What Cisuregen owns:**
- **MAP** — Entity extraction, domain keyword matching, Neo4j triple store integration
- **PRICE** — Financial LLM token pricing, risk exposure calculations, ROI analysis
- **RESOLVE** — Cross-domain conflict detection, federated policy management, resolution workflows
- Board lifecycle management, policy export/import, compliance scoring (EU AI Act, CSRD, GDPR, ISO 27001)

---

### 4.7 TLA+ Formal Verification Specifications

| Property | Value |
|----------|-------|
| **Files** | [`tla_specs/EscalationProtocol.tla`](../tla_specs/EscalationProtocol.tla), [`tla_specs/StateGraph.tla`](../tla_specs/StateGraph.tla) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~600 |

**What Cisuregen owns:** The specific formal verification models that prove safety properties of the escalation protocol and state graph transitions.

**Note:** TLA+ is an open specification language (Leslie Lamport). The formal specifications themselves are Cisuregen IP.

---

### 4.8 Experience Buffer — Semantic Memory

| Property | Value |
|----------|-------|
| **File** | [`src/services/experience_buffer.py`](../src/services/experience_buffer.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~250 |

**What Cisuregen owns:** The semantic memory retrieval architecture, TF-IDF fallback mechanism, and domain pattern aggregation.

---

### 4.9 Causal World Model — Structural Causal Models (Phase 17)

| Property | Value |
|----------|-------|
| **File** | [`src/services/causal_world_model.py`](../src/services/causal_world_model.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~600+ |

**What Cisuregen owns:** The SCM evaluation engine with topological ordering, do-calculus intervention logic, forward simulation with noise injection, Pearl's 3-step counterfactual (Abduction → Action → Prediction), OLS learning from data + causal graph, and LLM-assisted probabilistic simulation fallback.

**What Cisuregen does NOT own:** Pearl's causal inference theory (academic), OLS regression (standard statistics).

---

### 4.10 Counterfactual Engine — Pearl Level-3 Reasoning (Phase 17)

| Property | Value |
|----------|-------|
| **File** | [`src/services/counterfactual_engine.py`](../src/services/counterfactual_engine.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~500+ |

**What Cisuregen owns:** Natural language counterfactual parsing, SCM-based reasoning with LLM fallback, multi-scenario comparison with ranking, but-for causal attribution with importance scoring, and result caching architecture.

---

### 4.11 Neurosymbolic Engine — Neural-Symbolic Reasoning Loop (Phase 17)

| Property | Value |
|----------|-------|
| **File** | [`src/services/neurosymbolic_engine.py`](../src/services/neurosymbolic_engine.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~700+ |

**What Cisuregen owns:** The tight neural-symbolic integration loop (LLM fact extraction → symbolic forward-chaining → rule validation → shortcut detection), knowledge base with typed facts and confidence scoring, CSL policy rule import, Neo4j graph grounding, and violation correction workflow.

---

### 4.12 H-Neuron Sentinel — Hallucination Detection (Phase 17)

| Property | Value |
|----------|-------|
| **File** | [`src/services/h_neuron_interceptor.py`](../src/services/h_neuron_interceptor.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~400+ |

**What Cisuregen owns:** The weighted signal fusion architecture for hallucination risk assessment (8 signals with configurable weights), proxy mode implementation, Cynefin domain-aware activation, and environment-based feature flagging. The mechanistic mode placeholder (PyTorch hooks for open-weights models) is also Cisuregen IP once implemented.

**What Cisuregen does NOT own:** The H-Neurons concept (THUNLP research), PyTorch hooks API (Meta, BSD-3).

---

### 4.13 Supervised Recursive Refinement (SRR) — Architectural Concept

| Property | Value |
|----------|-------|
| **File** | [`docs/CARF_RSI_ANALYSIS.md`](CARF_RSI_ANALYSIS.md) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~380 |

**What Cisuregen owns:** The Supervised Recursive Refinement (SRR) concept — a safety-first approach to system self-improvement where improvement cycles are bounded by formal invariants, policy enforcement, human oversight gates, and audit trails. This includes the RSI spectrum positioning analysis, the five independent containment mechanisms design, and the architectural principle that improvement components are structurally separate from safety enforcement components.

---

### 4.14 Insights Service — Persona-Specific Intelligence

| Property | Value |
|----------|-------|
| **File** | [`src/services/insights_service.py`](../src/services/insights_service.py) |
| **IP Classification** | 🟡 **Cisuregen Proprietary** |
| **LOC** | ~650 |

**What Cisuregen owns:** The persona-based insight generation (Analyst, Developer, Executive), actionable recommendation engine with effort badges, and analysis roadmap generation.

---

## 5. Proprietary IP — Tier 3: Supporting Assets

> These components provide moderate competitive value as configuration, tooling, and interface assets.

### 5.1 Configuration & Policy Assets

| Asset | Path | IP Classification |
|-------|------|-------------------|
| Agent configurations | [`config/agents.yaml`](../config/agents.yaml) | 🟢 Cisuregen Proprietary |
| Guardian YAML policies | [`config/policies.yaml`](../config/policies.yaml) | 🟢 Cisuregen Proprietary |
| CSL formal policy definitions | [`config/policies/`](../config/policies/) (5 `.csl` files) | 🟢 Cisuregen Proprietary |
| Federated domain policies | [`config/federated_policies/`](../config/federated_policies/) (5 YAML files) | 🟢 Cisuregen Proprietary |
| Policy scaffold templates | [`config/policy_scaffolds/`](../config/policy_scaffolds/) (5 YAML files) | 🟢 Cisuregen Proprietary |
| Governance board templates | [`config/governance_boards/`](../config/governance_boards/) (4 JSON files) | 🟢 Cisuregen Proprietary |
| Prompt engineering templates | [`config/prompts.yaml`](../config/prompts.yaml) | 🟢 Cisuregen Proprietary |

### 5.2 Benchmark Suite

| Asset | Path | IP Classification |
|-------|------|-------------------|
| Benchmark strategy | [`carf_benchmarking_strategy.md`](../carf_benchmarking_strategy.md) | 🟢 Cisuregen Proprietary |
| Technical benchmarks (39 hypotheses) | [`benchmarks/`](../benchmarks/) (~95 files) | 🟢 Cisuregen Proprietary |
| Synthetic DGP generators | Embedded in benchmark scripts | 🟢 Cisuregen Proprietary |
| 456-query router test set | Embedded in router benchmark | 🟢 Cisuregen Proprietary |

### 5.3 Demo Scenarios & Sample Data

| Asset | Path | IP Classification |
|-------|------|-------------------|
| 17 demo scenarios | [`demo/`](../demo/) (~32 files) | 🟢 Cisuregen Proprietary |
| Industry-specific causal datasets | Embedded in demo scenarios | 🟢 Cisuregen Proprietary |

### 5.4 CYNEPIC Cockpit (React Frontend)

| Asset | Path | IP Classification |
|-------|------|-------------------|
| 56 React components | [`carf-cockpit/src/components/`](../carf-cockpit/src/components/) | 🟢 Cisuregen Proprietary |
| 4 custom hooks | [`carf-cockpit/src/hooks/`](../carf-cockpit/src/hooks/) | 🟢 Cisuregen Proprietary |
| API service layer | [`carf-cockpit/src/services/`](../carf-cockpit/src/services/) | 🟢 Cisuregen Proprietary |
| 26 frontend test files | [`carf-cockpit/src/__tests__/`](../carf-cockpit/src/__tests__/) | 🟢 Cisuregen Proprietary |

**Dashboard views owned by Cisuregen:**
- Analyst View (query input, Cynefin classification, causal DAG, Guardian panel, transparency panel, insights)
- Developer View (execution trace, performance metrics, state snapshots, agent comparison, log streaming)
- Executive View (KPI dashboard, action summary, compliance overview)
- Governance View (spec map, cost intelligence, policy federation, compliance audit, semantic graph, policy ingestion)

### 5.5 Additional Proprietary Service Files

| Service | File | IP Classification |
|---------|------|-------------------|
| Agent Memory | [`agent_memory.py`](../src/services/agent_memory.py) | 🟢 Cisuregen Proprietary |
| Agent Tracker | [`agent_tracker.py`](../src/services/agent_tracker.py) | 🟢 Cisuregen Proprietary |
| Chat Service | [`chat.py`](../src/services/chat.py) | 🟢 Cisuregen Proprietary |
| Data Loader | [`data_loader.py`](../src/services/data_loader.py) | 🟢 Cisuregen Proprietary |
| Dataset Store | [`dataset_store.py`](../src/services/dataset_store.py) | 🟢 Cisuregen Proprietary |
| Developer Service | [`developer.py`](../src/services/developer.py) | 🟢 Cisuregen Proprietary |
| Document Processor | [`document_processor.py`](../src/services/document_processor.py) | 🟢 Cisuregen Proprietary |
| Embedding Engine | [`embedding_engine.py`](../src/services/embedding_engine.py) | 🟢 Cisuregen Proprietary |
| Evaluation Service | [`evaluation_service.py`](../src/services/evaluation_service.py) | 🟢 Cisuregen Proprietary |
| Explanation Builder | [`explanation_builder.py`](../src/services/explanation_builder.py) | 🟢 Cisuregen Proprietary |
| Explanations Service | [`explanations.py`](../src/services/explanations.py) | 🟢 Cisuregen Proprietary |
| File Analyzer | [`file_analyzer.py`](../src/services/file_analyzer.py) | 🟢 Cisuregen Proprietary |
| Human Layer Service | [`human_layer.py`](../src/services/human_layer.py) | 🟢 Cisuregen Proprietary |
| Improvement Suggestions | [`improvement_suggestions.py`](../src/services/improvement_suggestions.py) | 🟢 Cisuregen Proprietary |
| Kafka Audit | [`kafka_audit.py`](../src/services/kafka_audit.py) | 🟢 Cisuregen Proprietary |
| Neo4j Service | [`neo4j_service.py`](../src/services/neo4j_service.py) | 🟢 Cisuregen Proprietary |
| OPA Service | [`opa_service.py`](../src/services/opa_service.py) | 🟢 Cisuregen Proprietary |
| Policy Refinement Agent | [`policy_refinement_agent.py`](../src/services/policy_refinement_agent.py) | 🟢 Cisuregen Proprietary |
| Policy Scaffold Service | [`policy_scaffold_service.py`](../src/services/policy_scaffold_service.py) | 🟢 Cisuregen Proprietary |
| RAG Service | [`rag_service.py`](../src/services/rag_service.py) | 🟢 Cisuregen Proprietary |
| Router Retraining Service | [`router_retraining_service.py`](../src/services/router_retraining_service.py) | 🟢 Cisuregen Proprietary |
| Schema Detector | [`schema_detector.py`](../src/services/schema_detector.py) | 🟢 Cisuregen Proprietary |
| Visualization Engine | [`visualization_engine.py`](../src/services/visualization_engine.py) | 🟢 Cisuregen Proprietary |

### 5.6 API Layer

| Component | Path | IP Classification |
|-----------|------|-------------------|
| FastAPI entry point | [`src/main.py`](../src/main.py) | 🟢 Cisuregen Proprietary |
| 14 API router modules | [`src/api/routers/`](../src/api/routers/) | 🟢 Cisuregen Proprietary |
| API data models (80+ endpoints) | [`src/api/models.py`](../src/api/models.py) | 🟢 Cisuregen Proprietary |
| Security middleware | [`src/api/middleware.py`](../src/api/middleware.py) | 🟢 Cisuregen Proprietary |
| Library API (notebook wrappers) | [`src/api/library.py`](../src/api/library.py) | 🟢 Cisuregen Proprietary |
| Dependency injection | [`src/api/deps.py`](../src/api/deps.py) | 🟢 Cisuregen Proprietary |

### 5.7 MCP Server (Cognitive Tools Interface)

| Component | Path | IP Classification |
|-----------|------|-------------------|
| MCP server | [`src/mcp/server.py`](../src/mcp/server.py) | 🟢 Cisuregen Proprietary |
| 7 MCP tool modules | [`src/mcp/tools/`](../src/mcp/tools/) (bayesian, causal, guardian, memory, oracle, reflector, router) | 🟢 Cisuregen Proprietary |

### 5.8 Utility Layer

| Component | Path | IP Classification |
|-----------|------|-------------------|
| Telemetry | [`src/utils/`](../src/utils/) | 🟢 Cisuregen Proprietary |
| Caching & cache registry | [`src/utils/`](../src/utils/) | 🟢 Cisuregen Proprietary |
| Circuit breaker | [`src/utils/`](../src/utils/) | 🟢 Cisuregen Proprietary |
| Currency normalization | [`src/utils/`](../src/utils/) | 🟢 Cisuregen Proprietary |

### 5.9 Test Suite

| Component | Path | IP Classification |
|-----------|------|-------------------|
| 53 unit test files | [`tests/unit/`](../tests/unit/) | 🟢 Cisuregen Proprietary |
| DeepEval quality tests | [`tests/deepeval/`](../tests/deepeval/) | 🟢 Cisuregen Proprietary |
| E2E gold standard tests | [`tests/e2e/`](../tests/e2e/) | 🟢 Cisuregen Proprietary |
| Integration tests | [`tests/integration/`](../tests/integration/) | 🟢 Cisuregen Proprietary |

### 5.10 Documentation (Architectural IP)

| Document | Path | IP Classification |
|----------|------|-------------------|
| 30+ technical documents | [`docs/`](../docs/) | 🟢 Cisuregen Proprietary |
| Main README | [`README.md`](../README.md) | 🟢 Cisuregen Proprietary |
| Developer reference | [`DEV_REFERENCE.md`](../DEV_REFERENCE.md) | 🟢 Cisuregen Proprietary |
| Agent specifications | [`AGENTS.md`](../AGENTS.md) | 🟢 Cisuregen Proprietary |
| Current status | [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) | 🟢 Cisuregen Proprietary |

### 5.11 Infrastructure

| Component | Path | IP Classification |
|-----------|------|-------------------|
| Dockerfile | [`Dockerfile`](../Dockerfile) | 🟢 Cisuregen Proprietary |
| Docker Compose (full stack) | [`docker-compose.yml`](../docker-compose.yml) | 🟢 Cisuregen Proprietary |
| Deployment profiles | [`src/core/deployment_profile.py`](../src/core/deployment_profile.py) | 🟢 Cisuregen Proprietary |
| CI/CD workflows | [`.github/`](../.github/) | 🟢 Cisuregen Proprietary |
| Scripts (training, generation) | [`scripts/`](../scripts/) (13 files) | 🟢 Cisuregen Proprietary |

---

## 6. Integration Layer IP

> [!NOTE]
> These components are **Cisuregen IP in terms of the adapter, workflow, and integration logic**, but they wrap or depend on external libraries or concepts. The external dependency itself is NOT Cisuregen IP.

### 6.1 CSL-Core Policy Service (Integration Adapter)

| Property | Value |
|----------|-------|
| **File** | [`src/services/csl_policy_service.py`](../src/services/csl_policy_service.py) |
| **IP Classification** | 🔵 **Integration Layer** — Adapter is Cisuregen IP; Z3 solver engine is external |
| **LOC** | ~765 |

**What Cisuregen owns:**
- The adapter code connecting CSL-Core to the Guardian Layer
- The 35 policy rule definitions (in `config/policies/*.csl`)
- The built-in Python evaluator that operates when CSL-Core Z3 is unavailable
- The fail-closed safety architecture
- The CSL Tool Guard service ([`csl_tool_guard.py`](../src/services/csl_tool_guard.py))

**What Cisuregen does NOT own:**
- CSL-Core as a standalone policy language project (external)
- The Z3 SMT solver (Microsoft, MIT License)

---

### 6.2 ChimeraOracle — Fast Causal Predictions (Integration Adapter)

| Property | Value |
|----------|-------|
| **File** | [`src/services/chimera_oracle.py`](../src/services/chimera_oracle.py) |
| **IP Classification** | 🔵 **Integration Layer** — CARF-specific implementation is Cisuregen IP; the CausalForestDML concept originates from EconML |
| **LOC** | ~632 |

**What Cisuregen owns:**
- The specific model training workflow (distillation from heavy causal analysis to fast scoring)
- The drift detection mechanisms
- The integration with the CARF pipeline and Cynefin routing
- The MCP tool wrappers for agentic access
- Pre-trained model management and versioning

**What Cisuregen does NOT own:**
- The CausalForestDML algorithm (from EconML, Microsoft, MIT License)
- The EconML library itself

---

## 7. Third-Party Dependencies (NOT Cisuregen IP)

> [!WARNING]
> These are open-source libraries used by CARF. They are NOT Cisuregen intellectual property. All have permissive licenses (MIT, Apache 2.0, BSD-3-Clause, ISC) compatible with BSL 1.1.

### Core Orchestration

| Package | License | Owner |
|---------|---------|-------|
| LangGraph | MIT | LangChain, Inc. |
| LangChain | MIT | LangChain, Inc. |
| LangChain OpenAI | MIT | LangChain, Inc. |
| LangChain Anthropic | MIT | LangChain, Inc. |
| LangChain Google GenAI | Apache 2.0 | LangChain, Inc. |

### Causal & Bayesian Libraries

| Package | License | Owner |
|---------|---------|-------|
| DoWhy | MIT | Microsoft Corporation |
| EconML | MIT | Microsoft Corporation |
| causal-learn | Apache 2.0 | Center for Causal Discovery (CMU) |
| PyMC | Apache 2.0 | PyMC Development Team |
| ArviZ | Apache 2.0 | ArviZ Development Team |

### Machine Learning & NLP

| Package | License | Owner |
|---------|---------|-------|
| PyTorch | BSD-3-Clause | Meta Platforms, Inc. |
| Hugging Face Transformers | Apache 2.0 | Hugging Face, Inc. |
| Sentence Transformers | Apache 2.0 | UKP Lab, TU Darmstadt |
| scikit-learn | BSD-3-Clause | scikit-learn developers |
| pandas | BSD-3-Clause | pandas Development Team |

### API & Web Framework

| Package | License | Owner |
|---------|---------|-------|
| FastAPI | MIT | Sebastián Ramírez |
| Uvicorn | BSD-3-Clause | Encode OSS Ltd. |
| Pydantic | MIT | Samuel Colvin |

### Infrastructure Clients

| Package | License | Owner |
|---------|---------|-------|
| Neo4j Python Driver | Apache 2.0 | Neo4j, Inc. |
| Redis Client | BSD-3-Clause | Redis, Inc. |
| SQLAlchemy | MIT | Mike Bayer |
| Confluent Kafka | Apache 2.0 | Confluent, Inc. |

### Verification & Observability

| Package | License | Owner |
|---------|---------|-------|
| Z3 Solver | MIT | Microsoft Corporation |
| OpenTelemetry | Apache 2.0 | OpenTelemetry Authors |
| LangSmith | MIT | LangChain, Inc. |
| DeepEval | MIT | Confident AI |

### Frontend Libraries

| Package | License | Owner |
|---------|---------|-------|
| React | MIT | Meta Platforms, Inc. |
| ReactFlow | MIT | webkid GmbH |
| Recharts | MIT | Recharts Group |
| Plotly.js | MIT | Plotly, Inc. |
| Tailwind CSS | MIT | Tailwind Labs, Inc. |
| Vite | MIT | Evan You |
| Lucide React | ISC | Lucide Contributors |

### Other Utilities

| Package | License | Owner |
|---------|---------|-------|
| PyYAML | MIT | Kirill Simonov |
| python-dotenv | BSD-3-Clause | Saurabh Kumar |
| Tenacity | Apache 2.0 | Julien Danjou |
| HumanLayer | MIT | HumanLayer, Inc. |
| PyPDF | BSD-3-Clause | Mathieu Fenniak |
| openpyxl | MIT | Eric Gazoni / Charlie Clark |

> **License Compatibility:** 100% permissive stack — no copyleft (GPL/AGPL) in the direct dependency tree. Clean for BSL 1.1 → Apache 2.0 transition.

---

## 8. Runtime Service Dependencies (NOT Cisuregen IP)

These are external services used via network protocols. They are NOT distributed with CARF and are NOT Cisuregen IP.

| Service | License | Usage |
|---------|---------|-------|
| Neo4j Community Edition | GPL v3 (FOSS Exception) | Graph database (network service only, no GPL obligation transfer) |
| Apache Kafka | Apache 2.0 | Event streaming (network service) |
| Open Policy Agent (OPA) | Apache 2.0 | Policy evaluation (network service) |

---

## 9. External Concepts & Frameworks Referenced (NOT Cisuregen IP)

These are academic frameworks, theories, or methodologies that CARF builds upon. They are public domain knowledge, not proprietary to Cisuregen.

| Concept | Origin | How CARF Uses It |
|---------|--------|------------------|
| **Cynefin Framework** | Dave Snowden (Cognitive Edge) | Complexity classification domains (Clear, Complicated, Complex, Chaotic, Disorder) |
| **Shannon Entropy** | Claude Shannon (information theory) | Entropy-based confidence scoring in the Router |
| **Causal Inference Theory** | Judea Pearl (UCLA) | Foundational theory behind DAG discovery and ATE estimation |
| **Bayesian Inference** | Thomas Bayes / Pierre-Simon Laplace | Prior/posterior belief updating methodology |
| **EU AI Act** | European Parliament | Compliance framework mapped in Transparency Service |
| **CSRD / ESRS** | European Parliament | Sustainability reporting standards in Governance |
| **OWASP LLM Top 10** | OWASP Foundation | Security benchmark categories |
| **TLA+** | Leslie Lamport (Microsoft Research) | Formal specification language used for verification |
| **Model Context Protocol (MCP)** | Anthropic | Protocol standard for agentic tool exposure |

---

## 10. Complete File-Level IP Map

### Legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | Tier 1 — Core Innovation (Crown Jewels) |
| 🟡 | Tier 2 — Differentiating Assets |
| 🟢 | Tier 3 — Supporting Assets |
| 🔵 | Integration Layer (adapter is Cisuregen IP; core dependency is external) |
| ⬜ | Third-Party / Not Cisuregen IP |

### Source Code (`src/`)

```
src/
├── __init__.py                          🟢 Cisuregen
├── main.py                              🟢 Cisuregen
├── core/
│   ├── __init__.py                      🟢 Cisuregen
│   ├── state.py                         🔴 Cisuregen (EpistemicState)
│   ├── llm.py                           🟢 Cisuregen
│   ├── deployment_profile.py            🟢 Cisuregen
│   └── governance_models.py             🟡 Cisuregen
├── workflows/
│   ├── __init__.py                      🟢 Cisuregen
│   ├── graph.py                         🔴 Cisuregen (Orchestration Fabric)
│   ├── guardian.py                      🔴 Cisuregen (Policy Engine)
│   └── router.py                        🔴 Cisuregen (Cynefin Router)
├── services/
│   ├── __init__.py                      🟢 Cisuregen
│   ├── causal.py                        🟡 Cisuregen (wraps DoWhy/EconML)
│   ├── bayesian.py                      🟡 Cisuregen (wraps PyMC)
│   ├── chimera_oracle.py               🔵 Integration (wraps EconML CausalForestDML)
│   ├── csl_policy_service.py           🔵 Integration (wraps Z3/CSL-Core)
│   ├── csl_tool_guard.py               🔵 Integration
│   ├── transparency.py                  🟡 Cisuregen
│   ├── simulation.py                    🟡 Cisuregen
│   ├── smart_reflector.py               🟡 Cisuregen
│   ├── causal_world_model.py           🟡 Cisuregen (SCMs, do-calculus, Phase 17)
│   ├── counterfactual_engine.py        🟡 Cisuregen (Pearl Level-3, Phase 17)
│   ├── neurosymbolic_engine.py         🟡 Cisuregen (NeSy reasoning loop, Phase 17)
│   ├── h_neuron_interceptor.py         🟡 Cisuregen (Hallucination sentinel, Phase 17)
│   ├── governance_service.py            🟡 Cisuregen
│   ├── governance_graph_service.py      🟡 Cisuregen
│   ├── governance_board_service.py      🟡 Cisuregen
│   ├── governance_export_service.py     🟡 Cisuregen
│   ├── federated_policy_service.py      🟡 Cisuregen
│   ├── cost_intelligence_service.py     🟡 Cisuregen
│   ├── experience_buffer.py             🟡 Cisuregen
│   ├── insights_service.py              🟡 Cisuregen
│   ├── agent_memory.py                  🟢 Cisuregen
│   ├── agent_tracker.py                 🟢 Cisuregen
│   ├── chat.py                          🟢 Cisuregen
│   ├── data_loader.py                   🟢 Cisuregen
│   ├── dataset_store.py                 🟢 Cisuregen
│   ├── developer.py                     🟢 Cisuregen
│   ├── document_processor.py            🟢 Cisuregen
│   ├── embedding_engine.py              🟢 Cisuregen
│   ├── evaluation_service.py            🟢 Cisuregen
│   ├── explanation_builder.py           🟢 Cisuregen
│   ├── explanations.py                  🟢 Cisuregen
│   ├── file_analyzer.py                 🟢 Cisuregen
│   ├── human_layer.py                   🟢 Cisuregen
│   ├── improvement_suggestions.py       🟢 Cisuregen
│   ├── kafka_audit.py                   🟢 Cisuregen
│   ├── neo4j_service.py                 🟢 Cisuregen
│   ├── opa_service.py                   🟢 Cisuregen
│   ├── policy_refinement_agent.py       🟢 Cisuregen
│   ├── policy_scaffold_service.py       🟢 Cisuregen
│   ├── rag_service.py                   🟢 Cisuregen
│   ├── router_retraining_service.py     🟢 Cisuregen
│   ├── schema_detector.py               🟢 Cisuregen
│   └── visualization_engine.py          🟢 Cisuregen
├── api/
│   ├── __init__.py                      🟢 Cisuregen
│   ├── deps.py                          🟢 Cisuregen
│   ├── library.py                       🟢 Cisuregen
│   ├── middleware.py                     🟢 Cisuregen
│   ├── models.py                        🟢 Cisuregen
│   └── routers/ (14 router modules)     🟢 Cisuregen
├── mcp/
│   ├── __init__.py                      🟢 Cisuregen
│   ├── server.py                        🟢 Cisuregen
│   └── tools/ (7 tool modules)          🟢 Cisuregen
├── utils/ (6 utility modules)           🟢 Cisuregen
└── workflows/ (see above)
```

### Configuration (`config/`)

```
config/
├── agents.yaml                          🟢 Cisuregen
├── policies.yaml                        🟢 Cisuregen
├── prompts.yaml                         🟢 Cisuregen
├── policies/ (5 .csl files)             🟢 Cisuregen
├── federated_policies/ (5 YAML files)   🟢 Cisuregen
├── policy_scaffolds/ (5 YAML files)     🟢 Cisuregen
├── governance_boards/ (4 JSON files)    🟢 Cisuregen
└── opa/ (1 .rego file)                  🟢 Cisuregen
```

### Frontend (`carf-cockpit/src/`)

```
carf-cockpit/src/
├── App.tsx                              🟢 Cisuregen
├── components/carf/ (55 components)     🟢 Cisuregen
├── hooks/ (4 custom hooks)              🟢 Cisuregen
├── services/ (API client)               🟢 Cisuregen
├── types/ (TypeScript types)            🟢 Cisuregen
├── __tests__/ (26 test files)           🟢 Cisuregen
└── node_modules/                        ⬜ Third-Party
```

---

## 11. End-to-End Solution Reconstruction Guide

This section describes the complete system in sufficient detail to reconstruct the solution from first principles.

### Phase 1: Core State & Configuration

1. **EpistemicState** (`src/core/state.py`) — Define the central Pydantic state schema carrying query, domain classification, confidence, audit trail, and all intermediate results through the pipeline.
2. **LLM Configuration** (`src/core/llm.py`) — Multi-provider LLM abstraction supporting DeepSeek, OpenAI, Anthropic, Google GenAI with automatic fallback.
3. **Deployment Profiles** (`src/core/deployment_profile.py`) — Environment-aware presets (research/staging/production) controlling auth, CORS, rate limits.

### Phase 2: The Reasoning Fabric (Workflows)

4. **Cynefin Router** (`src/workflows/router.py`) — Implement dual-mode classifier:
   - LLM-based semantic analysis with structured prompts
   - DistilBERT neural classifier with confidence scoring
   - Shannon entropy calculation for domain uncertainty
   - Data-structure hint extraction (treatment, outcome, covariates)
   - Domain override tracking for retraining pipeline

5. **Domain Engines** (via `services/`):
   - Clear → Deterministic lookup and automation
   - Complicated → `causal.py` (DoWhy/EconML DAG discovery + ATE estimation + refutation)
   - Complex → `bayesian.py` (PyMC posterior inference + uncertainty decomposition)
   - Chaotic → Circuit breaker (emergency stop with human escalation)
   - Disorder → Human escalation via HumanLayer SDK

6. **Guardian Layer** (`src/workflows/guardian.py`) — Multi-layer policy engine:
   - YAML policy evaluation (attribute-based rules)
   - CSL-Core formal verification (Z3-backed, with built-in fallback)
   - OPA/Rego external policy evaluation
   - Risk decomposition and domain-adjusted thresholds
   - Currency-aware financial guardrails

7. **Graph Orchestration** (`src/workflows/graph.py`) — LangGraph StateGraph wiring:
   - Router → Domain Engine → Guardian → Output
   - Guardian rejection → Smart Reflector → Retry loop
   - CSL context injection before Guardian evaluation
   - Governance node integration (feature-flagged)

### Phase 3: Analytical Services

8. **Causal Inference** — LLM-assisted DAG discovery → DoWhy estimation → refutation testing → confidence assessment
9. **Bayesian Inference** — Prior specification → PyMC sampling → posterior analysis → epistemic/aleatoric decomposition
10. **ChimeraOracle** — CausalForestDML training → fast prediction (<100ms) → drift detection → model versioning
11. **Simulation Engine** — 6 data generators → multi-scenario comparison → realism assessment → what-if analysis
12. **Smart Reflector** — Hybrid heuristic + LLM repair for Guardian-rejected actions with observability

### Phase 4: Governance & Compliance

13. **MAP-PRICE-RESOLVE Framework**:
    - MAP: Entity extraction, domain keyword matching, Neo4j triple store
    - PRICE: LLM token pricing, risk exposure, ROI analysis
    - RESOLVE: Cross-domain conflict detection, federated policy management
14. **Compliance Scoring** — EU AI Act, CSRD, GDPR, ISO 27001 automated assessment
15. **Audit Trail** — Kafka-based immutable decision logging with cryptographic verification

### Phase 5: Memory & Intelligence

16. **Experience Buffer** — Sentence-transformer embeddings with TF-IDF fallback for semantic retrieval of past analyses
17. **Agent Memory** — Persistent cross-session memory with compaction and recall
18. **RAG Service** — In-memory retrieval-augmented generation for policy queries
19. **Embedding Engine** — all-MiniLM-L6-v2 sentence-transformer embeddings
20. **Insights Service** — Persona-specific recommendations, action items, and analysis roadmaps

### Phase 6: API & Interface

21. **FastAPI Backend** — 80+ REST endpoints across 14 router modules, SSE streaming, WebSocket logging
22. **Security Middleware** — API key auth, per-IP rate limiting, request size enforcement (profile-aware)
23. **MCP Server** — 18 cognitive tools exposed via Model Context Protocol for agentic integration
24. **React Cockpit** — 4-view dashboard (Analyst, Developer, Executive, Governance) with 56 components

### Phase 7: Quality & Verification

25. **TLA+ Specifications** — Formal verification of escalation protocol and state graph transitions
26. **Benchmark Suite** — 39 falsifiable hypotheses across 10 categories
27. **Test Suite** — 53 unit tests, DeepEval quality tests, E2E gold standard tests, integration tests

---

## 12. IP Summary Statistics

| Category | Count | IP Status |
|----------|-------|-----------|
| **Tier 1 Core Files** (Crown Jewels) | 4 files | 🔴 Cisuregen Proprietary |
| **Tier 2 Differentiating Services** | 17 files (+5 Phase 17) | 🟡 Cisuregen Proprietary |
| **Tier 3 Supporting Services** | 24 files | 🟢 Cisuregen Proprietary |
| **Integration Layer** | 3 files | 🔵 Adapter = Cisuregen; Core dependency = External |
| **API Routers** | 16 files (+2 Phase 17) | 🟢 Cisuregen Proprietary |
| **MCP Tools** | 7 files | 🟢 Cisuregen Proprietary |
| **React Components** | 58 files (+2 Phase 17) | 🟢 Cisuregen Proprietary |
| **Frontend Tests** | 26 files | 🟢 Cisuregen Proprietary |
| **Backend Tests** | 55+ files (+2 Phase 17) | 🟢 Cisuregen Proprietary |
| **Configuration/Policy Files** | 24 files | 🟢 Cisuregen Proprietary |
| **TLA+ Formal Specs** | 2 files | 🟡 Cisuregen Proprietary |
| **Benchmark Files** | ~95 files | 🟢 Cisuregen Proprietary |
| **Demo Scenarios** | ~32 files | 🟢 Cisuregen Proprietary |
| **Documentation** | 40+ files (+research analysis) | 🟢 Cisuregen Proprietary |
| **Scripts** | 13 files | 🟢 Cisuregen Proprietary |
| **Agent Skills** | 12 files | 🟢 Cisuregen Proprietary |
| **Trained Models** | 6 models (1 DistilBERT + 5 CausalForest) | 🟢 Cisuregen Proprietary |
| **Research Analysis** | 2 files (research.md, CARF_RSI_ANALYSIS.md) | 🟢 Cisuregen Proprietary |
| **Third-Party Dependencies** | ~50 packages | ⬜ NOT Cisuregen IP |
| **Runtime Services** | 3 services | ⬜ NOT Cisuregen IP |

### Total Cisuregen Original Code

| Metric | Approximate Count |
|--------|-------------------|
| Python source files (proprietary) | ~95+ files |
| TypeScript/React source files | ~90 files |
| Lines of proprietary Python logic | ~18,000+ LOC |
| Lines of proprietary TypeScript | ~12,000+ LOC |
| Configuration/policy assets | ~24 files |
| Documentation (architectural IP) | ~40 files |
| Trained model artifacts | 6 models |
| Agent skill definitions | 12 skills |

### Phase 18 IP Additions

| New Asset | Type | Classification |
|-----------|------|---------------|
| Drift Detector (KL-divergence monitoring) | Service | 🟢 Tier 3 |
| Bias Auditor (chi-squared fairness tests) | Service | 🟢 Tier 3 |
| Plateau Detection (convergence monitoring) | Enhancement | 🟢 Tier 3 (upgrade to existing) |
| ChimeraOracle StateGraph Integration | Enhancement | 🟡 Tier 2 (AP-7/AP-10 closure) |
| Monitoring API (7 endpoints) | API | 🟢 Tier 3 |
| MonitoringPanel (3-tab React component) | Frontend | 🟢 Tier 3 |
| Monitoring Benchmarks H40-H43 | Benchmarks | 🟢 Tier 3 |

### Phase 17 IP Additions

| New Asset | Type | Classification |
|-----------|------|---------------|
| Causal World Model (SCMs, do-calculus) | Service | 🟡 Tier 2 |
| Counterfactual Engine (Pearl Level-3) | Service | 🟡 Tier 2 |
| Neurosymbolic Engine (NeSy loop) | Service | 🟡 Tier 2 |
| H-Neuron Sentinel (hallucination detection) | Service | 🟡 Tier 2 |
| SRR Concept (Supervised Recursive Refinement) | Architectural IP | 🟡 Tier 2 |
| 3-layer NeSy-augmented RAG | Enhancement | 🟡 Tier 2 (upgrade to existing) |
| Firebase Auth middleware | Service | 🟢 Tier 3 |
| Cloud SQL connection factory | Service | 🟢 Tier 3 |
| World Model API (10 endpoints) | API | 🟢 Tier 3 |
| History API (3 endpoints) | API | 🟢 Tier 3 |

---

*This document is maintained by Cisuregen and should be updated with each major release. Last updated: 2026-03-16.*
