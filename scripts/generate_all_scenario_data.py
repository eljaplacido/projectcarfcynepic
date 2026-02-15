"""Generate comprehensive simulation data for all scenario types.

Produces realistic datasets with known causal structures for end-to-end
platform testing. Each scenario covers a different Cynefin domain pathway
and analytical capability.

Usage:
    cd C:\\Users\\35845\\Desktop\\DIGICISU\\projectcarf
    python scripts/generate_all_scenario_data.py

Generates:
    demo/data/scope3_emissions.csv        (2000 rows, Complicated → Causal)
    demo/data/supply_chain_resilience.csv  (1500 rows, Complex → Bayesian)
    demo/data/pricing_data.csv            (2000 rows, Complicated → Causal)
    demo/data/renewable_energy.csv        (1000 rows, Complicated → Causal)
    demo/data/shipping_carbon.csv         (1500 rows, Complicated → Causal)
    demo/data/customer_churn.csv          (2000 rows, Complicated → Causal)
    demo/data/market_uncertainty.csv      (1000 rows, Complex → Bayesian)
    demo/data/crisis_response.csv         (500 rows, Chaotic → Circuit Breaker)
"""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from src.services.simulation import (
    generate_scope3_emissions_data,
    generate_supply_chain_resilience_data,
    generate_pricing_optimization_data,
    generate_renewable_energy_roi_data,
    generate_shipping_carbon_data,
    generate_customer_churn_data,
)

DEMO_DATA_DIR = project_root / "demo" / "data"


def generate_market_uncertainty_data(n_samples: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generate market uncertainty data for Bayesian/Complex domain testing.

    This data has high inherent uncertainty (aleatoric) and limited information
    (epistemic), making it suitable for Bayesian belief updating.
    """
    rng = np.random.default_rng(seed)

    # Market segments with different volatility profiles
    segments = rng.choice(["tech", "energy", "healthcare", "finance", "consumer"], n_samples)
    segment_volatility = {"tech": 0.35, "energy": 0.45, "healthcare": 0.20, "finance": 0.30, "consumer": 0.15}

    # Base adoption rate varies by segment
    segment_base = {"tech": 0.42, "energy": 0.28, "healthcare": 0.55, "finance": 0.38, "consumer": 0.62}

    base_rates = np.array([segment_base[s] for s in segments])
    volatilities = np.array([segment_volatility[s] for s in segments])

    # Time periods (quarterly)
    quarters = rng.choice(["Q1", "Q2", "Q3", "Q4"], n_samples)
    quarter_effect = {"Q1": -0.05, "Q2": 0.02, "Q3": 0.08, "Q4": -0.03}
    q_effects = np.array([quarter_effect[q] for q in quarters])

    # Market sentiment (noisy signal)
    sentiment = rng.normal(0.5, 0.2, n_samples).clip(0, 1)

    # Adoption probability with genuine uncertainty
    noise = rng.normal(0, volatilities)
    adoption_rate = (base_rates + q_effects + 0.15 * sentiment + noise).clip(0, 1)

    # Confidence score (lower for high-volatility segments)
    confidence = (0.7 - volatilities + rng.normal(0, 0.05, n_samples)).clip(0.3, 0.95)

    df = pd.DataFrame({
        "observation_id": [f"MKT-{i:04d}" for i in range(n_samples)],
        "segment": segments,
        "quarter": quarters,
        "market_sentiment": sentiment.round(3),
        "adoption_rate": adoption_rate.round(4),
        "volatility": volatilities.round(3),
        "confidence_score": confidence.round(3),
        "sample_size": rng.integers(50, 500, n_samples),
    })

    return df


def generate_crisis_response_data(n_samples: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate crisis response data for Chaotic/Circuit Breaker domain testing.

    This data represents rapidly evolving situations with high entropy,
    multiple simultaneous signals, and time pressure.
    """
    rng = np.random.default_rng(seed)

    crisis_types = rng.choice(
        ["supply_disruption", "cyber_incident", "regulatory_change", "market_crash", "natural_disaster"],
        n_samples,
        p=[0.25, 0.20, 0.15, 0.25, 0.15],
    )

    # Severity escalates rapidly
    severity = rng.beta(2, 1.5, n_samples)  # Skewed toward high severity

    # Response time pressure (minutes)
    urgency_minutes = rng.exponential(30, n_samples).clip(5, 480)

    # Multiple simultaneous signals (high entropy)
    signal_count = rng.poisson(4, n_samples).clip(1, 12)
    contradictory_signals = rng.binomial(1, 0.4, n_samples)

    # Impact dimensions
    financial_impact = (severity * rng.uniform(10000, 5000000, n_samples)).round(2)
    operational_impact = rng.uniform(0, 1, n_samples).round(3)
    reputational_risk = (severity * rng.uniform(0.3, 1.0, n_samples)).round(3)

    # Information completeness (low in chaotic situations)
    info_completeness = rng.beta(1.5, 4, n_samples).round(3)

    # Entropy (high for chaotic scenarios)
    entropy = (0.6 + 0.4 * rng.beta(3, 1.5, n_samples)).round(3)

    df = pd.DataFrame({
        "incident_id": [f"INC-{i:04d}" for i in range(n_samples)],
        "crisis_type": crisis_types,
        "severity": severity.round(3),
        "urgency_minutes": urgency_minutes.round(1),
        "signal_count": signal_count,
        "contradictory_signals": contradictory_signals,
        "financial_impact": financial_impact,
        "operational_impact": operational_impact,
        "reputational_risk": reputational_risk,
        "info_completeness": info_completeness,
        "entropy": entropy,
        "requires_escalation": (severity > 0.7).astype(int),
    })

    return df


def main():
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)

    generators = [
        ("scope3_emissions", generate_scope3_emissions_data, 2000, "Complicated (Causal)"),
        ("supply_chain_resilience", generate_supply_chain_resilience_data, 1500, "Complex (Bayesian)"),
        ("pricing_data", generate_pricing_optimization_data, 2000, "Complicated (Causal)"),
        ("renewable_energy", generate_renewable_energy_roi_data, 1000, "Complicated (Causal)"),
        ("shipping_carbon", generate_shipping_carbon_data, 1500, "Complicated (Causal)"),
        ("customer_churn", generate_customer_churn_data, 2000, "Complicated (Causal)"),
        ("market_uncertainty", generate_market_uncertainty_data, 1000, "Complex (Bayesian)"),
        ("crisis_response", generate_crisis_response_data, 500, "Chaotic (Circuit Breaker)"),
    ]

    print("=" * 70)
    print("CYNEPIC Platform — Comprehensive Scenario Data Generation")
    print("=" * 70)

    for name, gen_func, n_samples, domain in generators:
        output_path = DEMO_DATA_DIR / f"{name}.csv"
        print(f"\n  Generating {name} ({n_samples} rows, {domain})...")

        df = gen_func(n_samples=n_samples, seed=42)
        df.to_csv(output_path, index=False)

        print(f"    Saved: {output_path}")
        print(f"    Columns: {list(df.columns)}")
        print(f"    Shape: {df.shape}")

    print("\n" + "=" * 70)
    print("All scenario data generated. Ready for platform testing.")
    print(f"Data directory: {DEMO_DATA_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
