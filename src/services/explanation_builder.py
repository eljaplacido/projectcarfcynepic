"""Explanation Builder — Structured evidence weaving for XAI fidelity.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Weaves causal_evidence and bayesian_evidence fields into the
final_response and reasoning chain so that XAI benchmarks can
verify that domain-specific evidence is faithfully surfaced.

All operations are non-destructive: text is appended, never replaced.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("carf.explanation_builder")


def build_causal_explanation(evidence: Any) -> str:
    """Build a structured explanation paragraph from CausalEvidence.

    Args:
        evidence: A CausalEvidence object (or compatible duck-typed object).

    Returns:
        Human-readable explanation string weaving all evidence fields.
    """
    parts: list[str] = []

    treatment = getattr(evidence, "treatment", "") or "treatment"
    outcome = getattr(evidence, "outcome", "") or "outcome"
    effect_size = getattr(evidence, "effect_size", None)
    ci = getattr(evidence, "confidence_interval", None)
    refutation_passed = getattr(evidence, "refutation_passed", None)
    confounders = getattr(evidence, "confounders_checked", []) or []
    p_value = getattr(evidence, "p_value", None)
    mechanism = getattr(evidence, "mechanism", "") or ""
    refutation_results = getattr(evidence, "refutation_results", {}) or {}

    parts.append(
        f"Causal analysis examined the effect of {treatment} on {outcome}."
    )

    if mechanism:
        parts.append(f"The proposed mechanism is: {mechanism}.")

    if effect_size is not None:
        parts.append(f"The estimated causal effect size is {effect_size:.4f}.")

    if ci and len(ci) == 2:
        parts.append(
            f"The 95% confidence interval is [{ci[0]:.4f}, {ci[1]:.4f}]."
        )

    if p_value is not None:
        parts.append(f"Statistical significance: p-value = {p_value:.4f}.")

    if confounders:
        parts.append(
            f"Confounders checked: {', '.join(confounders)}."
        )

    if refutation_passed is not None:
        status = "PASSED" if refutation_passed else "FAILED"
        parts.append(f"Refutation tests: {status}.")

    if refutation_results:
        details = ", ".join(
            f"{k}: {'passed' if v else 'failed'}"
            for k, v in refutation_results.items()
        )
        parts.append(f"Individual refutations: {details}.")

    return " ".join(parts)


def build_bayesian_explanation(evidence: Any) -> str:
    """Build a structured explanation paragraph from BayesianEvidence.

    Args:
        evidence: A BayesianEvidence object (or compatible duck-typed object).

    Returns:
        Human-readable explanation string weaving all evidence fields.
    """
    parts: list[str] = []

    hypothesis = getattr(evidence, "hypothesis", "") or ""
    posterior_mean = getattr(evidence, "posterior_mean", None)
    credible_interval = getattr(evidence, "credible_interval", None)
    epistemic = getattr(evidence, "epistemic_uncertainty", None)
    aleatoric = getattr(evidence, "aleatoric_uncertainty", None)
    uncertainty_before = getattr(evidence, "uncertainty_before", None)
    uncertainty_after = getattr(evidence, "uncertainty_after", None)
    probes_designed = getattr(evidence, "probes_designed", None)
    recommended_probe = getattr(evidence, "recommended_probe", None)

    if hypothesis:
        parts.append(f"Bayesian analysis explored the hypothesis: {hypothesis}.")

    if posterior_mean is not None:
        parts.append(f"The posterior mean estimate is {posterior_mean:.4f}.")

    if credible_interval and len(credible_interval) == 2:
        parts.append(
            f"The 95% credible interval is [{credible_interval[0]:.4f}, {credible_interval[1]:.4f}]."
        )

    if epistemic is not None:
        parts.append(f"Epistemic uncertainty (reducible): {epistemic:.4f}.")

    if aleatoric is not None:
        parts.append(f"Aleatoric uncertainty (irreducible): {aleatoric:.4f}.")

    if uncertainty_before is not None and uncertainty_after is not None:
        reduction = uncertainty_before - uncertainty_after
        if reduction > 0:
            parts.append(
                f"Uncertainty reduced from {uncertainty_before:.4f} to {uncertainty_after:.4f} "
                f"(reduction: {reduction:.4f})."
            )

    if probes_designed is not None and probes_designed > 0:
        parts.append(f"Number of probes designed: {probes_designed}.")

    if recommended_probe:
        parts.append(f"Recommended next probe: {recommended_probe}.")

    return " ".join(parts)


def enrich_state_explanation(state: Any) -> Any:
    """Append structured evidence summary to state's final_response and reasoning chain.

    Non-destructive: appends to existing final_response and enriches the last
    reasoning_chain entry's output_summary. Never replaces existing content.

    Args:
        state: EpistemicState (or compatible) with causal_evidence / bayesian_evidence.

    Returns:
        The same state object, enriched.
    """
    evidence_parts: list[str] = []

    # Build causal explanation if evidence exists
    causal_evidence = getattr(state, "causal_evidence", None)
    if causal_evidence:
        try:
            causal_text = build_causal_explanation(causal_evidence)
            if causal_text:
                evidence_parts.append(causal_text)
        except Exception as exc:
            logger.debug("Causal explanation build failed: %s", exc)

    # Build Bayesian explanation if evidence exists
    bayesian_evidence = getattr(state, "bayesian_evidence", None)
    if bayesian_evidence:
        try:
            bayesian_text = build_bayesian_explanation(bayesian_evidence)
            if bayesian_text:
                evidence_parts.append(bayesian_text)
        except Exception as exc:
            logger.debug("Bayesian explanation build failed: %s", exc)

    if not evidence_parts:
        return state

    evidence_summary = "\n\n**Evidence Summary:** " + " ".join(evidence_parts)

    # Append to final_response (non-destructive)
    current_response = getattr(state, "final_response", None) or ""
    state.final_response = current_response + evidence_summary

    # Enrich last reasoning chain entry's output_summary
    reasoning_chain = getattr(state, "reasoning_chain", None)
    if reasoning_chain and len(reasoning_chain) > 0:
        last_step = reasoning_chain[-1]
        existing_summary = getattr(last_step, "output_summary", "")
        enriched = f"{existing_summary} | Evidence: {' '.join(evidence_parts)[:200]}"
        last_step.output_summary = enriched

    return state
