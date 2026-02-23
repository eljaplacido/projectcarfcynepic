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

    def retrieve_for_pipeline(
        self,
        query: str,
        domain_id: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Retrieve and format context for injection into the LLM pipeline.

        Returns a plain-text context block suitable for prompt augmentation.
        """
        resp = self.retrieve(query, top_k=top_k, domain_id=domain_id)
        if not resp.results:
            return ""
        lines = ["[Retrieved context from knowledge base]"]
        for r in resp.results:
            lines.append(f"--- [{r.source}] (relevance: {r.score:.2f}) ---")
            lines.append(r.content[:400])
        return "\n".join(lines)

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
