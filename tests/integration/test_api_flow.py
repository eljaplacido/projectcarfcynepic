"""Integration tests for the CARF API flow.

Tests verify end-to-end behaviour:
- Query without data -> 400 Bad Request
- Query with data -> 200 + valid result
- Smart reflector integration
- Enhanced insights endpoint
- Experience buffer accumulation
- Retraining readiness
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def async_client():
    """Reusable async HTTP client fixture."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_query_without_data_returns_400():
    """Submitting a causal query without data must return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
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
            "/query",
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


# ── Smart Reflector Integration ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_smart_reflector_in_pipeline():
    """Smart reflector should repair budget violations when triggered."""
    from src.core.state import EpistemicState, GuardianVerdict
    from src.workflows.graph import reflector_node

    state = EpistemicState(
        user_input="Budget repair integration test",
        proposed_action={"action_type": "invest", "amount": 150000},
        policy_violations=["Budget exceeded: 150000 > 100000"],
        guardian_verdict=GuardianVerdict.REJECTED,
        reflection_count=0,
    )

    result = await reflector_node(state)

    assert result.proposed_action is not None
    assert result.proposed_action["amount"] < 150000
    assert result.context.get("repair_strategy") is not None


# ── Enhanced Insights Endpoint ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_enhanced_insights_endpoint():
    """Enhanced insights should return action items and roadmap."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/insights/enhanced",
            json={
                "persona": "analyst",
                "domain": "complicated",
                "domain_confidence": 0.85,
                "has_causal_result": True,
                "causal_effect": -0.15,
                "refutation_pass_rate": 0.6,
                "sample_size": 200,
            },
            timeout=30.0,
        )

    assert response.status_code == 200
    body = response.json()
    assert "insights" in body
    assert "action_items" in body
    assert "roadmap" in body
    assert len(body["action_items"]) > 0
    assert len(body["roadmap"]) > 0


# ── Experience Buffer Accumulation ───────────────────────────────────────

@pytest.mark.asyncio
async def test_experience_buffer_accumulation():
    """Experience buffer should grow as entries are added."""
    from src.services.experience_buffer import ExperienceBuffer, ExperienceEntry

    buffer = ExperienceBuffer(max_entries=100)

    assert buffer.size == 0

    for i in range(3):
        buffer.add(ExperienceEntry(
            query=f"Test query number {i} about supply chain risk",
            domain="complicated",
            domain_confidence=0.85,
            session_id=f"sess-{i}",
        ))

    assert buffer.size == 3

    # Find similar
    results = buffer.find_similar("supply chain risk", top_k=3)
    assert len(results) > 0


# ── Retraining Readiness ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retraining_readiness():
    """Retraining readiness endpoint should return status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/feedback/retraining-readiness")

    assert response.status_code == 200
    body = response.json()
    assert "total_overrides" in body
    assert "ready_for_retraining" in body
    assert "recommendation" in body
