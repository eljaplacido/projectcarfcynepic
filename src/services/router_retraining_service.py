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
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.router_retraining")


class ConvergenceResult(BaseModel):
    """Result of plateau/convergence detection in retraining."""

    epoch: int = 0
    accuracy_delta: float = 0.0
    converged: bool = False
    regressed: bool = False
    plateau_detected: bool = False
    recommendation: str = ""
    history: list[dict[str, Any]] = []


class RouterRetrainingService:
    """Extracts retraining signals from user domain-override feedback.

    Methods:
        get_training_data() — fetches all domain overrides from feedback store
        should_retrain(min_samples) — checks if there's enough data
        retrain_keyword_hints() — extracts frequent terms per corrected domain
        check_convergence() — Phase 18C plateau detection
    """

    def __init__(self, hint_store_path: Path | None = None) -> None:
        self._accuracy_history: list[dict[str, Any]] = []
        self._convergence_epsilon: float = 0.005  # 0.5% improvement threshold
        self._max_plateau_epochs: int = 3  # consecutive epochs below epsilon
        self._last_auto_refresh_count: int = 0
        if hint_store_path is None:
            data_dir = Path(
                os.getenv(
                    "CARF_DATA_DIR",
                    str(Path(__file__).resolve().parents[2] / "var"),
                )
            )
            self._hint_store_path = Path(
                os.getenv(
                    "CARF_ROUTER_HINTS_PATH",
                    str(data_dir / "router_hint_overrides.json"),
                )
            )
        else:
            self._hint_store_path = hint_store_path

    _DOMAIN_ALIAS_TO_CANONICAL: dict[str, str] = {
        "clear": "Clear",
        "complicated": "Complicated",
        "complex": "Complex",
        "chaotic": "Chaotic",
        "disorder": "Disorder",
    }

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

    def retrain_keyword_hints(self, top_k: int = 10) -> dict[str, list[str]]:
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

        # Extract top-k keywords per domain
        hints: dict[str, list[str]] = {}
        for domain, counter in domain_terms.items():
            top_words = [word for word, _ in counter.most_common(max(1, top_k))]
            if top_words:
                hints[domain] = top_words

        logger.info(
            "Extracted keyword hints from %d overrides: %s",
            len(overrides),
            {d: len(kws) for d, kws in hints.items()},
        )

        return hints

    def apply_keyword_hints_to_router(
        self,
        hints: dict[str, list[str]],
        *,
        max_new_per_domain: int = 5,
        max_indicators_per_domain: int = 40,
    ) -> dict[str, Any]:
        """Apply extracted hint keywords directly to router indicator hints.

        This operationalizes feedback-to-router adaptation while preserving
        bounded growth and explicit reporting.
        """
        from src.workflows.router import DATA_STRUCTURE_HINTS

        applied: dict[str, list[str]] = {}
        skipped: dict[str, str] = {}

        for raw_domain, keywords in hints.items():
            canonical_domain = self._DOMAIN_ALIAS_TO_CANONICAL.get(raw_domain.lower().strip())
            if not canonical_domain or canonical_domain not in DATA_STRUCTURE_HINTS:
                skipped[raw_domain] = "unknown_domain"
                continue

            domain_hints = DATA_STRUCTURE_HINTS[canonical_domain]
            existing_indicators = list(domain_hints.get("indicators", []))
            existing_lower = {str(i).lower() for i in existing_indicators}

            additions: list[str] = []
            for keyword in keywords:
                if len(additions) >= max_new_per_domain:
                    break
                if len(existing_indicators) >= max_indicators_per_domain:
                    break

                normalized = str(keyword).strip().lower()
                if len(normalized) < 3:
                    continue
                if normalized in existing_lower:
                    continue

                existing_indicators.append(normalized)
                existing_lower.add(normalized)
                additions.append(normalized)

            domain_hints["indicators"] = existing_indicators
            if additions:
                applied[canonical_domain] = additions

        result = {
            "applied_domains": len(applied),
            "applied_hints": applied,
            "skipped_domains": skipped,
            "max_new_per_domain": max_new_per_domain,
            "max_indicators_per_domain": max_indicators_per_domain,
        }
        logger.info("Applied router keyword hints: %s", result)
        return result

    def load_persisted_hint_overrides(self) -> dict[str, list[str]]:
        """Load persisted router hint overrides from disk."""
        if not self._hint_store_path.exists():
            return {}
        try:
            data = json.loads(self._hint_store_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load router hint overrides: %s", exc)
            return {}

        if not isinstance(data, dict):
            return {}

        normalized: dict[str, list[str]] = {}
        for domain, values in data.items():
            if not isinstance(domain, str) or not isinstance(values, list):
                continue
            cleaned = [
                str(v).strip().lower()
                for v in values
                if isinstance(v, str) and str(v).strip()
            ]
            if cleaned:
                normalized[domain.lower().strip()] = cleaned

        return normalized

    def get_persisted_hint_status(self) -> dict[str, Any]:
        """Get persisted hint file status and high-level stats."""
        if not self._hint_store_path.exists():
            return {
                "exists": False,
                "path": str(self._hint_store_path),
                "domains": 0,
                "total_keywords": 0,
                "last_modified": None,
                "last_auto_refresh_count": self._last_auto_refresh_count,
            }

        hints = self.load_persisted_hint_overrides()
        total_keywords = sum(len(values) for values in hints.values())
        stat = self._hint_store_path.stat()
        return {
            "exists": True,
            "path": str(self._hint_store_path),
            "domains": len(hints),
            "total_keywords": total_keywords,
            "last_modified": datetime.fromtimestamp(
                stat.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "last_auto_refresh_count": self._last_auto_refresh_count,
        }

    def persist_keyword_hints(
        self,
        hints: dict[str, list[str]],
        *,
        max_keywords_per_domain: int = 200,
    ) -> dict[str, Any]:
        """Persist keyword hints for automatic router loading on restart."""
        existing = self.load_persisted_hint_overrides()
        merged: dict[str, list[str]] = {
            domain: list(values) for domain, values in existing.items()
        }

        added_count = 0
        for domain, values in hints.items():
            canonical = domain.lower().strip()
            bucket = merged.setdefault(canonical, [])
            current_set = {v.lower() for v in bucket}

            for value in values:
                normalized = str(value).strip().lower()
                if len(normalized) < 3:
                    continue
                if normalized in current_set:
                    continue
                if len(bucket) >= max_keywords_per_domain:
                    break
                bucket.append(normalized)
                current_set.add(normalized)
                added_count += 1

        self._hint_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._hint_store_path.write_text(
            json.dumps(merged, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return {
            "path": str(self._hint_store_path),
            "domains": len(merged),
            "added_keywords": added_count,
            "max_keywords_per_domain": max_keywords_per_domain,
        }

    def maybe_auto_refresh_router_hints(
        self,
        *,
        min_samples: int = 10,
        min_new_overrides: int = 5,
        top_k: int = 10,
        max_new_per_domain: int = 5,
        max_indicators_per_domain: int = 40,
        max_persisted_keywords_per_domain: int = 200,
    ) -> dict[str, Any]:
        """Auto-refresh router hints when sufficient new feedback arrives."""
        overrides = self.get_training_data()
        total_overrides = len(overrides)

        if total_overrides < min_samples:
            return {
                "status": "skipped_insufficient_samples",
                "total_overrides": total_overrides,
                "min_samples": min_samples,
                "last_auto_refresh_count": self._last_auto_refresh_count,
            }

        new_since_last = total_overrides - self._last_auto_refresh_count
        if new_since_last < min_new_overrides:
            return {
                "status": "skipped_not_enough_new_overrides",
                "total_overrides": total_overrides,
                "new_since_last": new_since_last,
                "min_new_overrides": min_new_overrides,
                "last_auto_refresh_count": self._last_auto_refresh_count,
            }

        hints = self.retrain_keyword_hints(top_k=top_k)
        if not hints:
            self._last_auto_refresh_count = total_overrides
            return {
                "status": "skipped_no_hints",
                "total_overrides": total_overrides,
                "last_auto_refresh_count": self._last_auto_refresh_count,
            }

        applied = self.apply_keyword_hints_to_router(
            hints,
            max_new_per_domain=max_new_per_domain,
            max_indicators_per_domain=max_indicators_per_domain,
        )
        persisted = self.persist_keyword_hints(
            hints,
            max_keywords_per_domain=max_persisted_keywords_per_domain,
        )
        self._last_auto_refresh_count = total_overrides

        return {
            "status": "auto_refreshed",
            "total_overrides": total_overrides,
            "new_since_last": new_since_last,
            "keyword_hints": hints,
            "application_summary": applied,
            "persisted_hints": persisted,
            "last_auto_refresh_count": self._last_auto_refresh_count,
        }


    def record_accuracy(self, accuracy: float, epoch: int | None = None) -> None:
        """Record an accuracy measurement from a retraining epoch.

        Args:
            accuracy: Accuracy score (0.0 to 1.0) from the latest retraining.
            epoch: Optional epoch number. Auto-incremented if not provided.
        """
        if epoch is None:
            epoch = len(self._accuracy_history) + 1
        self._accuracy_history.append({
            "epoch": epoch,
            "accuracy": accuracy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "Recorded retraining accuracy: epoch=%d, accuracy=%.4f",
            epoch, accuracy,
        )

    def check_convergence(self) -> ConvergenceResult:
        """Check whether the retraining pipeline has plateaued or regressed.

        Phase 18C: Detects diminishing returns in successive retraining cycles.

        Returns:
            ConvergenceResult with plateau/regression detection.
        """
        history = self._accuracy_history
        result = ConvergenceResult(
            epoch=len(history),
            history=list(history[-10:]),  # last 10 for context
        )

        if len(history) < 2:
            result.recommendation = "Insufficient data (need 2+ epochs)"
            return result

        # Compute accuracy delta from last two epochs
        current = history[-1]["accuracy"]
        previous = history[-2]["accuracy"]
        result.accuracy_delta = round(current - previous, 6)

        # Check for regression (accuracy decreased)
        if result.accuracy_delta < -self._convergence_epsilon:
            result.regressed = True
            result.recommendation = (
                f"REGRESSION detected: accuracy dropped by {abs(result.accuracy_delta):.4f} "
                f"(from {previous:.4f} to {current:.4f}). "
                "Investigate data quality or revert to previous model."
            )
            logger.warning("Retraining REGRESSION: %s", result.recommendation)
            return result

        # Check for plateau (consecutive epochs below epsilon)
        plateau_count = 0
        for i in range(len(history) - 1, max(0, len(history) - self._max_plateau_epochs) - 1, -1):
            if i == 0:
                break
            delta = abs(history[i]["accuracy"] - history[i - 1]["accuracy"])
            if delta < self._convergence_epsilon:
                plateau_count += 1
            else:
                break

        if plateau_count >= self._max_plateau_epochs:
            result.plateau_detected = True
            result.converged = True
            result.recommendation = (
                f"PLATEAU detected: {plateau_count} consecutive epochs with "
                f"<{self._convergence_epsilon:.2%} improvement. "
                "Further retraining unlikely to improve accuracy. "
                "Consider: (1) new training data, (2) model architecture change, "
                "or (3) accepting current performance."
            )
            logger.info("Retraining PLATEAU: %s", result.recommendation)
        elif result.accuracy_delta < self._convergence_epsilon:
            result.recommendation = (
                f"Marginal improvement ({result.accuracy_delta:.4f}). "
                f"Plateau count: {plateau_count}/{self._max_plateau_epochs}."
            )
        else:
            result.recommendation = (
                f"Improvement detected ({result.accuracy_delta:.4f}). "
                "Retraining is productive."
            )

        return result

    def get_convergence_status(self) -> dict[str, Any]:
        """Get convergence monitoring status."""
        result = self.check_convergence()
        return {
            "total_epochs": len(self._accuracy_history),
            "convergence": result.model_dump(),
            "config": {
                "epsilon": self._convergence_epsilon,
                "max_plateau_epochs": self._max_plateau_epochs,
            },
        }


# Singleton
_router_retraining_service: RouterRetrainingService | None = None


def get_router_retraining_service() -> RouterRetrainingService:
    """Get or create the router retraining service singleton."""
    global _router_retraining_service
    if _router_retraining_service is None:
        _router_retraining_service = RouterRetrainingService()
    return _router_retraining_service
