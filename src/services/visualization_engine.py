from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Optional

class VisualizationContext(str, Enum):
    """Business context for visualization adaptation"""
    SUSTAINABILITY = "sustainability"  # Scope 3, carbon
    FINANCIAL = "financial"            # Cost, ROI, profit
    OPERATIONAL = "operational"        # Supply chain, logistics
    RISK = "risk"                      # Resilience, failure
    GENERAL = "general"                # Default fallback

class KPITemplate(BaseModel):
    name: str
    unit: str
    trend: str # "up_good", "down_good", "neutral"
    description: Optional[str] = None

class ContextualVisualization(BaseModel):
    context: VisualizationContext
    chart_type: str  # line, bar, sankey, treemap, gauge, waterfall
    color_scheme: List[str]
    kpi_templates: List[KPITemplate]
    recommended_panels: List[str]
    
    # Textual guidance for the frontend
    title_template: str
    insight_prompt: str

class CynefinVizConfig(BaseModel):
    """Cynefin domain-specific visualization strategy."""
    domain: str  # clear, complicated, complex, chaotic, disorder
    primary_chart: str  # Main chart type for this domain
    secondary_charts: List[str]  # Additional chart types
    color_scheme: List[str]  # Domain-specific colors
    interaction_mode: str  # "checklist", "explore", "act_first", "triage"
    detail_level: str  # "summary", "detailed", "raw"
    recommended_panels: List[str]  # Frontend component names to show


CYNEFIN_VIZ_CONFIGS: Dict[str, CynefinVizConfig] = {
    "clear": CynefinVizConfig(
        domain="clear",
        primary_chart="bar",
        secondary_charts=["checklist"],
        color_scheme=["#10B981", "#059669", "#D1FAE5"],
        interaction_mode="checklist",
        detail_level="summary",
        recommended_panels=["ClearDomainView", "GuardianPanel"],
    ),
    "complicated": CynefinVizConfig(
        domain="complicated",
        primary_chart="dag",
        secondary_charts=["waterfall", "sensitivity"],
        color_scheme=["#3B82F6", "#1D4ED8", "#DBEAFE"],
        interaction_mode="explore",
        detail_level="detailed",
        recommended_panels=["CausalDAG", "ComplicatedDomainView", "SensitivityPlot", "InterventionSimulator"],
    ),
    "complex": CynefinVizConfig(
        domain="complex",
        primary_chart="area",
        secondary_charts=["gauge", "heatmap"],
        color_scheme=["#8B5CF6", "#6D28D9", "#EDE9FE"],
        interaction_mode="explore",
        detail_level="detailed",
        recommended_panels=["BayesianPanel", "ComplexDomainView"],
    ),
    "chaotic": CynefinVizConfig(
        domain="chaotic",
        primary_chart="timeline",
        secondary_charts=["alert_list"],
        color_scheme=["#EF4444", "#B91C1C", "#FEF2F2"],
        interaction_mode="act_first",
        detail_level="summary",
        recommended_panels=["ChaoticDomainView", "GuardianPanel"],
    ),
    "disorder": CynefinVizConfig(
        domain="disorder",
        primary_chart="radar",
        secondary_charts=["confidence_bar"],
        color_scheme=["#9CA3AF", "#6B7280", "#F3F4F6"],
        interaction_mode="triage",
        detail_level="summary",
        recommended_panels=["DisorderDomainView", "CynefinRouter"],
    ),
}


def get_cynefin_viz_config(domain_str: str) -> CynefinVizConfig:
    """Return domain-appropriate visualization config."""
    return CYNEFIN_VIZ_CONFIGS.get(
        domain_str.lower(),
        CYNEFIN_VIZ_CONFIGS["disorder"]  # fallback
    )


