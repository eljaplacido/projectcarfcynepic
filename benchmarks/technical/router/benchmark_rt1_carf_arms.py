"""RT1, second half — CARF's own routers on the same 456-query spine.

The Rust implementations (`keyword`, `lexical_centroid`, `discriminative_logreg`)
were scored on this spine by `cynepic-router`'s `rt1_spine` example. RT1 names
five implementations; these are the other two, and until they are on the same
table no cross-tool statement about routing is admissible.

ONE PROTOCOL, AND BOTH READINGS OF IT
=====================================

Scored exactly as the Rust arms were: the same 456 items, and both readings of
what `Disorder` means.

    five_class   all 456 items, Disorder is a class to be predicted
    four_class   the 354 non-Disorder items, an abstention counted as an error

That distinction reordered the Rust table, so it is carried here rather than
chosen.

WHAT IS NOT CROSS-VALIDATED HERE, AND WHY THAT MATTERS
======================================================

The Rust arms were 4-fold cross-validated: every item was scored by a model that
never saw it. **DistilBERT is not**, because it arrives already trained and
there is no fold structure to impose on a fixed checkpoint.

Exact-overlap between its training file (`data/router_training/`, 1000 items)
and this spine is **2 of 456 (0.4%)**, which is negligible. But both sets come
from generators, so near-duplicates that are not byte-identical would not show
up in that count. DistilBERT's figure here is therefore *held-out-ish* and the
Rust figures are *held-out*, and that asymmetry favours DistilBERT. It is
recorded rather than corrected because correcting it would mean retraining, and
a comparison that flatters the other side is the safe direction for a claim that
the Rust arms are competitive.

THE SILENT FALLBACK THIS GUARDS AGAINST
=======================================

`CynefinRouter._load_distilbert` falls back to LLM mode when the deps or the
model path are missing, and logs a warning. A benchmark that trusted
`ROUTER_MODE=distilbert` would then report LLM numbers under a DistilBERT label
and nothing on the table would say so.

So the mode is read back off the constructed router and recorded in the result,
and the run refuses if it does not match what was asked for. Booking one arm's
numbers under another arm's name is the same failure as H43's unmeasured cell
being published as a guardian score.

    python -m benchmarks.technical.router.benchmark_rt1_carf_arms          # distilbert only
    python -m benchmarks.technical.router.benchmark_rt1_carf_arms --llm    # adds the paid arm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("benchmark.rt1_carf")

HERE = Path(__file__).parent
SPINE = HERE / "test_set.jsonl"
RUST_RESULTS = HERE / "rt1_spine_results.json"

DOMAINS_5 = ["Clear", "Complicated", "Complex", "Chaotic", "Disorder"]
DOMAINS_4 = DOMAINS_5[:4]


def load_spine() -> list[tuple[str, str]]:
    items = []
    for line in SPINE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        items.append((d["query"], d["domain"].strip().capitalize()))
    return items


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def score(pairs: list[tuple[str, str]], labels: list[str]) -> dict[str, Any]:
    """Macro F1 and accuracy over (predicted, actual) pairs."""
    per = {}
    for d in labels:
        tp = sum(1 for p, a in pairs if p == d and a == d)
        fp = sum(1 for p, a in pairs if p == d and a != d)
        fn = sum(1 for p, a in pairs if p != d and a == d)
        per[d] = {
            "f1": round(_f1(tp, fp, fn), 4),
            "recall": round(tp / (tp + fn), 4) if (tp + fn) else 0.0,
            "precision": round(tp / (tp + fp), 4) if (tp + fp) else 0.0,
            "support": tp + fn,
        }
    acc = sum(1 for p, a in pairs if p == a) / len(pairs) if pairs else 0.0
    return {
        "macro_f1": round(sum(per[d]["f1"] for d in labels) / len(labels), 4),
        "accuracy": round(acc, 4),
        "n_scored": len(pairs),
        "per_domain": per,
    }


def point_llm_at_openrouter(model: str) -> None:
    """Select the OpenRouter provider for CARF's LLM layer.

    The configured DeepSeek backend returns 402 Insufficient Balance, so the
    published DeepSeek figure cannot be reproduced at all right now. This
    substitutes a backend WITHOUT touching the router: the same
    `get_chat_model` -> `ChatOpenAI` path runs, only the endpoint moves.

    The result is therefore a measurement of CARF's router LOGIC on a different
    model, and is labelled `carf_llm_via_openrouter` rather than `carf_llm` so
    it is never mistaken for a reproduction of the published number.
    """
    # `openrouter` is now a first-class provider in src/core/llm.py, so this
    # is a configuration choice rather than a patch. It was a monkeypatch on the
    # OPENAI entry when this first ran, which worked and was the wrong shape:
    # a benchmark that rewrites the code under test is measuring something it
    # also authored.
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_MODEL"] = model


async def run_arm(mode: str, items: list[tuple[str, str]], label: str | None = None) -> dict[str, Any]:
    """Classify every spine item through CARF's router in `mode`."""
    os.environ["ROUTER_MODE"] = mode
    from src.core.state import EpistemicState
    from src.workflows.router import CynefinRouter

    # The model is loaded in __init__, and the fallback to LLM happens there
    # too, so the mode is already settled by the time construction returns.
    router = CynefinRouter(mode=mode)
    actual_mode = getattr(router, "mode", "unknown")
    if actual_mode != mode:
        raise RuntimeError(
            f"asked for ROUTER_MODE={mode!r} and got {actual_mode!r}; the router "
            "fell back silently and these numbers would be published under the "
            "wrong arm's name"
        )

    pairs: list[tuple[str, str]] = []
    errors = 0
    first_error: str | None = None
    started = time.time()
    for i, (query, truth) in enumerate(items, 1):
        try:
            # `user_input`, not `query`: an EpistemicState built with the wrong
            # field name is silently EMPTY, and every item comes back Disorder
            # at confidence 0.90 -- which looks like a classifier result.
            state = EpistemicState(user_input=query)
            out = await router.classify(state)
            pred = out.cynefin_domain.value.capitalize()
        except Exception as exc:  # noqa: BLE001
            errors += 1
            first_error = first_error or f"{type(exc).__name__}: {exc}"
            if errors <= 3:
                logger.warning("query %d failed: %s", i, exc)
            # NOT recorded as a prediction. An arm that raised did not answer
            # "Disorder"; booking the exception as a wrong answer is how a dead
            # backend publishes as a classifier scoring 0.000, which is the
            # failure H43 already cost this programme once.
            continue
        pairs.append((pred, truth))
        if i % 100 == 0:
            logger.info("  %s: %d/%d", mode, i, len(items))

    elapsed = time.time() - started
    if not pairs or errors > 0.1 * len(items):
        # Too little of the arm ran to score it. Reported as absent with the
        # reason, never as a number.
        return {
            "implementation": f"carf_{mode}",
            "ran": False,
            "requested_mode": mode,
            "actual_mode": actual_mode,
            "errors": errors,
            "answered": len(pairs),
            "of": len(items),
            "reason": f"{errors} of {len(items)} calls failed; first was {first_error}",
        }
    four = [(p, a) for p, a in pairs if a != "Disorder"]
    return {
        "implementation": label or f"carf_{mode}",
        "requested_mode": mode,
        "actual_mode": actual_mode,
        "errors": errors,
        "seconds": round(elapsed, 1),
        "ms_per_query": round(1000 * elapsed / max(len(items), 1), 1),
        "five_class": score(pairs, DOMAINS_5),
        "four_class": score(four, DOMAINS_4),
        "cross_validated": False,
        "held_out_caveat": (
            "arrives pre-trained; 2 of 456 spine items appear verbatim in its "
            "training file, and near-duplicates from a shared generator would "
            "not show in that count"
        ),
    }


