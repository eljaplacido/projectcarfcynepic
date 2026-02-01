"""Unit tests for the ChimeraOracle Engine.

Tests cover model loading, prediction, training, and caching functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd


class TestChimeraOracleEngine:
    """Tests for ChimeraOracleEngine class."""

    def test_initialization(self, tmp_path):
        """Test engine initialization."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        assert engine._models == {}
        assert engine._model_metadata == {}
        assert isinstance(engine.models_dir, Path)

    def test_initialization_creates_models_dir(self, tmp_path):
        """Test engine initialization creates models directory."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        models_path = tmp_path / "new_models_dir"
        engine = ChimeraOracleEngine(models_dir=str(models_path))
        assert models_path.exists()

    def test_get_available_scenarios_empty(self, tmp_path):
        """Test listing scenarios when none exist."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        scenarios = engine.get_available_scenarios()
        assert scenarios == []

    def test_has_model_false(self, tmp_path):
        """Test checking if model exists when it doesn't."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        assert engine.has_model("nonexistent") is False

    def test_get_average_treatment_effect_not_found(self, tmp_path):
        """Test getting ATE for non-existent model."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        result = engine.get_average_treatment_effect("nonexistent")
        assert result["ate"] == 0.0
        assert result["std"] == 0.0
        assert result["n_samples"] == 0

    def test_predict_raises_without_model(self, tmp_path):
        """Test that predict raises error when model not found."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        with pytest.raises(ValueError, match="No trained model"):
            engine.predict_effect(
                scenario_id="nonexistent",
                context={"supplier_size": 50}
            )


class TestChimeraOracleTraining:
    """Tests for ChimeraOracle training functionality."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        np.random.seed(42)
        n = 200
        treatment = np.random.binomial(1, 0.5, n)
        # Create outcome with known effect
        true_effect = -50
        base = 100
        noise = np.random.normal(0, 10, n)
        outcome = base + true_effect * treatment + noise
        
        return pd.DataFrame({
            "treatment": treatment,
            "outcome": outcome,
            "covariate1": np.random.normal(50, 10, n),
            "covariate2": np.random.uniform(0, 100, n),
        })

    @pytest.mark.asyncio
    async def test_train_model_creates_file(self, tmp_path, sample_data):
        """Test that training creates model file."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        csv_path = tmp_path / "test_data.csv"
        sample_data.to_csv(csv_path, index=False)
        
        result = await engine.train_on_scenario(
            scenario_id="test_scenario",
            csv_path=str(csv_path),
            treatment="treatment",
            outcome="outcome",
            covariates=["covariate1", "covariate2"],
        )
        
        assert result.status == "trained"
        assert result.n_samples == 200
        
        # Check model file was created
        model_path = tmp_path / "test_scenario_causal_forest.pkl"
        assert model_path.exists()

    @pytest.mark.asyncio
    async def test_train_model_with_effect_modifiers(self, tmp_path, sample_data):
        """Test training with effect modifier columns."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        # Add effect modifier column
        sample_data["region"] = np.random.choice(["EU", "US", "APAC"], 200)
        
        csv_path = tmp_path / "test_data_modifiers.csv"
        sample_data.to_csv(csv_path, index=False)
        
        result = await engine.train_on_scenario(
            scenario_id="test_with_modifiers",
            csv_path=str(csv_path),
            treatment="treatment",
            outcome="outcome",
            covariates=["covariate1", "covariate2"],
            effect_modifiers=["region"],
        )
        
        assert result.status == "trained"

    @pytest.mark.asyncio
    async def test_train_missing_file_fails(self, tmp_path):
        """Test training with missing file fails gracefully."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        # Use a definitely non-existent path in tmp
        missing_path = tmp_path / "definitely_does_not_exist.csv"
        
        result = await engine.train_on_scenario(
            scenario_id="missing_data",
            csv_path=str(missing_path),
            treatment="treatment",
            outcome="outcome",
        )
        
        assert result.status == "failed"
        assert result.error is not None


class TestChimeraOraclePrediction:
    """Tests for ChimeraOracle prediction functionality."""

    @pytest.fixture
    def trained_engine(self, tmp_path):
        """Create an engine with a mock trained model."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        # Create minimal mock model structure
        mock_model = MagicMock()
        mock_model.effect = MagicMock(return_value=np.array([-50.0]))
        mock_model.effect_interval = MagicMock(
            return_value=(np.array([-70.0]), np.array([-30.0]))
        )
        
        engine._models["test_scenario"] = mock_model
        engine._model_metadata["test_scenario"] = {
            "scenario_id": "test_scenario",
            "n_samples": 1000,
            "ate": -50.0,
            "effect_std": 10.0,
            "effect_modifier_names": ["covariate1", "region_EU"],
            "treatment": "treatment",
            "outcome": "outcome",
        }
        
        return engine

    def test_predict_returns_valid_result(self, trained_engine):
        """Test prediction returns valid structure."""
        result = trained_engine.predict_effect(
            scenario_id="test_scenario",
            context={"covariate1": 50, "region": "EU"}
        )
        
        assert hasattr(result, "effect_estimate")
        assert hasattr(result, "confidence_interval")
        assert hasattr(result, "prediction_time_ms")

    def test_predict_with_missing_features_uses_zeros(self, trained_engine):
        """Test prediction handles missing features (defaults to 0)."""
        result = trained_engine.predict_effect(
            scenario_id="test_scenario",
            context={"covariate1": 50}  # Missing region
        )
        
        assert result is not None
        assert result.effect_estimate == -50.0

    def test_batch_predict(self, trained_engine):
        """Test batch prediction for multiple contexts."""
        contexts = [
            {"covariate1": 40, "region": "EU"},
            {"covariate1": 60, "region": "US"},
            {"covariate1": 80, "region": "APAC"},
        ]
        
        results = trained_engine.predict_heterogeneous_effects(
            scenario_id="test_scenario",
            contexts=contexts
        )
        
        assert len(results) == 3
        for result in results:
            assert hasattr(result, "effect_estimate")


