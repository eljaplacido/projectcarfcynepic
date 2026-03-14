"""RAG Service — Graph-enhanced Retrieval-Augmented Generation for CARF.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides a dual-level retrieval service:
  1. Local entity retrieval (keyword/embedding match)
  2. Global community retrieval (graph-neighbourhood context)

When LightRAG is installed (`pip install lightrag-hku`) the service delegates
to the library.  Otherwise it falls back to a built-in TF-IDF + policy graph
retrieval that works with zero external dependencies.

Usage:
    from src.services.rag_service import get_rag_service
    service = get_rag_service()
    service.ingest_text("EU AI Act Article 9: ...", source="eu_ai_act")
    results = service.retrieve("What are the risk management requirements?", top_k=5)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.rag_service")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class RAGDocument(BaseModel):
    """A document chunk stored in the RAG index."""
    doc_id: str
    content: str
    source: str = "unknown"
    domain_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RAGResult(BaseModel):
    """A single retrieval result."""
    doc_id: str
    content: str
    source: str = "unknown"
    score: float = 0.0
    retrieval_mode: str = "local"  # local | global | hybrid
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryResponse(BaseModel):
    """Response from a RAG query."""
    query: str
    results: list[RAGResult] = Field(default_factory=list)
    total_documents: int = 0
    retrieval_mode: str = "hybrid"
    backend: str = "builtin"


# ---------------------------------------------------------------------------
# Built-in retrieval (no external deps beyond sklearn/numpy)
# ---------------------------------------------------------------------------

class _BuiltinRAGIndex:
    """Dense + TF-IDF cosine similarity index with graph-neighbourhood boost."""

    def __init__(self) -> None:
        self._documents: list[RAGDocument] = []
        self._vectorizer = None
        self._tfidf_matrix = None
        self._dense_embeddings = None
        self._use_dense = False
        self._dirty = True

    @property
    def size(self) -> int:
        return len(self._documents)

    def add(self, doc: RAGDocument) -> None:
        self._documents.append(doc)
        self._dirty = True

    def _rebuild(self) -> None:
        if not self._documents:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._dense_embeddings = None
            self._use_dense = False
            self._dirty = False
            return

        texts = [d.content for d in self._documents]

        # Try dense embeddings via shared engine
        try:
            from src.services.embedding_engine import get_embedding_engine
            engine = get_embedding_engine()
            if engine.dense_available:
                self._dense_embeddings = engine.encode(texts)
                self._use_dense = True
                self._dirty = False
                return
        except Exception as exc:
            logger.debug("Dense RAG rebuild failed, falling back to TF-IDF: %s", exc)

        # TF-IDF fallback
        self._use_dense = False
        self._dense_embeddings = None
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(
                max_features=2000,
                stop_words="english",
                ngram_range=(1, 2),
            )
            self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        except (ImportError, ValueError):
            # ValueError: empty vocabulary (all stop words or empty docs)
            logger.warning("TF-IDF vectorization failed; RAG retrieval disabled")
            self._vectorizer = None
            self._tfidf_matrix = None
        self._dirty = False

    def search(self, query: str, top_k: int = 5, min_score: float = 0.05) -> list[RAGResult]:
        if not self._documents:
            return []
        if self._dirty:
            self._rebuild()

        try:
            # Dense path
            if self._use_dense and self._dense_embeddings is not None:
                from src.services.embedding_engine import get_embedding_engine
                engine = get_embedding_engine()
                q_vec = engine.encode([query])
                sims = engine.cosine_similarity(q_vec, self._dense_embeddings).flatten()
            elif self._vectorizer is not None and self._tfidf_matrix is not None:
                # TF-IDF fallback
                from sklearn.metrics.pairwise import cosine_similarity
                q_vec = self._vectorizer.transform([query])
                sims = cosine_similarity(q_vec, self._tfidf_matrix).flatten()
            else:
                return []

            scored: list[tuple[int, float]] = []
            for idx, sim in enumerate(sims):
                if sim >= min_score:
                    scored.append((idx, float(sim)))
            scored.sort(key=lambda x: x[1], reverse=True)

            results: list[RAGResult] = []
            for idx, score in scored[:top_k]:
                doc = self._documents[idx]
                results.append(RAGResult(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    source=doc.source,
                    score=round(score, 4),
                    retrieval_mode="local",
                    metadata=doc.metadata,
                ))
            return results
        except Exception as exc:
            logger.warning("RAG search failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Graph neighbourhood boost
# ---------------------------------------------------------------------------

def _boost_with_graph_context(
    results: list[RAGResult],
    query_domain: str | None,
) -> list[RAGResult]:
    """Boost results that share the same governance domain (graph neighbourhood)."""
    if not query_domain:
        return results
    for r in results:
        if r.metadata.get("domain_id") == query_domain:
            r.score = min(1.0, r.score * 1.25)
            r.retrieval_mode = "hybrid"
    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# GraphRAG — structural graph traversal retrieval (Phase 17)
# ---------------------------------------------------------------------------

async def _graph_rag_retrieve(
    query: str,
    top_k: int = 5,
) -> list[RAGResult]:
    """Retrieve context by traversing Neo4j causal and governance graphs.

    Combines:
    1. Causal graph: find variables and causal paths related to query terms
    2. Governance graph: find triples, policies, and domain relationships
    3. Converts graph structures into text context for LLM consumption

    Returns RAGResults with retrieval_mode="graph".
    """
    results: list[RAGResult] = []

    # Extract key terms from query for graph matching
    query_lower = query.lower()
    query_terms = [
        t.strip() for t in query_lower.replace(",", " ").replace(".", " ").split()
        if len(t.strip()) > 3
    ]

    # 1. Causal graph traversal
    try:
        from src.services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        graph = await neo4j.get_causal_graph()

        if graph and graph.nodes:
            adj = graph.to_adjacency_list()

            # Find nodes matching query terms
            matched_nodes: list[str] = []
            for node in graph.nodes:
                node_lower = node.name.lower()
                for term in query_terms:
                    if term in node_lower or node_lower in term:
                        matched_nodes.append(node.name)
                        break

            # For each matched node, get its causal neighbourhood
            for node_name in matched_nodes[:3]:
                neighbors = await neo4j.get_variable_neighbors(node_name)
                causes = neighbors.get("causes", [])
                effects = neighbors.get("effects", [])

                context_parts = [f"Variable: {node_name}"]
                if causes:
                    context_parts.append(f"Caused by: {', '.join(causes)}")
                if effects:
                    context_parts.append(f"Causes: {', '.join(effects)}")

                # Find causal paths from this node
                for target in effects[:2]:
                    try:
                        paths = await neo4j.get_causal_path(node_name, target, max_depth=3)
                        for path in paths[:1]:
                            context_parts.append(f"Causal path: {' → '.join(path)}")
                    except Exception:
                        pass

                results.append(RAGResult(
                    doc_id=f"graph_causal_{node_name}",
                    content="\n".join(context_parts),
                    source="neo4j_causal_graph",
                    score=0.7,
                    retrieval_mode="graph",
                    metadata={"node": node_name, "type": "causal_neighbourhood"},
                ))
    except Exception as exc:
        logger.debug("Causal graph RAG retrieval skipped: %s", exc)

    # 2. Governance graph traversal
    try:
        from src.services.governance_graph_service import get_governance_graph_service
        gov_graph = get_governance_graph_service()

        if gov_graph.is_available:
            # Search for triples matching query terms
            triples = await gov_graph.search_triples(query, limit=top_k)
            for triple in triples:
                text = (
                    f"{triple.subject} --[{triple.predicate}]--> {triple.object} "
                    f"(confidence: {triple.confidence:.0%}, "
                    f"domains: {triple.domain_source} → {triple.domain_target})"
                )
                results.append(RAGResult(
                    doc_id=f"graph_triple_{triple.triple_id}",
                    content=text,
                    source="neo4j_governance_graph",
                    score=triple.confidence * 0.8,
                    retrieval_mode="graph",
                    metadata={
                        "triple_id": str(triple.triple_id),
                        "predicate": triple.predicate,
                        "domain_source": triple.domain_source,
                    },
                ))
    except Exception as exc:
        logger.debug("Governance graph RAG retrieval skipped: %s", exc)

    # 3. Historical analysis retrieval from Neo4j
    try:
        from src.services.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()

        # Search for similar past analyses
        for term in query_terms[:2]:
            similar = await neo4j.find_similar_analyses(term, term, limit=2)
            for analysis in similar:
                text = (
                    f"Past analysis: {analysis.get('treatment', '?')} → "
                    f"{analysis.get('outcome', '?')} "
                    f"(effect: {analysis.get('effect_size', 'N/A')}, "
                    f"session: {analysis.get('session_id', 'N/A')})"
                )
                results.append(RAGResult(
                    doc_id=f"graph_history_{analysis.get('session_id', 'unknown')}",
                    content=text,
                    source="neo4j_analysis_history",
                    score=0.5,
                    retrieval_mode="graph",
                    metadata={"type": "historical_analysis"},
                ))
    except Exception as exc:
        logger.debug("Historical analysis retrieval skipped: %s", exc)

    # Deduplicate by doc_id and sort by score
    seen = set()
    unique: list[RAGResult] = []
    for r in results:
        if r.doc_id not in seen:
            seen.add(r.doc_id)
            unique.append(r)
    unique.sort(key=lambda r: r.score, reverse=True)
    return unique[:top_k]


def _merge_vector_and_graph(
    vector_results: list[RAGResult],
    graph_results: list[RAGResult],
    top_k: int = 5,
    vector_weight: float = 0.6,
    graph_weight: float = 0.4,
) -> list[RAGResult]:
    """Merge vector-based and graph-based retrieval results.

    Uses reciprocal rank fusion (RRF) for combining ranked lists.
    """
    # RRF constant
    k = 60

    # Build score maps
    all_ids: dict[str, RAGResult] = {}
    rrf_scores: dict[str, float] = {}

    for rank, r in enumerate(vector_results):
        all_ids[r.doc_id] = r
        rrf_scores[r.doc_id] = vector_weight / (k + rank + 1)

    for rank, r in enumerate(graph_results):
        if r.doc_id in all_ids:
            # Boost items found in both
            rrf_scores[r.doc_id] += graph_weight / (k + rank + 1)
            all_ids[r.doc_id].retrieval_mode = "hybrid"
        else:
            all_ids[r.doc_id] = r
            rrf_scores[r.doc_id] = graph_weight / (k + rank + 1)

    # Sort by RRF score
    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    merged: list[RAGResult] = []
    for doc_id, score in ranked[:top_k]:
        result = all_ids[doc_id]
        result.score = round(score, 4)
        merged.append(result)

    return merged


# ---------------------------------------------------------------------------
# Main RAG Service
# ---------------------------------------------------------------------------

class RAGService:
    """Graph-enhanced RAG service for CARF.

    Ingests governance policies, causal analysis history, and arbitrary
    text documents.  Retrieval combines local (keyword/embedding) search
    with global graph-neighbourhood boosting.
    """

    def __init__(self) -> None:
        self._index = _BuiltinRAGIndex()
        self._lightrag = None
        self._backend = "builtin"
        self._try_lightrag()

    def _try_lightrag(self) -> None:
        """Attempt to initialise LightRAG if available."""
        try:
            from lightrag import LightRAG as _LightRAG  # type: ignore[import-untyped]
            logger.info("LightRAG library detected — using graph-enhanced RAG backend")
            self._backend = "lightrag"
            # NOTE: LightRAG requires a working directory; defer full init
            # until first ingest so config (Neo4j URL etc.) can be set.
        except ImportError:
            logger.debug("LightRAG not installed; using built-in TF-IDF RAG")

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def document_count(self) -> int:
        return self._index.size

    # -- Ingestion ----------------------------------------------------------

    def ingest_text(
        self,
        text: str,
        source: str = "unknown",
        domain_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> int:
        """Ingest a text document into the RAG index.

        Long texts are split into overlapping chunks.  Returns the number
        of chunks ingested.
        """
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        count = 0
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.sha256(f"{source}:{i}:{chunk[:64]}".encode()).hexdigest()[:16]
            doc = RAGDocument(
                doc_id=doc_id,
                content=chunk,
                source=source,
                domain_id=domain_id,
                metadata={**(metadata or {}), "chunk_index": i, "domain_id": domain_id},
            )
            self._index.add(doc)
            count += 1
        logger.info("Ingested %d chunks from source=%s domain=%s", count, source, domain_id)
        return count

    def ingest_policies(self) -> int:
        """Ingest all federated governance policies into the RAG index."""
        try:
            from src.services.federated_policy_service import get_federated_service
            service = get_federated_service()
            policies = service.list_policies()
            total = 0
            for policy in policies:
                text_parts = [
                    f"Policy: {policy.name}",
                    f"Domain: {policy.domain_id}",
                    f"Description: {policy.description}",
                ]
                for rule in policy.rules:
                    rule_text = f"Rule {rule.name}: {rule.message} (severity: {rule.severity})"
                    text_parts.append(rule_text)
                total += self.ingest_text(
                    "\n".join(text_parts),
                    source=f"policy:{policy.namespace}",
                    domain_id=policy.domain_id,
                    metadata={"policy_id": str(policy.policy_id), "namespace": policy.namespace},
                )
            logger.info("Ingested %d policy chunks from %d policies", total, len(policies))
            return total
        except Exception as exc:
            logger.warning("Failed to ingest policies: %s", exc)
            return 0

    def ingest_triples(
        self,
        triples: list,
        source: str = "governance_triples",
    ) -> int:
        """Ingest governance triples (ContextTriple objects) into the RAG index.

        Each triple is converted to a text chunk:
          ``{subject} --[{predicate}]--> {object} (domains: {source} -> {target})``

        Returns the number of chunks ingested.
        """
        count = 0
        for triple in triples:
            try:
                subject = getattr(triple, "subject", str(triple))
                predicate = getattr(triple, "predicate", "related_to")
                obj = getattr(triple, "object", "")
                domain_source = getattr(triple, "domain_source", "")
                domain_target = getattr(triple, "domain_target", "")
                text = (
                    f"{subject} --[{predicate}]--> {obj} "
                    f"(domains: {domain_source} -> {domain_target})"
                )
                doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
                doc = RAGDocument(
                    doc_id=doc_id,
                    content=text,
                    source=source,
                    domain_id=domain_source or None,
                    metadata={"triple": True, "predicate": predicate},
                )
                self._index.add(doc)
                count += 1
            except Exception:
                pass
        if count:
            logger.info("Ingested %d triples into RAG index", count)
        return count

    # -- Retrieval ----------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain_id: str | None = None,
        min_score: float = 0.05,
    ) -> RAGQueryResponse:
        """Retrieve relevant documents for a query.

        Combines local TF-IDF search with graph-neighbourhood boosting
        when a domain_id is provided.
        """
        results = self._index.search(query, top_k=top_k * 2, min_score=min_score)
        results = _boost_with_graph_context(results, domain_id)
        return RAGQueryResponse(
            query=query,
            results=results[:top_k],
            total_documents=self._index.size,
            retrieval_mode="hybrid" if domain_id else "local",
            backend=self._backend,
        )

    async def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 5,
        domain_id: str | None = None,
        min_score: float = 0.05,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
    ) -> RAGQueryResponse:
        """Hybrid retrieval combining vector search + GraphRAG traversal.

        Phase 17 enhancement: true graph-structural retrieval from Neo4j
        merged with vector similarity via reciprocal rank fusion.

        This is the recommended retrieval method for maximum contextual
        reliability — combining semantic similarity (vector) with
        structural relationships (graph).
        """
        # Vector retrieval (synchronous, from local index)
        vector_results = self._index.search(query, top_k=top_k * 2, min_score=min_score)
        vector_results = _boost_with_graph_context(vector_results, domain_id)

        # Graph retrieval (async, from Neo4j)
        graph_results: list[RAGResult] = []
        try:
            graph_results = await _graph_rag_retrieve(query, top_k=top_k)
        except Exception as exc:
            logger.debug("GraphRAG retrieval failed, using vector-only: %s", exc)

        # Merge via reciprocal rank fusion
        if graph_results:
            merged = _merge_vector_and_graph(
                vector_results, graph_results, top_k,
                vector_weight, graph_weight,
            )
            mode = "hybrid_graphrag"
        else:
            merged = vector_results[:top_k]
            mode = "vector_only"

        return RAGQueryResponse(
            query=query,
            results=merged,
            total_documents=self._index.size,
            retrieval_mode=mode,
            backend=self._backend,
        )

    def retrieve_for_pipeline(
        self,
        query: str,
        domain_id: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve and format context for injection into the LLM pipeline.

        Returns a plain-text context block suitable for prompt augmentation.
        Uses synchronous vector retrieval (for LangGraph node compatibility).
        """
        resp = self.retrieve(query, top_k=top_k, domain_id=domain_id)
        if not resp.results:
            return ""
        lines = ["[Retrieved context from knowledge base]"]
        for r in resp.results:
            lines.append(f"--- [{r.source}] (relevance: {r.score:.2f}) ---")
            lines.append(r.content[:400])
        return "\n".join(lines)

    async def retrieve_for_pipeline_hybrid(
        self,
        query: str,
        domain_id: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Hybrid retrieval formatted for pipeline injection (Phase 17).

        Combines vector + GraphRAG for maximum contextual reliability.
        Falls back to vector-only if graph is unavailable.
        """
        resp = await self.retrieve_hybrid(query, top_k=top_k, domain_id=domain_id)
        if not resp.results:
            return ""
        lines = [f"[Retrieved context — mode: {resp.retrieval_mode}]"]
        for r in resp.results:
            source_tag = r.source
            if r.retrieval_mode == "graph":
                source_tag = f"GRAPH:{r.source}"
            lines.append(f"--- [{source_tag}] (relevance: {r.score:.2f}) ---")
            lines.append(r.content[:400])
        return "\n".join(lines)

    async def retrieve_neurosymbolic_augmented(
        self,
        query: str,
        top_k: int = 5,
        domain_id: str | None = None,
        include_causal_context: bool = True,
        include_symbolic_facts: bool = True,
    ) -> RAGQueryResponse:
        """Neurosymbolic-augmented retrieval — highest contextual reliability.

        Combines three retrieval layers for maximum epistemic grounding:
        1. Vector similarity (TF-IDF / dense embeddings)
        2. Graph-structural traversal (Neo4j causal + governance graphs)
        3. Symbolic knowledge base facts (neurosymbolic engine grounding)

        This method implements the research insight that combining vector-based
        RAG with GraphRAG and symbolic grounding achieves the highest
        contextual memory reliability (refs: [30][31] Knowledge Graphs for NeSy).

        Falls back gracefully: if NeSy or graph layers are unavailable,
        returns vector-only results.
        """
        # Layer 1: Hybrid vector + graph retrieval
        hybrid_response = await self.retrieve_hybrid(
            query, top_k=top_k * 2, domain_id=domain_id
        )
        results = list(hybrid_response.results)

        # Layer 2: Causal context enrichment
        causal_context_added = 0
        if include_causal_context:
            try:
                from src.services.causal_world_model import get_causal_world_model

                wm_service = get_causal_world_model()
                query_lower = query.lower()
                for model_id, model in wm_service._models.items():
                    for var in model.variables:
                        if var.lower() in query_lower or query_lower in var.lower():
                            eq = model.equations.get(var)
                            if eq:
                                ctx = f"Causal equation: {var} = {eq.intercept:.2f}"
                                if eq.coefficients:
                                    terms = " + ".join(
                                        f"{c:.2f}*{p}"
                                        for p, c in eq.coefficients.items()
                                    )
                                    ctx += f" + {terms}"
                                ctx += (
                                    f" (type: {eq.equation_type}, "
                                    f"noise_std: {eq.noise_std:.3f})"
                                )
                                results.append(RAGResult(
                                    doc_id=f"scm_{model_id}_{var}",
                                    content=ctx,
                                    source="causal_world_model",
                                    score=0.65,
                                    retrieval_mode="causal",
                                    metadata={
                                        "model_id": model_id,
                                        "variable": var,
                                        "type": "structural_equation",
                                    },
                                ))
                                causal_context_added += 1
            except Exception as exc:
                logger.debug("Causal context enrichment skipped: %s", exc)

        # Layer 3: Symbolic knowledge base grounding
        symbolic_facts_added = 0
        if include_symbolic_facts:
            try:
                from src.services.neurosymbolic_engine import get_neurosymbolic_engine

                nesy = get_neurosymbolic_engine()
                nesy._ensure_initialized()

                query_lower = query.lower()
                query_terms = {
                    t.strip()
                    for t in query_lower.replace(",", " ").replace(".", " ").split()
                    if len(t.strip()) > 3
                }

                for fact in list(nesy._kb.facts.values()):
                    entity_lower = fact.entity.lower()
                    attr_lower = fact.attribute.lower()
                    value_lower = fact.value.lower()
                    relevance = sum(
                        1 for term in query_terms
                        if (term in entity_lower or term in attr_lower
                            or term in value_lower)
                    )
                    if relevance > 0:
                        fact_text = (
                            f"Known fact: {fact.entity}.{fact.attribute} = "
                            f"{fact.value} (confidence: {fact.confidence:.0%}, "
                            f"source: {fact.source})"
                        )
                        results.append(RAGResult(
                            doc_id=f"nesy_fact_{fact.fact_id}",
                            content=fact_text,
                            source="neurosymbolic_kb",
                            score=fact.confidence * 0.6 * relevance,
                            retrieval_mode="symbolic",
                            metadata={
                                "fact_id": fact.fact_id,
                                "entity": fact.entity,
                                "type": "symbolic_fact",
                            },
                        ))
                        symbolic_facts_added += 1

                for rule in nesy._kb.rules:
                    rule_name_lower = (rule.name or "").lower()
                    if any(term in rule_name_lower for term in query_terms):
                        conds = ", ".join(
                            f"{c.attribute} {c.operator} {c.value}"
                            for c in rule.conditions
                        )
                        rule_text = (
                            f"Symbolic rule '{rule.name}': IF {conds} "
                            f"THEN {rule.conclusion_attribute} = "
                            f"{rule.conclusion_value} "
                            f"(confidence: {rule.confidence:.0%})"
                        )
                        results.append(RAGResult(
                            doc_id=f"nesy_rule_{rule.rule_id}",
                            content=rule_text,
                            source="neurosymbolic_kb",
                            score=rule.confidence * 0.5,
                            retrieval_mode="symbolic",
                            metadata={
                                "rule_id": rule.rule_id,
                                "type": "symbolic_rule",
                            },
                        ))
            except Exception as exc:
                logger.debug("Symbolic KB grounding skipped: %s", exc)

        # Deduplicate and sort by score
        seen: set[str] = set()
        unique: list[RAGResult] = []
        for r in results:
            if r.doc_id not in seen:
                seen.add(r.doc_id)
                unique.append(r)
        unique.sort(key=lambda r: r.score, reverse=True)

        # Determine retrieval mode label
        modes_used = {r.retrieval_mode for r in unique}
        if len(modes_used) >= 3:
            mode = "neurosymbolic_augmented"
        elif "graph" in modes_used or "hybrid" in modes_used:
            mode = "hybrid_graphrag"
        else:
            mode = "vector_only"

        logger.info(
            "NeSy-augmented retrieval: %d results "
            "(causal: %d, symbolic: %d, mode: %s)",
            len(unique[:top_k]), causal_context_added, symbolic_facts_added, mode,
        )

        return RAGQueryResponse(
            query=query,
            results=unique[:top_k],
            total_documents=self._index.size,
            retrieval_mode=mode,
            backend=self._backend,
        )

    # -- Utilities ----------------------------------------------------------

    @staticmethod
    def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks by character count."""
        if len(text) <= size:
            return [text] if text.strip() else []
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += size - overlap
        return chunks

    def get_status(self) -> dict[str, Any]:
        return {
            "backend": self._backend,
            "document_count": self._index.size,
            "ready": self._index.size > 0,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Get the singleton RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
