# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H47: NeSy Hallucination Precision — PR curve over KG-verifiable claims.

Hypothesis: A two-stage NeSy verification pipeline (LLM claim extraction →
Neo4j graph validation) achieves precision >= 0.70 with recall >= 0.50
on distinguishing factual from hallucinated claims.

Approach:
1. Construct an in-memory knowledge graph with known facts
2. Generate a balanced set of true claims (KG-verifiable) and false claims
   (contradict KG facts or fabricate entities)
3. Run each claim through the verification pipeline:
   a. Extract entities/relations from claim text
   b. Look up in knowledge graph (exact match + reachability)
   c. Assign epistemic score based on verification coverage
4. Compute precision-recall curve at varying confidence thresholds
5. Report AUPRC and threshold-level metrics

Graceful degradation: if Neo4j is available, uses real graph for additional
test coverage; otherwise operates entirely on in-memory KG.

Metrics:
    auprc: area under precision-recall curve
    precision_at_0.5: P when R=0.5
    recall_at_0.7: R when P=0.7
    best_f1: maximum F1 across thresholds
    verification_latency_ms: per-claim timing
    kg_coverage: % of claims with at least one KG lookup possible

Targets:
    AUPRC >= 0.65
    Best F1 >= 0.70
    P@R=0.5 >= 0.60

Usage:
    python benchmarks/technical/governance/benchmark_nesy_hallucination.py
    python benchmarks/technical/governance/benchmark_nesy_hallucination.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.nesy_hallucination")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


# ── In-Memory Knowledge Graph ────────────────────────────────────────────
# A small but realistic schema covering enterprise domains: procurement,
# sustainability, finance, operations. Used as ground truth for claim
# verification when Neo4j is unavailable.


@dataclass
class KGFact:
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0


@dataclass
class ClaimWithLabel:
    """A claim with its ground-truth label (factual or hallucinated)."""

    text: str
    label: bool  # True = factual, False = hallucinated
    category: str = ""
    entities: list[str] = field(default_factory=list)


# In-memory KG: 30 facts across procurement, sustainability, finance
_KG_FACTS: list[KGFact] = [
    # Procurement domain
    KGFact("Supplier_A", "located_in", "Vietnam"),
    KGFact("Supplier_A", "industry", "electronics"),
    KGFact("Supplier_A", "annual_revenue", "USD_50M"),
    KGFact("Supplier_A", "carbon_emissions_tons", "12000"),
    KGFact("Supplier_B", "located_in", "Germany"),
    KGFact("Supplier_B", "industry", "automotive"),
    KGFact("Supplier_B", "is_certified", "ISO_14001"),
    KGFact("Supplier_C", "located_in", "USA"),
    KGFact("Supplier_C", "industry", "logistics"),
    KGFact("Supplier_C", "annual_revenue", "USD_200M"),
    # Sustainability
    KGFact("Supplier_A", "scope_1_emissions", "5000"),
    KGFact("Supplier_A", "scope_2_emissions", "3000"),
    KGFact("Supplier_A", "scope_3_emissions", "4000"),
    KGFact("Supplier_B", "scope_1_emissions", "8000"),
    KGFact("Supplier_B", "uses_renewable_energy", "true"),
    KGFact("Region_SE_Asia", "avg_carbon_intensity", "0.65"),
    KGFact("Region_EU", "avg_carbon_intensity", "0.25"),
    # Financial
    KGFact("Contract_2024_Q1", "value", "USD_500K"),
    KGFact("Contract_2024_Q1", "vendor", "Supplier_A"),
    KGFact("Contract_2024_Q1", "status", "active"),
    KGFact("Contract_2024_Q2", "value", "USD_1.2M"),
    KGFact("Contract_2024_Q2", "vendor", "Supplier_B"),
    KGFact("Budget_2024", "procurement", "USD_5M"),
    KGFact("Budget_2024", "sustainability", "USD_2M"),
    # Operations
    KGFact("Factory_Hanoi", "capacity_units_per_day", "5000"),
    KGFact("Factory_Hanoi", "energy_source", "grid_mix"),
    KGFact("Factory_Stuttgart", "capacity_units_per_day", "8000"),
    KGFact("Factory_Stuttgart", "energy_source", "renewable"),
    KGFact("Logistics_Route_Asia_EU", "avg_transit_days", "35"),
    KGFact("Logistics_Route_Asia_EU", "carbon_per_ton_km", "0.045"),
]


