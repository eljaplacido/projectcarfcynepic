"""Tests for CynefinRouter._apply_causal_language_boost()."""

import pytest

from src.core.state import CynefinDomain
from src.workflows.router import CynefinRouter, DomainClassification


@pytest.fixture
def router():
    """Create a router instance (LLM model not needed for boost tests)."""
    r = CynefinRouter.__new__(CynefinRouter)
    r.config = None  # Not needed for this method
    return r


def _make_classification(domain: CynefinDomain, confidence: float = 0.78) -> DomainClassification:
    return DomainClassification(
        domain=domain,
        confidence=confidence,
        reasoning="LLM classification",
        key_indicators=["test"],
    )


class TestCausalLanguageBoost:
    """Tests for the causal language boost heuristic."""

    @pytest.mark.parametrize("query", [
        "What is the causal effect of marketing spend on customer acquisition?",
        "Determine the impact of the new pricing strategy on revenue",
        "What is the causal relationship between employee training hours and productivity?",
    ])
    def test_misclassified_queries_get_boosted(self, router, query):
        """Queries with explicit causal language should be boosted Complex → Complicated."""
        classification = _make_classification(CynefinDomain.COMPLEX, 0.78)
        result = router._apply_causal_language_boost(query, classification)
        assert result.domain == CynefinDomain.COMPLICATED
        assert result.confidence >= 0.85
        assert "causal_language_boost" in result.key_indicators

    @pytest.mark.parametrize("query", [
        "How uncertain are we about the long-term ROI of our solar panel investment?",
        "What probes should we design to understand grid frequency stability?",
        "Given the recent market crash, how uncertain are we about recovery?",
    ])
    def test_complex_queries_without_causal_language_stay_complex(self, router, query):
        """Complex queries without causal phrases should not be boosted."""
        classification = _make_classification(CynefinDomain.COMPLEX, 0.80)
        result = router._apply_causal_language_boost(query, classification)
        assert result.domain == CynefinDomain.COMPLEX

    @pytest.mark.parametrize("domain", [
        CynefinDomain.CLEAR,
        CynefinDomain.COMPLICATED,
        CynefinDomain.CHAOTIC,
        CynefinDomain.DISORDER,
    ])
    def test_non_complex_domains_unaffected(self, router, domain):
        """Non-Complex domains should never be affected by the boost."""
        query = "What is the causal effect of X on Y?"
        classification = _make_classification(domain, 0.90)
        result = router._apply_causal_language_boost(query, classification)
        assert result.domain == domain

    def test_boost_preserves_original_indicators(self, router):
        """Boost should append indicator, not replace originals."""
        classification = DomainClassification(
            domain=CynefinDomain.COMPLEX,
            confidence=0.75,
            reasoning="Original reasoning",
            key_indicators=["original_indicator"],
        )
        result = router._apply_causal_language_boost(
            "What is the causal effect of training on productivity?",
            classification,
        )
        assert "original_indicator" in result.key_indicators
        assert "causal_language_boost" in result.key_indicators

    def test_boost_sets_minimum_confidence(self, router):
        """Boost should ensure confidence is at least 0.85."""
        classification = _make_classification(CynefinDomain.COMPLEX, 0.60)
        result = router._apply_causal_language_boost(
            "What is the causal effect of X on Y?",
            classification,
        )
        assert result.confidence >= 0.85