def merge_with_rust() -> dict[str, Any]:
    """The Rust arms, if their result file is present."""
    if not RUST_RESULTS.exists():
        logger.warning("%s missing; the Rust arms will be absent from the table", RUST_RESULTS.name)
        return {}
    d = json.loads(RUST_RESULTS.read_text(encoding="utf-8"))
    out = {}
    for protocol in ("five_class", "four_class"):
        for r in d[protocol]["results"]:
            out.setdefault(r["implementation"], {})[protocol] = {
                "macro_f1": round(r["macro_f1"], 4),
                "accuracy": round(r["accuracy"], 4),
            }
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="RT1: CARF's routers on the 456-query spine")
    parser.add_argument("--llm", action="store_true", help="also run the paid LLM arm")
    parser.add_argument("--openrouter-model", default="deepseek/deepseek-chat",
                        help="model id for the LLM arm, routed via OpenRouter")
    parser.add_argument("--limit", type=int, default=0, help="first N items only (smoke)")
    parser.add_argument("-o", "--output", default=str(HERE / "rt1_carf_arms_results.json"))
    args = parser.parse_args()

    items = load_spine()
    if args.limit:
        items = items[: args.limit]
    logger.info("=== RT1 second half: CARF routers on %d spine items ===", len(items))

    arms = []
    plan: list[tuple[str, str | None]] = [("distilbert", None)]
    if args.llm:
        point_llm_at_openrouter(args.openrouter_model)
        plan.append(("llm", f"carf_llm_via_openrouter[{args.openrouter_model}]"))
    for mode, label in plan:
        logger.info("running arm: %s%s", mode, f" ({label})" if label else "")
        try:
            arms.append(asyncio.run(run_arm(mode, items, label)))
        except Exception as exc:  # noqa: BLE001
            # An arm that cannot run is recorded as absent, never as zero.
            logger.error("arm %s did not run: %s", mode, exc)
            arms.append({"implementation": label or f"carf_{mode}", "ran": False, "reason": str(exc)})

    rust = merge_with_rust()
    logger.info("")
    logger.info("  %-26s %10s %10s %10s %10s", "implementation", "5c macroF1", "5c acc", "4c macroF1", "4c acc")
    for name, v in rust.items():
        logger.info("  %-26s %10.3f %10.3f %10.3f %10.3f", name,
                    v["five_class"]["macro_f1"], v["five_class"]["accuracy"],
                    v["four_class"]["macro_f1"], v["four_class"]["accuracy"])
    for a in arms:
        if not a.get("five_class"):
            logger.info("  %-26s %10s %10s %10s %10s  ABSENT: %s",
                        a["implementation"], "-", "-", "-", "-", a.get("reason", "")[:60])
            continue
        logger.info("  %-26s %10.3f %10.3f %10.3f %10.3f", a["implementation"],
                    a["five_class"]["macro_f1"], a["five_class"]["accuracy"],
                    a["four_class"]["macro_f1"], a["four_class"]["accuracy"])

    report: dict[str, Any] = {
        "benchmark": "rt1_carf_arms",
        "hypothesis": "RT1",
        "spine": str(SPINE.name),
        "n_items": len(items),
        "carf_arms": arms,
        "rust_arms": rust,
        "protocol_note": (
            "Rust arms are 4-fold cross-validated; CARF's DistilBERT arrives "
            "pre-trained and is not. The asymmetry favours DistilBERT and is "
            "recorded rather than corrected."
        ),
    }
    try:
        from benchmarks import finalize_benchmark_report

        report = finalize_benchmark_report(report, benchmark_id="rt1_carf_arms",
                                           source_reference=str(SPINE))
    except Exception:  # noqa: BLE001
        pass

    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Results written to %s", args.output)


if __name__ == "__main__":
    main()
