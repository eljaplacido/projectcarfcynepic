# Great Barrier Reef Rescue Plan — CARF Application Planning Document

**Date:** 2026-03-12
**Status:** Planning
**Source:** `gbr_feasibility_analysis.md` — GBR Rescue Plan 2030–2050

---

## 1. Use Case Summary

Model, analyze, and support decision-making for a Great Barrier Reef (GBR) rescue plan spanning 2030–2050. The analysis question:

> *"With what combination of policy, technology, restoration, and adaptation measures can the GBR's ecological function, biodiversity, and connected human systems be stabilized or partially restored during 2030–2050, given that global warming has already exceeded the critical threshold for coral reefs?"*

This is CARF's **first cross-domain environmental scenario** — it naturally spans Complicated (causal intervention effects), Complex (ecosystem uncertainty, tipping points), Chaotic (past-threshold crisis), and Disorder (unknown cascading effects) simultaneously.

---

## 2. Existing CARF Capabilities That Apply

### 2.1 Ready to Use Today

| # | Capability | Component | GBR Application |
|---|-----------|-----------|-----------------|
| 1 | **Causal Inference (DoWhy)** | `src/services/causal.py` | Estimate ATE of interventions (coral planting, heat-resistant deployment) on coral cover, fish biomass |
| 2 | **Bayesian Inference (PyMC)** | `src/services/bayesian.py` | Model uncertainty in recovery rates, tipping point probabilities, belief updating with monitoring data |
| 3 | **Circuit Breaker** | `src/workflows/graph.py` | Tipping point alerts when thresholds exceeded (coral cover < critical %) |
| 4 | **What-If Simulation** | `src/services/simulation.py` | Compare intervention scenarios across 20-year horizon; 18+ generators already exist |
| 5 | **Guardian Policies** | `src/services/guardian.py` | Environmental governance rules, escalation policies |
| 6 | **CSL Policy Engine** | `src/services/csl_policy_service.py` | Deterministic policy enforcement (e.g., "DENY if coral_cover < 10%") |
| 7 | **Scenario Registry** | `demo/scenarios.json` | 14 scenarios registered; pattern established for new entries |
| 8 | **ChimeraOracle** | `src/services/chimera_oracle.py` | Fast probabilistic predictions for real-time monitoring dashboard |
| 9 | **Audit Trail & Lineage** | `src/services/audit.py` | Provenance tracking for ecological data and decisions |
| 10 | **Causal World Model (Phase 17)** | `src/services/causal_world_model.py` | SCM evaluation, do-calculus interventions, counterfactual reasoning |
| 11 | **Counterfactual Engine (Phase 17)** | `src/services/counterfactual_engine.py` | "What if we had deployed heat-resistant coral 5 years earlier?" |
| 12 | **Neurosymbolic Engine (Phase 17)** | `src/services/neurosymbolic_engine.py` | Symbolic grounding of ecological rules, shortcut detection in reasoning chains |
| 13 | **H-Neuron Sentinel (Phase 17)** | `src/services/h_neuron_interceptor.py` | Hallucination detection on ecological predictions |
| 14 | **NeSy-Augmented RAG (Phase 17)** | `src/services/rag_service.py` | Vector + graph + symbolic retrieval for GBR literature |
| 15 | **Governance Graph** | `src/services/governance_graph_service.py` | Neo4j-backed knowledge graph for ecological relationships |

### 2.2 Compatibility Assessment

| CARF Feature | GBR Fit | Notes |
|-------------|---------|-------|
| Cynefin Router | ✅ Native | Classifies sub-questions to domains |
| DoWhy Causal Engine | ✅ Native | ATE estimation with confounders |
| PyMC Bayesian Engine | ✅ Native | Posterior belief on recovery rates |
| Circuit Breaker | ✅ Native | Threshold-based crisis escalation |
| Guardian Policies | ✅ Native | Environmental governance rules |
| What-If Simulations | ✅ Native | Multi-scenario comparison |
| Data Lineage | ✅ Native | Audit trail for ecological data |
| Feedback Loop Modeling | ⚠️ Partial | DAGs are acyclic; cyclic feedback via iterated simulation |
| Multi-Domain Routing | ❌ Gap | Single `cynefin_domain` field; GBR needs array |