class TestGetOracleEngine:
    """Tests for get_oracle_engine singleton."""

    def test_returns_engine_instance(self):
        """Test get_oracle_engine returns an engine."""
        from src.services.chimera_oracle import get_oracle_engine, ChimeraOracleEngine
        import src.services.chimera_oracle as oracle_module
        
        # Reset singleton
        oracle_module._oracle_engine = None
        
        engine = get_oracle_engine()
        assert isinstance(engine, ChimeraOracleEngine)
        
        # Reset for other tests
        oracle_module._oracle_engine = None

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance."""
        from src.services.chimera_oracle import get_oracle_engine
        import src.services.chimera_oracle as oracle_module
        
        oracle_module._oracle_engine = None
        
        engine1 = get_oracle_engine()
        engine2 = get_oracle_engine()
        assert engine1 is engine2
        
        oracle_module._oracle_engine = None


class TestOraclePredictionAccuracy:
    """Integration tests for prediction accuracy."""

    @pytest.mark.asyncio
    async def test_prediction_recovers_known_effect(self, tmp_path):
        """Test that trained model can recover known treatment effect."""
        from src.services.chimera_oracle import ChimeraOracleEngine
        
        # Generate data with known treatment effect
        np.random.seed(42)
        n = 500
        treatment = np.random.binomial(1, 0.5, n)
        true_effect = -50  # Known effect
        noise = np.random.normal(0, 10, n)
        covariate = np.random.normal(100, 20, n)
        outcome = covariate + true_effect * treatment + noise
        
        df = pd.DataFrame({
            "treatment": treatment,
            "outcome": outcome,
            "covariate": covariate,
        })
        
        csv_path = tmp_path / "known_effect_data.csv"
        df.to_csv(csv_path, index=False)
        
        engine = ChimeraOracleEngine(models_dir=str(tmp_path))
        
        result = await engine.train_on_scenario(
            scenario_id="known_effect",
            csv_path=str(csv_path),
            treatment="treatment",
            outcome="outcome",
            covariates=["covariate"],
        )
        
        # Verify ATE is close to true effect
        ate = result.average_treatment_effect
        assert abs(ate - true_effect) < 15, f"ATE {ate} not close to true effect {true_effect}"
