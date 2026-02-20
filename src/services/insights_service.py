"""Insights Service for CARF.

Generates contextual, actionable insights for different user personas:
- Analysts: Technical insights about methodology and data quality
- Developers: System performance, debugging, and optimization insights
- Executives: Business impact, risk, and decision-making insights

This service analyzes the current analysis state and provides proactive
recommendations based on the Cynefin domain, confidence levels, and results.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.insights")


class InsightType(str, Enum):
    """Types of insights."""
    IMPROVEMENT = "improvement"      # How to improve the analysis
    WARNING = "warning"              # Potential issues to be aware of
    OPPORTUNITY = "opportunity"      # Opportunities for better insights
    RECOMMENDATION = "recommendation" # Recommended next steps
    EXPLANATION = "explanation"      # Explaining what happened
    VALIDATION = "validation"        # Validation of the results


class InsightPriority(str, Enum):
    """Priority levels for insights."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Insight(BaseModel):
    """A single actionable insight."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    type: InsightType
    priority: InsightPriority
    title: str
    description: str
    action: str | None = None  # Suggested action to take
    related_component: str | None = None  # Component this relates to
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InsightsResponse(BaseModel):
    """Response containing insights for a given persona."""
    persona: str
    insights: list[Insight]
    total_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisContext(BaseModel):
    """Context for generating insights."""
    domain: str | None = None
    domain_confidence: float | None = None
    domain_entropy: float | None = None
    has_causal_result: bool = False
    causal_effect: float | None = None
    refutation_pass_rate: float | None = None
    has_bayesian_result: bool = False
    epistemic_uncertainty: float | None = None
    aleatoric_uncertainty: float | None = None
    guardian_verdict: str | None = None
    policies_passed: int = 0
    policies_total: int = 0
    sample_size: int | None = None
    processing_time_ms: int | None = None


class ActionItem(BaseModel):
    """A concrete action a user can take, optionally with an API call."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    title: str
    description: str
    effort: str = Field(description="quick | medium | deep")
    category: str = Field(description="data_quality | model_improvement | risk_mitigation | exploration")
    api_endpoint: str | None = None
    api_payload: dict[str, Any] | None = None


class RoadmapItem(BaseModel):
    """A single step in a recommended analysis roadmap."""
    step: int
    title: str
    description: str
    depends_on: list[int] = Field(default_factory=list)
    estimated_time: str = ""