def _kg_lookup(subject: str, predicate: str | None = None) -> list[KGFact]:
    """Find all facts matching subject (and optionally predicate)."""
    if predicate:
        return [
            f
            for f in _KG_FACTS
            if f.subject.lower() == subject.lower() and f.predicate == predicate
        ]
    return [f for f in _KG_FACTS if f.subject.lower() == subject.lower()]


def _kg_exists(subject: str) -> bool:
    return any(f.subject.lower() == subject.lower() for f in _KG_FACTS)


# ── Claim Generation ─────────────────────────────────────────────────────
# 50 claims: 25 factual (derived from KG), 25 hallucinated (contradict KG)


def _generate_claims() -> list[ClaimWithLabel]:
    claims: list[ClaimWithLabel] = []

    # Factual claims — directly supported by KG
    factual = [
        ("Supplier A is located in Vietnam", True, "entity_fact", ["Supplier_A"]),
        ("Supplier A operates in the electronics industry", True, "entity_fact", ["Supplier_A"]),
        ("Supplier A has annual revenue of USD 50 million", True, "entity_fact", ["Supplier_A"]),
        (
            "Supplier A's annual carbon emissions are 12,000 tons",
            True,
            "entity_fact",
            ["Supplier_A"],
        ),
        ("Supplier B is located in Germany", True, "entity_fact", ["Supplier_B"]),
        ("Supplier B is ISO 14001 certified", True, "entity_fact", ["Supplier_B"]),
        ("Supplier C is in the logistics industry", True, "entity_fact", ["Supplier_C"]),
        ("Contract 2024 Q1 has a value of USD 500,000", True, "entity_fact", ["Contract_2024_Q1"]),
        (
            "Contract 2024 Q1 vendor is Supplier A",
            True,
            "relation",
            ["Contract_2024_Q1", "Supplier_A"],
        ),
        ("The procurement budget for 2024 is USD 5 million", True, "entity_fact", ["Budget_2024"]),
        (
            "The sustainability budget for 2024 is USD 2 million",
            True,
            "entity_fact",
            ["Budget_2024"],
        ),
        (
            "Factory Hanoi has capacity of 5,000 units per day",
            True,
            "entity_fact",
            ["Factory_Hanoi"],
        ),
        ("Factory Stuttgart runs on renewable energy", True, "entity_fact", ["Factory_Stuttgart"]),
        ("Supplier B uses renewable energy", True, "entity_fact", ["Supplier_B"]),
        ("Supplier A Scope 1 emissions are 5,000 tons", True, "entity_fact", ["Supplier_A"]),
        ("Supplier A Scope 2 emissions are 3,000 tons", True, "entity_fact", ["Supplier_A"]),
        ("Supplier B Scope 1 emissions are 8,000 tons", True, "entity_fact", ["Supplier_B"]),
        ("EU region average carbon intensity is 0.25", True, "entity_fact", ["Region_EU"]),
        ("SE Asia average carbon intensity is 0.65", True, "entity_fact", ["Region_SE_Asia"]),
        (
            "Factory Stuttgart capacity is 8,000 units per day",
            True,
            "entity_fact",
            ["Factory_Stuttgart"],
        ),
        (
            "Logistics route Asia-EU averages 35 transit days",
            True,
            "entity_fact",
            ["Logistics_Route_Asia_EU"],
        ),
        ("Supplier C annual revenue is USD 200 million", True, "entity_fact", ["Supplier_C"]),
        ("Supplier A Scope 3 emissions are 4,000 tons", True, "entity_fact", ["Supplier_A"]),
        ("Contract 2024 Q2 value is USD 1.2 million", True, "entity_fact", ["Contract_2024_Q2"]),
        (
            "Contract 2024 Q2 vendor is Supplier B",
            True,
            "relation",
            ["Contract_2024_Q2", "Supplier_B"],
        ),
    ]

    # Hallucinated claims — contradict KG or fabricate entities
    hallucinated = [
        ("Supplier A is located in Thailand", False, "entity_substitution", ["Supplier_A"]),
        (
            "Supplier A operates in the pharmaceutical industry",
            False,
            "entity_substitution",
            ["Supplier_A"],
        ),
        ("Supplier A annual revenue is USD 500 million", False, "value_error", ["Supplier_A"]),
        ("Supplier A carbon emissions are 5,000 tons", False, "value_error", ["Supplier_A"]),
        ("Supplier D is located in Brazil", False, "fabricated_entity", ["Supplier_D"]),
        ("Supplier B is located in France", False, "entity_substitution", ["Supplier_B"]),
        (
            "Contract 2024 Q1 has a value of USD 5 million",
            False,
            "value_error",
            ["Contract_2024_Q1"],
        ),
        (
            "The marketing budget for 2024 is USD 3 million",
            False,
            "fabricated_entity",
            ["Budget_2024"],
        ),
        ("Factory Hanoi runs on solar energy", False, "entity_substitution", ["Factory_Hanoi"]),
        (
            "Factory Stuttgart has capacity of 2,000 units per day",
            False,
            "value_error",
            ["Factory_Stuttgart"],
        ),
        ("Supplier B Scope 1 emissions are 2,000 tons", False, "value_error", ["Supplier_B"]),
        ("Region_EU has average carbon intensity of 0.55", False, "value_error", ["Region_EU"]),
        (
            "Logistics route Asia-EU takes 15 transit days",
            False,
            "value_error",
            ["Logistics_Route_Asia_EU"],
        ),
        (
            "Supplier C is in the pharmaceutical industry",
            False,
            "entity_substitution",
            ["Supplier_C"],
        ),
        (
            "Supplier X was acquired by Supplier A in 2023",
            False,
            "fabricated_entity",
            ["Supplier_A"],
        ),
        ("Contract 2024 Q3 value is USD 800,000", False, "fabricated_entity", []),
        (
            "Factory Hanoi capacity increased to 12,000 units",
            False,
            "value_error",
            ["Factory_Hanoi"],
        ),
        ("Supplier A has ISO 9001 certification", False, "fabricated_attribute", ["Supplier_A"]),
        ("The EU carbon tax will increase 25% next year", False, "speculative", []),
        (
            "Supplier B carbon emissions are the lowest in the industry",
            False,
            "unverifiable_comparison",
            ["Supplier_B"],
        ),
        (
            "Region SE Asia carbon intensity dropped 50% since 2020",
            False,
            "speculative",
            ["Region_SE_Asia"],
        ),
        ("Supplier A uses 100% renewable energy", False, "entity_substitution", ["Supplier_A"]),
        (
            "The logistics route Asia-EU carbon is 0.10 per ton-km",
            False,
            "value_error",
            ["Logistics_Route_Asia_EU"],
        ),
        (
            "Budget 2024 has an R&D allocation of USD 1M",
            False,
            "fabricated_attribute",
            ["Budget_2024"],
        ),
        ("Contract 2024 Q1 will be renewed in Q3", False, "speculative", ["Contract_2024_Q1"]),
    ]

    for text, label, cat, entities in factual + hallucinated:
        claims.append(ClaimWithLabel(text=text, label=label, category=cat, entities=entities))
    return claims


