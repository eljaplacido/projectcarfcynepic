"""
Tests for the explanations service.
"""

import pytest
from src.services.explanations import (
    ExplanationService,
    ExplanationRequest,
    ExplanationComponent,
    ExplanationResponse,
)


class TestExplanationService:
    """Tests for the ExplanationService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ExplanationService()

    @pytest.mark.asyncio
    async def test_explain_cynefin_domain(self):
        """Test explanation for Cynefin domain."""
        request = ExplanationRequest(
            component=ExplanationComponent.CYNEFIN_DOMAIN,
            element_id=None,
            context={"domain": "complex", "confidence": 0.85},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None
        assert result.summary is not None
        assert isinstance(result.key_points, list)
        assert result.reliability_score >= 0 and result.reliability_score <= 1

    @pytest.mark.asyncio
    async def test_explain_causal_effect(self):
        """Test explanation for causal effect."""
        request = ExplanationRequest(
            component=ExplanationComponent.CAUSAL_EFFECT,
            element_id=None,
            context={"effect": 0.42, "unit": "units", "pValue": 0.03},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_explain_bayesian_epistemic(self):
        """Test explanation for epistemic uncertainty."""
        request = ExplanationRequest(
            component=ExplanationComponent.BAYESIAN_EPISTEMIC,
            element_id=None,
            context={"value": 0.35},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_explain_guardian_policy(self):
        """Test explanation for guardian policy."""
        request = ExplanationRequest(
            component=ExplanationComponent.GUARDIAN_POLICY,
            element_id="budget_check",
            context={"policyName": "Budget Check", "status": "passed"},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_explain_cynefin_confidence(self):
        """Test explanation for Cynefin confidence."""
        request = ExplanationRequest(
            component=ExplanationComponent.CYNEFIN_CONFIDENCE,
            element_id=None,
            context={"confidence": 0.92},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_explain_cynefin_entropy(self):
        """Test explanation for Cynefin entropy."""
        request = ExplanationRequest(
            component=ExplanationComponent.CYNEFIN_ENTROPY,
            element_id=None,
            context={"entropy": 0.65},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_explain_causal_pvalue(self):
        """Test explanation for p-value."""
        request = ExplanationRequest(
            component=ExplanationComponent.CAUSAL_PVALUE,
            element_id=None,
            context={"pValue": 0.01},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert isinstance(result.related_concepts, list)

    @pytest.mark.asyncio
    async def test_explain_bayesian_posterior(self):
        """Test explanation for Bayesian posterior."""
        request = ExplanationRequest(
            component=ExplanationComponent.BAYESIAN_POSTERIOR,
            element_id=None,
            context={},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert isinstance(result.learn_more_links, list)

    @pytest.mark.asyncio
    async def test_explain_dag_node(self):
        """Test explanation for DAG node."""
        request = ExplanationRequest(
            component=ExplanationComponent.DAG_NODE,
            element_id="treatment_node",
            context={"node_type": "treatment"},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_explain_guardian_verdict(self):
        """Test explanation for Guardian verdict."""
        request = ExplanationRequest(
            component=ExplanationComponent.GUARDIAN_VERDICT,
            element_id="final_verdict",
            context={"verdict": "passed", "policies_checked": 5},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_explanation_includes_required_fields(self):
        """Test that explanations include all required fields."""
        request = ExplanationRequest(
            component=ExplanationComponent.CYNEFIN_DOMAIN,
            element_id=None,
            context={"domain": "complicated"},
        )
        result = await self.service.explain(request)

        assert result is not None
        assert result.component == ExplanationComponent.CYNEFIN_DOMAIN
        assert result.title is not None
        assert result.summary is not None
        assert result.key_points is not None
        assert result.implications is not None
        assert result.reliability is not None
        assert result.reliability_score is not None
        assert result.related_concepts is not None
        assert result.learn_more_links is not None

    @pytest.mark.asyncio
    async def test_explanation_detail_levels(self):
        """Test different detail levels for explanations."""
        for detail_level in ["brief", "standard", "detailed"]:
            request = ExplanationRequest(
                component=ExplanationComponent.CAUSAL_EFFECT,
                element_id=None,
                context={"effect": 0.25},
                detail_level=detail_level,
            )
            result = await self.service.explain(request)

            assert result is not None
            assert result.title is not None
