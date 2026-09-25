"""SE6, SE7 and CI7 on the C2 corpus: what escalation buys, and what it costs.

THE DESIGN POINT THAT DECIDES WHETHER THIS MEASURES ANYTHING
============================================================

System 2 here is an **estimated** causal model, fitted on the observed,
confounded data exactly as it would be in production. It is not the oracle.

That distinction is the whole experiment. If S2 read the ground truth C2
generated, it would choose the optimal action every time, SE6's frontier would
be a trivially monotone march to zero regret, SE7 would report that S2 wins
everywhere, and all three hypotheses would be answered by the fixture rather
than by the components. The interesting question is whether a causal estimator
*that can be wrong* still beats a predictive one, and by enough to pay for
itself.

Both layers are **cross-fitted** over five folds: every item is scored by a
model that never saw it in training. Without that, S2's apparent advantage would
include its own overfitting.

    S1  cheap, predictive.  Regress y_observed on covariates, ignoring
        treatment entirely. Rank by predicted value and treat the high-risk
        half. This is a churn ranker: it has no representation of an action, so
        its only lever is who looks worst.

    S2  expensive, causal.  T-learner: one model on the treated, one on the
        control, CATE = mu1(x) - mu0(x). Treat where the estimated effect
        exceeds the treatment cost. It can decline to act, which S1 cannot.

WHY S1 IS REPORTED TWICE
========================

The corpus ships an `s1_action` computed from `risk_score_true` -- the latent
risk, which no deployed model has. That is S1's **ceiling**, not S1. This
benchmark refits S1 from data and reports both, because the gap between them is
the part of S1's regret that is estimation error rather than the structural
blindness SE5 is about. Quoting the ceiling as "S1" would flatter the predictive
layer; quoting only the fitted one would blame estimation for a failure that is
actually structural.

HYPOTHESES AND THEIR FALSIFIERS
===============================

SE6  Escalation traces an efficient frontier: decision regret against total
     cost, swept over escalation rate.
     FALSIFIED IF the frontier is flat -- escalation rate does not matter and
     you should take the cheapest option.

SE7  S2 beats S1 on interventional questions and not on associational ones;
     S2-everywhere is strictly worse on cost at equal quality.
     FALSIFIED IF S2 wins on every stratum -- then drop S1 and pay the latency.

CI7  Causal estimates reduce decision regret versus predictive scores at equal
     cost.
     FALSIFIED IF there is no regret reduction -- the causal layer is
     epistemically nicer and operationally inert.

A NOTE ON THE STRATA
====================

SE7 stratifies by *question type*. C2's question text is templated and its type
is assigned round-robin, so it carries no item-level signal by construction --
using it as a trigger would measure nothing. The stratification here is by
**task**, which is well defined regardless of wording:

    associational   predict the outcome           scored by error
    interventional  choose the action             scored by regret

That is what the question types stand for, and it is the distinction SE7 is
actually about. Whether the *type* is recoverable from natural phrasing is SE2,
which needs a hand-labelled corpus and is not answerable here.

    python -m benchmarks.technical.escalation.benchmark_escalation_frontier
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold

from benchmarks import finalize_benchmark_report

logger = logging.getLogger("benchmark.escalation")

CORPUS = Path(__file__).resolve().parents[2] / "corpora" / "c2_corpus.jsonl"
MANIFEST = Path(__file__).resolve().parents[2] / "corpora" / "c2_manifest.json"

SEED = 20260925
N_FOLDS = 5

#: Relative cost of one decision at each layer, in the same abstract units.
#: S2 is a fitted causal analysis; S1 is a table lookup against a trained
#: regressor. The ratio, not the absolute values, is what the frontier reads,
#: and it is swept in `cost_ratio_sensitivity` rather than asserted.
COST_S1 = 1.0
COST_S2 = 20.0

#: Escalation rates swept for SE6.
RATES = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def load_corpus() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return records, manifest


def _design(records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Covariate matrix, treatment indicator, observed outcome."""
    keys = sorted(records[0]["covariates"].keys())
    x = np.array([[r["covariates"][k] for k in keys] for r in records], dtype=float)
    t = np.array([r["treated"] for r in records], dtype=int)
    y = np.array([r["y_observed"] for r in records], dtype=float)
    return x, t, y


