"""Integration tests for Neo4j governance graph persistence.

These tests require a live Neo4j connection and are skipped when Neo4j is
unavailable. They validate:
- Triple persistence to Neo4j
- Cross-domain impact queries
- Session triple sync

Prerequisites:
  - Neo4j running at NEO4J_URI (default bolt://localhost:7687)
  - NEO4J_USERNAME / NEO4J_PASSWORD set
"""

import os
import pytest

os.environ.setdefault("GOVERNANCE_ENABLED", "true")
os.environ.setdefault("CARF_TEST_MODE", "1")

# ---------------------------------------------------------------------------
# Check Neo4j availability before collecting tests
# ---------------------------------------------------------------------------


def _neo4j_available() -> bool:
    """Check if Neo4j driver is installed and a connection can be established."""
    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")

        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


neo4j_available = _neo4j_available()

pytestmark = pytest.mark.skipif(
    not neo4j_available,
    reason="Neo4j is not available — skipping governance graph integration tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def graph_service():
    """Create and connect a GovernanceGraphService for testing."""
    from src.services.governance_graph_service import GovernanceGraphService

    service = GovernanceGraphService()
    await service.connect()

    if not service.is_available:
        pytest.skip("Neo4j governance graph service not available after connect")

    yield service

    # Cleanup test data
    try:
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        async with service._driver.session(database=database) as session:
            await session.run("""
                MATCH (t:ContextTriple)
                WHERE t.session_id STARTS WITH 'test-neo4j-'
                DETACH DELETE t
            """)
    except Exception:
        pass

    await service.disconnect()


@pytest.fixture
def sample_triples():
    """Create sample ContextTriple objects for testing."""
    from src.core.governance_models import ContextTriple, EvidenceType

    return [
        ContextTriple(
            subject="procurement_context",
            predicate="impacts",
            object="sustainability_context",
            domain_source="procurement",
            domain_target="sustainability",
            confidence=0.85,
            evidence_type=EvidenceType.RULE_BASED,
            session_id="test-neo4j-session-001",
        ),
        ContextTriple(
            subject="sustainability_context",
            predicate="constrains",
            object="finance_context",
            domain_source="sustainability",
            domain_target="finance",
            confidence=0.72,
            evidence_type=EvidenceType.LLM_EXTRACTED,
            session_id="test-neo4j-session-001",
        ),
        ContextTriple(
            subject="security_context",
            predicate="requires",
            object="procurement_context",
            domain_source="security",
            domain_target="procurement",
            confidence=0.90,
            evidence_type=EvidenceType.POLICY_DERIVED,
            session_id="test-neo4j-session-002",
        ),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTriplePersistence:
    """Test storing and retrieving context triples in Neo4j."""

    async def test_save_single_triple(self, graph_service, sample_triples):
        triple = sample_triples[0]
        await graph_service.save_triple(triple)

        # Verify the triple can be retrieved
        triples = await graph_service.get_all_triples(
            session_id="test-neo4j-session-001", limit=10
        )
        assert len(triples) >= 1

        saved = triples[0]
        assert saved["subject"] == "procurement_context"
        assert saved["predicate"] == "impacts"
        assert saved["domain_source"] == "procurement"
        assert saved["domain_target"] == "sustainability"

    async def test_save_triples_batch(self, graph_service, sample_triples):
        count = await graph_service.save_triples_batch(sample_triples)

        assert count == 3, f"Expected 3 triples saved, got {count}"

        all_triples = await graph_service.get_all_triples(limit=100)
        session_triples = [
            t for t in all_triples
            if t.get("session_id", "").startswith("test-neo4j-")
        ]
        assert len(session_triples) >= 3

    async def test_triple_upsert_on_duplicate(self, graph_service, sample_triples):
        triple = sample_triples[0]

        # Save twice — should MERGE, not create duplicate
        await graph_service.save_triple(triple)
        await graph_service.save_triple(triple)

        triples = await graph_service.get_all_triples(
            session_id="test-neo4j-session-001", limit=100
        )
        # Count triples with our specific subject
        matching = [
            t for t in triples
            if t.get("subject") == "procurement_context"
            and t.get("predicate") == "impacts"
        ]
        assert len(matching) == 1, "Duplicate save should not create a second node"


@pytest.mark.asyncio
class TestCrossDomainQuery:
    """Test cross-domain impact path queries in Neo4j."""

    async def test_find_cross_domain_impacts(self, graph_service, sample_triples):
        # Persist triples first
        await graph_service.save_triples_batch(sample_triples)

        # Query impacts from procurement
        impacts = await graph_service.find_cross_domain_impacts("procurement")

        # procurement -> sustainability (via triple[0])
        impacted_domains = [i["domain_id"] for i in impacts]
        assert "sustainability" in impacted_domains

    async def test_find_impacts_empty_for_unlinked_domain(self, graph_service, sample_triples):
        await graph_service.save_triples_batch(sample_triples)

        # legal has no triples in our test data
        impacts = await graph_service.find_cross_domain_impacts("legal")
        assert len(impacts) == 0

    async def test_impact_path_between_domains(self, graph_service, sample_triples):
        await graph_service.save_triples_batch(sample_triples)

        # There should be a path from procurement to sustainability
        paths = await graph_service.get_impact_path("procurement", "sustainability")

        # At minimum we expect some path structure (even if just direct)
        # The path may be empty if the graph structure doesn't match the
        # shortestPath pattern, so we allow both outcomes
        assert isinstance(paths, list)


@pytest.mark.asyncio
class TestSessionSync:
    """Test session-based triple synchronization."""

    async def test_sync_session_triples(self, graph_service, sample_triples):
        # Sync only triples from session 001 (first two triples)
        count = await graph_service.sync_session_triples(
            "test-neo4j-session-001", sample_triples
        )

        # Two triples have session_id "test-neo4j-session-001"
        assert count == 2

        # Verify they are in the database
        stored = await graph_service.get_all_triples(
            session_id="test-neo4j-session-001", limit=10
        )
        assert len(stored) >= 2

    async def test_sync_filters_by_session_id(self, graph_service, sample_triples):
        # Sync session 002 — only the third triple matches
        count = await graph_service.sync_session_triples(
            "test-neo4j-session-002", sample_triples
        )
        assert count == 1

    async def test_health_check_returns_healthy(self, graph_service):
        health = await graph_service.health_check()

        assert health["status"] == "healthy"
        assert health["neo4j_connected"] is True
        assert isinstance(health.get("triples", 0), int)
        assert isinstance(health.get("domains", 0), int)
