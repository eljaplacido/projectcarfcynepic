# Research Evaluation: THUNLP H-Neurons Integration into CARF

**Date:** 2026-03-11  
**Scope:** Evaluate the feasibility, architecture, and value of integrating THUNLP's H-Neurons (hallucination-detecting neurons) into the CARF pipeline as a mechanistic interpretability layer.

---

## Executive Summary

THUNLP's H-Neurons research demonstrates that specific neurons in transformer hidden layers **causally encode hallucination behavior** — they fire predictably when the model generates unfaithful content. A lightweight linear classifier over these activations can detect hallucinations *during* generation, before the output reaches the user.

CARF already has a **multi-layered hallucination defense** (DeepEval scoring, quality gates, Smart Reflector, Guardian). However, all current defenses are **post-hoc** — they evaluate the *finished* output. H-Neurons would add a fundamentally new capability: **pre-delivery, mechanistic hallucination interception** at the neural activation level.

### Feasibility Verdict

| Dimension | Assessment |
|-----------|-----------|
| **Architectural Fit** | 🟢 Excellent — CARF's modular LangGraph pipeline has clear injection points |
| **White-Box Constraint** | 🟠 Medium — Requires local open-weights model (Ollama path exists; HuggingFace/vLLM needed) |
| **Latency Impact** | 🟡 Manageable — Feature-flag activation only for high-risk domains; ~15-50ms overhead |
| **Value-Add** | 🟢 High — Shifts from "detect after generation" to "detect during generation" |
| **Implementation Effort** | 🟠 Medium — New module + router/graph updates + PyTorch model hosting |

---

## 1. CARF's Current Hallucination Defense Stack

Before proposing H-Neuron integration, here is a precise map of CARF's **existing** hallucination defenses, traced through the source code:

### Layer-by-Layer Defense

```
Query → Router → Domain Agent → [HALLUCINATION CHECKS] → Guardian → Response
```

| Layer | File | Mechanism | When | Type |
|-------|------|-----------|------|------|
| **DeepEval Quality Gate** | `graph.py` L57-123 | `evaluate_node_output()` scores `hallucination_risk` after each workflow node | Post-generation | Output-based |
| **Hallucination Threshold** | `graph.py` L111-117 | If `hallucination_risk > 0.3` → quality warning + human review flag | Post-scoring | Threshold gate |
| **Heuristic Fallback** | `evaluation_service.py` L290-349 | When DeepEval unavailable, uses keyword-overlap heuristic for `hallucination_risk` | Post-generation | Statistical |
| **Guardian Policy** | `guardian.py` L333-359 | Confidence threshold check per Cynefin domain (Clear: 0.95, Complicated: 0.85, etc.) | Post-analysis | Policy-based |
| **Smart Reflector** | `smart_reflector.py` L221-286 | Hybrid heuristic + LLM repair on Guardian rejection | Post-rejection | Repair loop |
| **EpistemicState Tracking** | `state.py` L177 | `deepeval_scores` field stores per-node quality metrics including `hallucination_risk` | Throughout | Audit |
| **ChimeraOracle Validation** | LLM_AGENTIC_STRATEGY.md | Only cache predictions with `hallucination_risk < 0.2` | Pre-cache | Quality gate |

### The Gap

All defenses share a **fundamental limitation**: they operate on the **finished text output**. They ask *"Does this text look hallucinated?"* — not *"Is the model currently in a state where it will hallucinate?"*

**H-Neurons close this gap** by providing a **mechanistic, pre-delivery signal** from the model's internal state.

---

## 2. H-Neurons: What They Are and How They Work

### Core Mechanism

THUNLP's research identifies specific neurons (dubbed "H-Neurons") in transformer MLP layers whose activation patterns **causally correlate with hallucination**:

1. **Identification**: Run the model on a labeled dataset of factual vs. hallucinated outputs. Record activations at every hidden layer.
2. **Classification**: Train a lightweight linear classifier on these activations to predict hallucination probability.
3. **Detection**: At inference time, extract hidden states via PyTorch `register_forward_hook()` and run the classifier — producing a `hallucination_risk_score` in real-time.
4. **Intervention** (optional): Clamp H-Neuron activations to zero during the forward pass, forcing the model toward more factual generation.