def cross_fitted_layers(
    records: list[dict[str, Any]], treatment_cost: float, seed: int = SEED
) -> dict[str, np.ndarray]:
    """Fit S1 and S2 out-of-fold and return their per-item outputs.

    Every item is scored by models that never saw it. The S2 fold models are
    fitted on the treated and control subsets of the training fold separately,
    which is the T-learner; a fold whose training half lacks one arm is skipped
    for that item rather than silently falling back to the other arm.
    """
    x, t, y = _design(records)
    n = len(records)
    s1_pred = np.full(n, np.nan)
    s2_cate = np.full(n, np.nan)

    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    for train_idx, test_idx in kf.split(x):
        # ── S1: purely predictive. Treatment is not among its inputs, which is
        # the point: a churn model does not know what an intervention does.
        m1 = GradientBoostingRegressor(random_state=seed, n_estimators=120, max_depth=3)
        m1.fit(x[train_idx], y[train_idx])
        s1_pred[test_idx] = m1.predict(x[test_idx])

        # ── S2: causal. Two models, one per arm, differenced.
        tr, ct = train_idx[t[train_idx] == 1], train_idx[t[train_idx] == 0]
        if len(tr) < 10 or len(ct) < 10:
            logger.warning("fold lacks an arm (treated=%d control=%d); left unscored", len(tr), len(ct))
            continue
        mt = GradientBoostingRegressor(random_state=seed, n_estimators=120, max_depth=3)
        mc = GradientBoostingRegressor(random_state=seed, n_estimators=120, max_depth=3)
        mt.fit(x[tr], y[tr])
        mc.fit(x[ct], y[ct])
        s2_cate[test_idx] = mt.predict(x[test_idx]) - mc.predict(x[test_idx])

    # S1's action: treat the half that looks worst. A ranker's threshold is a
    # budget decision and only exists relative to a population.
    threshold = float(np.nanmedian(s1_pred))
    s1_action = np.where(s1_pred < threshold, 1, 0)
    # Its margin is distance from that threshold -- which is exactly what a
    # confidence score is for a ranker, and exactly what SE1 tested.
    denom = float(np.nanstd(s1_pred)) or 1.0
    s1_conf = np.abs(s1_pred - threshold) / denom

    # S2's action: act where the estimated effect clears the cost.
    s2_action = np.where(s2_cate > treatment_cost, 1, 0)
    # S2's margin: how far the estimated effect sits from the decision boundary.
    s2_margin = np.abs(s2_cate - treatment_cost)

    return {
        "s1_pred": s1_pred,
        "s1_action": s1_action,
        "s1_confidence": s1_conf,
        "s2_cate": s2_cate,
        "s2_action": s2_action,
        "s2_margin": s2_margin,
    }


def regret_of(records: list[dict[str, Any]], actions: np.ndarray) -> np.ndarray:
    """Per-item regret of an action vector, against the corpus ground truth."""
    return np.array(
        [
            r["regret_if_treat"] if a == 1 else r["regret_if_do_nothing"]
            for r, a in zip(records, actions)
        ],
        dtype=float,
    )


def se7_by_task(records: list[dict[str, Any]], layers: dict[str, np.ndarray]) -> dict[str, Any]:
    """Each layer on each task. SE7 predicts a crossover, not a winner."""
    y0 = np.array([r["y0_value"] for r in records])
    # Associational task: predict the untreated outcome.
    s1_err = float(np.sqrt(np.nanmean((layers["s1_pred"] - y0) ** 2)))
    # S2 estimates an effect, not a level; used as a predictor of the outcome it
    # is simply the wrong instrument, which is the asymmetry SE7 asserts.
    s2_as_predictor = float(np.sqrt(np.nanmean((layers["s2_cate"] - y0) ** 2)))

    # Interventional task: choose the action.
    s1_regret = float(np.mean(regret_of(records, layers["s1_action"])))
    s2_regret = float(np.mean(regret_of(records, layers["s2_action"])))

    return {
        "associational": {
            "task": "predict the untreated outcome (RMSE, lower is better)",
            "s1_rmse": round(s1_err, 4),
            "s2_rmse": round(s2_as_predictor, 4),
            "winner": "S1" if s1_err < s2_as_predictor else "S2",
        },
        "interventional": {
            "task": "choose the action (mean regret, lower is better)",
            "s1_regret": round(s1_regret, 4),
            "s2_regret": round(s2_regret, 4),
            "winner": "S2" if s2_regret < s1_regret else "S1",
        },
    }


