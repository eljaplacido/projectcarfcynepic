"""Experiment #8 — every causal implementation, one corpus, one known answer.

SE6, SE7 and CI7 were established with sklearn stand-ins. That made them
statements about the *logic* of a tiered architecture. This makes them
statements about **these implementations**, by running the ones actually shipped
over the same 500 items with the same ground truth.

Three implementations are compared:

    cynepic-causal   the Rust crate. OLS-adjusted, IPW (cross-fitted by
                     default), and ATT. Run separately on GX10 via
                     `cargo run -p cynepic-causal --example c2_report`; its
                     output is read here rather than re-derived, so the number
                     in this table is the number the crate emitted.

    CARF engine      the Python service in `src.services.causal`, which wraps
                     DoWhy. This is what the product calls.

    sklearn          the T-learner used to establish SE6/SE7/CI7, carried
                     forward as the reference the earlier findings were built
                     on. If the shipped implementations disagree with it, those
                     findings need restating.

WHY A KNOWN ANSWER MATTERS MORE THAN AGREEMENT
==============================================

Three implementations agreeing tells you they share an assumption, not that the
assumption is right. C2's ATE is known exactly because both arms were generated,
so each implementation is scored against the truth rather than against the
others. Agreement is then a secondary reading: implementations that agree *and*
cover are corroborating; implementations that agree *and* miss are sharing a
defect.

WHAT THE NAIVE ROW IS FOR
=========================

`difference_in_means` is included and is expected to miss. C2 confounds
assignment on purpose, so an adjustment that cannot beat the naive contrast on
this corpus is not adjusting. It is the floor, not a candidate.

    python -m benchmarks.technical.escalation.benchmark_implementations_on_c2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks import finalize_benchmark_report

logger = logging.getLogger("benchmark.implementations_on_c2")

HERE = Path(__file__).parent
CORPUS = HERE.parents[1] / "corpora" / "c2_corpus.jsonl"
RUST_RESULTS = HERE / "cynepic_causal_on_c2_results.json"

TREATMENT = "treated"
OUTCOME = "y_observed"


def load_corpus() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line]


def flat_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, float]], list[str]]:
    """Flatten to the row-per-item shape the CARF engine expects."""
    covariates = sorted(records[0]["covariates"].keys())
    rows = [
        {**{k: float(r["covariates"][k]) for k in covariates},
         TREATMENT: float(r[TREATMENT]),
         OUTCOME: float(r[OUTCOME])}
        for r in records
    ]
    return rows, covariates


async def carf_estimates(rows: list[dict[str, float]], covariates: list[str]) -> list[dict[str, Any]]:
    """Run CARF's causal service over C2, once per estimation method."""
    from src.services.causal import (
        CausalEstimationConfig,
        CausalHypothesis,
        CausalInferenceEngine,
    )

    engine = CausalInferenceEngine(neo4j_service=None)
    hypothesis = CausalHypothesis(
        treatment=TREATMENT,
        outcome=OUTCOME,
        mechanism="C2 retention offer effect on retained value",
        confounders=covariates,
    )

    out: list[dict[str, Any]] = []
    for method in ("backdoor.linear_regression", "backdoor.propensity_score_weighting"):
        config = CausalEstimationConfig(
            data=rows,
            treatment=TREATMENT,
            outcome=OUTCOME,
            covariates=covariates,
            method_name=method,
        )
        try:
            result = await engine.estimate_effect(hypothesis=hypothesis, estimation_config=config)
            ci = getattr(result, "confidence_interval", None)
            out.append(
                {
                    "implementation": "CARF (DoWhy)",
                    "estimator": method,
                    "ate": float(result.effect_estimate),
                    "ci95_low": float(ci[0]) if ci else None,
                    "ci95_high": float(ci[1]) if ci else None,
                    "robust": bool(getattr(result, "robust", False)),
                    "refutation_status": getattr(result, "refutation_status", None),
                }
            )
        except Exception as exc:  # noqa: BLE001 - an engine failure is a result
            # Recorded, not swallowed. An implementation that cannot run on this
            # corpus is a finding about the implementation, and booking it as a
            # missing row would hide it.
            out.append(
                {
                    "implementation": "CARF (DoWhy)",
                    "estimator": method,
                    "ate": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            logger.warning("CARF %s failed: %s", method, exc)
    return out


def sklearn_estimate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The T-learner SE6/SE7/CI7 were established with, as an ATE."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import KFold

    covariate_keys = sorted(records[0]["covariates"].keys())
    x = np.array([[r["covariates"][k] for k in covariate_keys] for r in records])
    t = np.array([r[TREATMENT] for r in records])
    y = np.array([r[OUTCOME] for r in records])

    cate = np.full(len(records), np.nan)
    kf = KFold(n_splits=5, shuffle=True, random_state=20260925)
    for tr_idx, te_idx in kf.split(x):
        tr, ct = tr_idx[t[tr_idx] == 1], tr_idx[t[tr_idx] == 0]
        mt = GradientBoostingRegressor(random_state=20260925, n_estimators=120, max_depth=3)
        mc = GradientBoostingRegressor(random_state=20260925, n_estimators=120, max_depth=3)
        mt.fit(x[tr], y[tr])
        mc.fit(x[ct], y[ct])
        cate[te_idx] = mt.predict(x[te_idx]) - mc.predict(x[te_idx])

    ate = float(np.nanmean(cate))
    se = float(np.nanstd(cate) / np.sqrt(np.sum(~np.isnan(cate))))
    return {
        "implementation": "sklearn (reference)",
        "estimator": "t_learner_gbm_crossfit5",
        "ate": ate,
        "ci95_low": ate - 1.96 * se,
        "ci95_high": ate + 1.96 * se,
        "note": "SE of the mean CATE, not a causal standard error; shown for scale only",
    }


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    records = load_corpus()
    rows, covariates = flat_records(records)
    true_ate = float(np.mean([r["ite"] for r in records]))
    treated_mask = [r[TREATMENT] == 1 for r in records]
    true_att = float(np.mean([r["ite"] for r, m in zip(records, treated_mask) if m]))

    logger.info("=== #8: every implementation, one corpus (C2, n=%d) ===", len(records))
    logger.info("  true ATE %.5f   true ATT %.5f", true_ate, true_att)

    table: list[dict[str, Any]] = []

    # ── cynepic-causal, read from the Rust run ──
    if RUST_RESULTS.exists():
        rust = json.loads(RUST_RESULTS.read_text(encoding="utf-8"))
        for e in rust["estimates"]:
            truth = true_att if e["estimand"] == "ATT" else true_ate
            table.append(
                {
                    "implementation": "cynepic-causal (Rust)",
                    "estimator": e["estimator"],
                    "ate": e["ate"],
                    "ci95_low": e.get("ci95_low"),
                    "ci95_high": e.get("ci95_high"),
                    "estimand": e["estimand"],
                    "truth": truth,
                }
            )
    else:
        logger.warning("%s missing - run the Rust example on GX10 first", RUST_RESULTS.name)

    # ── CARF's own engine ──
    table.extend(asyncio.run(carf_estimates(rows, covariates)))

    # ── the sklearn reference SE6/SE7/CI7 were built on ──
    table.append(sklearn_estimate(records))

    # Score every row against the truth for its estimand.
    for row in table:
        truth = row.get("truth", true_ate)
        row.setdefault("estimand", "ATE")
        row["truth"] = truth
        if row.get("ate") is None:
            row["bias"] = None
            row["covers_truth"] = None
            continue
        row["bias"] = row["ate"] - truth
        lo, hi = row.get("ci95_low"), row.get("ci95_high")
        row["covers_truth"] = bool(lo is not None and hi is not None and lo <= truth <= hi)

    logger.info("")
    logger.info("  %-24s %-34s %10s %10s %8s", "implementation", "estimator", "estimate", "bias", "covers")
    for row in table:
        if row["ate"] is None:
            logger.info("  %-24s %-34s %10s %10s %8s", row["implementation"], row["estimator"],
                        "FAILED", "-", "-")
            logger.info("      %s", row.get("error"))
            continue
        logger.info("  %-24s %-34s %10.5f %+10.5f %8s", row["implementation"], row["estimator"],
                    row["ate"], row["bias"], row["covers_truth"])

    scored = [r for r in table if r["ate"] is not None]
    missed = [r for r in scored if r["covers_truth"] is False]
    logger.info("")
    logger.info("  %d of %d estimates cover the known truth; %d miss",
                len(scored) - len(missed), len(scored), len(missed))
    for r in missed:
        logger.info("    MISS  %s / %s  bias %+0.5f", r["implementation"], r["estimator"], r["bias"])

    report: dict[str, Any] = {
        "benchmark": "implementations_on_c2",
        "experiment": "#8",
        "corpus": "C2",
        "n_items": len(records),
        "true_ate": true_ate,
        "true_att": true_att,
        "results": table,
        "n_scored": len(scored),
        "n_missing_truth": len(missed),
        "methodology": (
            "Every implementation scored against C2's known ATE rather than "
            "against each other. Agreement between implementations that MISS is "
            "a shared defect, not corroboration. difference_in_means is the "
            "floor and is expected to miss on a corpus that confounds "
            "assignment deliberately."
        ),
    }
    report = finalize_benchmark_report(
        report,
        benchmark_id="implementations_on_c2",
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
    parser = argparse.ArgumentParser(description="#8: every causal implementation on C2")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    run_benchmark(args.output)


if __name__ == "__main__":
    main()
