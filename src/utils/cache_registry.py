"""Central cache registry for CARF.

Provides a single `clear_all_caches()` entry-point that clears every
in-memory cache across the system — async LRU caches, LLM model cache,
DataLoader, AgentTracker, ChimeraOracle, and SimulationService.

This file intentionally lives *outside* the services package to avoid
circular imports (services import from utils; the registry imports services).
"""

import gc
import logging

logger = logging.getLogger("carf.cache_registry")


def clear_all_caches() -> dict[str, int]:
    """Clear all in-memory caches and return a stats dict."""
    stats: dict[str, int] = {}

    # 1. Async LRU caches (5 decorated methods)
    try:
        from src.utils.cache import clear_all_caches as _clear_lru
        stats["async_lru"] = _clear_lru()
    except Exception as exc:
        logger.debug(f"async_lru clear skipped: {exc}")
        stats["async_lru"] = 0

    # 2. LLM model cache (stdlib lru_cache)
    try:
        from src.core.llm import get_chat_model
        get_chat_model.cache_clear()
        stats["llm_model"] = 1
    except Exception as exc:
        logger.debug(f"llm_model clear skipped: {exc}")
        stats["llm_model"] = 0

    # 3. DataLoader cache
    try:
        from src.services.data_loader import get_data_loader
        loader = get_data_loader()
        n = len(loader._cache)
        loader.clear_cache()
        stats["data_loader"] = n
    except Exception as exc:
        logger.debug(f"data_loader clear skipped: {exc}")
        stats["data_loader"] = 0

    # 4. AgentTracker traces
    try:
        from src.services.agent_tracker import get_agent_tracker
        tracker = get_agent_tracker()
        n = len(tracker._traces)
        tracker.clear_traces()
        stats["agent_tracker"] = n
    except Exception as exc:
        logger.debug(f"agent_tracker clear skipped: {exc}")
        stats["agent_tracker"] = 0

    # 5. ChimeraOracle in-memory models
    try:
        from src.services.chimera_oracle import get_oracle_engine
        oracle = get_oracle_engine()
        n = len(oracle._models)
        oracle.clear_models()
        stats["chimera_oracle"] = n
    except Exception as exc:
        logger.debug(f"chimera_oracle clear skipped: {exc}")
        stats["chimera_oracle"] = 0

    # 6. SimulationService caches
    try:
        from src.services.simulation import get_simulation_service
        sim = get_simulation_service()
        n = len(sim._realism_cache) + len(sim._running_simulations)
        sim.clear_caches()
        stats["simulation"] = n
    except Exception as exc:
        logger.debug(f"simulation clear skipped: {exc}")
        stats["simulation"] = 0

    # 7. Two-pass GC (second pass collects weak-ref dependent objects)
    gc.collect()
    gc.collect()

    return stats
