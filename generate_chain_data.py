import pandas as pd
import numpy as np
import random
import os

def generate_supply_chain_data(n_samples=2000):
    """
    Generates a synthetic dataset for 'Supply Chain Resilience under Climate Stress'.
    Focus: How does 'climate_stress_index' affect 'supplier_disruption_risk'?
    """
    print(f"Generating {n_samples} samples for Supply Chain Resilience Scenario...")
    
    # 1. Generate Covariates (Confounders & Context)
    
    # Region categories
    regions = ['APAC', 'EMEA', 'NAM', 'LATAM']
    supplier_region = np.random.choice(regions, n_samples, p=[0.4, 0.3, 0.2, 0.1])
    
    # Supplier Tier (Tier 1 is direct, Tier 3 is raw material)
    supplier_tiers = ['Tier 1', 'Tier 2', 'Tier 3']
    supplier_tier = np.random.choice(supplier_tiers, n_samples, p=[0.2, 0.3, 0.5])
    
    # Operational Maturity (0-100)
    # Higher maturity -> better able to handle stress
    operational_maturity = np.random.normal(60, 15, n_samples).clip(0, 100)
    
    # Inventory Buffer (Days)
    inventory_days = np.random.lognormal(3, 0.5, n_samples).clip(5, 90)
    
    # 2. Generate Treatment: Climate Stress Index (0-10)
    # This represents the intensity of climate events (floods, heatwaves) in the supplier's region.
    # It is correlated with Region (APAC/LATAM might have higher stress in this scenario).
    
    base_stress = np.random.normal(4, 2, n_samples)
    region_stress_map = {'APAC': 2.0, 'LATAM': 1.5, 'EMEA': 0.5, 'NAM': 0.0}
    
    climate_stress_index = (
        base_stress + 
        np.array([region_stress_map[r] for r in supplier_region])
    ).clip(0, 10)
    
    # 3. Generate Outcome: Supplier Disruption Risk (0-100%)
    # Causal Model:
    # Disruption Risk = f(Climate Stress, Maturity, Inventory, Tier)
    # - Higher Climate Stress -> Higher Risk (Treatment Effect)
    # - Higher Maturity -> Lower Risk (Mitigator)
    # - Higher Inventory -> Lower Risk (Buffer)
    # - Tier 3 -> Higher Risk (Visibility issues)
    
    # True Causal Effect: 1 unit of stress -> +5% risk (approx)
    
    risk_score = (
        20 +                                      # Baseline risk
        5.0 * climate_stress_index +              # Causal Effect
        -0.4 * operational_maturity +             # Maturity reduces risk
        -0.2 * inventory_days +                   # Inventory reduces risk
        (np.array([10 if t == 'Tier 3' else 0 for t in supplier_tier])) + # Tier 3 operational opacity
        np.random.normal(0, 5, n_samples)         # Noise
    ).clip(0, 100)
    
    # Create DataFrame
    df = pd.DataFrame({
        'supplier_id': [f'SUP-{i:04d}' for i in range(n_samples)],
        'supplier_region': supplier_region,
        'supplier_tier': supplier_tier,
        'operational_maturity': operational_maturity.round(1),
        'inventory_days': inventory_days.round(1),
        'climate_stress_index': climate_stress_index.round(2),
        'disruption_risk_percent': risk_score.round(2)
    })
    
    # Save
    filename = 'supply_chain_resilience.csv'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)
    df.to_csv(file_path, index=False)
    print(f"✅ Dataset saved to {file_path}")
    print("\n--- Analysis Hint ---")
    print("Suggested Question: 'What is the causal effect of climate_stress_index on disruption_risk_percent?'")
    print("Expected Result: Positive causal effect (~5.0).")
    print("Confounders to control: operational_maturity, inventory_days, supplier_region")

if __name__ == "__main__":
    generate_supply_chain_data()
