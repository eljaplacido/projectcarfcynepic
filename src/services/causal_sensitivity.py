# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Quantitative sensitivity analysis for causal estimates.

Implements the metrics that turn refutation from a binary pass/fail into
quantified evidence about how strong an unobserved confounder would need to be
to overturn the conclusion:

* **E-value** — VanderWeele & Ding (2017). On the risk-ratio scale,
  ``E = RR + sqrt(RR * (RR - 1))``. For continuous outcomes we approximate the
  RR via VanderWeele's recommended transform from a standardised effect size:
  ``RR ≈ exp(0.91 * d)`` where ``d = ATE / SD(outcome)``.
* **CI E-value** — same metric applied to the confidence-interval bound that
  is closest to the null. If the CI crosses the null, the CI E-value is 1.0
  (the result is consistent with no effect, so trivial confounding suffices).
* **Robustness verdict** — a single string in
  ``{passed, partial, failed, skipped}`` summarising the placebo / random
  common cause / data-subset / unobserved-common-cause battery.

These functions intentionally have **no DoWhy dependency** — they take the
estimate, its CI, and (optionally) the outcome SD as plain numbers so we can
unit-test them deterministically and call them from anywhere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

# Threshold below which an E-value is considered "weak evidence" — a confounder
# with strength ≤ 1.25 on each association is plausible in most observational
# settings (VanderWeele & Ding 2017, §4).
DEFAULT_MIN_E_VALUE = 1.25


@dataclass(frozen=True)
class SensitivityReport:
    """Container for the quantified sensitivity assessment."""

    e_value: float | None
    e_value_ci: float | None
    refutations_passed: int
    refutations_total: int
    refutation_status: str  # passed | partial | failed | skipped
    robust: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "e_value": self.e_value,
            "e_value_ci": self.e_value_ci,
            "refutations_passed": self.refutations_passed,
            "refutations_total": self.refutations_total,
            "refutation_status": self.refutation_status,
            "robust": self.robust,
            "reasons": list(self.reasons),
        }


def _rr_from_continuous(effect: float, outcome_sd: float | None) -> float:
    """Convert a continuous-outcome effect to an approximate RR.

    Uses VanderWeele's transform RR ≈ exp(0.91 * d) where d is the
    standardised effect (Cohen's-d analogue). When ``outcome_sd`` is None or
    non-positive we treat the effect itself as the standardised quantity.
    """
    if outcome_sd is not None and outcome_sd > 0:
        d = effect / outcome_sd
    else:
        d = effect
    # Clamp d to a sane range — extremely large standardised effects produce
    # numerically uninterpretable RRs. d=10 already gives RR≈e^9 ≈ 8000 which
    # collapses the E-value formula to a no-op.
    d = max(min(d, 10.0), -10.0)
    return math.exp(0.91 * d)


def e_value_from_rr(rr: float) -> float:
    """E-value on the risk-ratio scale (VanderWeele & Ding 2017, eq 1).

    ``E = RR + sqrt(RR * (RR - 1))`` for RR > 1. For RR < 1 we apply the same
    formula to ``1/RR`` (symmetry of the bound). RR == 1 gives 1.0.
    """
    if not math.isfinite(rr) or rr <= 0:
        return float("nan")
    if rr == 1:
        return 1.0
    if rr < 1:
        rr = 1.0 / rr
    return rr + math.sqrt(rr * (rr - 1.0))


def compute_e_value(
    effect: float,
    confidence_interval: tuple[float, float] | None = None,
    *,
    outcome_sd: float | None = None,
    scale: str = "continuous",
) -> tuple[float | None, float | None]:
    """Compute the (point, CI) E-value pair.

    Args:
        effect: The point estimate — interpreted as a risk ratio when
            ``scale="risk_ratio"``, or as a continuous-outcome effect
            otherwise.
        confidence_interval: 95% CI as ``(lower, upper)``. Optional.
        outcome_sd: Outcome SD used for continuous-to-RR conversion. Ignored
            for ``scale="risk_ratio"``.
        scale: ``"risk_ratio"`` or ``"continuous"`` (default).

    Returns:
        ``(e_value, e_value_ci)``. ``e_value_ci`` is the E-value applied to
        the CI bound nearest the null (1 for RR scale). Returns ``(None, None)``
        if the inputs are non-finite.
    """
    if not math.isfinite(effect):
        return None, None

    if scale == "risk_ratio":
        rr_point = effect
    else:
        rr_point = _rr_from_continuous(effect, outcome_sd)

    e_point = e_value_from_rr(rr_point)

    e_ci: float | None = None
    if confidence_interval is not None:
        lo, hi = confidence_interval
        if math.isfinite(lo) and math.isfinite(hi):
            null_value = 1.0 if scale == "risk_ratio" else 0.0
            # If the CI contains the null, no confounding is needed to
            # "explain away" the result — the data are already consistent
            # with no effect, so the CI E-value collapses to 1.
            if lo <= null_value <= hi:
                e_ci = 1.0
            else:
                bound = lo if abs(lo - null_value) < abs(hi - null_value) else hi
                if scale == "risk_ratio":
                    e_ci = e_value_from_rr(bound)
                else:
                    rr_bound = _rr_from_continuous(bound, outcome_sd)
                    e_ci = e_value_from_rr(rr_bound)

    return e_point, e_ci


