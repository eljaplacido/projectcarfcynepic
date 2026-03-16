# Self-Healing Architecture

> Last Updated: 2026-03-16 (Phase 17 complete, SRR model formalized)

## Purpose
Explain how CARF detects failures, retries safely, involves humans, and learns from outcomes — within the Supervised Recursive Refinement (SRR) safety model.

## Supervised Recursive Refinement (SRR) Model

CARF's self-healing is governed by the SRR model, which bounds all improvement loops:

```
No Self-       Bounded            Supervised           Autonomous          Unbounded
Improvement    Self-Correction    Self-Modification    Self-Enhancement    RSI
│              │                  │                    │                   │
│              │     ◄── CARF ──► │                    │                   │
│              │                  │                    │                   │
Static tools   Reflector loop,    Feedback→Retrain,    —                   Theory only
               auto-repair        Memory→Router hints
```

**Key SRR Properties:**
- Self-correction bounded by `max_reflections` (default: 2)
- Meta-learning through memory with deliberately small influence (0.03 weight)
- Self-modification requires human triggering
- Safety containment uses independent, deterministic, formally verified mechanisms
- System CANNOT modify its own architecture, policies, or core logic autonomously

**Reference:** See [`CARF_RSI_ANALYSIS.md`](CARF_RSI_ANALYSIS.md) for the complete RSI alignment assessment.

## Self-Healing Mechanisms

### 1. Smart Reflector (Bounded Self-Correction)

The Smart Reflector (`src/services/smart_reflector.py`) implements a three-strategy repair system:

```
Guardian REJECTS → Reflector → [Heuristic | LLM | Hybrid] → Re-route to Router
```

| Strategy | Speed | Scope | How it works |
|----------|-------|-------|-------------|
| **Heuristic** | Sub-ms | Known patterns | Budget → 20% reduction, threshold → 10% safety margin, approval → flag for review |
| **LLM** | ~1s | Unrecognized violations | Contextual repair via `get_chat_model()` with structured JSON output |
| **Hybrid** (default) | Variable | Full coverage | Heuristic first; if confidence < 0.7 or violations remain, fallback to LLM |

**Safety bounds:**
- Maximum `max_reflections=2` retries (TLA+ invariant S2)
- After exhaustion → human escalation (never continues self-modifying)
- Each repair attempt logged with strategy, success/failure, violation details
- Original action preserved in `context["original_action"]`

### 2. Memory-Driven Learning (Bounded Meta-Learning)

Dual-layer memory provides experiential learning within strict bounds:

| Layer | Scope | Influence | Bound |
|-------|-------|-----------|-------|
| **Agent Memory** | Cross-session, persistent | 0.03 routing weight | `max_entries=10000` |
| **Experience Buffer** | Session-scoped | Pattern aggregation only | `deque(maxlen=1000)` |

**Key safety feature:** Memory hints are **soft signals** in routing — they can never override domain-level separation or Guardian enforcement.

### 3. Feedback → Retraining Pipeline (Human-Supervised Self-Modification)

```
User feedback (domain_override) → FeedbackStore (SQLite) → RouterRetrainingService
  → Keyword hint extraction → Updated DATA_STRUCTURE_HINTS
```

**Safety bounds:**
- Readiness thresholds: ≥10 overrides with ≥3 per domain before triggering
- Non-destructive: keyword hints extracted but not automatically applied
- `/feedback/retrain-router` explicitly states "does not modify the running router directly"
- Entire pipeline requires human triggering

### 4. H-Neuron Sentinel (Pre-Delivery Interception)

Phase 17 added hallucination detection as a pre-Guardian gate:

| Signal | Weight | Source |
|--------|--------|--------|
| DeepEval hallucination risk | 35% | EvaluationService |
| Confidence risk (1 - domain_confidence) | 20% | Router |
| Epistemic uncertainty | 15% | Bayesian engine |
| Reflection risk | 10% | Reflector loop count |
| Irrelevancy risk | 7% | DeepEval relevancy |
| Brevity/shallow/verbosity risks | 13% combined | Response heuristics |

**Action:** Flagged responses (risk > threshold) are escalated to human review before delivery.

### 5. Multi-Agent Critic-Worker Architecture

The LangGraph cognitive mesh implements structured agent interaction:

| Agent | Role | Self-Healing Function |
|-------|------|----------------------|
| Router | Classifier | Learns from memory hints |
| Domain Agents (4) | Workers | Produce analyses |
| Guardian | Critic | Evaluates all outputs against policies |
| Reflector | Repair | Attempts self-correction on rejection |
| Governance | Auditor | Tracks cross-domain impacts, detects conflicts |
| EvaluationService | Quality judge | DeepEval scoring at every node |

## Formal Verification (TLA+)

TLA+ specifications mathematically verify that CARF's self-healing cannot enter unsafe states:

| Property | Guarantee |
|----------|-----------|
| **Liveness L1** | Every request eventually terminates (no infinite loops) |
| **Safety S1** | No domain agent runs without prior router classification |
| **Safety S2** | Reflector loops bounded by `MaxReflections` |
| **Safety S3** | Human escalation loops bounded by `MaxHumanLoops` |
| **Safety S4** | Every non-emergency output passes through Guardian |
| **Escalation S5** | No escalation request is silently dropped |

The TLC model checker exhaustively explores ~10k-50k states to prove no violation exists.

## Known SRR Gaps (Phase 18 Addresses)

| Gap | Risk | Phase 18 Solution |
|-----|------|-------------------|
| No drift detection | Memory→router hints may shift routing distribution silently | 18A: KL-divergence monitoring |
| No bias auditing | Accumulated memory may contain systematic domain bias | 18B: Statistical fairness audit |
| No plateau detection | Retraining may overfit or show diminishing returns | 18C: Convergence monitoring |
| ChimeraOracle isolated | Fast predictions bypass Guardian enforcement | 18D: StateGraph integration |

## Observability

- Log each transition: node, action, confidence, verdict, violations
- Trace IDs/session IDs preserved through Router → Guardian → Reflector → HumanLayer
- EvaluationService scores logged at every node (hallucination, relevancy, UIX, reasoning depth)
- Repair history accumulated in `context["guardian_rejections"]` for downstream learning
- Governance semantic triples feed back into RAG index
- All quality scores available via `/transparency/*` API endpoints

## Integration Points

- **Router**: Downgrade to Disorder on repeated failures; causal language boost for reclassification
- **Guardian**: Includes recommendations to guide reflection; domain-adjusted thresholds
- **Reflector**: Stores repair provenance; each attempt logged with strategy used
- **HumanLayer**: Returns override instructions stored in EpistemicState; used on retry
- **H-Neuron**: Pre-delivery hallucination gate; flags high-risk outputs before Guardian
- **Governance**: MAP-PRICE-RESOLVE audits all approved actions; conflict detection feeds back to policies
