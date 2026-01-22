"""Simulation Service for CARF - What-If Scenario Management.

Provides multi-scenario simulation capabilities for comparing
different intervention strategies and their projected outcomes.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.core.state import EpistemicState
from src.services.causal import CausalInferenceEngine, CausalEstimationConfig
from src.services.neo4j_service import get_neo4j_service

logger = logging.getLogger("carf.simulation")


class Intervention(BaseModel):
    """A single intervention in a scenario."""
    
    variable: str = Field(..., description="Variable to intervene on")
    value: float = Field(..., description="Intervention value")
    description: str | None = Field(None, description="Human-readable description")


class ScenarioConfig(BaseModel):
    """Configuration for a what-if scenario."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Scenario ID")
    name: str = Field(..., description="Scenario name")
    description: str | None = Field(None, description="Scenario description")
    interventions: list[Intervention] = Field(..., description="List of interventions")
    baseline_dataset_id: str = Field(..., description="Dataset to use as baseline")
    parent_session_id: str | None = Field(None, description="Parent analysis session")


class SimulationResult(BaseModel):
    """Result from running a scenario simulation."""
    
    scenario_id: str = Field(..., description="Scenario identifier")
    session_id: str = Field(..., description="Analysis session ID")
    effect_estimate: float = Field(..., description="Estimated causal effect")
    confidence_interval: tuple[float, float] = Field(..., description="95% CI")
    confidence: float = Field(..., description="Overall confidence score")
    metrics: dict[str, float] = Field(default_factory=dict, description="Additional metrics")
    updated_at: str = Field(..., description="Last update timestamp")
    status: str = Field(default="completed", description="pending, running, completed, failed")
    error: str | None = Field(None, description="Error message if failed")


class SimulationComparison(BaseModel):
    """Comparison of multiple simulation results."""
    
    scenarios: list[SimulationResult] = Field(..., description="All scenario results")
    best_by_metric: dict[str, str] = Field(..., description="Best scenario ID per metric")
    baseline_scenario_id: str | None = Field(None, description="Baseline scenario for comparison")


