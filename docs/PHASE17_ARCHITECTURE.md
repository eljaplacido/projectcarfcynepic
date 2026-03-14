# Phase 17 — Causal World Models, Neurosymbolic AI & Advanced RAG

**Date:** 2026-03-12
**Status:** Implemented
**Components:** 6 new/enhanced services, 3 API routers, 10 endpoints, 154+ tests

---

## Architecture Overview

Phase 17 implements the convergence of causal reasoning, neurosymbolic AI, and world models as recommended by recent research ([1]-[34] in CAUSAL_NEUROSYMBOLIC_RESEARCH_EVALUATION.md). It adds three new cognitive layers to CARF's existing 4-layer architecture:

```
                    ┌─────────────────────────────────────────────┐
                    │          CARF Phase 17 Architecture          │
                    └─────────────────────────────────────────────┘

 Query ──→ Router ──→ Domain Agent ──→ H-Neuron Gate ──→ Guardian ──→ Response
                          │                  │
              ┌───────────┴──────────┐       │
              │                      │       │
    ┌─────────▼─────────┐  ┌────────▼───────▼──────────┐
    │  Causal World Model│  │  Neurosymbolic Engine      │
    │  - SCM Evaluation  │  │  - Knowledge Base          │
    │  - Simulation      │  │  - Forward Chaining        │
    │  - Counterfactual  │  │  - Shortcut Detection      │
    │  - Learning        │  │  - Graph Grounding         │
    └────────┬──────────┘  └────────┬───────────────────┘
             │                      │
    ┌────────▼──────────────────────▼───────────────────┐
    │         Neurosymbolic-Augmented RAG                │
    │  Layer 1: Vector (TF-IDF / Dense Embeddings)      │
    │  Layer 2: Graph (Neo4j Causal + Governance)       │
    │  Layer 3: Symbolic (Knowledge Base Facts + Rules)  │
    │  Fusion: Reciprocal Rank Fusion (RRF)             │
    └───────────────────────────────────────────────────┘
```

---

## Component Inventory

### 1. Causal World Model (`src/services/causal_world_model.py`)

**Research basis:** COMET [9], CausalARC [10], CWMI [12], CASSANDRA [25], Causal Cartographer [14]

Implements Structural Causal Models (SCMs) with:

| Feature | Implementation | Research Alignment |
|---------|---------------|-------------------|
| **SCM Evaluation** | Topological ordering + structural equation evaluation | Pearl's SCM framework |
| **do-Calculus Interventions** | `do(X=x)` overrides structural equations | Causal Cartographer [14] |
| **Forward Simulation** | N-step trajectory with noise injection | Clinical World Models [5] |
| **Counterfactual Reasoning** | Abduction → Action → Prediction (Pearl's 3-step) | CausalARC [10] |
| **Learning from Data** | OLS regression given known causal graph | COMET [9] |
| **LLM Fallback** | Probabilistic simulation when no SCM available | CASSANDRA [25] |

### 2. Counterfactual Engine (`src/services/counterfactual_engine.py`)

**Research basis:** Causal Cartographer [14], Beyond Generative AI [5], Think Before You Simulate [34]

| Feature | Description |
|---------|-------------|
| **Natural Language Parsing** | LLM extracts structured `CounterfactualQuery` from text |
| **SCM-Based Reasoning** | When data available, uses `CausalWorldModel.counterfactual()` |
| **LLM-Assisted Fallback** | Pearl's 3-step reasoning via prompted LLM |
| **Scenario Comparison** | Multi-intervention comparison with ranking |
| **Causal Attribution** | But-for causation tests with importance scoring |

### 3. Neurosymbolic Engine (`src/services/neurosymbolic_engine.py`)

**Research basis:** DeepGraphLog [19], ProSLM [29], CASSANDRA [25], Prototypical NeSy [21], KG for NeSy [30][31]

| Feature | Implementation | Research Alignment |
|---------|---------------|-------------------|
| **Knowledge Base** | Typed facts with confidence, deduplication | KG for NeSy [30] |
| **Forward Chaining** | Horn clause inference with confidence decay | ProSLM [29] |
| **LLM Fact Extraction** | Iterative extraction → KB → forward chain loop | CASSANDRA [25] |
| **Shortcut Detection** | Dependency graph analysis for skipped causal steps | Prototypical NeSy [21] |
| **Constraint Validation** | Symbolic rules validate LLM output | NeSy robustness [18] |
| **Graph Grounding** | Neo4j causal graph → symbolic facts | KG for NeSy [30][31] |
| **CSL Import** | CSL-Core policies as symbolic rules | CARF CSL framework |

### 4. H-Neuron Sentinel (`src/services/h_neuron_interceptor.py`)

**Research basis:** THUNLP H-Neurons (docs/H_NEURONS_INTEGRATION_EVALUATION.md)

Pre-delivery hallucination interception with two modes:

| Mode | Availability | Mechanism |
|------|-------------|-----------|
| **Proxy** (default) | Always | Fuses DeepEval scores, domain confidence, epistemic uncertainty, reflection count, response heuristics into unified risk score |
| **Mechanistic** | Requires PyTorch + local model | Forward-hook activation analysis on open-weights model (placeholder, ready for classifier training) |

Signal fusion weights:
- `deepeval_hallucination_risk`: 35%
- `confidence_risk` (1 - domain_confidence): 20%
- `epistemic_uncertainty`: 15%
- `reflection_risk`: 10%
- `irrelevancy_risk`: 7%
- `brevity_risk`: 5%
- `shallow_reasoning_risk`: 5%
- `verbosity_risk`: 3%

### 5. Neurosymbolic-Augmented RAG (`src/services/rag_service.py`)

**Research insight:** Highest contextual memory reliability through vector + graph + symbolic fusion [30][31]

Three-layer retrieval:

```
Layer 1: Vector Similarity
  ├── Dense embeddings (sentence-transformers) — primary
  └── TF-IDF (scikit-learn) — fallback

Layer 2: Graph Structural Traversal
  ├── Neo4j Causal Graph — variable neighborhoods, causal paths
  ├── Neo4j Governance Graph — triple search, domain relationships
  └── Historical Analysis — past session results

Layer 3: Symbolic Knowledge Base
  ├── NeSy KB facts — entity/attribute/value matching
  └── NeSy KB rules — symbolic rule surfacing

Fusion: Reciprocal Rank Fusion (RRF)
  ├── Vector weight: 0.6 (configurable)
  ├── Graph weight: 0.4 (configurable)
  └── Boost: 1.25x for domain-matching results
```

### 6. EpistemicState Extensions (`src/core/state.py`)

| Field | Type | Purpose |
|-------|------|---------|
| `counterfactual_evidence` | `CounterfactualEvidence` | Stores factual/counterfactual outcomes, causal attributions |
| `neurosymbolic_evidence` | `NeurosymbolicEvidence` | Stores derived facts, rule chain, shortcut warnings |
| `context["h_neuron_*"]` | dict entries | H-Neuron risk score, flagged status, mode |

---

## API Endpoints

All mounted under `/world-model` prefix:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/counterfactual` | Counterfactual reasoning from natural language |
| POST | `/counterfactual/compare` | Multi-scenario comparison |
| POST | `/counterfactual/attribute` | Causal attribution with but-for tests |
| POST | `/simulate` | Forward simulation with do-calculus interventions |
| POST | `/neurosymbolic/reason` | Full neural-symbolic reasoning loop |
| POST | `/neurosymbolic/validate` | Claim validation against symbolic KB |
| GET | `/h-neuron/status` | H-Neuron sentinel configuration and status |
| POST | `/h-neuron/assess` | Run hallucination risk assessment |
| POST | `/retrieve/neurosymbolic` | Neurosymbolic-augmented retrieval |
| POST | `/analyze-deep` | Combined CARF + counterfactual + NeSy + simulation |

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|---------|
| `test_phase17_world_model.py` | 80 | SCM evaluation, simulation, counterfactuals, learning, KB, rules, operators, state, router |
| `test_phase17_integration.py` | 37 | H-Neuron sentinel, RAG↔NeSy, Causal↔NeSy, E2E coherence, KB↔RAG, retrieval modes |
| **Total Phase 17** | **117** | All services, models, API routes, cross-service interconnections |

---

## Research Alignment Matrix

| Research Finding | CARF Implementation | Component |
|-----------------|--------------------|-----------|
| COMET [9] — Causal world models prevent spurious correlations | `CausalWorldModel.learn_from_data()` fits SCMs from data | causal_world_model.py |
| CausalARC [10] — SCM-based abstract reasoning | `CausalWorldModel.counterfactual()` Pearl's 3-step | causal_world_model.py |
| CWMI [12] — Embedding causal models in LLMs | `CausalWorldModelService.simulate_from_text()` LLM fallback | causal_world_model.py |
| Causal Cartographer [14] — Counterfactual world reasoning | `CounterfactualEngine.reason_from_text()` | counterfactual_engine.py |
| CASSANDRA [25] — LLM as knowledge prior for world models | `NeuralSymbolicReasoner._extract_facts()` LLM→KB loop | neurosymbolic_engine.py |
| ProSLM [29] — Formal logic for LLM QA | `KnowledgeBase.forward_chain()` + constraint validation | neurosymbolic_engine.py |
| Prototypical NeSy [21] — Anti-shortcut reasoning | `_detect_shortcuts()` dependency graph analysis | neurosymbolic_engine.py |
| KG for NeSy [30][31] — Knowledge graphs empower NeSy | `_ground_in_graph()` Neo4j → symbolic facts | neurosymbolic_engine.py |
| H-Neurons (THUNLP) — Mechanistic hallucination detection | `HNeuronSentinel.assess_hallucination_risk()` proxy + mechanistic | h_neuron_interceptor.py |
| Vector + Graph + Symbolic retrieval | `RAGService.retrieve_neurosymbolic_augmented()` | rag_service.py |

---

## Graceful Degradation

Every Phase 17 component degrades gracefully when dependencies are unavailable:

| Dependency | When Missing | Fallback |
|-----------|-------------|----------|
| Neo4j | Graph grounding returns empty facts | Vector-only RAG, no graph traversal |
| PyTorch | Mechanistic H-Neuron unavailable | Proxy mode signal fusion |
| LLM API key | Fact extraction fails | Empty facts, static KB rules only |
| scikit-learn | TF-IDF unavailable | Dense embeddings only |
| sentence-transformers | Dense embeddings unavailable | TF-IDF only |
| CSL policies | CSL import returns 0 | KB works with manually added rules |
