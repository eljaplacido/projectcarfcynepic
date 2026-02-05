# CARF Evaluation Framework

## Overview

The CARF Evaluation Framework provides **quantitative quality metrics** for LLM outputs across all system layers. Built on [DeepEval](https://github.com/confident-ai/deepeval), it enables:

- **Real-time quality scoring** of AI-generated responses
- **Transparency and traceability** across analysis pipelines
- **Regression testing** for LLM output quality
- **Multi-view insights** for Analysts, Developers, and Executives

---

## Core Quality Metrics

### DeepEval Scores

| Metric | Range | Description | Threshold |
|--------|-------|-------------|-----------|
| **Relevancy Score** | 0.0 - 1.0 | How relevant the response is to the query | ≥ 0.7 |
| **Hallucination Risk** | 0.0 - 1.0 | Probability of fabricated content (lower = better) | ≤ 0.3 |
| **Reasoning Depth** | 0.0 - 1.0 | Quality and rigor of reasoning | ≥ 0.6 |
| **UIX Compliance** | 0.0 - 1.0 | Adherence to CARF UIX standards | ≥ 0.6 |
| **Task Completion** | Boolean | Whether the query was adequately addressed | True |

### UIX Standards (What UIX Compliance Measures)

Based on [CARF_UIX_INTERACTION_GUIDELINES.md](./CARF_UIX_INTERACTION_GUIDELINES.md):

1. **"Why this?"** - Explains reasoning behind recommendations
2. **"How confident?"** - Quantifies uncertainty (percentages, ranges)
3. **"Based on what?"** - Cites data sources and methodology
4. **"Accessible language"** - Non-experts can understand

---

## Evaluation by View

### Analyst View

Analysts use evaluation metrics to **enrich insights** and **validate AI guidance**.

#### Use Cases & Evaluation Integration

| Use Case | Relevant Metrics | How Evaluation Helps |
|----------|------------------|---------------------|
| **Causal Analysis** | Hallucination Risk, Reasoning Depth | Validates causal claims aren't overstated; ensures confounders properly explained |
| **Bayesian Inference** | Relevancy, Reasoning Depth | Verifies uncertainty quantification is complete; probes are well-designed |
| **Chat-Based Guidance** | Relevancy, UIX Compliance | Ensures conversational responses answer user questions with proper context |
| **Cynefin Classification** | Relevancy, Task Completion | Validates domain classification reasoning is sound |

#### Transparency & Traceability for Analysts

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYST TRANSPARENCY VIEW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Query: "Why did sales increase after the marketing campaign?"   │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │  Cynefin Router │───▶│ Causal Analyst  │───▶│   Guardian   │ │
│  │                 │    │                 │    │              │ │
│  │ Relevancy: 92%  │    │ Relevancy: 87%  │    │ Approved ✓   │ │
│  │ Halluc.: 5%     │    │ Halluc.: 12%    │    │              │ │
│  │ Reasoning: 88%  │    │ Reasoning: 91%  │    │              │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│                                                                  │
│  Overall Quality: 89% (HIGH)                                     │
│  UIX Compliance: 94%                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Causal Analysis Evaluation

When reviewing causal analysis results, evaluation metrics answer:

- **Is the causal claim justified?** (Reasoning Depth > 0.8)
- **Are confounders properly acknowledged?** (UIX Compliance includes limitations)
- **Is there evidence of hallucination?** (Hallucination Risk < 0.2)
- **Are refutation test interpretations accurate?** (Relevancy to actual results)

#### Bayesian Analysis Evaluation

For Bayesian/Complex domain queries:

- **Is uncertainty properly communicated?** (UIX "How confident?" criterion)
- **Are probability distributions explained accessibly?** (UIX Compliance)
- **Are probing recommendations safe-to-fail?** (Reasoning Depth)
- **Is epistemic vs aleatoric uncertainty distinguished?** (Reasoning Depth)

#### Guardian Layer Evaluation

Guardian decisions include evaluation to ensure:

- **Policy evaluations are explained** (Reasoning Depth)
- **Escalation reasons are clear** (UIX Compliance)
- **Risk breakdown is accurate** (Hallucination Risk on risk claims)

#### Cynefin Router Debugging

Evaluation helps debug router classification:

| Router Issue | Evaluation Metric | Diagnostic |
|--------------|-------------------|------------|
| Wrong domain | Relevancy < 0.7 | Query-classification mismatch |
| Low confidence | Reasoning < 0.6 | Insufficient reasoning chain |
| Boundary confusion | Task Completion = False | Failed to commit to classification |

#### Chimera Oracle Integration

The Chimera Oracle (fast causal predictions) uses evaluation for:

1. **Prediction Validation**: Compare Chimera output relevancy vs full DoWhy analysis
2. **Cache Quality**: Only cache predictions with Hallucination Risk < 0.2
3. **Confidence Calibration**: Evaluate if Chimera confidence aligns with actual accuracy

```python
# Chimera Oracle with evaluation gating
chimera_prediction = await chimera_oracle.predict(features)

# Evaluate prediction quality
eval_scores = await evaluation_service.evaluate_response(
    input=query,
    output=chimera_prediction.explanation,
    context=[feature_importance_context]
)

# Only use if quality threshold met
if eval_scores.hallucination_risk > 0.3:
    # Fall back to full DoWhy analysis
    return await causal_engine.analyze(query, data)
```

---

### Developer View

Developers use evaluation metrics for **debugging**, **performance analysis**, and **system understanding**.

#### Analysis Chain Drill-Down

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPER DEBUG VIEW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Session: abc-123                                                │
│  Total Latency: 2,497ms                                          │
│  Overall Quality: 87%                                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ STEP 1: Router (145ms)                                      ││
│  │   Input:  "Why did sales increase..."                       ││
│  │   Output: { domain: "Complicated", confidence: 0.89 }       ││
│  │   Eval:   Relevancy=0.92, Reasoning=0.88, Halluc=0.05      ││
│  │   Status: ✓ PASS (all thresholds met)                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ STEP 2: Causal Analyst (2,340ms)                            ││
│  │   Input:  Sales data, marketing spend, confounders          ││
│  │   Output: { effect: 0.15, ci: [0.12, 0.18], p: 0.001 }     ││
│  │   Eval:   Relevancy=0.87, Reasoning=0.91, Halluc=0.12      ││
│  │   Status: ✓ PASS                                            ││
│  │   ⚠️ Note: Hallucination slightly elevated - review claims  ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ STEP 3: Guardian (12ms)                                     ││
│  │   Input:  Analysis result, confidence=0.87                  ││
│  │   Output: { verdict: "APPROVE", risk: "LOW" }               ││
│  │   Eval:   Relevancy=0.95, Reasoning=0.89                    ││
│  │   Status: ✓ PASS                                            ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Data Layer Analysis

Evaluation integrates with data layer for:

| Data Component | Evaluation Use |
|----------------|----------------|
| **Neo4j (Causal Graph)** | Store quality scores with CausalAnalysis nodes |
| **SQLite (Dataset Registry)** | Index datasets by analysis quality outcomes |
| **Kafka (Audit Trail)** | Include eval scores in audit events |
| **Cache (LRU)** | Prefer high-quality cached responses |

**Neo4j Quality Schema Extension:**
```cypher
(:CausalAnalysis {
    session_id: "abc-123",
    effect_size: 0.15,
    confidence: 0.87,
    // NEW: Evaluation metrics
    eval_relevancy: 0.87,
    eval_hallucination_risk: 0.12,
    eval_reasoning_depth: 0.91,
    eval_uix_compliance: 0.88,
    eval_timestamp: datetime()
})
```

#### Reliability Understanding

Evaluation contributes to reliability assessment:

```
Reliability Score = weighted_average([
    Data Quality Score      (25%),
    Model Confidence Score  (30%),
    Refutation Score        (25%),
    Sample Size Score       (20%),
    + DeepEval Quality Score (NEW - adjusts final score)
])

DeepEval Adjustment:
- If hallucination_risk > 0.3: Reduce reliability by 10%
- If relevancy < 0.7: Flag for human review
- If reasoning_depth < 0.6: Add to improvement suggestions
```

#### Indexing & Retrieval

Evaluation enables quality-aware retrieval:

```python
# Quality-filtered retrieval from Neo4j
query = """
MATCH (a:CausalAnalysis)
WHERE a.eval_hallucination_risk < 0.2
  AND a.eval_relevancy > 0.8
RETURN a
ORDER BY a.eval_relevancy DESC
LIMIT 10
"""
high_quality_analyses = neo4j_service.query(query)
```

#### Developer Debugging Workflows

| Debug Scenario | Evaluation Insight |
|----------------|-------------------|
| Unexpected router classification | Check router step Relevancy score |
| Causal analysis seems wrong | Check Hallucination Risk on causal claims |
| Guardian rejected valid analysis | Verify reasoning_depth on Guardian input |
| Chat response unhelpful | Check UIX Compliance breakdown |
| Chimera vs DoWhy mismatch | Compare evaluation scores for consistency |

---

### Executive View

Executives need **aggregated quality insights** for strategic decisions.

#### Quality Dashboard Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTIVE QUALITY DASHBOARD                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Period: Last 30 Days          Total Analyses: 1,247             │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ OVERALL QUALITY TREND                                      │  │
│  │                                                            │  │
│  │  100% ─┬─────────────────────────────────────────────────  │  │
│  │        │                                    ╭──────────    │  │
│  │   80% ─┤                        ╭──────────╯              │  │
│  │        │            ╭──────────╯                          │  │
│  │   60% ─┤ ──────────╯                                      │  │
│  │        │                                                   │  │
│  │   40% ─┴─────────────────────────────────────────────────  │  │
│  │        Week 1   Week 2   Week 3   Week 4                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Key Metrics:                                                    │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │ Avg Relevancy  │ Halluc. Rate   │ UIX Compliance │          │
│  │     87%        │     8%         │     91%        │          │
│  │   ▲ +3% MoM    │   ▼ -2% MoM    │   ▲ +5% MoM    │          │
│  └────────────────┴────────────────┴────────────────┘          │
│                                                                  │
│  Quality by Domain:                                              │
│  ├─ Clear:        94% avg quality (n=342)                       │
│  ├─ Complicated:  86% avg quality (n=521)                       │
│  ├─ Complex:      79% avg quality (n=298)                       │
│  └─ Chaotic:      72% avg quality (n=86)                        │
│                                                                  │
│  Human Escalation Rate: 12% (target: <15%)                      │
│  EU AI Act Compliance:  94%                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Executive KPIs

| KPI | Metric | Target | Why It Matters |
|-----|--------|--------|----------------|
| **Analysis Quality** | Avg Relevancy Score | > 85% | Ensures AI outputs are useful |
| **Trustworthiness** | Avg Hallucination Rate | < 10% | Prevents misinformation |
| **Compliance** | UIX Compliance Score | > 90% | EU AI Act readiness |
| **Efficiency** | Human Escalation Rate | < 15% | Automation effectiveness |
| **Reliability** | Task Completion Rate | > 95% | System dependability |

#### Quality Alerts for Executives

```
⚠️ QUALITY ALERT: Causal Analysis Domain

Hallucination risk increased 15% this week.
Affected: 23 analyses (4.4% of total)

Root Cause: New marketing dataset introduced confounding variables
            not in training data.

Recommended Action:
1. Retrain Chimera Oracle with updated features
2. Increase Guardian confidence threshold temporarily
3. Flag affected analyses for human review

Business Impact: Low - analyses flagged before delivery to users
```

---

## Integration Architecture

### Evaluation Service Integration Points

```
┌──────────────────────────────────────────────────────────────────┐
│                        CARF PIPELINE                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   User Query                                                      │
│       │                                                           │
│       ▼                                                           │
│   ┌─────────────┐     ┌─────────────────────┐                    │
│   │   Router    │────▶│ EvaluationService   │◀─── [1] Router     │
│   └─────────────┘     │                     │      classification │
│       │               │  • Relevancy        │      quality        │
│       ▼               │  • Hallucination    │                     │
│   ┌─────────────┐     │  • Reasoning        │                     │
│   │   Domain    │────▶│  • UIX Compliance   │◀─── [2] Analysis   │
│   │   Agent     │     │                     │      output         │
│   └─────────────┘     └─────────────────────┘      quality        │
│       │                         │                                 │
│       ▼                         │                                 │
│   ┌─────────────┐               │                                 │
│   │  Guardian   │───────────────┘◀─── [3] Decision               │
│   └─────────────┘                     justification              │
│       │                               quality                     │
│       ▼                                                           │
│   ┌─────────────┐     ┌─────────────────────┐                    │
│   │   Output    │────▶│  TransparencyPanel  │◀─── [4] Quality    │
│   └─────────────┘     │  (Frontend)         │      scores        │
│                       └─────────────────────┘      displayed      │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Workflow Graph Integration

```python
# src/workflows/graph.py - Integration points

from src.services.evaluation_service import get_evaluation_service

async def cynefin_router_node(state: EpistemicState) -> EpistemicState:
    # ... existing router logic ...

    # NEW: Evaluate router output quality
    eval_service = get_evaluation_service()
    router_scores = await eval_service.evaluate_response(
        input=state.user_input,
        output=f"Domain: {result.domain}, Confidence: {result.confidence}",
        context=[state.user_input]
    )

    # Add to reasoning chain
    state.eval_scores["router"] = router_scores

    # Quality gate: if hallucination risk high, add human review flag
    if router_scores.hallucination_risk > 0.3:
        state.requires_human_review = True

    return state
```

### Kafka Audit Event Extension

```python
# Extended audit event with evaluation scores
class KafkaAuditEvent(BaseModel):
    session_id: str
    timestamp: datetime
    domain: str
    verdict: str
    reasoning_chain: list[dict]
    # NEW: Evaluation metrics
    evaluation_scores: dict = {
        "relevancy": 0.0,
        "hallucination_risk": 0.0,
        "reasoning_depth": 0.0,
        "uix_compliance": 0.0,
        "task_completion": False
    }
```

---

## Testing

### Running Evaluation Tests

```bash
# Install with evaluation dependencies
pip install -e ".[dev,evaluation]"

# Run all DeepEval tests
pytest tests/deepeval/ -v

# Run specific test categories
pytest tests/deepeval/test_chat_quality.py -v
pytest tests/deepeval/test_causal_quality.py -v
pytest tests/deepeval/test_router_accuracy.py -v

# Run with DeepEval CLI (parallel execution)
deepeval test run tests/deepeval/ -n 4

# Run with coverage
pytest tests/deepeval/ -v --cov=src/services/evaluation_service
```

### Test Coverage

| Test File | Coverage Area | Tests |
|-----------|---------------|-------|
| `test_chat_quality.py` | Chat response quality | 4 |
| `test_explanation_quality.py` | Explanation UIX compliance | 5 |
| `test_router_accuracy.py` | Cynefin classification | 6 |
| `test_causal_quality.py` | Causal analysis output | 7 |
| `test_bayesian_quality.py` | Bayesian analysis output | 6 |
| `test_transparency_quality.py` | Audit trail completeness | 5 |
| `test_evaluation_service.py` | Evaluation service itself | 8 |
| `test_workflow_e2e.py` | End-to-end workflows | 4 |

---

## Configuration

### Environment Variables

```bash
# Required for evaluation
DEEPSEEK_API_KEY=your_key_here

# Optional: Confident AI dashboard
CONFIDENT_API_KEY=your_key_here

# Evaluation thresholds (customize per environment)
EVAL_RELEVANCY_THRESHOLD=0.7
EVAL_HALLUCINATION_THRESHOLD=0.3
EVAL_REASONING_THRESHOLD=0.6
EVAL_UIX_THRESHOLD=0.6
```

### EvaluationConfig

```python
from src.services.evaluation_service import EvaluationConfig

config = EvaluationConfig(
    enabled=True,
    relevancy_threshold=0.7,
    hallucination_threshold=0.3,
    model_name="deepseek-chat",
    api_base_url="https://api.deepseek.com",
    timeout_seconds=30,
    async_evaluation=True
)
```

---

## Roadmap

### Short-Term (v0.7)
- [x] Core DeepEval integration
- [x] Chat, explanation, router tests
- [x] GitHub Actions CI/CD
- [ ] Causal/Bayesian evaluation tests
- [ ] Frontend quality display

### Medium-Term (v0.8)
- [ ] Quality-aware caching
- [ ] Neo4j quality score persistence
- [ ] Kafka audit event extension
- [ ] Executive dashboard metrics

### Long-Term (v1.0)
- [ ] Real-time quality monitoring
- [ ] Automated quality regression alerts
- [ ] Human feedback loop integration
- [ ] Domain-specific evaluation fine-tuning

---

## References

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [CARF UIX Interaction Guidelines](./CARF_UIX_INTERACTION_GUIDELINES.md)
- [LLM Agentic Strategy](./LLM_AGENTIC_STRATEGY.md)
- [EU AI Act Compliance](https://artificialintelligenceact.eu/)
