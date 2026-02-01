"""Simulation Service for CARF - What-If Scenario Management.

Provides multi-scenario simulation capabilities for comparing
different intervention strategies and their projected outcomes.

Also includes realistic data generation for training causal models.
"""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.core.state import EpistemicState
from src.services.causal import CausalInferenceEngine, CausalEstimationConfig
from src.services.neo4j_service import get_neo4j_service

logger = logging.getLogger("carf.simulation")


# ============================================================================
# Realistic Data Generators (No Mock Data - Simulated with Causal Structure)
# ============================================================================

def generate_scope3_emissions_data(
    n_samples: int = 2000,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate realistic Scope 3 emissions data with known causal structure.
    
    The data has the following causal properties:
    - supplier_program → scope3_emissions (treatment effect, heterogeneous)
    - supplier_size → supplier_program (confounding: larger suppliers more likely in program)
    - region → scope3_emissions (effect modifier: EU has stronger program effect)
    - baseline_emissions → scope3_emissions (confounder)
    
    GHG Protocol Scope 3 categories included:
    - Category 1: Purchased Goods & Services
    - Category 4: Upstream Transportation
    - Category 6: Business Travel
    - Category 11: Use of Sold Products
    
    Args:
        n_samples: Number of supplier records to generate
        seed: Random seed for reproducibility
        output_path: Optional path to save CSV (defaults to demo/data/scope3_emissions.csv)
    
    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)
    
    regions = ["EU", "NA", "APAC", "LATAM", "EMEA"]
    sizes = ["small", "medium", "large"]
    
    # GHG Protocol Scope 3 categories with emission factors (kgCO2e per unit)
    categories = {
        "Cat1_Purchased_Goods": {"weight": 0.40, "emission_factor": 2.5, "unit": "kg/unit"},
        "Cat4_Transport": {"weight": 0.25, "emission_factor": 0.12, "unit": "kg/tkm"},
        "Cat6_Business_Travel": {"weight": 0.15, "emission_factor": 0.255, "unit": "kg/pkm"},
        "Cat11_Use_of_Products": {"weight": 0.20, "emission_factor": 1.8, "unit": "kg/use"},
    }
    category_names = list(categories.keys())
    category_probs = [categories[c]["weight"] for c in category_names]
    
    # Region-specific effects (EU strongest climate policy)
    region_effect_modifiers = {"EU": 1.3, "NA": 1.0, "APAC": 0.8, "LATAM": 0.7, "EMEA": 0.95}
    
    # Size-specific effects (larger suppliers have more reduction potential)
    size_effect_modifiers = {"large": 1.5, "medium": 1.0, "small": 0.6}
    
    # Size influences program participation (confounding)
    size_program_propensity = {"large": 0.7, "medium": 0.45, "small": 0.2}
    
    # Generate timestamps over 2 years (for time-series analysis)
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    date_range_days = (end_date - start_date).days
    
    data = []
    for i in range(n_samples):
        # Generate timestamp (distributed over 2 years)
        random_days = np.random.randint(0, date_range_days)
        timestamp = start_date + pd.Timedelta(days=random_days)
        
        # Generate baseline characteristics
        region = np.random.choice(regions, p=[0.25, 0.20, 0.30, 0.10, 0.15])
        size = np.random.choice(sizes, p=[0.30, 0.45, 0.25])
        
        # Assign GHG category
        category = np.random.choice(category_names, p=category_probs)
        emission_factor = categories[category]["emission_factor"]
        
        # Baseline emissions (before any intervention)
        # Larger suppliers have higher baselines
        size_baseline = {"small": 400, "medium": 700, "large": 1100}
        baseline_emissions = max(100, np.random.normal(size_baseline[size], 150))
        
        # Market conditions (0-1, affects business constraints)
        market_conditions = np.clip(np.random.normal(0.6, 0.15), 0.2, 0.95)
        
        # Energy mix (fraction of renewables, 0-1)
        # EU and NA have higher renewable adoption
        energy_base = {"EU": 0.45, "NA": 0.35, "APAC": 0.25, "LATAM": 0.30, "EMEA": 0.35}
        energy_mix = np.clip(np.random.normal(energy_base[region], 0.12), 0.05, 0.85)
        
        # Treatment assignment (supplier program participation)
        # Confounded by size (larger suppliers more likely to join)
        program_prob = size_program_propensity[size]
        # Also slightly influenced by energy mix (greener suppliers more likely)
        program_prob = program_prob + 0.1 * (energy_mix - 0.3)
        program_prob = np.clip(program_prob, 0.1, 0.9)
        supplier_program = int(np.random.random() < program_prob)
        
        # CAUSAL EFFECT: supplier program on emissions change
        # Base effect: program reduces emissions by ~60 tCO2e on average
        base_treatment_effect = -60 if supplier_program else 5  # slight increase without program
        
        # Heterogeneous effects by region and size
        region_mod = region_effect_modifiers[region]
        size_mod = size_effect_modifiers[size]
        
        # Energy mix also moderates: higher renewables = less room for reduction
        energy_mod = 1.2 - 0.5 * energy_mix
        
        # Baseline emissions affect potential: higher baseline = more reduction possible
        baseline_mod = 0.8 + 0.4 * (baseline_emissions / 1000)
        
        # Calculate emissions change (outcome)
        emissions_change = (
            base_treatment_effect 
            * region_mod 
            * size_mod 
            * energy_mod
            * baseline_mod
            + np.random.normal(0, 12)  # individual-level noise
        )
        
        # Confidence score based on data quality factors
        # Higher if: recent timestamp, large supplier (more data), stable market
        recency_factor = 0.5 + 0.5 * (1 - random_days / date_range_days)
        size_factor = {"large": 0.9, "medium": 0.75, "small": 0.6}[size]
        market_factor = 0.7 + 0.3 * (1 - abs(market_conditions - 0.6) / 0.4)
        confidence_score = np.clip(
            (recency_factor + size_factor + market_factor) / 3 + np.random.normal(0, 0.05),
            0.4, 0.98
        )
        
        data.append({
            "supplier_id": f"SUP-{i:04d}",
            "timestamp": timestamp.strftime("%Y-%m-%d"),
            "category": category,
            "supplier_program": supplier_program,
            "scope3_emissions": round(emissions_change, 1),
            "region": region,
            "market_conditions": round(market_conditions, 2),
            "energy_mix": round(energy_mix, 2),
            "supplier_size": size,
            "baseline_emissions": round(baseline_emissions, 0),
            "emission_factor": round(emission_factor, 3),
            "confidence_score": round(confidence_score, 2),
        })
    
    df = pd.DataFrame(data)
    
    # Save to file if path provided
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} Scope 3 records to {output_path}")
    
    return df



