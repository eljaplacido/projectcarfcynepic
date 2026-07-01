# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""H50: Cross-lingual Ontology Gain — FI/PT QA, OG-RAG vs vector-only.

Hypothesis: Ontology-grounded retrieval improves cross-lingual QA by
mapping FI/PT queries to language-agnostic OWL concepts, reducing the
precision gap vs English-language vector-only RAG.

Approach:
    1. Define 20 domain queries in English, Finnish, and Portuguese
    2. Run OG-RAG concept retrieval on each language variant
    3. Measure concept recall consistency across languages
    4. Compare OG-RAG recall vs vector-only recall (simulated)

The key insight: OWL/SHACL concepts and SKOS labels are language-agnostic —
"Supplier" (EN), "Toimittaja" (FI), "Fornecedor" (PT) all map to the same
carf:Supplier OWL class. OG-RAG's concept lookup should find the concept
regardless of input language, where vector-only RAG often misses non-English
queries due to embedding model language bias.

Usage:
    python benchmarks/technical/og_rag/benchmark_cross_lingual_og_rag.py
    python benchmarks/technical/og_rag/benchmark_cross_lingual_og_rag.py -o results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.cross_lingual_og_rag")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"

# ── Cross-lingual Test Queries ────────────────────────────────────────────
# 10 queries, each in English, Finnish (FI), and Portuguese (PT).
# Ground truth: expected ontology concepts that SHOULD match regardless of language.

CROSS_LINGUAL_QUERIES = [
    {
        "id": "xl1",
        "domain": "sustainability",
        "en": "What are the Scope 1 emissions of the supplier?",
        "fi": "Mitkä ovat toimittajan Scope 1 -päästöt?",
        "pt": "Quais são as emissões de Escopo 1 do fornecedor?",
        "ground_truth_concepts": ["Supplier", "scope1Emissions"],
        "ground_truth_terms_en": ["scope", "emissions", "supplier"],
    },
    {
        "id": "xl2",
        "domain": "sustainability",
        "en": "Does the facility use renewable energy?",
        "fi": "Käyttääkö laitos uusiutuvaa energiaa?",
        "pt": "A instalação usa energia renovável?",
        "ground_truth_concepts": ["Facility", "energySource", "usesRenewableEnergy"],
        "ground_truth_terms_en": ["facility", "renewable", "energy"],
    },
    {
        "id": "xl3",
        "domain": "sustainability",
        "en": "What is the carbon intensity in the EU region?",
        "fi": "Mikä on hiili-intensiteetti EU:n alueella?",
        "pt": "Qual é a intensidade de carbono na região da UE?",
        "ground_truth_concepts": ["EconomicRegion", "avgCarbonIntensity"],
        "ground_truth_terms_en": ["carbon", "intensity", "eu", "region"],
    },
    {
        "id": "xl4",
        "domain": "procurement",
        "en": "Show contracts worth more than 500,000 euros",
        "fi": "Näytä sopimukset, joiden arvo ylittää 500 000 euroa",
        "pt": "Mostrar contratos com valor superior a 500.000 euros",
        "ground_truth_concepts": ["Contract", "value"],
        "ground_truth_terms_en": ["contract", "value", "500", "000"],
    },
    {
        "id": "xl5",
        "domain": "sustainability",
        "en": "Which suppliers have environmental certification?",
        "fi": "Millä toimittajilla on ympäristösertifiointi?",
        "pt": "Quais fornecedores têm certificação ambiental?",
        "ground_truth_concepts": ["Supplier", "isCertified"],
        "ground_truth_terms_en": ["supplier", "environmental", "certification"],
    },
    {
        "id": "xl6",
        "domain": "finance",
        "en": "What is the sustainability budget for this year?",
        "fi": "Mikä on kestävän kehityksen budjetti tälle vuodelle?",
        "pt": "Qual é o orçamento de sustentabilidade para este ano?",
        "ground_truth_concepts": ["Budget", "sustainabilityBudget"],
        "ground_truth_terms_en": ["sustainability", "budget", "year"],
    },
    {
        "id": "xl7",
        "domain": "procurement",
        "en": "How many transit days for the logistics route?",
        "fi": "Kuinka monta kuljetuspäivää logistiikkareitillä on?",
        "pt": "Quantos dias de trânsito para a rota logística?",
        "ground_truth_concepts": ["LogisticsRoute", "avgTransitDays"],
        "ground_truth_terms_en": ["transit", "days", "logistics", "route"],
    },
    {
        "id": "xl8",
        "domain": "sustainability",
        "en": "What is the carbon per ton-kilometer in our supply chain?",
        "fi": "Mikä on hiilidioksidipäästö tonnikilometriä kohden toimitusketjussamme?",
        "pt": "Qual é o carbono por tonelada-quilômetro na nossa cadeia de suprimentos?",
        "ground_truth_concepts": ["LogisticsRoute", "carbonPerTonKm"],
        "ground_truth_terms_en": ["carbon", "ton", "kilometer", "supply", "chain"],
    },
    {
        "id": "xl9",
        "domain": "sustainability",
        "en": "What industry is Supplier A in and where is it located?",
        "fi": "Millä toimialalla Toimittaja A toimii ja missä se sijaitsee?",
        "pt": "Em que setor o Fornecedor A atua e onde está localizado?",
        "ground_truth_concepts": ["Supplier", "industry", "locatedIn"],
        "ground_truth_terms_en": ["industry", "supplier", "located"],
    },
    {
        "id": "xl10",
        "domain": "finance",
        "en": "What is the annual revenue of the logistics supplier?",
        "fi": "Mikä on logistiikkatoimittajan vuosiliikevaihto?",
        "pt": "Qual é a receita anual do fornecedor de logística?",
        "ground_truth_concepts": ["Supplier", "annualRevenue"],
        "ground_truth_terms_en": ["annual", "revenue", "logistics", "supplier"],
    },
]


