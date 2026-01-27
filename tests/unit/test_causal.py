"""Unit tests for the Causal Inference Engine.

Tests cover Pydantic models, CausalGraph operations, and configuration validation.
"""

import pytest
from pydantic import ValidationError

from src.services.causal import (
    CausalVariable,
    CausalHypothesis,
    CausalAnalysisResult,
    CausalEstimationConfig,
    CausalGraph,
)


class TestCausalVariable:
    """Tests for CausalVariable model."""

    def test_valid_variable(self):
        """Test creating a valid CausalVariable."""
        var = CausalVariable(
            name="treatment",
            description="The intervention",
            variable_type="continuous",
            role="treatment",
        )
        assert var.name == "treatment"
        assert var.role == "treatment"

    def test_default_values(self):
        """Test default values for CausalVariable."""
        var = CausalVariable(name="x", description="A variable")
        assert var.variable_type == "continuous"
        assert var.role == "covariate"

    def test_invalid_variable_type(self):
        """Test that invalid variable_type raises error."""
        with pytest.raises(ValidationError):
            CausalVariable(
                name="x",
                description="test",
                variable_type="invalid_type",
            )

    def test_invalid_role(self):
        """Test that invalid role raises error."""
        with pytest.raises(ValidationError):
            CausalVariable(
                name="x",
                description="test",
                role="invalid_role",
            )