### Key Properties

- **Causal, not correlational**: The neurons are validated via activation patching — clamping them *changes* model behavior, confirming causal influence.
- **Lightweight**: A single linear classifier over hidden states; ~1-5ms inference overhead per forward pass.
- **Model-specific**: The classifier must be trained per model architecture (e.g., LLaMA-3 8B).
- **White-box only**: Requires access to model weights and hidden states — **incompatible with API-based providers** (OpenAI, Anthropic, DeepSeek API).

---

## 3. Integration Architecture: The "Mechanistic Sentinel" Pattern

### Design Principle

Rather than replacing CARF's primary LLM (which may be a cloud API), introduce a **local open-weights model as a parallel "Mechanistic Sentinel"** that monitors for hallucination risk. This is analogous to CARF's existing dual-model pattern (DistilBERT router alongside LLM router).

### Architecture Diagram

```
                          ┌──────────────────────────────┐
                          │   H-Neuron Sentinel (LOCAL)   │
                          │   LLaMA-3 8B + Classifier     │
                          │   PyTorch forward hooks        │
                          └──────────┬───────────────────┘
                                     │ hallucination_risk_score
                                     ▼
Query → Router → CSL Precheck → Domain Agent ──→ H-Neuron Gate (NEW)
                                     │                    │
                                     │            ┌───────┴────────┐
                                     │            │ risk < 0.3     │ risk ≥ 0.85
                                     │            │ PASS           │ REROUTE
                                     │            └───────┬────────┘
                                     ▼                    │
                              Guardian ←──────────────────┘
                                     │
                              Response / Reflector / Human
```

### Integration Points in CARF Codebase

| Component | File | Change Type | Description |
|-----------|------|-------------|-------------|
| **H-Neuron Interceptor** | `src/services/h_neuron_interceptor.py` | **[NEW]** | PyTorch model wrapper with `register_forward_hook`, linear classifier, `predict_hallucination_risk()` |
| **LLM Config** | `src/core/llm.py` | **[MODIFY]** | Add `SENTINEL` provider type; new `get_sentinel_model()` factory for local PyTorch model |
| **EpistemicState** | `src/core/state.py` | **[MODIFY]** | Add `h_neuron_risk_score: float`, `h_neuron_flagged: bool`, `h_neuron_intervention_applied: bool` fields |
| **LangGraph Workflow** | `src/workflows/graph.py` | **[MODIFY]** | Add `h_neuron_gate_node` after domain agents; conditional edge to reroute/intervene |
| **Router** | `src/workflows/router.py` | **[MODIFY]** | Add `reclassify_on_hallucination_risk()` method for dynamic domain override |
| **Guardian** | `src/workflows/guardian.py` | **[MODIFY]** | Add H-Neuron risk score to `RiskComponent` decomposition |
| **Config** | `config/h_neuron_config.yaml` | **[NEW]** | Thresholds, sentinel model path, enabled domains, intervention mode |
| **Benchmarks** | `benchmarks/h_neuron/` | **[NEW]** | H43: H-Neuron detection accuracy, H44: Intervention effectiveness, H45: Latency overhead |

---

## 4. Proposed Module: `h_neuron_interceptor.py`

