"""LLM-Powered Explanation Service for CARF.

Provides contextual explanations for all CARF components:
- Cynefin domain classification
- Causal analysis results
- Bayesian inference results
- Guardian policy decisions
- DAG nodes and edges
"""

import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.llm import get_chat_model

logger = logging.getLogger("carf.explanations")


class ExplanationComponent(str, Enum):
    """Components that can be explained."""

    CYNEFIN_DOMAIN = "cynefin_domain"
    CYNEFIN_CONFIDENCE = "cynefin_confidence"
    CYNEFIN_ENTROPY = "cynefin_entropy"
    CYNEFIN_SOLVER = "cynefin_solver"
    CAUSAL_EFFECT = "causal_effect"
    CAUSAL_PVALUE = "causal_pvalue"
    CAUSAL_CI = "causal_ci"
    CAUSAL_REFUTATION = "causal_refutation"
    CAUSAL_CONFOUNDER = "causal_confounder"
    BAYESIAN_POSTERIOR = "bayesian_posterior"
    BAYESIAN_EPISTEMIC = "bayesian_epistemic"
    BAYESIAN_ALEATORIC = "bayesian_aleatoric"
    BAYESIAN_PROBE = "bayesian_probe"
    GUARDIAN_POLICY = "guardian_policy"
    GUARDIAN_VERDICT = "guardian_verdict"
    DAG_NODE = "dag_node"
    DAG_EDGE = "dag_edge"
    DAG_PATH = "dag_path"


class ExplanationRequest(BaseModel):
    """Request for component explanation."""

    component: ExplanationComponent = Field(..., description="Component to explain")
    element_id: str | None = Field(None, description="Specific element ID")
    context: dict[str, Any] | None = Field(None, description="Additional context")
    detail_level: str = Field("standard", description="brief, standard, or detailed")


class ExplanationResponse(BaseModel):
    """Response with LLM-generated explanation."""

    component: ExplanationComponent
    element_id: str | None
    title: str
    summary: str
    key_points: list[str]
    implications: str
    reliability: str
    reliability_score: float
    related_concepts: list[str]
    learn_more_links: list[str]