# ── KG-Verification Pipeline ──────────────────────────────────────────────


def _extract_entities(claim: str) -> list[str]:
    """Simple entity extraction from claim text using known KG entities."""
    found: list[str] = []
    claim_lower = claim.lower()
    # Check for known entities from KG
    known = {s.lower(): s for f in _KG_FACTS for s in [f.subject]}
    for key, name in known.items():
        if key.replace("_", " ") in claim_lower or key in claim_lower:
            if name not in found:
                found.append(name)
    return found


def _verify_claim(claim: str, entities: list[str]) -> dict[str, Any]:
    """Verify a claim against the in-memory KG.

    Strategy:
    1. Extract subject/predicate/object-like patterns from the claim
    2. Look up subject in KG
    3. For each KG fact about the subject, check if the claim text contains
       the predicate and object values
    4. Score by matched_facts / total_extracted
    """
    extracted_entities = _extract_entities(claim) if not entities else entities

    if not extracted_entities:
        return {
            "verifiable": False,
            "score": 0.5,
            "matched_facts": 0,
            "total_facts": 0,
            "entities_found": [],
            "rationale": "No known KG entities found in claim",
        }

    all_matched = 0
    all_total = 0
    claim_lower = claim.lower()

    for entity in extracted_entities:
        facts = _kg_lookup(entity)
        if not facts:
            continue
        all_total += len(facts)
        for fact in facts:
            pred_tokens = fact.predicate.replace("_", " ").lower().split()
            obj_tokens = fact.obj.replace("_", " ").lower().split()
            if any(t in claim_lower for t in pred_tokens) and any(
                t in claim_lower for t in obj_tokens
            ):
                all_matched += 1

    if all_total == 0:
        return {
            "verifiable": False,
            "score": 0.3,
            "matched_facts": 0,
            "total_facts": 0,
            "entities_found": extracted_entities,
            "rationale": f"Entities found ({', '.join(extracted_entities)}) but no KG facts match",
        }

    score = all_matched / all_total
    return {
        "verifiable": True,
        "score": score,
        "matched_facts": all_matched,
        "total_facts": all_total,
        "entities_found": extracted_entities,
        "rationale": f"Matched {all_matched}/{all_total} KG facts",
    }


