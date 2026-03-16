"""Monitoring API endpoint tests — Phase 18 drift, bias, convergence.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Tests all 7 endpoints in src/api/routers/monitoring.py using
httpx.AsyncClient with ASGITransport.
"""

import os
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """Provide a fresh FastAPI app instance with test mode enabled."""
    os.environ["CARF_TEST_MODE"] = "1"

    # Reset singletons so each test gets a clean state
    import src.services.drift_detector as dd_mod
    import src.services.bias_auditor as ba_mod
    import src.services.router_retraining_service as rr_mod

    dd_mod._drift_detector = None
    ba_mod._bias_auditor = None
    rr_mod._router_retraining_service = None

    from src.main import app
    return app


# ── GET /monitoring/drift ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_drift_status(app):
    """GET /monitoring/drift returns 200 with expected shape."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/monitoring/drift")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_observations" in data
    assert "baseline_established" in data
    assert "config" in data
    assert "baseline_distribution" in data
    assert "current_distribution" in data
    assert "alert_count" in data
    assert "snapshot_count" in data


# ── GET /monitoring/drift/history ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_drift_history(app):
    """GET /monitoring/drift/history returns 200 with snapshots list."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/monitoring/drift/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "snapshots" in data
    assert isinstance(data["snapshots"], list)


# ── POST /monitoring/drift/reset ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_drift_baseline(app):
    """POST /monitoring/drift/reset returns 200 with status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/monitoring/drift/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "baseline_reset"
    assert "new_status" in data
    assert "total_observations" in data["new_status"]


# ── GET /monitoring/bias-audit ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_bias_audit(app):
    """GET /monitoring/bias-audit returns 200 with BiasReport fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/monitoring/bias-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data
    assert "domain_distribution" in data
    assert "chi_squared_statistic" in data
    assert "chi_squared_p_value" in data
    assert "distribution_biased" in data
    assert "quality_by_domain" in data
    assert "overall_bias_detected" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)


# ── GET /monitoring/convergence ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_convergence_status(app):
    """GET /monitoring/convergence returns 200 with convergence shape."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/monitoring/convergence")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_epochs" in data
    assert "convergence" in data
    assert "config" in data
    assert "epsilon" in data["config"]
    assert "max_plateau_epochs" in data["config"]


# ── POST /monitoring/convergence/record — valid ───────────────────────


@pytest.mark.asyncio
async def test_record_convergence_valid(app):
    """POST /monitoring/convergence/record with valid accuracy returns 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/monitoring/convergence/record",
            json={"accuracy": 0.85},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert "convergence" in data
    assert "epoch" in data["convergence"]
    assert "recommendation" in data["convergence"]


# ── POST /monitoring/convergence/record — invalid (422) ───────────────


@pytest.mark.asyncio
async def test_record_convergence_invalid(app):
    """POST /monitoring/convergence/record with accuracy > 1.0 returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/monitoring/convergence/record",
            json={"accuracy": 1.5},
        )
    assert resp.status_code == 422


# ── GET /monitoring/status ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_monitoring_status(app):
    """GET /monitoring/status returns 200 with drift/bias/convergence keys."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/monitoring/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "drift" in data
    assert "bias" in data
    assert "convergence" in data
    # Drift sub-fields
    assert "total_observations" in data["drift"]
    # Bias sub-fields
    assert "overall_bias_detected" in data["bias"]
    assert "findings" in data["bias"]
    # Convergence sub-fields
    assert "total_epochs" in data["convergence"]
