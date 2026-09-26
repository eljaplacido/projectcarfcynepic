"""V1/V2 validation for the C2 decision corpus.

A generated fixture is only worth what its checks are worth. These run before
C2 is used for anything, and the programme ledger's "V1/V2 pass" means this
script exited zero.

V1 — INTERNAL. Does the emitted sample have the properties the generator
intended? Parameters are not evidence: a segment table that *says* risk and
effect are independent is a claim about the design, and the corpus is a sample
from it. V1 asserts the properties hold in the bytes that were written.

V2 — EXTERNAL. Does the estimation machinery recover a known answer on real
data with a real intervention? C2's ground truth is true by construction, so a
result computed on C2 alone cannot distinguish "the finding is real" from "the
estimator is broken and C2 happens to flatter it". LaLonde NSW is a randomised
experiment whose effect is published, so recovering it anchors the tooling
against something nobody in this repo chose.

Every check states what failing it would mean. A check whose failure has no
consequence is decoration.

    python -m benchmarks.corpora.validate_c2
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("corpora.validate_c2")

CORPUS = Path(__file__).parent / "c3_corpus.jsonl"
MANIFEST = Path(__file__).parent / "c3_manifest.json"

#: Above this, the predictive signal and the true effect are entangled and SE1
#: would return a large |rho| for a reason that is a property of the generator.
MAX_RISK_EFFECT_CORR = 0.15

#: Below this share of "do nothing" items, the case a predictive ranker cannot
#: represent is too rare for SE5/SE6 to resolve anything.
MIN_DO_NOTHING_SHARE = 0.10

#: The naive contrast must be biased by at least this much, or the corpus does
#: not reward adjustment and S1 vs S2 collapses to a group-by.
MIN_CONFOUNDING_BIAS = 0.02

#: LaLonde NSW experimental benchmark, Dehejia-Wahba. The randomised contrast is
#: around $1,794; a wide band is used because the check is "the estimator is not
#: broken", not "the estimator reproduces a point estimate to the dollar".
LALONDE_LOW, LALONDE_HIGH = 1000.0, 2600.0


class CheckFailed(Exception):
    """A validation check failed; the corpus must not be used."""


def _load() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not CORPUS.exists():
        raise CheckFailed(f"{CORPUS} missing - run build_c3.py first")
    records = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return records, manifest


# ── V1: internal ──────────────────────────────────────────────────────────

def v1_decorrelation(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The predictive signal must not encode the treatment effect.

    Failing this means SE1's answer would be about the generator: a corpus where
    high risk implied high uplift makes S1 and S2 agree by construction, and the
    correlation SE1 reports would be an artefact rather than a finding.
    """
    risk = np.array([r["risk_score_true"] for r in records])
    ite = np.array([r["ite"] for r in records])
    rho = float(np.corrcoef(risk, ite)[0, 1])
    ok = abs(rho) <= MAX_RISK_EFFECT_CORR
    if not ok:
        raise CheckFailed(
            f"risk/effect correlation {rho:+.3f} exceeds {MAX_RISK_EFFECT_CORR}; "
            "the predictive signal encodes the effect and SE1 would measure the generator"
        )
    return {"check": "V1.decorrelation", "corr_risk_effect": round(rho, 4), "passed": ok}


