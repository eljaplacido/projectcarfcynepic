"""Tests for src/utils/resiliency.py."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from src.utils.resiliency import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    retry_with_backoff,
    async_retry_with_backoff,
    with_timeout,
    with_fallback,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker should start in closed state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_circuit_breaker_records_success(self):
        """Success should reset failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb._failure_count = 2
        cb.record_success()
        assert cb._failure_count == 0

    def test_circuit_breaker_records_failure(self):
        """Failure should increment failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        assert cb._failure_count == 1
        cb.record_failure()
        assert cb._failure_count == 2

    def test_circuit_breaker_opens_after_threshold(self):
        """Circuit should open after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_blocks_when_open(self):
        """Open circuit should raise CircuitBreakerOpenError."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()  # Opens the circuit

        @cb
        def test_func():
            return "test"

        with pytest.raises(CircuitBreakerOpenError):
            test_func()

    def test_circuit_breaker_allows_when_closed(self):
        """Closed circuit should allow calls."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @cb
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_circuit_breaker_half_open_recovery(self):
        """Circuit should transition to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)  # Immediate recovery
        cb.record_failure()  # Opens
        assert cb._state == CircuitState.OPEN

        # After timeout (immediate), checking state triggers half-open
        # Force the transition by checking state
        import time
        time.sleep(0.01)  # Ensure some time passes
        state = cb.state  # This triggers the transition check
        assert state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_on_half_open_success(self):
        """Successful call in half-open should close circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()  # Opens

        import time
        time.sleep(0.01)
        _ = cb.state  # Force half-open transition

        @cb
        def success_func():
            return "recovered"

        result = success_func()
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_reopens_on_half_open_failure(self):
        """Failed call in half-open should reopen circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()  # Opens

        import time
        time.sleep(0.01)
        _ = cb.state  # Force half-open transition

        @cb
        def failing_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            failing_func()

        assert cb._state == CircuitState.OPEN


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_successful_call_no_retry(self):
        """Successful call should not retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        """Should retry on failure up to max_attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        """Should raise after exhausting retries."""
        from tenacity import RetryError
        call_count = 0

        @retry_with_backoff(max_attempts=2, min_wait=0.01, max_wait=0.02)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent failure")

        with pytest.raises(RetryError):
            always_fails()

        assert call_count == 2

    def test_retry_specific_exceptions(self):
        """Should only retry on specified exceptions."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=(ValueError,))
        def type_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            type_error_func()

        assert call_count == 1  # No retry for TypeError


class TestAsyncRetryWithBackoff:
    """Tests for async_retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_async_successful_call(self):
        """Successful async call should not retry."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await async_success()
        assert result == "async success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retries_on_failure(self):
        """Should retry async function on failure."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def async_failing():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("async temp failure")
            return "async recovered"

        result = await async_failing()
        assert result == "async recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_raises_after_max_retries(self):
        """Should raise after exhausting async retries."""
        from tenacity import RetryError
        call_count = 0

        @async_retry_with_backoff(max_attempts=2, min_wait=0.01, max_wait=0.02)
        async def async_always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("async permanent failure")

        with pytest.raises(RetryError):
            await async_always_fails()

        assert call_count == 2


class TestWithTimeout:
    """Tests for with_timeout utility."""

    @pytest.mark.asyncio
    async def test_completes_within_timeout(self):
        """Should return result if completes within timeout."""
        async def quick_operation():
            return "done"

        result = await with_timeout(quick_operation(), timeout_seconds=1.0)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        """Should raise TimeoutError if exceeds timeout."""
        async def slow_operation():
            await asyncio.sleep(10)
            return "never"

        with pytest.raises(TimeoutError, match="Operation timed out"):
            await with_timeout(slow_operation(), timeout_seconds=0.01)


class TestWithFallback:
    """Tests for with_fallback decorator."""

    def test_returns_normal_value_on_success(self):
        """Should return normal value when no exception."""
        @with_fallback(fallback_value="fallback")
        def success_func():
            return "success"

        assert success_func() == "success"

    def test_returns_fallback_on_exception(self):
        """Should return fallback value on exception."""
        @with_fallback(fallback_value="fallback")
        def failing_func():
            raise ValueError("fail")

        assert failing_func() == "fallback"

    def test_returns_fallback_only_for_specified_exceptions(self):
        """Should only use fallback for specified exceptions."""
        @with_fallback(fallback_value="fallback", exceptions=(ValueError,))
        def type_error_func():
            raise TypeError("not caught")

        with pytest.raises(TypeError):
            type_error_func()


class TestCircuitBreakerAsync:
    """Tests for CircuitBreaker with async functions."""

    @pytest.mark.asyncio
    async def test_async_circuit_breaker_allows_when_closed(self):
        """Closed circuit should allow async calls."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @cb
        async def async_success():
            return "async success"

        result = await async_success()
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_async_circuit_breaker_blocks_when_open(self):
        """Open circuit should block async calls."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()  # Opens

        @cb
        async def async_func():
            return "test"

        with pytest.raises(CircuitBreakerOpenError):
            await async_func()

    @pytest.mark.asyncio
    async def test_async_circuit_breaker_records_failure(self):
        """Async function failure should be recorded."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @cb
        async def async_failing():
            raise ValueError("async fail")

        with pytest.raises(ValueError):
            await async_failing()

        assert cb._failure_count == 1
