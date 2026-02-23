"""Shared Embedding Engine — Singleton dense-embedding infrastructure for CARF.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides a single lazy-loaded sentence-transformers model (all-MiniLM-L6-v2)
shared by AgentMemory, RAG, and ExperienceBuffer.  Falls back to TF-IDF
when sentence-transformers is not installed.

Usage:
    from src.services.embedding_engine import get_embedding_engine
    engine = get_embedding_engine()
    vectors = engine.encode(["hello world", "another text"])
    sim = engine.cosine_similarity(vec_a, vec_b)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("carf.embedding_engine")

EMBEDDINGS_DIR = os.environ.get("CARF_EMBEDDINGS_DIR", "data/embeddings")


class EmbeddingEngine:
    """Singleton embedding engine with dense (sentence-transformers) primary
    and TF-IDF fallback.

    Dense path:
      - Lazy-loads ``all-MiniLM-L6-v2`` on first ``encode()`` call.
      - Returns 384-dim float32 vectors.

    TF-IDF path:
      - Used when sentence-transformers is unavailable.
      - ``fit_tfidf()`` must be called first with corpus, then ``encode_tfidf()``
        transforms new texts against that vocabulary.

    Both paths expose the same ``cosine_similarity`` utility.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._model_loaded: bool = False
        self._dense_available: bool = False

        # TF-IDF state (for fallback)
        self._tfidf_vectorizer: Any = None
        self._tfidf_fitted: bool = False

    # ------------------------------------------------------------------
    # Dense embeddings (sentence-transformers)
    # ------------------------------------------------------------------

    def _ensure_model(self) -> bool:
        """Lazy-load the sentence-transformers model.  Returns True if available."""
        if self._model_loaded:
            return self._dense_available
        self._model_loaded = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._dense_available = True
            logger.info("EmbeddingEngine: loaded sentence-transformers (all-MiniLM-L6-v2)")
        except Exception:
            self._model = None
            self._dense_available = False
            logger.debug("EmbeddingEngine: sentence-transformers not available; TF-IDF fallback active")
        return self._dense_available

    @property
    def dense_available(self) -> bool:
        """Whether dense embeddings are available (loads model on first access)."""
        return self._ensure_model()

    @property
    def backend(self) -> str:
        """Return the active embedding backend name."""
        if self._ensure_model():
            return "sentence-transformers"
        return "tfidf"

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts into dense vectors.

        Returns:
            numpy array of shape ``(len(texts), dim)`` — 384 for all-MiniLM-L6-v2.

        Raises:
            RuntimeError: if sentence-transformers is not installed.
        """
        if not self._ensure_model():
            raise RuntimeError(
                "Dense embeddings require sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )
        return self._model.encode(texts, convert_to_numpy=True)

    def encode_safe(self, texts: list[str]) -> np.ndarray | None:
        """Encode texts into dense vectors; return None on failure."""
        try:
            return self.encode(texts)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # TF-IDF fallback
    # ------------------------------------------------------------------

    def fit_tfidf(
        self,
        corpus: list[str],
        max_features: int = 1000,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> Any:
        """Fit a TF-IDF vectorizer on the given corpus.

        Returns the sparse TF-IDF matrix for the corpus.
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=max_features,
                stop_words="english",
                ngram_range=ngram_range,
            )
            matrix = self._tfidf_vectorizer.fit_transform(corpus)
            self._tfidf_fitted = True
            return matrix
        except ImportError:
            logger.warning("scikit-learn not installed; TF-IDF fallback unavailable")
            self._tfidf_vectorizer = None
            self._tfidf_fitted = False
            return None

    def transform_tfidf(self, texts: list[str]) -> Any:
        """Transform texts using a previously fitted TF-IDF vectorizer.

        Returns:
            Sparse TF-IDF matrix, or None if not fitted.
        """
        if not self._tfidf_fitted or self._tfidf_vectorizer is None:
            return None
        try:
            return self._tfidf_vectorizer.transform(texts)
        except Exception:
            return None

    @property
    def tfidf_fitted(self) -> bool:
        return self._tfidf_fitted

    # ------------------------------------------------------------------
    # Similarity utilities
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between two sets of vectors.

        Args:
            a: array of shape ``(m, d)``
            b: array of shape ``(n, d)``

        Returns:
            array of shape ``(m, n)`` with pairwise cosine similarities.
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity as sklearn_cos

            return sklearn_cos(a, b)
        except ImportError:
            # Pure numpy fallback
            a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
            b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
            return a_norm @ b_norm.T

    # ------------------------------------------------------------------
    # Persistence (optional)
    # ------------------------------------------------------------------

    def save_embeddings(self, name: str, vectors: np.ndarray) -> Path:
        """Persist embeddings to ``data/embeddings/<name>.npy``."""
        out_dir = Path(EMBEDDINGS_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{name}.npy"
        np.save(str(path), vectors)
        logger.debug("Saved embeddings to %s (%s)", path, vectors.shape)
        return path

    def load_embeddings(self, name: str) -> np.ndarray | None:
        """Load persisted embeddings.  Returns None if file missing."""
        path = Path(EMBEDDINGS_DIR) / f"{name}.npy"
        if not path.exists():
            return None
        try:
            return np.load(str(path))
        except Exception as exc:
            logger.warning("Failed to load embeddings from %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "dense_available": self._dense_available,
            "model_loaded": self._model_loaded,
            "tfidf_fitted": self._tfidf_fitted,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_embedding_engine: EmbeddingEngine | None = None


def get_embedding_engine() -> EmbeddingEngine:
    """Get the singleton EmbeddingEngine instance."""
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine
