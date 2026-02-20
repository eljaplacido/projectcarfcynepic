"""Tests for ExperienceBuffer service."""

import pytest
from src.services.experience_buffer import (
    ExperienceBuffer,
    ExperienceEntry,
    get_experience_buffer,
)


@pytest.fixture
def buffer():
    """Create a fresh ExperienceBuffer for testing."""
    return ExperienceBuffer(max_entries=100)


@pytest.fixture
def populated_buffer(buffer):
    """Buffer with 3 pre-loaded entries."""
    buffer.add(ExperienceEntry(
        query="What is the causal effect of marketing spend on revenue?",
        domain="complicated",
        domain_confidence=0.85,
        response_summary="Marketing spend has a positive causal effect.",
        causal_effect=0.35,
        guardian_verdict="approved",
        session_id="sess-1",
    ))
    buffer.add(ExperienceEntry(
        query="How does supply chain diversification affect disruption risk?",
        domain="complicated",
        domain_confidence=0.90,
        response_summary="Diversification reduces disruption frequency.",
        causal_effect=-2.5,
        guardian_verdict="approved",
        session_id="sess-2",
    ))
    buffer.add(ExperienceEntry(
        query="What strategy should we adopt for climate adaptation?",
        domain="complex",
        domain_confidence=0.75,
        response_summary="Active inference suggests safe-to-fail probes.",
        bayesian_posterior=0.08,
        guardian_verdict="approved",
        session_id="sess-3",
    ))
    return buffer


class TestExperienceBuffer:
    """Core Experience Buffer tests."""

    def test_add_and_find_similar(self, populated_buffer):
        """Add entries and find most similar."""
        results = populated_buffer.find_similar("marketing revenue impact")
        assert len(results) > 0
        # Marketing-related query should be most similar
        best_match, score = results[0]
        assert "marketing" in best_match.query.lower()
        assert score > 0

    def test_similarity_ranking(self, populated_buffer):
        """Most similar query should rank first."""
        results = populated_buffer.find_similar("supply chain risk")
        assert len(results) > 0
        # Supply chain query should rank highest
        best_match, best_score = results[0]
        assert "supply chain" in best_match.query.lower()
        # Scores should be descending
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_max_entries_eviction(self):
        """Buffer should respect max_entries limit."""
        buf = ExperienceBuffer(max_entries=3)
        for i in range(5):
            buf.add(ExperienceEntry(
                query=f"Query number {i}",
                domain="clear",
            ))
        assert buf.size == 3

    def test_context_augmentation(self, populated_buffer):
        """to_context_augmentation should return proper dict."""
        aug = populated_buffer.to_context_augmentation("marketing effect")
        assert "similar_past_queries" in aug
        assert "domain_patterns" in aug
        assert "buffer_size" in aug
        assert aug["buffer_size"] == 3

    def test_empty_buffer(self):
        """Operations on empty buffer should not error."""
        buf = ExperienceBuffer()
        assert buf.find_similar("test query") == []
        assert buf.get_domain_patterns() == {}
        aug = buf.to_context_augmentation("test")
        assert aug["buffer_size"] == 0

    def test_domain_patterns(self, populated_buffer):
        """Pattern aggregation should work correctly."""
        patterns = populated_buffer.get_domain_patterns()
        assert "complicated" in patterns
        assert "complex" in patterns
        assert patterns["complicated"]["count"] == 2
        assert patterns["complex"]["count"] == 1
        assert patterns["complicated"]["avg_confidence"] > 0

    def test_clear(self, populated_buffer):
        """Clear should reset buffer completely."""
        assert populated_buffer.size == 3
        populated_buffer.clear()
        assert populated_buffer.size == 0
        assert populated_buffer.find_similar("anything") == []

    def test_singleton(self):
        """get_experience_buffer returns same instance."""
        import src.services.experience_buffer as mod
        mod._experience_buffer = None

        b1 = get_experience_buffer()
        b2 = get_experience_buffer()
        assert b1 is b2

        mod._experience_buffer = None

    def test_min_similarity_threshold(self, populated_buffer):
        """Results below min_similarity should be filtered out."""
        results = populated_buffer.find_similar(
            "completely unrelated quantum physics topic",
            min_similarity=0.5,  # High threshold
        )
        # May return empty if no match is above 0.5
        for entry, score in results:
            assert score >= 0.5

    def test_top_k_limit(self, populated_buffer):
        """Should return at most top_k results."""
        results = populated_buffer.find_similar("query", top_k=1)
        assert len(results) <= 1

    def test_similarity_backend_property(self, buffer):
        """similarity_backend should return a valid backend name."""
        backend = buffer.similarity_backend
        assert backend in ("sentence-transformers", "tfidf")