# Pre-defined explanation templates for demo mode
DEMO_EXPLANATIONS: dict[ExplanationComponent, dict[str, Any]] = {
    ExplanationComponent.CYNEFIN_DOMAIN: {
        "title": "Cynefin Domain Classification",
        "summary": "The Cynefin framework classifies problems into five domains based on the relationship between cause and effect.",
        "key_points": [
            "Clear: Obvious cause-effect, best practices apply",
            "Complicated: Requires expert analysis to understand",
            "Complex: Cause-effect only visible in hindsight",
            "Chaotic: No clear cause-effect, act first",
            "Disorder: Cannot determine which domain applies",
        ],
        "implications": "The domain determines which analytical approach CARF uses.",
        "reliability": "Classification based on query entropy and pattern matching",
        "reliability_score": 0.85,
        "related_concepts": ["Decision theory", "Systems thinking", "Sense-making"],
        "learn_more_links": ["https://en.wikipedia.org/wiki/Cynefin_framework"],
    },
    ExplanationComponent.CAUSAL_EFFECT: {
        "title": "Causal Effect Estimate",
        "summary": "The estimated causal effect represents the expected change in outcome when treatment is applied, controlling for confounders.",
        "key_points": [
            "Effect size indicates magnitude and direction of impact",
            "Negative values mean treatment reduces outcome",
            "Positive values mean treatment increases outcome",
            "Effect is measured in outcome units",
        ],
        "implications": "Use this to predict the impact of interventions.",
        "reliability": "Based on statistical estimation with confounder control",
        "reliability_score": 0.78,
        "related_concepts": ["Average Treatment Effect", "DoWhy", "Backdoor criterion"],
        "learn_more_links": ["https://www.pywhy.org/dowhy/"],
    },
    ExplanationComponent.CAUSAL_PVALUE: {
        "title": "Statistical Significance (p-value)",
        "summary": "The p-value indicates the probability of observing this effect by chance if there were no true causal relationship.",
        "key_points": [
            "p < 0.05 typically considered significant",
            "Lower p-value = stronger evidence against null",
            "Does not measure effect size or practical importance",
            "Should be combined with confidence intervals",
        ],
        "implications": "Low p-value supports the causal claim but doesn't prove it.",
        "reliability": "Standard statistical measure",
        "reliability_score": 0.90,
        "related_concepts": ["Hypothesis testing", "Type I error", "Statistical power"],
        "learn_more_links": ["https://en.wikipedia.org/wiki/P-value"],
    },
    ExplanationComponent.CAUSAL_REFUTATION: {
        "title": "Refutation Test",
        "summary": "Refutation tests challenge the causal estimate by checking its robustness under various conditions.",
        "key_points": [
            "Placebo test: Uses fake treatment to check for spurious effects",
            "Random confounder: Adds random variables to test stability",
            "Data subset: Tests if effect holds across data splits",
            "Sensitivity: Checks impact of unobserved confounders",
        ],
        "implications": "More passed tests = more confidence in the causal claim.",
        "reliability": "Industry-standard validation approach",
        "reliability_score": 0.82,
        "related_concepts": ["Sensitivity analysis", "Robustness checks", "DoWhy refuters"],
        "learn_more_links": ["https://www.pywhy.org/dowhy/"],
    },
    ExplanationComponent.BAYESIAN_EPISTEMIC: {
        "title": "Epistemic Uncertainty",
        "summary": "Epistemic uncertainty reflects our lack of knowledge - it can be reduced by collecting more data or better understanding the system.",
        "key_points": [
            "Reducible with more information",
            "High epistemic = we need more data",
            "Represents model uncertainty",
            "Drives probe recommendations",
        ],
        "implications": "High epistemic uncertainty suggests collecting more data before acting.",
        "reliability": "Quantified through Bayesian inference",
        "reliability_score": 0.75,
        "related_concepts": ["Bayesian inference", "Information gain", "Active learning"],
        "learn_more_links": ["https://www.pymc.io/"],
    },
    ExplanationComponent.BAYESIAN_ALEATORIC: {
        "title": "Aleatoric Uncertainty",
        "summary": "Aleatoric uncertainty represents inherent randomness in the system - it cannot be reduced even with more data.",
        "key_points": [
            "Irreducible - fundamental to the process",
            "Represents natural variation",
            "Examples: market fluctuations, human behavior",
            "Must be accounted for in decision-making",
        ],
        "implications": "Accept this uncertainty and build robust decisions around it.",
        "reliability": "Estimated from data variance",
        "reliability_score": 0.80,
        "related_concepts": ["Stochastic processes", "Risk management", "Uncertainty quantification"],
        "learn_more_links": ["https://en.wikipedia.org/wiki/Uncertainty_quantification"],
    },
    ExplanationComponent.GUARDIAN_POLICY: {
        "title": "Guardian Policy Check",
        "summary": "Guardian policies are rules that must be satisfied before CARF recommends an action.",
        "key_points": [
            "Policies enforce organizational constraints",
            "Include budget limits, confidence thresholds, compliance rules",
            "Violations trigger human review",
            "Versioned for audit trail",
        ],
        "implications": "Policy violations require human approval or action modification.",
        "reliability": "Rule-based evaluation",
        "reliability_score": 0.95,
        "related_concepts": ["OPA policies", "Governance", "Risk management"],
        "learn_more_links": ["https://www.openpolicyagent.org/"],
    },
    ExplanationComponent.GUARDIAN_VERDICT: {
        "title": "Guardian Verdict",
        "summary": "The overall Guardian decision on whether the proposed action is safe to execute.",
        "key_points": [
            "Approved: All policies passed, safe to act",
            "Rejected: Critical policy violations",
            "Requires Human: Needs human review and approval",
        ],
        "implications": "Respect Guardian decisions to maintain safe AI operations.",
        "reliability": "Aggregate of all policy checks",
        "reliability_score": 0.92,
        "related_concepts": ["Human-in-the-loop", "AI safety", "Governance"],
        "learn_more_links": [],
    },
    ExplanationComponent.DAG_NODE: {
        "title": "Causal DAG Node",
        "summary": "A node in the causal graph represents a variable in the system.",
        "key_points": [
            "Treatment nodes: Variables we can intervene on",
            "Outcome nodes: Variables we want to affect",
            "Confounders: Variables affecting both treatment and outcome",
            "Mediators: Variables on the causal path",
        ],
        "implications": "Understanding node roles helps design better interventions.",
        "reliability": "Based on domain knowledge and data analysis",
        "reliability_score": 0.70,
        "related_concepts": ["Causal graphs", "DAG", "Structural causal models"],
        "learn_more_links": ["https://en.wikipedia.org/wiki/Causal_graph"],
    },
    ExplanationComponent.DAG_EDGE: {
        "title": "Causal DAG Edge",
        "summary": "An edge in the causal graph represents a direct causal relationship between variables.",
        "key_points": [
            "Direction indicates causation flow",
            "Effect size shows strength of relationship",
            "Validated edges passed statistical tests",
            "Edges form paths from treatment to outcome",
        ],
        "implications": "Edge effects compound along causal paths.",
        "reliability": "Estimated from data with statistical validation",
        "reliability_score": 0.75,
        "related_concepts": ["Path coefficients", "Mediation", "Total effects"],
        "learn_more_links": [],
    },
}


