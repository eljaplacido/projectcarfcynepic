"""Script to train ChimeraOracle models on demo scenarios."""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Train models on all available demo scenarios."""
    from src.services.chimera_oracle import get_oracle_engine
    from src.services.simulation import generate_scope3_emissions_data
    
    engine = get_oracle_engine()
    
    # Ensure Scope 3 data exists
    scope3_path = Path("demo/data/scope3_emissions.csv")
    if not scope3_path.exists():
        logger.info("Generating Scope 3 emissions data...")
        generate_scope3_emissions_data(
            n_samples=2000,
            output_path=str(scope3_path)
        )
    
    # Train on Scope 3 Attribution scenario
    logger.info("Training on Scope 3 Attribution scenario...")
    result = await engine.train_on_scenario(
        scenario_id="scope3_attribution",
        csv_path=str(scope3_path),
        treatment="supplier_program",
        outcome="scope3_emissions",
        covariates=["market_conditions", "energy_mix"],
        effect_modifiers=["region", "supplier_size", "baseline_emissions"],
        n_estimators=100,
    )
    
    print("\n" + "="*50)
    print("SCOPE 3 ATTRIBUTION MODEL TRAINING")
    print("="*50)
    print(f"Status: {result.status}")
    print(f"Samples: {result.n_samples}")
    print(f"Average Treatment Effect: {result.average_treatment_effect:.2f} tCO2e")
    print(f"Effect Std Dev: {result.effect_std:.2f}")
    print(f"Model Path: {result.model_path}")
    
    if result.status == "trained":
        # Test a prediction
        print("\n" + "-"*50)
        print("TEST PREDICTIONS:")
        print("-"*50)
        
        test_contexts = [
            {"region": "EU", "supplier_size": "large", "baseline_emissions": 1000},
            {"region": "EU", "supplier_size": "small", "baseline_emissions": 500},
            {"region": "APAC", "supplier_size": "large", "baseline_emissions": 1000},
            {"region": "LATAM", "supplier_size": "medium", "baseline_emissions": 700},
        ]
        
        for ctx in test_contexts:
            pred = engine.predict_effect("scope3_attribution", ctx)
            print(f"\n{ctx}")
            print(f"  Effect: {pred.effect_estimate:.1f} tCO2e")
            print(f"  95% CI: [{pred.confidence_interval[0]:.1f}, {pred.confidence_interval[1]:.1f}]")
            print(f"  Time: {pred.prediction_time_ms:.1f}ms")
    
    # Train on Supply Chain Resilience (if data exists)
    scr_path = Path("demo/data/supply_chain_resilience.csv")
    if scr_path.exists():
        logger.info("Training on Supply Chain Resilience scenario...")
        scr_result = await engine.train_on_scenario(
            scenario_id="supply_chain_resilience",
            csv_path=str(scr_path),
            treatment="climate_stress_index",
            outcome="disruption_risk_percent",
            covariates=["operational_maturity", "inventory_days"],
            effect_modifiers=["supplier_region", "supplier_tier"],
            n_estimators=100,
        )
        print("\n" + "="*50)
        print("SUPPLY CHAIN RESILIENCE MODEL TRAINING")
        print("="*50)
        print(f"Status: {scr_result.status}")
        print(f"ATE: {scr_result.average_treatment_effect:.2f}% per unit stress")
    
    print("\n" + "="*50)
    print("AVAILABLE MODELS:")
    print("="*50)
    for scenario in engine.get_available_scenarios():
        stats = engine.get_average_treatment_effect(scenario)
        print(f"  - {scenario}: ATE={stats['ate']:.2f}, n={stats['n_samples']}")


if __name__ == "__main__":
    asyncio.run(main())
