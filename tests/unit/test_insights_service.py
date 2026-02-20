"""Tests for the InsightsService."""

import pytest
from src.services.insights_service import (
    InsightsService,
    AnalysisContext,
    InsightType,
    InsightPriority,
    ActionItem,
    RoadmapItem,
    EnhancedInsightsResponse,
    get_insights_service,
)


@pytest.fixture
def insights_service():
    """Create a fresh InsightsService for testing."""
    return InsightsService()


class TestInsightsService:
    """Tests for InsightsService class."""

    def test_get_insights_service_singleton(self):
        """Test that get_insights_service returns same instance."""
        service1 = get_insights_service()
        service2 = get_insights_service()
        assert service1 is service2

    def test_generate_analyst_insights_low_confidence(self, insights_service):
        """Test analyst insights for low confidence scenarios."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.5,  # Below 0.7 threshold
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include low confidence warning
        assert any(i.title == "Low confidence in domain classification" for i in insights)
        assert any(i.priority == InsightPriority.HIGH for i in insights)

    def test_generate_analyst_insights_high_entropy(self, insights_service):
        """Test analyst insights for high entropy scenarios."""
        context = AnalysisContext(
            domain="complex",
            domain_confidence=0.8,
            domain_entropy=0.7,  # Above 0.5 threshold
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include high entropy warning
        assert any(i.title == "High uncertainty in domain" for i in insights)

    def test_generate_analyst_insights_refutation_failed(self, insights_service):
        """Test analyst insights when refutation tests fail."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            refutation_pass_rate=0.6,  # Below 0.8 threshold
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include refutation warning
        assert any(i.title == "Refutation tests indicate concerns" for i in insights)

    def test_generate_analyst_insights_strong_effect(self, insights_service):
        """Test analyst insights for strong causal effects."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            refutation_pass_rate=0.9,  # Passing
            causal_effect=0.35,  # Strong effect
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include strong effect validation
        assert any(i.title == "Strong causal effect detected" for i in insights)
        assert any(i.type == InsightType.VALIDATION for i in insights)

    def test_generate_analyst_insights_high_epistemic(self, insights_service):
        """Test analyst insights for high epistemic uncertainty."""
        context = AnalysisContext(
            domain="complex",
            domain_confidence=0.8,
            epistemic_uncertainty=0.5,  # Above 0.3 threshold
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include opportunity for improvement
        assert any(i.title == "Reducible uncertainty detected" for i in insights)
        assert any(i.type == InsightType.OPPORTUNITY for i in insights)

    def test_generate_analyst_insights_small_sample(self, insights_service):
        """Test analyst insights for small sample sizes."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.8,
            sample_size=100,  # Below 500 threshold
        )
        insights = insights_service.generate_analyst_insights(context)

        # Should include sample size warning
        assert any(i.title == "Limited sample size" for i in insights)

    def test_generate_developer_insights(self, insights_service):
        """Test developer insights generation."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            processing_time_ms=6000,  # Slow - above 5000 threshold
        )
        insights = insights_service.generate_developer_insights(context)

        # Should include slow processing warning
        assert any(i.title == "Slow processing detected" for i in insights)
        # Should include routing explanation
        assert any("Routed to" in i.title for i in insights)

    def test_generate_developer_insights_fast_processing(self, insights_service):
        """Test developer insights for fast processing."""
        context = AnalysisContext(
            domain="clear",
            domain_confidence=0.95,
            processing_time_ms=200,  # Fast - below 500 threshold
        )
        insights = insights_service.generate_developer_insights(context)

        # Should include fast processing validation
        assert any(i.title == "Fast processing" for i in insights)

    def test_generate_executive_insights_high_confidence(self, insights_service):
        """Test executive insights for high confidence scenarios."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.9,  # Above 0.85 threshold
        )
        insights = insights_service.generate_executive_insights(context)

        # Should include high confidence validation
        assert any(i.title == "High-confidence analysis" for i in insights)

    def test_generate_executive_insights_low_confidence(self, insights_service):
        """Test executive insights for low confidence scenarios."""
        context = AnalysisContext(
            domain="complex",
            domain_confidence=0.5,  # Below 0.6 threshold
        )
        insights = insights_service.generate_executive_insights(context)

        # Should include caution warning
        assert any(i.title == "Exercise caution with results" for i in insights)

    def test_generate_executive_insights_policy_passed(self, insights_service):
        """Test executive insights when all policies pass."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            policies_passed=5,
            policies_total=5,
        )
        insights = insights_service.generate_executive_insights(context)

        # Should include policy compliance validation
        assert any(i.title == "All policy checks passed" for i in insights)

    def test_generate_executive_insights_policy_violated(self, insights_service):
        """Test executive insights when policies are violated."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            policies_passed=3,
            policies_total=5,  # 2 violations
        )
        insights = insights_service.generate_executive_insights(context)

        # Should include policy violation warning
        assert any(i.title == "Policy violation detected" for i in insights)

    def test_generate_executive_insights_causal_effect(self, insights_service):
        """Test executive insights for causal effects."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            has_causal_result=True,
            causal_effect=0.25,
        )
        insights = insights_service.generate_executive_insights(context)

        # Should include effect recommendation
        assert any("effect identified" in i.title.lower() for i in insights)

    def test_generate_insights_sorts_by_priority(self, insights_service):
        """Test that insights are sorted by priority."""
        context = AnalysisContext(
            domain="complex",
            domain_confidence=0.5,  # Low - HIGH priority
            domain_entropy=0.6,  # High - MEDIUM priority
            sample_size=100,  # Small - MEDIUM priority
        )
        response = insights_service.generate_insights(context, "analyst")

        # High priority should come first
        priorities = [i.priority for i in response.insights]
        assert priorities == sorted(priorities, key=lambda p: {
            InsightPriority.HIGH: 0,
            InsightPriority.MEDIUM: 1,
            InsightPriority.LOW: 2
        }.get(p, 99))

    def test_generate_insights_persona_routing(self, insights_service):
        """Test that different personas get different insights."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            processing_time_ms=6000,
        )

        analyst_response = insights_service.generate_insights(context, "analyst")
        developer_response = insights_service.generate_insights(context, "developer")
        executive_response = insights_service.generate_insights(context, "executive")

        # Developer should have processing time insight
        dev_titles = [i.title for i in developer_response.insights]
        assert any("processing" in t.lower() for t in dev_titles)

    def test_generate_insights_response_structure(self, insights_service):
        """Test the structure of InsightsResponse."""
        context = AnalysisContext(domain="clear", domain_confidence=0.95)
        response = insights_service.generate_insights(context, "analyst")

        assert response.persona == "analyst"
        assert isinstance(response.insights, list)
        assert response.total_count == len(response.insights)
        assert response.generated_at is not None


