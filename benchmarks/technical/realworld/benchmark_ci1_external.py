"""CI1 — is `cynepic-causal` within tolerance of DoWhy and EconML on external data?

Every causal comparison in this programme so far has run on C2, a corpus this
project generated. Agreement there shows the implementations share an
assumption; it cannot show the assumption is right, because the data was built
to match it.

IHDP is not ours. It is the standard semi-synthetic benchmark for heterogeneous
treatment effects — real covariates from the Infant Health and Development
Program, outcomes simulated so that **both potential outcomes are known**.
That gives an exact ATE and an exact per-unit effect, on covariates nobody here
chose.

    CI1  cynepic-causal ATE is within tolerance of DoWhy/EconML on external data.
         FALSIFIED IF systematically worse eps_ATE / PEHE -> use DoWhy, and keep
         the crate for embedding only.

WHAT IS COMPARED, AND ON WHAT
=============================

    eps_ATE   |estimated ATE - true ATE|. What an estimator gets right on
              average. All three implementations produce this.

    PEHE      root mean squared error of the per-unit effect. Only the
              CATE-capable estimators produce this; an ATE-only estimator has
              no per-unit answer and is recorded as absent rather than as a
              large number.

Averaged over several IHDP replicates, because a single replicate is one draw
and the spread between replicates is large enough to reorder methods.

THE RUST ARM RUNS AS ITSELF
===========================

`cynepic-causal` is invoked through its own `c2_report` example over SSH, on a
JSONL export of the same rows the Python estimators see. It is not
reimplemented here. If the export or the transport fails the arm is recorded
ABSENT with its reason -- never as a zero, which is the failure this programme
has now hit three times.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("benchmark.ci1")

GX10_REPO = "~/Desktop/causalrust/causalrust"


def load_replicate(rep: int) -> dict[str, np.ndarray] | None:
    """One IHDP replicate with both potential outcomes."""
    from benchmarks.technical.realworld.benchmark_ihdp import load_ihdp

    loaded = load_ihdp(replicate=rep)
    if loaded is None:
        return None
    # The loader hands back (frame, true_ite): the per-unit effects live
    # OUTSIDE the frame, which is why looking for mu0/mu1 among its columns
    # found nothing and skipped every replicate on the first attempt.
    df, true_ite = loaded
    ite = np.asarray(true_ite, dtype=float)
    cols = list(df.columns)

    def pick(*names):
        for n in names:
            if n in cols:
                return np.asarray(df[n], dtype=float)
        return None

    t = pick("treatment", "treat", "t")
    y = pick("y_factual", "y", "outcome")
    if t is None or y is None:
        logger.warning("replicate %d: no treatment/outcome column in %s", rep, cols)
        return None

    # Both arms, recovered exactly from the factual outcome and the known
    # effect: y0 = y - t*ite, y1 = y0 + ite. No estimation involved.
    mu0 = y - t * ite
    mu1 = mu0 + ite

    xcols = [c for c in cols if c not in {"treatment", "treat", "t",
                                          "y_factual", "y", "outcome"}]
    x = np.asarray(df[xcols], dtype=float)
    return {"x": x, "t": t, "y": y, "mu0": mu0, "mu1": mu1, "ite": ite}


def python_estimators(d: dict[str, np.ndarray]) -> dict[str, dict[str, float | None]]:
    """DoWhy and EconML on the same rows."""
    import pandas as pd

    out: dict[str, dict[str, float | None]] = {}
    x, t, y = d["x"], d["t"], d["y"]
    true_ate = float(np.mean(d["ite"]))
    cols = [f"x{i}" for i in range(x.shape[1])]
    frame = pd.DataFrame(x, columns=cols)
    frame["treatment"] = t
    frame["y"] = y

    # ── DoWhy, backdoor linear regression ──
    try:
        from dowhy import CausalModel

        model = CausalModel(data=frame, treatment="treatment", outcome="y", common_causes=cols)
        est = model.estimate_effect(
            model.identify_effect(proceed_when_unidentifiable=True),
            method_name="backdoor.linear_regression",
        )
        ate = float(est.value)
        out["dowhy_linear"] = {"ate": ate, "eps_ate": abs(ate - true_ate), "pehe": None}
    except Exception as exc:  # noqa: BLE001
        out["dowhy_linear"] = {"ate": None, "error": f"{type(exc).__name__}: {exc}"}

    # ── EconML causal forest, which does produce per-unit effects ──
    try:
        from econml.dml import CausalForestDML
        from sklearn.ensemble import RandomForestRegressor

        cf = CausalForestDML(
            model_y=RandomForestRegressor(n_estimators=100, random_state=0),
            model_t=RandomForestRegressor(n_estimators=100, random_state=0),
            discrete_treatment=True,
            random_state=0,
        )
        cf.fit(y, t, X=x)
        cate = np.asarray(cf.effect(x)).ravel()
        ate = float(np.mean(cate))
        out["econml_causal_forest"] = {
            "ate": ate,
            "eps_ate": abs(ate - true_ate),
            "pehe": float(np.sqrt(np.mean((cate - d["ite"]) ** 2))),
        }
    except Exception as exc:  # noqa: BLE001
        out["econml_causal_forest"] = {"ate": None, "error": f"{type(exc).__name__}: {exc}"}

    return out


def rust_estimators(d: dict[str, np.ndarray], rep: int) -> dict[str, dict[str, Any]]:
    """`cynepic-causal` on the same rows, through its own example binary."""
    rows = []
    for i in range(len(d["t"])):
        rows.append({
            "covariates": {f"x{j}": float(v) for j, v in enumerate(d["x"][i])},
            "treated": int(d["t"][i]),
            "y_observed": float(d["y"][i]),
            "y0_value": float(d["mu0"][i]),
            "y1_value": float(d["mu1"][i]),
            "ite": float(d["ite"][i]),
        })
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
        local = fh.name

    remote = f"/tmp/ihdp_rep{rep}.jsonl"
    try:
        subprocess.run(["scp", "-q", local, f"gx10:{remote}"], check=True, timeout=180)
        proc = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "gx10",
             f"export PATH=$HOME/.cargo/bin:$PATH; cd {GX10_REPO} && "
             f"cargo run -q -p cynepic-causal --example c2_report -- {remote}"],
            capture_output=True, text=True, timeout=900,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {"_absent": {"reason": f"rust arm exit {proc.returncode}: {proc.stderr[:200]}"}}
        report = json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"_absent": {"reason": f"{type(exc).__name__}: {exc}"}}

    true_ate = float(np.mean(d["ite"]))
    out: dict[str, dict[str, Any]] = {}
    for e in report["estimates"]:
        if e["estimand"] != "ATE":
            continue
        out[f"cynepic_{e['estimator']}"] = {
            "ate": e["ate"],
            "eps_ate": abs(e["ate"] - true_ate),
            # The crate's estimators are ATE-only; PEHE is not something they
            # claim, so it is absent rather than penalised.
            "pehe": None,
        }
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="CI1: cynepic-causal vs DoWhy/EconML on IHDP")
    ap.add_argument("--replicates", type=int, default=5)
    ap.add_argument("-o", "--output", default=str(Path(__file__).with_name("benchmark_ci1_external_results.json")))
    args = ap.parse_args()

    per_rep: list[dict[str, Any]] = []
    for rep in range(1, args.replicates + 1):
        d = load_replicate(rep)
        if d is None:
            logger.warning("replicate %d unavailable; skipped", rep)
            continue
        true_ate = float(np.mean(d["ite"]))
        logger.info("replicate %d: n=%d p=%d true ATE=%.4f", rep, len(d["t"]), d["x"].shape[1], true_ate)
        row: dict[str, Any] = {"replicate": rep, "n": int(len(d["t"])), "true_ate": true_ate}
        row.update(python_estimators(d))
        row.update(rust_estimators(d, rep))
        per_rep.append(row)

    if not per_rep:
        logger.error("no replicates loaded; CI1 is ABSENT, not zero")
        Path(args.output).write_text(json.dumps(
            {"benchmark": "ci1_external", "ran": False,
             "reason": "no IHDP replicate could be loaded (network?)"}, indent=2), encoding="utf-8")
        return

    methods = sorted({k for r in per_rep for k in r
                      if k not in {"replicate", "n", "true_ate"} and not k.startswith("_")})
    summary = {}
    for m in methods:
        eps = [r[m]["eps_ate"] for r in per_rep if m in r and r[m].get("eps_ate") is not None]
        peh = [r[m]["pehe"] for r in per_rep if m in r and r[m].get("pehe") is not None]
        summary[m] = {
            "replicates_scored": len(eps),
            "mean_eps_ate": round(float(np.mean(eps)), 4) if eps else None,
            "mean_pehe": round(float(np.mean(peh)), 4) if peh else None,
        }

    logger.info("")
    logger.info("  %-34s %10s %10s %8s", "method", "eps_ATE", "PEHE", "reps")
    for m, v in sorted(summary.items(), key=lambda z: (z[1]["mean_eps_ate"] is None, z[1]["mean_eps_ate"])):
        logger.info("  %-34s %10s %10s %8d", m,
                    f"{v['mean_eps_ate']:.4f}" if v["mean_eps_ate"] is not None else "-",
                    f"{v['mean_pehe']:.4f}" if v["mean_pehe"] is not None else "n/a",
                    v["replicates_scored"])

    report = {
        "benchmark": "ci1_external",
        "hypothesis": "CI1",
        "dataset": "IHDP (semi-synthetic; real covariates, simulated outcomes, both arms known)",
        "replicates": len(per_rep),
        "per_replicate": per_rep,
        "summary": summary,
        "note": (
            "PEHE is absent for ATE-only estimators rather than penalised: an "
            "estimator that does not claim a per-unit effect has not got one wrong."
        ),
    }
    try:
        from benchmarks import finalize_benchmark_report

        report = finalize_benchmark_report(report, benchmark_id="ci1_external")
    except Exception:  # noqa: BLE001
        pass
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Results written to %s", args.output)


if __name__ == "__main__":
    main()
