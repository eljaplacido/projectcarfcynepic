import asyncio
import json
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable

# Global registry of all async_lru_cache instances for coordinated clearing
_CACHE_REGISTRY: list[dict] = []


def make_hashable(value: Any) -> Any:
    """Convert unhashable types (dict, list, Pydantic models) to hashable ones (tuple)."""
    if isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(make_hashable(v) for v in value)
    # Pydantic v2
    if hasattr(value, "model_dump"):
        return make_hashable(value.model_dump())
    # Pydantic v1
    if hasattr(value, "dict") and callable(value.dict):
        return make_hashable(value.dict())

    return value


def async_lru_cache(maxsize: int = 16, ttl: float = 300.0):
    """Async LRU cache decorator with TTL and global registry.

    Supports caching async function results based on arguments.
    Handles Pydantic models and dictionaries by converting to hashable structure.

    Args:
        maxsize: Maximum number of cached entries (default 16).
        ttl: Time-to-live in seconds for each entry (default 300s / 5 min).
    """
    def decorator(func: Callable) -> Callable:
        # OrderedDict for true LRU: most-recently-used at the end
        cache: OrderedDict = OrderedDict()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = []
            for arg in args:
                key_parts.append(make_hashable(arg))

            key_args = tuple(key_parts)
            key_kwargs = tuple(sorted((k, make_hashable(v)) for k, v in kwargs.items()))
            key = (key_args, key_kwargs)

            if key in cache:
                result, ts = cache[key]
                if time.monotonic() - ts < ttl:
                    # Move to end (most recently used)
                    cache.move_to_end(key)
                    return result
                # Expired — remove stale entry
                del cache[key]

            result = await func(*args, **kwargs)

            # Sweep expired entries before inserting (prevents stale data from
            # occupying slots when entries expire without being looked up)
            now = time.monotonic()
            expired = [k for k, (_, ts) in cache.items() if now - ts >= ttl]
            for k in expired:
                del cache[k]

            # Evict LRU entries if still at capacity
            while len(cache) >= maxsize:
                cache.popitem(last=False)

            cache[key] = (result, time.monotonic())
            return result

        def _cache_clear():
            cache.clear()

        wrapper.cache_clear = _cache_clear
        wrapper.cache_info = lambda: {"size": len(cache), "maxsize": maxsize, "ttl": ttl}

        # Register in global registry
        _CACHE_REGISTRY.append({
            "name": func.__qualname__,
            "cache": cache,
            "clear": _cache_clear,
            "info": wrapper.cache_info,
        })

        return wrapper
    return decorator


def clear_all_caches() -> int:
    """Clear every registered async_lru_cache. Returns total entries cleared."""
    total = 0
    for entry in _CACHE_REGISTRY:
        total += len(entry["cache"])
        entry["clear"]()
    return total


def get_cache_stats() -> list[dict]:
    """Return stats for every registered async_lru_cache."""
    return [
        {"name": entry["name"], **entry["info"]()}
        for entry in _CACHE_REGISTRY
    ]