---

## 3. New Capabilities Required

### 3.1 Critical Gaps

#### Gap 1: Multi-Domain Scenario Routing
**Severity:** High — architectural change
**Problem:** Current `demo/scenarios.json` schema uses `"cynefin_domain": "Complicated"` (single string). The Cynefin router classifies queries into one domain. GBR requires simultaneous analysis across Complicated + Complex + Chaotic + Disorder.

**Changes required:**
- `demo/scenarios.json` — Add `cynefin_domains` (array) field alongside existing `cynefin_domain`
- `src/workflows/graph.py` — Extend router to decompose multi-domain queries into sub-queries, route each to appropriate handler, and merge results
- `src/core/state.py` — `EpistemicState` may need a `domain_decomposition` field to track which sub-answer came from which domain
- `src/api/routers/analysis.py` — Response model should include per-domain breakdown

**Effort:** ~5 days
**Refactoring risk:** Medium — router changes affect all scenarios, needs backward compatibility with single-domain entries

#### Gap 2: GBR Data Generator
**Severity:** Medium — new feature, no refactoring
**Problem:** No ecological data generator exists. Need synthetic coral reef data with known causal structure for DoWhy analysis.

**Changes required:**
- `src/services/simulation.py` — Add `generate_coral_reef_data()` function following existing generator pattern

**Data schema:**
```
Treatment:  heat_resistant_coral_deployment (0–1)
Outcome:    coral_cover_change_percent (-100 to +50)
Covariates: sea_temperature_anomaly (°C), water_quality_index (0–1),
            fishing_pressure (0–1), reef_structural_diversity (0–1)
Modifiers:  region (Cairns|Townsville|Mackay|Whitsundays),
            reef_zone (inner|mid|outer)
Known ATE:  ~+8% coral cover per unit deployment
            (heterogeneous: stronger in cooler zones)
```

**Effort:** ~3 days

#### Gap 3: GBR Scenario Registry & Payload
**Severity:** Low — configuration, no code changes
**Changes required:**
- `demo/scenarios.json` — New entry with `cynefin_domains: ["Complicated", "Complex", "Chaotic"]`
- `demo/payloads/coral_reef_rescue.json` — Scenario payload with treatment/outcome/covariates definition and causal DAG

**Effort:** ~1 day

### 3.2 Enhancement Gaps

#### Gap 4: Marine Environmental Policy Scaffold
**Severity:** Medium — new policies, no code changes
**Changes required:**
- `config/policies.yaml` or new CSL policies in `config/policies/` — Environmental thresholds:
  - `coral_cover < 15%` → escalate to crisis response
  - `sea_temperature_anomaly > 2.0°C` → circuit breaker activation
  - `fishing_pressure > 0.7` → restrict fishing recommendations
  - CSRD E4 (Biodiversity) and E1 (Climate) alignment rules

**Effort:** ~2 days

#### Gap 5: GBR Causal Graph for Neo4j
**Severity:** Medium — data setup, no code changes
**Changes required:**
- Seed script or migration to populate Neo4j with GBR causal structure:
  - ~30 variables across 5 categories (Climate, Coral, Biodiversity, Human, Interventions)
  - 3 causal chains (primary ecological, cascade, economic)
  - 3 feedback loops (reinforcing × 2, balancing × 1)
- NeSy engine can then ground symbolic facts from graph via `_ground_in_graph()`

**Effort:** ~2 days

#### Gap 6: Feedback Loop Modeling
**Severity:** Low — workaround exists
**Problem:** DoWhy requires DAGs (acyclic). GBR has 3 feedback loops (cyclic).
**Workaround:** Model feedback via iterated epoch-based simulation — run causal analysis per epoch, feed outputs as inputs to next epoch. Phase 17's `CausalWorldModel.simulate()` already supports multi-step forward simulation with this pattern.
**Full fix (optional):** Add explicit feedback loop detection and epoch-unrolling to simulation service.

