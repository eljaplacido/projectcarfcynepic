"""Resiliency utilities for CARF.

This module provides retry logic, circuit breakers, and other reliability patterns.
All external API calls should use these decorators.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ParamSpec, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("carf.resiliency")

P = ParamSpec("P")
T = TypeVar("T")


# =============================================================================
# RETRY DECORATORS
# =============================================================================


def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for synchronous functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def call_external_api():
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
        ),
    )


def async_retry_with_backoff(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for async functions with exponential backoff.

    Usage:
        @async_retry_with_backoff(max_attempts=3)
        async def call_external_api():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type(exceptions),
            ):
                with attempt:
                    return await func(*args, **kwargs)
            # This should never be reached due to tenacity's behavior
            raise RetryError(None)  # type: ignore

        return wrapper  # type: ignore

    return decorator


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================


class CircuitState(Enum):
    """States for the circuit breaker pattern."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation to prevent cascading failures.

    Usage:
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        @breaker
        async def call_external_service():
            ...
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, handling automatic state transitions."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
        return self._state

    def record_success(self) -> None:
        """Record a successful call, potentially closing the circuit."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker CLOSED after successful recovery")

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self._failure_count} failures"
            )

    def __call__(
        self, func: Callable[P, T]
    ) -> Callable[P, T]:
        """Decorator to wrap a function with circuit breaker logic."""

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Recovery in {self.recovery_timeout}s"
                )

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Recovery in {self.recovery_timeout}s"
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected due to open circuit."""

    pass


# =============================================================================
# TIMEOUT UTILITIES
# =============================================================================


async def with_timeout(
    coro: Any,
    timeout_seconds: float,
    error_message: str = "Operation timed out",
) -> Any:
    """Execute a coroutine with a timeout.

    Args:
        coro: The coroutine to execute
        timeout_seconds: Maximum time to wait
        error_message: Message for timeout error

    Raises:
        TimeoutError: If the operation exceeds the timeout

    Usage:
        result = await with_timeout(
            long_running_operation(),
            timeout_seconds=30,
            error_message="API call timed out"
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(f"Timeout after {timeout_seconds}s: {error_message}")
        raise TimeoutError(error_message)


# =============================================================================
# FALLBACK UTILITIES
# =============================================================================


def with_fallback(
    fallback_value: T,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_level: int = logging.WARNING,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that returns a fallback value on exception.

    Usage:
        @with_fallback(fallback_value=[], exceptions=(ConnectionError,))
        def fetch_data():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.log(
                    log_level,
                    f"Function {func.__name__} failed, returning fallback: {e}",
                )
                return fallback_value

        return wrapper

    return decorator
