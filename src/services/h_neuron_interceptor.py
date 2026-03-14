# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H-Neuron Interceptor — Mechanistic hallucination detection for CARF.

Provides a pluggable sentinel interface for pre-delivery hallucination
interception. Two modes:

1. PROXY (default): Uses existing CARF signals (DeepEval scores, uncertainty,
   domain confidence) to approximate hallucination risk. Always available.
2. MECHANISTIC (requires PyTorch + local model): Uses forward-hook activation
   analysis on a local open-weights model to detect hallucination neurons.

Feature-flagged via HNEURON_ENABLED environment variable (default: false).

Research basis: THUNLP H-Neurons, detailed in
docs/H_NEURONS_INTEGRATION_EVALUATION.md
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.h_neuron")


# ---------------------------------------------------------------------------
# Configuration & Data Models
# ---------------------------------------------------------------------------


class HNeuronConfig(BaseModel):
    """Configuration for H-Neuron Sentinel."""

    enabled: bool = Field(default=False)
    mode: str = Field(default="proxy", description="proxy or mechanistic")
    hallucination_threshold: float = Field(default=0.3)
    intervention_threshold: float = Field(default=0.85)
    active_domains: list[str] = Field(
        default_factory=lambda: ["Complicated", "Complex"]
    )
    max_latency_ms: int = Field(default=100)
    # Mechanistic mode settings (only used when mode="mechanistic")
    model_id: str = Field(default="meta-llama/Meta-Llama-3-8B-Instruct")
    target_layers: list[int] = Field(
        default_factory=lambda: [15, 16, 17, 18, 19]
    )
    classifier_path: str = Field(default="models/h_neuron_classifier.pt")


class HallucinationAssessment(BaseModel):
    """Result of H-Neuron hallucination assessment."""

    score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="0=factual, 1=hallucinating"
    )
    flagged: bool = Field(default=False)
    intervention_recommended: bool = Field(default=False)
    mode: str = Field(default="proxy", description="proxy or mechanistic")
    latency_ms: int = Field(default=0)
    signal_components: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of signals contributing to score",
    )
    explanation: str = Field(default="")


# ---------------------------------------------------------------------------
# Signal weights for proxy fusion
# ---------------------------------------------------------------------------

_PROXY_WEIGHTS: dict[str, float] = {
    "deepeval_hallucination_risk": 0.35,
    "confidence_risk": 0.20,
    "epistemic_uncertainty": 0.15,
    "reflection_risk": 0.10,
    "brevity_risk": 0.05,
    "verbosity_risk": 0.03,
    "irrelevancy_risk": 0.07,
    "shallow_reasoning_risk": 0.05,
}


# ---------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------