class TestActionItems:
    """Tests for action item generation."""

    def test_generate_action_items_low_refutation(self, insights_service):
        """Low refutation rate should generate sensitivity analysis action."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            refutation_pass_rate=0.6,
        )
        items = insights_service.generate_action_items(context, "analyst")
        assert any("sensitivity" in a.title.lower() for a in items)

    def test_generate_action_items_small_sample(self, insights_service):
        """Small sample should generate upload data action."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            sample_size=100,
        )
        items = insights_service.generate_action_items(context, "analyst")
        assert any("upload" in a.title.lower() or "data" in a.title.lower() for a in items)

    def test_generate_action_items_executive_impact(self, insights_service):
        """Executive persona should get impact assessment action."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            has_causal_result=True,
            causal_effect=0.25,
        )
        items = insights_service.generate_action_items(context, "executive")
        assert any("impact" in a.title.lower() or "review" in a.title.lower() for a in items)

    def test_generate_action_items_developer_perf(self, insights_service):
        """Developer persona should get Oracle training action on slow queries."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            processing_time_ms=6000,
        )
        items = insights_service.generate_action_items(context, "developer")
        assert any("oracle" in a.title.lower() or "monitor" in a.title.lower() for a in items)

    def test_action_items_empty_when_clean(self, insights_service):
        """Clean analysis should not produce false-positive actions."""
        context = AnalysisContext(
            domain="clear",
            domain_confidence=0.95,
            refutation_pass_rate=0.95,
            sample_size=1000,
        )
        items = insights_service.generate_action_items(context, "analyst")
        # Should have at most confounder review for causal results
        assert len(items) <= 1


class TestRoadmap:
    """Tests for roadmap generation."""

    def test_generate_roadmap_ordering(self, insights_service):
        """Steps should be sequential with correct dependencies."""
        context = AnalysisContext(domain="complicated", domain_confidence=0.85)
        roadmap = insights_service.generate_roadmap(context, "analyst")

        assert len(roadmap) >= 4
        # Steps must be increasing
        steps = [r.step for r in roadmap]
        assert steps == sorted(steps)
        # Step 1 should have no dependencies
        assert roadmap[0].depends_on == []
        # Step 2+ should depend on prior steps
        for item in roadmap[1:]:
            assert len(item.depends_on) > 0
            for dep in item.depends_on:
                assert dep < item.step


class TestEnhancedResponse:
    """Tests for full enhanced insights response."""

    def test_enhanced_response_structure(self, insights_service):
        """Enhanced response should have all three sections populated."""
        context = AnalysisContext(
            domain="complicated",
            domain_confidence=0.85,
            refutation_pass_rate=0.6,
            sample_size=200,
        )
        response = insights_service.generate_enhanced_insights(context, "analyst")

        assert isinstance(response, EnhancedInsightsResponse)
        assert response.persona == "analyst"
        assert len(response.insights) > 0
        assert len(response.action_items) > 0
        assert len(response.roadmap) > 0
        assert response.generated_at is not None