class TestCausalHypothesis:
    """Tests for CausalHypothesis model."""

    def test_valid_hypothesis(self):
        """Test creating a valid CausalHypothesis."""
        hyp = CausalHypothesis(
            treatment="training",
            outcome="productivity",
            mechanism="Skills improvement leads to higher output",
            confounders=["experience", "motivation"],
            confidence=0.75,
        )
        assert hyp.treatment == "training"
        assert hyp.outcome == "productivity"
        assert len(hyp.confounders) == 2

    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            CausalHypothesis(
                treatment="x",
                outcome="y",
                mechanism="test",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            CausalHypothesis(
                treatment="x",
                outcome="y",
                mechanism="test",
                confidence=-0.1,
            )

    def test_default_values(self):
        """Test default values for CausalHypothesis."""
        hyp = CausalHypothesis(
            treatment="x",
            outcome="y",
            mechanism="test",
        )
        assert hyp.confounders == []
        assert hyp.confidence == 0.5


class TestCausalAnalysisResult:
    """Tests for CausalAnalysisResult model."""

    def test_valid_result(self):
        """Test creating a valid CausalAnalysisResult."""
        hyp = CausalHypothesis(
            treatment="x",
            outcome="y",
            mechanism="test mechanism",
        )
        result = CausalAnalysisResult(
            hypothesis=hyp,
            effect_estimate=0.45,
            confidence_interval=(0.2, 0.7),
            p_value=0.03,
            refutation_results={"placebo": True, "random_cause": True},
            passed_refutation=True,
            interpretation="Significant positive effect",
        )
        assert result.effect_estimate == 0.45
        assert result.passed_refutation is True
        assert len(result.refutation_results) == 2

    def test_default_values(self):
        """Test default values for CausalAnalysisResult."""
        hyp = CausalHypothesis(treatment="x", outcome="y", mechanism="test")
        result = CausalAnalysisResult(
            hypothesis=hyp,
            effect_estimate=0.3,
            confidence_interval=(0.1, 0.5),
            interpretation="Test",
        )
        assert result.p_value is None
        assert result.refutation_results == {}
        assert result.passed_refutation is False


class TestCausalEstimationConfig:
    """Tests for CausalEstimationConfig model."""

    def test_has_data_with_inline_data(self):
        """Test has_data returns True when data is provided."""
        config = CausalEstimationConfig(
            treatment="x",
            outcome="y",
            data=[{"x": 1, "y": 2}],
        )
        assert config.has_data() is True

    def test_has_data_with_csv_path(self):
        """Test has_data returns True when csv_path is provided."""
        config = CausalEstimationConfig(
            treatment="x",
            outcome="y",
            csv_path="/path/to/data.csv",
        )
        assert config.has_data() is True

    def test_has_data_with_dataset_id(self):
        """Test has_data returns True when dataset_id is provided."""
        config = CausalEstimationConfig(
            treatment="x",
            outcome="y",
            dataset_id="dataset_123",
        )
        assert config.has_data() is True

    def test_has_data_no_data(self):
        """Test has_data returns False when no data source is provided."""
        config = CausalEstimationConfig(
            treatment="x",
            outcome="y",
        )
        assert config.has_data() is False

    def test_default_method(self):
        """Test default estimation method."""
        config = CausalEstimationConfig(treatment="x", outcome="y")
        assert config.method_name == "backdoor.linear_regression"


class TestCausalGraph:
    """Tests for CausalGraph dataclass."""

    def test_add_node(self):
        """Test adding nodes to graph."""
        graph = CausalGraph()
        var = CausalVariable(name="x", description="test")
        graph.add_node(var)
        assert len(graph.nodes) == 1
        assert graph.nodes[0].name == "x"

    def test_add_duplicate_node(self):
        """Test that duplicate nodes are not added."""
        graph = CausalGraph()
        var = CausalVariable(name="x", description="test")
        graph.add_node(var)
        graph.add_node(var)
        assert len(graph.nodes) == 1

    def test_add_edge(self):
        """Test adding edges to graph."""
        graph = CausalGraph()
        graph.add_edge("x", "y")
        assert ("x", "y") in graph.edges

    def test_add_duplicate_edge(self):
        """Test that duplicate edges are not added."""
        graph = CausalGraph()
        graph.add_edge("x", "y")
        graph.add_edge("x", "y")
        assert len(graph.edges) == 1

    def test_to_adjacency_list(self):
        """Test converting graph to adjacency list."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(name="x", description="cause"))
        graph.add_node(CausalVariable(name="y", description="effect"))
        graph.add_edge("x", "y")
        adj = graph.to_adjacency_list()
        assert adj["x"] == ["y"]
        assert adj["y"] == []

    def test_get_confounders(self):
        """Test identifying confounders."""
        graph = CausalGraph()
        graph.add_node(CausalVariable(name="T", description="treatment"))
        graph.add_node(CausalVariable(name="Y", description="outcome"))
        graph.add_node(CausalVariable(name="C", description="confounder"))
        graph.add_edge("C", "T")
        graph.add_edge("C", "Y")
        graph.add_edge("T", "Y")
        confounders = graph.get_confounders("T", "Y")
        assert confounders == ["C"]


class TestCausalInferenceEngine:
    """Tests for CausalInferenceEngine class."""

    def test_initialization(self):
        """Test engine initialization."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()
        assert engine.model is not None
        assert engine._neo4j is None

    def test_initialization_with_neo4j(self):
        """Test engine initialization with Neo4j service."""
        from src.services.causal import CausalInferenceEngine
        from unittest.mock import MagicMock

        mock_neo4j = MagicMock()
        engine = CausalInferenceEngine(neo4j_service=mock_neo4j)
        assert engine._neo4j is mock_neo4j

    def test_enable_neo4j(self):
        """Test enabling Neo4j after initialization."""
        from src.services.causal import CausalInferenceEngine
        from unittest.mock import MagicMock

        engine = CausalInferenceEngine()
        assert engine._neo4j is None

        mock_neo4j = MagicMock()
        engine.enable_neo4j(mock_neo4j)
        assert engine._neo4j is mock_neo4j

    def test_parse_estimation_config_none(self):
        """Test parsing None context."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()
        result = engine._parse_estimation_config(None)
        assert result is None

    def test_parse_estimation_config_empty(self):
        """Test parsing empty context."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()
        result = engine._parse_estimation_config({})
        assert result is None

    def test_parse_estimation_config_valid(self):
        """Test parsing valid causal estimation config."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()
        context = {
            "causal_estimation": {
                "treatment": "price",
                "outcome": "sales",
                "data": [{"price": 10, "sales": 100}],
            }
        }
        result = engine._parse_estimation_config(context)
        assert result is not None
        assert result.treatment == "price"
        assert result.outcome == "sales"

    def test_parse_estimation_config_invalid(self):
        """Test parsing invalid config returns None."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()
        context = {
            "causal_estimation": {
                "invalid_field": "value",
            }
        }
        result = engine._parse_estimation_config(context)
        assert result is None

    @pytest.mark.asyncio
    async def test_discover_causal_structure(self):
        """Test discovering causal structure from query."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()

        hypothesis, graph = await engine.discover_causal_structure(
            "What causes customer churn when we increase prices?"
        )

        assert hypothesis is not None
        assert hypothesis.treatment is not None
        assert hypothesis.outcome is not None
        assert graph is not None

    @pytest.mark.asyncio
    async def test_discover_causal_structure_with_context(self):
        """Test discovering causal structure with additional context."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()

        context = {
            "domain": "retail",
            "variables": ["price", "sales", "marketing"],
        }

        hypothesis, graph = await engine.discover_causal_structure(
            "How does marketing affect sales?",
            context=context,
        )

        assert hypothesis is not None
        assert hypothesis.treatment is not None

    @pytest.mark.asyncio
    async def test_estimate_effect_raises_without_data(self):
        """Test that estimate_effect raises ValueError when no data is provided."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()

        hypothesis = CausalHypothesis(
            treatment="training",
            outcome="productivity",
            mechanism="Skills improvement",
            confidence=0.7,
        )

        with pytest.raises(ValueError, match="No data provided"):
            await engine.estimate_effect(hypothesis)

    @pytest.mark.asyncio
    async def test_estimate_effect_raises_with_empty_config(self):
        """Test that estimate_effect raises ValueError with config but no data."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()

        hypothesis = CausalHypothesis(
            treatment="x",
            outcome="y",
            mechanism="test",
        )
        config = CausalEstimationConfig(treatment="x", outcome="y")

        with pytest.raises(ValueError, match="No data provided"):
            await engine.estimate_effect(hypothesis, estimation_config=config)

    @pytest.mark.asyncio
    async def test_find_historical_analyses_no_neo4j(self):
        """Test finding historical analyses without Neo4j returns empty."""
        from src.services.causal import CausalInferenceEngine
        engine = CausalInferenceEngine()

        result = await engine.find_historical_analyses("price", "churn")
        assert result == []


class TestGetCausalEngine:
    """Tests for get_causal_engine singleton."""

    def test_returns_engine_instance(self):
        """Test get_causal_engine returns an engine."""
        from src.services.causal import get_causal_engine, CausalInferenceEngine
        import src.services.causal as causal_module

        # Reset singleton
        causal_module._engine_instance = None

        engine = get_causal_engine()
        assert isinstance(engine, CausalInferenceEngine)

        # Reset for other tests
        causal_module._engine_instance = None

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance."""
        from src.services.causal import get_causal_engine
        import src.services.causal as causal_module

        causal_module._engine_instance = None

        engine1 = get_causal_engine()
        engine2 = get_causal_engine()
        assert engine1 is engine2

        causal_module._engine_instance = None


class TestRunCausalAnalysis:
    """Tests for run_causal_analysis function."""

    @pytest.mark.asyncio
    async def test_raises_without_data(self):
        """Test that run_causal_analysis raises ValueError without data."""
        from src.services.causal import run_causal_analysis
        from src.core.state import EpistemicState
        import src.services.causal as causal_module

        causal_module._engine_instance = None

        state = EpistemicState(
            user_input="Does marketing spend affect customer acquisition?"
        )

        with pytest.raises(ValueError, match="No data provided"):
            await run_causal_analysis(state)

        causal_module._engine_instance = None
