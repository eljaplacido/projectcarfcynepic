"""Strict tests for the hardened Causal Inference Engine.

These tests verify that:
- estimate_effect NEVER returns mocked/hallucinated results
- A real DataFrame triggers DoWhy and returns a float effect size
- Missing data always produces a clear ValueError
"""

import pytest

from src.services.causal import (
    CausalHypothesis,
    CausalEstimationConfig,
    CausalInferenceEngine,
)


class TestStrictCausalEstimation:
    """Tests verifying that causal estimation requires real data."""

    @pytest.mark.asyncio
    async def test_no_data_raises_value_error(self):
        """estimate_effect must raise ValueError when called without data."""
        engine = CausalInferenceEngine()
        hypothesis = CausalHypothesis(
            treatment="discount",
            outcome="churn",
            mechanism="Incentive reduces attrition",
        )

        with pytest.raises(ValueError, match="No data provided"):
            await engine.estimate_effect(hypothesis)

    @pytest.mark.asyncio
    async def test_empty_config_raises_value_error(self):
        """estimate_effect must raise ValueError when config has no data source."""
        engine = CausalInferenceEngine()
        hypothesis = CausalHypothesis(
            treatment="x",
            outcome="y",
            mechanism="test",
        )
        empty_config = CausalEstimationConfig(treatment="x", outcome="y")
        assert empty_config.has_data() is False

        with pytest.raises(ValueError, match="No data provided"):
            await engine.estimate_effect(hypothesis, estimation_config=empty_config)

    @pytest.mark.asyncio
    async def test_real_data_returns_float_effect(self):
        """With a real DataFrame, DoWhy must return a numeric effect estimate."""
        pytest.importorskip("dowhy", reason="dowhy not installed")

        engine = CausalInferenceEngine()
        hypothesis = CausalHypothesis(
            treatment="x",
            outcome="y",
            mechanism="x causes y",
            confounders=["z"],
        )

        # Build a small synthetic dataset where x -> y with confounder z
        import random
        random.seed(42)
        data = []
        for _ in range(200):
            z = random.gauss(0, 1)
            x = z + random.gauss(0, 0.5)
            y = 0.5 * x + 0.3 * z + random.gauss(0, 0.2)
            data.append({"x": x, "y": y, "z": z})

        config = CausalEstimationConfig(
            treatment="x",
            outcome="y",
            covariates=["z"],
            data=data,
        )

        result = await engine.estimate_effect(hypothesis, estimation_config=config)

        assert isinstance(result.effect_estimate, float)
        # The true effect is 0.5; DoWhy should be in the right ballpark
        assert 0.1 < result.effect_estimate < 1.0
        assert result.confidence_interval[0] < result.confidence_interval[1]

    @pytest.mark.asyncio
    async def test_analyze_raises_without_estimation_data(self):
        """Full analyze() pipeline must propagate ValueError when no data."""
        engine = CausalInferenceEngine()

        with pytest.raises(ValueError, match="No data provided"):
            await engine.analyze(
                query="Does x cause y?",
                persist=False,
            )
