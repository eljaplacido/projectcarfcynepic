import asyncio
import json
from functools import wraps
from typing import Any, Callable

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

def async_lru_cache(maxsize: int = 128):
    """Async LRU cache decorator.
    
    Supports caching async function results based on arguments.
    Handles Pydantic models and dictionaries by converting to hashable structure.
    """
    def decorator(func: Callable) -> Callable:
        cache: dict = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # We skip 'self' (args[0]) for the key if it's a method
            # But checking if it's a method is tricky.
            # Usually we want instance-independent caching for pure functions,
            # but services are singletons so caching based on 'self' is redundant but harmless 
            # (as long as self is the same instance).
            # If 'self' changes (e.g. fresh instance), we miss cache, which is correct.
            # However, for robustness, we use all args.
            
            key_parts = []
            for arg in args:
                # If arg is an object instance that doesn't implement specialized hash, 
                # we might rely on id(). But for Pydantic/dicts we want value equality.
                key_parts.append(make_hashable(arg))
                
            key_args = tuple(key_parts)
            key_kwargs = tuple(sorted((k, make_hashable(v)) for k, v in kwargs.items()))
            key = (key_args, key_kwargs)
            
            if key in cache:
                return cache[key]
            
            result = await func(*args, **kwargs)
            
            if len(cache) >= maxsize:
                # Remove oldest item (Python 3.7+ dicts preserve insertion order)
                try:
                    cache.pop(next(iter(cache)))
                except StopIteration:
                    pass
            
            cache[key] = result
            return result
            
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = lambda: {"size": len(cache), "maxsize": maxsize}
        return wrapper
    return decorator
