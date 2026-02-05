"""Simulation Service for CARF - What-If Scenario Management.

Provides multi-scenario simulation capabilities for comparing
different intervention strategies and their projected outcomes.

Also includes realistic data generation for training causal models,
scenario realism scoring, and transparency integration.
"""

import logging
import math
from datetime import datetime
from enum import Enum
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
# Scenario Realism Assessment
# ============================================================================

class RealismLevel(str, Enum):
    """Scenario realism assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    SYNTHETIC = "synthetic"


class DataRichnessIndicator(BaseModel):
    """Indicators for data richness in a scenario."""
    sample_size: int = Field(..., description="Number of records")
    feature_count: int = Field(..., description="Number of features/covariates")
    treatment_balance: float = Field(..., ge=0, le=1, description="Treatment/control balance")
    covariate_coverage: float = Field(..., ge=0, le=1, description="Covariate completeness")
    temporal_span_days: int = Field(0, description="Time span of data in days")
    geographic_diversity: int = Field(1, description="Number of distinct regions")
    causal_identifiability: float = Field(..., ge=0, le=1, description="Strength of causal identification")


class ScenarioRealismScore(BaseModel):
    """Realism assessment for a simulation scenario."""
    overall_score: float = Field(..., ge=0, le=1, description="Overall realism score")
    level: RealismLevel = Field(..., description="Categorical realism level")
    data_richness: DataRichnessIndicator = Field(..., description="Data richness indicators")

    # Component scores
    sample_adequacy: float = Field(..., ge=0, le=1, description="Sample size adequacy")
    causal_validity: float = Field(..., ge=0, le=1, description="Causal structure validity")
    covariate_balance: float = Field(..., ge=0, le=1, description="Covariate balance score")
    effect_plausibility: float = Field(..., ge=0, le=1, description="Effect size plausibility")

    # Issues and recommendations
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


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


def generate_pricing_optimization_data(
    n_samples: int = 1500,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate realistic pricing optimization data with causal structure.

    Causal structure:
    - price_change → sales_volume (treatment effect, heterogeneous by segment)
    - seasonality → sales_volume (time confounder)
    - competitor_price → price_change (confounding: react to competitors)
    - market_segment → price elasticity (effect modifier)

    Args:
        n_samples: Number of records
        seed: Random seed
        output_path: Optional path to save CSV

    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)

    regions = ["North", "South", "East", "West", "Central"]
    categories = ["Electronics", "Apparel", "Home", "Food", "Industrial"]
    segments = ["Premium", "Mid-Market", "Budget", "Enterprise"]

    # Price elasticity by segment (how much sales drop per % price increase)
    segment_elasticity = {
        "Premium": -0.8,      # Less price sensitive
        "Mid-Market": -1.2,
        "Budget": -2.5,       # Very price sensitive
        "Enterprise": -0.5,   # Contract-based, least sensitive
    }

    # Seasonal multipliers (quarterly)
    season_effect = {"Q1": 0.85, "Q2": 1.0, "Q3": 0.95, "Q4": 1.3}  # Q4 holiday boost

    data = []
    for i in range(n_samples):
        region = np.random.choice(regions, p=[0.25, 0.20, 0.20, 0.15, 0.20])
        category = np.random.choice(categories, p=[0.25, 0.20, 0.25, 0.15, 0.15])
        segment = np.random.choice(segments, p=[0.15, 0.40, 0.30, 0.15])
        quarter = np.random.choice(["Q1", "Q2", "Q3", "Q4"], p=[0.25, 0.25, 0.25, 0.25])

        # Base price by category
        base_price = {
            "Electronics": 450, "Apparel": 65, "Home": 120,
            "Food": 25, "Industrial": 890
        }[category]

        # Competitor price (affects our pricing decisions - confounder)
        competitor_price = base_price * np.clip(np.random.normal(1.0, 0.15), 0.7, 1.4)

        # Treatment: Price change decision (influenced by competitor)
        # More likely to increase price if competitor is higher
        price_change_prob = 0.3 + 0.4 * (competitor_price / base_price - 0.8)
        price_change_pct = np.random.choice(
            [-10, -5, 0, 5, 10, 15],
            p=[0.1, 0.15, 0.35, 0.2, 0.15, 0.05]
        )

        # Baseline sales volume
        baseline_sales = max(50, np.random.normal(500, 150))

        # CAUSAL EFFECT: Price change on sales
        elasticity = segment_elasticity[segment]
        price_effect = baseline_sales * (price_change_pct / 100) * elasticity

        # Seasonal adjustment
        seasonal_mult = season_effect[quarter]

        # Category effect
        category_mult = {"Electronics": 0.9, "Apparel": 1.1, "Home": 1.0,
                        "Food": 1.3, "Industrial": 0.7}[category]

        # Calculate sales volume (outcome)
        sales_volume = (
            baseline_sales * seasonal_mult * category_mult
            + price_effect
            + np.random.normal(0, 30)
        )
        sales_volume = max(10, sales_volume)

        # Revenue = sales * (base_price + change)
        final_price = base_price * (1 + price_change_pct / 100)
        revenue = sales_volume * final_price

        data.append({
            "record_id": f"PRC-{i:04d}",
            "region": region,
            "product_category": category,
            "market_segment": segment,
            "seasonality": quarter,
            "competitor_price": round(competitor_price, 2),
            "base_price": round(base_price, 2),
            "price_change": price_change_pct,
            "sales_volume": round(sales_volume, 0),
            "revenue": round(revenue, 2),
        })

    df = pd.DataFrame(data)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} pricing records to {output_path}")

    return df


def generate_renewable_energy_roi_data(
    n_samples: int = 800,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate renewable energy ROI data with realistic causal structure.

    Causal structure:
    - solar_investment → energy_cost_savings (treatment effect)
    - sun_hours → energy_cost_savings (moderator)
    - facility_size → both treatment and outcome (confounder)
    - local_incentives → solar_investment (instrument-like)
    - grid_price → energy_cost_savings (exogenous driver)

    Args:
        n_samples: Number of facility records
        seed: Random seed
        output_path: Optional path to save CSV

    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)

    facility_sizes = ["small", "medium", "large"]
    facility_types = ["warehouse", "office", "manufacturing", "retail"]
    regions = ["Southwest", "Southeast", "Northeast", "Midwest", "Pacific"]

    # Regional sun hours (annual average daily hours)
    region_sun_hours = {
        "Southwest": 6.5, "Southeast": 5.2, "Northeast": 4.0,
        "Midwest": 4.5, "Pacific": 5.8
    }

    # Regional grid prices ($/kWh)
    region_grid_price = {
        "Southwest": 0.11, "Southeast": 0.10, "Northeast": 0.16,
        "Midwest": 0.09, "Pacific": 0.14
    }

    # Regional incentives (% of installation cost rebated)
    region_incentives = {
        "Southwest": 0.25, "Southeast": 0.15, "Northeast": 0.30,
        "Midwest": 0.10, "Pacific": 0.35
    }

    data = []
    for i in range(n_samples):
        region = np.random.choice(regions, p=[0.25, 0.20, 0.15, 0.20, 0.20])
        facility_size = np.random.choice(facility_sizes, p=[0.30, 0.45, 0.25])
        facility_type = np.random.choice(facility_types, p=[0.30, 0.25, 0.25, 0.20])

        # Facility characteristics
        size_sqft = {
            "small": np.random.uniform(5000, 20000),
            "medium": np.random.uniform(20000, 80000),
            "large": np.random.uniform(80000, 300000),
        }[facility_size]

        roof_area = size_sqft * np.random.uniform(0.6, 0.9)  # Usable roof
        sun_hours = region_sun_hours[region] + np.random.normal(0, 0.5)
        grid_price = region_grid_price[region] + np.random.normal(0, 0.02)
        local_incentives = int(np.random.random() < region_incentives[region] + 0.2)

        # Annual energy consumption (kWh)
        consumption_per_sqft = {
            "warehouse": 8, "office": 18, "manufacturing": 35, "retail": 22
        }[facility_type]
        annual_consumption = size_sqft * consumption_per_sqft

        # Treatment: Solar investment (influenced by incentives and size)
        invest_prob = 0.2 + 0.3 * local_incentives + 0.1 * (size_sqft / 100000)
        solar_investment = int(np.random.random() < np.clip(invest_prob, 0.1, 0.8))

        # CAUSAL EFFECT: Solar investment on energy cost savings
        if solar_investment:
            # Solar panel output: ~15W per sqft of panels
            panel_area = min(roof_area * 0.7, 50000)  # Cap practical coverage
            solar_output_kwh = panel_area * 0.015 * sun_hours * 365

            # Savings = min(solar output, consumption) * grid price
            avoided_grid = min(solar_output_kwh, annual_consumption * 0.7)
            base_savings = avoided_grid * grid_price

            # Installation year bonus (newer systems more efficient)
            efficiency_factor = np.random.uniform(0.85, 1.15)
            energy_cost_savings = base_savings * efficiency_factor
        else:
            # Minor efficiency improvements without solar
            energy_cost_savings = annual_consumption * grid_price * np.random.uniform(0.01, 0.05)

        # Add noise
        energy_cost_savings += np.random.normal(0, energy_cost_savings * 0.1)
        energy_cost_savings = max(0, energy_cost_savings)

        # Installation cost (for ROI calculation)
        if solar_investment:
            cost_per_watt = np.random.uniform(2.5, 4.0)
            panel_watts = panel_area * 15
            installation_cost = panel_watts * cost_per_watt * (1 - local_incentives * 0.25)
        else:
            installation_cost = 0

        data.append({
            "facility_id": f"FAC-{i:04d}",
            "region": region,
            "facility_type": facility_type,
            "facility_size": facility_size,
            "size_sqft": round(size_sqft, 0),
            "roof_area": round(roof_area, 0),
            "sun_hours": round(sun_hours, 2),
            "grid_price": round(grid_price, 3),
            "local_incentives": local_incentives,
            "annual_consumption_kwh": round(annual_consumption, 0),
            "solar_investment": solar_investment,
            "energy_cost_savings": round(energy_cost_savings, 2),
            "installation_cost": round(installation_cost, 2),
        })

    df = pd.DataFrame(data)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} renewable energy records to {output_path}")

    return df


def generate_shipping_carbon_data(
    n_samples: int = 1200,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate shipping mode carbon footprint data with causal structure.

    Causal structure:
    - sea_freight → co2_emissions (treatment effect)
    - distance_km → co2_emissions (scale factor)
    - weight_tons → co2_emissions (scale factor)
    - urgency → sea_freight (confounding: urgent = air)
    - product_type → both mode choice and emissions

    Emission factors (gCO2 per ton-km):
    - Air freight: ~500-600
    - Road freight: ~60-150
    - Rail freight: ~20-40
    - Sea freight: ~10-20

    Args:
        n_samples: Number of shipment records
        seed: Random seed
        output_path: Optional path to save CSV

    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)

    routes = [
        ("asia_europe", 18000), ("asia_na", 12000), ("europe_na", 6000),
        ("intra_europe", 2500), ("intra_asia", 5000), ("europe_sa", 10000),
        ("na_sa", 8000), ("apac_africa", 14000)
    ]
    route_names = [r[0] for r in routes]
    route_distances = {r[0]: r[1] for r in routes}

    product_types = ["electronics", "machinery", "textiles", "pharma",
                    "food", "raw_materials", "automotive", "consumer_goods"]
    urgency_levels = ["low", "medium", "high", "critical"]

    # Product type affects mode choice (perishable/high-value = air)
    product_air_propensity = {
        "electronics": 0.4, "machinery": 0.2, "textiles": 0.15, "pharma": 0.6,
        "food": 0.5, "raw_materials": 0.05, "automotive": 0.1, "consumer_goods": 0.25
    }

    # Emission factors (gCO2 per ton-km)
    emission_factors = {"air": 550, "road": 100, "rail": 30, "sea": 15}

    data = []
    for i in range(n_samples):
        route = np.random.choice(route_names)
        distance_km = route_distances[route] + np.random.normal(0, 500)
        distance_km = max(500, distance_km)

        product_type = np.random.choice(product_types)
        urgency = np.random.choice(
            urgency_levels,
            p=[0.40, 0.30, 0.20, 0.10]
        )

        weight_tons = max(0.5, np.random.exponential(12))

        # Treatment: Sea freight vs other modes
        # Influenced by urgency and product type (confounding)
        urgency_factor = {"low": 0.8, "medium": 0.5, "high": 0.15, "critical": 0.02}
        sea_prob = urgency_factor[urgency] * (1 - product_air_propensity[product_type])

        # Long distance favors sea
        if distance_km > 10000:
            sea_prob += 0.2
        elif distance_km < 3000:
            sea_prob -= 0.3

        sea_freight = int(np.random.random() < np.clip(sea_prob, 0.05, 0.95))

        # Determine actual mode (for non-sea, could be air/road/rail)
        if sea_freight:
            mode = "sea"
        else:
            if urgency in ["high", "critical"] or distance_km > 8000:
                mode = "air"
            elif distance_km < 2000:
                mode = np.random.choice(["road", "rail"], p=[0.6, 0.4])
            else:
                mode = np.random.choice(["air", "road"], p=[0.4, 0.6])

        # CAUSAL EFFECT: Mode on emissions
        base_emission_factor = emission_factors[mode]

        # Efficiency variations
        efficiency_var = np.random.uniform(0.85, 1.20)

        # Calculate emissions (kg CO2)
        co2_emissions_kg = (base_emission_factor * efficiency_var *
                          weight_tons * distance_km / 1000)

        # Add some noise
        co2_emissions_kg += np.random.normal(0, co2_emissions_kg * 0.05)
        co2_emissions_kg = max(10, co2_emissions_kg)

        # Transit time (days)
        transit_speed = {"air": 800, "road": 50, "rail": 60, "sea": 30}  # km/day
        transit_time = distance_km / transit_speed[mode]

        data.append({
            "shipment_id": f"SHP-{i:04d}",
            "route": route,
            "distance_km": round(distance_km, 0),
            "product_type": product_type,
            "urgency": urgency,
            "weight_tons": round(weight_tons, 2),
            "sea_freight": sea_freight,
            "transport_mode": mode,
            "co2_emissions_kg": round(co2_emissions_kg, 1),
            "transit_time_days": round(transit_time, 1),
        })

    df = pd.DataFrame(data)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} shipping records to {output_path}")

    return df


def generate_customer_churn_data(
    n_samples: int = 2000,
    seed: int = 42,
    output_path: str | None = None
) -> pd.DataFrame:
    """Generate customer churn data with discount intervention.

    Causal structure:
    - discount_offered → churned (treatment effect)
    - tenure_months → churned (protective factor)
    - monthly_spend → discount_offered (confounding: target high-risk)
    - region → churned (baseline differences)
    - support_tickets → churned (risk indicator)

    Args:
        n_samples: Number of customer records
        seed: Random seed
        output_path: Optional path to save CSV

    Returns:
        DataFrame with generated data
    """
    np.random.seed(seed)

    regions = ["North", "South", "East", "West"]
    plan_types = ["Basic", "Standard", "Premium", "Enterprise"]

    data = []
    for i in range(n_samples):
        region = np.random.choice(regions, p=[0.25, 0.25, 0.25, 0.25])
        plan_type = np.random.choice(plan_types, p=[0.30, 0.40, 0.20, 0.10])

        # Customer characteristics
        tenure_months = max(1, np.random.exponential(24))
        age = np.random.randint(18, 75)

        # Monthly spend by plan
        base_spend = {"Basic": 25, "Standard": 50, "Premium": 100, "Enterprise": 500}
        monthly_spend = base_spend[plan_type] * np.random.uniform(0.8, 1.3)

        # Support tickets (higher = more issues)
        support_tickets = np.random.poisson(2)

        # Calculate churn risk (pre-treatment)
        base_churn_risk = 0.15
        tenure_effect = -0.005 * tenure_months  # Longer tenure = lower risk
        spend_effect = -0.001 * monthly_spend   # Higher spend = lower risk (more invested)
        ticket_effect = 0.03 * support_tickets  # More tickets = higher risk
        region_effect = {"North": 0, "South": 0.02, "East": -0.01, "West": 0.01}[region]

        churn_risk = base_churn_risk + tenure_effect + spend_effect + ticket_effect + region_effect
        churn_risk = np.clip(churn_risk, 0.02, 0.60)

        # Treatment: Discount offered (targeted at high-risk customers)
        discount_prob = 0.1 + 0.8 * (churn_risk - 0.02) / 0.58
        discount_offered = int(np.random.random() < np.clip(discount_prob, 0.05, 0.70))

        # CAUSAL EFFECT: Discount on churn
        # Discount reduces churn risk by ~40% on average
        if discount_offered:
            treatment_effect = -churn_risk * 0.40  # 40% reduction
            # Heterogeneous: more effective for medium-tenure customers
            if 6 < tenure_months < 36:
                treatment_effect *= 1.3
        else:
            treatment_effect = 0

        final_churn_prob = np.clip(churn_risk + treatment_effect, 0.01, 0.90)
        churned = int(np.random.random() < final_churn_prob)

        data.append({
            "customer_id": f"CUST-{i:05d}",
            "region": region,
            "plan_type": plan_type,
            "tenure_months": round(tenure_months, 1),
            "age": age,
            "monthly_spend": round(monthly_spend, 2),
            "support_tickets": support_tickets,
            "discount_offered": discount_offered,
            "churned": churned,
        })

    df = pd.DataFrame(data)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Generated {n_samples} churn records to {output_path}")

    return df


def assess_scenario_realism(
    df: pd.DataFrame,
    treatment_col: str,
    outcome_col: str,
    covariates: list[str] | None = None,
) -> ScenarioRealismScore:
    """Assess the realism of a simulation scenario/dataset.

    Evaluates:
    - Sample size adequacy for causal inference
    - Treatment/control balance (positivity)
    - Covariate coverage and completeness
    - Effect size plausibility
    - Causal identifiability assumptions

    Args:
        df: Dataset to assess
        treatment_col: Treatment variable column
        outcome_col: Outcome variable column
        covariates: List of covariate columns

    Returns:
        ScenarioRealismScore with detailed assessment
    """
    covariates = covariates or []
    issues = []
    recommendations = []

    n = len(df)
    n_features = len(df.columns)

    # 1. Sample size adequacy
    if n < 100:
        sample_adequacy = 0.3
        issues.append(f"Sample size ({n}) too small for reliable causal inference")
        recommendations.append("Collect at least 500 samples for robust analysis")
    elif n < 500:
        sample_adequacy = 0.6
        issues.append(f"Sample size ({n}) marginal for causal inference")
    elif n < 2000:
        sample_adequacy = 0.85
    else:
        sample_adequacy = 1.0

    # 2. Treatment/control balance
    if treatment_col in df.columns:
        treatment_counts = df[treatment_col].value_counts(normalize=True)
        if len(treatment_counts) >= 2:
            min_prop = treatment_counts.min()
            treatment_balance = min(1.0, min_prop / 0.3)  # Ideal: at least 30% minority
            if min_prop < 0.1:
                issues.append(f"Severe treatment imbalance: minority group only {min_prop:.1%}")
                recommendations.append("Use propensity score methods to address imbalance")
            elif min_prop < 0.2:
                issues.append(f"Treatment imbalance: minority group {min_prop:.1%}")
        else:
            treatment_balance = 0.0
            issues.append("Treatment variable has only one value")
    else:
        treatment_balance = 0.0
        issues.append(f"Treatment column '{treatment_col}' not found")

    # 3. Covariate coverage
    missing_covariates = [c for c in covariates if c not in df.columns]
    if missing_covariates:
        issues.append(f"Missing covariates: {missing_covariates}")
        covariate_coverage = 1 - len(missing_covariates) / max(len(covariates), 1)
    else:
        covariate_coverage = 1.0

    # Check for missing values in covariates
    available_covs = [c for c in covariates if c in df.columns]
    if available_covs:
        cov_missing_rate = df[available_covs].isnull().mean().mean()
        if cov_missing_rate > 0.1:
            covariate_coverage *= (1 - cov_missing_rate)
            issues.append(f"High missing rate in covariates: {cov_missing_rate:.1%}")

    # 4. Effect size plausibility
    if outcome_col in df.columns and treatment_col in df.columns:
        try:
            treated = df[df[treatment_col] == 1][outcome_col]
            control = df[df[treatment_col] == 0][outcome_col]

            if len(treated) > 0 and len(control) > 0:
                effect_size = (treated.mean() - control.mean())
                pooled_std = np.sqrt(
                    (treated.var() * len(treated) + control.var() * len(control)) /
                    (len(treated) + len(control))
                )
                if pooled_std > 0:
                    cohens_d = abs(effect_size) / pooled_std
                    # Plausible effects: Cohen's d typically 0.2-1.5
                    if cohens_d < 0.05:
                        effect_plausibility = 0.5
                        issues.append("Effect size very small - may lack practical significance")
                    elif cohens_d > 3.0:
                        effect_plausibility = 0.4
                        issues.append(f"Effect size unusually large (d={cohens_d:.2f}) - verify data")
                    else:
                        effect_plausibility = min(1.0, 0.5 + 0.5 * (1 - abs(cohens_d - 0.8) / 2))
                else:
                    effect_plausibility = 0.7
            else:
                effect_plausibility = 0.5
        except Exception:
            effect_plausibility = 0.5
    else:
        effect_plausibility = 0.5
        if outcome_col not in df.columns:
            issues.append(f"Outcome column '{outcome_col}' not found")

    # 5. Causal identifiability (heuristic)
    # More covariates + larger sample = better identification
    covariate_ratio = len(available_covs) / max(n_features - 2, 1)
    sample_factor = min(1.0, n / 1000)
    causal_identifiability = (covariate_ratio * 0.4 + sample_factor * 0.4 +
                             treatment_balance * 0.2)

    # Temporal span
    date_cols = [c for c in df.columns if any(d in c.lower() for d in
                                              ['date', 'time', 'timestamp'])]
    temporal_span = 0
    if date_cols:
        try:
            date_col = date_cols[0]
            dates = pd.to_datetime(df[date_col])
            temporal_span = (dates.max() - dates.min()).days
        except Exception:
            pass

    # Geographic diversity
    geo_cols = [c for c in df.columns if any(g in c.lower() for g in
                                            ['region', 'country', 'state', 'location'])]
    geo_diversity = 1
    if geo_cols:
        geo_diversity = df[geo_cols[0]].nunique()

    # Build data richness indicators
    data_richness = DataRichnessIndicator(
        sample_size=n,
        feature_count=n_features,
        treatment_balance=treatment_balance,
        covariate_coverage=covariate_coverage,
        temporal_span_days=temporal_span,
        geographic_diversity=geo_diversity,
        causal_identifiability=causal_identifiability,
    )

    # Calculate overall score
    overall_score = (
        sample_adequacy * 0.25 +
        treatment_balance * 0.25 +
        covariate_coverage * 0.20 +
        effect_plausibility * 0.15 +
        causal_identifiability * 0.15
    )

    # Determine level
    if overall_score >= 0.85:
        level = RealismLevel.EXCELLENT
    elif overall_score >= 0.70:
        level = RealismLevel.GOOD
    elif overall_score >= 0.55:
        level = RealismLevel.FAIR
    elif overall_score >= 0.40:
        level = RealismLevel.POOR
    else:
        level = RealismLevel.SYNTHETIC

    # Add recommendations based on issues
    if sample_adequacy < 0.8 and "Collect" not in str(recommendations):
        recommendations.append("Increase sample size for more reliable estimates")
    if treatment_balance < 0.7 and "propensity" not in str(recommendations):
        recommendations.append("Consider propensity score matching to improve balance")
    if covariate_coverage < 0.8:
        recommendations.append("Include additional covariates to reduce confounding")

    return ScenarioRealismScore(
        overall_score=overall_score,
        level=level,
        data_richness=data_richness,
        sample_adequacy=sample_adequacy,
        causal_validity=causal_identifiability,
        covariate_balance=covariate_coverage,
        effect_plausibility=effect_plausibility,
        issues=issues,
        recommendations=recommendations,
    )


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


class EnhancedSimulationResult(BaseModel):
    """Simulation result with transparency and reliability information."""

    result: SimulationResult = Field(..., description="Base simulation result")
    realism_score: ScenarioRealismScore | None = Field(None, description="Scenario realism assessment")
    reliability_score: float = Field(0.0, ge=0, le=1, description="Overall reliability")
    agents_used: list[str] = Field(default_factory=list, description="Agents involved in analysis")
    data_sources: list[str] = Field(default_factory=list, description="Data sources used")
    methodology_transparency: dict[str, Any] = Field(default_factory=dict, description="Method details")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")


class SimulationService:
    """Service for managing what-if scenario simulations.

    Features:
    - Multi-scenario simulation and comparison
    - Realistic data generation with known causal structure
    - Scenario realism assessment
    - Transparency integration for reliability scoring
    """

    # Data generators registry
    DATA_GENERATORS = {
        "scope3_emissions": generate_scope3_emissions_data,
        "supply_chain_resilience": generate_supply_chain_resilience_data,
        "pricing_optimization": generate_pricing_optimization_data,
        "renewable_energy_roi": generate_renewable_energy_roi_data,
        "shipping_carbon": generate_shipping_carbon_data,
        "customer_churn": generate_customer_churn_data,
    }

    def __init__(self):
        self.causal_engine = CausalInferenceEngine()
        self.neo4j = get_neo4j_service()
        self._running_simulations: dict[str, SimulationResult] = {}
        self._realism_cache: dict[str, ScenarioRealismScore] = {}
    
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

    async def run_scenario_with_transparency(
        self,
        config: ScenarioConfig,
        data: pd.DataFrame | None = None,
        treatment_col: str | None = None,
        outcome_col: str | None = None,
        covariates: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> EnhancedSimulationResult:
        """Run scenario with full transparency and reliability reporting.

        Args:
            config: Scenario configuration
            data: Optional DataFrame for realism assessment
            treatment_col: Treatment column name
            outcome_col: Outcome column name
            covariates: List of covariate columns
            context: Additional context

        Returns:
            EnhancedSimulationResult with transparency information
        """
        # Run base simulation
        result = await self.run_scenario(config, context)

        # Assess scenario realism if data provided
        realism_score = None
        if data is not None and treatment_col and outcome_col:
            realism_score = assess_scenario_realism(
                df=data,
                treatment_col=treatment_col,
                outcome_col=outcome_col,
                covariates=covariates,
            )
            self._realism_cache[config.id] = realism_score

        # Calculate reliability score
        reliability_components = []

        # Component 1: Simulation success
        if result.status == "completed":
            reliability_components.append(0.3)
        else:
            reliability_components.append(0.0)

        # Component 2: Confidence interval width
        ci_width = abs(result.confidence_interval[1] - result.confidence_interval[0])
        effect_magnitude = abs(result.effect_estimate) if result.effect_estimate != 0 else 1
        ci_reliability = max(0, 1 - ci_width / (2 * effect_magnitude))
        reliability_components.append(ci_reliability * 0.25)

        # Component 3: Refutation pass rate
        refutation_rate = result.metrics.get("refutation_rate", 0.5)
        reliability_components.append(refutation_rate * 0.25)

        # Component 4: Realism score
        if realism_score:
            reliability_components.append(realism_score.overall_score * 0.2)
        else:
            reliability_components.append(0.1)

        reliability_score = sum(reliability_components)

        # Methodology transparency
        methodology = {
            "analysis_type": "causal_inference",
            "estimation_method": context.get("method_name", "backdoor.linear_regression") if context else "backdoor.linear_regression",
            "refutation_tests": ["placebo_treatment", "random_common_cause", "data_subset"],
            "confidence_level": 0.95,
            "interventions": [i.model_dump() for i in config.interventions],
        }

        # Known limitations
        limitations = []
        if result.confidence < 0.7:
            limitations.append("Low confidence - interpret with caution")
        if realism_score and realism_score.overall_score < 0.6:
            limitations.append("Data realism concerns may affect validity")
        if ci_width > effect_magnitude:
            limitations.append("Wide confidence interval - effect estimate uncertain")

        for issue in (realism_score.issues if realism_score else []):
            limitations.append(f"Data: {issue}")

        return EnhancedSimulationResult(
            result=result,
            realism_score=realism_score,
            reliability_score=reliability_score,
            agents_used=["CausalInferenceEngine", "DoWhy", "RefutationValidator"],
            data_sources=[config.baseline_dataset_id] if config.baseline_dataset_id else [],
            methodology_transparency=methodology,
            limitations=limitations,
        )

    def generate_scenario_data(
        self,
        scenario_type: str,
        n_samples: int = 1000,
        seed: int = 42,
        output_path: str | None = None
    ) -> pd.DataFrame | None:
        """Generate realistic data for a scenario type.

        Args:
            scenario_type: Type of scenario (e.g., 'scope3_emissions', 'pricing_optimization')
            n_samples: Number of samples to generate
            seed: Random seed for reproducibility
            output_path: Optional path to save CSV

        Returns:
            Generated DataFrame or None if scenario type not found
        """
        generator = self.DATA_GENERATORS.get(scenario_type)
        if generator:
            return generator(n_samples=n_samples, seed=seed, output_path=output_path)
        else:
            logger.warning(f"Unknown scenario type: {scenario_type}. Available: {list(self.DATA_GENERATORS.keys())}")
            return None

    def list_available_generators(self) -> list[dict[str, str]]:
        """List available data generators with descriptions."""
        descriptions = {
            "scope3_emissions": "Scope 3 emissions data with supplier sustainability programs",
            "supply_chain_resilience": "Supply chain disruption risk under climate stress",
            "pricing_optimization": "Pricing strategy impact on sales and revenue",
            "renewable_energy_roi": "Renewable energy investment ROI by facility",
            "shipping_carbon": "Shipping mode carbon footprint comparison",
            "customer_churn": "Customer churn with discount intervention",
        }
        return [
            {"name": name, "description": descriptions.get(name, "")}
            for name in self.DATA_GENERATORS.keys()
        ]

    def get_cached_realism_score(self, scenario_id: str) -> ScenarioRealismScore | None:
        """Get cached realism score for a scenario."""
        return self._realism_cache.get(scenario_id)


# Singleton instance
_simulation_service: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    """Get or create the simulation service singleton."""
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = SimulationService()
    return _simulation_service
