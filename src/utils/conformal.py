"""Split-conformal calibration for the Cynefin router (R1/G2).

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Wraps the router's domain-probability output with a distribution-free calibration
step that yields finite-sample *marginal coverage*:

    P( true_domain in prediction_set(X) ) >= 1 - alpha

This implements split-conformal classification with the **LAC** (Least Ambiguous
set-valued Classifier; Sadinle, Lei & Wasserman 2019) non-conformity score
``s = 1 - p[true_label]`` — the same marginal-coverage method the MAPIE library
exposes — but in pure NumPy so it carries no extra dependency and degrades
gracefully (a router with no calibration artifact simply behaves as before).

A prediction set with cardinality > 1 marks a *borderline* query the router cannot
separate at the chosen confidence level; the Guardian/escalation layer can use that
signal to demand stricter human review.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.conformal")


class ConformalCalibration(BaseModel):
    """A fitted split-conformal calibration artifact (serializable)."""

    alpha: float = Field(..., ge=0.0, le=1.0, description="Miscoverage level (target coverage = 1-alpha)")
    qhat: float = Field(..., description="Calibrated non-conformity quantile threshold")
    labels: list[str] = Field(..., description="Domain label space, fixed at calibration time")
    n_calibration: int = Field(..., ge=0, description="Number of calibration examples used")
    method: str = Field(default="lac", description="Non-conformity score method")


def _nonconformity(scores: dict[str, float], label: str) -> float:
    """LAC non-conformity score: 1 - P(true label). Higher = worse fit."""
    total = sum(v for v in scores.values() if v > 0) or 1.0
    return 1.0 - (max(0.0, scores.get(label, 0.0)) / total)


def fit_conformal(
    scores: list[dict[str, float]],
    labels: list[str],
    alpha: float = 0.1,
) -> ConformalCalibration:
    """Fit a split-conformal calibration on held-out (scores, true_label) pairs.

    Uses the finite-sample corrected quantile level ceil((n+1)(1-alpha))/n. When that
    level exceeds 1 (too few calibration points for the requested alpha) qhat is set to
    +inf, i.e. the prediction set conservatively contains every domain.
    """
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have equal length")
    if not scores:
        raise ValueError("at least one calibration example is required")

    label_space = sorted({lab for d in scores for lab in d} | set(labels))
    nonconf = np.array(
        [_nonconformity(s, y) for s, y in zip(scores, labels, strict=False)], dtype=float
    )
    n = len(nonconf)

    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        qhat = float("inf")
    else:
        # k-th smallest non-conformity score (1-indexed) == the corrected quantile.
        qhat = float(np.sort(nonconf)[k - 1])

    return ConformalCalibration(
        alpha=alpha, qhat=qhat, labels=label_space, n_calibration=n, method="lac"
    )


def prediction_set(
    scores: dict[str, float], calibration: ConformalCalibration
) -> list[str]:
    """Return the conformal prediction set {y : 1 - p[y] <= qhat}.

    Guaranteed non-empty: if no label clears the threshold, the single most likely
    domain is returned so routing always has a concrete choice.
    """
    total = sum(v for v in scores.values() if v > 0) or 1.0
    chosen = [
        lab
        for lab in calibration.labels
        if (1.0 - max(0.0, scores.get(lab, 0.0)) / total) <= calibration.qhat
    ]
    if not chosen and scores:
        chosen = [max(scores, key=lambda k: scores[k])]
    return chosen


def empirical_coverage(
    scores: list[dict[str, float]],
    labels: list[str],
    calibration: ConformalCalibration,
) -> float:
    """Fraction of test examples whose prediction set contains the true label."""
    if not scores:
        return 0.0
    hits = sum(
        1 for s, y in zip(scores, labels, strict=False) if y in prediction_set(s, calibration)
    )
    return hits / len(scores)


def average_set_size(
    scores: list[dict[str, float]], calibration: ConformalCalibration
) -> float:
    """Mean prediction-set cardinality (efficiency; smaller is sharper)."""
    if not scores:
        return 0.0
    return sum(len(prediction_set(s, calibration)) for s in scores) / len(scores)


def save_calibration(calibration: ConformalCalibration, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(calibration.model_dump_json(indent=2), encoding="utf-8")


def load_calibration(path: str | Path) -> ConformalCalibration | None:
    """Load a calibration artifact; returns None if absent or unreadable (graceful)."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return ConformalCalibration.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load conformal calibration %s: %s", p, exc)
        return None
