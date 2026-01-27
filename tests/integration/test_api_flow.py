"""Integration tests for the CARF API flow.

Tests verify end-to-end behaviour:
- Query without data -> 400 Bad Request
- Query with data -> 200 + valid result
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_query_without_data_returns_400():
    """Submitting a causal query without data must return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={"query": "Does price affect churn?"},
            timeout=60.0,
        )

    # Should fail with a validation error because no data is provided
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body
    assert "data" in body["detail"].lower() or "no data" in body["detail"].lower()


@pytest.mark.asyncio
async def test_query_with_data_returns_200():
    """Submitting a query with inline data should succeed."""
    pytest.importorskip("dowhy", reason="dowhy not installed")

    import random
    random.seed(42)
    data = []
    for _ in range(100):
        z = random.gauss(0, 1)
        x = z + random.gauss(0, 0.5)
        y = 0.5 * x + 0.3 * z + random.gauss(0, 0.2)
        data.append({"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={
                "query": "Does x cause y?",
                "context": {
                    "causal_estimation": {
                        "treatment": "x",
                        "outcome": "y",
                        "covariates": ["z"],
                        "data": data,
                    }
                },
            },
            timeout=120.0,
        )

    assert response.status_code == 200
    body = response.json()
    assert "response" in body or "session_id" in body


@pytest.mark.asyncio
async def test_health_endpoint():
    """The health endpoint should always return 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
