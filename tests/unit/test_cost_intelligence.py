"""Tests for CostIntelligenceService."""

import os
import pytest

os.environ["CARF_TEST_MODE"] = "1"


from src.services.cost_intelligence_service import CostIntelligenceService


@pytest.fixture
def service():
    return CostIntelligenceService()


class TestComputeLLMCost:
    def test_deepseek_cost(self, service):
        cost = service.compute_llm_cost(1_000_000, 1_000_000, "deepseek")
        assert cost == pytest.approx(0.42, abs=0.01)  # 0.14 + 0.28

    def test_openai_cost(self, service):
        cost = service.compute_llm_cost(1_000_000, 1_000_000, "openai")
        assert cost == pytest.approx(9.0, abs=0.01)  # 3.0 + 6.0

    def test_anthropic_cost(self, service):
        cost = service.compute_llm_cost(1_000_000, 1_000_000, "anthropic")
        assert cost == pytest.approx(18.0, abs=0.01)  # 3.0 + 15.0

    def test_zero_tokens(self, service):
        cost = service.compute_llm_cost(0, 0, "deepseek")
        assert cost == 0.0

    def test_unknown_provider_falls_back(self, service):
        cost = service.compute_llm_cost(1_000_000, 0, "unknown_provider")
        assert cost == pytest.approx(0.14, abs=0.01)  # falls back to deepseek

    def test_ollama_free(self, service):
        cost = service.compute_llm_cost(1_000_000, 1_000_000, "ollama")
        assert cost == 0.0


class TestComputeRiskExposure:
    def test_with_exposure(self, service):
        result = service.compute_risk_exposure(0.5, 100000)
        assert result == 50000.0

    def test_zero_exposure(self, service):
        result = service.compute_risk_exposure(0.9, 0)
        assert result == 0.0

    def test_zero_risk(self, service):
        result = service.compute_risk_exposure(0.0, 100000)
        assert result == 0.0


class TestComputeOpportunityCost:
    def test_basic(self, service):
        result = service.compute_opportunity_cost(3600)  # 1 hour
        assert result == 150.0  # default analyst rate

    def test_zero_time(self, service):
        result = service.compute_opportunity_cost(0)
        assert result == 0.0


class TestComputeFullBreakdown:
    def test_returns_breakdown(self, service):
        breakdown = service.compute_full_breakdown(
            session_id="test-123",
            input_tokens=500,
            output_tokens=200,
            provider="deepseek",
            compute_time_ms=1500,
        )
        assert breakdown.session_id == "test-123"
        assert breakdown.llm_tokens_used == 700
        assert breakdown.total_cost > 0
        assert len(breakdown.breakdown_items) == 4

    def test_stores_session_cost(self, service):
        service.compute_full_breakdown(session_id="store-test", input_tokens=100, output_tokens=50)
        result = service.get_session_cost("store-test")
        assert result is not None
        assert result.session_id == "store-test"

    def test_missing_session_returns_none(self, service):
        assert service.get_session_cost("nonexistent") is None


class TestAggregateCosts:
    def test_empty(self, service):
        agg = service.aggregate_costs()
        assert agg.total_sessions == 0
        assert agg.total_cost == 0

    def test_single_session(self, service):
        service.compute_full_breakdown(session_id="agg-1", input_tokens=1000, output_tokens=500, provider="deepseek")
        agg = service.aggregate_costs()
        assert agg.total_sessions == 1
        assert agg.total_cost > 0

    def test_multiple_sessions(self, service):
        service.compute_full_breakdown(session_id="agg-a", input_tokens=1000, output_tokens=500)
        service.compute_full_breakdown(session_id="agg-b", input_tokens=2000, output_tokens=1000)
        agg = service.aggregate_costs()
        assert agg.total_sessions == 2
        assert agg.total_tokens == 4500


class TestROIMetrics:
    def test_basic_roi(self, service):
        service.compute_full_breakdown(session_id="roi-1", input_tokens=500, output_tokens=200)
        roi = service.get_roi_metrics()
        assert roi.ai_analysis_cost >= 0
        assert roi.roi_percentage >= 0
        assert roi.insights_generated == 1


class TestPricing:
    def test_get_pricing(self, service):
        pricing = service.get_pricing()
        assert "deepseek" in pricing
        assert "openai" in pricing

    def test_update_pricing(self, service):
        service.update_pricing("deepseek", 1.0, 2.0)
        pricing = service.get_pricing()
        assert pricing["deepseek"]["input"] == 1.0
        assert pricing["deepseek"]["output"] == 2.0
