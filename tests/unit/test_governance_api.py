# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for Governance API endpoints."""

import os
import pytest

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.routers import governance


def _make_governance_app() -> FastAPI:
    """Build a minimal FastAPI app with the governance router registered."""
    test_app = FastAPI()
    test_app.include_router(governance.router)
    return test_app


@pytest.fixture
def client():
    """Create test client with governance router always registered."""
    return TestClient(_make_governance_app())


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset governance singletons between tests."""
    import src.services.federated_policy_service as fps
    import src.services.governance_service as gs
    import src.services.cost_intelligence_service as cis
    fps._federated_service = None
    gs._governance_service = None
    cis._cost_service = None
    yield
    fps._federated_service = None
    gs._governance_service = None
    cis._cost_service = None


class TestDomainEndpoints:
    def test_list_domains(self, client):
        resp = client.get("/governance/domains")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_domain(self, client):
        resp = client.post("/governance/domains", json={
            "domain_id": "test_domain",
            "display_name": "Test Domain",
            "description": "A test domain",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["domain_id"] == "test_domain"
        assert data["display_name"] == "Test Domain"

    def test_get_domain(self, client):
        client.post("/governance/domains", json={
            "domain_id": "get_test",
            "display_name": "Get Test",
        })
        resp = client.get("/governance/domains/get_test")
        assert resp.status_code == 200
        assert resp.json()["domain_id"] == "get_test"

    def test_get_domain_not_found(self, client):
        resp = client.get("/governance/domains/nonexistent")
        assert resp.status_code == 404

    def test_update_domain(self, client):
        client.post("/governance/domains", json={
            "domain_id": "upd_test",
            "display_name": "Original",
        })
        resp = client.put("/governance/domains/upd_test", json={
            "display_name": "Updated",
        })
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated"


class TestPolicyEndpoints:
    def test_list_policies(self, client):
        resp = client.get("/governance/policies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_policy(self, client):
        # First create domain
        client.post("/governance/domains", json={
            "domain_id": "pol_domain",
            "display_name": "Policy Domain",
        })
        resp = client.post("/governance/policies", json={
            "name": "test_policy",
            "domain_id": "pol_domain",
            "namespace": "pol_domain.test",
            "rules": [{"name": "rule1", "condition": {}, "constraint": {}, "message": "test"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test_policy"

    def test_get_policy(self, client):
        client.post("/governance/domains", json={"domain_id": "gp", "display_name": "GP"})
        client.post("/governance/policies", json={
            "name": "gp_policy",
            "domain_id": "gp",
            "namespace": "gp.policy",
        })
        resp = client.get("/governance/policies/gp.policy")
        assert resp.status_code == 200

    def test_delete_policy(self, client):
        client.post("/governance/domains", json={"domain_id": "dp", "display_name": "DP"})
        client.post("/governance/policies", json={
            "name": "del_policy",
            "domain_id": "dp",
            "namespace": "dp.del",
        })
        resp = client.delete("/governance/policies/dp.del")
        assert resp.status_code == 204


class TestConflictEndpoints:
    def test_list_conflicts(self, client):
        resp = client.get("/governance/conflicts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestComplianceEndpoints:
    def test_get_compliance_eu_ai_act(self, client):
        resp = client.get("/governance/compliance/eu_ai_act")
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework"] == "eu_ai_act"
        assert 0 <= data["overall_score"] <= 1
        assert len(data["articles"]) > 0

    def test_get_compliance_csrd(self, client):
        resp = client.get("/governance/compliance/csrd")
        assert resp.status_code == 200
        assert resp.json()["framework"] == "csrd"

    def test_get_compliance_gdpr(self, client):
        resp = client.get("/governance/compliance/gdpr")
        assert resp.status_code == 200

    def test_get_compliance_iso_27001(self, client):
        resp = client.get("/governance/compliance/iso_27001")
        assert resp.status_code == 200

    def test_get_compliance_invalid_framework(self, client):
        resp = client.get("/governance/compliance/invalid")
        assert resp.status_code == 400


class TestCostEndpoints:
    def test_get_cost_aggregate(self, client):
        resp = client.get("/governance/cost/aggregate")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "total_cost" in data

    def test_get_cost_roi(self, client):
        resp = client.get("/governance/cost/roi")
        assert resp.status_code == 200
        data = resp.json()
        assert "roi_percentage" in data

    def test_get_cost_pricing(self, client):
        resp = client.get("/governance/cost/pricing")
        assert resp.status_code == 200
        data = resp.json()
        assert "deepseek" in data

    def test_update_pricing(self, client):
        resp = client.put("/governance/cost/pricing", json={
            "provider": "deepseek",
            "input_price": 0.5,
            "output_price": 1.0,
        })
        assert resp.status_code == 200

    def test_get_cost_breakdown_not_found(self, client):
        resp = client.get("/governance/cost/breakdown/nonexistent")
        assert resp.status_code == 404


class TestAuditEndpoints:
    def test_get_audit_timeline(self, client):
        resp = client.get("/governance/audit")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestHealthEndpoint:
    def test_governance_health(self, client):
        resp = client.get("/governance/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert "status" in data


class TestSemanticGraphEndpoints:
    def test_get_semantic_graph(self, client):
        # Seed one domain/policy so graph has deterministic structure
        client.post("/governance/domains", json={
            "domain_id": "procurement",
            "display_name": "Procurement",
        })
        client.post("/governance/policies", json={
            "name": "Spend Control",
            "domain_id": "procurement",
            "namespace": "procurement.spend_control",
            "rules": [{"name": "max_spend", "condition": {}, "constraint": {"max_amount": 100000}, "message": "Cap spend"}],
        })

        resp = client.get("/governance/semantic-graph")
        assert resp.status_code == 200
        payload = resp.json()
        assert "nodes" in payload
        assert "edges" in payload
        assert "stats" in payload
        assert "explainability" in payload
        assert "why_this" in payload["explainability"]
        assert "how_confident" in payload["explainability"]
        assert "based_on" in payload["explainability"]

    def test_get_semantic_graph_board_not_found(self, client):
        resp = client.get("/governance/semantic-graph?board_id=missing-board")
        assert resp.status_code == 404


class TestPolicyExtractionEndpoints:
    def test_extract_policies_from_text_returns_explainability(self, client):
        resp = client.post(
            "/governance/policies/extract",
            json={
                "text": "If supplier risk > 0.8, procurement approval is required.",
                "source_name": "test_policy_note",
                "target_domain": "procurement",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["source_name"] == "test_policy_note"
        assert payload["target_domain"] == "procurement"
        assert "extraction_confidence_avg" in payload
        assert "explainability" in payload
        assert "why_this" in payload["explainability"]
        assert "how_confident" in payload["explainability"]
        assert "based_on" in payload["explainability"]

    def test_extract_policies_from_text_parses_fenced_json(self, client, monkeypatch):
        def _fake_invoke(prompt: str) -> str:
            return """```json
[
  {
    "name": "supplier_risk_gate",
    "condition": {"supplier_risk": {"gt": 0.8}},
    "constraint": {"approval_required": true},
    "message": "Require approval for high supplier risk",
    "severity": "high",
    "confidence": 0.9,
    "rationale": "High supplier risk requires governance review.",
    "evidence": ["supplier risk > 0.8", "approval is required"]
  }
]
```"""

        monkeypatch.setattr(governance, "_invoke_extraction_model", _fake_invoke)
        resp = client.post(
            "/governance/policies/extract",
            json={"text": "supplier risk > 0.8 then approval is required"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["rules_extracted"] == 1
        assert payload["rules"][0]["name"] == "supplier_risk_gate"
        assert payload["rules"][0]["severity"] == "high"
        assert payload["rules"][0]["confidence"] == 0.9
        assert payload["rules"][0]["evidence"]

    def test_extract_policies_from_text_reports_error(self, client, monkeypatch):
        def _raise_error(prompt: str) -> str:
            raise RuntimeError("model unavailable")

        monkeypatch.setattr(governance, "_invoke_extraction_model", _raise_error)
        resp = client.post(
            "/governance/policies/extract",
            json={"text": "dummy"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["rules_extracted"] == 0
        assert payload["error"] is not None
