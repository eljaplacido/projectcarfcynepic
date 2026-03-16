# End-to-End Context Flow

> Last Updated: 2026-03-16 (Phase 17 complete, Phase 18 designed)

## Purpose
Describe how data and context move through CARF's 6-layer cognitive stack: Memory Augmentation → Router → RAG → Domain Agents → H-Neuron → Guardian → Governance → Reflector → HumanLayer, with full audit integration.

## High-Level Flow

```
1. Ingest         → User query + optional scenario/dataset context enters EpistemicState
2. Memory Aug     → Agent Memory retrieves similar past analyses → soft routing hints (0.03 weight)
3. Router         → Compute entropy; classify domain (LLM/DistilBERT); set confidence, domain, hypothesis
4. RAG Context    → 3-layer retrieval (Vector + Graph + Symbolic) via Reciprocal Rank Fusion
5. CSL Precheck   → CSL-Core policy pre-evaluation (context injection before domain agent)
6. Domain Agent   → Route by Cynefin domain (see below)
7. H-Neuron Gate  → Hallucination risk assessment via weighted signal fusion (8 signals)
8. Guardian       → Multi-layer policy check (YAML + CSL-Core + OPA); verdict = approved | rejected | escalate
9. Governance     → MAP-PRICE-RESOLVE: entity extraction, cost analysis, conflict detection, audit
10. Output        → Final response/action with audit trail, evaluation scores, and provenance
```

### Domain Agent Routing (Step 6)

| Domain | Agent | Engine | Phase 17 Enhancement |
|--------|-------|--------|---------------------|
| Clear | `deterministic_runner` | Lookup/automation | — |
| Complicated | `causal_analyst` | DoWhy/EconML | + Causal World Model (SCMs, counterfactuals) |
| Complex | `bayesian_explorer` | PyMC | + NeSy validation of Bayesian assumptions |
| Chaotic | `circuit_breaker` | Stabilize + escalate | — |
| Disorder | `human_escalation` | HumanLayer | — |

### Phase 17 Cognitive Extensions (between Steps 6-7)

When invoked by domain agents or via `/world-model/*` API:

```
Causal World Model:
  SCM Evaluation → do-Calculus Interventions → Forward Simulation → Counterfactual (Pearl 3-step)
                                                                      ↕
Neurosymbolic Engine:
  LLM Fact Extraction → Knowledge Base → Forward Chaining → Shortcut Detection → Constraint Validation
                           ↕                                       ↕
                      Neo4j Graph Grounding                  CSL Policy Rule Import
```

## State Propagation (EpistemicState)

### Core Fields
- `cynefin_domain`, `domain_confidence`, `domain_entropy`
- `current_hypothesis`, `reasoning_chain` (list of ReasoningStep)
- `proposed_action`, `guardian_verdict`, `policy_violations`
- `reflection_count` / `max_reflections` (SRR bound)
- `human_interaction_status`, `human_verification`, `human_override_instructions`
- `final_response`, `final_action`, `error`

### Phase 17 Additions
- `counterfactual_evidence` — Factual/counterfactual outcomes, causal attributions
- `neurosymbolic_evidence` — Derived facts, rule chain, shortcut warnings
- `context["h_neuron_*"]` — H-Neuron risk score, flagged status, mode
- `session_triples` — Governance semantic triples (MAP output)
- `cost_breakdown` — LLM token costs, risk exposure (PRICE output)

## Memory & Data Layer Integration

| System | Scope | Role in Flow |
|--------|-------|-------------|
| **Agent Memory** (JSONL) | Cross-session, persistent | Step 2: routing hints, reflexion-weighted recall |
| **Experience Buffer** | Session-scoped | Pattern aggregation, similar query retrieval |
| **3-Layer NeSy-RAG** | Query-scoped | Step 4: Vector (0.6w) + Graph (0.4w) + Symbolic fusion |
| **Neo4j** | Persistent | Causal DAGs, governance triples, graph grounding |
| **Cloud SQL** | Persistent | Per-user analysis history, feedback, datasets |
| **Kafka** | Streaming | Immutable audit events (all state transitions) |