def get_visualization_config(context_str: str) -> ContextualVisualization:
    """Return context-appropriate visualization settings."""
    
    try:
        context = VisualizationContext(context_str.lower())
    except ValueError:
        context = VisualizationContext.GENERAL

    # Sustainability Configuration (Gold Standard)
    if context == VisualizationContext.SUSTAINABILITY:
        return ContextualVisualization(
            context=VisualizationContext.SUSTAINABILITY,
            chart_type="sankey",  # Emissions flow is best viewed as Sankey
            color_scheme=["#10B981", "#059669", "#047857", "#D1FAE5"],  # Emerald Green shades
            kpi_templates=[
                KPITemplate(name="Total Reduction", unit="tCO2e", trend="down_good", description="Total emissions reduced vs baseline"),
                KPITemplate(name="Supplier Coverage", unit="%", trend="up_good", description="Percentage of suppliers reporting"),
                KPITemplate(name="Carbon Intensity", unit="kg/$", trend="down_good", description="Emissions per dollar spend")
            ],
            recommended_panels=["CausalDAG", "EffectSummary", "SupplierMap"],
            title_template="Emissions Impact Analysis",
            insight_prompt="Analyze the carbon footprint reduction potential across the supply chain."
        )
    
    # Financial Configuration
    elif context == VisualizationContext.FINANCIAL:
        return ContextualVisualization(
            context=VisualizationContext.FINANCIAL,
            chart_type="waterfall",  # Profit/loss breakdown
            color_scheme=["#3B82F6", "#1D4ED8", "#6366F1", "#DBEAFE"],  # Blue/Indigo shades
            kpi_templates=[
                KPITemplate(name="ROI", unit="%", trend="up_good", description="Return on Investment"),
                KPITemplate(name="Payback Period", unit="months", trend="down_good", description="Time to break even"),
                KPITemplate(name="Net Savings", unit="$K", trend="up_good", description="Projected savings after costs")
            ],
            recommended_panels=["WaterfallChart", "ROITimeline", "CostBreakdown"],
            title_template="Financial Feasibility Report",
            insight_prompt="Evaluate the financial viability and return on investment."
        )

    # Operational Configuration
    elif context == VisualizationContext.OPERATIONAL:
        return ContextualVisualization(
            context=VisualizationContext.OPERATIONAL,
            chart_type="bar",
            color_scheme=["#F59E0B", "#B45309", "#FCD34D", "#FFFBEB"],  # Amber shades
            kpi_templates=[
                KPITemplate(name="Throughput", unit="u/h", trend="up_good"),
                KPITemplate(name="Lead Time", unit="days", trend="down_good"),
                KPITemplate(name="OEE", unit="%", trend="up_good")
            ],
            recommended_panels=["ProcessMap", "BottleneckAnalysis", "InventoryLevels"],
            title_template="Operational Efficiency Dashboard",
            insight_prompt="Assess operational bottlenecks and throughput efficiency."
        )

    # Risk Configuration
    elif context == VisualizationContext.RISK:
        return ContextualVisualization(
            context=VisualizationContext.RISK,
            chart_type="radar",
            color_scheme=["#EF4444", "#B91C1C", "#F87171", "#FEF2F2"],  # Red shades
            kpi_templates=[
                KPITemplate(name="Risk Score", unit="/100", trend="down_good"),
                KPITemplate(name="Compliance", unit="%", trend="up_good"),
                KPITemplate(name="Incident Rate", unit="%", trend="down_good")
            ],
            recommended_panels=["RiskHeatmap", "ComplianceTracker", "MitigationPlan"],
            title_template="Risk & Resilience Profile",
            insight_prompt="Identify and mitigate potential high-impact risks."
        )

    # Default / General
    else:
        return ContextualVisualization(
            context=VisualizationContext.GENERAL,
            chart_type="line",
            color_scheme=["#6B7280", "#374151", "#9CA3AF", "#F3F4F6"],  # Gray/Neutral
            kpi_templates=[
                KPITemplate(name="Impact Score", unit="/10", trend="up_good"),
                KPITemplate(name="Confidence", unit="%", trend="up_good"),
                KPITemplate(name="Data Quality", unit="%", trend="up_good")
            ],
            recommended_panels=["GeneralSummary", "Timeline"],
            title_template="Analysis Overview",
            insight_prompt="Provide a general overview of the system state."
        )
