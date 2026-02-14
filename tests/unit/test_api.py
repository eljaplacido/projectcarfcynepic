"""Unit tests for FastAPI endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

import src.main as main_module
import src.api.routers.datasets as datasets_router
from src.services.dataset_store import DatasetStore


@pytest.fixture
def dataset_store():
    """Provide a dataset store backed by a workspace temp directory."""
    base_root = Path("var") / "pytest_dataset_store" / str(uuid4())
    base_root.mkdir(parents=True, exist_ok=True)
    return DatasetStore(base_dir=base_root)


@pytest.fixture
def client(dataset_store, monkeypatch):
    """Create a TestClient with an isolated dataset store."""
    monkeypatch.setattr(datasets_router, "get_dataset_store", lambda: dataset_store)
    return TestClient(main_module.app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data


def test_domains_endpoint(client):
    response = client.get("/domains")
    assert response.status_code == 200
    data = response.json()
    names = {domain["name"] for domain in data["domains"]}
    assert names == {"Clear", "Complicated", "Complex", "Chaotic", "Disorder"}


def test_scenarios_endpoint(client):
    response = client.get("/scenarios")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert scenarios

    scenario_id = scenarios[0]["id"]
    detail = client.get(f"/scenarios/{scenario_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["scenario"]["id"] == scenario_id
    assert isinstance(payload["payload"], dict)


def test_dataset_lifecycle(client):
    create_payload = {
        "name": "Unit Test Dataset",
        "description": "Test dataset",
        "data": [
            {"region": "NA", "value": 10},
            {"region": "EU", "value": 12},
        ],
    }
    create_resp = client.post("/datasets", json=create_payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    dataset_id = created["dataset_id"]
    assert created["row_count"] == 2

    list_resp = client.get("/datasets")
    assert list_resp.status_code == 200
    listed = list_resp.json()["datasets"]
    assert any(item["dataset_id"] == dataset_id for item in listed)

    preview_resp = client.get(f"/datasets/{dataset_id}/preview?limit=1")
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["dataset_id"] == dataset_id
    assert preview["rows"] == [create_payload["data"][0]]


def test_query_endpoint(client):
    response = client.post("/query", json={"query": "What is 2 + 2?"})
    assert response.status_code == 200
    payload = response.json()
    # API uses camelCase serialization
    assert payload["sessionId"]
    assert payload["domain"]
    assert payload["reasoningChain"]


def test_query_validation_conflict(client):
    response = client.post(
        "/query",
        json={
            "query": "Test validation",
            "dataset_selection": {
                "dataset_id": "fake",
                "treatment": "a",
                "outcome": "b",
                "covariates": [],
                "effect_modifiers": [],
            },
            "causal_estimation": {
                "treatment": "a",
                "outcome": "b",
                "data": [{"a": 1, "b": 2}],
            },
        },
    )
    assert response.status_code == 400
