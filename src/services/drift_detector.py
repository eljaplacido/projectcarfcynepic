"""Drift Detector — Monitors memory→router feedback loop for distributional drift.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Phase 18A: Tracks domain routing distribution over rolling windows and
computes KL-divergence between current and baseline distributions.
Alerts on statistically significant shifts.

Addresses RSI Analysis Gap #1 and Antipattern AP-9.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.drift_detector")

# Cynefin domains for consistent ordering
DOMAINS = ["clear", "complicated", "complex", "chaotic", "disorder"]


class DriftSnapshot(BaseModel):
    """A single drift measurement."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    window_size: int = 0
    current_distribution: dict[str, float] = Field(default_factory=dict)
    baseline_distribution: dict[str, float] = Field(default_factory=dict)
    kl_divergence: float = 0.0
    max_domain_shift: float = 0.0
    shifted_domain: str = ""
    drift_detected: bool = False
    alert_reason: str = ""


class DriftDetector:
    """Monitors routing distribution for drift over rolling windows.

    Uses KL-divergence to compare current routing distribution against
    a baseline established from the first N observations. Alerts when
    drift exceeds configurable thresholds.

    Safety properties (AP-9 compliance):
    - Drift metric: KL-divergence between current and baseline distributions
    - Bound: Memory hint weight capped at 0.03 (enforced in router.py)
    - Convergence check: Not applicable (drift is monitored, not optimized)
    - Audit trail: All drift snapshots stored in bounded deque
    """

    def __init__(
        self,
        baseline_window: int = 100,
        detection_window: int = 50,
        kl_threshold: float = 0.15,
        domain_shift_threshold: float = 0.10,
        max_history: int = 500,
    ) -> None:
        self._baseline_window = baseline_window
        self._detection_window = detection_window
        self._kl_threshold = kl_threshold
        self._domain_shift_threshold = domain_shift_threshold

        self._observations: deque[str] = deque(maxlen=max_history)
        self._baseline: dict[str, float] | None = None
        self._baseline_count: int = 0
        self._snapshots: deque[DriftSnapshot] = deque(maxlen=200)
        self._total_observations: int = 0
        self._alert_count: int = 0

    def record_routing(self, domain: str) -> DriftSnapshot | None:
        """Record a domain routing decision and check for drift.

        Args:
            domain: The Cynefin domain the query was routed to.

        Returns:
            DriftSnapshot if enough observations exist, None otherwise.
        """
        domain_lower = domain.lower()
        self._observations.append(domain_lower)
        self._total_observations += 1

        # Build baseline from first N observations
        if self._baseline is None and self._total_observations >= self._baseline_window:
            self._baseline = self._compute_distribution(
                list(self._observations)[:self._baseline_window]
            )
            self._baseline_count = self._baseline_window
            logger.info(
                "Drift baseline established from %d observations: %s",
                self._baseline_window,
                {d: f"{v:.2%}" for d, v in self._baseline.items()},
            )

        # Check drift after baseline is established and we have enough new data
        if (
            self._baseline is not None
            and self._total_observations >= self._baseline_window + self._detection_window
            and self._total_observations % self._detection_window == 0
        ):
            return self._check_drift()

        return None

    def _compute_distribution(self, observations: list[str]) -> dict[str, float]:
        """Compute domain frequency distribution from observations."""
        counts: dict[str, int] = {d: 0 for d in DOMAINS}
        for obs in observations:
            if obs in counts:
                counts[obs] += 1
        total = len(observations) or 1
        return {d: c / total for d, c in counts.items()}

    def _kl_divergence(
        self, p: dict[str, float], q: dict[str, float], epsilon: float = 1e-10
    ) -> float:
        """Compute KL divergence D(P || Q) with smoothing."""
        kl = 0.0
        for d in DOMAINS:
            p_val = max(p.get(d, 0.0), epsilon)
            q_val = max(q.get(d, 0.0), epsilon)
            kl += p_val * math.log(p_val / q_val)
        return kl

    def _check_drift(self) -> DriftSnapshot:
        """Check current window against baseline for drift."""
        recent = list(self._observations)[-self._detection_window:]
        current_dist = self._compute_distribution(recent)

        kl = self._kl_divergence(current_dist, self._baseline)  # type: ignore[arg-type]

        # Find the domain with the largest shift
        max_shift = 0.0
        shifted_domain = ""
        for d in DOMAINS:
            shift = abs(current_dist.get(d, 0) - self._baseline.get(d, 0))  # type: ignore[union-attr]
            if shift > max_shift:
                max_shift = shift
                shifted_domain = d

        # Determine if drift is significant
        drift_detected = False
        alert_reason = ""

        if kl > self._kl_threshold:
            drift_detected = True
            alert_reason = f"KL divergence {kl:.4f} exceeds threshold {self._kl_threshold}"
            self._alert_count += 1
            logger.warning("DRIFT DETECTED: %s", alert_reason)

        if max_shift > self._domain_shift_threshold:
            drift_detected = True
            shift_msg = (
                f"Domain '{shifted_domain}' shifted by {max_shift:.2%} "
                f"(threshold: {self._domain_shift_threshold:.2%})"
            )
            if alert_reason:
                alert_reason += f"; {shift_msg}"
            else:
                alert_reason = shift_msg
            self._alert_count += 1
            logger.warning("DRIFT DETECTED: %s", shift_msg)

        snapshot = DriftSnapshot(
            window_size=self._detection_window,
            current_distribution=current_dist,
            baseline_distribution=self._baseline or {},  # type: ignore[arg-type]
            kl_divergence=round(kl, 6),
            max_domain_shift=round(max_shift, 4),
            shifted_domain=shifted_domain,
            drift_detected=drift_detected,
            alert_reason=alert_reason,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_status(self) -> dict[str, Any]:
        """Get current drift monitoring status."""
        recent_dist = {}
        if self._observations:
            recent = list(self._observations)[-min(len(self._observations), self._detection_window):]
            recent_dist = self._compute_distribution(recent)

        return {
            "total_observations": self._total_observations,
            "baseline_established": self._baseline is not None,
            "baseline_distribution": self._baseline or {},
            "current_distribution": recent_dist,
            "alert_count": self._alert_count,
            "snapshot_count": len(self._snapshots),
            "last_snapshot": self._snapshots[-1].model_dump() if self._snapshots else None,
            "config": {
                "baseline_window": self._baseline_window,
                "detection_window": self._detection_window,
                "kl_threshold": self._kl_threshold,
                "domain_shift_threshold": self._domain_shift_threshold,
            },
        }

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent drift snapshots."""
        snapshots = list(self._snapshots)[-limit:]
        return [s.model_dump() for s in snapshots]

    def reset_baseline(self) -> None:
        """Force baseline recalculation from current observations."""
        if len(self._observations) >= self._baseline_window:
            recent = list(self._observations)[-self._baseline_window:]
            self._baseline = self._compute_distribution(recent)
            self._baseline_count = self._baseline_window
            self._alert_count = 0
            logger.info("Drift baseline reset from %d recent observations", self._baseline_window)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_drift_detector: DriftDetector | None = None


def get_drift_detector() -> DriftDetector:
    """Get the singleton DriftDetector instance."""
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = DriftDetector()
    return _drift_detector