class SimulationService:
    """Service for managing what-if scenario simulations."""
    
    def __init__(self):
        self.causal_engine = CausalInferenceEngine()
        self.neo4j = get_neo4j_service()
        self._running_simulations: dict[str, SimulationResult] = {}
    
    async def run_scenario(
        self,
        config: ScenarioConfig,
        context: dict[str, Any] | None = None
    ) -> SimulationResult:
        """Run a single scenario simulation.
        
        Args:
            config: Scenario configuration
            context: Additional context for the analysis
            
        Returns:
            Simulation result
        """
        logger.info(f"Running scenario: {config.name} ({config.id})")
        
        # Mark as running
        result = SimulationResult(
            scenario_id=config.id,
            session_id=str(uuid4()),
            effect_estimate=0.0,
            confidence_interval=(0.0, 0.0),
            confidence=0.0,
            updated_at=datetime.utcnow().isoformat(),
            status="running"
        )
        self._running_simulations[config.id] = result
        
        try:
            # Build intervention description for query
            intervention_desc = ", ".join([
                f"{i.variable}={i.value}" for i in config.interventions
            ])
            query = f"What if we set {intervention_desc}?"
            
            # Prepare context with interventions
            sim_context = context or {}
            sim_context["interventions"] = [i.model_dump() for i in config.interventions]
            sim_context["scenario_id"] = config.id
            sim_context["scenario_name"] = config.name
            
            # Add causal estimation config if dataset provided
            if config.baseline_dataset_id:
                sim_context["dataset_selection"] = {
                    "dataset_id": config.baseline_dataset_id
                }
            
            # Discover causal structure
            hypothesis, graph = await self.causal_engine.discover_causal_structure(
                query=query,
                context=sim_context
            )
            
            # Estimate effect with interventions
            causal_result = await self.causal_engine.estimate_effect(
                hypothesis=hypothesis,
                graph=graph,
                context=sim_context
            )
            
            # Update result
            result.effect_estimate = causal_result.effect_estimate
            result.confidence_interval = causal_result.confidence_interval
            result.confidence = 1.0 if causal_result.passed_refutation else 0.5
            result.metrics = {
                "p_value": causal_result.p_value or 0.0,
                "refutations_passed": sum(1 for v in causal_result.refutation_results.values() if v),
                "refutations_total": len(causal_result.refutation_results)
            }
            result.status = "completed"
            result.updated_at = datetime.utcnow().isoformat()
            
            # Link to parent session if provided
            if config.parent_session_id:
                try:
                    await self.neo4j.link_analysis_sessions(
                        parent_id=config.parent_session_id,
                        child_id=result.session_id,
                        relationship_type="SIMULATES"
                    )
                except Exception as e:
                    logger.warning(f"Failed to link sessions: {e}")
            
            logger.info(f"Scenario completed: {config.name}")
            
        except Exception as e:
            logger.error(f"Scenario failed: {config.name} - {e}")
            result.status = "failed"
            result.error = str(e)
            result.updated_at = datetime.utcnow().isoformat()
        
        self._running_simulations[config.id] = result
        return result
    
    async def run_multiple_scenarios(
        self,
        scenarios: list[ScenarioConfig],
        context: dict[str, Any] | None = None
    ) -> list[SimulationResult]:
        """Run multiple scenarios in parallel.
        
        Args:
            scenarios: List of scenario configurations
            context: Shared context for all scenarios
            
        Returns:
            List of simulation results
        """
        results = []
        for scenario in scenarios:
            result = await self.run_scenario(scenario, context)
            results.append(result)
        
        return results
    
    async def compare_scenarios(
        self,
        scenario_ids: list[str]
    ) -> SimulationComparison:
        """Compare multiple simulation results.
        
        Args:
            scenario_ids: List of scenario IDs to compare
            
        Returns:
            Comparison summary
        """
        results = [
            self._running_simulations[sid]
            for sid in scenario_ids
            if sid in self._running_simulations
        ]
        
        if not results:
            raise ValueError("No simulation results found for comparison")
        
        # Find best scenario for each metric
        best_by_metric = {}
        
        # Best by effect size (absolute value)
        best_effect = max(results, key=lambda r: abs(r.effect_estimate))
        best_by_metric["effect_size"] = best_effect.scenario_id
        
        # Best by confidence
        best_conf = max(results, key=lambda r: r.confidence)
        best_by_metric["confidence"] = best_conf.scenario_id
        
        # Best by refutation pass rate
        for result in results:
            if "refutations_passed" in result.metrics and "refutations_total" in result.metrics:
                result.metrics["refutation_rate"] = (
                    result.metrics["refutations_passed"] / result.metrics["refutations_total"]
                    if result.metrics["refutations_total"] > 0 else 0
                )
        
        best_refutation = max(
            results,
            key=lambda r: r.metrics.get("refutation_rate", 0)
        )
        best_by_metric["refutation_rate"] = best_refutation.scenario_id
        
        return SimulationComparison(
            scenarios=results,
            best_by_metric=best_by_metric
        )
    
    def get_simulation_status(self, scenario_id: str) -> SimulationResult | None:
        """Get the current status of a simulation.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            Current simulation result or None if not found
        """
        return self._running_simulations.get(scenario_id)
    
    async def invalidate_and_rerun(
        self,
        scenario_id: str,
        config: ScenarioConfig,
        context: dict[str, Any] | None = None
    ) -> SimulationResult:
        """Invalidate cached results and re-run a scenario.
        
        Args:
            scenario_id: Scenario to invalidate
            config: Updated scenario configuration
            context: Analysis context
            
        Returns:
            Fresh simulation result
        """
        # Get old result if exists
        old_result = self._running_simulations.get(scenario_id)
        
        # Invalidate cache in Neo4j if we have a session
        if old_result and old_result.session_id:
            try:
                await self.neo4j.invalidate_session_cache(old_result.session_id)
                logger.info(f"Invalidated cache for scenario: {scenario_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
        
        # Re-run the scenario
        return await self.run_scenario(config, context)


# Singleton instance
_simulation_service: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    """Get or create the simulation service singleton."""
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = SimulationService()
    return _simulation_service
