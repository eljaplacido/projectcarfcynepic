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
