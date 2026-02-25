# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for src/services/router_retraining_service.py."""

from unittest.mock import patch

from src.services.router_retraining_service import RouterRetrainingService


class TestRouterRetrainingService:
    """Tests for RouterRetrainingService."""

    def _make_overrides(self, n: int = 15) -> list[dict]:
        """Create mock domain override records."""
        domains = ["complicated", "complex", "clear", "chaotic"]
        queries = [
            "What is the causal effect of discount on churn",
            "How uncertain is our market adoption rate",
            "Look up the current stock level for product X",
            "Emergency shutdown of production system required",
            "Estimate the impact of supplier change on costs",
            "Update our belief on conversion rate",
            "What is the current exchange rate",
            "System experiencing cascading failures",
            "Analyze supplier sustainability programs impact",
            "Model uncertainty in new product adoption",
            "List all products in Electronics category",
            "Critical supplier failure detected",
            "Impact of price changes on sales volume",
            "Forecast demand using Bayesian inference",
            "Show me the invoice for order 12345",
        ]
        overrides = []
        for i in range(n):
            overrides.append({
                "feedback_id": f"fb-{i:04d}",
                "session_id": f"sess-{i:04d}",
                "original_domain": "Disorder",
                "correct_domain": domains[i % len(domains)],
                "query": queries[i % len(queries)],
                "timestamp": f"2026-02-{10+i}T12:00:00Z",
            })
        return overrides

    def test_should_retrain_with_enough_data(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=self._make_overrides(15)):
            assert service.should_retrain(min_samples=10) is True

    def test_should_not_retrain_with_insufficient_data(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=self._make_overrides(3)):
            assert service.should_retrain(min_samples=10) is False

    def test_should_retrain_empty(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=[]):
            assert service.should_retrain(min_samples=1) is False

    def test_retrain_keyword_hints_extracts_terms(self):
        service = RouterRetrainingService()
        overrides = self._make_overrides(15)
        with patch.object(service, "get_training_data", return_value=overrides):
            hints = service.retrain_keyword_hints()

        assert isinstance(hints, dict)
        # Should have at least some domains
        assert len(hints) > 0
        # Each domain should have keyword lists
        for _domain, keywords in hints.items():
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_retrain_keyword_hints_empty(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=[]):
            hints = service.retrain_keyword_hints()

        assert hints == {}

    def test_retrain_keyword_hints_filters_stop_words(self):
        service = RouterRetrainingService()
        overrides = [
            {
                "correct_domain": "complicated",
                "query": "the causal effect of discount on churn rate",
            },
            {
                "correct_domain": "complicated",
                "query": "causal impact of pricing on revenue growth",
            },
        ]
        with patch.object(service, "get_training_data", return_value=overrides):
            hints = service.retrain_keyword_hints()

        if "complicated" in hints:
            # "the", "of", "on" should be filtered out
            assert "the" not in hints["complicated"]
            assert "of" not in hints["complicated"]
            # "causal" should appear
            assert "causal" in hints["complicated"]
