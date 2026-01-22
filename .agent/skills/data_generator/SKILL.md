---
description: Generate realistic test datasets with configurable parameters for causal/Bayesian analysis demos
---

# CARF Data Generator Skill

## Purpose
Generate authentic simulated datasets with known ground truth for testing and demonstrating CARF analysis capabilities.

## When to Use
- Creating demo data for scenarios
- Generating test data with known causal effects
- Building datasets for unit testing
- Allowing users to create custom test data

## Generator Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `n_rows` | int | Number of observations (100-10,000) |
| `treatment` | string | Treatment variable name |
| `outcome` | string | Outcome variable name |
| `true_effect` | float | Ground truth causal effect |
| `confounders` | list | Confounder variable names |
| `confounding_strength` | float | Bias from confounders (0-1) |
| `noise_level` | float | Aleatoric uncertainty (0-1) |
| `seed` | int | Random seed for reproducibility |

## Python Generator Template

```python
# demo/generators/generate_causal_data.py
import numpy as np
import pandas as pd

def generate_causal_dataset(
    n_rows: int = 1000,
    treatment: str = "treatment",
    outcome: str = "outcome",
    true_effect: float = 0.5,
    confounders: list = None,
    confounding_strength: float = 0.3,
    noise_level: float = 0.2,
    seed: int = 42
) -> pd.DataFrame:
    """Generate dataset with known causal structure."""
    np.random.seed(seed)
    
    confounders = confounders or ["confounder_1", "confounder_2"]
    
    # Generate confounders
    data = {}
    for c in confounders:
        data[c] = np.random.normal(0, 1, n_rows)
    
    # Treatment affected by confounders
    confounder_effect = sum(
        confounding_strength * data[c] for c in confounders
    )
    data[treatment] = (
        confounder_effect + 
        np.random.binomial(1, 0.5, n_rows)
    ).clip(0, 1)
    
    # Outcome affected by treatment AND confounders
    data[outcome] = (
        true_effect * data[treatment] +
        confounding_strength * sum(data[c] for c in confounders) / len(confounders) +
        noise_level * np.random.normal(0, 1, n_rows)
    )
    
    return pd.DataFrame(data)
```

## Scenario-Specific Generators

### Scope 3 Attribution
```python
generate_scope3_dataset(
    n_suppliers=247,
    treatment="sustainability_program",
    outcome="emissions_kgco2",
    true_effect=-0.42,
    confounders=["industry", "supplier_size", "region"],
)
```

### Discount Churn
```python
generate_churn_dataset(
    n_customers=1000,
    treatment="discount_applied",
    outcome="churned",
    true_effect=-0.15,
    confounders=["tenure", "monthly_charges", "contract_type"],
)
```

### Grid Stability
```python
generate_grid_dataset(
    n_observations=500,
    treatment="renewable_share",
    outcome="frequency_deviation",
    true_effect=0.08,
    confounders=["time_of_day", "season", "demand_level"],
)
```

## Frontend Data Generation Wizard

### UI Flow
```
Step 1: Choose base scenario or start blank
Step 2: Set row count (slider: 100 - 10,000)
Step 3: Define treatment/outcome variables
Step 4: Set true effect size (for validation)
Step 5: Configure noise and confounding
Step 6: Generate & Preview
Step 7: Download or send to API
```

### API Endpoint (Planned)

```python
# POST /generate-dataset
class GenerateDatasetRequest(BaseModel):
    template: str  # "blank" | "scope3" | "churn" | "grid"
    n_rows: int = Field(1000, ge=100, le=10000)
    true_effect: float = Field(0.5, ge=-1, le=1)
    noise_level: float = Field(0.2, ge=0, le=1)
    seed: int | None = None
```

## Backend Integration Status

| Feature | Endpoint | Status |
|---------|----------|--------|
| Dataset upload | `POST /datasets` | ✅ Available |
| Dataset list | `GET /datasets` | ✅ Available |
| Dataset preview | `GET /datasets/{id}/preview` | ✅ Available |
| Generate dataset | `POST /generate-dataset` | ⚠️ PLANNED |

## Validation Patterns

After generating data, verify:
1. Run causal analysis → effect estimate ≈ true_effect
2. Check refutation tests pass
3. Verify confounders are detected
4. Confirm sample size matches

## File Output Locations

| Output | Path |
|--------|------|
| Scenario payloads | `demo/payloads/{scenario}.json` |
| Generated CSVs | `var/datasets/{id}.csv` |
| Generator scripts | `demo/generators/` |