**Effort:** ~2 days (optional)

#### Gap 7: Time-Horizon Support (20-Year Epoch Simulation)
**Severity:** Low — extension of existing capability
**Changes required:**
- `src/services/simulation.py` — Add epoch-based simulation mode (e.g., 4 × 5-year epochs)
- Bayesian belief updating between epochs with simulated monitoring data

**Effort:** ~2 days

#### Gap 8: GBR Context for Phase 17 Services
**Severity:** Low — configuration/prompting
**Changes required:**
- SCM definitions for GBR variables in causal world model
- NeSy knowledge base seeded with ecological rules (e.g., "coral bleaching occurs when sea temperature anomaly > 1°C")
- RAG corpus with GBR policy documents (GBR 2050 Sustainability Plan, AIMS reports)

**Effort:** ~2 days

---

## 4. Refactoring Assessment

### 4.1 Required Refactoring

| Area | Current State | Required Change | Risk |
|------|--------------|-----------------|------|
| **Cynefin Router** | Single-domain classification | Multi-domain decomposition + merge | Medium — must preserve backward compat with 14 existing scenarios |
| **Scenario Schema** | `cynefin_domain: string` | Add `cynefin_domains: string[]` (optional, fallback to single) | Low — additive change |
| **EpistemicState** | Single domain result | Optional `domain_decomposition` dict | Low — additive field |

### 4.2 No Refactoring Needed

| Area | Why |
|------|-----|
| Causal Engine | Works as-is with new data generator |
| Bayesian Engine | Standard posterior inference |
| Guardian / CSL | Add policies, no code changes |
| Simulation Service | Add generator following existing pattern |
| Phase 17 Services | Work with any domain; just need GBR-specific context |
| RAG Service | Ingest GBR documents into existing pipeline |
| Audit / Lineage | Domain-agnostic, works out of the box |

---

## 5. Phased Implementation Plan

### Phase 1: Core Scenario (Complicated Domain) — ~5 days

**Goal:** GBR causal analysis working end-to-end with synthetic data

| Task | File(s) | Days |
|------|---------|------|
| `generate_coral_reef_data()` | `src/services/simulation.py` | 2 |
| Scenario registry entry | `demo/scenarios.json` | 0.5 |
| Scenario payload with causal DAG | `demo/payloads/coral_reef_rescue.json` | 0.5 |
| Environmental Guardian policies | `config/policies.yaml` | 1 |
| Unit tests for data generator | `tests/unit/test_coral_reef_data.py` | 1 |

**Deliverable:** `"What is the causal effect of heat-resistant coral deployment on coral cover?"` returns valid DoWhy ATE estimate.

### Phase 2: Bayesian Uncertainty Layer (Complex Domain) — ~3 days

**Goal:** Epistemic uncertainty quantification for ecosystem recovery

| Task | File(s) | Days |
|------|---------|------|
| Bayesian priors for recovery rate, tipping probability | Payload config | 1 |
| Epoch-based belief updating with monitoring data | `src/services/simulation.py` | 1.5 |
| Integration tests | `tests/unit/test_gbr_bayesian.py` | 0.5 |

**Deliverable:** `"How confident should we be that intervention X prevents tipping point?"` returns posterior distribution with credible intervals.

### Phase 3: Multi-Domain Integration — ~5 days

**Goal:** Cross-domain routing and feedback loop modeling

| Task | File(s) | Days |
|------|---------|------|
| Multi-domain router (decompose → route → merge) | `src/workflows/graph.py` | 3 |
| Schema extension (`cynefin_domains` array) | `demo/scenarios.json`, state models | 0.5 |
| Feedback loop epoch-unrolling | `src/services/simulation.py` | 1 |
| Cross-domain integration tests | `tests/unit/test_gbr_multidomain.py` | 0.5 |

