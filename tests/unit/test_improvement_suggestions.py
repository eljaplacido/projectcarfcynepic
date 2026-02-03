"""Unit tests for the improvement suggestions service."""

import pytest
from src.services.improvement_suggestions import (
    improvement_service,
    ImprovementSuggestionService,
    ImprovementContext,
    Suggestion,
)


class TestImprovementSuggestionService:
    """Tests for ImprovementSuggestionService class."""

    def test_short_query_suggests_expansion(self):
        """Test that short queries get expansion suggestions."""
        context = ImprovementContext(
            current_query="sales",
            last_domain=None,
            last_confidence=None,
            available_columns=[]
        )

        suggestions = improvement_service.suggest(context)

        expand_suggestion = next(
            (s for s in suggestions if s.id == "expand_query"), None
        )
        assert expand_suggestion is not None
        assert expand_suggestion.type == "prompt_refinement"
        assert "specific" in expand_suggestion.text.lower()

    def test_causal_query_with_region_suggests_drill_down(self):
        """Test that causal queries with region column suggest drill-down."""
        context = ImprovementContext(
            current_query="What is the effect of treatment on outcome?",
            last_domain=None,
            last_confidence=None,
            available_columns=["treatment", "outcome", "region", "date"]
        )

        suggestions = improvement_service.suggest(context)

        region_suggestion = next(
            (s for s in suggestions if s.id == "subgroup_region"), None
        )
        assert region_suggestion is not None
        assert "region" in region_suggestion.text.lower()
        assert "region" in region_suggestion.action_payload.lower()

    def test_complex_low_confidence_suggests_bayesian(self):
        """Test that complex domain with low confidence suggests Bayesian."""
        context = ImprovementContext(
            current_query="What drives customer behavior?",
            last_domain="complex",
            last_confidence=0.5,
            available_columns=[]
        )

        suggestions = improvement_service.suggest(context)

        bayesian_suggestion = next(
            (s for s in suggestions if s.id == "switch_bayesian"), None
        )
        assert bayesian_suggestion is not None
        assert bayesian_suggestion.type == "methodology"
        assert "bayesian" in bayesian_suggestion.text.lower()

    def test_empty_query_suggests_starters(self):
        """Test that empty queries get starter suggestions."""
        context = ImprovementContext(
            current_query="",
            last_domain=None,
            last_confidence=None,
            available_columns=[]
        )

        suggestions = improvement_service.suggest(context)

        # Should have starter suggestions
        assert len(suggestions) >= 2

        causal_starter = next(
            (s for s in suggestions if s.id == "starter_causal"), None
        )
        trend_starter = next(
            (s for s in suggestions if s.id == "starter_trend"), None
        )

        assert causal_starter is not None
        assert trend_starter is not None
        assert "causal" in causal_starter.text.lower()
        assert "trend" in trend_starter.text.lower()

    def test_no_region_in_columns_no_drill_down(self):
        """Test that drill-down is not suggested without region column."""
        context = ImprovementContext(
            current_query="What is the effect of treatment on outcome?",
            last_domain=None,
            last_confidence=None,
            available_columns=["treatment", "outcome", "date"]  # No region
        )

        suggestions = improvement_service.suggest(context)

        region_suggestion = next(
            (s for s in suggestions if s.id == "subgroup_region"), None
        )
        assert region_suggestion is None

    def test_high_confidence_no_bayesian_suggestion(self):
        """Test that high confidence doesn't trigger Bayesian suggestion."""
        context = ImprovementContext(
            current_query="What drives customer behavior?",
            last_domain="complex",
            last_confidence=0.85,  # High confidence
            available_columns=[]
        )

        suggestions = improvement_service.suggest(context)

        bayesian_suggestion = next(
            (s for s in suggestions if s.id == "switch_bayesian"), None
        )
        assert bayesian_suggestion is None

    def test_suggestion_has_action_payload(self):
        """Test that suggestions include actionable payloads."""
        context = ImprovementContext(
            current_query="",
            last_domain=None,
            last_confidence=None,
            available_columns=[]
        )

        suggestions = improvement_service.suggest(context)

        for suggestion in suggestions:
            assert suggestion.action_payload is not None or suggestion.type == "methodology"

    def test_non_causal_query_no_region_drill_down(self):
        """Test that non-causal queries don't get region drill-down."""
        context = ImprovementContext(
            current_query="Show me the data summary",  # No 'cause' or 'effect'
            last_domain=None,
            last_confidence=None,
            available_columns=["region", "sales"]
        )

        suggestions = improvement_service.suggest(context)

        region_suggestion = next(
            (s for s in suggestions if s.id == "subgroup_region"), None
        )
        assert region_suggestion is None


class TestSuggestionModel:
    """Tests for Suggestion model."""

    def test_suggestion_creation(self):
        """Test basic Suggestion creation."""
        suggestion = Suggestion(
            id="test_id",
            type="prompt_refinement",
            text="Test suggestion",
            action_payload="Test action"
        )

        assert suggestion.id == "test_id"
        assert suggestion.type == "prompt_refinement"
        assert suggestion.text == "Test suggestion"
        assert suggestion.action_payload == "Test action"

    def test_suggestion_optional_payload(self):
        """Test that action_payload is optional."""
        suggestion = Suggestion(
            id="test_id",
            type="methodology",
            text="Test suggestion"
        )

        assert suggestion.action_payload is None


class TestImprovementContext:
    """Tests for ImprovementContext model."""

    def test_context_creation(self):
        """Test basic ImprovementContext creation."""
        context = ImprovementContext(
            current_query="test query",
            last_domain="complicated",
            last_confidence=0.85,
            available_columns=["col1", "col2"]
        )

        assert context.current_query == "test query"
        assert context.last_domain == "complicated"
        assert context.last_confidence == 0.85
        assert context.available_columns == ["col1", "col2"]

    def test_context_defaults(self):
        """Test ImprovementContext default values."""
        context = ImprovementContext(current_query="test")

        assert context.last_domain is None
        assert context.last_confidence is None
        assert context.available_columns == []