def _concept_recall(matched_results: list, ground_truth: list[str]) -> float:
    """Recall of ground truth concepts in matched set (checks all_labels)."""
    if not ground_truth:
        return 0.0
    gt_lower = {c.lower() for c in ground_truth}
    matched_labels = set()
    for r in matched_results:
        matched_labels.add(r.concept.label.lower())
        for lab in r.concept.all_labels:
            matched_labels.add(lab.lower())
    return len(gt_lower & matched_labels) / len(gt_lower)


def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    logger.info("=" * 60)
    logger.info("H50: Cross-lingual Ontology Gain Benchmark (FI/PT)")
    logger.info("=" * 60)

    try:
        from src.services.og_rag_service import OGRAGService, reset_og_rag_service
    except ImportError as exc:
        return {"benchmark_id": "cross_lingual_og_rag", "status": "skipped", "reason": str(exc)}

    reset_og_rag_service()
    service = OGRAGService()

    if not service.available:
        logger.warning("rdflib not installed — skipping")
        return {
            "benchmark_id": "cross_lingual_og_rag",
            "status": "skipped",
            "reason": "rdflib not installed",
        }

    ontology_path = _PROJECT_ROOT / "config" / "ontologies" / "carf.ttl"
    if not service.load_ontology(ontology_path):
        return {
            "benchmark_id": "cross_lingual_og_rag",
            "status": "skipped",
            "reason": "Ontology not found",
        }

    # ── Evaluate each language ────────────────────────────────────────────
    languages = ["en", "fi", "pt"]
    lang_results: dict[str, dict[str, Any]] = {}

    for lang in languages:
        recalls: list[float] = []
        concept_counts: list[int] = []

        for query in CROSS_LINGUAL_QUERIES:
            query_text = query[lang]
            response = service.retrieve_ontology_grounded(
                query_text,
                top_k=5,
                expand_hierarchy=True,
            )
            recall = _concept_recall(response.concepts_matched, query["ground_truth_concepts"])
            recalls.append(recall)
            concept_counts.append(len(response.concepts_matched))

        avg_recall = sum(recalls) / max(1, len(recalls))
        avg_concepts = sum(concept_counts) / max(1, len(concept_counts))
        lang_results[lang] = {
            "average_concept_recall": round(avg_recall, 4),
            "average_concepts_matched": round(avg_concepts, 2),
            "per_query_recalls": [round(r, 4) for r in recalls],
        }

        logger.info("  %s: recall=%.4f, avg_concepts=%.1f", lang.upper(), avg_recall, avg_concepts)

    # ── Cross-lingual consistency ─────────────────────────────────────────
    en_recall = lang_results["en"]["average_concept_recall"]
    fi_recall = lang_results["fi"]["average_concept_recall"]
    pt_recall = lang_results["pt"]["average_concept_recall"]

    fi_gap = en_recall - fi_recall
    pt_gap = en_recall - pt_recall
    avg_gap = (abs(fi_gap) + abs(pt_gap)) / 2.0

    # Consistency score: lower gap = more consistent
    consistency = 1.0 - min(avg_gap, 1.0)

    # ── Per-query cross-lingual analysis ──────────────────────────────────
    per_query = []
    for query in CROSS_LINGUAL_QUERIES:
        q_recalls = {}
        for lang in languages:
            response = service.retrieve_ontology_grounded(
                query[lang], top_k=5, expand_hierarchy=True
            )
            q_recalls[lang] = round(
                _concept_recall(response.concepts_matched, query["ground_truth_concepts"]), 4
            )
        per_query.append(
            {
                "id": query["id"],
                "domain": query["domain"],
                "en_text": query["en"],
                "fi_text": query["fi"],
                "pt_text": query["pt"],
                "ground_truth_concepts": query["ground_truth_concepts"],
                "recall_en": q_recalls["en"],
                "recall_fi": q_recalls["fi"],
                "recall_pt": q_recalls["pt"],
                "max_gap": round(max(q_recalls.values()) - min(q_recalls.values()), 4),
            }
        )

    def _grade(consistency: float, avg_recall: float) -> str:
        if consistency >= 0.75 and avg_recall >= 0.50:
            return "validated"
        if consistency >= 0.50:
            return "needs-independent-replication"
        if consistency >= 0.30:
            return "synthetic-only"
        return "aspirational"

    avg_recall_all = (en_recall + fi_recall + pt_recall) / 3.0
    grade = _grade(consistency, avg_recall_all)

    logger.info("Cross-lingual consistency: %.4f", consistency)
    logger.info("EN-FI gap: %.4f, EN-PT gap: %.4f", fi_gap, pt_gap)
    logger.info("Grade: %s", grade)

    result = {
        "benchmark_id": "cross_lingual_og_rag",
        "hypothesis": "H50",
        "hypothesis_text": "Cross-lingual ontology gain — OG-RAG FI/PT QA vs vector-only",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "languages_tested": languages,
        "num_queries": len(CROSS_LINGUAL_QUERIES),
        "ontology_concepts": service.concept_count,
        "language_results": lang_results,
        "cross_lingual": {
            "en_avg_recall": round(en_recall, 4),
            "fi_avg_recall": round(fi_recall, 4),
            "pt_avg_recall": round(pt_recall, 4),
            "fi_gap_vs_en": round(fi_gap, 4),
            "pt_gap_vs_en": round(pt_gap, 4),
            "avg_cross_lingual_gap": round(avg_gap, 4),
            "consistency_score": round(consistency, 4),
        },
        "per_query": per_query,
        "grade": grade,
    }

    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2))
        logger.info("Results written to %s", output_path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="H50: Cross-lingual Ontology Gain Benchmark")
    parser.add_argument("-o", "--output", type=str, default=None)
    args = parser.parse_args()
    result = run_benchmark(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
