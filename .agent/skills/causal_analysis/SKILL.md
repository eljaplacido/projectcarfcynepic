---
description: Run causal inference analysis using DoWhy/EconML on datasets (effect estimation, refutation tests)
---

# CARF Causal Analysis Skill

## Purpose
Perform causal inference using the DoWhy/EconML ecosystem.
Discovers causal structure, estimates treatment effects, and validates with refutation tests.

## When to Use
- Queries routed to "Complicated" domain
- Estimating causal effects from observational data
- Testing causal hypotheses with refutation
- Building causal DAGs for analysis

## Causal Inference Workflow

```mermaid
graph LR
    A[Query] --> B[Discover Structure]
    B --> C[Build DAG]
    C --> D[Estimate Effect]
    D --> E[Refutation Tests]
    E --> F[Interpretation]
```

## Execution Steps

### 1. Prepare Data

Data can be provided as:
- List of dicts: `[{"treatment": 1, "outcome": 10, ...}]`
- Column format: `{"treatment": [1,0,1], "outcome": [10,8,12]}`
- Dataset reference: `{"dataset_id": "registered_dataset_id"}`

### 2. Define Causal Hypothesis

```python
from src.services.causal import CausalHypothesis

hypothesis = CausalHypothesis(
    treatment="discount_applied",
    outcome="customer_churned",
    mechanism="Discount reduces churn risk",
    confounders=["tenure", "monthly_charges", "contract_type"]
)
```

### 3. Run Analysis via API

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the causal effect of discount on churn?",
    "causal_estimation": {
      "data": [
        {"discount": 1, "churned": 0, "tenure": 12},
        {"discount": 0, "churned": 1, "tenure": 6}
      ],
      "treatment": "discount",
      "outcome": "churned",
      "covariates": ["tenure"]
    }
  }'
```

### 4. Run Analysis via Python

```python
from src.services.causal import CausalInferenceEngine

engine = CausalInferenceEngine()

# Discover causal structure
hypothesis, graph = await engine.discover_causal_structure(
    query="What causes customer churn?",
    context={"domain": "telecom"}
)

# Estimate effect
result = await engine.estimate_effect(
    hypothesis=hypothesis,
    graph=graph,
    context={
        "causal_estimation": {
            "data": df.to_dict('records'),
            "treatment": "discount",
            "outcome": "churned"
        }
    }
)

print(f"Effect: {result.effect_estimate}")
print(f"CI: {result.confidence_interval}")
print(f"Passed Refutation: {result.passed_refutation}")
```

## Causal Result Schema

```json
{
  "causal_result": {
    "effect": 0.15,
    "unit": "percentage points",
    "p_value": 0.023,
    "ci_low": 0.08,
    "ci_high": 0.22,
    "description": "Discount reduces churn by ~15 percentage points",
    "refutations_passed": 3,
    "refutations_total": 3,
    "confounders_controlled": 2,
    "confounders_total": 3,
    "treatment": "discount",
    "outcome": "churned"
  }
}
```

## Refutation Tests

The engine runs these refutation tests:

| Test | Purpose | Pass Criteria |
|------|---------|---------------|
| Random Common Cause | Add random confounder | Effect stable |
| Placebo Treatment | Randomize treatment | Effect → 0 |
| Data Subset | Random 80% subset | Effect stable |

## DoWhy Estimation Methods

Default: `backdoor.linear_regression`

Available methods:
- `backdoor.linear_regression`
- `backdoor.propensity_score_matching`
- `backdoor.propensity_score_weighting`
- `iv.instrumental_variable`

Configure via:
```json
{
  "causal_estimation": {
    "method_name": "backdoor.propensity_score_matching",
    ...
  }
}
```

## Neo4j Persistence (Optional)

If Neo4j is configured, causal graphs are persisted:

```python
from src.services.neo4j_service import get_neo4j_service
from src.services.causal import CausalInferenceEngine

neo4j = get_neo4j_service()
engine = CausalInferenceEngine(neo4j_service=neo4j)

# Analysis results are automatically persisted
# Query historical analyses:
history = await engine.find_historical_analyses(
    treatment="discount",
    outcome="churned",
    limit=5
)
```

## Troubleshooting

### "No causal effect found"
- Check data has variance in treatment/outcome
- Verify confounder selection is correct
- May indicate no causal relationship exists

### Refutation Test Failed
- Causal claim may be spurious
- Check for missing confounders
- Consider different causal model

### DoWhy Import Error
```bash
pip install "carf[causal]"
# or
pip install dowhy econml causal-learn
```

## Best Practices

1. **Always specify confounders** - Omitted variable bias is common
2. **Check refutation tests** - Don't trust unrefuted estimates
3. **Use domain knowledge** - LLM-assisted discovery is a starting point
4. **Validate with stakeholders** - Causal claims require human review
