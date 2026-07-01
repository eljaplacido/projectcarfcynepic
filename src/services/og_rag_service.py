"""OG-RAG Service — Ontology-Grounded Retrieval-Augmented Generation.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides ontology-grounded retrieval that upgrades CARF's symbolic RAG layer
from Horn clauses to OWL/SHACL concept-based retrieval.

Architecture:
    OWL ontology (Turtle) ─→ rdflib graph ─→ concept hierarchy + SPARQL
    User query ──→ concept extraction ──→ class/property expansion ──→ OG results
                                            ↓
    Vector results + Graph results + Symbolic results + OG results ──→ RRF fusion

Key capabilities:
    - Query-to-concept mapping via SKOS labels + class hierarchy
    - SPARQL query generation for structured ontology retrieval
    - Class-hierarchy-aware relevance scoring (subClassOf boost)
    - Cross-lingual label expansion via SKOS altLabel/prefLabel
    - Integration point: RAGService.retrieve_neurosymbolic_augmented

Usage:
    service = OGRAGService()
    service.load_ontology("config/ontologies/carf.ttl")
    results = service.retrieve_ontology_grounded("carbon emissions supplier", top_k=5)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.og_rag")

CARF_NS = "https://carf.cisuregen.com/ontology/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"


class OGConcept(BaseModel):
    """An ontology concept extracted from the knowledge graph."""

    uri: str
    label: str
    all_labels: list[str] = Field(default_factory=list)
    alt_labels: list[str] = Field(default_factory=list)
    parent_uris: list[str] = Field(default_factory=list)
    child_uris: list[str] = Field(default_factory=list)
    properties: list[str] = Field(default_factory=list)
    depth: int = 0


class OGRAGResult(BaseModel):
    """A single ontology-grounded retrieval result."""

    concept: OGConcept
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_type: str = Field(default="label")  # label, alt_label, parent, child, property
    query_terms_matched: list[str] = Field(default_factory=list)
    sparql_query: str | None = None
    instance_count: int = 0


class OGRAGResponse(BaseModel):
    """Full OG-RAG retrieval response."""

    query: str
    concepts_matched: list[OGRAGResult] = Field(default_factory=list)
    total_concepts: int = 0
    ontology_loaded: bool = False
    query_expansion_terms: list[str] = Field(default_factory=list)
    retrieval_time_ms: float = 0.0


@dataclass
class _ConceptIndex:
    """In-memory index of ontology concepts for fast lookup."""

    by_uri: dict[str, OGConcept] = field(default_factory=dict)
    by_label: dict[str, list[str]] = field(default_factory=dict)
    by_alt_label: dict[str, list[str]] = field(default_factory=dict)
    hierarchy: dict[str, list[str]] = field(default_factory=dict)
    properties: dict[str, list[str]] = field(default_factory=dict)


class OGRAGService:
    """Ontology-Grounded Retrieval Service."""

    def __init__(self) -> None:
        self._graph = None
        self._index = _ConceptIndex()
        self._loaded = False
        self._ontology_path: str | None = None

    @property
    def available(self) -> bool:
        """Check if rdflib is importable."""
        try:
            import rdflib  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def concept_count(self) -> int:
        return len(self._index.by_uri)

    def load_ontology(self, ontology_path: str | Path) -> bool:
        """Load an OWL/RDF ontology from Turtle file.

        Args:
            ontology_path: Path to .ttl ontology file.

        Returns:
            True if loaded successfully.
        """
        if not self.available:
            logger.warning("rdflib not installed — OG-RAG unavailable")
            return False

        from rdflib import Graph

        ontology_path = Path(ontology_path)
        if not ontology_path.exists():
            logger.warning("Ontology file not found: %s", ontology_path)
            return False

        self._ontology_path = str(ontology_path)
        self._graph = Graph()
        self._graph.parse(str(ontology_path), format="turtle")
        self._build_index()
        self._loaded = True
        logger.info(
            "OG-RAG loaded ontology %s: %d concepts indexed",
            ontology_path.name,
            self.concept_count,
        )
        return True

    def _build_index(self) -> None:
        """Build in-memory concept index from the RDF graph."""
        if self._graph is None:
            return

        from rdflib import URIRef
        from rdflib.namespace import RDF

        self._index = _ConceptIndex()

        OWL = URIRef("http://www.w3.org/2002/07/owl#Class")
        SKOS_CONCEPT = URIRef(f"{SKOS}Concept")
        SKOS_SCHEME = URIRef(f"{SKOS}ConceptScheme")
        RDFS_CLASS = URIRef(f"{RDFS}Class")
        SKOS_PREF = URIRef(f"{SKOS}prefLabel")
        SKOS_ALT = URIRef(f"{SKOS}altLabel")
        SKOS_BROADER = URIRef(f"{SKOS}broader")
        SKOS_NARROWER = URIRef(f"{SKOS}narrower")
        RDFS_SUBCLASS = URIRef(f"{RDFS}subClassOf")
        RDFS_LABEL = URIRef(f"{RDFS}label")
        RDFS_DOMAIN = URIRef(f"{RDFS}domain")

        # Step 1: Find all classes and SKOS concepts
        concept_uris: set[str] = set()
        for s, _p, _o in self._graph.triples((None, RDF.type, OWL)):
            concept_uris.add(str(s))
        for s, _p, _o in self._graph.triples((None, RDF.type, RDFS_CLASS)):
            concept_uris.add(str(s))
        for s, _p, _o in self._graph.triples((None, RDF.type, SKOS_CONCEPT)):
            concept_uris.add(str(s))
        for s, _p, _o in self._graph.triples((None, RDF.type, SKOS_SCHEME)):
            concept_uris.add(str(s))

        # Step 2: For each concept URI, collect labels and hierarchy
        for uri_str in concept_uris:
            uri = URIRef(uri_str)

            label = ""
            all_labels: list[str] = []
            for _s, _p, o in self._graph.triples((uri, RDFS_LABEL, None)):
                label = str(o)
                all_labels.append(str(o))
            for _s, _p, o in self._graph.triples((uri, SKOS_PREF, None)):
                if not label:
                    label = str(o)
                all_labels.append(str(o))
            if not label:
                label = uri_str.split("#")[-1] if "#" in uri_str else uri_str.split("/")[-1]

            alt_labels: list[str] = []
            for _s, _p, o in self._graph.triples((uri, SKOS_ALT, None)):
                alt_labels.append(str(o))

            parent_uris: list[str] = []
            for _s, _p, o in self._graph.triples((uri, RDFS_SUBCLASS, None)):
                parent_uris.append(str(o))
            for _s, _p, o in self._graph.triples((uri, SKOS_BROADER, None)):
                parent_uris.append(str(o))

            child_uris: list[str] = []
            for s, _p, _o in self._graph.triples((None, RDFS_SUBCLASS, uri)):
                child_uris.append(str(s))
            for s, _p, _o in self._graph.triples((None, SKOS_NARROWER, uri)):
                child_uris.append(str(s))

            props: list[str] = []
            for s, _p, _o in self._graph.triples((None, RDFS_DOMAIN, uri)):
                prop_name = str(s).split("#")[-1] if "#" in str(s) else str(s).split("/")[-1]
                props.append(prop_name)

            concept = OGConcept(
                uri=uri_str,
                label=label,
                all_labels=list(dict.fromkeys([label] + all_labels + alt_labels)),
                alt_labels=alt_labels,
                parent_uris=parent_uris,
                child_uris=child_uris,
                properties=props,
                depth=0,
            )
            self._index.by_uri[uri_str] = concept

            label_lower = label.lower()
            self._index.by_label.setdefault(label_lower, []).append(uri_str)
            for lab in all_labels:
                lab_lower = lab.lower()
                if lab_lower != label_lower:
                    self._index.by_label.setdefault(lab_lower, []).append(uri_str)
            for alt in alt_labels:
                self._index.by_alt_label.setdefault(alt.lower(), []).append(uri_str)
            for child in child_uris:
                self._index.hierarchy.setdefault(str(child), []).append(uri_str)

        # Step 3: Compute depth via BFS from roots
        self._compute_depths()

        # Step 4: Index properties
        for s, _p, _o in self._graph:
            if str(s).startswith(CARF_NS) and str(_p) not in (
                RDF_TYPE,
                str(RDFS_LABEL),
                str(RDFS_SUBCLASS),
                str(SKOS_PREF),
                str(SKOS_ALT),
                str(SKOS_BROADER),
                str(SKOS_NARROWER),
            ):
                prop_name = str(_p).split("#")[-1] if "#" in str(_p) else str(_p).split("/")[-1]
                self._index.properties.setdefault(prop_name.lower(), []).append(str(s))

    def _compute_depths(self) -> None:
        """Assign depth values via BFS from root concepts (no parents)."""
        roots = [uri for uri, c in self._index.by_uri.items() if not c.parent_uris]
        seen: set[str] = set()
        queue: list[tuple[str, int]] = [(r, 0) for r in roots]
        while queue:
            uri, depth = queue.pop(0)
            if uri in seen:
                continue
            seen.add(uri)
            if uri in self._index.by_uri:
                self._index.by_uri[uri].depth = depth
            for child in self._index.by_uri.get(uri, OGConcept(uri=uri, label="")).child_uris:
                if child not in seen:
                    queue.append((child, depth + 1))

    def _tokenize(self, query: str) -> list[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric."""
        return re.findall(r"[a-zA-Z0-9_]+", query.lower())

    def _concept_label_similarity(
        self, tokens: list[str], concept: OGConcept
    ) -> tuple[float, list[str], str]:
        """Compute token overlap similarity between query and concept labels.

        Returns (score, matched_tokens, match_type).
        """
        label_tokens = self._tokenize(concept.label)
        matches = [t for t in tokens if t in label_tokens]
        if matches:
            precision = len(matches) / len(label_tokens) if label_tokens else 0.0
            recall = len(matches) / len(tokens) if tokens else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            return (f1, matches, "label")

        for lab in concept.all_labels:
            if lab == concept.label:
                continue
            lab_tokens = self._tokenize(lab)
            lab_matches = [t for t in tokens if t in lab_tokens]
            if lab_matches:
                precision = len(lab_matches) / len(lab_tokens) if lab_tokens else 0.0
                recall = len(lab_matches) / len(tokens) if tokens else 0.0
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )
                return (f1 * 1.2, lab_matches, "alt_label")

        return (0.0, [], "")

    def retrieve_ontology_grounded(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.01,
        expand_hierarchy: bool = True,
    ) -> OGRAGResponse:
        """Retrieve ontology-grounded concepts for a natural language query.

        Args:
            query: Natural language query text.
            top_k: Maximum concepts to return.
            min_score: Minimum relevance score threshold.
            expand_hierarchy: Include parent/child concepts for matched items.

        Returns:
            OGRAGResponse with matched concepts and expansion terms.
        """
        import time

        t0 = time.perf_counter()

        if not self._loaded:
            return OGRAGResponse(query=query, ontology_loaded=False)

        tokens = self._tokenize(query)

        # Phase 1: Direct concept matching
        scored: list[tuple[float, OGConcept, str, list[str]]] = []
        for _uri, concept in self._index.by_uri.items():
            score, matched, match_type = self._concept_label_similarity(tokens, concept)
            if score > 0:
                scored.append((score, concept, match_type, matched))

        # Phase 2: Hierarchy expansion
        if expand_hierarchy:
            expanded: dict[str, tuple[float, str, list[str]]] = {}
            for score, concept, match_type, matched in scored:
                expanded[concept.uri] = (score, match_type, matched)
                # Boost children (more specific concepts are more relevant)
                for child in concept.child_uris:
                    if child in self._index.by_uri and child not in expanded:
                        child_score = score * 0.7
                        expanded[child] = (child_score, "child", matched)
                # Include parents (less specific, lower weight)
                for parent in concept.parent_uris:
                    if parent in self._index.by_uri and parent not in expanded:
                        parent_score = score * 0.35
                        expanded[parent] = (parent_score, "parent", matched)

            scored = []
            for uri, (score, mt, matched) in expanded.items():
                if uri in self._index.by_uri:
                    scored.append((score, self._index.by_uri[uri], mt, matched))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Phase 3: Build results
        results: list[OGRAGResult] = []
        seen_uris: set[str] = set()
        expansion_terms: set[str] = set()

        for score, concept, match_type, matched in scored[:top_k]:
            if concept.uri in seen_uris:
                continue
            if score < min_score:
                continue
            seen_uris.add(concept.uri)

            results.append(
                OGRAGResult(
                    concept=concept,
                    relevance_score=round(min(score, 1.0), 4),
                    match_type=match_type,
                    query_terms_matched=matched,
                    sparql_query=self._build_sparql_query(concept),
                    instance_count=0,
                )
            )

        # Build expansion terms from matched concepts
        for r in results:
            expansion_terms.update(self._tokenize(r.concept.label))
            for alt in r.concept.alt_labels:
                expansion_terms.update(self._tokenize(alt))
            # Add parent/child labels
            for parent_uri in r.concept.parent_uris:
                if parent_uri in self._index.by_uri:
                    expansion_terms.update(self._tokenize(self._index.by_uri[parent_uri].label))

        return OGRAGResponse(
            query=query,
            concepts_matched=results,
            total_concepts=self.concept_count,
            ontology_loaded=True,
            query_expansion_terms=list(expansion_terms),
            retrieval_time_ms=(time.perf_counter() - t0) * 1000,
        )

    def _build_sparql_query(self, concept: OGConcept) -> str:
        """Build a sample SPARQL query for the concept (for explainability)."""
        label = concept.label.replace("'", "\\'")
        return (
            f"SELECT ?instance WHERE {{\n  ?instance rdf:type/rdfs:subClassOf* carf:{label} .\n}}"
        )

    def expand_query(self, query: str) -> list[str]:
        """Expand query terms using ontology concept hierarchy.

        Returns additional search terms derived from ontology-grounded concepts
        that can be injected into vector/BM25 retrieval for hybrid OG-RAG.
        """
        response = self.retrieve_ontology_grounded(query, top_k=5, expand_hierarchy=True)
        return list(dict.fromkeys(response.query_expansion_terms))

    def get_concept_info(self, concept_id: str) -> OGConcept | None:
        """Get detailed concept information by exact URI."""
        return self._index.by_uri.get(concept_id)

    def get_subconcepts(self, parent_uri: str) -> list[OGConcept]:
        """Get all direct sub-concepts of a parent concept."""
        parent = self._index.by_uri.get(parent_uri)
        if not parent:
            return []
        return [self._index.by_uri[c] for c in parent.child_uris if c in self._index.by_uri]

    def search_by_label(self, label: str) -> list[OGConcept]:
        """Find concepts by label substring match across all language variants."""
        label_lower = label.lower()
        results = []
        seen: set[str] = set()
        for uri, concept in self._index.by_uri.items():
            if uri in seen:
                continue
            for lab in concept.all_labels:
                if label_lower in lab.lower():
                    results.append(concept)
                    seen.add(uri)
                    break
        return results


_og_rag_instance: OGRAGService | None = None


def get_og_rag_service() -> OGRAGService:
    """Get or create the OG-RAG service singleton."""
    global _og_rag_instance
    if _og_rag_instance is None:
        _og_rag_instance = OGRAGService()
    return _og_rag_instance


def reset_og_rag_service() -> None:
    """Reset the singleton (test helper)."""
    global _og_rag_instance
    _og_rag_instance = None
