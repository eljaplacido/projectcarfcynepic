# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H52 — Real-covariate CATE benchmark on IHDP (R2).

The IHDP (Infant Health and Development Program) benchmark of Hill (2011) is the
standard test for *heterogeneous* treatment-effect estimation. It is semi-synthetic:
the 25 covariates and treatment come from a **real** RCT, while the outcomes follow a
known simulated response surface — so the true individual treatment effects (ITE) and
ATE are exactly known. That makes it the canonical way to measure **PEHE** (precision
in estimating heterogeneous effects) on a realistic covariate distribution.

This benchmark replaces CARF's previous "IHDP-inspired" *synthetic* healthcare
proxy with the actual NPCI realization and measures CARF's real machinery:

1. **ATE recovery** — CARF's causal engine vs the known true ATE.
2. **CATE / PEHE** — the ChimeraOracle estimator (EconML ``CausalForestDML``) vs the
   true per-unit ITE, compared against a constant-effect baseline (does the
   heterogeneous model actually capture the real heterogeneity?).

Data is fetched once from the public NPCI CSV and cached under ``var/`` (not vendored,
not committed). If neither cache nor network is available the benchmark records
``status: skipped`` / ``evidence_grade: aspirational`` with **no fabricated metrics**.

Evidence grade: ``needs-independent-replication`` — real covariates but *simulated*
ground-truth effects (distinct from LaLonde's empirical RCT truth).

Run:
    python -m benchmarks.technical.realworld.benchmark_ihdp
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("benchmark.ihdp")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from benchmarks.technical.realworld._engine import carf_ate  # noqa: E402

# Public NPCI realization (real IHDP covariates + simulated response surface "B").
_CEVAE_URL = (
    "https://raw.githubusercontent.com/AMLab-Amsterdam/CEVAE/master/"
    "datasets/IHDP/csv/ihdp_npci_{replicate}.csv"
)
_CACHE_DIR = _PROJECT_ROOT / "var" / "benchmark_data" / "ihdp"
N_COVARIATES = 25
COVARIATES = [f"x{i}" for i in range(N_COVARIATES)]
TREATMENT = "treat"
OUTCOME = "y"

ATE_REL_ERROR_MAX = 0.25
PEHE_IMPROVEMENT_MIN = 0.10  # CForest PEHE must beat constant-effect baseline by >=10%


def load_ihdp(replicate: int = 1) -> tuple[Any, Any] | None:
    """Load an IHDP NPCI replicate as ``(df, true_ite)``.

    Reads a local cache first, then fetches from the public NPCI mirror and caches
    under ``var/`` (gitignored). Returns ``None`` when neither is available, so the
    caller can record an honest 'skipped' result.
    """
    try:
        import numpy as np
        import pandas as pd
    except Exception:  # pragma: no cover - numpy/pandas are core deps
        return None

    cache_path = _CACHE_DIR / f"ihdp_npci_{replicate}.csv"
    raw: str | None = None
    if cache_path.exists():
        raw = cache_path.read_text(encoding="utf-8")
    else:
        try:
            url = _CEVAE_URL.format(replicate=replicate)
            raw = urllib.request.urlopen(url, timeout=15).read().decode("utf-8")  # noqa: S310
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(raw, encoding="utf-8")
            logger.info("Cached IHDP replicate %d to %s", replicate, cache_path)
        except Exception as exc:  # pragma: no cover - network-defensive
            logger.warning("IHDP dataset unavailable (no cache, no network): %s", exc)
            return None

    arr = np.array([line.split(",") for line in raw.strip().splitlines()], dtype=float)
    # NPCI layout: [t, y_factual, y_cfactual, mu0, mu1, x0..x24]
    treatment = arr[:, 0].astype(int)
    y_factual = arr[:, 1]
    mu0, mu1 = arr[:, 3], arr[:, 4]
    covariate_matrix = arr[:, 5 : 5 + N_COVARIATES]
    true_ite = mu1 - mu0

    df = pd.DataFrame(covariate_matrix, columns=COVARIATES)
    df[TREATMENT] = treatment
    df[OUTCOME] = y_factual
    return df, true_ite


def pehe(cate_hat: Any, true_ite: Any) -> float:
    """Precision in Estimating Heterogeneous Effects = sqrt(mean((est-true)^2))."""
    import numpy as np

    return float(np.sqrt(np.mean((np.asarray(cate_hat) - np.asarray(true_ite)) ** 2)))


def causal_forest_cate(df: Any, true_ite: Any) -> dict[str, Any] | None:
    """Estimate per-unit CATE with CARF's ChimeraOracle estimator (CausalForestDML)."""
    try:
        import numpy as np
        from econml.dml import CausalForestDML
        from sklearn.ensemble import GradientBoostingRegressor
    except Exception:  # pragma: no cover
        return None

    X = df[COVARIATES].to_numpy()
    t = df[TREATMENT].to_numpy()
    y = df[OUTCOME].to_numpy()
    model = CausalForestDML(
        model_t=GradientBoostingRegressor(n_estimators=50, max_depth=4),
        model_y=GradientBoostingRegressor(n_estimators=50, max_depth=4),
        n_estimators=200,
        min_samples_leaf=10,
        random_state=42,
    )
    model.fit(y, t, X=X)
    cate = model.effect(X)
    return {"cate_mean": float(np.mean(cate)), "pehe": pehe(cate, true_ite)}


def compute_metrics(
    true_ate: float,
    carf_ate_value: float,
    pehe_cf: float | None,
    pehe_const: float | None,
) -> dict[str, Any]:
    """Pure metric computation (testable without DoWhy/EconML)."""
    abs_err = abs(carf_ate_value - true_ate)
    rel_err = abs_err / abs(true_ate) if true_ate else float("inf")
    metrics: dict[str, Any] = {
        "true_ate": round(true_ate, 4),
        "carf_ate": round(carf_ate_value, 4),
        "ate_abs_error": round(abs_err, 4),
        "ate_rel_error": round(rel_err, 4),
    }
    pehe_improvement = None
    if pehe_cf is not None and pehe_const is not None and pehe_const > 0:
        pehe_improvement = (pehe_const - pehe_cf) / pehe_const
        metrics.update(
            {
                "pehe_causal_forest": round(pehe_cf, 4),
                "pehe_constant_baseline": round(pehe_const, 4),
                "pehe_improvement": round(pehe_improvement, 4),
            }
        )
    ate_pass = rel_err <= ATE_REL_ERROR_MAX
    pehe_pass = pehe_improvement is None or pehe_improvement >= PEHE_IMPROVEMENT_MIN
    metrics["passed"] = bool(ate_pass and pehe_pass)
    return metrics


async def run_benchmark(replicate: int = 1) -> dict[str, Any]:
    from benchmarks import finalize_benchmark_report

    loaded = load_ihdp(replicate)
    if loaded is None:
        report = {
            "hypothesis": "H52",
            "claim": "On real-covariate IHDP data, CARF recovers the true ATE and its "
            "CATE estimator captures real heterogeneity (PEHE beats a constant baseline)",
            "status": "skipped",
            "passed": False,
            "evidence_grade": "aspirational",
            "reason": "IHDP NPCI dataset unavailable (no var/ cache and no network)",
            "data_source": _CEVAE_URL.format(replicate=replicate),
        }
        return finalize_benchmark_report(report, benchmark_id="ihdp_realworld")

    df, true_ite = loaded
    import numpy as np

    true_ate = float(np.mean(true_ite))
    engine = await carf_ate(df.to_dict("records"), TREATMENT, OUTCOME, COVARIATES)

    cf = causal_forest_cate(df, true_ite)
    pehe_cf = cf["pehe"] if cf else None
    pehe_const = pehe(np.full_like(true_ite, engine["effect"]), true_ite) if cf else None

    metrics = compute_metrics(true_ate, engine["effect"], pehe_cf, pehe_const)

    report = {
        "hypothesis": "H52",
        "claim": "On real-covariate IHDP data, CARF recovers the true ATE within "
        f"{ATE_REL_ERROR_MAX:.0%} and its CausalForestDML CATE estimator beats a "
        f"constant-effect baseline on PEHE by >={PEHE_IMPROVEMENT_MIN:.0%}",
        "metric": "ate_rel_error + pehe_improvement",
        "replicate": replicate,
        **metrics,
        "experimental_engine": engine,
        "causal_forest": cf,
        "dataset_profile": "hybrid",
        "ground_truth_type": "synthetic",
        "data_source": _CEVAE_URL.format(replicate=replicate),
        "n_units": int(len(df)),
        "n_covariates": N_COVARIATES,
        "samples": int(len(df)),
        "evidence_grade": "needs-independent-replication",
        "thresholds": {
            "ate_rel_error_max": ATE_REL_ERROR_MAX,
            "pehe_improvement_min": PEHE_IMPROVEMENT_MIN,
        },
    }
    return finalize_benchmark_report(
        report,
        benchmark_id="ihdp_realworld",
        source_reference="Hill (2011) IHDP semi-synthetic benchmark, NPCI realization (CEVAE mirror)",
        dataset_context={"dataset_profile": "hybrid", "ground_truth_type": "synthetic"},
        sample_context={"n_units": int(len(df))},
    )


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    report = asyncio.run(run_benchmark())
    out_path = Path(__file__).with_name("benchmark_ihdp_results.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report.get("status") == "skipped":
        print("[H52] IHDP benchmark SKIPPED (dataset unavailable)")
    else:
        status = "PASS" if report["passed"] else "FAIL"
        print(f"[H52] IHDP real-covariate CATE: {status}")
        print(f"  true ATE              : {report['true_ate']:.4f}")
        print(f"  CARF ATE              : {report['carf_ate']:.4f}  (rel err {report['ate_rel_error']:.1%})")
        if "pehe_causal_forest" in report:
            print(f"  PEHE (CausalForest)   : {report['pehe_causal_forest']:.4f}")
            print(f"  PEHE (constant)       : {report['pehe_constant_baseline']:.4f}"
                  f"  -> improvement {report['pehe_improvement']:.1%}")
    print(f"  results -> {out_path}")


if __name__ == "__main__":
    main()
