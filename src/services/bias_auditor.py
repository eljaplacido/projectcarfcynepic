"""Bias Auditor — System-level fairness audit across accumulated agent memory.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Phase 18B: Scans the agent memory corpus for domain distribution skew,
cross-references quality scores against domain to detect systematic
quality differences, and runs statistical tests for representation bias.

Addresses RSI Analysis Gap #2 and Antipattern AP-9.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.bias_auditor")

DOMAINS = ["clear", "complicated", "complex", "chaotic", "disorder"]


class BiasReport(BaseModel):
    """Result of a bias audit across accumulated memory."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_entries: int = 0
    domain_distribution: dict[str, int] = Field(default_factory=dict)
    domain_percentages: dict[str, float] = Field(default_factory=dict)
    chi_squared_statistic: float = 0.0
    chi_squared_p_value: float = 1.0
    distribution_biased: bool = False
    quality_by_domain: dict[str, dict[str, float]] = Field(default_factory=dict)
    quality_disparity: float = 0.0
    quality_biased: bool = False
    verdict_by_domain: dict[str, dict[str, int]] = Field(default_factory=dict)
    approval_rate_disparity: float = 0.0
    overall_bias_detected: bool = False
    findings: list[str] = Field(default_factory=list)


class BiasAuditor:
    """Audits agent memory for systematic bias.

    Three audit dimensions:
    1. Domain representation bias (chi-squared test)
    2. Quality score disparity across domains
    3. Guardian verdict disparity across domains

    Safety properties (AP-9 compliance):
    - Monitors the memory corpus that feeds routing hints
    - Detects if accumulated analyses are systematically skewed
    - Reports enable human review of memory-driven routing influence
    """

    def __init__(
        self,
        chi_squared_threshold: float = 0.05,
        quality_disparity_threshold: float = 0.20,
        approval_disparity_threshold: float = 0.15,
    ) -> None:
        self._chi_squared_threshold = chi_squared_threshold
        self._quality_disparity_threshold = quality_disparity_threshold
        self._approval_disparity_threshold = approval_disparity_threshold

    def audit(self, memory: Any = None) -> BiasReport:
        """Run a full bias audit on the agent memory corpus.

        Args:
            memory: AgentMemory instance. If None, uses singleton.

        Returns:
            BiasReport with findings and statistical tests.
        """
        if memory is None:
            from src.services.agent_memory import get_agent_memory
            memory = get_agent_memory()

        entries = memory._store._entries  # Access internal store entries
        report = BiasReport(total_entries=len(entries))

        if len(entries) < 10:
            report.findings.append(
                f"Insufficient data for audit ({len(entries)} entries, need 10+)"
            )
            return report

        # 1. Domain distribution bias
        self._audit_distribution(entries, report)

        # 2. Quality score disparity
        self._audit_quality(entries, report)

        # 3. Guardian verdict disparity
        self._audit_verdicts(entries, report)

        # Overall assessment
        report.overall_bias_detected = (
            report.distribution_biased
            or report.quality_biased
            or report.approval_rate_disparity > self._approval_disparity_threshold
        )

        if report.overall_bias_detected:
            logger.warning(
                "BIAS DETECTED in agent memory: %s",
                "; ".join(report.findings),
            )
        else:
            logger.info("Bias audit passed: no significant bias detected")

        return report

    def _audit_distribution(self, entries: list, report: BiasReport) -> None:
        """Chi-squared test for domain representation bias."""
        domain_counts: dict[str, int] = {d: 0 for d in DOMAINS}
        for entry in entries:
            d = entry.domain.lower() if hasattr(entry, "domain") else "unknown"
            if d in domain_counts:
                domain_counts[d] += 1

        total = sum(domain_counts.values())
        if total == 0:
            return

        report.domain_distribution = domain_counts
        report.domain_percentages = {
            d: round(c / total, 4) for d, c in domain_counts.items()
        }

        # Chi-squared test against uniform distribution
        expected = total / len(DOMAINS)
        chi_sq = 0.0
        for count in domain_counts.values():
            chi_sq += (count - expected) ** 2 / expected if expected > 0 else 0

        report.chi_squared_statistic = round(chi_sq, 4)

        # Approximate p-value using chi-squared distribution (df = 4)
        # Using Wilson-Hilferty approximation
        df = len(DOMAINS) - 1
        report.chi_squared_p_value = round(
            self._chi_squared_p_value(chi_sq, df), 6
        )
        report.distribution_biased = report.chi_squared_p_value < self._chi_squared_threshold

        if report.distribution_biased:
            # Find most over/under-represented domains
            max_pct = max(report.domain_percentages.values())
            min_pct = min(report.domain_percentages.values())
            over = [d for d, p in report.domain_percentages.items() if p == max_pct]
            under = [d for d, p in report.domain_percentages.items() if p == min_pct]
            report.findings.append(
                f"Domain distribution biased (chi²={chi_sq:.2f}, p={report.chi_squared_p_value:.4f}): "
                f"over-represented={over}, under-represented={under}"
            )

    def _audit_quality(self, entries: list, report: BiasReport) -> None:
        """Check for systematic quality score differences across domains."""
        domain_quality: dict[str, list[float]] = {d: [] for d in DOMAINS}

        for entry in entries:
            d = entry.domain.lower() if hasattr(entry, "domain") else "unknown"
            if d in domain_quality and hasattr(entry, "quality_score") and entry.quality_score is not None:
                domain_quality[d].append(entry.quality_score)

        quality_stats: dict[str, dict[str, float]] = {}
        for d, scores in domain_quality.items():
            if scores:
                avg = sum(scores) / len(scores)
                quality_stats[d] = {
                    "mean": round(avg, 4),
                    "count": len(scores),
                    "min": round(min(scores), 4),
                    "max": round(max(scores), 4),
                }

        report.quality_by_domain = quality_stats

        if len(quality_stats) >= 2:
            means = [s["mean"] for s in quality_stats.values()]
            report.quality_disparity = round(max(means) - min(means), 4)
            report.quality_biased = report.quality_disparity > self._quality_disparity_threshold

            if report.quality_biased:
                best = max(quality_stats.items(), key=lambda x: x[1]["mean"])
                worst = min(quality_stats.items(), key=lambda x: x[1]["mean"])
                report.findings.append(
                    f"Quality disparity {report.quality_disparity:.2%} between "
                    f"best ({best[0]}: {best[1]['mean']:.2f}) and "
                    f"worst ({worst[0]}: {worst[1]['mean']:.2f})"
                )

    def _audit_verdicts(self, entries: list, report: BiasReport) -> None:
        """Check for Guardian verdict disparity across domains."""
        domain_verdicts: dict[str, dict[str, int]] = {d: {} for d in DOMAINS}

        for entry in entries:
            d = entry.domain.lower() if hasattr(entry, "domain") else "unknown"
            verdict = entry.guardian_verdict if hasattr(entry, "guardian_verdict") else None
            if d in domain_verdicts and verdict:
                v = verdict.lower()
                domain_verdicts[d][v] = domain_verdicts[d].get(v, 0) + 1

        report.verdict_by_domain = domain_verdicts

        # Compute approval rates
        approval_rates: dict[str, float] = {}
        for d, verdicts in domain_verdicts.items():
            total = sum(verdicts.values())
            if total >= 3:  # Need minimum data
                approved = verdicts.get("approved", 0)
                approval_rates[d] = approved / total

        if len(approval_rates) >= 2:
            rates = list(approval_rates.values())
            report.approval_rate_disparity = round(max(rates) - min(rates), 4)

            if report.approval_rate_disparity > self._approval_disparity_threshold:
                best = max(approval_rates.items(), key=lambda x: x[1])
                worst = min(approval_rates.items(), key=lambda x: x[1])
                report.findings.append(
                    f"Approval rate disparity {report.approval_rate_disparity:.2%}: "
                    f"{best[0]} ({best[1]:.0%}) vs {worst[0]} ({worst[1]:.0%})"
                )

    @staticmethod
    def _chi_squared_p_value(chi_sq: float, df: int) -> float:
        """Approximate p-value for chi-squared distribution.

        Uses the regularized incomplete gamma function approximation.
        """
        if chi_sq <= 0:
            return 1.0
        if df <= 0:
            return 0.0

        # Simple approximation using normal distribution for large df
        # For df=4 (our case), this is reasonable
        z = ((chi_sq / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
        # Standard normal CDF approximation
        p = 0.5 * (1 + math.erf(-z / math.sqrt(2)))
        return max(0.0, min(1.0, p))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_bias_auditor: BiasAuditor | None = None


def get_bias_auditor() -> BiasAuditor:
    """Get the singleton BiasAuditor instance."""
    global _bias_auditor
    if _bias_auditor is None:
        _bias_auditor = BiasAuditor()
    return _bias_auditor
