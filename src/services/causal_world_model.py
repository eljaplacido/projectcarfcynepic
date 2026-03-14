# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Causal World Model Service — Phase 17.

Implements Structural Causal Models (SCMs) with forward simulation,
do-calculus interventions, counterfactual reasoning, and learning from data.

Research basis: COMET [9], CausalARC [10], CWMI [12], CASSANDRA [25],
Causal Cartographer [14].
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.services.causal import CausalGraph

logger = logging.getLogger("carf.world_model")


# =============================================================================
# DATA MODELS
# =============================================================================


class StructuralEquation(BaseModel):
    """A structural equation defining how a variable is determined by its parents.

    Y = f(parents) + noise
    For linear models: Y = intercept + sum(coeff_i * parent_i) + N(0, noise_std)
    """

    variable: str = Field(..., description="The variable this equation defines")
    parents: list[str] = Field(default_factory=list, description="Parent variable names")
    coefficients: dict[str, float] = Field(
        default_factory=dict, description="Coefficient for each parent"
    )
    intercept: float = Field(default=0.0, description="Intercept term")
    noise_std: float = Field(default=0.1, description="Standard deviation of noise term")
    equation_type: str = Field(default="linear", description="linear or logistic")

    def evaluate(self, parent_values: dict[str, float], noise: float = 0.0) -> float:
        """Evaluate the structural equation given parent values."""
        result = self.intercept
        for parent, coeff in self.coefficients.items():
            result += coeff * parent_values.get(parent, 0.0)
        result += noise

        if self.equation_type == "logistic":
            result = 1.0 / (1.0 + np.exp(-result))

        return float(result)


class SimulationTrajectory(BaseModel):
    """Result of a forward simulation."""

    trajectory: list[dict[str, float]] = Field(
        default_factory=list, description="State at each timestep"
    )
    variables: list[str] = Field(default_factory=list)
    interventions_applied: dict[str, float] = Field(default_factory=dict)
    steps: int = Field(default=0)
    model_id: str = Field(default="")


class CounterfactualResult(BaseModel):
    """Result of counterfactual reasoning."""

    factual_state: dict[str, float] = Field(default_factory=dict)
    counterfactual_state: dict[str, float] = Field(default_factory=dict)
    intervention: dict[str, float] = Field(default_factory=dict)
    differences: dict[str, float] = Field(default_factory=dict)
    abducted_noise: dict[str, float] = Field(default_factory=dict)


# =============================================================================
# CAUSAL WORLD MODEL
# =============================================================================


