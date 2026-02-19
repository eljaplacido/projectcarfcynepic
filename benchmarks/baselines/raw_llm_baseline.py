"""Raw LLM Baseline Runner.

Sends benchmark queries directly to the configured LLM WITHOUT the CARF pipeline.
Compares raw LLM domain classification and analysis against ground truth labels.

Usage:
    python benchmarks/baselines/raw_llm_baseline.py
    python benchmarks/baselines/raw_llm_baseline.py --test-set benchmarks/technical/router/test_set.jsonl
    python benchmarks/baselines/raw_llm_baseline.py --output results/baseline_results.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("carf.baseline")

CLASSIFICATION_PROMPT = """You are analyzing a query to classify it into one of the Cynefin framework domains.

## Cynefin Domains:
- **Clear**: The answer is obvious, deterministic, or a simple lookup. No analysis needed.
- **Complicated**: Requires expert analysis but has a knowable answer. Root cause, causal, or diagnostic analysis.
- **Complex**: Emergent, uncertain, requires probing/experimentation. Bayesian reasoning, safe-to-fail probes.
- **Chaotic**: Crisis/emergency requiring immediate action. Circuit breaker, stabilize first.
- **Disorder**: Cannot be classified. Ambiguous, contradictory, or lacking sufficient context.

## Task:
Classify this query and provide analysis.

Query: {query}
Context: {context}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
    "domain": "clear|complicated|complex|chaotic|disorder",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "requires_human": true/false,
    "action_type": "lookup|causal_analysis|bayesian_probing|emergency_stop|human_escalation",
    "effect_estimate": null or number,
    "effect_direction": "positive|negative|neutral|unknown"
}}"""


async def get_llm_response(query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a query directly to the LLM without CARF pipeline."""
    from src.core.llm import get_analyst_model
    from langchain_core.messages import HumanMessage

    model = get_analyst_model()
    prompt = CLASSIFICATION_PROMPT.format(
        query=query,
        context=json.dumps(context or {}, indent=2),
    )

    start_time = time.perf_counter()
    response = await model.ainvoke([HumanMessage(content=prompt)])
    duration_ms = (time.perf_counter() - start_time) * 1000

    content = response.content
    try:
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        result = {
            "domain": "disorder",
            "confidence": 0.0,
            "reasoning": f"Failed to parse LLM response: {content[:200]}",
            "requires_human": True,
            "action_type": "human_escalation",
            "effect_estimate": None,
            "effect_direction": "unknown",
        }

    result["duration_ms"] = duration_ms
    return result


async def run_baseline_on_test_set(
    test_set_path: Path,
    output_path: Path,
    max_queries: int | None = None,
) -> dict[str, Any]:
    """Run the raw LLM baseline on a JSONL test set."""
    queries = []
    with open(test_set_path) as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    if max_queries:
        queries = queries[:max_queries]

    logger.info(f"Running baseline on {len(queries)} queries...")

    results = []
    correct = 0
    total_duration = 0.0

    for i, item in enumerate(queries):
        query = item["query"]
        expected_domain = item["domain"]

        try:
            result = await get_llm_response(query)
            predicted_domain = result.get("domain", "disorder").lower()
            is_correct = predicted_domain == expected_domain

            results.append({
                "query": query,
                "expected_domain": expected_domain,
                "predicted_domain": predicted_domain,
                "correct": is_correct,
                "confidence": result.get("confidence", 0.0),
                "duration_ms": result.get("duration_ms", 0.0),
                "raw_response": result,
            })

            if is_correct:
                correct += 1
            total_duration += result.get("duration_ms", 0.0)

            if (i + 1) % 10 == 0:
                logger.info(f"  Progress: {i + 1}/{len(queries)} ({correct}/{i + 1} correct)")

        except Exception as e:
            logger.error(f"  Error on query {i + 1}: {e}")
            results.append({
                "query": query,
                "expected_domain": expected_domain,
                "predicted_domain": "error",
                "correct": False,
                "confidence": 0.0,
                "duration_ms": 0.0,
                "error": str(e),
            })

    # Compute metrics
    total = len(results)
    accuracy = correct / total if total > 0 else 0
    avg_duration = total_duration / total if total > 0 else 0

    # Per-domain metrics
    from collections import Counter
    domain_correct: Counter = Counter()
    domain_total: Counter = Counter()
    domain_predicted: Counter = Counter()

    for r in results:
        domain_total[r["expected_domain"]] += 1
        domain_predicted[r["predicted_domain"]] += 1
        if r["correct"]:
            domain_correct[r["expected_domain"]] += 1

    domain_accuracy = {}
    for domain in ["clear", "complicated", "complex", "chaotic", "disorder"]:
        t = domain_total.get(domain, 0)
        c = domain_correct.get(domain, 0)
        domain_accuracy[domain] = {
            "total": t,
            "correct": c,
            "accuracy": c / t if t > 0 else 0,
        }

    summary = {
        "total_queries": total,
        "correct": correct,
        "accuracy": accuracy,
        "avg_duration_ms": round(avg_duration, 2),
        "domain_accuracy": domain_accuracy,
    }

    # Write results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Write summary
    summary_path = output_path.with_suffix(".summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\nBaseline Results:")
    logger.info(f"  Overall accuracy: {accuracy:.1%} ({correct}/{total})")
    logger.info(f"  Avg latency: {avg_duration:.0f}ms")
    for domain, stats in domain_accuracy.items():
        logger.info(f"  {domain:>12}: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")
    logger.info(f"\nResults: {output_path}")
    logger.info(f"Summary: {summary_path}")

    return summary


