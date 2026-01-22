---
description: Manage CARF demo scenarios (list, get, create) for testing and demonstrations
---

# CARF Scenario Manager Skill

## Purpose
Create, list, and load demo scenarios for the CARF cockpit.
Scenarios provide pre-configured causal/Bayesian analysis contexts.

## When to Use
- Setting up demos for stakeholders
- Testing specific analysis workflows
- Creating new example use cases
- Loading sample data for development

## Available Scenarios

| ID | Name | Domain | Analysis Type |
|----|------|--------|---------------|
| `scope3_attribution` | Scope 3 Emissions | Complicated | Causal |
| `causal_discount_churn` | Discount → Churn | Complicated | Causal |
| `bayesian_conversion_rate` | Conversion Rate | Complex | Bayesian |
| `supply_chain_disruption` | Supply Chain Risk | Complex | Bayesian |
| `financial_anomaly` | Cost Anomaly | Complicated | Causal |

## Execution Steps

### 1. List All Scenarios

```bash
curl http://localhost:8000/scenarios
```

**Response:**
```json
{
  "scenarios": [
    {
      "id": "scope3_attribution",
      "name": "Scope 3 Emissions Attribution",
      "description": "Analyze supplier emission drivers",
      "payload_path": "demo/payloads/scope3_attribution.json"
    }
  ]
}
```

### 2. Get Scenario Details

```bash
curl http://localhost:8000/scenarios/scope3_attribution
```

**Response:**
```json
{
  "scenario": {
    "id": "scope3_attribution",
    "name": "Scope 3 Emissions Attribution",
    "description": "..."
  },
  "payload": {
    "query": "What causes supplier emissions to increase?",
    "context": {
      "treatment": "supplier_size",
      "outcome": "emissions_kgco2",
      "confounders": ["industry", "location"]
    },
    "causal_estimation": {
      "data": [...],
      "treatment": "supplier_size",
      "outcome": "emissions_kgco2"
    }
  }
}
```

### 3. Use Scenario in Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the causal effect of supplier size on emissions?",
    "scenario_id": "scope3_attribution"
  }'
```

### 4. Create New Scenario

**File Location:** `demo/scenarios.json`

Add new scenario entry:
```json
{
  "id": "new_scenario_id",
  "name": "New Scenario Name",
  "description": "Brief description",
  "payload_path": "demo/payloads/new_scenario.json"
}
```

Create payload file:
```json
// demo/payloads/new_scenario.json
{
  "query": "Default query for this scenario",
  "context": {
    "domain": "business_domain",
    "custom_key": "custom_value"
  },
  "causal_estimation": {
    "data": [
      {"treatment": 1, "outcome": 10, "covariate": 5},
      {"treatment": 0, "outcome": 8, "covariate": 5}
    ],
    "treatment": "treatment",
    "outcome": "outcome",
    "covariates": ["covariate"]
  }
}
```

### 5. Run Scenario Simulation (New)

Run "what-if" simulations on scenarios using the new simulation engine.

```bash
POST /simulations/run
{
  "scenarios": [
    {
      "name": "Baseline",
      "interventions": [],
      "baseline_dataset_id": "scope3_attribution"
    },
    {
      "name": "Increase Renewables",
      "interventions": [{"variable": "renewable_pct", "value": 0.4}],
      "baseline_dataset_id": "scope3_attribution"
    }
  ]
}
```

### 6. Compare Simulation Results

Compare metrics across multiple simulation runs.

```bash
POST /simulations/compare
{
  "scenario_ids": ["sim_baseline_123", "sim_renewables_456"]
}
```

## Scenario Payload Schema

```typescript
interface ScenarioPayload {
  query: string;                    // Default query text
  context?: {
    domain?: string;                // Business domain hint
    [key: string]: any;             // Custom context
  };
  causal_estimation?: {
    data: Record<string, any>[];    // Tabular data rows
    treatment: string;              // Treatment column name
    outcome: string;                // Outcome column name
    covariates?: string[];          // Covariate columns
  };
  bayesian_inference?: {
    observations?: number[];        // Observed values
    successes?: number;             // For binomial model
    trials?: number;                // For binomial model
    draws?: number;                 // MCMC samples
  };
}
```

## React Cockpit Integration

Scenarios are loaded in `DashboardHeader.tsx`:

```tsx
// Fetch scenarios on mount
const [scenarios, setScenarios] = useState<Scenario[]>([]);

useEffect(() => {
  fetch('/scenarios')
    .then(res => res.json())
    .then(data => setScenarios(data.scenarios));
}, []);

// Scenario selector dropdown
<select onChange={(e) => loadScenario(e.target.value)}>
  {scenarios.map(s => (
    <option key={s.id} value={s.id}>{s.name}</option>
  ))}
</select>
```

## Validation

After adding scenarios:
1. Restart API server
2. Call `GET /scenarios` to verify listing
3. Call `GET /scenarios/{id}` to verify payload loads
4. Submit query with `scenario_id` to verify integration
5. Test simulation endpoints `POST /simulations/run` using the new scenarios
