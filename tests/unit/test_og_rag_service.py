"""Unit tests for OG-RAG Ontology-Grounded Retrieval Service (R5/G13)."""

import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ["CARF_TEST_MODE"] = "1"


@pytest.fixture(autouse=True)
def reset_og_rag():
    from src.services.og_rag_service import reset_og_rag_service

    reset_og_rag_service()
    yield
    reset_og_rag_service()


class TestOGRAGServiceAvailability:
    def test_service_import(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        assert service is not None

    def test_service_available(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        assert service.available is True

    def test_singleton(self):
        from src.services.og_rag_service import get_og_rag_service

        s1 = get_og_rag_service()
        s2 = get_og_rag_service()
        assert s1 is s2

    def test_not_loaded_initially(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        assert not service.loaded
        assert service.concept_count == 0


class TestOGRAGOntologyLoading:
    def test_load_ontology(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        ontology_path = _PROJECT_ROOT / "config" / "ontologies" / "carf.ttl"
        result = service.load_ontology(ontology_path)
        assert result is True
        assert service.loaded
        assert service.concept_count > 0

    def test_load_nonexistent_returns_false(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        result = service.load_ontology("nonexistent.ttl")
        assert result is False
        assert not service.loaded

    def test_load_counts_concepts(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        ontology_path = _PROJECT_ROOT / "config" / "ontologies" / "carf.ttl"
        service.load_ontology(ontology_path)
        assert service.concept_count >= 40


class TestOGRAGRetrieval:
    def test_retrieve_basic_query(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("carbon emissions supplier", top_k=5)
        assert response.ontology_loaded
        assert len(response.concepts_matched) >= 1
        assert "Emissions" in [c.concept.label for c in response.concepts_matched]

    def test_retrieve_sustainability_supplier(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded(
            "What supplier has the most emissions?", top_k=3
        )
        concept_labels = [c.concept.label for c in response.concepts_matched]
        assert any("Supplier" in lab or "Emissions" in lab for lab in concept_labels)

    def test_retrieve_empty_query(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("", top_k=5)
        assert response.ontology_loaded
        assert len(response.concepts_matched) == 0

    def test_retrieve_not_loaded(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        response = service.retrieve_ontology_grounded("test query")
        assert not response.ontology_loaded
        assert len(response.concepts_matched) == 0

    def test_retrieve_response_structure(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("supplier contract budget", top_k=3)
        assert hasattr(response, "query")
        assert hasattr(response, "concepts_matched")
        assert hasattr(response, "query_expansion_terms")
        assert hasattr(response, "retrieval_time_ms")
        assert response.retrieval_time_ms >= 0

    def test_query_expansion_terms(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        terms = service.expand_query("supplier carbon emissions")
        assert len(terms) > 0
        assert isinstance(terms, list)
        assert all(isinstance(t, str) for t in terms)


class TestOGRAGConceptSearch:
    def test_get_concept_info(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        for uri, concept in service._index.by_uri.items():
            if any("Supplier" in lab for lab in concept.all_labels):
                info = service.get_concept_info(uri)
                assert info is not None
                assert any("Supplier" in lab or "Fornecedor" in lab for lab in info.all_labels)
                break

    def test_search_by_label(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        results = service.search_by_label("Supplier")
        assert len(results) >= 1
        assert any(
            "Supplier" in lab or "Fornecedor" in lab for r in results for lab in r.all_labels
        )

    def test_get_subconcepts(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        for uri, concept in service._index.by_uri.items():
            if concept.label == "Organization" or "Organization" in concept.all_labels:
                children = service.get_subconcepts(uri)
                assert len(children) >= 1
                assert any(
                    "Supplier" in lab or "Fornecedor" in lab
                    for c in children
                    for lab in c.all_labels
                )
                break


class TestOGRAGHierarchy:
    def test_concepts_have_depth(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        depths = {c.depth for c in service._index.by_uri.values()}
        assert 0 in depths  # Root concepts at depth 0

    def test_hierarchy_parent_child(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        for _uri, concept in service._index.by_uri.items():
            if concept.label == "Supplier":
                assert len(concept.parent_uris) >= 1
                parent_uris = [str(p) for p in concept.parent_uris]
                assert any("Organization" in p for p in parent_uris)
                break

    def test_hierarchy_expansion_increases_results(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        no_expand = service.retrieve_ontology_grounded(
            "supplier co2", top_k=3, expand_hierarchy=False
        )
        with_expand = service.retrieve_ontology_grounded(
            "supplier co2", top_k=3, expand_hierarchy=True
        )
        assert len(with_expand.concepts_matched) >= len(no_expand.concepts_matched)


class TestOGRAGCrossLingual:
    def test_english_label_matches(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("supplier", top_k=3)
        all_labs = set()
        for c in response.concepts_matched:
            all_labs.update(lab.lower() for lab in c.concept.all_labels)
        assert "supplier" in all_labs

    def test_finnish_label_matches(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("toimittaja", top_k=3)
        all_labs = set()
        for c in response.concepts_matched:
            all_labs.update(lab.lower() for lab in c.concept.all_labels)
        assert "supplier" in all_labs or "toimittaja" in all_labs

    def test_portuguese_label_matches(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        service.load_ontology(_PROJECT_ROOT / "config" / "ontologies" / "carf.ttl")
        response = service.retrieve_ontology_grounded("fornecedor", top_k=3)
        all_labs = set()
        for c in response.concepts_matched:
            all_labs.update(lab.lower() for lab in c.concept.all_labels)
        assert "supplier" in all_labs or "fornecedor" in all_labs


class TestOGRAGTokenization:
    def test_tokenize_simple(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        result = service._tokenize("carbon emissions supplier")
        assert isinstance(result, list)
        assert "carbon" in result

    def test_tokenize_punctuation(self):
        from src.services.og_rag_service import OGRAGService

        service = OGRAGService()
        result = service._tokenize("What are the Scope 1 emissions?")
        assert "what" in result
        assert "scope" in result
        assert "1" in result
        assert "?" not in "".join(result) if isinstance(result, list) else True
