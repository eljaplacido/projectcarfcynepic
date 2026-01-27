"""Unit tests for the Bayesian Active Inference Engine.

Tests cover Pydantic models, BeliefNetwork operations, and configuration validation.
"""

import pytest
from pydantic import ValidationError

from src.services.bayesian import (
    BayesianBelief,
    ExplorationProbe,
    ActiveInferenceResult,
    BayesianInferenceConfig,
    BayesianInferenceResult,
    BeliefNetwork,
)


class TestBayesianBelief:
    """Tests for BayesianBelief model."""

    def test_valid_belief(self):
        """Test creating a valid BayesianBelief."""
        belief = BayesianBelief(
            hypothesis="Product will succeed",
            prior=0.6,
            posterior=0.75,
            evidence_considered=["market research", "competitor analysis"],
            confidence_interval=(0.65, 0.85),
        )
        assert belief.hypothesis == "Product will succeed"
        assert belief.prior == 0.6
        assert belief.posterior == 0.75

    def test_probability_bounds(self):
        """Test that probabilities must be between 0 and 1."""
        with pytest.raises(ValidationError):
            BayesianBelief(
                hypothesis="test",
                prior=1.5,
                posterior=0.5,
            )
        with pytest.raises(ValidationError):
            BayesianBelief(
                hypothesis="test",
                prior=0.5,
                posterior=-0.1,
            )

    def test_default_values(self):
        """Test default values for BayesianBelief."""
        belief = BayesianBelief(
            hypothesis="test",
            prior=0.5,
            posterior=0.6,
        )
        assert belief.evidence_considered == []
        assert belief.confidence_interval == (0.0, 1.0)