def summarize_refutations(
    refutation_results: Mapping[str, bool] | None,
) -> tuple[int, int, str]:
    """Reduce a refutation dict to ``(passed, total, status)``.

    Status semantics:
      * ``skipped`` — ``refutation_results`` is None or empty.
      * ``passed`` — every test passed.
      * ``failed`` — every test failed.
      * ``partial`` — mixed.
    """
    if not refutation_results:
        return 0, 0, "skipped"
    total = len(refutation_results)
    passed = sum(1 for v in refutation_results.values() if v)
    if passed == total:
        status = "passed"
    elif passed == 0:
        status = "failed"
    else:
        status = "partial"
    return passed, total, status


def assess_robustness(
    *,
    effect: float,
    confidence_interval: tuple[float, float] | None,
    refutation_results: Mapping[str, bool] | None,
    outcome_sd: float | None = None,
    scale: str = "continuous",
    min_e_value: float = DEFAULT_MIN_E_VALUE,
    require_all_refutations: bool = False,
) -> SensitivityReport:
    """Combine refutation + E-value into a single robustness verdict.

    Args:
        effect: Point estimate.
        confidence_interval: 95% CI (optional).
        refutation_results: Pass/fail dict from DoWhy refuters (optional).
        outcome_sd: Outcome SD for continuous → RR conversion.
        scale: ``"continuous"`` or ``"risk_ratio"``.
        min_e_value: Minimum acceptable point E-value. Below this we judge
            the result vulnerable to plausible unobserved confounding.
        require_all_refutations: When True, partial refutation counts as
            failure. Default False (partial counts as warning).
    """
    e_point, e_ci = compute_e_value(
        effect=effect,
        confidence_interval=confidence_interval,
        outcome_sd=outcome_sd,
        scale=scale,
    )
    passed, total, status = summarize_refutations(refutation_results)

    reasons: list[str] = []
    robust = True

    if status == "skipped":
        robust = False
        reasons.append("no refutation tests were executed")
    elif status == "failed":
        robust = False
        reasons.append(f"all {total} refutation tests failed")
    elif status == "partial":
        msg = f"only {passed}/{total} refutation tests passed"
        reasons.append(msg)
        if require_all_refutations:
            robust = False

    if e_point is None:
        robust = False
        reasons.append("e-value could not be computed (non-finite estimate)")
    elif e_point < min_e_value:
        robust = False
        reasons.append(
            f"e-value {e_point:.2f} below minimum {min_e_value:.2f} — "
            "a modest unobserved confounder could explain this effect away"
        )

    if e_ci is not None and e_ci <= 1.0:
        # Only treat as a hard failure when the CI itself crosses null;
        # otherwise it's already captured by e_point.
        if confidence_interval is not None:
            lo, hi = confidence_interval
            if math.isfinite(lo) and math.isfinite(hi) and lo <= 0 <= hi:
                robust = False
                reasons.append("confidence interval crosses the null")

    return SensitivityReport(
        e_value=e_point,
        e_value_ci=e_ci,
        refutations_passed=passed,
        refutations_total=total,
        refutation_status=status,
        robust=robust,
        reasons=tuple(reasons),
    )


def aggregate_pass_rate(reports: Iterable[SensitivityReport]) -> float:
    """Helper for benchmark dashboards: fraction of robust reports."""
    reports = list(reports)
    if not reports:
        return 0.0
    return sum(1 for r in reports if r.robust) / len(reports)