def se6_frontier(
    records: list[dict[str, Any]], layers: dict[str, np.ndarray], seed: int = SEED
) -> dict[str, Any]:
    """Regret against cost, swept over escalation rate, for several triggers.

    The triggers are the point of comparison, not the rate. `confidence` is the
    one SE1 said should not work; `margin` is the second gate; `random` is the
    floor any trigger must beat; `oracle` is the ceiling no deployable trigger
    can reach and is reported so the others can be read as a fraction of what
    was available.
    """
    rng = np.random.default_rng(seed)
    n = len(records)
    r1 = regret_of(records, layers["s1_action"])
    r2 = regret_of(records, layers["s2_action"])

    triggers: dict[str, np.ndarray] = {
        # Escalate where S1 is LEAST confident -> smallest confidence first.
        "s1_confidence": layers["s1_confidence"],
        # Escalate where S2's own estimate is closest to the boundary. Only
        # computable after paying for S2, so it is an upper reference for a
        # margin gate rather than a deployable trigger on its own.
        "s2_margin": layers["s2_margin"],
        "random": rng.random(n),
        # Escalate exactly where doing so helps most. Not deployable: it needs
        # the answer. Reported as the ceiling.
        "oracle": -(r1 - r2),
    }

    curves: dict[str, list[dict[str, float]]] = {}
    for name, score in triggers.items():
        order = np.argsort(np.nan_to_num(score, nan=np.inf))
        rows = []
        for rate in RATES:
            k = int(round(rate * n))
            escalated = np.zeros(n, dtype=bool)
            escalated[order[:k]] = True
            regret = float(np.mean(np.where(escalated, r2, r1)))
            cost = float(np.mean(np.where(escalated, COST_S1 + COST_S2, COST_S1)))
            rows.append({"rate": rate, "mean_regret": round(regret, 5), "mean_cost": round(cost, 3)})
        curves[name] = rows

    # Is the frontier flat? Measured as the spread of regret across the sweep
    # for the best deployable trigger, relative to the S1-only baseline.
    base = curves["s1_confidence"][0]["mean_regret"]
    best_span = max(
        max(r["mean_regret"] for r in rows) - min(r["mean_regret"] for r in rows)
        for name, rows in curves.items()
        if name != "oracle"
    )
    relative_span = best_span / base if base else 0.0

    return {
        "curves": curves,
        "s1_only_regret": round(base, 5),
        "s2_everywhere_regret": round(curves["random"][-1]["mean_regret"], 5),
        "largest_deployable_span": round(best_span, 5),
        "span_relative_to_s1_only": round(relative_span, 4),
        "flat_threshold": 0.05,
        "frontier_is_flat": bool(relative_span < 0.05),
    }