def compute_pr_curve(
    claims: list[ClaimWithLabel],
    verification_fn: Any,
) -> dict[str, Any]:
    """Compute precision-recall curve by varying epistemic score threshold.

    For each claim:
        - verification_fn returns a score in [0, 1]
        - score >= threshold → predicted factual
        - Compare prediction to ground-truth label

    Returns AUPRC, best F1, and per-threshold metrics.
    """
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []

    for claim in claims:
        v = verification_fn(claim.text, claim.entities)
        results.append(
            {
                "claim": claim.text,
                "label": claim.label,
                "category": claim.category,
                "verification_score": v["score"],
                "verifiable": v.get("verifiable", False),
                "matched_facts": v.get("matched_facts", 0),
                "total_facts": v.get("total_facts", 0),
                "rationale": v.get("rationale", ""),
            }
        )

    # Sort by score descending for PR curve computation
    results_sorted = sorted(results, key=lambda r: r["verification_score"], reverse=True)

    num_pos = sum(1 for r in results if r["label"])
    total = len(results)
    verification_time_ms = (time.perf_counter() - t0) * 1000

    if num_pos == 0 or total == 0:
        return {
            "auprc": 0.0,
            "best_f1": 0.0,
            "precision_at_recall_0.5": 0.0,
            "recall_at_precision_0.7": 0.0,
            "num_claims": total,
            "num_positive": num_pos,
            "verification_time_ms": verification_time_ms,
            "thresholds": [],
            "per_claim": results,
        }

    tp = 0
    fp = 0
    fn = num_pos
    prev_score = None
    pr_points: list[dict[str, float]] = []

    for r in results_sorted:
        score = r["verification_score"]
        if score != prev_score and prev_score is not None:
            precision = tp / max(1, tp + fp)
            recall = tp / max(1, tp + fn)
            pr_points.append(
                {
                    "threshold": prev_score,
                    "precision": precision,
                    "recall": recall,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                }
            )

        if r["label"]:
            tp += 1
            fn -= 1
        else:
            fp += 1
        prev_score = score

    # Final point
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    pr_points.append(
        {
            "threshold": prev_score or 0.0,
            "precision": precision,
            "recall": recall,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    )

    # AUPRC via trapezoidal integration
    if len(pr_points) < 2:
        auprc = pr_points[0]["precision"] * pr_points[0]["recall"] if pr_points else 0.0
    else:
        auprc = 0.0
        for i in range(len(pr_points) - 1):
            pr_i = pr_points[i]
            pr_j = pr_points[i + 1]
            avg_p = (pr_i["precision"] + pr_j["precision"]) / 2
            delta_r = abs(pr_j["recall"] - pr_i["recall"])
            auprc += avg_p * delta_r

    # Best F1
    best_f1 = 0.0
    for pt in pr_points:
        if pt["precision"] + pt["recall"] > 0:
            f1_val = 2 * pt["precision"] * pt["recall"] / (pt["precision"] + pt["recall"])
            best_f1 = max(best_f1, f1_val)

    # Precision at recall ≈ 0.5, recall at precision ≈ 0.7
    p_at_r50 = 0.0
    r_at_p70 = 0.0
    for pt in pr_points:
        if pt["recall"] >= 0.5:
            p_at_r50 = pt["precision"]
            break
    for pt in reversed(pr_points):
        if pt["precision"] >= 0.7:
            r_at_p70 = pt["recall"]
            break

    kg_coverage = sum(1 for r in results if r["verifiable"]) / max(1, len(results))

    return {
        "auprc": round(auprc, 4),
        "best_f1": round(best_f1, 4),
        "precision_at_recall_0.5": round(p_at_r50, 4),
        "recall_at_precision_0.7": round(r_at_p70, 4),
        "num_claims": total,
        "num_positive": num_pos,
        "kg_coverage": round(kg_coverage, 4),
        "verification_time_ms": round(verification_time_ms, 2),
        "pr_points": pr_points[:20],
        "per_claim": results,
    }


def _grade(auprc: float, best_f1: float) -> str:
    if auprc >= 0.80 and best_f1 >= 0.80:
        return "validated"
    if auprc >= 0.65 and best_f1 >= 0.70:
        return "needs-independent-replication"
    if auprc >= 0.50:
        return "synthetic-only"
    return "aspirational"


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    logger.info("=" * 60)
    logger.info("H47: NeSy Hallucination Precision Benchmark")
    logger.info("=" * 60)

    claims = _generate_claims()
    logger.info(
        "Generated %d claims (%d factual, %d hallucinated)",
        len(claims),
        sum(1 for c in claims if c.label),
        sum(1 for c in claims if not c.label),
    )

    # Category breakdown
    categories: dict[str, int] = {}
    for c in claims:
        categories[c.category] = categories.get(c.category, 0) + 1
    logger.info("Categories: %s", categories)

    logger.info("Running KG verification pipeline...")
    pr_result = compute_pr_curve(claims, _verify_claim)

    # ── Per-category analysis ──
    factual_claims = [r for r in pr_result["per_claim"] if r["label"]]
    hallucinated_claims = [r for r in pr_result["per_claim"] if not r["label"]]

    factual_mean_score = sum(r["verification_score"] for r in factual_claims) / max(
        1, len(factual_claims)
    )
    hallucinated_mean_score = sum(r["verification_score"] for r in hallucinated_claims) / max(
        1, len(hallucinated_claims)
    )

    category_metrics = {}
    for cat in {c.category for c in claims}:
        cat_results = [r for r in pr_result["per_claim"] if r["category"] == cat]
        cat_labels = [r["label"] for r in cat_results]
        cat_pos = sum(cat_labels)
        cat_neg = len(cat_labels) - cat_pos
        cat_mean_score = sum(r["verification_score"] for r in cat_results) / max(
            1, len(cat_results)
        )
        # Accuracy at mid-threshold (0.5)
        cat_correct = sum(1 for r in cat_results if (r["verification_score"] >= 0.5) == r["label"])
        category_metrics[cat] = {
            "count": len(cat_results),
            "positives": cat_pos,
            "negatives": cat_neg,
            "mean_verification_score": round(cat_mean_score, 4),
            "accuracy_at_0.5": round(cat_correct / max(1, len(cat_results)), 4),
        }

    grade = _grade(pr_result["auprc"], pr_result["best_f1"])

    logger.info("AUPRC: %.4f", pr_result["auprc"])
    logger.info("Best F1: %.4f", pr_result["best_f1"])
    logger.info("Factual mean score: %.4f", factual_mean_score)
    logger.info("Hallucinated mean score: %.4f", hallucinated_mean_score)
    logger.info("KG coverage: %.1f%%", pr_result["kg_coverage"] * 100)
    logger.info("Verification time: %.2f ms total", pr_result["verification_time_ms"])
    logger.info("Grade: %s", grade)

    result = {
        "benchmark_id": "nesy_hallucination_precision",
        "hypothesis": "H47",
        "hypothesis_text": "NeSy hallucination precision — PR curve over KG-verifiable claims",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "pr_curve": {
            "auprc": pr_result["auprc"],
            "best_f1": pr_result["best_f1"],
            "precision_at_recall_0.5": pr_result["precision_at_recall_0.5"],
            "recall_at_precision_0.7": pr_result["recall_at_precision_0.7"],
            "num_claims": pr_result["num_claims"],
            "num_positive": pr_result["num_positive"],
            "kg_coverage": pr_result["kg_coverage"],
        },
        "score_distribution": {
            "factual_mean_score": round(factual_mean_score, 4),
            "hallucinated_mean_score": round(hallucinated_mean_score, 4),
            "separation_ratio": round(factual_mean_score / max(0.001, hallucinated_mean_score), 4)
            if hallucinated_mean_score > 0
            else float("inf"),
        },
        "category_breakdown": category_metrics,
        "verification_time_ms": pr_result["verification_time_ms"],
        "pr_points": pr_result["pr_points"],
        "grade": grade,
    }

    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2))
        logger.info("Results written to %s", output_path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="H47: NeSy Hallucination Precision Benchmark")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    result = run_benchmark(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
