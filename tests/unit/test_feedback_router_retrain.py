"""Tests for /feedback/retrain-router endpoint auto-apply behavior."""

from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")


@pytest.mark.anyio
async def test_retrain_router_applies_hints_when_requested():
    from httpx import ASGITransport, AsyncClient
    from src.main import app

    transport = ASGITransport(app=app)
    payload = {
        "min_samples": 1,
        "top_k": 5,
        "apply_to_router": True,
        "max_new_per_domain": 2,
    }

    with patch(
        "src.services.router_retraining_service.RouterRetrainingService.should_retrain",
        return_value=True,
    ), patch(
        "src.services.router_retraining_service.RouterRetrainingService.retrain_keyword_hints",
        return_value={"complicated": ["causal_uplift", "instrumental"]},
    ), patch(
        "src.services.router_retraining_service.RouterRetrainingService.apply_keyword_hints_to_router",
        return_value={"applied_domains": 1, "applied_hints": {"Complicated": ["causal_uplift"]}},
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/feedback/retrain-router", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "hints_extracted"
    assert body["applied_to_router"] is True
    assert "application_summary" in body


@pytest.mark.anyio
async def test_retrain_router_returns_insufficient_data():
    from httpx import ASGITransport, AsyncClient
    from src.main import app

    transport = ASGITransport(app=app)

    with patch(
        "src.services.router_retraining_service.RouterRetrainingService.should_retrain",
        return_value=False,
    ), patch(
        "src.services.router_retraining_service.RouterRetrainingService.get_training_data",
        return_value=[],
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/feedback/retrain-router",
                json={"min_samples": 9, "apply_to_router": True},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["min_required"] == 9


@pytest.mark.anyio
async def test_submit_domain_override_triggers_auto_refresh_check():
    from httpx import ASGITransport, AsyncClient
    from src.main import app

    transport = ASGITransport(app=app)

    with patch(
        "src.services.router_retraining_service.RouterRetrainingService.maybe_auto_refresh_router_hints",
        return_value={"status": "skipped_not_enough_new_overrides"},
    ) as mocked_refresh:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                json={
                    "type": "domain_override",
                    "description": "Router domain should be complicated",
                    "correct_domain": "complicated",
                    "context": {
                        "sessionId": "sess-auto-refresh",
                        "domain": "complex",
                        "query": "What is the causal effect of discount on churn?",
                    },
                },
            )

    assert response.status_code == 200
    assert mocked_refresh.called
