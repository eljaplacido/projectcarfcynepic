"""Unit tests for the Simulation Service.

Tests cover:
- Data generator functions (scope3, supply chain, pricing, energy, shipping, churn)
- Scenario realism assessment
- Shannon entropy calculation
- Pydantic models (Intervention, ScenarioConfig, SimulationResult, etc.)
- SimulationService initialization, status, comparison
"""

import numpy as np
import pandas as pd
import pytest

from src.services.simulation import (
    DataRichnessIndicator,
    EnhancedSimulationResult,
    Intervention,
    RealismLevel,
    ScenarioConfig,
    ScenarioRealismScore,
    SimulationComparison,
    SimulationResult,
    SimulationService,
    assess_scenario_realism,
    calculate_shannon_entropy,
    generate_customer_churn_data,
    generate_pricing_optimization_data,
    generate_renewable_energy_roi_data,
    generate_scope3_emissions_data,
    generate_shipping_carbon_data,
    generate_supply_chain_resilience_data,
)


# =============================================================================
# Data Generator Tests
# =============================================================================


class TestGenerateScope3EmissionsData:
    """Tests for Scope 3 emissions data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_scope3_emissions_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_scope3_emissions_data(n_samples=50, seed=42)
        # Check that key columns exist (supplier_id and supplier_program at minimum)
        assert "supplier_id" in df.columns
        assert "supplier_program" in df.columns
        assert len(df.columns) >= 6

    def test_reproducible_with_seed(self):
        df1 = generate_scope3_emissions_data(n_samples=50, seed=42)
        df2 = generate_scope3_emissions_data(n_samples=50, seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_treatment_is_binary(self):
        df = generate_scope3_emissions_data(n_samples=200, seed=42)
        assert set(df["supplier_program"].unique()).issubset({0, 1})

    def test_emissions_column_exists(self):
        df = generate_scope3_emissions_data(n_samples=200, seed=42)
        # Find the emissions column (may be scope3_emissions or similar)
        emission_cols = [c for c in df.columns if "emission" in c.lower()]
        assert len(emission_cols) > 0, "No emissions column found"

    def test_saves_to_file(self, tmp_path):
        output = str(tmp_path / "scope3.csv")
        df = generate_scope3_emissions_data(n_samples=50, seed=42, output_path=output)
        assert len(df) == 50
        loaded = pd.read_csv(output)
        assert len(loaded) == 50


class TestGenerateSupplyChainResilienceData:
    """Tests for supply chain resilience data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_supply_chain_resilience_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_supply_chain_resilience_data(n_samples=50, seed=42)
        required = [
            "supplier_id", "supplier_region", "supplier_tier",
            "operational_maturity", "inventory_days",
            "climate_stress_index", "disruption_risk_percent",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_climate_stress_bounded(self):
        df = generate_supply_chain_resilience_data(n_samples=200, seed=42)
        assert (df["climate_stress_index"] >= 0).all()
        assert (df["climate_stress_index"] <= 10).all()

    def test_disruption_risk_bounded(self):
        df = generate_supply_chain_resilience_data(n_samples=200, seed=42)
        assert (df["disruption_risk_percent"] >= 0).all()
        assert (df["disruption_risk_percent"] <= 100).all()


class TestGeneratePricingOptimizationData:
    """Tests for pricing optimization data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_pricing_optimization_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_pricing_optimization_data(n_samples=50, seed=42)
        required = [
            "record_id", "region", "product_category", "market_segment",
            "seasonality", "competitor_price", "base_price",
            "price_change", "sales_volume", "revenue",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_revenue_positive(self):
        df = generate_pricing_optimization_data(n_samples=200, seed=42)
        assert (df["revenue"] > 0).all()

    def test_sales_volume_positive(self):
        df = generate_pricing_optimization_data(n_samples=200, seed=42)
        assert (df["sales_volume"] >= 10).all()


class TestGenerateRenewableEnergyROIData:
    """Tests for renewable energy ROI data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_renewable_energy_roi_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_renewable_energy_roi_data(n_samples=50, seed=42)
        required = [
            "facility_id", "region", "facility_type", "facility_size",
            "solar_investment", "energy_cost_savings",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_solar_investment_binary(self):
        df = generate_renewable_energy_roi_data(n_samples=200, seed=42)
        assert set(df["solar_investment"].unique()).issubset({0, 1})

    def test_savings_non_negative(self):
        df = generate_renewable_energy_roi_data(n_samples=200, seed=42)
        assert (df["energy_cost_savings"] >= 0).all()


class TestGenerateShippingCarbonData:
    """Tests for shipping carbon footprint data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_shipping_carbon_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_shipping_carbon_data(n_samples=50, seed=42)
        required = [
            "shipment_id", "route", "product_type",
            "weight_tons", "co2_emissions_kg",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_emissions_positive(self):
        df = generate_shipping_carbon_data(n_samples=200, seed=42)
        assert (df["co2_emissions_kg"] > 0).all()


class TestGenerateCustomerChurnData:
    """Tests for customer churn data generator."""

    def test_generates_correct_number_of_rows(self):
        df = generate_customer_churn_data(n_samples=100, seed=42)
        assert len(df) == 100

    def test_has_required_columns(self):
        df = generate_customer_churn_data(n_samples=50, seed=42)
        required = [
            "customer_id", "region", "plan_type", "tenure_months",
            "monthly_spend", "support_tickets", "discount_offered", "churned",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_treatment_is_binary(self):
        df = generate_customer_churn_data(n_samples=200, seed=42)
        assert set(df["discount_offered"].unique()).issubset({0, 1})

    def test_outcome_is_binary(self):
        df = generate_customer_churn_data(n_samples=200, seed=42)
        assert set(df["churned"].unique()).issubset({0, 1})


# =============================================================================
# Scenario Realism Assessment Tests
# =============================================================================


class TestAssessScenarioRealism:
    """Tests for scenario realism scoring."""

    def test_large_balanced_dataset_scores_high(self):
        df = generate_scope3_emissions_data(n_samples=2000, seed=42)
        score = assess_scenario_realism(
            df, treatment_col="supplier_program", outcome_col="scope3_emissions",
            covariates=["supplier_size", "supplier_region", "baseline_emissions"],
        )
        assert isinstance(score, ScenarioRealismScore)
        assert score.overall_score > 0.6
        assert score.sample_adequacy > 0.8

    def test_small_dataset_warns(self):
        df = generate_scope3_emissions_data(n_samples=50, seed=42)
        score = assess_scenario_realism(
            df, treatment_col="supplier_program", outcome_col="scope3_emissions",
        )
        assert score.sample_adequacy < 0.7
        assert any("sample" in issue.lower() for issue in score.issues)

    def test_missing_treatment_column(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        score = assess_scenario_realism(df, treatment_col="missing", outcome_col="b")
        assert any("not found" in issue for issue in score.issues)

    def test_missing_outcome_column(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        score = assess_scenario_realism(df, treatment_col="a", outcome_col="missing")
        assert any("not found" in issue for issue in score.issues)

    def test_missing_covariates_detected(self):
        df = pd.DataFrame({"t": [0, 1, 0, 1], "y": [1, 2, 3, 4]})
        score = assess_scenario_realism(
            df, treatment_col="t", outcome_col="y", covariates=["z1", "z2"],
        )
        assert any("missing" in issue.lower() for issue in score.issues)


# =============================================================================
# Shannon Entropy Tests
# =============================================================================


class TestCalculateShannonEntropy:
    """Tests for Shannon entropy calculation."""

    def test_empty_string(self):
        assert calculate_shannon_entropy("") == 0.0

    def test_single_token(self):
        assert calculate_shannon_entropy("hello") == 0.0

    def test_uniform_distribution(self):
        # All unique tokens → max entropy
        text = "a b c d e f g h"
        entropy = calculate_shannon_entropy(text)
        assert entropy == pytest.approx(3.0, abs=0.01)

    def test_repeated_tokens_low_entropy(self):
        text = "hello hello hello hello"
        assert calculate_shannon_entropy(text) == 0.0

    def test_mixed_entropy(self):
        text = "the the the cat sat on the mat"
        entropy = calculate_shannon_entropy(text)
        assert entropy > 0
        assert entropy < 3.0


# =============================================================================
# Pydantic Model Tests
# =============================================================================


class TestPydanticModels:
    """Tests for simulation Pydantic models."""

    def test_intervention_creation(self):
        i = Intervention(variable="price", value=10.0, description="Set price to 10")
        assert i.variable == "price"
        assert i.value == 10.0

    def test_scenario_config_auto_id(self):
        config = ScenarioConfig(
            name="Test Scenario",
            interventions=[Intervention(variable="x", value=1.0)],
            baseline_dataset_id="ds-001",
        )
        assert config.id  # Auto-generated
        assert config.name == "Test Scenario"

    def test_simulation_result(self):
        r = SimulationResult(
            scenario_id="sc-001",
            session_id="sess-001",
            effect_estimate=0.42,
            confidence_interval=(0.1, 0.7),
            confidence=0.85,
            updated_at="2026-01-01T00:00:00",
        )
        assert r.effect_estimate == 0.42
        assert r.status == "completed"

    def test_simulation_comparison(self):
        r1 = SimulationResult(
            scenario_id="sc-001", session_id="s1",
            effect_estimate=0.5, confidence_interval=(0.1, 0.9),
            confidence=0.8, updated_at="2026-01-01",
        )
        r2 = SimulationResult(
            scenario_id="sc-002", session_id="s2",
            effect_estimate=0.3, confidence_interval=(0.0, 0.6),
            confidence=0.9, updated_at="2026-01-01",
        )
        comp = SimulationComparison(
            scenarios=[r1, r2],
            best_by_metric={"effect": "sc-001", "confidence": "sc-002"},
        )
        assert len(comp.scenarios) == 2
        assert comp.best_by_metric["effect"] == "sc-001"

    def test_enhanced_simulation_result(self):
        r = SimulationResult(
            scenario_id="sc-001", session_id="s1",
            effect_estimate=0.5, confidence_interval=(0.1, 0.9),
            confidence=0.8, updated_at="2026-01-01",
        )
        enhanced = EnhancedSimulationResult(
            result=r,
            reliability_score=0.75,
            agents_used=["causal_analyst", "guardian"],
        )
        assert enhanced.reliability_score == 0.75
        assert len(enhanced.agents_used) == 2

    def test_realism_level_enum(self):
        assert RealismLevel.EXCELLENT == "excellent"
        assert RealismLevel.SYNTHETIC == "synthetic"

    def test_data_richness_indicator(self):
        dri = DataRichnessIndicator(
            sample_size=1000,
            feature_count=10,
            treatment_balance=0.45,
            covariate_coverage=0.95,
            temporal_span_days=365,
            geographic_diversity=5,
            causal_identifiability=0.8,
        )
        assert dri.sample_size == 1000
        assert dri.geographic_diversity == 5


# =============================================================================
# SimulationService Tests
# =============================================================================


class TestSimulationService:
    """Tests for the SimulationService class."""

    def test_data_generators_registry(self):
        assert "scope3_emissions" in SimulationService.DATA_GENERATORS
        assert "supply_chain_resilience" in SimulationService.DATA_GENERATORS
        assert "pricing_optimization" in SimulationService.DATA_GENERATORS
        assert "renewable_energy_roi" in SimulationService.DATA_GENERATORS
        assert "shipping_carbon" in SimulationService.DATA_GENERATORS
        assert "customer_churn" in SimulationService.DATA_GENERATORS

    def test_all_generators_callable(self):
        for name, gen_func in SimulationService.DATA_GENERATORS.items():
            assert callable(gen_func), f"Generator {name} not callable"

    def test_get_simulation_status_not_found(self):
        service = SimulationService()
        assert service.get_simulation_status("nonexistent") is None

    @pytest.mark.asyncio
    async def test_compare_scenarios_empty_raises(self):
        service = SimulationService()
        with pytest.raises(ValueError, match="No simulation results found"):
            await service.compare_scenarios(["nonexistent-1", "nonexistent-2"])

    @pytest.mark.asyncio
    async def test_compare_scenarios_with_results(self):
        service = SimulationService()
        # Manually insert results
        r1 = SimulationResult(
            scenario_id="sc-1", session_id="s1",
            effect_estimate=0.5, confidence_interval=(0.1, 0.9),
            confidence=0.8, updated_at="2026-01-01",
            metrics={"refutations_passed": 2, "refutations_total": 3},
        )
        r2 = SimulationResult(
            scenario_id="sc-2", session_id="s2",
            effect_estimate=0.3, confidence_interval=(0.0, 0.6),
            confidence=0.9, updated_at="2026-01-01",
            metrics={"refutations_passed": 3, "refutations_total": 3},
        )
        service._running_simulations["sc-1"] = r1
        service._running_simulations["sc-2"] = r2

        comp = await service.compare_scenarios(["sc-1", "sc-2"])
        assert len(comp.scenarios) == 2
        assert comp.best_by_metric["effect_size"] == "sc-1"
        assert comp.best_by_metric["confidence"] == "sc-2"

    def test_get_simulation_status_found(self):
        service = SimulationService()
        r = SimulationResult(
            scenario_id="sc-1", session_id="s1",
            effect_estimate=0.5, confidence_interval=(0.1, 0.9),
            confidence=0.8, updated_at="2026-01-01",
        )
        service._running_simulations["sc-1"] = r
        result = service.get_simulation_status("sc-1")
        assert result is not None
        assert result.scenario_id == "sc-1"
