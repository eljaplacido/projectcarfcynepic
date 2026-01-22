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
