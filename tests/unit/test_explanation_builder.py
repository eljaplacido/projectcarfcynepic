# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for src/services/explanation_builder.py."""

from unittest.mock import MagicMock

from src.services.explanation_builder import (
    build_bayesian_explanation,
    build_causal_explanation,
    enrich_state_explanation,
)


class TestBuildCausalExplanation:
    """Tests for build_causal_explanation."""

    def test_basic_causal_evidence(self):
        evidence = MagicMock()
        evidence.treatment = "discount"
        evidence.outcome = "churn"
        evidence.effect_size = 0.35
        evidence.confidence_interval = (-0.05, 0.75)
        evidence.refutation_passed = True
        evidence.confounders_checked = ["region", "tenure"]
        evidence.p_value = 0.02
        evidence.mechanism = "Price sensitivity"
        evidence.refutation_results = {"placebo": True, "subset": True}

        text = build_causal_explanation(evidence)

        assert "discount" in text
        assert "churn" in text
        assert "0.3500" in text
        assert "confidence interval" in text.lower()
        assert "PASSED" in text
        assert "region" in text
        assert "tenure" in text
        assert "Price sensitivity" in text

    def test_minimal_evidence(self):
        evidence = MagicMock()
        evidence.treatment = "treatment"
        evidence.outcome = "outcome"
        evidence.effect_size = 1.5
        evidence.confidence_interval = None
        evidence.refutation_passed = None
        evidence.confounders_checked = []
        evidence.p_value = None
        evidence.mechanism = ""
        evidence.refutation_results = {}

        text = build_causal_explanation(evidence)

        assert "treatment" in text
        assert "outcome" in text
        assert "1.5000" in text

    def test_failed_refutation(self):
        evidence = MagicMock()
        evidence.treatment = "treatment"
        evidence.outcome = "outcome"
        evidence.effect_size = 0.1
        evidence.confidence_interval = (-0.5, 0.7)
        evidence.refutation_passed = False
        evidence.confounders_checked = []
        evidence.p_value = None
        evidence.mechanism = ""
        evidence.refutation_results = {"placebo": False}

        text = build_causal_explanation(evidence)

        assert "FAILED" in text
        assert "placebo: failed" in text


class TestBuildBayesianExplanation:
    """Tests for build_bayesian_explanation."""

    def test_basic_bayesian_evidence(self):
        evidence = MagicMock()
        evidence.hypothesis = "Conversion rate > 0.5"
        evidence.posterior_mean = 0.42
        evidence.credible_interval = (0.18, 0.66)
        evidence.epistemic_uncertainty = 0.25
        evidence.aleatoric_uncertainty = 0.10
        evidence.uncertainty_before = 1.0
        evidence.uncertainty_after = 0.5
        evidence.probes_designed = 3
        evidence.recommended_probe = "Run A/B test with 200 samples"

        text = build_bayesian_explanation(evidence)

        assert "Conversion rate > 0.5" in text
        assert "0.4200" in text
        assert "credible interval" in text.lower()
        assert "Epistemic" in text
        assert "Aleatoric" in text
        assert "reduced" in text.lower()
        assert "3" in text
        assert "A/B test" in text

    def test_minimal_bayesian_evidence(self):
        evidence = MagicMock()
        evidence.hypothesis = ""
        evidence.posterior_mean = 0.7
        evidence.credible_interval = None
        evidence.epistemic_uncertainty = None
        evidence.aleatoric_uncertainty = None
        evidence.uncertainty_before = None
        evidence.uncertainty_after = None
        evidence.probes_designed = 0
        evidence.recommended_probe = None

        text = build_bayesian_explanation(evidence)

        assert "0.7000" in text


class TestEnrichStateExplanation:
    """Tests for enrich_state_explanation."""

    def test_enriches_causal_state(self):
        state = MagicMock()
        state.final_response = "Original response."
        state.causal_evidence = MagicMock()
        state.causal_evidence.treatment = "supplier"
        state.causal_evidence.outcome = "cost"
        state.causal_evidence.effect_size = 0.5
        state.causal_evidence.confidence_interval = (0.1, 0.9)
        state.causal_evidence.refutation_passed = True
        state.causal_evidence.confounders_checked = []
        state.causal_evidence.p_value = 0.01
        state.causal_evidence.mechanism = "cost reduction"
        state.causal_evidence.refutation_results = {}
        state.bayesian_evidence = None
        state.reasoning_chain = [MagicMock()]
        state.reasoning_chain[0].output_summary = "Effect: 0.50"

        result = enrich_state_explanation(state)

        assert "Evidence Summary" in result.final_response
        assert "supplier" in result.final_response
        assert "cost" in result.final_response
        assert "Evidence:" in result.reasoning_chain[0].output_summary

    def test_enriches_bayesian_state(self):
        state = MagicMock()
        state.final_response = "Bayesian analysis done."
        state.causal_evidence = None
        state.bayesian_evidence = MagicMock()
        state.bayesian_evidence.hypothesis = "Rate exceeds target"
        state.bayesian_evidence.posterior_mean = 0.6
        state.bayesian_evidence.credible_interval = (0.3, 0.9)
        state.bayesian_evidence.epistemic_uncertainty = 0.2
        state.bayesian_evidence.aleatoric_uncertainty = 0.1
        state.bayesian_evidence.uncertainty_before = 1.0
        state.bayesian_evidence.uncertainty_after = 0.4
        state.bayesian_evidence.probes_designed = 2
        state.bayesian_evidence.recommended_probe = None
        state.reasoning_chain = []

        result = enrich_state_explanation(state)

        assert "Evidence Summary" in result.final_response
        assert "Rate exceeds target" in result.final_response

    def test_no_evidence_returns_unchanged(self):
        state = MagicMock()
        state.final_response = "No evidence here."
        state.causal_evidence = None
        state.bayesian_evidence = None

        result = enrich_state_explanation(state)

        assert result.final_response == "No evidence here."

    def test_handles_none_final_response(self):
        state = MagicMock()
        state.final_response = None
        state.causal_evidence = MagicMock()
        state.causal_evidence.treatment = "T"
        state.causal_evidence.outcome = "Y"
        state.causal_evidence.effect_size = 1.0
        state.causal_evidence.confidence_interval = (0.5, 1.5)
        state.causal_evidence.refutation_passed = True
        state.causal_evidence.confounders_checked = []
        state.causal_evidence.p_value = None
        state.causal_evidence.mechanism = ""
        state.causal_evidence.refutation_results = {}
        state.bayesian_evidence = None
        state.reasoning_chain = []

        result = enrich_state_explanation(state)

        assert "Evidence Summary" in result.final_response
