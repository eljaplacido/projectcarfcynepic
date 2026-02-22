"""Unit tests for GovernanceGraphService with Neo4j MOCKED.

All methods should gracefully degrade when Neo4j is unavailable,
returning empty results without raising exceptions.
"""

import os
import pytest

os.environ["CARF_TEST_MODE"] = "1"

from src.core.governance_models import ContextTriple, EvidenceType
from src.services.governance_graph_service import (
    GovernanceGraphService,
    get_governance_graph_service,
)


@pytest.fixture
def graph_service():
    """Create a fresh GovernanceGraphService instance (Neo4j unavailable by default)."""
    return GovernanceGraphService()


@pytest.fixture
def sample_triple():
    """Create a sample ContextTriple for testing."""
    return ContextTriple(
        subject="procurement_spend",
        predicate="increases",
        object="carbon_footprint",
        domain_source="procurement",
        domain_target="sustainability",
        confidence=0.85,
        evidence_type=EvidenceType.RULE_BASED,
        session_id="test-session-1",
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInitialization:
    """Test service initialization."""

    def test_default_not_available(self, graph_service):
        assert graph_service.is_available is False

    def test_driver_is_none(self, graph_service):
        assert graph_service._driver is None

    def test_initialized_flag_false(self, graph_service):
        assert graph_service._initialized is False


# ---------------------------------------------------------------------------
# Graceful degradation — save
# ---------------------------------------------------------------------------

class TestSaveGracefulDegradation:
    """Test that save methods degrade gracefully when Neo4j is unavailable."""

    @pytest.mark.asyncio
    async def test_save_triple_when_unavailable(self, graph_service, sample_triple):
        # Should return None and not raise
        result = await graph_service.save_triple(sample_triple)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_triples_batch_when_unavailable(self, graph_service, sample_triple):
        result = await graph_service.save_triples_batch([sample_triple])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_triples_batch_empty_list(self, graph_service):
        result = await graph_service.save_triples_batch([])
        assert result == 0


# ---------------------------------------------------------------------------
# Graceful degradation — query
# ---------------------------------------------------------------------------

class TestQueryGracefulDegradation:
    """Test that query methods degrade gracefully when Neo4j is unavailable."""

    @pytest.mark.asyncio
    async def test_find_cross_domain_impacts_when_unavailable(self, graph_service):
        result = await graph_service.find_cross_domain_impacts("procurement")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_impact_path_when_unavailable(self, graph_service):
        result = await graph_service.get_impact_path("procurement", "sustainability")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_triples_when_unavailable(self, graph_service):
        result = await graph_service.get_all_triples()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_triples_with_session_when_unavailable(self, graph_service):
        result = await graph_service.get_all_triples(session_id="sess-1")
        assert result == []


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Test health_check when Neo4j is unavailable."""

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, graph_service):
        result = await graph_service.health_check()
        assert result["status"] == "unavailable"
        assert result["neo4j_connected"] is False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_returns_same_instance(self):
        import src.services.governance_graph_service as mod
        # Reset the singleton
        mod._governance_graph_instance = None
        svc1 = get_governance_graph_service()
        svc2 = get_governance_graph_service()
        assert svc1 is svc2
        # Cleanup
        mod._governance_graph_instance = None

    @pytest.mark.asyncio
    async def test_sync_session_triples_when_unavailable(self, graph_service, sample_triple):
        result = await graph_service.sync_session_triples("test-session-1", [sample_triple])
        assert result == 0