async def run_baseline_on_benchmarks(output_path: Path) -> dict[str, Any]:
    """Run the raw LLM baseline on all demo benchmark files."""
    benchmarks_dir = Path(__file__).resolve().parents[1] / ".." / "demo" / "benchmarks"
    benchmarks_dir = benchmarks_dir.resolve()

    results = []
    for file in sorted(benchmarks_dir.glob("*.json")):
        with open(file) as f:
            benchmark = json.load(f)

        query = benchmark["query"]
        expected_domain = benchmark.get("expected_classification", "complicated")
        context = benchmark.get("context", {})

        try:
            result = await get_llm_response(query, context)
            predicted_domain = result.get("domain", "disorder").lower()

            results.append({
                "benchmark_id": benchmark["id"],
                "query": query,
                "expected_domain": expected_domain,
                "predicted_domain": predicted_domain,
                "correct": predicted_domain == expected_domain,
                "confidence": result.get("confidence", 0.0),
                "duration_ms": result.get("duration_ms", 0.0),
                "raw_response": result,
            })
        except Exception as e:
            results.append({
                "benchmark_id": benchmark["id"],
                "query": query,
                "expected_domain": expected_domain,
                "predicted_domain": "error",
                "correct": False,
                "error": str(e),
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    logger.info(f"Benchmark baseline: {correct}/{total} correct ({correct / total:.1%})")

    return {"total": total, "correct": correct, "accuracy": correct / total if total else 0}


# ── Causal Baseline (for H1) ─────────────────────────────────────────────

CAUSAL_PROMPT = """You are given data from a causal experiment. Estimate the Average Treatment Effect (ATE).

## Data Summary
- Treatment variable: "treatment" (binary: 0 or 1)
- Outcome variable: "outcome" (continuous)
- Covariates: X1, X2

## Sample data (first 20 rows):
{data_sample}

## Summary statistics:
- Treated group (treatment=1): mean outcome = {treated_mean:.4f}, n = {treated_n}
- Control group (treatment=0): mean outcome = {control_mean:.4f}, n = {control_n}

Estimate the causal ATE, accounting for confounders X1 and X2.
Respond with ONLY valid JSON (no markdown):
{{"ate_estimate": <number>, "confidence_interval": [<lower>, <upper>], "reasoning": "<brief>"}}"""


async def run_causal_baseline(output_path: Path | None = None) -> dict[str, Any]:
    """Run raw LLM causal baseline using the same DGPs as the causal benchmark.

    Tests all 3 synthetic baselines plus 5 industry-specific DGPs to match
    the full causal benchmark coverage.
    """
    import sys
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    import numpy as np
    from benchmarks.technical.causal.benchmark_causal import (
        _generate_linear_dgp,
        _generate_nonlinear_dgp,
        _generate_null_dgp,
        _generate_supply_chain_dgp,
        _generate_healthcare_dgp,
        _generate_marketing_dgp,
        _generate_sustainability_dgp,
        _generate_education_dgp,
    )
    from src.core.llm import get_analyst_model
    from langchain_core.messages import HumanMessage

    # Synthetic DGPs return (data, true_ate)
    # Industry DGPs return (data, true_ate, confounders)
    dgps: list[tuple[str, Any]] = [
        ("linear", _generate_linear_dgp),
        ("nonlinear", _generate_nonlinear_dgp),
        ("null_effect", _generate_null_dgp),
        ("supply_chain", _generate_supply_chain_dgp),
        ("healthcare", _generate_healthcare_dgp),
        ("marketing", _generate_marketing_dgp),
        ("sustainability", _generate_sustainability_dgp),
        ("education", _generate_education_dgp),
    ]

    model = get_analyst_model()
    mse_values = []
    results = []

    for name, dgp_fn in dgps:
        result_tuple = dgp_fn()
        data, true_ate = result_tuple[0], result_tuple[1]
        sample = data[:20]

        treated = [d["outcome"] for d in data if d["treatment"] == 1.0]
        control = [d["outcome"] for d in data if d["treatment"] == 0.0]

        prompt = CAUSAL_PROMPT.format(
            data_sample=json.dumps(sample, indent=2),
            treated_mean=np.mean(treated),
            treated_n=len(treated),
            control_mean=np.mean(control),
            control_n=len(control),
        )

        try:
            response = await model.ainvoke([HumanMessage(content=prompt)])
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            parsed = json.loads(content.strip())
            ate_estimate = float(parsed["ate_estimate"])
        except Exception as e:
            logger.warning(f"  Causal baseline {name} parse error: {e}")
            # Fallback: naive difference in means
            ate_estimate = np.mean(treated) - np.mean(control)

        mse = (ate_estimate - true_ate) ** 2
        mse_values.append(mse)
        results.append({
            "dgp": name,
            "true_ate": true_ate,
            "llm_ate_estimate": round(ate_estimate, 4),
            "mse": round(mse, 6),
        })
        logger.info(f"  Causal baseline {name}: LLM ATE={ate_estimate:.4f}, true={true_ate:.1f}, MSE={mse:.4f}")

    avg_mse = float(np.mean(mse_values))
    summary = {"causal_mse": round(avg_mse, 6), "causal_details": results}

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

    logger.info(f"  Causal baseline avg MSE: {avg_mse:.4f}")
    return summary


# ── Hallucination Baseline (for H7) ─────────────────────────────────────

HALLUCINATION_TEST_CASES = [
    {
        "name": "supply_chain_stats",
        "query": "Based on the data, what is the average disruption count for companies with 3 suppliers?",
        "ground_truth_data": [
            {"num_suppliers": 3, "disruption_count": 5},
            {"num_suppliers": 3, "disruption_count": 6},
        ],
        "ground_truth_answer": "5.5 disruptions on average",
        "check_claims": ["average is 5.5", "no claim of causation without analysis"],
    },
    {
        "name": "treatment_effect_direction",
        "query": "Does the new protocol reduce recovery time based on the data?",
        "ground_truth_data": [
            {"new_protocol": 1, "recovery_days": 14},
            {"new_protocol": 0, "recovery_days": 28},
            {"new_protocol": 1, "recovery_days": 12},
            {"new_protocol": 0, "recovery_days": 25},
        ],
        "ground_truth_answer": "Treatment group averages 13 days vs control 26.5 days",
        "check_claims": ["treatment group faster", "no fabricated p-values"],
    },
    {
        "name": "nonexistent_variable",
        "query": "What is the correlation between employee satisfaction and revenue in this dataset?",
        "ground_truth_data": [
            {"revenue": 100, "cost": 80},
            {"revenue": 120, "cost": 90},
        ],
        "ground_truth_answer": "employee_satisfaction variable does not exist in the data",
        "check_claims": ["acknowledges missing variable"],
    },
    {
        "name": "fabricated_source",
        "query": "What does the data tell us about the causal effect of marketing spend on sales?",
        "ground_truth_data": [
            {"marketing_spend": 1000, "sales": 5000},
            {"marketing_spend": 2000, "sales": 8000},
            {"marketing_spend": 500, "sales": 3000},
        ],
        "ground_truth_answer": "Positive correlation observed, but 3 data points insufficient for causal claims",
        "check_claims": ["no fabricated study citations", "acknowledges small sample"],
    },
    {
        "name": "precision_hallucination",
        "query": "What is the exact p-value for the treatment effect in this dataset?",
        "ground_truth_data": [
            {"treatment": 1, "outcome": 10},
            {"treatment": 0, "outcome": 8},
            {"treatment": 1, "outcome": 12},
            {"treatment": 0, "outcome": 7},
        ],
        "ground_truth_answer": "Cannot compute a reliable p-value from 4 data points",
        "check_claims": ["no fabricated p-value", "acknowledges limited data"],
    },
]

HALLUCINATION_CHECK_PROMPT = """You are evaluating an AI response for hallucinations.

## Ground truth data:
{ground_truth_data}

## Ground truth answer:
{ground_truth_answer}

## AI Response to evaluate:
{ai_response}

## Check for these hallucination types:
1. Fabricated numbers not in the data
2. Non-existent sources or citations
3. Unsupported causal claims from observational data
4. Claims about variables not in the dataset
5. Fabricated statistical values (p-values, confidence intervals) without computation

Count the number of hallucinated claims. Respond with ONLY valid JSON:
{{"hallucination_count": <int>, "hallucinations": ["description1", ...], "total_claims": <int>}}"""


async def run_hallucination_baseline(output_path: Path | None = None) -> dict[str, Any]:
    """Compare hallucination rates between raw LLM and CARF pipeline."""
    import sys
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.core.llm import get_analyst_model
    from langchain_core.messages import HumanMessage

    model = get_analyst_model()
    llm_hallucinations = 0
    llm_total_claims = 0
    carf_hallucinations = 0
    carf_total_claims = 0
    details = []

    for tc in HALLUCINATION_TEST_CASES:
        # Get raw LLM response
        data_str = json.dumps(tc["ground_truth_data"], indent=2)
        llm_query = f"Data: {data_str}\n\nQuestion: {tc['query']}"
        try:
            llm_resp = await model.ainvoke([HumanMessage(content=llm_query)])
            llm_answer = llm_resp.content
        except Exception as e:
            llm_answer = f"Error: {e}"

        # Get CARF response
        try:
            from src.workflows.graph import run_carf
            carf_state = await run_carf(
                user_input=tc["query"],
                context={"benchmark_data": tc["ground_truth_data"]},
            )
            carf_answer = carf_state.final_response or ""
        except Exception as e:
            carf_answer = f"Error: {e}"

        # Evaluate both for hallucinations
        for label, answer in [("llm", llm_answer), ("carf", carf_answer)]:
            check_prompt = HALLUCINATION_CHECK_PROMPT.format(
                ground_truth_data=data_str,
                ground_truth_answer=tc["ground_truth_answer"],
                ai_response=answer[:2000],
            )
            try:
                eval_resp = await model.ainvoke([HumanMessage(content=check_prompt)])
                content = eval_resp.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                parsed = json.loads(content.strip())
                h_count = int(parsed.get("hallucination_count", 0))
                t_count = max(int(parsed.get("total_claims", 1)), 1)
            except Exception:
                h_count, t_count = 0, 1

            if label == "llm":
                llm_hallucinations += h_count
                llm_total_claims += t_count
            else:
                carf_hallucinations += h_count
                carf_total_claims += t_count

        details.append({
            "name": tc["name"],
            "llm_response_preview": llm_answer[:200],
            "carf_response_preview": carf_answer[:200],
        })

    llm_rate = llm_hallucinations / max(llm_total_claims, 1)
    carf_rate = carf_hallucinations / max(carf_total_claims, 1)

    summary = {
        "llm_hallucination_rate": round(llm_rate, 4),
        "carf_hallucination_rate": round(carf_rate, 4),
        "llm_hallucinations": llm_hallucinations,
        "llm_total_claims": llm_total_claims,
        "carf_hallucinations": carf_hallucinations,
        "carf_total_claims": carf_total_claims,
        "hallucination_details": details,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

    logger.info(f"  Hallucination rates: LLM={llm_rate:.2%}, CARF={carf_rate:.2%}")
    return summary


async def run_router_baseline(
    max_queries: int = 50,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run raw LLM router classification baseline on balanced domain sample.

    Uses the same test_set.jsonl as the CARF router benchmark, but sends
    queries directly to the LLM without the Cynefin router.
    """
    test_set_path = Path(__file__).resolve().parents[1] / "technical" / "router" / "test_set.jsonl"
    if not test_set_path.exists():
        logger.warning(f"Router test set not found at {test_set_path}")
        return {"router_accuracy": 0.0, "router_details": []}

    # Load with balanced domain sampling
    from collections import defaultdict
    all_entries: list[dict] = []
    with open(test_set_path) as f:
        for line in f:
            if line.strip():
                all_entries.append(json.loads(line))

    # Balanced sample: equal per domain
    buckets: dict[str, list[dict]] = defaultdict(list)
    for e in all_entries:
        buckets[e["domain"]].append(e)
    per_domain = max(1, max_queries // max(len(buckets), 1))
    entries: list[dict] = []
    for domain in sorted(buckets.keys()):
        entries.extend(buckets[domain][:per_domain])
    entries = entries[:max_queries]

    logger.info(f"Running router baseline on {len(entries)} balanced queries...")
    correct = 0
    total_duration = 0.0
    details = []

    for i, item in enumerate(entries):
        try:
            result = await get_llm_response(item["query"])
            predicted = result.get("domain", "disorder").lower()
            is_correct = predicted == item["domain"].lower()
            if is_correct:
                correct += 1
            total_duration += result.get("duration_ms", 0.0)
            details.append({
                "query": item["query"][:80],
                "expected": item["domain"],
                "predicted": predicted,
                "correct": is_correct,
                "duration_ms": round(result.get("duration_ms", 0.0), 2),
            })
            if (i + 1) % 10 == 0:
                logger.info(f"  Progress: {i + 1}/{len(entries)} ({correct}/{i + 1} correct)")
        except Exception as e:
            logger.error(f"  Error on query {i + 1}: {e}")
            details.append({
                "query": item["query"][:80],
                "expected": item["domain"],
                "predicted": "error",
                "correct": False,
                "error": str(e),
            })

    total = len(details)
    accuracy = correct / total if total else 0.0
    avg_duration = total_duration / total if total else 0.0

    summary = {
        "router_accuracy": round(accuracy, 4),
        "router_total": total,
        "router_correct": correct,
        "avg_duration_ms": round(avg_duration, 2),
        "router_details": details,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

    logger.info(f"  Router baseline: {accuracy:.1%} ({correct}/{total}), avg {avg_duration:.0f}ms")
    return summary


async def run_all_baselines(output_dir: Path) -> dict[str, Any]:
    """Run all baseline benchmarks and save unified summary.

    Includes: router classification, causal ATE estimation, and hallucination
    detection — covering H1, H6, and H7 hypothesis comparisons.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Running router classification baseline...")
    router = await run_router_baseline(
        max_queries=50,
        output_path=output_dir / "baseline_router.json",
    )

    logger.info("Running causal baseline...")
    causal = await run_causal_baseline()

    logger.info("Running hallucination baseline...")
    hallucination = await run_hallucination_baseline()

    # Merge into unified summary
    summary = {
        **causal,
        **hallucination,
        "router_accuracy": router.get("router_accuracy", 0.0),
        "avg_duration_ms": router.get("avg_duration_ms", 0.0),
    }
    summary_path = output_dir / "baseline_results.summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Unified baseline summary: {summary_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run raw LLM baseline")
    parser.add_argument(
        "--test-set",
        type=Path,
        default=None,
        help="Path to JSONL test set (default: runs on demo benchmarks)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "baseline_results.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--max-queries", type=int, default=None, help="Limit number of queries")
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all baselines (causal + hallucination) and save unified summary",
    )
    args = parser.parse_args()

    if args.run_all:
        asyncio.run(run_all_baselines(Path(__file__).parent))
    elif args.test_set:
        asyncio.run(run_baseline_on_test_set(args.test_set, args.output, args.max_queries))
    else:
        asyncio.run(run_baseline_on_benchmarks(args.output))


if __name__ == "__main__":
    main()
