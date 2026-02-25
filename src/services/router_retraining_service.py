"""Router Retraining Service — Active learning from domain override feedback.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Reads domain overrides from the feedback store, extracts frequent terms
per corrected domain, and returns new keyword hints. Non-destructive:
does not modify the running router directly.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger("carf.router_retraining")


class RouterRetrainingService:
    """Extracts retraining signals from user domain-override feedback.

    Methods:
        get_training_data() — fetches all domain overrides from feedback store
        should_retrain(min_samples) — checks if there's enough data
        retrain_keyword_hints() — extracts frequent terms per corrected domain
    """

    def get_training_data(self) -> list[dict[str, Any]]:
        """Fetch all domain override records from the feedback store."""
        try:
            from src.api.routers.feedback import get_feedback_store
            store = get_feedback_store()
            return store.get_domain_overrides()
        except Exception as exc:
            logger.warning("Failed to fetch domain overrides: %s", exc)
            return []

    def should_retrain(self, min_samples: int = 10) -> bool:
        """Check whether enough override samples exist for meaningful retraining.

        Args:
            min_samples: Minimum total overrides required.

        Returns:
            True if total overrides >= min_samples.
        """
        overrides = self.get_training_data()
        return len(overrides) >= min_samples

    def retrain_keyword_hints(self) -> dict[str, list[str]]:
        """Extract frequent terms per corrected domain from override feedback.

        Returns a dict mapping domain → list of top keywords discovered
        from user queries that were reclassified into that domain.
        Non-destructive: does not modify the running router.
        """
        overrides = self.get_training_data()
        if not overrides:
            return {}

        # Collect query terms per corrected domain
        domain_terms: dict[str, Counter] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "not", "no", "this",
            "that", "these", "those", "it", "its", "our", "we", "they",
            "what", "how", "which", "who", "when", "where", "why",
        }

        for override in overrides:
            domain = (override.get("correct_domain") or "").strip().lower()
            query = (override.get("query") or "").strip().lower()
            if not domain or not query:
                continue

            if domain not in domain_terms:
                domain_terms[domain] = Counter()

            words = [
                w for w in query.split()
                if len(w) > 2 and w not in stop_words
            ]
            domain_terms[domain].update(words)

        # Extract top-10 keywords per domain
        hints: dict[str, list[str]] = {}
        for domain, counter in domain_terms.items():
            top_words = [word for word, _ in counter.most_common(10)]
            if top_words:
                hints[domain] = top_words

        logger.info(
            "Extracted keyword hints from %d overrides: %s",
            len(overrides),
            {d: len(kws) for d, kws in hints.items()},
        )

        return hints


# Singleton
_router_retraining_service: RouterRetrainingService | None = None


def get_router_retraining_service() -> RouterRetrainingService:
    """Get or create the router retraining service singleton."""
    global _router_retraining_service
    if _router_retraining_service is None:
        _router_retraining_service = RouterRetrainingService()
    return _router_retraining_service
