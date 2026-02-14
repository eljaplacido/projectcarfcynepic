"""Unit tests for Cynefin visualization config."""

import pytest
from src.services.visualization_engine import (
    get_cynefin_viz_config,
    CynefinVizConfig,
    CYNEFIN_VIZ_CONFIGS,
)


class TestCynefinVizConfig:
    """Tests for get_cynefin_viz_config function."""

    @pytest.mark.parametrize("domain", ["clear", "complicated", "complex", "chaotic", "disorder"])
    def test_all_domains_return_valid_config(self, domain: str):
        config = get_cynefin_viz_config(domain)
        assert isinstance(config, CynefinVizConfig)
        assert config.domain == domain
        assert len(config.color_scheme) >= 3
        assert len(config.recommended_panels) >= 1
        assert config.interaction_mode in ("checklist", "explore", "act_first", "triage")
        assert config.detail_level in ("summary", "detailed", "raw")

    def test_unknown_domain_falls_back_to_disorder(self):
        config = get_cynefin_viz_config("nonexistent")
        assert config.domain == "disorder"

    def test_case_insensitive(self):
        upper = get_cynefin_viz_config("COMPLICATED")
        lower = get_cynefin_viz_config("complicated")
        assert upper.domain == lower.domain

    def test_complicated_recommends_causal_panels(self):
        config = get_cynefin_viz_config("complicated")
        assert "CausalDAG" in config.recommended_panels
        assert config.primary_chart == "dag"

    def test_complex_recommends_bayesian_panels(self):
        config = get_cynefin_viz_config("complex")
        assert "BayesianPanel" in config.recommended_panels
        assert config.primary_chart == "area"

    def test_chaotic_is_act_first(self):
        config = get_cynefin_viz_config("chaotic")
        assert config.interaction_mode == "act_first"
        assert config.detail_level == "summary"

    def test_all_configs_registered(self):
        assert len(CYNEFIN_VIZ_CONFIGS) == 5
