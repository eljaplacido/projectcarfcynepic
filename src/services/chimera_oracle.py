"""Chimera Oracle Engine for CARF.

Fast causal effect prediction using pre-trained CausalForestDML models.
Provides low-latency scoring for routine queries while maintaining
the option for rigorous DoWhy analysis on high-stakes decisions.

Integration pattern:
1. Train on scenario data once (or periodically)
2. Use predict_effect() for fast scoring (<100ms)
3. Fall back to full DoWhy analysis for refutation when needed
"""

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("carf.chimera_oracle")


@dataclass
class OraclePrediction:
    """Result from ChimeraOracle fast prediction."""
    
    effect_estimate: float
    confidence_interval: tuple[float, float]
    feature_importance: dict[str, float] = field(default_factory=dict)
    used_model: str = "causal_forest"  # or "fallback_linear"
    prediction_time_ms: float = 0.0


@dataclass
class TrainingResult:
    """Result from model training."""
    
    status: str  # "trained", "failed"
    n_samples: int = 0
    model_path: str = ""
    error: str | None = None
    average_treatment_effect: float = 0.0
    effect_std: float = 0.0


class ChimeraOracleEngine:
    """Fast causal effect prediction using pre-trained CausalForestDML.
    
    This engine provides a fast path for causal effect estimation when:
    1. A model has been pre-trained on scenario data
    2. The query context matches the trained scenario
    
    For novel queries or high-stakes decisions, use the full DoWhy pipeline.
    """
    
    def __init__(self, models_dir: str = "models"):
        """Initialize the oracle engine.
        
        Args:
            models_dir: Directory to store/load trained models
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._models: dict[str, Any] = {}  # scenario_id → trained model
        self._model_metadata: dict[str, dict] = {}  # scenario_id → training info
        
        # Load any existing models
        self._load_existing_models()
    
    def _load_existing_models(self) -> None:
        """Load pre-trained models from disk."""
        for model_file in self.models_dir.glob("*.pkl"):
            scenario_id = model_file.stem.replace("_causal_forest", "")
            try:
                with open(model_file, "rb") as f:
                    data = pickle.load(f)
                    self._models[scenario_id] = data.get("model")
                    self._model_metadata[scenario_id] = data.get("metadata", {})
                    logger.info(f"Loaded model for scenario: {scenario_id}")
            except Exception as e:
                logger.warning(f"Failed to load model {model_file}: {e}")
    
    def has_model(self, scenario_id: str) -> bool:
        """Check if a model exists for the given scenario."""
        return scenario_id in self._models and self._models[scenario_id] is not None
    
    def get_available_scenarios(self) -> list[str]:
        """Get list of scenarios with trained models."""
        return list(self._models.keys())
    
    async def train_on_scenario(
        self,
        scenario_id: str,
        csv_path: str,
        treatment: str,
        outcome: str,
        covariates: list[str] | None = None,
        effect_modifiers: list[str] | None = None,
        n_estimators: int = 100,
    ) -> TrainingResult:
        """Train CausalForestDML on scenario data.

        Args:
            scenario_id: Unique identifier for this scenario model
            csv_path: Path to training data CSV
            treatment: Name of treatment variable (binary)
            outcome: Name of outcome variable
            covariates: Variables to control for (W in causal model)
            effect_modifiers: Variables that modify treatment effect (X in causal model)
            n_estimators: Number of trees in the forest

        Returns:
            TrainingResult with status and metrics
        """
        try:
            from econml.dml import CausalForestDML
            from sklearn.ensemble import GradientBoostingRegressor

            # Load data
            df = pd.read_csv(csv_path)
            logger.info(f"Training on {len(df)} samples from {csv_path}")

            # CausalForestDML requires X (effect modifiers) to not be None
            # If no effect_modifiers specified, use covariates as effect modifiers
            if not effect_modifiers and covariates:
                effect_modifiers = covariates.copy()
                logger.info(f"Using covariates as effect modifiers: {effect_modifiers}")

            # If still no effect modifiers, create a constant feature
            if not effect_modifiers:
                logger.warning("No effect modifiers or covariates provided, using constant feature")
                effect_modifiers = []

            # Prepare variables
            # Effect modifiers (X) - variables that may create heterogeneous effects
            if effect_modifiers:
                # Handle categorical variables by one-hot encoding
                X_df = df[effect_modifiers].copy()
                for col in X_df.select_dtypes(include=['object']).columns:
                    dummies = pd.get_dummies(X_df[col], prefix=col, drop_first=True)
                    X_df = X_df.drop(col, axis=1)
                    X_df = pd.concat([X_df, dummies], axis=1)
                X = X_df.values
                effect_modifier_names = list(X_df.columns)
            else:
                # CausalForestDML needs X, use a constant intercept column
                X = np.ones((len(df), 1))
                effect_modifier_names = ["_intercept"]

            # Treatment (T)
            T = df[treatment].values

            # Outcome (Y)
            Y = df[outcome].values

            # Covariates for confounding adjustment (W)
            W = None
            if covariates:
                W_df = df[covariates].copy()
                for col in W_df.select_dtypes(include=['object']).columns:
                    dummies = pd.get_dummies(W_df[col], prefix=col, drop_first=True)
                    W_df = W_df.drop(col, axis=1)
                    W_df = pd.concat([W_df, dummies], axis=1)
                W = W_df.values
            
            # Train CausalForestDML
            model = CausalForestDML(
                model_t=GradientBoostingRegressor(n_estimators=50, max_depth=4),
                model_y=GradientBoostingRegressor(n_estimators=50, max_depth=4),
                n_estimators=n_estimators,
                min_samples_leaf=10,
                random_state=42,
            )
            
            model.fit(Y, T, X=X, W=W)
            
            # Calculate average treatment effect
            if X is not None:
                effects = model.effect(X)
                ate = float(np.mean(effects))
                effect_std = float(np.std(effects))
            else:
                ate = float(model.effect()[0])
                effect_std = 0.0
            
            # Get feature importance if available
            feature_importance = {}
            if hasattr(model, 'feature_importances_') and X is not None:
                importance = model.feature_importances_
                feature_importance = dict(zip(effect_modifier_names, importance.tolist()))
            
            # Save model
            model_path = self.models_dir / f"{scenario_id}_causal_forest.pkl"
            metadata = {
                "scenario_id": scenario_id,
                "treatment": treatment,
                "outcome": outcome,
                "covariates": covariates or [],
                "effect_modifiers": effect_modifiers or [],
                "effect_modifier_names": effect_modifier_names,
                "n_samples": len(df),
                "ate": ate,
                "effect_std": effect_std,
                "feature_importance": feature_importance,
            }
            
            with open(model_path, "wb") as f:
                pickle.dump({"model": model, "metadata": metadata}, f)
            
            # Cache in memory
            self._models[scenario_id] = model
            self._model_metadata[scenario_id] = metadata
            
            logger.info(
                f"Trained model for {scenario_id}: ATE={ate:.2f} (±{effect_std:.2f})"
            )
            
            return TrainingResult(
                status="trained",
                n_samples=len(df),
                model_path=str(model_path),
                average_treatment_effect=ate,
                effect_std=effect_std,
            )
            
        except ImportError as e:
            logger.error(f"EconML not available: {e}")
            return TrainingResult(
                status="failed",
                error=f"EconML not installed: {e}"
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return TrainingResult(
                status="failed",
                error=str(e)
            )
    
    def predict_effect(
        self,
        scenario_id: str,
        context: dict[str, Any],
    ) -> OraclePrediction:
        """Fast effect prediction for a single context.
        
        Args:
            scenario_id: Which scenario model to use
            context: Dictionary with feature values matching effect modifiers
            
        Returns:
            OraclePrediction with effect estimate and confidence interval
        """
        import time
        start = time.perf_counter()
        
        if not self.has_model(scenario_id):
            raise ValueError(f"No trained model for scenario: {scenario_id}")
        
        model = self._models[scenario_id]
        metadata = self._model_metadata.get(scenario_id, {})
        effect_modifier_names = metadata.get("effect_modifier_names", [])
        
        # Build feature vector from context
        X = np.zeros((1, len(effect_modifier_names)))
        for i, name in enumerate(effect_modifier_names):
            # Handle encoded feature names (e.g., "region_EU")
            if name in context:
                X[0, i] = context[name]
            else:
                # Check if this is a one-hot encoded feature
                parts = name.rsplit("_", 1)
                if len(parts) == 2:
                    base_name, value = parts
                    if base_name in context:
                        X[0, i] = 1.0 if context[base_name] == value else 0.0
        
        # Predict
        effect = model.effect(X)[0]
        
        # Get confidence interval
        try:
            lower, upper = model.effect_interval(X, alpha=0.05)
            ci = (float(lower[0]), float(upper[0]))
        except Exception:
            # Fallback: use ±1.96 * std
            std = metadata.get("effect_std", abs(effect) * 0.2)
            ci = (effect - 1.96 * std, effect + 1.96 * std)
        
        # Feature importance
        feature_importance = metadata.get("feature_importance", {})
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return OraclePrediction(
            effect_estimate=float(effect),
            confidence_interval=ci,
            feature_importance=feature_importance,
            used_model="causal_forest",
            prediction_time_ms=elapsed,
        )
    
    def predict_heterogeneous_effects(
        self,
        scenario_id: str,
        contexts: list[dict[str, Any]],
    ) -> list[OraclePrediction]:
        """Predict effects for multiple contexts (batch).
        
        Args:
            scenario_id: Which scenario model to use
            contexts: List of context dictionaries
            
        Returns:
            List of predictions
        """
        return [self.predict_effect(scenario_id, ctx) for ctx in contexts]
    
    def get_average_treatment_effect(self, scenario_id: str) -> dict[str, float]:
        """Get the average treatment effect from training.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            Dictionary with 'ate' and 'std' keys
        """
        metadata = self._model_metadata.get(scenario_id, {})
        return {
            "ate": metadata.get("ate", 0.0),
            "std": metadata.get("effect_std", 0.0),
            "n_samples": metadata.get("n_samples", 0),
        }


# Singleton instance
_oracle_engine: ChimeraOracleEngine | None = None


def get_oracle_engine() -> ChimeraOracleEngine:
    """Get or create the ChimeraOracle singleton."""
    global _oracle_engine
    if _oracle_engine is None:
        _oracle_engine = ChimeraOracleEngine()
    return _oracle_engine
