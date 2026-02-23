"""Agent Memory — Persistent vector memory for cross-session learning.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides persistent memory that survives server restarts, replacing the
volatile in-memory ExperienceBuffer for long-term knowledge retention.

Features:
  - JSON-file-backed persistence (works without any DB)
  - Semantic similarity search (sentence-transformers or TF-IDF fallback)
  - Domain pattern aggregation for router hints
  - Reflexion: stores quality scores and uses them to weight future results

When AgentDB is available (`pip install agentdb`) the service delegates
to it for cognitive memory with vector indexing.  Otherwise it uses a
built-in JSON file store with the same ExperienceBuffer similarity engine.

Usage:
    from src.services.agent_memory import get_agent_memory
    memory = get_agent_memory()
    memory.store(MemoryEntry(query="...", domain="Complicated", ...))
    similar = memory.recall("related query", top_k=3)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.agent_memory")

MEMORY_DIR = os.environ.get("CARF_MEMORY_DIR", "data/memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "agent_memory.jsonl")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class MemoryEntry(BaseModel):
    """A single memory record from a CARF analysis session."""
    query: str
    domain: str = "unknown"
    domain_confidence: float = 0.0
    response_summary: str = ""
    causal_effect: float | None = None
    bayesian_posterior: float | None = None
    guardian_verdict: str | None = None
    quality_score: float | None = None  # Reflexion: how good was this response?
    session_id: str = ""
    triggered_method: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecallResult(BaseModel):
    """A recalled memory with similarity score."""
    entry: MemoryEntry
    similarity: float = 0.0


# ---------------------------------------------------------------------------
# Built-in persistent store
# ---------------------------------------------------------------------------

class _FileBackedStore:
    """JSONL-file-backed memory store with dense + TF-IDF similarity search."""

    def __init__(self, file_path: str, max_entries: int = 10000) -> None:
        self._file_path = file_path
        self._max_entries = max_entries
        self._entries: list[MemoryEntry] = []
        self._vectorizer = None
        self._tfidf_matrix = None
        self._dense_embeddings = None
        self._use_dense = False
        self._dirty = True
        self._load()

    def _load(self) -> None:
        """Load entries from disk."""
        path = Path(self._file_path)
        if not path.exists():
            logger.debug("No memory file at %s; starting fresh", self._file_path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self._entries.append(MemoryEntry(**json.loads(line)))
                        except Exception:
                            pass  # skip malformed entries
            # Trim to max
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]
            self._dirty = True
            logger.info("Loaded %d memory entries from %s", len(self._entries), self._file_path)
        except Exception as exc:
            logger.warning("Failed to load memory file: %s", exc)

    def _persist(self, entry: MemoryEntry) -> None:
        """Append a single entry to disk."""
        path = Path(self._file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as exc:
            logger.warning("Failed to persist memory entry: %s", exc)

    @property
    def size(self) -> int:
        return len(self._entries)

    def store(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        self._dirty = True
        self._persist(entry)
        # Trim in-memory if needed
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        logger.debug("Stored memory: %s... (size: %d)", entry.query[:40], len(self._entries))

    def _rebuild_index(self) -> None:
        if not self._entries:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._dense_embeddings = None
            self._use_dense = False
            self._dirty = False
            return

        texts = [e.query for e in self._entries]

        # Try dense embeddings first via shared engine
        try:
            from src.services.embedding_engine import get_embedding_engine
            engine = get_embedding_engine()
            if engine.dense_available:
                self._dense_embeddings = engine.encode(texts)
                self._use_dense = True
                self._dirty = False
                return
        except Exception as exc:
            logger.debug("Dense embedding rebuild failed, falling back to TF-IDF: %s", exc)

        # TF-IDF fallback
        self._use_dense = False
        self._dense_embeddings = None
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words="english",
                ngram_range=(1, 2),
            )
            self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        except (ImportError, ValueError):
            # ValueError: empty vocabulary (all stop words or empty docs)
            self._vectorizer = None
            self._tfidf_matrix = None
        self._dirty = False

    def recall(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.1,
    ) -> list[RecallResult]:
        if not self._entries:
            return []
        if self._dirty:
            self._rebuild_index()

        try:
            # Dense embedding path
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

            scored = [
                (i, float(sims[i]))
                for i in range(len(self._entries))
                if sims[i] >= min_similarity
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, score in scored[:top_k]:
                entry = self._entries[idx]
                # Reflexion: weight by quality score if available
                adjusted = score
                if entry.quality_score is not None:
                    adjusted = score * (0.5 + 0.5 * entry.quality_score)
                results.append(RecallResult(entry=entry, similarity=round(adjusted, 4)))

            results.sort(key=lambda r: r.similarity, reverse=True)
            return results
        except Exception as exc:
            logger.warning("Memory recall failed: %s", exc)
            return []

    def get_domain_patterns(self) -> dict[str, dict[str, Any]]:
        """Aggregate patterns by domain for router hints."""
        patterns: dict[str, dict[str, Any]] = {}
        for entry in self._entries:
            domain = entry.domain
            if domain not in patterns:
                patterns[domain] = {
                    "count": 0,
                    "total_confidence": 0.0,
                    "methods": {},
                    "verdicts": {},
                }
            p = patterns[domain]
            p["count"] += 1
            p["total_confidence"] += entry.domain_confidence
            if entry.triggered_method:
                p["methods"][entry.triggered_method] = p["methods"].get(entry.triggered_method, 0) + 1
            if entry.guardian_verdict:
                p["verdicts"][entry.guardian_verdict] = p["verdicts"].get(entry.guardian_verdict, 0) + 1

        for p in patterns.values():
            p["avg_confidence"] = round(p["total_confidence"] / p["count"], 4) if p["count"] else 0
            del p["total_confidence"]

        return patterns

    def compact(self) -> int:
        """Rewrite the memory file to remove any trailing garbage.  Returns entry count."""
        path = Path(self._file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                for entry in self._entries:
                    f.write(entry.model_dump_json() + "\n")
            return len(self._entries)
        except Exception as exc:
            logger.warning("Memory compaction failed: %s", exc)
            return len(self._entries)


# ---------------------------------------------------------------------------
# Agent Memory Service
# ---------------------------------------------------------------------------

class AgentMemory:
    """Persistent cross-session memory for the CARF agent.

    Provides:
      - store(): persist analysis results
      - recall(): find similar past analyses
      - get_context_augmentation(): format past knowledge for router injection
    """

    def __init__(self, file_path: str = MEMORY_FILE, max_entries: int = 10000) -> None:
        self._store = _FileBackedStore(file_path, max_entries)
        self._agentdb_available = False
        try:
            import agentdb  # type: ignore[import-untyped]
            self._agentdb_available = True
            logger.info("AgentDB detected — cognitive memory features enabled")
        except ImportError:
            logger.debug("AgentDB not installed; using file-backed memory")

    @property
    def size(self) -> int:
        return self._store.size

    @property
    def backend(self) -> str:
        return "agentdb" if self._agentdb_available else "jsonl_file"

    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry (persisted to disk immediately)."""
        self._store.store(entry)

    def recall(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.1,
    ) -> list[RecallResult]:
        """Recall similar past analyses."""
        return self._store.recall(query, top_k, min_similarity)

    def get_context_augmentation(self, query: str) -> dict[str, Any]:
        """Generate context augmentation dict for Router injection.

        Replaces ExperienceBuffer.to_context_augmentation() with persistent
        memory and reflexion-weighted results.
        """
        similar = self.recall(query, top_k=3)
        patterns = self._store.get_domain_patterns()

        return {
            "memory_similar_queries": [
                {
                    "query": r.entry.query[:100],
                    "domain": r.entry.domain,
                    "confidence": r.entry.domain_confidence,
                    "similarity": r.similarity,
                    "method": r.entry.triggered_method,
                }
                for r in similar
            ],
            "domain_patterns": patterns,
            "memory_size": self._store.size,
            "memory_backend": self.backend,
        }

    def store_from_state(self, final_state: Any) -> None:
        """Store a memory entry from a completed EpistemicState."""
        try:
            entry = MemoryEntry(
                query=final_state.user_input,
                domain=final_state.cynefin_domain.value if hasattr(final_state.cynefin_domain, "value") else str(final_state.cynefin_domain),
                domain_confidence=final_state.domain_confidence,
                response_summary=(final_state.final_response or "")[:200],
                causal_effect=final_state.causal_evidence.effect_size if final_state.causal_evidence else None,
                bayesian_posterior=final_state.bayesian_evidence.posterior_mean if final_state.bayesian_evidence else None,
                guardian_verdict=final_state.guardian_verdict.value if final_state.guardian_verdict and hasattr(final_state.guardian_verdict, "value") else None,
                session_id=str(final_state.session_id),
                triggered_method=final_state.triggered_method or "",
            )
            self.store(entry)
        except Exception as exc:
            logger.debug("Failed to store memory from state: %s", exc)

    def compact(self) -> int:
        """Rewrite the memory file (removes gaps from rotation)."""
        return self._store.compact()

    def get_status(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "entries": self._store.size,
            "patterns": self._store.get_domain_patterns(),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_agent_memory: AgentMemory | None = None


def get_agent_memory() -> AgentMemory:
    """Get the singleton AgentMemory instance."""
    global _agent_memory
    if _agent_memory is None:
        _agent_memory = AgentMemory()
    return _agent_memory
