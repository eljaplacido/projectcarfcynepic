# CARF Quick Start Guide

Get CARF running and test the demo scenarios in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- (Optional) Docker and Docker Compose

## 1. Installation

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/projectcarf.git
cd projectcarf

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install with all extras
pip install -e ".[dev,dashboard,causal,bayesian]"
```

### Configure Environment

```bash
# Create environment file
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required for full functionality
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key-here

# OR use OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here
```

**No API Key?** Run in test mode:
```bash
export CARF_TEST_MODE=1  # Uses offline stubs
```

## 2. Start the Services

### Option A: Two Terminals (Recommended for Development)

**Terminal 1 - API Server:**
```bash
cd projectcarf
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m src.main
```
API will be available at http://localhost:8000

**Terminal 2 - Dashboard:**
```bash
cd projectcarf
source .venv/bin/activate
streamlit run src/dashboard/app.py
```
Dashboard will open at http://localhost:8501

### Option B: Docker Compose (Full Stack)

```bash
docker compose up --build
```

Services:
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- Neo4j: http://localhost:7474 (user: neo4j, password: carf_password)

## 3. Test the Demo Scenarios

### Via Dashboard (Recommended)

1. Open http://localhost:8501
2. Select a scenario from the dropdown (top-right)
3. Click "Analyze" to run the pipeline
4. Explore the results across three views:
   - **End-User**: Query, simulation controls, analysis results
   - **Developer**: Execution trace, DAG structure, state snapshots
   - **Executive**: KPIs, proposed actions, policy summary

### Via API (curl)

**Health Check:**
```bash
curl http://localhost:8000/health
```

**List Demo Scenarios:**
```bash
curl http://localhost:8000/scenarios
```

**Run Scope 3 Attribution Analysis:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which suppliers have the highest emissions reduction potential?",
    "context": {"scenario": "scope3_attribution"},
    "causal_estimation": {
      "treatment": "supplier_program",
      "outcome": "scope3_emissions",
      "covariates": ["region", "market_conditions"],
      "data": [
        {"supplier_program": 1, "scope3_emissions": -85, "region": "EU", "market_conditions": 0.5},
        {"supplier_program": 0, "scope3_emissions": 10, "region": "EU", "market_conditions": 0.5}
      ]
    }
  }'
```

**Run Bayesian Conversion Rate Update:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Update belief on our conversion rate",
    "bayesian_inference": {
      "successes": 42,
      "trials": 100
    }
  }'
```

## 4. Available Demo Scenarios

| ID | Name | Description | Type |
|----|------|-------------|------|
| `scope3_attribution` | Scope 3 Attribution | Supplier sustainability impact analysis | Causal |
| `causal_discount_churn` | Discount vs Churn | Impact of discounts on customer churn | Causal |
| `bayesian_conversion_rate` | Conversion Belief | Update beliefs about conversion rates | Bayesian |
| `renewable_energy_roi` | Renewable Energy ROI | ROI from solar investments | Causal |
| `shipping_carbon_footprint` | Shipping Carbon | Freight mode emissions impact | Causal |

**Load scenario details:**
```bash
curl http://localhost:8000/scenarios/scope3_attribution
```

## 5. Using Your Own Data

### Option A: Inline Data in API Request

Include your data directly in the request:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the impact of marketing spend on sales?",
    "causal_estimation": {
      "treatment": "marketing_spend",
      "outcome": "sales",
      "covariates": ["region", "season"],
      "data": [
        {"marketing_spend": 1000, "sales": 5000, "region": "north", "season": "Q1"},
        {"marketing_spend": 2000, "sales": 8000, "region": "north", "season": "Q1"},
        {"marketing_spend": 500, "sales": 3000, "region": "south", "season": "Q2"},
        {"marketing_spend": 1500, "sales": 6500, "region": "south", "season": "Q2"}
      ]
    }
  }'
```

**Data Limits:**
- Causal estimation: max 5,000 rows
- Bayesian observations: max 10,000 values

### Option B: Upload Dataset via API

**Step 1: Upload your data**
```bash
curl -X POST http://localhost:8000/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_sales_data",
    "description": "Q1 2024 sales data",
    "data": [
      {"marketing_spend": 1000, "sales": 5000, "region": "north"},
      {"marketing_spend": 2000, "sales": 8000, "region": "north"},
      {"marketing_spend": 500, "sales": 3000, "region": "south"}
    ]
  }'
```