class CausalWorldModel:
    """A Structural Causal Model that supports simulation and counterfactuals.

    The SCM consists of:
    - A set of structural equations (one per endogenous variable)
    - Exogenous variables (noise terms)
    - A topological ordering for evaluation
    """

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or str(uuid4())[:8]
        self.equations: dict[str, StructuralEquation] = {}
        self._topo_order: list[str] | None = None

    def add_equation(self, equation: StructuralEquation) -> None:
        """Add a structural equation to the model."""
        self.equations[equation.variable] = equation
        self._topo_order = None  # Invalidate cached order

    @property
    def variables(self) -> list[str]:
        """All variables in the model."""
        return list(self.equations.keys())

    @property
    def topological_order(self) -> list[str]:
        """Compute topological ordering of variables."""
        if self._topo_order is not None:
            return self._topo_order

        # Kahn's algorithm
        in_degree: dict[str, int] = {v: 0 for v in self.equations}
        for eq in self.equations.values():
            for parent in eq.parents:
                if parent in in_degree:
                    pass  # Parent is endogenous
            in_degree[eq.variable] = len(
                [p for p in eq.parents if p in self.equations]
            )

        queue = [v for v, d in in_degree.items() if d == 0]
        order: list[str] = []

        while queue:
            v = queue.pop(0)
            order.append(v)
            for eq in self.equations.values():
                if v in eq.parents and eq.variable in in_degree:
                    in_degree[eq.variable] -= 1
                    if in_degree[eq.variable] == 0:
                        queue.append(eq.variable)

        # Add any remaining variables (handles cycles gracefully)
        for v in self.equations:
            if v not in order:
                order.append(v)

        self._topo_order = order
        return order

    def evaluate(
        self,
        exogenous: dict[str, float] | None = None,
        interventions: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Evaluate the SCM once, producing values for all endogenous variables.

        Args:
            exogenous: Noise values for each variable (default: zeros)
            interventions: do(X=x) interventions — overrides structural equations

        Returns:
            Dict of variable -> value
        """
        exogenous = exogenous or {}
        interventions = interventions or {}
        state: dict[str, float] = {}

        for var in self.topological_order:
            if var in interventions:
                # do(X=x): replace structural equation with constant
                state[var] = interventions[var]
            elif var in self.equations:
                eq = self.equations[var]
                noise = exogenous.get(var, 0.0)
                state[var] = eq.evaluate(state, noise)

        return state

    def simulate(
        self,
        initial_state: dict[str, float] | None = None,
        interventions: dict[str, float] | None = None,
        steps: int = 5,
        seed: int | None = None,
    ) -> SimulationTrajectory:
        """Forward-simulate the SCM for N steps.

        Each step adds noise drawn from the structural equations' noise distributions.
        """
        rng = np.random.default_rng(seed)
        trajectory: list[dict[str, float]] = []

        # Step 0: initial state
        if initial_state:
            current = dict(initial_state)
        else:
            current = self.evaluate(interventions=interventions)
        trajectory.append(dict(current))

        # Steps 1..N
        for _ in range(steps):
            # Generate noise for this step
            noise = {
                var: float(rng.normal(0, eq.noise_std))
                for var, eq in self.equations.items()
            }
            # Evaluate with current state as context and new noise
            new_state: dict[str, float] = {}
            for var in self.topological_order:
                if var in (interventions or {}):
                    new_state[var] = interventions[var]  # type: ignore[index]
                elif var in self.equations:
                    eq = self.equations[var]
                    # Use mix of current state and already-computed new values
                    parent_values = {**current, **new_state}
                    new_state[var] = eq.evaluate(parent_values, noise.get(var, 0.0))
                else:
                    new_state[var] = current.get(var, 0.0)

            current = new_state
            trajectory.append(dict(current))

        return SimulationTrajectory(
            trajectory=trajectory,
            variables=self.variables,
            interventions_applied=interventions or {},
            steps=steps,
            model_id=self.model_id,
        )

    def counterfactual(
        self,
        factual_observation: dict[str, float],
        intervention: dict[str, float],
    ) -> CounterfactualResult:
        """Three-step counterfactual reasoning (Pearl's approach).

        1. Abduction: Infer exogenous noise from factual observations
        2. Action: Apply do(X=x) intervention to the SCM
        3. Prediction: Evaluate the modified SCM with abducted noise

        Args:
            factual_observation: The actually observed values
            intervention: do(X=x) — what we want to change

        Returns:
            CounterfactualResult with factual vs. counterfactual outcomes
        """
        # Step 1: ABDUCTION — infer noise from observations
        abducted_noise: dict[str, float] = {}
        for var in self.topological_order:
            if var in self.equations:
                eq = self.equations[var]
                predicted = eq.evaluate(factual_observation, noise=0.0)
                observed = factual_observation.get(var, predicted)
                abducted_noise[var] = observed - predicted

        # Step 2: ACTION — apply intervention (done in evaluate via interventions param)

        # Step 3: PREDICTION — evaluate with abducted noise + intervention
        cf_state = self.evaluate(
            exogenous=abducted_noise,
            interventions=intervention,
        )

        # Compute differences
        differences = {
            var: cf_state.get(var, 0.0) - factual_observation.get(var, 0.0)
            for var in self.variables
        }

        return CounterfactualResult(
            factual_state=factual_observation,
            counterfactual_state=cf_state,
            intervention=intervention,
            differences=differences,
            abducted_noise=abducted_noise,
        )

    @classmethod
    def learn_from_data(
        cls,
        data: list[dict[str, float]],
        causal_graph: "CausalGraph",
        model_id: str | None = None,
    ) -> "CausalWorldModel":
        """Fit structural equations from data given a known causal graph.

        Uses OLS for continuous variables. Requires numpy only.

        Args:
            data: List of observation dicts
            causal_graph: Known causal structure (DAG)
            model_id: Optional model identifier
        """
        model = cls(model_id=model_id)
        adj = causal_graph.to_adjacency_list()

        # Get all variable names
        all_vars = set()
        for obs in data:
            all_vars.update(obs.keys())

        # Convert to arrays
        n = len(data)
        if n == 0:
            logger.warning("No data provided for learning")
            return model

        arrays: dict[str, np.ndarray] = {}
        for var in all_vars:
            arrays[var] = np.array([obs.get(var, 0.0) for obs in data])

        # Fit structural equation for each variable
        for node in causal_graph.nodes:
            var_name = node.name
            if var_name not in arrays:
                continue

            # Find parents from the adjacency list
            parents: list[str] = []
            for src, targets in adj.items():
                if var_name in targets and src in arrays:
                    parents.append(src)

            y = arrays[var_name]

            if not parents:
                # Root node: equation is just intercept + noise
                intercept = float(np.mean(y))
                noise_std = float(np.std(y)) or 0.1
                eq = StructuralEquation(
                    variable=var_name,
                    parents=[],
                    coefficients={},
                    intercept=intercept,
                    noise_std=noise_std,
                )
            else:
                # OLS regression: Y = X @ beta + noise
                X = np.column_stack(
                    [arrays[p] for p in parents if p in arrays]
                )
                valid_parents = [p for p in parents if p in arrays]

                if X.shape[1] == 0:
                    eq = StructuralEquation(
                        variable=var_name,
                        parents=[],
                        coefficients={},
                        intercept=float(np.mean(y)),
                        noise_std=float(np.std(y)) or 0.1,
                    )
                else:
                    # Add intercept column
                    X_with_intercept = np.column_stack([np.ones(n), X])
                    try:
                        beta, residuals, _, _ = np.linalg.lstsq(
                            X_with_intercept, y, rcond=None
                        )
                        intercept = float(beta[0])
                        coefficients = {
                            valid_parents[i]: float(beta[i + 1])
                            for i in range(len(valid_parents))
                        }
                        # Noise std from residuals
                        predicted = X_with_intercept @ beta
                        residual_std = float(np.std(y - predicted)) or 0.1
                    except np.linalg.LinAlgError:
                        intercept = float(np.mean(y))
                        coefficients = {p: 0.0 for p in valid_parents}
                        residual_std = float(np.std(y)) or 0.1

                    eq = StructuralEquation(
                        variable=var_name,
                        parents=valid_parents,
                        coefficients=coefficients,
                        intercept=intercept,
                        noise_std=residual_std,
                    )

            model.add_equation(eq)

        logger.info(
            "Learned CausalWorldModel '%s' with %d equations from %d observations",
            model.model_id, len(model.equations), n,
        )
        return model


# =============================================================================
# SERVICE LAYER — LLM-ASSISTED WORLD MODEL
# =============================================================================


class CausalWorldModelService:
    """Service layer wrapping CausalWorldModel with LLM-assisted construction.

    Can build world models from:
    - Natural language queries (LLM extracts variables and relationships)
    - Existing CausalGraphs from the causal engine
    - Raw data + causal graph (learns structural equations)
    """

    def __init__(self):
        self._models: dict[str, CausalWorldModel] = {}

    async def simulate_from_text(
        self,
        query: str,
        initial_conditions: dict[str, float] | None = None,
        interventions: dict[str, float] | None = None,
        steps: int = 5,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a world model from a text query and simulate it.

        Falls back to LLM-assisted probabilistic simulation when no
        structural equations can be learned.
        """
        context = context or {}

        # Try to use existing causal graph from context
        causal_graph = None
        try:
            from src.services.causal import get_causal_engine
            engine = get_causal_engine()
            hypothesis, graph = await engine.discover_causal_structure(query, context)
            causal_graph = graph
        except Exception as e:
            logger.debug("Could not discover causal structure: %s", e)

        # If we have data + graph, learn structural equations
        data = context.get("data") or context.get("benchmark_data")
        if data and causal_graph and isinstance(data, list):
            try:
                model = CausalWorldModel.learn_from_data(data, causal_graph)
                self._models[model.model_id] = model

                result = model.simulate(
                    initial_state=initial_conditions,
                    interventions=interventions,
                    steps=steps,
                )
                return {
                    "trajectory": result.trajectory,
                    "variables": result.variables,
                    "interventions_applied": result.interventions_applied,
                    "confidence": 0.8,
                    "interpretation": (
                        f"Simulated {steps} steps using learned SCM "
                        f"with {len(model.equations)} structural equations."
                    ),
                    "model_id": model.model_id,
                }
            except Exception as e:
                logger.warning("SCM learning failed, falling back to LLM: %s", e)

        # Fallback: LLM-assisted simulation
        return await self._llm_simulate(
            query, initial_conditions, interventions, steps, context
        )

    async def _llm_simulate(
        self,
        query: str,
        initial_conditions: dict[str, float] | None,
        interventions: dict[str, float] | None,
        steps: int,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to generate a plausible simulation trajectory."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        prompt = f"""You are a causal reasoning expert. Given the following query, generate a plausible
simulation trajectory showing how key variables evolve over {steps} time steps.

Query: {query}
Initial conditions: {json.dumps(initial_conditions or {}, indent=2)}
Interventions (do-calculus): {json.dumps(interventions or {}, indent=2)}

Return a JSON object with:
- "variables": list of variable names
- "trajectory": list of {steps + 1} dicts mapping variable names to numeric values
- "interpretation": a 2-3 sentence explanation

Return ONLY valid JSON, no markdown fencing."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            # Strip markdown fencing if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)

            return {
                "trajectory": parsed.get("trajectory", []),
                "variables": parsed.get("variables", []),
                "interventions_applied": interventions or {},
                "confidence": 0.4,  # Lower confidence for LLM-generated
                "interpretation": parsed.get(
                    "interpretation",
                    "LLM-assisted simulation (no structural equations available)."
                ),
            }
        except Exception as e:
            logger.error("LLM simulation failed: %s", e)
            return {
                "trajectory": [],
                "variables": [],
                "interventions_applied": interventions or {},
                "confidence": 0.0,
                "interpretation": f"Simulation failed: {str(e)}",
            }

    def get_model(self, model_id: str) -> CausalWorldModel | None:
        """Retrieve a previously created world model."""
        return self._models.get(model_id)


# =============================================================================
# SINGLETON
# =============================================================================

_service: CausalWorldModelService | None = None


def get_causal_world_model() -> CausalWorldModelService:
    """Get the singleton CausalWorldModelService."""
    global _service
    if _service is None:
        _service = CausalWorldModelService()
    return _service
