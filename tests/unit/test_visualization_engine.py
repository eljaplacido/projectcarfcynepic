"""Unit tests for the visualization engine service."""

import pytest
from src.services.visualization_engine import (
    get_visualization_config,
    VisualizationContext,
    ContextualVisualization,
    KPITemplate,
)


class TestGetVisualizationConfig:
    """Tests for get_visualization_config function."""

    def test_sustainability_context(self):
        """Test sustainability context returns correct configuration."""
        config = get_visualization_config("sustainability")

        assert config.context == VisualizationContext.SUSTAINABILITY
        assert config.chart_type == "sankey"
        assert "#10B981" in config.color_scheme  # Green color
        assert len(config.kpi_templates) >= 3
        assert "CausalDAG" in config.recommended_panels
        assert "Emissions" in config.title_template

    def test_financial_context(self):
        """Test financial context returns correct configuration."""
        config = get_visualization_config("financial")

        assert config.context == VisualizationContext.FINANCIAL
        assert config.chart_type == "waterfall"
        assert "#3B82F6" in config.color_scheme  # Blue color

        roi_kpi = next(k for k in config.kpi_templates if "ROI" in k.name)
        assert roi_kpi.trend == "up_good"
        assert roi_kpi.unit == "%"

    def test_operational_context(self):
        """Test operational context returns correct configuration."""
        config = get_visualization_config("operational")

        assert config.context == VisualizationContext.OPERATIONAL
        assert config.chart_type == "bar"
        assert "#F59E0B" in config.color_scheme  # Amber color

        throughput_kpi = next(k for k in config.kpi_templates if "Throughput" in k.name)
        assert throughput_kpi.trend == "up_good"

    def test_risk_context(self):
        """Test risk context returns correct configuration."""
        config = get_visualization_config("risk")

        assert config.context == VisualizationContext.RISK
        assert config.chart_type == "radar"
        assert "#EF4444" in config.color_scheme  # Red color

        risk_kpi = next(k for k in config.kpi_templates if "Risk" in k.name)
        assert risk_kpi.trend == "down_good"  # Lower risk is better

    def test_general_context(self):
        """Test general/fallback context returns default configuration."""
        config = get_visualization_config("general")

        assert config.context == VisualizationContext.GENERAL
        assert config.chart_type == "line"
        assert "#6B7280" in config.color_scheme  # Gray color

    def test_unknown_context_falls_back_to_general(self):
        """Test that unknown context falls back to general."""
        config = get_visualization_config("unknown_context")

        assert config.context == VisualizationContext.GENERAL
        assert config.chart_type == "line"

    def test_case_insensitive_context(self):
        """Test that context matching is case-insensitive."""
        config_upper = get_visualization_config("SUSTAINABILITY")
        config_lower = get_visualization_config("sustainability")
        config_mixed = get_visualization_config("Sustainability")

        assert config_upper.context == VisualizationContext.SUSTAINABILITY
        assert config_lower.context == VisualizationContext.SUSTAINABILITY
        assert config_mixed.context == VisualizationContext.SUSTAINABILITY

    def test_sustainability_kpi_trends(self):
        """Test that sustainability KPIs have correct trend directions."""
        config = get_visualization_config("sustainability")

        # Total Reduction should be down_good (lower emissions is better)
        reduction_kpi = next(k for k in config.kpi_templates if "Reduction" in k.name)
        assert reduction_kpi.trend == "down_good"

        # Coverage should be up_good (more coverage is better)
        coverage_kpi = next(k for k in config.kpi_templates if "Coverage" in k.name)
        assert coverage_kpi.trend == "up_good"

    def test_financial_kpi_trends(self):
        """Test that financial KPIs have correct trend directions."""
        config = get_visualization_config("financial")

        # Payback Period should be down_good (shorter is better)
        payback_kpi = next(k for k in config.kpi_templates if "Payback" in k.name)
        assert payback_kpi.trend == "down_good"

    def test_config_has_insight_prompt(self):
        """Test that all configs have insight prompts."""
        contexts = ["sustainability", "financial", "operational", "risk", "general"]

        for ctx in contexts:
            config = get_visualization_config(ctx)
            assert config.insight_prompt is not None
            assert len(config.insight_prompt) > 0

    def test_config_has_title_template(self):
        """Test that all configs have title templates."""
        contexts = ["sustainability", "financial", "operational", "risk", "general"]

        for ctx in contexts:
            config = get_visualization_config(ctx)
            assert config.title_template is not None
            assert len(config.title_template) > 0


class TestVisualizationContext:
    """Tests for VisualizationContext enum."""

    def test_all_contexts_defined(self):
        """Test that all expected contexts are defined."""
        expected = ["sustainability", "financial", "operational", "risk", "general"]

        for ctx in expected:
            assert VisualizationContext(ctx) is not None

    def test_context_values(self):
        """Test context enum values."""
        assert VisualizationContext.SUSTAINABILITY.value == "sustainability"
        assert VisualizationContext.FINANCIAL.value == "financial"
        assert VisualizationContext.OPERATIONAL.value == "operational"
        assert VisualizationContext.RISK.value == "risk"
        assert VisualizationContext.GENERAL.value == "general"


class TestKPITemplate:
    """Tests for KPITemplate model."""

    def test_kpi_template_creation(self):
        """Test basic KPITemplate creation."""
        kpi = KPITemplate(
            name="Test KPI",
            unit="units",
            trend="up_good",
            description="Test description"
        )

        assert kpi.name == "Test KPI"
        assert kpi.unit == "units"
        assert kpi.trend == "up_good"
        assert kpi.description == "Test description"

    def test_kpi_template_optional_description(self):
        """Test that description is optional."""
        kpi = KPITemplate(
            name="Test KPI",
            unit="%",
            trend="down_good"
        )

        assert kpi.description is None


class TestContextualVisualization:
    """Tests for ContextualVisualization model."""

    def test_contextual_visualization_creation(self):
        """Test basic ContextualVisualization creation."""
        viz = ContextualVisualization(
            context=VisualizationContext.SUSTAINABILITY,
            chart_type="sankey",
            color_scheme=["#10B981"],
            kpi_templates=[
                KPITemplate(name="Test", unit="%", trend="up_good")
            ],
            recommended_panels=["Panel1"],
            title_template="Test Title",
            insight_prompt="Test prompt"
        )

        assert viz.context == VisualizationContext.SUSTAINABILITY
        assert viz.chart_type == "sankey"
        assert len(viz.color_scheme) == 1
        assert len(viz.kpi_templates) == 1
        assert len(viz.recommended_panels) == 1

    def test_visualization_serialization(self):
        """Test that visualization can be serialized to dict."""
        config = get_visualization_config("sustainability")
        config_dict = config.model_dump()

        assert "context" in config_dict
        assert "chart_type" in config_dict
        assert "color_scheme" in config_dict
        assert "kpi_templates" in config_dict