Response:
```json
{
  "dataset_id": "ds_abc123",
  "name": "my_sales_data",
  "row_count": 3,
  "column_names": ["marketing_spend", "sales", "region"]
}
```

**Step 2: Use the dataset in analysis**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze marketing impact on sales",
    "dataset_selection": {
      "dataset_id": "ds_abc123",
      "treatment": "marketing_spend",
      "outcome": "sales",
      "covariates": ["region"]
    }
  }'
```

### Option C: Upload via Dashboard

1. Open the dashboard at http://localhost:8501
2. In the **End-User** view, look for "Data Sources" section
3. Upload your CSV file
4. Map columns to treatment, outcome, and covariates
5. Run analysis

### Data Format Requirements

**For Causal Analysis:**
```json
{
  "treatment": "column_name",      // Binary or continuous treatment variable
  "outcome": "column_name",        // Outcome to measure
  "covariates": ["col1", "col2"],  // Control variables
  "effect_modifiers": ["col3"],    // Optional: heterogeneous effects
  "data": [...]                    // List of rows or dict of columns
}
```

**For Bayesian Inference:**
```json
{
  "observations": [1.2, 1.5, 1.3, 1.4],  // Continuous observations
  // OR for binomial model:
  "successes": 42,
  "trials": 100
}
```

## 6. Understanding the Output

### API Response Structure

```json
{
  "session_id": "uuid-here",
  "domain": "complicated",           // Cynefin classification
  "domain_confidence": 0.87,         // 0-1 confidence score
  "guardian_verdict": "approved",    // approved/rejected/requires_escalation
  "response": "Analysis summary...", // Natural language response
  "requires_human": false,           // Human escalation flag
  "reasoning_chain": [               // Audit trail
    {"node": "router", "action": "classified as complicated", "confidence": "high"},
    {"node": "causal_analyst", "action": "estimated effect", "confidence": "high"},
    {"node": "guardian", "action": "policy check passed", "confidence": "high"}
  ],
  "error": null
}
```

### Dashboard Components

| Component | Description |
|-----------|-------------|
| **Cynefin Classification** | Domain scores, routing decision, entropy |
| **Bayesian Belief State** | Prior/posterior distribution, uncertainty decomposition |
| **Causal DAG** | Interactive graph of causal relationships |
| **Causal Analysis Results** | Effect estimate, confidence interval, refutation tests |
| **Guardian Policy Check** | Policy violations, approval workflow |
| **Execution Trace** | Timeline of pipeline steps |

## 7. Running Tests

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/eval/ -v
```

### Manual Test Suite
```bash
python test_carf.py
```

This runs 5 comprehensive tests:
1. LLM configuration
2. Router classification
3. Causal inference engine
4. Bayesian inference engine
5. Full pipeline end-to-end

### Test Coverage
```bash
pytest tests/ -v --cov=src --cov-report=html
open htmlcov/index.html
```

## 8. Troubleshooting

### API Not Starting
```bash
# Check port 8000 is free
lsof -i :8000

# Check logs
python -m src.main 2>&1 | tee carf.log
```

### Dashboard Connection Error
```bash
# Ensure API is running first
curl http://localhost:8000/health

# Set API URL if different
export CARF_API_URL=http://localhost:8000
streamlit run src/dashboard/app.py
```

### LLM Errors
```bash
# Verify API key
echo $DEEPSEEK_API_KEY

# Use test mode
export CARF_TEST_MODE=1
```

### Import Errors
```bash
# Reinstall dependencies
pip install -e ".[dev,dashboard,causal,bayesian]" --force-reinstall
```

## 9. Next Steps

1. **Explore the Demo Scenarios**: Try each scenario to understand different analysis types
2. **Upload Your Data**: Test with your own datasets
3. **Customize Policies**: Edit `config/policies.yaml` to add business rules
4. **Integrate HITL**: Set up HumanLayer for approval workflows
5. **Deploy**: Use Docker Compose for production deployment

## Support

- **Issues**: https://github.com/yourusername/projectcarf/issues
- **Docs**: See `/docs` folder for detailed documentation
- **API Docs**: http://localhost:8000/docs (Swagger UI when running)