## Self-Correction Loop (SRR-Bounded)

```
Guardian REJECTS → Reflector (Heuristic → LLM → Hybrid repair)
  ↓ (success)        → Re-route to Router (retry)
  ↓ (max_reflections) → Human Escalation (3-point context)
  ↓ (critical)       → Immediate BLOCK (no self-repair possible)
```

**SRR Safety Properties:**
- Reflector bounded by `max_reflections=2` (TLA+ invariant S2)
- Guardian verdicts are deterministic/symbolic — not LLM-manipulable
- Human escalation bounded by `MaxHumanLoops` (TLA+ invariant S3)
- All paths eventually terminate (TLA+ liveness L1)

## Model/LLM Touchpoints

| Step | LLM Role | Deterministic Core |
|------|----------|-------------------|
| Router | Classification (+ DistilBERT option) | Entropy calculation, threshold gating |
| RAG | Retrieval ranking | Vector similarity, graph traversal |
| Causal Analyst | Hypothesis surfacing, narration | DoWhy/EconML estimation, refutation |
| Bayesian Explorer | Probe design, scenario narration | PyMC sampling, posterior analysis |
| World Model | Simulation fallback when no SCM data | SCM evaluation, OLS learning, do-calculus |
| NeSy Engine | Fact extraction from text | Forward-chaining, shortcut detection, constraint validation |
| Reflector | Self-correction reasoning | Heuristic repair patterns |
| Guardian | Verdict explanation only | Policy evaluation (YAML + CSL + OPA) |
| HumanLayer | 3-point context crafting | Escalation routing |

## Phase 18 Enhancements (Implemented)

| Enhancement | Flow Impact | Step Affected | Status |
|------------|------------|---------------|--------|
| Drift Detection | Records routing domain in DriftDetector, KL-divergence monitoring | Post-Step 10 (in `run_carf()`) | ✅ Implemented |
| Bias Auditing | Chi-squared test on agent memory corpus | On-demand via `/monitoring/bias-audit` | ✅ Implemented |
| Plateau Detection | Convergence monitoring on retraining epochs | Offline (feedback pipeline) | ✅ Implemented |
| ChimeraOracle Integration | `chimera_fast_path` conditional node in StateGraph with Guardian | Step 6 (new conditional edge for Complicated domain) | ✅ Implemented |
| Scalable Inference | Configurable MCMC/variational/cached modes | Step 6 (Bayesian agent) | Designed |

### Monitoring Data Flow (Phase 18)

```
Pipeline Execution:
  run_carf() → ... → final_state → drift_detector.record_routing(domain)
                                  → experience_buffer.add(entry)
                                  → agent_memory.store_from_state(final_state)

Monitoring API (on-demand):
  GET /monitoring/drift       → DriftDetector.get_status()
  GET /monitoring/bias-audit  → BiasAuditor.audit(agent_memory)
  GET /monitoring/convergence → RouterRetrainingService.check_convergence()
  GET /monitoring/status      → Unified: drift + bias + convergence

Frontend Views:
  Developer View  → MonitoringPanel (Drift tab + Convergence tab)
  Governance View → MonitoringPanel (Bias Audit tab + all tabs)
  Executive View  → 3 KPI cards: Routing Drift, Memory Bias, Retraining Health
```

## Failure Handling & Escalation

- Low confidence or parse failure → Disorder/Human
- Repeated rejection → `human_escalation` after `max_reflections`
- Circuit breaker always escalates to human after stabilization attempt
- Chaotic domain → automatic escalation (Phase 14 fix)
- H-Neuron flagged (hallucination risk > threshold) → human review

## Cost/Latency Considerations

- Prefer local/distilled model for routing when sufficient accuracy
- Use stronger LLM only on high entropy/uncertainty
- ChimeraOracle fast-path: <100ms vs 2-3s for full DoWhy (40x speedup)
- Governance node: <1ms P95 latency (feature-flagged, zero overhead when disabled)
- RAG: Reciprocal Rank Fusion adds <50ms overhead
- Keep prompts short; structure outputs; cache safe summaries