**Deliverable:** Single GBR query decomposes across Complicated + Complex + Chaotic domains, returns unified analysis.

### Phase 4: Knowledge & Governance — ~4 days

**Goal:** Full ecological knowledge base + compliance

| Task | File(s) | Days |
|------|---------|------|
| Neo4j GBR causal graph seed | Migration script | 1 |
| NeSy KB ecological rules | Configuration | 0.5 |
| CSL policies for CSRD E4/E1 | `config/policies/` | 1 |
| RAG corpus ingestion (GBR documents) | Data pipeline | 1 |
| Benchmark hypotheses (H40-H42) | Tests + scenarios | 0.5 |

**Deliverable:** End-to-end GBR analysis with symbolic grounding, graph traversal, policy compliance, and audit trail.

---

## 6. Effort Summary

| Phase | Days | Dependencies |
|-------|------|-------------|
| Phase 1: Core Scenario | 5 | None |
| Phase 2: Bayesian Layer | 3 | Phase 1 data generator |
| Phase 3: Multi-Domain | 5 | Phase 1 scenario entry |
| Phase 4: Knowledge & Gov | 4 | Phase 1 + Neo4j running |
| **Total** | **17** | Phases 2–4 partially parallelizable |

**Realistic timeline:** ~12–15 days with parallelization.

---

## 7. Causal DAG Structure

```
Global Temperature Rise → Sea Temperature Anomaly → Coral Heat Stress → Coral Cover Change
                                                                              ↑
Heat-Resistant Coral Deployment ─────────────────────────────────────────────┘
Water Quality Index ──────────────────────────────┬───────────────────────────┘
Fishing Pressure ─────────────────────────────────┘
Reef Structural Diversity ────────────────────────┘
Region → Sea Temperature Anomaly, Water Quality Index
Reef Zone → Sea Temperature Anomaly

Coral Cover Change → Fish Biomass → Fishing Income, Food Security
Coral Cover Change → Tourism Revenue
Coral Cover Change → Coastal Protection
```

**Feedback loops (modeled via epoch iteration):**
1. Coral death → fish decline → increased fishing pressure → faster collapse
2. Reef degradation → food stress → agriculture expansion → deforestation → warming
3. Coral decline → restoration investment → local recovery (weakly balancing)

---

## 8. New Benchmark Hypotheses

| ID | Hypothesis | Domain | Metric |
|----|-----------|--------|--------|
| H40 | Environmental CATE — causal effect estimation accuracy for ecological interventions vs known ground truth ATE | Complicated | ATE error < 15% |
| H41 | Multi-Domain Routing — correct domain classification when sub-questions span multiple Cynefin domains | Cross-domain | F1 > 0.85 |
| H42 | Feedback Loop Detection — identification of reinforcing/balancing loops in causal structures | Complex | Precision > 0.80 |

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Multi-domain router breaks existing scenarios | Medium | High | Backward-compat: single `cynefin_domain` still works; array is opt-in |
| Ecological data generator produces unrealistic data | Low | Medium | Validate against published GBR monitoring data distributions |
| Feedback loops create instability in epoch simulation | Medium | Medium | Cap iteration count; convergence checks between epochs |
| Neo4j unavailable in some deployments | High | Low | Graceful degradation already built into Phase 17 |
| Scope creep into full ecological modeling platform | Medium | High | Stick to CARF's decision-intelligence scope; ecological fidelity is secondary to analytical depth |

---

## 10. Success Criteria

1. GBR scenario runs end-to-end: query → Cynefin classification → causal analysis → Guardian check → response
2. DoWhy ATE estimate within 15% of known ground truth (±1.2% of +8% true effect)
3. Bayesian posterior updates correctly with simulated monitoring epochs
4. Multi-domain query decomposes and merges results from ≥2 Cynefin domains
5. Guardian escalates when coral_cover < 15% threshold
6. H-Neuron sentinel catches low-confidence ecological predictions
7. All new code has ≥90% test coverage
8. Benchmark hypotheses H40-H42 pass
