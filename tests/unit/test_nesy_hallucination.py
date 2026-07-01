"""Unit tests for H47 NeSy Hallucination Precision Benchmark (R3)."""

import json
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


class TestH47ClaimGeneration:
    def test_generate_claims_balanced(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _generate_claims

        claims = _generate_claims()
        factual = [c for c in claims if c.label]
        hallucinated = [c for c in claims if not c.label]
        assert len(factual) == 25
        assert len(hallucinated) == 25
        assert len(claims) == 50

    def test_claims_have_categories(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _generate_claims

        claims = _generate_claims()
        categories = {c.category for c in claims}
        assert "entity_fact" in categories
        assert "value_error" in categories
        assert "fabricated_entity" in categories
        assert "speculative" in categories

    def test_claims_have_entities(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _generate_claims

        claims = _generate_claims()
        factual = [c for c in claims if c.label]
        for c in factual:
            assert len(c.entities) > 0, f"Factual claim '{c.text}' has no entities"


class TestH47KGLookup:
    def test_kg_lookup_known_entity(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _kg_lookup

        facts = _kg_lookup("Supplier_A")
        assert len(facts) >= 1
        assert any(f.predicate == "located_in" for f in facts)

    def test_kg_lookup_unknown_entity(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _kg_lookup

        facts = _kg_lookup("NonexistentCorp")
        assert len(facts) == 0

    def test_kg_lookup_with_predicate(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _kg_lookup

        facts = _kg_lookup("Supplier_A", "industry")
        assert len(facts) == 1
        assert facts[0].obj == "electronics"

    def test_kg_exists(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _kg_exists

        assert _kg_exists("Supplier_A") is True
        assert _kg_exists("Supplier_D") is False


class TestH47EntityExtraction:
    def test_extract_known_entity(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _extract_entities

        entities = _extract_entities("Supplier A is located in Vietnam")
        assert "Supplier_A" in entities

    def test_extract_no_entities(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _extract_entities

        entities = _extract_entities("The weather is nice today")
        assert len(entities) == 0


class TestH47Verification:
    def test_verify_factual_claim(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _verify_claim

        result = _verify_claim(
            "Supplier A is located in Vietnam",
            ["Supplier_A"],
        )
        assert result["verifiable"] is True
        assert result["matched_facts"] >= 1

    def test_verify_hallucinated_claim(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _verify_claim

        result = _verify_claim(
            "Supplier A is located in Thailand",
            ["Supplier_A"],
        )
        assert result["score"] < 0.5

    def test_verify_fabricated_entity(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import _verify_claim

        result = _verify_claim(
            "Supplier D is located in Brazil",
            ["Supplier_D"],
        )
        assert not result["verifiable"]


class TestH47PRCurve:
    def test_compute_pr_curve_structure(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import (
            _generate_claims,
            _verify_claim,
            compute_pr_curve,
        )

        claims = _generate_claims()
        result = compute_pr_curve(claims, _verify_claim)
        assert "auprc" in result
        assert "best_f1" in result
        assert 0.0 <= result["auprc"] <= 1.0
        assert 0.0 <= result["best_f1"] <= 1.0

    def test_pr_curve_has_points(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import (
            _generate_claims,
            _verify_claim,
            compute_pr_curve,
        )

        claims = _generate_claims()
        result = compute_pr_curve(claims, _verify_claim)
        assert len(result["pr_points"]) >= 2

    def test_pr_curve_monotonic_recall(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import (
            _generate_claims,
            _verify_claim,
            compute_pr_curve,
        )

        claims = _generate_claims()
        result = compute_pr_curve(claims, _verify_claim)
        recalls = [p["recall"] for p in result["pr_points"]]
        for i in range(len(recalls) - 1):
            assert recalls[i] <= recalls[i + 1] + 0.001


class TestH47Benchmark:
    def test_run_benchmark_returns_dict(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import run_benchmark

        result = run_benchmark()
        assert isinstance(result, dict)
        assert result["benchmark_id"] == "nesy_hallucination_precision"

    def test_run_benchmark_grade(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import run_benchmark

        result = run_benchmark()
        assert result["grade"] in (
            "validated",
            "needs-independent-replication",
            "synthetic-only",
            "aspirational",
        )

    def test_run_benchmark_auprc_positive(self):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import run_benchmark

        result = run_benchmark()
        assert result["pr_curve"]["auprc"] > 0.0
        assert result["pr_curve"]["best_f1"] > 0.0

    def test_run_benchmark_with_output(self, tmp_path):
        from benchmarks.technical.governance.benchmark_nesy_hallucination import run_benchmark

        output = tmp_path / "h47_result.json"
        run_benchmark(str(output))
        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded["benchmark_id"] == "nesy_hallucination_precision"
