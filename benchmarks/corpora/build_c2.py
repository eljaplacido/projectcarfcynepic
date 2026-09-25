"""C2 — the shared decision corpus, where predicting and intervening disagree.

WHY THIS CORPUS HAS TO BE BUILT RATHER THAN FOUND
=================================================

SE1 asks whether a System-1 model's *confidence* predicts whether a System-2
causal analysis would have *changed the action*. Answering it needs both answers
for the same item: what the predictor says, and what the intervention would
actually do. No observational dataset can supply the second one — that is the
entire reason interventions are hard — so the corpus is generated, and its
ground truth is true by construction rather than by estimation.

The construction is the churn case in miniature, and it is the one place where
a purely predictive system is not merely imprecise but *systematically wrong*:

    a customer with a high probability of churning is not the same as
    a customer whom an intervention would retain.

A retention team that ranks by churn probability spends its budget on two
groups it should not touch — the doomed, who leave regardless, and the safe, who
stay regardless — and misses the persuadable. Uplift modelling has known this
for decades; the point here is to make it *measurable per item*, so that
"escalate to causal analysis" can be scored as a decision rather than argued
as a principle.

WHAT IS TRUE BY CONSTRUCTION
============================

For every item both arms are generated, `y0_value` and `y1_value`. Therefore:

* the individual treatment effect `y1_value - y0_value` is known exactly;
* the segment ATE is known exactly, not estimated;
* the optimal action under a stated treatment cost is known exactly;
* "do nothing" is the right answer for a non-trivial share of items — which is
  the case a predictive ranker can never learn, because it has no representation
  of an action that is not taken.

THE DECORRELATION IS THE FIXTURE
================================

Segments are laid out on a 2x2 of (baseline risk) x (treatment effect), plus
two harm segments. Risk and effect are assigned *independently* across segments,
so across the corpus the correlation between the predictive signal and the true
effect is near zero by design. A corpus where high risk implied high uplift
would make S1 and S2 agree, SE1 would return a large |rho| for a reason that is
an artefact of the fixture, and the finding would be about the generator.

`validate.py` asserts the decorrelation actually holds in the emitted sample
rather than trusting that it holds in the parameters (V1), and anchors the
estimation machinery against LaLonde, whose experimental benchmark is published
(V2). Both must pass before the corpus is used, which is what "V1/V2 pass"
means in the programme ledger.

WHY THE OUTCOME IS CONTINUOUS
=============================

The first version of this generator used a bounded probability outcome:
retention probability, with the segment effect added to it. Validation rejected
it, and the reason is worth keeping rather than quietly fixing.

On a bounded scale a large positive effect cannot be applied to an item that is
already near the ceiling. `y0_prob + effect` clips at 1.0, and clipping bites
hardest on exactly the segment the corpus needs intact -- low baseline risk with
large uplift. The realised effect there came out at +0.227 against a declared
+0.310, and because clipping is a function of baseline risk, it re-introduced
precisely the risk/effect correlation the design exists to remove: +0.185
against a 0.15 ceiling.

That is not a tuning problem. **On a bounded outcome, risk and uplift cannot be
made independent**, because headroom is itself a function of risk. So the
outcome here is a continuous retained-value score, effects are additive and
never truncated, and the decorrelation is exact by construction rather than
approximate after clipping.

CONFOUNDING IS DELIBERATE
==========================

Treatment assignment depends on the covariates that also drive the outcome, so a
naive difference in means is biased and the causal machinery has something to
do. Without it, `do_nothing` versus `treat` would be recoverable by a group-by
and the corpus would not discriminate between S1 and S2 at all.

WHAT THIS CORPUS DOES NOT DO
============================

The question text is **templated**, and every record says so in `phrasing`.
Templated text is adequate for SE1, SE5, SE6 and SE7, which turn on the decision
and not on the wording. It is *not* adequate for SE2, which asks whether question
type is recoverable from **natural** phrasing; that needs hand-labelled items
from real tickets and prompts, and is tracked separately. Scoring SE2 on
templates would measure the templates.

Usage
-----
    python -m benchmarks.corpora.build_c2            # writes corpus + manifest
    python -m benchmarks.corpora.build_c2 --items 500
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("corpora.c2")

#: Fixed seed. The corpus is a fixture, so it must be byte-identical on every
#: machine that rebuilds it; a corpus that drifts between runs would make every
#: number computed against it unreproducible.
SEED = 20260925

#: Cost of applying the treatment, in outcome units. This is what makes
#: "do nothing" optimal for some items rather than merely tied: without a cost,
#: any positive effect justifies acting and the interesting half of the decision
#: problem disappears.
TREATMENT_COST = 0.08

#: How many covariates each item carries.
N_COVARIATES = 6


@dataclass(frozen=True)
class Segment:
    """One cell of the risk x effect design.

    `baseline_risk` drives the predictive signal; `ate` is the true average
    effect of treating. They are set independently — that independence is the
    property the whole corpus exists to have.
    """

    name: str
    baseline_risk: float
    ate: float
    share: float
    note: str


#: The design. Risk and effect are crossed rather than correlated.
#:
#: `persuadable` and `sure_thing` carry the same effect at opposite risk; `lost_cause`
#: and `safe` carry ~no effect at opposite risk. If a ranker used risk as a proxy
#: for effect it would treat `lost_cause` (wrongly) and skip `sure_thing`
#: (wrongly), which is exactly the failure this corpus is built to expose.
#:
#: The two `sleeping_dog` segments are where treating actively *harms* — the
#: case for which "do nothing" is not a tie-break but the only correct answer.
SEGMENTS: tuple[Segment, ...] = (
    Segment("persuadable_high_risk", 0.72, 0.34, 0.16,
            "high risk, large positive effect - treat"),
    Segment("persuadable_low_risk", 0.24, 0.31, 0.14,
            "low risk, large positive effect - treat, and a ranker never gets here"),
    Segment("lost_cause", 0.81, 0.02, 0.16,
            "high risk, no effect - a ranker spends its whole budget here"),
    Segment("sure_thing", 0.19, 0.01, 0.14,
            "low risk, no effect - correctly skipped by both"),
    Segment("sleeping_dog_high_risk", 0.68, -0.22, 0.10,
            "high risk, treating HARMS - the case a ranker cannot represent"),
    Segment("sleeping_dog_low_risk", 0.22, -0.18, 0.08,
            "low risk, treating harms"),
    Segment("marginal_positive", 0.50, 0.10, 0.12,
            "effect positive but near the cost line - the decision-margin case"),
    Segment("marginal_negative", 0.46, 0.05, 0.10,
            "effect positive but BELOW the cost line - do nothing is correct"),
)

#: Question templates per type. Deliberately plain: the decision, not the
#: wording, is what SE1/SE5/SE6/SE7 score.
TEMPLATES: dict[str, str] = {
    "associational": "what is the probability that customer {cid} churns this quarter",
    "interventional": "what happens to customer {cid}'s retention if we apply the offer",
    "counterfactual": "would customer {cid} have stayed if we had applied the offer",
    "decision": "should we apply the retention offer to customer {cid}",
}


def _segment_draw(rng: np.random.Generator, n: int) -> np.ndarray:
    """Assign each item to a segment, by declared share."""
    shares = np.array([s.share for s in SEGMENTS], dtype=float)
    shares = shares / shares.sum()
    return rng.choice(len(SEGMENTS), size=n, p=shares)


def build(n_items: int, seed: int = SEED) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Generate the corpus and the manifest describing how it was made."""
    rng = np.random.default_rng(seed)
    seg_idx = _segment_draw(rng, n_items)

    records: list[dict[str, Any]] = []
    for i in range(n_items):
        seg = SEGMENTS[seg_idx[i]]

        # Covariates. Two of them (x0, x1) carry the confounding: they shift
        # both the propensity to be treated and the baseline outcome, so a
        # naive contrast between treated and untreated is biased.
        x = rng.normal(0.0, 1.0, size=N_COVARIATES)

        # Baseline risk for this item: the segment level, nudged by the
        # confounders, squashed into (0, 1).
        logit = np.log(seg.baseline_risk / (1 - seg.baseline_risk))
        logit += 0.45 * x[0] + 0.30 * x[1]
        risk = float(1.0 / (1.0 + np.exp(-logit)))

        # y0: retained value without treatment, continuous. Higher churn risk
        # means less value retained. Unbounded on purpose -- see the module
        # docstring: a bounded scale makes headroom a function of risk, which
        # makes risk and uplift dependent no matter what the segment table says.
        y0_value = float(1.0 - risk + 0.05 * x[3])

        # y1: the segment effect, plus individual variation that is a function
        # of x[4] ALONE. x[4] enters nothing else, so the individual effect is
        # statistically independent of the risk score by construction rather
        # than by adjustment.
        effect = float(seg.ate + 0.05 * x[4])
        y1_value = y0_value + effect

        # Observed assignment: confounded by the same covariates that drive the
        # outcome, so the corpus rewards adjustment rather than a group-by.
        #
        # Both x0 and x1 must enter with the SAME sign they carry in the
        # outcome. An earlier version used `+0.8*x0 - 0.5*x1` while risk used
        # `+0.45*x0 + 0.30*x1`, so the two confounding paths partially cancelled
        # and the naive contrast landed within 0.013 of the true ATE -- the
        # corpus looked unconfounded to any estimator, and V1 rejected it.
        # Confounding that cancels is not weak confounding; it is a corpus that
        # cannot tell an adjusted estimate from an unadjusted one.
        propensity = float(1.0 / (1.0 + np.exp(-(0.9 * x[0] + 0.7 * x[1] + 0.15))))
        treated = int(rng.random() < propensity)
        y_obs = y1_value if treated else y0_value

        # Ground truth, all of it known because both arms were generated.
        ite = effect
        value_treat = y1_value - TREATMENT_COST
        value_nothing = y0_value
        best_action = "treat" if value_treat > value_nothing else "do_nothing"
        regret_if_treat = max(0.0, value_nothing - value_treat)
        regret_if_nothing = max(0.0, value_treat - value_nothing)

        # What a purely PREDICTIVE system does: rank by risk, treat the top.
        # It has no representation of an action not taken, so its only lever is
        # the risk score. The threshold is set at the corpus median below.
        qtype = ("decision", "interventional", "associational", "counterfactual")[i % 4]

        records.append(
            {
                "id": f"c2-{i:04d}",
                "segment": seg.name,
                "segment_note": seg.note,
                "covariates": {f"x{j}": round(float(v), 6) for j, v in enumerate(x)},
                "propensity_true": round(propensity, 6),
                "treated": treated,
                "y_observed": round(float(y_obs), 6),
                # --- ground truth, true by construction ---
                "y0_value": round(y0_value, 6),
                "y1_value": round(y1_value, 6),
                "ite": round(float(ite), 6),
                "segment_ate": seg.ate,
                "risk_score_true": round(risk, 6),
                "value_treat": round(float(value_treat), 6),
                "value_do_nothing": round(float(value_nothing), 6),
                "best_action": best_action,
                "regret_if_treat": round(float(regret_if_treat), 6),
                "regret_if_do_nothing": round(float(regret_if_nothing), 6),
                # --- question surface ---
                "question_type": qtype,
                "question": TEMPLATES[qtype].format(cid=f"c2-{i:04d}"),
                "phrasing": "templated",
            }
        )

    # Refuse rather than emit a corpus whose effects were deformed. The first
    # version deformed silently and only the validator noticed; a generator that
    # can produce a broken fixture is one that will, on some future parameter
    # change nobody re-validates.
    spread = float(np.std([r["ite"] for r in records]))
    if not np.isfinite(spread) or spread <= 0.0:
        raise ValueError("individual effects have no spread; the corpus is degenerate")

    # The S1 policy: treat everyone above the median risk. Defined over the
    # corpus rather than per item, because a ranker's threshold is a budget
    # decision and only exists relative to a population.
    risks = np.array([r["risk_score_true"] for r in records])
    threshold = float(np.median(risks))
    for r in records:
        r["s1_action"] = "treat" if r["risk_score_true"] > threshold else "do_nothing"
        r["s1_confidence"] = round(
            float(abs(r["risk_score_true"] - threshold) / max(threshold, 1e-9)), 6
        )
        r["s2_changes_action"] = int(r["s1_action"] != r["best_action"])
        r["regret_of_s1"] = round(
            float(r["regret_if_treat"] if r["s1_action"] == "treat" else r["regret_if_do_nothing"]),
            6,
        )

    manifest = {
        "corpus_id": "C2",
        "title": "Shared decision corpus: prediction vs intervention",
        "seed": seed,
        "n_items": n_items,
        "treatment_cost": TREATMENT_COST,
        "n_covariates": N_COVARIATES,
        "s1_policy": {
            "rule": "treat if true risk score > corpus median risk",
            "threshold": round(threshold, 6),
            "note": "a purely predictive ranker; it has no representation of an "
                    "action that is not taken",
        },
        "segments": [asdict(s) for s in SEGMENTS],
        "ground_truth_fields": [
            "y0_value", "y1_value", "ite", "segment_ate", "best_action",
            "value_treat", "value_do_nothing", "regret_if_treat",
            "regret_if_do_nothing", "s2_changes_action",
        ],
        "serves_hypotheses": ["SE1", "SE5", "SE6", "SE7", "CI4", "CI7"],
        "does_not_serve": {
            "SE2": "question text is templated; SE2 needs natural phrasing from "
                   "real tickets and prompts, hand-labelled by two raters",
        },
        "phrasing": "templated",
    }
    return records, manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="Build the C2 shared decision corpus")
    parser.add_argument("--items", type=int, default=500)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    records, manifest = build(args.items, args.seed)

    corpus_path = args.out_dir / "c2_corpus.jsonl"
    with open(corpus_path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    manifest_path = args.out_dir / "c2_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    n_nothing = sum(1 for r in records if r["best_action"] == "do_nothing")
    n_changed = sum(r["s2_changes_action"] for r in records)
    logger.info("C2 built: %d items -> %s", len(records), corpus_path)
    logger.info("  best action is 'do nothing' on %d of %d (%.1f%%)",
                n_nothing, len(records), 100 * n_nothing / len(records))
    logger.info("  S2 changes the action on %d of %d (%.1f%%)",
                n_changed, len(records), 100 * n_changed / len(records))
    logger.info("  manifest -> %s", manifest_path)
    logger.info("Run validate_c2.py before using it. V1/V2 must pass.")


if __name__ == "__main__":
    main()
