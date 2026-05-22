# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for src/services/router_retraining_service.py."""

import json
from pathlib import Path
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

    def test_apply_keyword_hints_to_router(self):
        service = RouterRetrainingService()
        hints = {
            "complicated": ["causality", "uplift_modeling", "propensity"],
            "complex": ["posterior_shift"],
        }

        result = service.apply_keyword_hints_to_router(
            hints,
            max_new_per_domain=3,
            max_indicators_per_domain=100,
        )

        assert result["applied_domains"] >= 1
        assert "Complicated" in result["applied_hints"]
        assert "causality" in result["applied_hints"]["Complicated"]

    def test_apply_keyword_hints_skips_unknown_domain(self):
        service = RouterRetrainingService()
        result = service.apply_keyword_hints_to_router(
            {"not_a_domain": ["foo", "bar"]}
        )

        assert result["applied_domains"] == 0
        assert result["skipped_domains"]["not_a_domain"] == "unknown_domain"

    def test_persist_and_load_keyword_hints(self, tmp_path: Path):
        hint_path = tmp_path / "router_hints.json"
        service = RouterRetrainingService(hint_store_path=hint_path)

        persist_result = service.persist_keyword_hints(
            {
                "complicated": ["causal_lift", "uplift_modeling"],
                "complex": ["posterior_shift"],
            }
        )
        assert persist_result["added_keywords"] >= 3
        assert hint_path.exists()

        loaded = service.load_persisted_hint_overrides()
        assert "complicated" in loaded
        assert "causal_lift" in loaded["complicated"]
        assert "complex" in loaded

        raw = json.loads(hint_path.read_text(encoding="utf-8"))
        assert "complicated" in raw

    def test_persist_keyword_hints_merges_without_duplicates(self, tmp_path: Path):
        hint_path = tmp_path / "router_hints.json"
        service = RouterRetrainingService(hint_store_path=hint_path)

        service.persist_keyword_hints({"complicated": ["causal_lift"]})
        service.persist_keyword_hints({"complicated": ["causal_lift", "instrumental"]})

        loaded = service.load_persisted_hint_overrides()
        assert loaded["complicated"].count("causal_lift") == 1
        assert "instrumental" in loaded["complicated"]

    def test_router_module_loads_persisted_hints(self, tmp_path: Path, monkeypatch):
        import importlib
        import src.services.router_retraining_service as retrain_mod
        import src.workflows.router as router_mod

        hint_path = tmp_path / "router_hints.json"
        unique_hint = "persisted_hint_unit_test_marker"
        hint_path.write_text(
            json.dumps({"complicated": [unique_hint]}),
            encoding="utf-8",
        )
        monkeypatch.setenv("CARF_ROUTER_HINTS_PATH", str(hint_path))
        retrain_mod._router_retraining_service = None

        reloaded = importlib.reload(router_mod)
        assert unique_hint in reloaded.DATA_STRUCTURE_HINTS["Complicated"]["indicators"]

    def test_get_persisted_hint_status_missing_file(self, tmp_path: Path):
        hint_path = tmp_path / "missing_router_hints.json"
        service = RouterRetrainingService(hint_store_path=hint_path)

        status = service.get_persisted_hint_status()
        assert status["exists"] is False
        assert status["domains"] == 0

    def test_maybe_auto_refresh_skips_when_insufficient_samples(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=self._make_overrides(3)):
            result = service.maybe_auto_refresh_router_hints(
                min_samples=10,
                min_new_overrides=2,
            )

        assert result["status"] == "skipped_insufficient_samples"

    def test_maybe_auto_refresh_runs_when_threshold_reached(self):
        service = RouterRetrainingService()
        with patch.object(service, "get_training_data", return_value=self._make_overrides(15)), patch.object(
            service,
            "retrain_keyword_hints",
            return_value={"complicated": ["causal_lift"]},
        ), patch.object(
            service,
            "apply_keyword_hints_to_router",
            return_value={"applied_domains": 1, "applied_hints": {"Complicated": ["causal_lift"]}},
        ), patch.object(
            service,
            "persist_keyword_hints",
            return_value={"path": "/tmp/x", "domains": 1, "added_keywords": 1},
        ):
            result = service.maybe_auto_refresh_router_hints(
                min_samples=10,
                min_new_overrides=5,
                top_k=3,
            )

        assert result["status"] == "auto_refreshed"
        assert result["last_auto_refresh_count"] == 15

    def test_maybe_auto_refresh_skips_when_not_enough_new_overrides(self):
        service = RouterRetrainingService()
        service._last_auto_refresh_count = 14
        with patch.object(service, "get_training_data", return_value=self._make_overrides(15)):
            result = service.maybe_auto_refresh_router_hints(
                min_samples=10,
                min_new_overrides=5,
            )

        assert result["status"] == "skipped_not_enough_new_overrides"
