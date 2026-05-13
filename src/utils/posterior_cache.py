"""Posterior Distribution Cache for CARF Bayesian Inference.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides time-bounded, hash-keyed caching of posterior distributions
to avoid redundant MCMC runs for identical inference configurations.

Phase 18E: Scalable Inference Strategy — ``cached`` mode support.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from src.core.deployment_profile import get_profile

logger = logging.getLogger("carf.posterior_cache")


@dataclass
class _CachedEntry:
    """Internal cache entry with TTL."""

    samples: list[float]
    timestamp: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    credible_interval: tuple[float, float]
    posterior_mean: float


class PosteriorCache:
    """Bounded, TTL-aware cache for Bayesian posterior distributions.

    Keys are deterministic hashes of ``BayesianInferenceConfig`` fields
    so that identical configurations reuse previous MCMC results.

    The cache is bounded by ``maxlen`` (LRU eviction) and TTL (time-based
    eviction).  Both parameters are read from the active deployment profile
    so that research/staging/production behave differently without code
    changes.
    """

    def __init__(
        self,
        max_entries: int | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        profile = get_profile()
        self._max_entries = max_entries if max_entries is not None else profile.inference_cache_max_entries
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else profile.inference_cache_ttl_seconds
        self._cache: OrderedDict[str, _CachedEntry] = OrderedDict()
        logger.info(
            "PosteriorCache initialised (max_entries=%d, ttl_seconds=%d)",
            self._max_entries,
            self._ttl_seconds,
        )

    @staticmethod
    def _make_key(config_dict: dict[str, Any]) -> str:
        """Create a deterministic hash key from an inference config dict."""
        canonical = json.dumps(config_dict, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]

    def get(
        self,
        config_dict: dict[str, Any],
    ) -> _CachedEntry | None:
        """Retrieve a cached posterior if present and not expired."""
        if self._ttl_seconds <= 0 or self._max_entries <= 0:
            return None

        key = self._make_key(config_dict)
        entry = self._cache.get(key)
        if entry is None:
            return None

        now = time.time()
        if now - entry.timestamp > self._ttl_seconds:
            logger.debug("Cache entry expired for key %s", key)
            self._cache.pop(key, None)
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        logger.debug("Cache hit for key %s", key)
        return entry

    def put(
        self,
        config_dict: dict[str, Any],
        samples: list[float],
        epistemic_uncertainty: float,
        aleatoric_uncertainty: float,
        credible_interval: tuple[float, float],
        posterior_mean: float,
    ) -> None:
        """Store a posterior result in the cache."""
        if self._ttl_seconds <= 0 or self._max_entries <= 0:
            return

        key = self._make_key(config_dict)
        now = time.time()

        # Evict oldest if at capacity
        while len(self._cache) >= self._max_entries:
            oldest_key, _ = self._cache.popitem(last=False)
            logger.debug("Evicted oldest cache entry %s", oldest_key)

        self._cache[key] = _CachedEntry(
            samples=samples,
            timestamp=now,
            epistemic_uncertainty=epistemic_uncertainty,
            aleatoric_uncertainty=aleatoric_uncertainty,
            credible_interval=credible_interval,
            posterior_mean=posterior_mean,
        )
        logger.debug("Cached posterior for key %s", key)

    def invalidate(self, config_dict: dict[str, Any] | None = None) -> None:
        """Remove a specific entry, or clear the entire cache if no key given."""
        if config_dict is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Invalidated entire posterior cache (%d entries)", count)
            return

        key = self._make_key(config_dict)
        removed = self._cache.pop(key, None)
        if removed:
            logger.info("Invalidated cache entry for key %s", key)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics for monitoring."""
        now = time.time()
        total = len(self._cache)
        expired = sum(1 for e in self._cache.values() if now - e.timestamp > self._ttl_seconds)
        return {
            "total_entries": total,
            "expired_entries": expired,
            "max_entries": self._max_entries,
            "ttl_seconds": self._ttl_seconds,
            "utilization": round(total / max(self._max_entries, 1), 3),
        }


# Singleton
_cache_instance: PosteriorCache | None = None


def get_posterior_cache() -> PosteriorCache:
    """Get or create the singleton posterior cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = PosteriorCache()
    return _cache_instance
