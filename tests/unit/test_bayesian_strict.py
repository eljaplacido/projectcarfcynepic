"""Strict tests for the hardened Bayesian Active Inference Engine.

These tests verify that:
- explore() NEVER fabricates posterior updates
- A real binomial dataset triggers PyMC and returns a meaningful posterior
- Missing data always produces a clear ValueError
"""

import pytest

from src.services.bayesian import (
    ActiveInferenceEngine,
    BayesianInferenceConfig,
)


class TestStrictBayesianInference:
    """Tests verifying that Bayesian inference requires real data."""

    @pytest.mark.asyncio
    async def test_no_data_raises_value_error(self):
        """explore() must raise ValueError when called without data."""
        engine = ActiveInferenceEngine()

        with pytest.raises(ValueError, match="No data provided"):
            await engine.explore("What is the probability of success?")

    @pytest.mark.asyncio
    async def test_empty_context_raises_value_error(self):
        """explore() must raise ValueError when context has no inference data."""
        engine = ActiveInferenceEngine()

        with pytest.raises(ValueError, match="No data provided"):
            await engine.explore(
                "Estimate probability",
                context={"some_key": "some_value"},
            )

    @pytest.mark.asyncio
    async def test_binomial_data_returns_real_posterior(self):
        """With binomial data (50 successes / 100 trials), posterior ~0.5."""
        pytest.importorskip("pymc", reason="pymc not installed")

        engine = ActiveInferenceEngine()

        context = {
            "bayesian_inference": {
                "successes": 50,
                "trials": 100,
                "draws": 200,
                "tune": 200,
                "chains": 2,
            }
        }

        result = await engine.explore(
            "What is the true success rate?",
            context=context,
        )

        assert result is not None
        assert result.updated_belief is not None

        # The posterior mean should be close to 0.5
        posterior = result.updated_belief.posterior
        assert 0.3 < posterior < 0.7, (
            f"Posterior {posterior} should be near 0.5 for 50/100 binomial"
        )

        # Uncertainty should be reduced from the prior
        assert result.uncertainty_after < result.uncertainty_before

        # Interpretation must mention PyMC (not simulated)
        assert "PyMC" in result.interpretation

    @pytest.mark.asyncio
    async def test_observations_data_returns_real_posterior(self):
        """With continuous observations, posterior should reflect the data."""
        pytest.importorskip("pymc", reason="pymc not installed")

        engine = ActiveInferenceEngine()

        # Observations centered around 5.0
        import random
        random.seed(42)
        observations = [random.gauss(5.0, 1.0) for _ in range(50)]

        context = {
            "bayesian_inference": {
                "observations": observations,
                "draws": 200,
                "tune": 200,
                "chains": 2,
            }
        }

        result = await engine.explore(
            "What is the true mean?",
            context=context,
        )

        assert result is not None
        assert result.updated_belief is not None
        # Posterior mean should be near 5.0
        assert 3.0 < result.updated_belief.posterior < 7.0

    def test_inference_config_validation(self):
        """Config with data must report has_data() == True."""
        config_binomial = BayesianInferenceConfig(successes=10, trials=20)
        assert config_binomial.has_data() is True
        assert config_binomial.mode() == "binomial"

        config_obs = BayesianInferenceConfig(observations=[1.0, 2.0, 3.0])
        assert config_obs.has_data() is True
        assert config_obs.mode() == "normal"

        config_empty = BayesianInferenceConfig()
        assert config_empty.has_data() is False