def generate_supply_chain_resilience_data(
    n_samples: int = 2000,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate supply chain resilience data with climate stress as treatment.
    
    Causal structure:
    - climate_stress_index → disruption_risk_percent (treatment effect)
    - operational_maturity → disruption_risk_percent (protective factor)
    - inventory_days → disruption_risk_percent (buffer effect)
    - supplier_tier → both treatment and outcome (confounder)
    
    Args:
        n_samples: Number of records
        seed: Random seed
        output_path: Optional path to save CSV
        
    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)
    
    regions = ["NAM", "APAC", "EMEA", "LATAM"]
    tiers = ["Tier 1", "Tier 2", "Tier 3"]
    
    # Region-specific climate vulnerability
    region_vulnerability = {"NAM": 0.9, "APAC": 1.15, "EMEA": 0.85, "LATAM": 1.1}
    
    # Tier affects both exposure and resilience
    tier_exposure = {"Tier 1": 0.7, "Tier 2": 1.0, "Tier 3": 1.3}
    
    data = []
    for i in range(n_samples):
        region = np.random.choice(regions, p=[0.25, 0.35, 0.25, 0.15])
        tier = np.random.choice(tiers, p=[0.20, 0.35, 0.45])
        
        # Operational maturity (0-100)
        # Tier 1 suppliers tend to be more mature
        tier_maturity_base = {"Tier 1": 70, "Tier 2": 55, "Tier 3": 45}
        operational_maturity = np.clip(
            np.random.normal(tier_maturity_base[tier], 15), 20, 100
        )
        
        # Inventory buffer days
        inventory_days = max(5, np.random.exponential(20) + 5)
        
        # Climate stress index (0-10)
        # Higher in APAC and LATAM
        climate_base = {"NAM": 4.0, "APAC": 5.5, "EMEA": 3.8, "LATAM": 5.0}
        climate_stress_index = np.clip(
            np.random.normal(climate_base[region], 2), 0, 10
        )
        
        # CAUSAL EFFECT: climate stress on disruption risk
        base_risk = 5  # base disruption risk %
        
        # Climate stress increases risk
        climate_effect = climate_stress_index * 4 * tier_exposure[tier] * region_vulnerability[region]
        
        # Operational maturity reduces risk
        maturity_protection = -0.3 * operational_maturity
        
        # Inventory provides buffer (diminishing returns)
        inventory_protection = -5 * (1 - np.exp(-inventory_days / 30))
        
        disruption_risk = base_risk + climate_effect + maturity_protection + inventory_protection
        disruption_risk = np.clip(disruption_risk + np.random.normal(0, 5), 0, 100)
        
        data.append({
            "supplier_id": f"SUP-{i:04d}",
            "supplier_region": region,
            "supplier_tier": tier,
            "operational_maturity": round(operational_maturity, 1),
            "inventory_days": round(inventory_days, 1),
            "climate_stress_index": round(climate_stress_index, 2),
            "disruption_risk_percent": round(disruption_risk, 2),
        })
    
    df = pd.DataFrame(data)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} supply chain records to {output_path}")
    
    return df


def calculate_shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of text token distribution.
    
    Used for complexity classification in the Cynefin router.
    Higher entropy suggests more disorder/complexity.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Shannon entropy value (bits)
    """
    tokens = text.lower().split()
    total = len(tokens)
    
    if total == 0:
        return 0.0
    
    # Count token frequencies
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    
    # Calculate entropy
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in freq.values()
    )
    
    return entropy




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