```python
"""H-Neuron Interceptor — Mechanistic hallucination detection for CARF.

Wraps a local open-weights model (e.g., LLaMA-3 8B) with PyTorch forward
hooks to extract hidden states and predict hallucination risk using a
pre-trained linear classifier (THUNLP H-Neurons approach).

Usage:
    sentinel = HNeuronSentinel.from_config("config/h_neuron_config.yaml")
    risk = await sentinel.assess_hallucination_risk(prompt, response)
    
    if risk.score > 0.85:
        # Trigger CARF rerouting or intervention
        safe_response = await sentinel.intervene_and_regenerate(prompt)
"""

class HNeuronConfig(BaseModel):
    """Configuration for H-Neuron Sentinel."""
    enabled: bool = False
    model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    classifier_path: str = "models/h_neuron_classifier.pt"
    hallucination_threshold: float = 0.85
    intervention_threshold: float = 0.95  # Above this, clamp neurons
    target_layers: list[int] = [15, 16, 17, 18, 19]  # MLP layers to monitor
    active_domains: list[str] = ["Complicated", "Complex"]  # Only active for these
    device: str = "cuda"  # or "cpu"
    max_latency_ms: int = 100  # Hard cap on sentinel latency

class HallucinationAssessment(BaseModel):
    """Result of H-Neuron hallucination assessment."""
    score: float  # 0.0 = factual, 1.0 = hallucinating
    flagged: bool  # score > threshold
    layer_activations: dict[int, float]  # per-layer risk contribution
    intervention_recommended: bool  # score > intervention_threshold
    latency_ms: int
    sentinel_model: str

class HNeuronSentinel:
    """Mechanistic hallucination detector using forward hook activation analysis.
    
    Integration with CARF:
    - Runs AFTER the primary LLM generates a response
    - Feeds the same prompt through the local sentinel model
    - Extracts hidden states via register_forward_hook
    - Runs pre-trained classifier on activations
    - Returns HallucinationAssessment to the LangGraph workflow
    
    Two modes:
    1. DETECTION: Score and flag, let Guardian/Reflector handle
    2. INTERVENTION: Clamp H-Neuron activations and regenerate
    """

    async def assess_hallucination_risk(
        self, prompt: str, primary_response: str
    ) -> HallucinationAssessment:
        """Run the sentinel model and classify hidden state activations."""
        ...

    async def intervene_and_regenerate(
        self, prompt: str, neurons_to_clamp: list[tuple[int, int]]
    ) -> str:
        """Regenerate with H-Neurons clamped to zero (factual forcing)."""
        ...

    def _register_hooks(self) -> list:
        """Register forward hooks on target MLP layers."""
        ...

    def _extract_activations(self, hook_outputs: list) -> torch.Tensor:
        """Concatenate layer activations for classifier input."""
        ...
```

---

## 5. LangGraph Workflow Integration

### New Node: `h_neuron_gate_node`

This node would be inserted into `src/workflows/graph.py` between the domain agents and the Guardian:

```python
async def h_neuron_gate_node(state: EpistemicState) -> EpistemicState:
    """H-Neuron mechanistic hallucination gate.
    
    Runs the sentinel model on the domain agent's output.
    If hallucination risk exceeds threshold:
      - Mode DETECT: Flag in state, let Guardian handle
      - Mode INTERVENE: Regenerate with clamped neurons
      - Mode REROUTE: Reclassify to Complex/Chaotic domain
    """
    sentinel = get_h_neuron_sentinel()
    if not sentinel or not sentinel.is_active_for(state.cynefin_domain):
        return state  # Pass through when disabled or inactive domain
    
    assessment = await sentinel.assess_hallucination_risk(
        prompt=state.user_input,
        primary_response=state.final_response or state.current_hypothesis or ""
    )
    
    # Store in state for audit trail
    state.context["h_neuron_risk_score"] = assessment.score
    state.context["h_neuron_flagged"] = assessment.flagged
    state.context["h_neuron_layer_activations"] = assessment.layer_activations
    
    if assessment.intervention_recommended:
        # Mode: INTERVENE — regenerate with clamped neurons
        safe_response = await sentinel.intervene_and_regenerate(state.user_input)
        state.final_response = safe_response
        state.context["h_neuron_intervention_applied"] = True
        
    elif assessment.flagged:
        # Mode: REROUTE — escalate complexity domain
        state.context["quality_warning"] = (
            f"H-Neuron mechanistic hallucination risk: {assessment.score:.2f}"
        )
        # Let Guardian handle with elevated risk score
    
    return state
```

### Updated Graph Edges

```python
# Current flow:
# causal_analyst → csl_guardian
# bayesian_explorer → csl_guardian

# Proposed flow:
# causal_analyst → h_neuron_gate → csl_guardian
# bayesian_explorer → h_neuron_gate → csl_guardian
```