class EnhancedInsightsResponse(BaseModel):
    """Full enhanced response with insights, action items, and roadmap."""
    persona: str
    insights: list[Insight]
    action_items: list[ActionItem]
    roadmap: list[RoadmapItem]
    total_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class InsightsService:
    """Service for generating contextual insights."""

    def __init__(self):
        self._insight_templates = self._load_insight_templates()

    def _load_insight_templates(self) -> dict[str, list[dict]]:
        """Load insight templates for different scenarios."""
        return {
            "low_confidence": [
                {
                    "type": InsightType.WARNING,
                    "priority": InsightPriority.HIGH,
                    "title": "Low confidence in domain classification",
                    "description": "The system has low confidence ({confidence:.0%}) in classifying this query. Results should be interpreted with caution.",
                    "action": "Consider providing more context or specifying the analysis type explicitly.",
                    "related_component": "cynefin_router"
                }
            ],
            "high_entropy": [
                {
                    "type": InsightType.WARNING,
                    "priority": InsightPriority.MEDIUM,
                    "title": "High uncertainty in domain",
                    "description": "Domain entropy of {entropy:.0%} indicates the query spans multiple domains.",
                    "action": "Break down the query into more specific questions for better results.",
                    "related_component": "cynefin_router"
                }
            ],
            "refutation_failed": [
                {
                    "type": InsightType.WARNING,
                    "priority": InsightPriority.HIGH,
                    "title": "Refutation tests indicate concerns",
                    "description": "Only {pass_rate:.0%} of refutation tests passed. The causal effect estimate may not be robust.",
                    "action": "Review the causal graph and consider additional confounders.",
                    "related_component": "causal_analyst"
                }
            ],
            "strong_effect": [
                {
                    "type": InsightType.VALIDATION,
                    "priority": InsightPriority.MEDIUM,
                    "title": "Strong causal effect detected",
                    "description": "Effect size of {effect:.3f} is statistically significant with robust validation.",
                    "action": None,
                    "related_component": "causal_analyst"
                }
            ],
            "high_epistemic": [
                {
                    "type": InsightType.OPPORTUNITY,
                    "priority": InsightPriority.MEDIUM,
                    "title": "Reducible uncertainty detected",
                    "description": "Epistemic uncertainty ({epistemic:.0%}) can be reduced with additional data.",
                    "action": "Consider collecting more samples or running targeted experiments.",
                    "related_component": "bayesian_explorer"
                }
            ],
            "guardian_violation": [
                {
                    "type": InsightType.WARNING,
                    "priority": InsightPriority.HIGH,
                    "title": "Policy violation detected",
                    "description": "{violations} policy checks failed. Human review is required.",
                    "action": "Review the Guardian panel for specific violations.",
                    "related_component": "guardian"
                }
            ],
            "small_sample": [
                {
                    "type": InsightType.IMPROVEMENT,
                    "priority": InsightPriority.MEDIUM,
                    "title": "Limited sample size",
                    "description": "Analysis based on {sample_size} samples. Results may not generalize.",
                    "action": "Increase sample size for more robust conclusions.",
                    "related_component": "data_quality"
                }
            ],
        }

    def generate_analyst_insights(self, context: AnalysisContext) -> list[Insight]:
        """Generate insights for data analysts."""
        insights = []

        # Low confidence warning
        if context.domain_confidence and context.domain_confidence < 0.7:
            template = self._insight_templates["low_confidence"][0]
            insights.append(Insight(
                type=template["type"],
                priority=template["priority"],
                title=template["title"],
                description=template["description"].format(confidence=context.domain_confidence),
                action=template["action"],
                related_component=template["related_component"]
            ))

        # High entropy warning
        if context.domain_entropy and context.domain_entropy > 0.5:
            template = self._insight_templates["high_entropy"][0]
            insights.append(Insight(
                type=template["type"],
                priority=template["priority"],
                title=template["title"],
                description=template["description"].format(entropy=context.domain_entropy),
                action=template["action"],
                related_component=template["related_component"]
            ))

        # Refutation test insights
        if context.refutation_pass_rate is not None:
            if context.refutation_pass_rate < 0.8:
                template = self._insight_templates["refutation_failed"][0]
                insights.append(Insight(
                    type=template["type"],
                    priority=template["priority"],
                    title=template["title"],
                    description=template["description"].format(pass_rate=context.refutation_pass_rate),
                    action=template["action"],
                    related_component=template["related_component"]
                ))
            elif context.causal_effect and abs(context.causal_effect) > 0.1:
                template = self._insight_templates["strong_effect"][0]
                insights.append(Insight(
                    type=template["type"],
                    priority=template["priority"],
                    title=template["title"],
                    description=template["description"].format(effect=context.causal_effect),
                    action=template["action"],
                    related_component=template["related_component"]
                ))

        # Epistemic uncertainty insights
        if context.epistemic_uncertainty and context.epistemic_uncertainty > 0.3:
            template = self._insight_templates["high_epistemic"][0]
            insights.append(Insight(
                type=template["type"],
                priority=template["priority"],
                title=template["title"],
                description=template["description"].format(epistemic=context.epistemic_uncertainty),
                action=template["action"],
                related_component=template["related_component"]
            ))

        # Sample size insights
        if context.sample_size and context.sample_size < 500:
            template = self._insight_templates["small_sample"][0]
            insights.append(Insight(
                type=template["type"],
                priority=template["priority"],
                title=template["title"],
                description=template["description"].format(sample_size=context.sample_size),
                action=template["action"],
                related_component=template["related_component"]
            ))

        return insights

    def generate_developer_insights(self, context: AnalysisContext) -> list[Insight]:
        """Generate insights for developers."""
        insights = []

        # Processing time insights
        if context.processing_time_ms:
            if context.processing_time_ms > 5000:
                insights.append(Insight(
                    type=InsightType.WARNING,
                    priority=InsightPriority.MEDIUM,
                    title="Slow processing detected",
                    description=f"Query processing took {context.processing_time_ms}ms. Consider optimization.",
                    action="Check LLM call latency and cache hit rates.",
                    related_component="performance"
                ))
            elif context.processing_time_ms < 500:
                insights.append(Insight(
                    type=InsightType.VALIDATION,
                    priority=InsightPriority.LOW,
                    title="Fast processing",
                    description=f"Query processed in {context.processing_time_ms}ms. Good performance.",
                    action=None,
                    related_component="performance"
                ))

        # Domain routing insights
        if context.domain:
            insights.append(Insight(
                type=InsightType.EXPLANATION,
                priority=InsightPriority.LOW,
                title=f"Routed to {context.domain.capitalize()} domain",
                description=f"Query was classified as {context.domain} with {context.domain_confidence or 0:.0%} confidence.",
                action=None,
                related_component="cynefin_router"
            ))

        # Include analyst insights at lower priority
        analyst_insights = self.generate_analyst_insights(context)
        for insight in analyst_insights:
            insight.priority = InsightPriority.LOW
        insights.extend(analyst_insights)

        return insights

    def generate_executive_insights(self, context: AnalysisContext) -> list[Insight]:
        """Generate insights for executives."""
        insights = []

        # Overall analysis quality
        if context.domain_confidence and context.domain_confidence >= 0.85:
            insights.append(Insight(
                type=InsightType.VALIDATION,
                priority=InsightPriority.HIGH,
                title="High-confidence analysis",
                description="This analysis has high confidence and can support decision-making.",
                action=None,
                related_component="overall"
            ))
        elif context.domain_confidence and context.domain_confidence < 0.6:
            insights.append(Insight(
                type=InsightType.WARNING,
                priority=InsightPriority.HIGH,
                title="Exercise caution with results",
                description="Analysis confidence is below threshold. Consider human review before acting.",
                action="Request additional analysis or expert review.",
                related_component="overall"
            ))

        # Guardian policy insights
        if context.policies_total > 0:
            if context.policies_passed == context.policies_total:
                insights.append(Insight(
                    type=InsightType.VALIDATION,
                    priority=InsightPriority.HIGH,
                    title="All policy checks passed",
                    description=f"All {context.policies_total} governance policies have been satisfied.",
                    action=None,
                    related_component="guardian"
                ))
            else:
                violations = context.policies_total - context.policies_passed
                template = self._insight_templates["guardian_violation"][0]
                insights.append(Insight(
                    type=template["type"],
                    priority=template["priority"],
                    title=template["title"],
                    description=template["description"].format(violations=violations),
                    action=template["action"],
                    related_component=template["related_component"]
                ))

        # Business impact insight
        if context.has_causal_result and context.causal_effect:
            direction = "positive" if context.causal_effect > 0 else "negative"
            magnitude = "strong" if abs(context.causal_effect) > 0.3 else "moderate" if abs(context.causal_effect) > 0.1 else "weak"
            insights.append(Insight(
                type=InsightType.RECOMMENDATION,
                priority=InsightPriority.HIGH,
                title=f"{magnitude.capitalize()} {direction} effect identified",
                description=f"The intervention shows a {magnitude} {direction} causal effect ({context.causal_effect:.2%}).",
                action="Review the detailed analysis before making decisions.",
                related_component="causal_analyst"
            ))

        return insights

    def generate_action_items(
        self,
        context: AnalysisContext,
        persona: str = "analyst",
    ) -> list[ActionItem]:
        """Generate rule-based action items keyed on analysis state and persona."""
        items: list[ActionItem] = []

        # Common actions based on analysis state
        if context.refutation_pass_rate is not None and context.refutation_pass_rate < 0.8:
            items.append(ActionItem(
                title="Run sensitivity analysis",
                description="Refutation pass rate is low — run additional sensitivity tests to validate the causal estimate.",
                effort="medium",
                category="data_quality",
                api_endpoint="/query",
                api_payload={"query": "Run sensitivity analysis on the current causal estimate", "context": {"run_type": "sensitivity"}},
            ))

        if context.sample_size is not None and context.sample_size < 500:
            items.append(ActionItem(
                title="Upload more data",
                description=f"Current sample size ({context.sample_size}) is small. Upload additional data for more robust results.",
                effort="medium",
                category="data_quality",
            ))

        if context.processing_time_ms is not None and context.processing_time_ms > 5000:
            items.append(ActionItem(
                title="Train ChimeraOracle for fast predictions",
                description="Processing time is high. Train the Oracle on this scenario for sub-100ms predictions.",
                effort="deep",
                category="model_improvement",
                api_endpoint="/oracle/train",
            ))

        if context.epistemic_uncertainty is not None and context.epistemic_uncertainty > 0.3:
            items.append(ActionItem(
                title="Design safe-to-fail probe",
                description="High epistemic uncertainty detected. Design a targeted experiment to reduce uncertainty.",
                effort="deep",
                category="exploration",
                api_endpoint="/query",
                api_payload={"query": "Design safe-to-fail probes for the current hypothesis", "context": {"run_type": "probe_design"}},
            ))

        # Persona-specific actions
        if persona == "analyst":
            if context.has_causal_result and context.causal_effect is not None:
                items.append(ActionItem(
                    title="Review confounder coverage",
                    description="Verify that all relevant confounders are included in the causal model.",
                    effort="quick",
                    category="data_quality",
                ))

        elif persona == "developer":
            items.append(ActionItem(
                title="Check cache hit rates",
                description="Monitor cache performance and optimize if hit rate is below 70%.",
                effort="quick",
                category="model_improvement",
            ))
            if context.processing_time_ms and context.processing_time_ms > 3000:
                items.append(ActionItem(
                    title="Set up performance monitoring",
                    description="Configure latency alerts for queries exceeding 3 seconds.",
                    effort="medium",
                    category="model_improvement",
                ))

        elif persona == "executive":
            if context.has_causal_result and context.causal_effect:
                items.append(ActionItem(
                    title="Schedule impact assessment review",
                    description="The causal analysis has results. Schedule a review with stakeholders to assess business impact.",
                    effort="quick",
                    category="risk_mitigation",
                ))
            if context.domain_confidence and context.domain_confidence >= 0.85:
                items.append(ActionItem(
                    title="Approve pilot program",
                    description="High-confidence results support a controlled pilot implementation.",
                    effort="medium",
                    category="risk_mitigation",
                ))

        return items

    def generate_roadmap(
        self,
        context: AnalysisContext,
        persona: str = "analyst",
    ) -> list[RoadmapItem]:
        """Generate a sequenced analysis roadmap with dependency tracking."""
        roadmap: list[RoadmapItem] = []
        step = 1

        # Step 1: Data validation (always first)
        roadmap.append(RoadmapItem(
            step=step,
            title="Validate data quality",
            description="Run data quality checks on input data. Verify completeness, distributions, and outliers.",
            estimated_time="5 min",
        ))

        # Step 2: Domain classification review
        step += 1
        roadmap.append(RoadmapItem(
            step=step,
            title="Review domain classification",
            description=f"Current domain: {context.domain or 'unknown'} ({context.domain_confidence or 0:.0%} confidence). Verify this is correct.",
            depends_on=[1],
            estimated_time="2 min",
        ))

        # Step 3: Analysis (depends on domain)
        step += 1
        if context.domain in ("complicated", "Complicated"):
            roadmap.append(RoadmapItem(
                step=step,
                title="Run causal analysis",
                description="Execute the full causal pipeline: DAG discovery, effect estimation, and refutation tests.",
                depends_on=[2],
                estimated_time="15 min",
            ))
        elif context.domain in ("complex", "Complex"):
            roadmap.append(RoadmapItem(
                step=step,
                title="Run Bayesian exploration",
                description="Establish priors, design probes, and update beliefs through active inference.",
                depends_on=[2],
                estimated_time="10 min",
            ))
        else:
            roadmap.append(RoadmapItem(
                step=step,
                title="Run primary analysis",
                description="Execute the appropriate analysis for the classified domain.",
                depends_on=[2],
                estimated_time="10 min",
            ))

        # Step 4: Validation
        step += 1
        roadmap.append(RoadmapItem(
            step=step,
            title="Validate results",
            description="Review Guardian policy checks, refutation tests, and confidence levels.",
            depends_on=[3],
            estimated_time="5 min",
        ))

        # Step 5: Persona-specific final step
        step += 1
        if persona == "analyst":
            roadmap.append(RoadmapItem(
                step=step,
                title="Document findings and limitations",
                description="Create a summary of findings, limitations, and recommended follow-up analyses.",
                depends_on=[4],
                estimated_time="10 min",
            ))
        elif persona == "developer":
            roadmap.append(RoadmapItem(
                step=step,
                title="Optimize and deploy",
                description="Train ChimeraOracle on validated scenario, set up monitoring, and optimize caching.",
                depends_on=[4],
                estimated_time="30 min",
            ))
        elif persona == "executive":
            roadmap.append(RoadmapItem(
                step=step,
                title="Prepare decision brief",
                description="Synthesize findings into an executive brief with recommendations and risk assessment.",
                depends_on=[4],
                estimated_time="15 min",
            ))

        return roadmap

    def generate_enhanced_insights(
        self,
        context: AnalysisContext,
        persona: str = "analyst",
    ) -> EnhancedInsightsResponse:
        """Generate enhanced insights with action items and roadmap."""
        base = self.generate_insights(context, persona)
        action_items = self.generate_action_items(context, persona)
        roadmap = self.generate_roadmap(context, persona)

        return EnhancedInsightsResponse(
            persona=base.persona,
            insights=base.insights,
            action_items=action_items,
            roadmap=roadmap,
            total_count=base.total_count,
        )

    def generate_insights(
        self,
        context: AnalysisContext,
        persona: str = "analyst"
    ) -> InsightsResponse:
        """Generate insights for the specified persona."""
        if persona == "analyst":
            insights = self.generate_analyst_insights(context)
        elif persona == "developer":
            insights = self.generate_developer_insights(context)
        elif persona == "executive":
            insights = self.generate_executive_insights(context)
        else:
            insights = self.generate_analyst_insights(context)

        # Sort by priority
        priority_order = {InsightPriority.HIGH: 0, InsightPriority.MEDIUM: 1, InsightPriority.LOW: 2}
        insights.sort(key=lambda x: priority_order.get(x.priority, 99))

        return InsightsResponse(
            persona=persona,
            insights=insights,
            total_count=len(insights)
        )


# Singleton instance
_insights_service: InsightsService | None = None


def get_insights_service() -> InsightsService:
    """Get singleton InsightsService instance."""
    global _insights_service
    if _insights_service is None:
        _insights_service = InsightsService()
    return _insights_service
