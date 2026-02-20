"""Experience Buffer — semantic memory for past CARF analyses.

Stores past analysis entries and retrieves similar past queries.
Uses sentence-transformers (all-MiniLM-L6-v2) for dense embeddings
when available, falling back to scikit-learn TF-IDF vectorization.

Usage:
    buffer = get_experience_buffer()
    buffer.add(ExperienceEntry(query="...", domain="complicated", ...))
    similar = buffer.find_similar("related query", top_k=3)
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.experience_buffer")

# ── Lazy sentence-transformer loader ────────────────────────────────────

_sentence_model = None
_sentence_model_loaded = False


def _load_sentence_model():
    """Lazy-load SentenceTransformer model; cache globally."""
    global _sentence_model, _sentence_model_loaded
    if _sentence_model_loaded:
        return _sentence_model
    _sentence_model_loaded = True
    try:
        from sentence_transformers import SentenceTransformer
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformers model (all-MiniLM-L6-v2)")
    except Exception:
        _sentence_model = None
        logger.debug("sentence-transformers not available; will use TF-IDF fallback")
    return _sentence_model


class ExperienceEntry(BaseModel):
    """A single experience record from a CARF analysis."""
    query: str
    domain: str = "unknown"
    domain_confidence: float = 0.0
    response_summary: str = ""
    causal_effect: float | None = None
    bayesian_posterior: float | None = None
    guardian_verdict: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = ""


class ExperienceBuffer:
    """Semantic memory for past CARF analyses.

    Uses sentence-transformers (all-MiniLM-L6-v2) for dense cosine similarity
    when available, falling back to sklearn TfidfVectorizer + cosine_similarity.
    """

    def __init__(self, max_entries: int = 1000):
        self._entries: deque[ExperienceEntry] = deque(maxlen=max_entries)
        self._max_entries = max_entries
        # TF-IDF state
        self._vectorizer = None
        self._tfidf_matrix = None
        # Embedding state
        self._embeddings: np.ndarray | None = None
        self._use_embeddings: bool = _load_sentence_model() is not None
        self._dirty = True  # Track if index needs rebuild

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def similarity_backend(self) -> str:
        """Return the active similarity backend name."""
        return "sentence-transformers" if self._use_embeddings else "tfidf"

    def add(self, entry: ExperienceEntry) -> None:
        """Add an experience entry to the buffer."""
        self._entries.append(entry)
        self._dirty = True
        logger.debug(f"Experience added: {entry.query[:50]}... (buffer size: {len(self._entries)})")

    def _rebuild_index(self) -> None:
        """Rebuild similarity index from current entries."""
        if not self._entries:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._embeddings = None
            self._dirty = False
            return

        queries = [e.query for e in self._entries]

        if self._use_embeddings:
            model = _load_sentence_model()
            if model is not None:
                try:
                    self._embeddings = model.encode(queries, convert_to_numpy=True)
                    self._dirty = False
                    return
                except Exception as e:
                    logger.warning(f"Embedding encode failed, falling back to TF-IDF: {e}")
                    self._use_embeddings = False

        # TF-IDF fallback
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words="english",
                ngram_range=(1, 2),
            )
            self._tfidf_matrix = self._vectorizer.fit_transform(queries)
            self._dirty = False
        except ImportError:
            logger.warning("scikit-learn not available; similarity search disabled")
            self._vectorizer = None
            self._tfidf_matrix = None
            self._dirty = False

    def find_similar(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.1,
    ) -> list[tuple[ExperienceEntry, float]]:
        """Find past entries most similar to the given query.

        Returns list of (entry, similarity_score) tuples sorted by descending similarity.
        """
        if not self._entries:
            return []

        if self._dirty:
            self._rebuild_index()

        # Try embeddings path
        if self._use_embeddings and self._embeddings is not None:
            return self._find_similar_embeddings(query, top_k, min_similarity)

        # TF-IDF path
        if self._vectorizer is not None and self._tfidf_matrix is not None:
            return self._find_similar_tfidf(query, top_k, min_similarity)

        return []

    def _find_similar_embeddings(
        self, query: str, top_k: int, min_similarity: float,
    ) -> list[tuple[ExperienceEntry, float]]:
        """Find similar using sentence embeddings + cosine similarity."""
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            model = _load_sentence_model()
            query_vec = model.encode([query], convert_to_numpy=True)
            similarities = cosine_similarity(query_vec, self._embeddings).flatten()
            return self._rank_results(similarities, top_k, min_similarity)
        except Exception as e:
            logger.warning(f"Embedding similarity failed: {e}")
            return []

    def _find_similar_tfidf(
        self, query: str, top_k: int, min_similarity: float,
    ) -> list[tuple[ExperienceEntry, float]]:
        """Find similar using TF-IDF + cosine similarity."""
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            query_vec = self._vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()
            return self._rank_results(similarities, top_k, min_similarity)
        except Exception as e:
            logger.warning(f"TF-IDF similarity failed: {e}")
            return []

    def _rank_results(
        self, similarities: np.ndarray, top_k: int, min_similarity: float,
    ) -> list[tuple[ExperienceEntry, float]]:
        """Rank entries by similarity scores."""
        entries_list = list(self._entries)
        scored = [
            (entries_list[i], float(similarities[i]))
            for i in range(len(entries_list))
            if similarities[i] >= min_similarity
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_domain_patterns(self) -> dict[str, dict]:
        """Aggregate patterns by domain.

        Returns per-domain statistics: count, avg confidence, common queries, etc.
        """
        patterns: dict[str, dict[str, Any]] = {}

        for entry in self._entries:
            domain = entry.domain
            if domain not in patterns:
                patterns[domain] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "total_confidence": 0.0,
                    "causal_effects": [],
                    "verdicts": {},
                }

            p = patterns[domain]
            p["count"] += 1
            p["total_confidence"] += entry.domain_confidence

            if entry.causal_effect is not None:
                p["causal_effects"].append(entry.causal_effect)

            if entry.guardian_verdict:
                p["verdicts"][entry.guardian_verdict] = p["verdicts"].get(entry.guardian_verdict, 0) + 1

        # Compute averages
        for domain, p in patterns.items():
            p["avg_confidence"] = round(p["total_confidence"] / p["count"], 4) if p["count"] else 0
            del p["total_confidence"]
            if p["causal_effects"]:
                p["avg_causal_effect"] = round(sum(p["causal_effects"]) / len(p["causal_effects"]), 4)
            else:
                p["avg_causal_effect"] = None
            del p["causal_effects"]

        return patterns

    def to_context_augmentation(self, query: str) -> dict[str, Any]:
        """Generate context augmentation dict for Router injection.

        Returns similar past queries and domain patterns to enrich the current
        analysis context.
        """
        similar = self.find_similar(query, top_k=3)
        patterns = self.get_domain_patterns()

        return {
            "similar_past_queries": [
                {
                    "query": entry.query[:100],
                    "domain": entry.domain,
                    "confidence": entry.domain_confidence,
                    "similarity": round(score, 4),
                }
                for entry, score in similar
            ],
            "domain_patterns": patterns,
            "buffer_size": len(self._entries),
        }

    def clear(self) -> None:
        """Reset the buffer completely."""
        self._entries.clear()
        self._vectorizer = None
        self._tfidf_matrix = None
        self._embeddings = None
        self._dirty = True


# Singleton
_experience_buffer: ExperienceBuffer | None = None


def get_experience_buffer() -> ExperienceBuffer:
    """Get singleton ExperienceBuffer instance."""
    global _experience_buffer
    if _experience_buffer is None:
        _experience_buffer = ExperienceBuffer()
    return _experience_buffer
