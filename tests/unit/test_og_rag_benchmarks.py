"""Unit tests for G13/H50/H7 benchmarks (R5/G13)."""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


class TestG13Benchmark:
    def test_run_returns_dict(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import run_benchmark

        result = run_benchmark()
        assert isinstance(result, dict)
        assert result["benchmark_id"] == "og_rag_g13"

    def test_retrieval_section_exists(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import run_benchmark

        result = run_benchmark()
        assert result["retrieval"]["num_queries"] == 20

    def test_per_query_structure(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import run_benchmark

        result = run_benchmark()
        assert len(result["per_query"]) == 20
        for q in result["per_query"]:
            assert "id" in q
            assert "domain" in q
            assert "concept_recall" in q

    def test_structured_queries_higher_recall(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import run_benchmark

        result = run_benchmark()
        assert (
            result["retrieval"]["avg_structured_recall"]
            >= result["retrieval"]["avg_unstructured_recall"]
        )

    def test_grade_valid(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import run_benchmark

        result = run_benchmark()
        assert result["grade"] in (
            "validated",
            "needs-independent-replication",
            "synthetic-only",
            "aspirational",
        )

    def test_test_queries_well_formed(self):
        from benchmarks.technical.og_rag.benchmark_og_rag import OG_RAG_TEST_QUERIES

        assert len(OG_RAG_TEST_QUERIES) >= 15
        for q in OG_RAG_TEST_QUERIES:
            assert "id" in q
            assert "text" in q
            assert "ground_truth_concepts" in q
            assert "is_structured" in q


class TestH7H10WikidataBenchmark:
    def test_run_returns_dict(self):
        from benchmarks.technical.og_rag.benchmark_wikidata_og_rag import run_benchmark

        result = run_benchmark()
        assert isinstance(result, dict)
        assert result["benchmark_id"] == "wikidata_og_rag"

    def test_has_queries_defined(self):
        from benchmarks.technical.og_rag.benchmark_wikidata_og_rag import run_benchmark

        result = run_benchmark()
        assert result["harness_valid"] is True
        assert result["queries_defined"] == 10

    def test_sparql_queries_well_formed(self):
        from benchmarks.technical.og_rag.benchmark_wikidata_og_rag import WIKIDATA_TEST_QUERIES

        assert len(WIKIDATA_TEST_QUERIES) == 10
        for q in WIKIDATA_TEST_QUERIES:
            assert "sparql" in q
            assert "SELECT" in q["sparql"]
            assert "id" in q
            assert q["expected_min_results"] >= 0

    def test_categories_diverse(self):
        from benchmarks.technical.og_rag.benchmark_wikidata_og_rag import WIKIDATA_TEST_QUERIES

        categories = {q["category"] for q in WIKIDATA_TEST_QUERIES}
        assert len(categories) >= 3


class TestH50CrossLingualBenchmark:
    def test_run_returns_dict(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import run_benchmark

        result = run_benchmark()
        assert isinstance(result, dict)
        assert result["benchmark_id"] == "cross_lingual_og_rag"

    def test_three_languages_tested(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import run_benchmark

        result = run_benchmark()
        assert len(result["languages_tested"]) == 3
        assert "en" in result["languages_tested"]
        assert "fi" in result["languages_tested"]
        assert "pt" in result["languages_tested"]

    def test_cross_lingual_metrics(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import run_benchmark

        result = run_benchmark()
        assert "consistency_score" in result["cross_lingual"]
        assert 0.0 <= result["cross_lingual"]["consistency_score"] <= 1.0

    def test_per_query_has_all_languages(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import run_benchmark

        result = run_benchmark()
        for q in result["per_query"]:
            assert "recall_en" in q
            assert "recall_fi" in q
            assert "recall_pt" in q

    def test_grade_valid(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import run_benchmark

        result = run_benchmark()
        assert result["grade"] in (
            "validated",
            "needs-independent-replication",
            "synthetic-only",
            "aspirational",
        )

    def test_queries_have_all_languages(self):
        from benchmarks.technical.og_rag.benchmark_cross_lingual_og_rag import CROSS_LINGUAL_QUERIES

        for q in CROSS_LINGUAL_QUERIES:
            assert "en" in q
            assert "fi" in q
            assert "pt" in q
            assert len(q["en"]) > 0
            assert len(q["fi"]) > 0
            assert len(q["pt"]) > 0