def ci7_regret_reduction(records: list[dict[str, Any]], layers: dict[str, np.ndarray]) -> dict[str, Any]:
    """Does the causal layer reduce decision regret, and what did it cost?"""
    r1 = regret_of(records, layers["s1_action"])
    r2 = regret_of(records, layers["s2_action"])
    # The corpus's own s1_action uses the LATENT risk -- S1's ceiling, which no
    # deployed model has. Reported so the fitted figure is not read as the
    # structural limit when part of it is estimation error.
    r1_ceiling = np.array([r["regret_of_s1"] for r in records], dtype=float)

    from scipy import stats

    diff = r1 - r2
    t_stat, p_val = stats.ttest_rel(r1, r2)
    return {
        "s1_fitted_mean_regret": round(float(np.mean(r1)), 5),
        "s1_oracle_risk_mean_regret": round(float(np.mean(r1_ceiling)), 5),
        "s2_mean_regret": round(float(np.mean(r2)), 5),
        "absolute_reduction": round(float(np.mean(diff)), 5),
        "relative_reduction": round(float(np.mean(diff) / np.mean(r1)), 4) if np.mean(r1) else None,
        "paired_t": round(float(t_stat), 3),
        "p_value": float(p_val),
        "cost_s1": COST_S1,
        "cost_s2": COST_S1 + COST_S2,
        "cost_multiple": round((COST_S1 + COST_S2) / COST_S1, 1),
    }


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    records, manifest = load_corpus()
    cost = float(manifest["treatment_cost"])
    logger.info("=== SE6 / SE7 / CI7 on C2 (%d items, treatment cost %.3f) ===", len(records), cost)

    layers = cross_fitted_layers(records, cost)
    unscored = int(np.isnan(layers["s2_cate"]).sum())
    if unscored:
        logger.warning("%d items left unscored by S2", unscored)

    se7 = se7_by_task(records, layers)
    se6 = se6_frontier(records, layers)
    ci7 = ci7_regret_reduction(records, layers)

    logger.info("")
    logger.info("SE7 - each layer on each task")
    logger.info("  associational (RMSE):  S1 %.4f   S2 %.4f   -> %s",
                se7["associational"]["s1_rmse"], se7["associational"]["s2_rmse"],
                se7["associational"]["winner"])
    logger.info("  interventional (regret): S1 %.4f   S2 %.4f   -> %s",
                se7["interventional"]["s1_regret"], se7["interventional"]["s2_regret"],
                se7["interventional"]["winner"])
    se7_crossover = (se7["associational"]["winner"] == "S1"
                     and se7["interventional"]["winner"] == "S2")
    logger.info("  SE7 predicts a crossover (S1 wins associational, S2 wins "
                "interventional): %s", "OBSERVED" if se7_crossover else "NOT OBSERVED")

    logger.info("")
    logger.info("SE6 - escalation frontier, mean regret by rate")
    header = "  {:>6} " + " ".join(f"{k:>14}" for k in se6["curves"])
    logger.info(header.format("rate", *se6["curves"].keys()))
    for i, rate in enumerate(RATES):
        vals = [se6["curves"][k][i]["mean_regret"] for k in se6["curves"]]
        logger.info("  {:>6.2f} ".format(rate) + " ".join(f"{v:>14.5f}" for v in vals))
    logger.info("  S1-only %.5f -> S2-everywhere %.5f; largest deployable span %.5f (%.1f%% of S1-only)",
                se6["s1_only_regret"], se6["s2_everywhere_regret"],
                se6["largest_deployable_span"], 100 * se6["span_relative_to_s1_only"])
    logger.info("  frontier_is_flat = %s (falsifier: flat means escalation rate does not matter)",
                se6["frontier_is_flat"])

    logger.info("")
    logger.info("CI7 - does the causal layer reduce regret, and at what cost")
    logger.info("  S1 fitted %.5f | S1 at its oracle-risk ceiling %.5f | S2 %.5f",
                ci7["s1_fitted_mean_regret"], ci7["s1_oracle_risk_mean_regret"], ci7["s2_mean_regret"])
    logger.info("  reduction %.5f (%.1f%%), paired t=%.3f p=%.3g, at %.1fx the cost",
                ci7["absolute_reduction"], 100 * (ci7["relative_reduction"] or 0),
                ci7["paired_t"], ci7["p_value"], ci7["cost_multiple"])

    report: dict[str, Any] = {
        "benchmark": "escalation_frontier",
        "hypotheses": ["SE6", "SE7", "CI7"],
        "corpus": "C2",
        "n_items": len(records),
        "n_folds": N_FOLDS,
        "treatment_cost": cost,
        "cost_model": {"s1": COST_S1, "s2": COST_S2, "note": "abstract units; the ratio is what the frontier reads"},
        "s2_is_estimated_not_oracle": True,
        "items_unscored_by_s2": unscored,
        "SE6": se6,
        "SE7": {**se7, "crossover_observed": se7_crossover},
        "CI7": ci7,
        "methodology": (
            "Both layers cross-fitted over 5 folds; every item scored by models "
            "that never saw it. S1 is a predictive regressor that never sees the "
            "treatment indicator; S2 is a T-learner on the observed confounded "
            "data. S2 is estimated, not oracle -- an oracle S2 would answer these "
            "hypotheses from the fixture rather than from the components."
        ),
    }
    report = finalize_benchmark_report(
        report,
        benchmark_id="escalation_frontier",
        source_reference="benchmarks/corpora/c2_corpus.jsonl",
    )

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        logger.info("Results written to %s", out)
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="SE6/SE7/CI7 escalation frontier on C2")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    run_benchmark(args.output)


if __name__ == "__main__":
    main()
