# CYNEPIC Integration Guide

## Overview

This guide details how to integrate the **CYNEPIC Architecture** (Neuro-Symbolic-Causal Agentic System) into existing enterprise infrastructures, including Cloud Platforms, ERP systems, and SaaS applications.

## 1. Integration Patterns

### A. REST API (Synchronous)
Best for: Interactive dashboards, chat bots, and real-time decision support.

**Endpoint**: `POST /query`
**Pattern**:
1. Client sends natural language query + context context.
2. CYNEPIC routes, analyses, and reasoning.
3. Returns structured JSON with `result`, `confidence`, and `actions`.

### B. Event-Driven (Asynchronous)
Best for: High-volume transaction monitoring, automated compliance checks.

**mechanism**: Kafka / Webhooks
**Pattern**:
1. Upstream (e.g., SAP, Salesforce) emits event -> Kafka Topic `orders.created`.
2. CYNEPIC Consumer reads event.
3. Runs Guardian Policy Check.
4. If `risk > threshold`, trigger HumanEscalation.
5. Else, publish to `orders.approved`.

### C. Batch Processing
Best for: Nightly causal analysis of historical data.

**Pattern**:
1. Upload CSV/Parquet to `/datasets`.
2. Trigger `/simulations/run` with scenario config.
3. Retrieve results via `/simulations/compare`.

---

## 2. ERP Integration Example (SAP/Oracle)

**Scenario**: Automate "Procurement Approval" based on Supplier Risk Causal Score.

**Steps**:
1.  **Data Ingestion**:
    *   Export Supplier Performance data to CYNEPIC via `/datasets`.
    *   Variables: `delivery_delay`, `financial_health`, `region_risk`.

2.  **API Hook**:
    *   In ERP workflow, call CYNEPIC API before final approval.

    ```bash
    curl -X POST https://cynepic-api.internal/query \
      -H "Authorization: Bearer <token>" \
      -d '{
        "query": "Assess risk for Supplier X PO #12345",
        "context": {
            "supplier_id": "SUP-99",
            "po_amount": 50000,
            "region": "APAC"
        }
      }'
    ```

3.  **Decision Logic**:
    *   If `response.guardian_verdict == "APPROVED"`, auto-approve in ERP.
    *   If `REJECTED`, flag for review.

---

## 3. Cloud Deployment (AWS/Azure/GCP)

### Container Architecture
*   **API Service**: Stateless Docker container (FastAPI). Scale horizontally.
*   **Dashboard**: React SPA (S3/CloudFront or Nginx).
*   **State Store**:
    *   Neo4j (Managed AuraDB or Self-Host EC2).
    *   Redis (ElastiCache).

### Security Best Practices
1.  **Identity**: Use IAM roles for service-to-service auth.
2.  **Secrets**: Inject `DEEPSEEK_API_KEY` via Secrets Manager (not env vars).
3.  **Network**: Run API/DB in private subnets; expose only via Load Balancer/WAF.

---

## 4. Design Questions for Integrators

When planning your integration, answer these:

1.  **Epistemic Uncertainty**: "Do we have enough data validity to trust the causal model?"
    *   *Mitigation*: Use the `confidence_score` in the API response to gate automated actions.
2.  **Latency Budget**: "Can we wait 10-20 seconds for full Causal + Bayesian analysis?"
    *   *Mitigation*: Use "Clear" domain routing for simple lookups (<1s).
3.  **Human-in-the-Loop**: "Who resolves 'Disorder' or 'Chaotic' queries?"
    *   *Mitigation*: Configure HumanLayer channels (Slack/Teams) correctly in `.env`.

---

## 5. Sample Integration Code (Python Client)

```python
import requests

def check_po_risk(po_data):
    response = requests.post(
        "http://localhost:8000/query",
        json={
            "query": f"Analyze risk for PO {po_data['id']}",
            "context": po_data
        }
    )
    result = response.json()

    if result['guardian']['status'] == 'pass':
        return "APPROVE"
    else:
        return f"REVIEW: {result['guardian']['reason']}"
```

---

## 6. MCP Agentic Integration (Phase 13+)

CARF exposes **18 cognitive tools** via its Model Context Protocol (MCP) server for integration with external AI agents (Claude, GPT, custom agents).

### Available MCP Tools

| Module | Tools | Purpose |
|--------|-------|---------|
| **router** | `classify_query`, `get_routing_config` | Cynefin domain classification |
| **causal** | `causal_analyze`, `estimate_effect` | Causal inference via DoWhy/EconML |
| **bayesian** | `bayesian_infer`, `update_beliefs` | Bayesian posterior estimation |
| **guardian** | `check_policy`, `evaluate_risk` | Policy compliance checking |
| **oracle** | `fast_predict`, `compare_strategies` | ChimeraOracle fast causal predictions |
| **memory** | `query_experience_buffer`, `search_memory` | Semantic memory retrieval |
| **reflector** | `reflector_repair` | Self-correction on rejected actions |

### MCP Server Setup
```bash
# Start MCP server (alongside FastAPI)
python -m src.mcp
```

### Key Safety Boundary
MCP tools expose CARF's **analytical capabilities** as read-mostly services. External agents **cannot** use MCP tools to modify CARF's policies, configuration, or internal state. The `reflector_repair` tool allows external agents to use CARF's repair logic on *their* proposed actions, not on CARF's internals.

---

## 7. Phase 17 API Endpoints

### Causal World Model & Neurosymbolic Reasoning

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/world-model/counterfactual` | Counterfactual reasoning from natural language |
| POST | `/world-model/counterfactual/compare` | Multi-scenario comparison |
| POST | `/world-model/counterfactual/attribute` | Causal attribution with but-for tests |
| POST | `/world-model/simulate` | Forward simulation with do-calculus interventions |
| POST | `/world-model/neurosymbolic/reason` | Full neural-symbolic reasoning loop |
| POST | `/world-model/neurosymbolic/validate` | Claim validation against symbolic KB |
| GET | `/world-model/h-neuron/status` | H-Neuron sentinel configuration |
| POST | `/world-model/h-neuron/assess` | Run hallucination risk assessment |
| POST | `/world-model/retrieve/neurosymbolic` | NeSy-augmented retrieval (3-layer) |
| POST | `/world-model/analyze-deep` | Combined CARF + counterfactual + NeSy + simulation |

### Governance (18 endpoints)

Key endpoints under `/governance/*`:
- `GET /governance/domains` — List governance domains
- `POST /governance/policies/extract` — LLM-assisted policy extraction
- `GET /governance/conflicts` — Cross-domain conflict detection
- `GET /governance/compliance/{framework}` — Compliance scoring (EU AI Act, CSRD, GDPR, ISO 27001)
- `GET /governance/cost/breakdown` — LLM token cost analysis
- `GET /governance/audit` — Audit trail

### Authentication (Phase 17)

Production deployments use Firebase JWT authentication:
```bash
# Authenticated request
curl -X POST https://api.example.com/query \
  -H "Authorization: Bearer <firebase_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze supplier risk"}'
```

Local development bypasses auth automatically.

---

## 8. Deployment Profiles

CARF supports three deployment profiles via `CARF_PROFILE` environment variable:

| Profile | Auth | Rate Limit | CORS | Use Case |
|---------|------|-----------|------|----------|
| `research` | None | None | `*` | Local development, experimentation |
| `staging` | API key | 100 req/min | Configured origins | Testing, demo |
| `production` | API key + Firebase JWT | 50 req/min | Strict origins | Enterprise deployment |
