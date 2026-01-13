"""Unit tests for the Neo4j service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from src.services.neo4j_service import (
    Neo4jService,
    Neo4jConfig,
    get_neo4j_service,
)
from src.services.causal import (
    CausalGraph,
    CausalVariable,
    CausalHypothesis,
    CausalAnalysisResult,
)


class TestNeo4jConfig:
    """Tests for Neo4jConfig."""

    def test_from_env_defaults(self):
        """Test config loads defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = Neo4jConfig.from_env()
            assert config.uri == "bolt://localhost:7687"
            assert config.username == "neo4j"
            assert config.password == "password"
            assert config.database == "neo4j"

    def test_from_env_custom(self):
        """Test config loads from environment variables."""
        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://custom:7688",
            "NEO4J_USERNAME": "admin",
            "NEO4J_PASSWORD": "secret",
            "NEO4J_DATABASE": "carf",
        }):
            config = Neo4jConfig.from_env()
            assert config.uri == "bolt://custom:7688"
            assert config.username == "admin"
            assert config.password == "secret"
            assert config.database == "carf"


class TestNeo4jService:
    """Tests for Neo4jService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        return Neo4jConfig(
            uri="bolt://test:7687",
            username="test",
            password="test",
            database="test",
        )

    @pytest.fixture
    def sample_graph(self):
        """Create a sample causal graph."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(
            name="price_increase",
            description="Increase in product price",
            variable_type="continuous",
            role="treatment",
        ))
        graph.add_node(CausalVariable(
            name="churn",
            description="Customer churn rate",
            variable_type="continuous",
            role="outcome",
        ))
        graph.add_node(CausalVariable(
            name="competitor_pricing",
            description="Competitor pricing strategy",
            variable_type="continuous",
            role="confounder",
        ))
        graph.add_edge("price_increase", "churn")
        graph.add_edge("competitor_pricing", "price_increase")
        graph.add_edge("competitor_pricing", "churn")
        return graph

    @pytest.fixture
    def sample_result(self):
        """Create a sample analysis result."""
        return CausalAnalysisResult(
            hypothesis=CausalHypothesis(
                treatment="price_increase",
                outcome="churn",
                mechanism="Higher prices reduce perceived value",
                confounders=["competitor_pricing"],
                confidence=0.75,
            ),
            effect_estimate=0.35,
            confidence_interval=(0.2, 0.5),
            passed_refutation=True,
            interpretation="Price increases have a moderate positive effect on churn.",
        )

    def test_service_initialization(self, mock_config):
        """Test service initializes correctly."""
        service = Neo4jService(config=mock_config)
        assert service.config == mock_config
        assert service._driver is None
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_config):
        """Test successful connection."""
        service = Neo4jService(config=mock_config)

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()

        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("src.services.neo4j_service.AsyncGraphDatabase.driver", return_value=mock_driver):
            await service.connect()

        assert service._driver is not None
        mock_driver.verify_connectivity.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_config):
        """Test disconnection."""
        service = Neo4jService(config=mock_config)
        mock_driver = AsyncMock()
        service._driver = mock_driver
        service._initialized = True

        await service.disconnect()

        mock_driver.close.assert_called_once()
        assert service._driver is None
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_save_causal_graph(self, mock_config, sample_graph):
        """Test saving a causal graph."""
        service = Neo4jService(config=mock_config)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_driver.verify_connectivity = AsyncMock()

        service._driver = mock_driver
        service._initialized = True

        await service.save_causal_graph(sample_graph, "test-session")

        # Should have called run for each node and each edge
        assert mock_session.run.call_count >= len(sample_graph.nodes) + len(sample_graph.edges)

    @pytest.mark.asyncio
    async def test_save_empty_graph_warning(self, mock_config, caplog):
        """Test warning when saving empty graph."""
        service = Neo4jService(config=mock_config)

        empty_graph = CausalGraph()
        await service.save_causal_graph(empty_graph, "test-session")

        assert "empty" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_config):
        """Test health check returns healthy status."""
        service = Neo4jService(config=mock_config)

        mock_result = AsyncMock()
        mock_data = {
            "variables": 10,
            "relationships": 15,
            "analyses": 5,
        }
        mock_result.single = AsyncMock(return_value=mock_data)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_driver.verify_connectivity = AsyncMock()

        service._driver = mock_driver
        service._initialized = True

        health = await service.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["statistics"]["variables"] == 10
        assert health["statistics"]["relationships"] == 15
        assert health["statistics"]["analyses"] == 5

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_config):
        """Test health check returns unhealthy on error."""
        service = Neo4jService(config=mock_config)

        with patch("src.services.neo4j_service.AsyncGraphDatabase.driver") as mock_driver_class:
            mock_driver_class.side_effect = Exception("Connection failed")
            health = await service.health_check()

        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "Connection failed" in health["error"]


class TestCausalGraphDataclass:
    """Tests for CausalGraph functionality used with Neo4j."""

    def test_add_node(self):
        """Test adding nodes to graph."""
        graph = CausalGraph()
        var = CausalVariable(name="test", description="Test var")
        graph.add_node(var)

        assert len(graph.nodes) == 1
        assert graph.nodes[0].name == "test"

    def test_add_duplicate_node(self):
        """Test duplicate nodes are not added."""
        graph = CausalGraph()
        var1 = CausalVariable(name="test", description="First")
        var2 = CausalVariable(name="test", description="Second")

        graph.add_node(var1)
        graph.add_node(var2)

        assert len(graph.nodes) == 1
        assert graph.nodes[0].description == "First"

    def test_add_edge(self):
        """Test adding edges to graph."""
        graph = CausalGraph()
        graph.add_edge("cause", "effect")

        assert len(graph.edges) == 1
        assert graph.edges[0] == ("cause", "effect")

    def test_add_duplicate_edge(self):
        """Test duplicate edges are not added."""
        graph = CausalGraph()
        graph.add_edge("cause", "effect")
        graph.add_edge("cause", "effect")

        assert len(graph.edges) == 1

    def test_to_adjacency_list(self):
        """Test conversion to adjacency list."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(name="A", description="A"))
        graph.add_node(CausalVariable(name="B", description="B"))
        graph.add_node(CausalVariable(name="C", description="C"))
        graph.add_edge("A", "B")
        graph.add_edge("A", "C")
        graph.add_edge("B", "C")

        adj = graph.to_adjacency_list()

        assert adj["A"] == ["B", "C"]
        assert adj["B"] == ["C"]
        assert adj["C"] == []

    def test_get_confounders(self):
        """Test identifying confounders."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(name="treatment", description="T", role="treatment"))
        graph.add_node(CausalVariable(name="outcome", description="O", role="outcome"))
        graph.add_node(CausalVariable(name="confounder", description="C", role="confounder"))

        # Confounder affects both treatment and outcome
        graph.add_edge("confounder", "treatment")
        graph.add_edge("confounder", "outcome")
        graph.add_edge("treatment", "outcome")

        confounders = graph.get_confounders("treatment", "outcome")

        assert "confounder" in confounders
        assert len(confounders) == 1


class TestSingletonPattern:
    """Tests for singleton pattern."""

    def test_get_neo4j_service_singleton(self):
        """Test singleton returns same instance."""
        # Reset singleton
        import src.services.neo4j_service as module
        module._neo4j_instance = None

        service1 = get_neo4j_service()
        service2 = get_neo4j_service()

        assert service1 is service2

        # Cleanup
        module._neo4j_instance = None