class TestExplorationProbe:
    """Tests for ExplorationProbe model."""

    def test_valid_probe(self):
        """Test creating a valid ExplorationProbe."""
        probe = ExplorationProbe(
            probe_id="probe_001",
            description="A/B test on pricing",
            expected_information_gain=0.4,
            risk_level="low",
            reversible=True,
            success_criteria="Conversion rate increase > 5%",
            failure_criteria="No significant change",
        )
        assert probe.probe_id == "probe_001"
        assert probe.expected_information_gain == 0.4

    def test_info_gain_bounds(self):
        """Test expected_information_gain must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ExplorationProbe(
                probe_id="test",
                description="test",
                expected_information_gain=1.5,
                success_criteria="test",
                failure_criteria="test",
            )

    def test_invalid_risk_level(self):
        """Test that invalid risk_level raises error."""
        with pytest.raises(ValidationError):
            ExplorationProbe(
                probe_id="test",
                description="test",
                expected_information_gain=0.5,
                risk_level="extreme",
                success_criteria="test",
                failure_criteria="test",
            )

    def test_default_values(self):
        """Test default values for ExplorationProbe."""
        probe = ExplorationProbe(
            probe_id="test",
            description="test",
            expected_information_gain=0.5,
            success_criteria="test",
            failure_criteria="test",
        )
        assert probe.risk_level == "low"
        assert probe.reversible is True


class TestBayesianInferenceConfig:
    """Tests for BayesianInferenceConfig model."""

    def test_has_data_with_observations(self):
        """Test has_data returns True when observations are provided."""
        config = BayesianInferenceConfig(
            observations=[1.0, 2.0, 3.0],
        )
        assert config.has_data() is True
        assert config.mode() == "normal"

    def test_has_data_with_binomial(self):
        """Test has_data returns True for binomial data."""
        config = BayesianInferenceConfig(
            successes=10,
            trials=20,
        )
        assert config.has_data() is True
        assert config.mode() == "binomial"

    def test_has_data_no_data(self):
        """Test has_data returns False when no data is provided."""
        config = BayesianInferenceConfig()
        assert config.has_data() is False
        assert config.mode() == "unknown"

    def test_default_values(self):
        """Test default values for BayesianInferenceConfig."""
        config = BayesianInferenceConfig()
        assert config.draws == 500
        assert config.tune == 500
        assert config.chains == 2
        assert config.target_accept == 0.9

    def test_validation_bounds(self):
        """Test validation bounds for config values."""
        with pytest.raises(ValidationError):
            BayesianInferenceConfig(draws=50)  # Must be >= 100
        with pytest.raises(ValidationError):
            BayesianInferenceConfig(trials=0)  # Must be >= 1


class TestBayesianInferenceResult:
    """Tests for BayesianInferenceResult model."""

    def test_valid_result(self):
        """Test creating a valid BayesianInferenceResult."""
        result = BayesianInferenceResult(
            posterior_mean=0.65,
            credible_interval=(0.55, 0.75),
            uncertainty=0.15,
        )
        assert result.posterior_mean == 0.65
        assert result.credible_interval == (0.55, 0.75)


class TestActiveInferenceResult:
    """Tests for ActiveInferenceResult model."""

    def test_valid_result(self):
        """Test creating a valid ActiveInferenceResult."""
        initial = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.5)
        updated = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.7)
        probe = ExplorationProbe(
            probe_id="p1",
            description="test probe",
            expected_information_gain=0.3,
            success_criteria="test",
            failure_criteria="fail",
        )
        result = ActiveInferenceResult(
            initial_belief=initial,
            updated_belief=updated,
            probes_designed=[probe],
            recommended_probe=probe,
            uncertainty_before=0.8,
            uncertainty_after=0.5,
            interpretation="Uncertainty reduced by exploration",
        )
        assert result.uncertainty_before == 0.8
        assert result.uncertainty_after == 0.5
        assert len(result.probes_designed) == 1

    def test_default_values(self):
        """Test default values for ActiveInferenceResult."""
        initial = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.5)
        updated = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.6)
        result = ActiveInferenceResult(
            initial_belief=initial,
            updated_belief=updated,
            uncertainty_before=0.7,
            uncertainty_after=0.5,
            interpretation="Test",
        )
        assert result.probes_designed == []
        assert result.recommended_probe is None


class TestBeliefNetwork:
    """Tests for BeliefNetwork dataclass."""

    def test_add_belief(self):
        """Test adding beliefs to network."""
        network = BeliefNetwork()
        belief = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.6)
        network.add_belief(belief)
        assert len(network.beliefs) == 1
        assert "test" in network.beliefs

    def test_get_belief(self):
        """Test getting a belief from network."""
        network = BeliefNetwork()
        belief = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.6)
        network.add_belief(belief)
        retrieved = network.get_belief("test")
        assert retrieved is not None
        assert retrieved.posterior == 0.6

    def test_get_belief_not_found(self):
        """Test getting a non-existent belief returns None."""
        network = BeliefNetwork()
        assert network.get_belief("nonexistent") is None

    def test_get_most_uncertain(self):
        """Test finding the most uncertain belief."""
        network = BeliefNetwork()
        belief_certain = BayesianBelief(hypothesis="certain", prior=0.9, posterior=0.95)
        belief_uncertain = BayesianBelief(hypothesis="uncertain", prior=0.5, posterior=0.52)
        network.add_belief(belief_certain)
        network.add_belief(belief_uncertain)
        most_uncertain = network.get_most_uncertain()
        assert most_uncertain is not None
        assert most_uncertain.hypothesis == "uncertain"

    def test_get_most_uncertain_empty(self):
        """Test get_most_uncertain on empty network returns None."""
        network = BeliefNetwork()
        assert network.get_most_uncertain() is None

    def test_update_belief(self):
        """Test updating an existing belief."""
        network = BeliefNetwork()
        belief1 = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.6)
        belief2 = BayesianBelief(hypothesis="test", prior=0.5, posterior=0.8)
        network.add_belief(belief1)
        network.add_belief(belief2)
        assert len(network.beliefs) == 1
        assert network.beliefs["test"].posterior == 0.8


class TestActiveInferenceEngine:
    """Tests for ActiveInferenceEngine class."""

    def test_initialization(self):
        """Test engine initialization."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        assert engine.model is not None

    def test_calculate_entropy_low(self):
        """Test entropy calculation for low uncertainty."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        # Probability near 0 or 1 should have low entropy
        entropy_low = engine._calculate_entropy(0.99)
        assert entropy_low < 0.2

    def test_calculate_entropy_high(self):
        """Test entropy calculation for high uncertainty."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        # Probability near 0.5 should have maximum entropy
        entropy_high = engine._calculate_entropy(0.5)
        assert entropy_high > 0.9

    def test_calculate_entropy_boundary(self):
        """Test entropy calculation at boundaries."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        # At boundary values, entropy should be 0
        assert engine._calculate_entropy(0.0) == 0.0
        assert engine._calculate_entropy(1.0) == 0.0

    def test_update_belief(self):
        """Test Bayesian belief update."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        initial_belief = BayesianBelief(
            hypothesis="Test hypothesis",
            prior=0.5,
            posterior=0.5,
        )

        # Positive evidence (likelihood ratio > 1)
        updated = engine.update_belief(
            initial_belief,
            evidence="Positive observation",
            likelihood_ratio=2.0,
        )

        assert updated.posterior > initial_belief.posterior
        assert "Positive observation" in updated.evidence_considered

    def test_update_belief_negative_evidence(self):
        """Test Bayesian belief update with negative evidence."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        initial_belief = BayesianBelief(
            hypothesis="Test hypothesis",
            prior=0.5,
            posterior=0.5,
        )

        # Negative evidence (likelihood ratio < 1)
        updated = engine.update_belief(
            initial_belief,
            evidence="Negative observation",
            likelihood_ratio=0.5,
        )

        assert updated.posterior < initial_belief.posterior

    def test_parse_inference_config_none(self):
        """Test parsing None context."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        result = engine._parse_inference_config(None)
        assert result is None

    def test_parse_inference_config_empty(self):
        """Test parsing empty context."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        result = engine._parse_inference_config({})
        assert result is None

    def test_parse_inference_config_valid(self):
        """Test parsing valid inference config."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        context = {
            "bayesian_inference": {
                "observations": [1.0, 2.0, 3.0],
            }
        }
        result = engine._parse_inference_config(context)
        assert result is not None
        assert result.observations == [1.0, 2.0, 3.0]

    def test_parse_inference_config_invalid(self):
        """Test parsing invalid config returns None."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        context = {
            "bayesian_inference": {
                "draws": 10,  # Invalid - must be >= 100
            }
        }
        result = engine._parse_inference_config(context)
        assert result is None

    def test_summarize_samples(self):
        """Test summarizing posterior samples."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        samples = [0.5, 0.6, 0.55, 0.58, 0.52, 0.57, 0.54, 0.56]
        result = engine._summarize_samples(samples)

        assert result.posterior_mean > 0.5
        assert result.posterior_mean < 0.6
        assert result.credible_interval[0] < result.credible_interval[1]

    def test_summarize_samples_empty(self):
        """Test summarizing empty samples raises error."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        with pytest.raises(ValueError):
            engine._summarize_samples([])

    @pytest.mark.asyncio
    async def test_establish_priors(self):
        """Test establishing priors from query."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        beliefs, uncertainty = await engine.establish_priors(
            "Will our new product launch be successful?"
        )

        assert beliefs is not None
        assert len(beliefs) >= 1
        assert 0 <= uncertainty <= 1

    @pytest.mark.asyncio
    async def test_establish_priors_with_context(self):
        """Test establishing priors with context."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        context = {
            "market_size": "large",
            "competition": "moderate",
        }

        beliefs, uncertainty = await engine.establish_priors(
            "What is the probability of market expansion?",
            context=context,
        )

        assert beliefs is not None

    @pytest.mark.asyncio
    async def test_design_probes(self):
        """Test designing probes to reduce uncertainty."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        beliefs = [
            BayesianBelief(
                hypothesis="Product will succeed",
                prior=0.5,
                posterior=0.55,
            ),
        ]

        probes = await engine.design_probes(
            beliefs,
            "Will our product launch succeed?",
        )

        assert probes is not None
        assert len(probes) >= 1
        assert all(isinstance(p, ExplorationProbe) for p in probes)

    @pytest.mark.asyncio
    async def test_explore_raises_without_data(self):
        """Test that explore raises ValueError when no data is provided."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        with pytest.raises(ValueError, match="No data provided"):
            await engine.explore("What factors determine customer loyalty?")

    @pytest.mark.asyncio
    async def test_explore_raises_with_empty_context(self):
        """Test that explore raises ValueError with context but no data."""
        from src.services.bayesian import ActiveInferenceEngine
        engine = ActiveInferenceEngine()

        context = {
            "industry": "retail",
            "customer_segment": "premium",
        }

        with pytest.raises(ValueError, match="No data provided"):
            await engine.explore(
                "How will pricing changes affect demand?",
                context=context,
            )


class TestGetBayesianEngine:
    """Tests for get_bayesian_engine singleton."""

    def test_returns_engine_instance(self):
        """Test get_bayesian_engine returns an engine."""
        from src.services.bayesian import get_bayesian_engine, ActiveInferenceEngine
        import src.services.bayesian as bayesian_module

        # Reset singleton
        bayesian_module._engine_instance = None

        engine = get_bayesian_engine()
        assert isinstance(engine, ActiveInferenceEngine)

        # Reset for other tests
        bayesian_module._engine_instance = None

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance."""
        from src.services.bayesian import get_bayesian_engine
        import src.services.bayesian as bayesian_module

        bayesian_module._engine_instance = None

        engine1 = get_bayesian_engine()
        engine2 = get_bayesian_engine()
        assert engine1 is engine2

        bayesian_module._engine_instance = None


class TestRunActiveInference:
    """Tests for run_active_inference function."""

    @pytest.mark.asyncio
    async def test_raises_without_data(self):
        """Test that run_active_inference raises ValueError without data."""
        from src.services.bayesian import run_active_inference
        from src.core.state import EpistemicState
        import src.services.bayesian as bayesian_module

        bayesian_module._engine_instance = None

        state = EpistemicState(
            user_input="What is the probability of project success?"
        )

        with pytest.raises(ValueError, match="No data provided"):
            await run_active_inference(state)

        bayesian_module._engine_instance = None