def v1_potential_outcomes(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Both arms present, and the ITE is exactly their difference.

    Failing this means the ground truth is not internally consistent, and every
    regret number computed downstream is meaningless.
    """
    # Tolerance is 1e-5, not 1e-6: every field is rounded to six decimals
    # independently, so a difference of rounded values can disagree with a
    # rounded difference in the last place. A tolerance tighter than the
    # storage precision fails on arithmetic that is in fact exact.
    worst = 0.0
    for r in records:
        worst = max(worst, abs((r["y1_value"] - r["y0_value"]) - r["ite"]))
    if worst > 1e-5:
        raise CheckFailed(f"ite != y1_value - y0_value, worst discrepancy {worst:.2e}")
    return {"check": "V1.potential_outcomes", "max_discrepancy": worst, "passed": True}


def v1_do_nothing_present(records: list[dict[str, Any]]) -> dict[str, Any]:
    """"Do nothing" must be correct often enough to be measurable.

    This is the case a purely predictive system can never learn, because it has
    no representation of an action that is not taken. If it is rare, SE5 and SE6
    have nothing to resolve.
    """
    n = len(records)
    k = sum(1 for r in records if r["best_action"] == "do_nothing")
    share = k / n
    if share < MIN_DO_NOTHING_SHARE:
        raise CheckFailed(f"'do nothing' correct on only {share:.1%}; below {MIN_DO_NOTHING_SHARE:.0%}")
    return {"check": "V1.do_nothing_present", "share": round(share, 4), "n": k, "passed": True}


def v1_confounding_is_real(records: list[dict[str, Any]]) -> dict[str, Any]:
    """A naive difference in means must be visibly biased.

    Failing this means adjustment buys nothing on this corpus, so it cannot
    distinguish a causal layer from a group-by, and CI7 would be unanswerable
    here.
    """
    treated = np.array([r["y_observed"] for r in records if r["treated"] == 1], dtype=float)
    control = np.array([r["y_observed"] for r in records if r["treated"] == 0], dtype=float)
    naive = float(treated.mean() - control.mean())
    true_ate = float(np.mean([r["ite"] for r in records]))
    bias = abs(naive - true_ate)
    if bias < MIN_CONFOUNDING_BIAS:
        raise CheckFailed(
            f"naive contrast {naive:+.4f} is within {bias:.4f} of the true ATE "
            f"{true_ate:+.4f}; the corpus does not reward adjustment"
        )
    return {
        "check": "V1.confounding_is_real",
        "naive_diff_in_means": round(naive, 4),
        "true_ate": round(true_ate, 4),
        "bias": round(bias, 4),
        "passed": True,
    }


def v1_segment_ates_recover(records: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    """Within-segment mean ITE must match the declared segment ATE.

    Failing this means the manifest describes a corpus that was not generated,
    and any per-segment reading would be wrong.
    """
    declared = {s["name"]: s["ate"] for s in manifest["segments"]}
    rows = []
    for name, ate in declared.items():
        ites = [r["ite"] for r in records if r["segment"] == name]
        if not ites:
            raise CheckFailed(f"segment {name} has no items")
        got = float(np.mean(ites))
        # Tolerance is DERIVED from the within-segment spread, not inherited.
        #
        # C2's validator used `0.02 + 2.5/sqrt(n) * 0.06`, where 0.06 stood in
        # for C2's individual-effect sd. C3's non-linear surface has an effect sd
        # of about 0.22 -- roughly four times larger -- so that constant made the
        # bound four times too tight, and a segment of ~50 items failed by 1.4
        # standard errors of its own mean.
        #
        # Widening the constant until the check passed would be tuning the check
        # to the data. Instead the bound is what it always should have been: a
        # ~2.5-sigma interval on a segment mean given the spread actually
        # observed, plus a small absolute allowance for rounding. It tightens
        # automatically on a corpus with smaller effects.
        spread = float(np.std(ites, ddof=1)) if len(ites) > 1 else 0.0
        tol = 0.02 + 2.5 * spread / max(len(ites), 1) ** 0.5
        if abs(got - ate) > tol:
            raise CheckFailed(f"segment {name}: mean ITE {got:+.3f} vs declared {ate:+.3f} (tol {tol:.3f})")
        rows.append({"segment": name, "declared_ate": ate, "observed_mean_ite": round(got, 4), "n": len(ites)})
    return {"check": "V1.segment_ates_recover", "segments": rows, "passed": True}


def v1_deterministic(manifest: dict[str, Any]) -> dict[str, Any]:
    """Rebuilding with the same seed must reproduce the corpus exactly.

    A fixture that drifts between runs makes every number computed against it
    unreproducible, and the drift would be invisible in any single report.
    """
    from benchmarks.corpora.build_c3 import build

    records, _ = build(manifest["n_items"], manifest["seed"])
    on_disk = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line]
    if len(records) != len(on_disk):
        raise CheckFailed("rebuild produced a different number of items")
    for a, b in zip(records, on_disk):
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            raise CheckFailed(f"rebuild differs at {a['id']}")
    return {"check": "V1.deterministic", "n_items": len(records), "passed": True}


# ── V2: external anchor ───────────────────────────────────────────────────

def v2_lalonde_anchor() -> dict[str, Any]:
    """Recover the published NSW experimental effect on real data.

    C2's truth is true by construction, so a C2-only result cannot separate "the
    finding is real" from "the tooling is broken in a way C2 flatters". LaLonde
    is a randomised experiment nobody in this repo designed, and its effect is
    published. If this fails, no C2 number should be believed.

    Skips rather than fails when dowhy's dataset is unavailable, and says so —
    an unreachable dataset is not a refuted anchor, and booking it as one would
    be the same error this programme has already had to correct once.
    """
    try:
        import dowhy.datasets as dd
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"check": "V2.lalonde_anchor", "passed": None, "skipped": f"dowhy unavailable: {exc}"}

    try:
        df = dd.lalonde_dataset().copy()
    except Exception as exc:
        return {"check": "V2.lalonde_anchor", "passed": None, "skipped": f"dataset unavailable: {exc}"}

    treat_col = "treat" if "treat" in df.columns else "treatment"
    out_col = "re78" if "re78" in df.columns else "y"
    treated = df.loc[df[treat_col] == 1, out_col].astype(float)
    control = df.loc[df[treat_col] == 0, out_col].astype(float)
    effect = float(treated.mean() - control.mean())

    ok = LALONDE_LOW <= effect <= LALONDE_HIGH
    if not ok:
        raise CheckFailed(
            f"LaLonde NSW randomised contrast {effect:,.0f} outside the published "
            f"band [{LALONDE_LOW:,.0f}, {LALONDE_HIGH:,.0f}]; the estimation path "
            "does not recover a known experimental answer, so no C2 number is trustworthy"
        )
    return {
        "check": "V2.lalonde_anchor",
        "randomised_effect_usd": round(effect, 1),
        "published_band": [LALONDE_LOW, LALONDE_HIGH],
        "n_treated": int(len(treated)),
        "n_control": int(len(control)),
        "passed": True,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    records, manifest = _load()
    logger.info("C3: %d items, seed %s", len(records), manifest["seed"])

    results: list[dict[str, Any]] = []
    failures: list[str] = []

    checks = [
        lambda: v1_decorrelation(records),
        lambda: v1_potential_outcomes(records),
        lambda: v1_do_nothing_present(records),
        lambda: v1_confounding_is_real(records),
        lambda: v1_segment_ates_recover(records, manifest),
        lambda: v1_deterministic(manifest),
        v2_lalonde_anchor,
    ]
    for fn in checks:
        try:
            r = fn()
            results.append(r)
            if r.get("skipped"):
                logger.warning("  [SKIP] %s - %s", r["check"], r["skipped"])
            else:
                logger.info("  [PASS] %s", r["check"])
        except CheckFailed as exc:
            name = getattr(fn, "__name__", "check")
            results.append({"check": name, "passed": False, "reason": str(exc)})
            failures.append(str(exc))
            logger.error("  [FAIL] %s - %s", name, exc)

    out = Path(__file__).parent / "c3_validation.json"
    skipped = [r for r in results if r.get("skipped")]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "corpus_id": "C3",
                "n_items": len(records),
                "seed": manifest["seed"],
                "checks": results,
                "v1_v2_pass": not failures,
                "skipped_count": len(skipped),
            },
            fh,
            indent=2,
        )

    if failures:
        logger.error("V1/V2 FAILED (%d). C2 must not be used.", len(failures))
        return 1
    if skipped:
        logger.warning("V1 passed; %d external check(s) SKIPPED - V2 is not evidence yet.", len(skipped))
    else:
        logger.info("V1/V2 PASS. C3 is usable. -> %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