class HNeuronSentinel:
    """Pluggable hallucination detection sentinel.

    In proxy mode, fuses existing CARF signals into a unified
    hallucination risk score.  In mechanistic mode, would use PyTorch
    forward hooks on a local model (requires classifier + weights).
    """

    def __init__(self, config: HNeuronConfig | None = None):
        self._config = config or self._load_config()
        self._mechanistic_available = False
        if self._config.mode == "mechanistic":
            self._try_init_mechanistic()

    # -- Factory -----------------------------------------------------------

    @staticmethod
    def _load_config() -> HNeuronConfig:
        """Load config from environment variables."""
        return HNeuronConfig(
            enabled=os.getenv("HNEURON_ENABLED", "false").lower()
            in ("true", "1", "yes"),
            mode=os.getenv("HNEURON_MODE", "proxy"),
            hallucination_threshold=float(
                os.getenv("HNEURON_THRESHOLD", "0.3")
            ),
            intervention_threshold=float(
                os.getenv("HNEURON_INTERVENTION_THRESHOLD", "0.85")
            ),
        )

    # -- Properties --------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._config.enabled

    @property
    def mode(self) -> str:
        if self._mechanistic_available:
            return "mechanistic"
        return "proxy"

    def is_active_for(self, cynefin_domain: str) -> bool:
        """Check if sentinel should activate for a given Cynefin domain."""
        if not self._config.enabled:
            return False
        return cynefin_domain in self._config.active_domains

    # -- Core Assessment ---------------------------------------------------

    def assess_hallucination_risk(
        self,
        *,
        response_text: str = "",
        deepeval_hallucination_risk: float | None = None,
        domain_confidence: float | None = None,
        epistemic_uncertainty: float | None = None,
        reflection_count: int = 0,
        quality_scores: dict[str, Any] | None = None,
    ) -> HallucinationAssessment:
        """Assess hallucination risk using available signals.

        In proxy mode, fuses:
        - DeepEval hallucination_risk (if available)
        - Domain confidence (inverse — low confidence = higher risk)
        - Epistemic uncertainty (direct)
        - Reflection count (multiple reflections suggest instability)
        - Response length heuristic
        - Quality score components (relevancy, reasoning depth)

        Returns ``HallucinationAssessment`` with fused score.
        """
        start = time.monotonic()
        signals: dict[str, float] = {}

        # Signal 1: DeepEval hallucination risk (direct, highest weight)
        if deepeval_hallucination_risk is not None:
            signals["deepeval_hallucination_risk"] = deepeval_hallucination_risk

        # Signal 2: Domain confidence (inverse)
        if domain_confidence is not None:
            signals["confidence_risk"] = max(0.0, 1.0 - domain_confidence)

        # Signal 3: Epistemic uncertainty (direct)
        if epistemic_uncertainty is not None:
            signals["epistemic_uncertainty"] = epistemic_uncertainty

        # Signal 4: Reflection instability
        if reflection_count > 0:
            signals["reflection_risk"] = min(reflection_count * 0.15, 0.6)

        # Signal 5: Response length heuristic
        if response_text:
            word_count = len(response_text.split())
            if word_count < 10:
                signals["brevity_risk"] = 0.3
            elif word_count > 2000:
                signals["verbosity_risk"] = 0.15

        # Signal 6: Quality score aggregation
        if quality_scores:
            relevancy = quality_scores.get("relevancy", 1.0)
            if isinstance(relevancy, (int, float)):
                signals["irrelevancy_risk"] = max(0.0, 1.0 - relevancy)
            reasoning = quality_scores.get("reasoning_depth", 1.0)
            if isinstance(reasoning, (int, float)):
                signals["shallow_reasoning_risk"] = max(0.0, 1.0 - reasoning)

        # Fuse signals with weighted average
        if not signals:
            score = 0.0
        else:
            total_weight = sum(
                _PROXY_WEIGHTS.get(k, 0.05) for k in signals
            )
            score = sum(
                signals[k] * _PROXY_WEIGHTS.get(k, 0.05) for k in signals
            ) / max(total_weight, 0.01)
            score = max(0.0, min(1.0, score))

        elapsed_ms = int((time.monotonic() - start) * 1000)

        flagged = score >= self._config.hallucination_threshold
        intervention = score >= self._config.intervention_threshold

        # Build explanation
        explanation_parts: list[str] = []
        if flagged:
            top_signals = sorted(
                signals.items(), key=lambda x: x[1], reverse=True
            )[:3]
            explanation_parts.append(
                f"Hallucination risk {score:.0%} exceeds threshold "
                f"{self._config.hallucination_threshold:.0%}."
            )
            explanation_parts.append(
                "Top signals: "
                + ", ".join(f"{k}={v:.2f}" for k, v in top_signals)
            )
        if intervention:
            explanation_parts.append(
                "Intervention recommended — risk exceeds intervention threshold."
            )

        return HallucinationAssessment(
            score=round(score, 4),
            flagged=flagged,
            intervention_recommended=intervention,
            mode=self.mode,
            latency_ms=elapsed_ms,
            signal_components=signals,
            explanation=(
                " ".join(explanation_parts)
                if explanation_parts
                else "Within acceptable risk bounds."
            ),
        )

    # -- Mechanistic mode (placeholder) ------------------------------------

    def _try_init_mechanistic(self) -> None:
        """Try to initialize mechanistic mode with PyTorch."""
        try:
            import torch  # noqa: F401

            logger.info(
                "PyTorch available — mechanistic H-Neuron mode could be enabled"
            )
            # Full implementation would:
            # 1. Load model from self._config.model_id
            # 2. Load classifier from self._config.classifier_path
            # 3. Register forward hooks on target_layers
            self._mechanistic_available = False  # Until classifier is trained
        except ImportError:
            logger.debug("PyTorch not available — using proxy mode")
            self._mechanistic_available = False

    # -- Status ------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return sentinel status for health checks."""
        return {
            "enabled": self._config.enabled,
            "mode": self.mode,
            "hallucination_threshold": self._config.hallucination_threshold,
            "intervention_threshold": self._config.intervention_threshold,
            "active_domains": self._config.active_domains,
            "mechanistic_available": self._mechanistic_available,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_sentinel: HNeuronSentinel | None = None


def get_h_neuron_sentinel() -> HNeuronSentinel:
    """Get the singleton H-Neuron Sentinel."""
    global _sentinel
    if _sentinel is None:
        _sentinel = HNeuronSentinel()
    return _sentinel