class ExplanationService:
    """Service for generating component explanations."""

    def __init__(self):
        self._demo_mode = not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY")
        if self._demo_mode:
            logger.info("ExplanationService running in demo mode (no API key)")

    async def explain(self, request: ExplanationRequest) -> ExplanationResponse:
        """Generate explanation for a component.

        Args:
            request: Explanation request with component and context

        Returns:
            ExplanationResponse with LLM-generated content
        """
        if self._demo_mode:
            return self._get_demo_explanation(request)

        return await self._get_llm_explanation(request)

    def _get_demo_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        """Get pre-defined explanation for demo mode."""
        template = DEMO_EXPLANATIONS.get(request.component, {
            "title": f"Explanation: {request.component.value}",
            "summary": "This component is part of the CARF analysis pipeline.",
            "key_points": ["Component contributes to the overall analysis"],
            "implications": "Consider the component's role in the full context.",
            "reliability": "Demo mode - limited explanation",
            "reliability_score": 0.5,
            "related_concepts": [],
            "learn_more_links": [],
        })

        # Customize with context if available
        if request.context:
            if "value" in request.context:
                template["summary"] = f"{template['summary']} Current value: {request.context['value']}"

        return ExplanationResponse(
            component=request.component,
            element_id=request.element_id,
            **template,
        )

    async def _get_llm_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        """Get LLM-generated explanation."""
        llm = get_chat_model(temperature=0.3, purpose="explanation")

        prompt = self._build_explanation_prompt(request)

        try:
            response = await llm.ainvoke([
                {"role": "system", "content": """You are an expert at explaining complex analytical concepts
in clear, accessible language. Provide explanations that are:
- Accurate and technically correct
- Easy to understand for non-experts
- Actionable with clear implications
- Connected to related concepts

Format your response as JSON with these fields:
title, summary, key_points (array), implications, reliability, reliability_score (0-1),
related_concepts (array), learn_more_links (array)"""},
                {"role": "user", "content": prompt},
            ])

            import json
            data = json.loads(response.content)

            return ExplanationResponse(
                component=request.component,
                element_id=request.element_id,
                **data,
            )

        except Exception as e:
            logger.error(f"LLM explanation failed: {e}")
            return self._get_demo_explanation(request)

    def _build_explanation_prompt(self, request: ExplanationRequest) -> str:
        """Build prompt for LLM explanation."""
        component_descriptions = {
            ExplanationComponent.CYNEFIN_DOMAIN: "Cynefin framework domain classification",
            ExplanationComponent.CAUSAL_EFFECT: "causal effect estimate from DoWhy analysis",
            ExplanationComponent.CAUSAL_PVALUE: "statistical p-value in causal inference",
            ExplanationComponent.CAUSAL_REFUTATION: "causal refutation test result",
            ExplanationComponent.BAYESIAN_EPISTEMIC: "epistemic uncertainty in Bayesian analysis",
            ExplanationComponent.BAYESIAN_ALEATORIC: "aleatoric uncertainty in Bayesian analysis",
            ExplanationComponent.GUARDIAN_POLICY: "Guardian policy check result",
            ExplanationComponent.GUARDIAN_VERDICT: "Guardian overall verdict",
            ExplanationComponent.DAG_NODE: "node in a causal DAG",
            ExplanationComponent.DAG_EDGE: "edge in a causal DAG",
        }

        component_desc = component_descriptions.get(
            request.component,
            request.component.value
        )

        context_str = ""
        if request.context:
            context_str = f"\n\nContext: {request.context}"

        detail_instructions = {
            "brief": "Keep explanation very concise (2-3 sentences).",
            "standard": "Provide a balanced explanation with key details.",
            "detailed": "Provide comprehensive explanation with examples.",
        }

        return f"""Explain: {component_desc}
{context_str}

Detail level: {detail_instructions.get(request.detail_level, detail_instructions['standard'])}

Provide explanation suitable for a business analyst or data scientist who may not be an expert in causal inference."""


# Singleton instance
_explanation_service: ExplanationService | None = None


def get_explanation_service() -> ExplanationService:
    """Get singleton ExplanationService instance."""
    global _explanation_service
    if _explanation_service is None:
        _explanation_service = ExplanationService()
    return _explanation_service
