---
description: Execute end-to-end CARF cognitive pipeline for analytical queries (Cynefin routing, causal/Bayesian analysis, Guardian policy check)
---

# CARF Query Processor Skill

## Purpose
Process analytical queries through the full CARF 4-layer cognitive pipeline:
1. **Router** → Classifies query into Cynefin domain
2. **Cognitive Mesh** → Routes to appropriate domain agent
3. **Reasoning Services** → Causal/Bayesian analysis
4. **Guardian** → Policy enforcement and human escalation

## When to Use
- When users ask causal questions ("Why did X cause Y?")
- Uncertainty quantification requests ("How confident are we?")
- Decision-support queries ("Should we take action X?")
- Any query requiring the full CARF reasoning chain

## Prerequisites
- API server running: `uvicorn src.main:app --port 8000`
- `.env` configured with `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`

## Execution Steps

### 1. Submit Query via API

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why did our costs increase by 15%?",
    "context": {
      "domain": "finance",
      "time_period": "Q4-2025"
    }
  }'
```

### 2. With Scenario Payload

Load a pre-configured scenario:

```bash
# Get available scenarios
curl http://localhost:8000/scenarios

# Get scenario payload
curl http://localhost:8000/scenarios/scope3_attribution

# Submit with scenario context
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What causes supplier emissions to increase?",
    "scenario_id": "scope3_attribution"
  }'
```

### 3. With Dataset Selection

For causal estimation with real data:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the effect of discount on churn?",
    "dataset_selection": {
      "dataset_id": "demo_churn",
      "treatment": "discount_applied",
      "outcome": "churned",
      "covariates": ["tenure", "monthly_charges"]
    }
  }'
```

## Response Schema

```json
{
  "session_id": "uuid",
  "domain": "Complicated",
  "domain_confidence": 0.89,
  "domain_entropy": 0.34,
  "guardian_verdict": "approved",
  "response": "Analysis summary...",
  "requires_human": false,
  "reasoning_chain": [
    {"node": "router", "action": "Classified", "confidence": "high"},
    {"node": "causal_analyst", "action": "Estimated effect", "confidence": "medium"}
  ],
  "causal_result": {
    "effect": 0.15,
    "unit": "percentage points",
    "ci_low": 0.08,
    "ci_high": 0.22,
    "refutations_passed": 3,
    "refutations_total": 3
  },
  "bayesian_result": null,
  "guardian_result": {
    "verdict": "approved",
    "policies_passed": 5,
    "policies_total": 5,
    "risk_level": "low"
  }
}
```

## Domain Routing Logic

| Domain | Confidence | Entropy | Agent |
|--------|------------|---------|-------|
| Clear | > 0.95 | < 0.2 | `deterministic_runner` |
| Complicated | > 0.85 | < 0.5 | `causal_analyst` |
| Complex | > 0.7 | 0.5-0.8 | `bayesian_explorer` |
| Chaotic | Any | > 0.9 | `circuit_breaker` |
| Disorder | < 0.85 | Any | `human_escalation` |

## Python API

For direct invocation:

```python
from src.workflows.graph import run_carf

result = await run_carf(
    user_input="Why did costs increase 15%?",
    context={"domain": "finance"}
)

print(f"Domain: {result.cynefin_domain}")
print(f"Response: {result.final_response}")
print(f"Causal Evidence: {result.causal_evidence}")
```

## Troubleshooting

### Query Routed to Disorder
- Low confidence from router (< 0.85)
- Ambiguous or vague query
- **Solution:** Rephrase with more specificity

### Guardian Rejected Action
- Policy violation detected
- Check `guardian_result.violations` in response
- May require human approval via HumanLayer

### Timeout on Complex Queries
- PyMC inference can be slow
- Increase timeout or reduce sample count
- Check for large dataset sizes