---

## 6. Critical Technical Constraints & Mitigations

### Constraint 1: White-Box Requirement

**Problem:** H-Neurons require access to model internals. CARF's primary providers (DeepSeek API, OpenAI, Anthropic) are **black-box APIs**.

**Mitigation — The "Sentinel" Pattern:**

```
┌──────────────────────────────────────────────────┐
│ Primary LLM (Black-Box API)                      │
│ DeepSeek / OpenAI / Anthropic                    │
│ → Generates main response                        │
└──────────────────────────────────────────────────┘
                     ↓ response text
┌──────────────────────────────────────────────────┐
│ Sentinel LLM (White-Box Local)                   │
│ LLaMA-3 8B via HuggingFace + PyTorch             │
│ → Re-processes prompt, extracts hidden states     │
│ → Classifier predicts hallucination probability   │
└──────────────────────────────────────────────────┘
```

CARF already supports **Ollama** as a local provider (`LLMProvider.OLLAMA` in `llm.py` L260-265). The sentinel would use a parallel local model path, not replacing the primary LLM but **shadowing** it for monitoring.

> [!IMPORTANT]
> The sentinel assesses *its own* hidden states when processing the same prompt, not the primary LLM's states. This is a **proxy signal** — it detects that "a model of similar capability would hallucinate on this prompt." This is a weaker signal than monitoring the actual generating model, but it avoids the white-box constraint entirely.

### Constraint 2: Latency Overhead

**Problem:** Running a second model forward pass adds latency.

**Mitigation — Selective Activation:**

| Strategy | Implementation |
|----------|---------------|
| **Domain-gated** | Only activate for `Complicated` and `Complex` domains (not `Clear` or `Chaotic`) |
| **Entropy-gated** | Only activate when router entropy > 0.6 (ambiguous queries) |
| **Confidence-gated** | Only activate when domain confidence < 0.8 |
| **Async shadow** | Run sentinel in parallel with Guardian check; merge results |

Expected overhead with selective activation: **15-50ms** on flagged queries, **0ms** on bypassed queries.

### Constraint 3: Classifier Training

**Problem:** The H-Neuron classifier must be trained per model architecture.

**Mitigation:**

1. Use THUNLP's published classifiers for LLaMA-3 if available
2. Fine-tune on CARF's own benchmark data (H7/H19 hallucination test cases + H17 counterfactual ground truth)
3. Store as `models/h_neuron_classifier.pt` alongside ChimeraOracle models

### Constraint 4: Proxy vs. Direct Monitoring

**Problem:** The sentinel monitors its *own* activations, not the primary LLM's — so it's an approximation.

**Mitigation — Validation benchmark:**

- Run H-Neuron sentinel against CARF's existing 45 OWASP injection cases (H23) and hallucination benchmark (H7, H19)
- Measure concordance between sentinel risk scores and DeepEval-based post-hoc hallucination scores
- Only deploy if sentinel achieves ≥ 80% agreement with existing detection

---

## 7. Integration with Existing Hallucination Defenses

H-Neurons don't replace existing defenses — they **layer underneath** them:

```
                    EXISTING DEFENSES                NEW DEFENSE
                    (Post-hoc, output-based)         (Mechanistic, pre-delivery)
                    ┌─────────────────────┐          ┌──────────────────────┐
                    │ DeepEval Scoring     │          │ H-Neuron Sentinel    │
  Generated    ───→ │ Heuristic Fallback   │    ───→  │ Activation Classifier│
  Response          │ Quality Gates (0.3)  │          │ Forward Hooks        │
                    │ Guardian Policies    │          │ Intervention Mode    │
                    │ Smart Reflector      │          └──────────────────────┘
                    └─────────────────────┘                    
                              ↓                                ↓
                    Evaluates finished text           Evaluates neural state
                    "Does this look wrong?"           "Is the model confused?"
```

### Combined Signal Fusion

Add to `evaluate_node_output()` in `graph.py`:

```python
# Fuse H-Neuron mechanistic signal with DeepEval output signal
combined_hallucination_risk = max(
    deepeval_risk,                          # Post-hoc output analysis
    state.context.get("h_neuron_risk_score", 0.0)  # Mechanistic signal
)
```

---

## 8. Proposed Benchmarks

| ID | Hypothesis | Metric | Threshold |
|----|-----------|--------|-----------|
| H43 | **H-Neuron Detection Accuracy** — Sentinel detects known hallucination cases from H7/H19 benchmarks | Precision, Recall | ≥ 80% |
| H44 | **Intervention Effectiveness** — Clamping H-Neurons reduces hallucination rate | Reduction % | ≥ 40% |
| H45 | **Sentinel Latency** — Overhead per monitored query | P95 ms | ≤ 100ms |
| H46 | **Signal Concordance** — Agreement between H-Neuron risk and DeepEval hallucination_risk | Cohen's κ | ≥ 0.6 |
| H47 | **Proxy Validity** — Sentinel risk on its own activations predicts primary LLM hallucination | AUROC | ≥ 0.75 |

---

## 9. What CARF Already Does That Supports This

| Existing CARF Capability | How It Enables H-Neurons |
|-------------------------|-------------------------|
| **Ollama provider** (`llm.py` L260-265) | Local model infrastructure already exists |
| **Feature-flag architecture** | H-Neuron sentinel can be `HNEURON_ENABLED=false` by default |
| **DeepEval hallucination_risk** | Existing metric provides validation ground truth |
| **EpistemicState.context** | Flexible dict allows H-Neuron scores without schema breaks |
| **Quality gates in graph.py** | Existing `if risk > 0.3` pattern is directly extensible |
| **Smart Reflector** | Repair loop can consume H-Neuron explanations for targeted fixes |
| **ChimeraOracle models dir** | `models/` directory pattern for storing classifier weights |
| **Dual-model router** (DistilBERT + LLM) | Parallel model pattern is already established in architecture |
| **H7/H19/H23 benchmarks** | Ground truth datasets for classifier training and validation |

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Low Risk)
1. **`h_neuron_interceptor.py`** — Core module with `HNeuronSentinel` class
2. **`config/h_neuron_config.yaml`** — Feature-flagged configuration
3. **State extensions** — Add H-Neuron fields to `EpistemicState.context` (no schema break)
4. **Classifier training** — Train on CARF's H7/H19 benchmark datasets

### Phase 2: Pipeline Integration (Medium Risk)
5. **`h_neuron_gate_node`** — New LangGraph node with conditional activation
6. **Graph edges** — Insert between domain agents and Guardian
7. **Signal fusion** — Combine H-Neuron + DeepEval scores in quality gates
8. **Guardian integration** — Add H-Neuron risk to `RiskComponent` breakdown

### Phase 3: Advanced (Higher Risk)
9. **Intervention mode** — Activation clamping for forced factual regeneration
10. **Dashboard integration** — H-Neuron risk visualization in Developer View
11. **Continuous learning** — Retrain classifier on production hallucination instances

---

## 11. Alignment with CARF's Existing IP & Philosophy

This integration aligns with CARF's core differentiator from the [SOLUTION_VISION](file:///c:/Users/35845/Desktop/DIGICISU/projectcarf/docs/SOLUTION_VISION.md):

> *"CARF addresses the fundamental epistemic deficit of LLMs: their inability to distinguish knowing from guessing"*

H-Neurons make this distinction **mechanistic and causal** rather than statistical:

| Approach | Question Answered | Signal Type |
|----------|------------------|-------------|
| DeepEval (current) | "Does this output *look* hallucinated?" | Statistical, output-based |
| Guardian (current) | "Does this action *violate* policy?" | Symbolic, rule-based |
| H-Neurons (proposed) | "Is the model *in a state* that produces hallucinations?" | Mechanistic, causal |

This creates a **three-pillar epistemic defense**: statistical + symbolic + mechanistic — directly embodying the Neuro-Symbolic-Causal vision.
