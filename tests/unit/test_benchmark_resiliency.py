"""Tests for the resiliency benchmark."""

import asyncio
import pytest
from src.utils.resiliency import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    with_timeout,
)


class TestCircuitBreakerUnit:
    """Unit tests verifying CircuitBreaker fundamentals for the benchmark."""

    def test_initial_state_is_closed(self):
        """CircuitBreaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=5)
        assert cb.state == CircuitState.CLOSED

    def test_failure_count_tracks(self):
        """Failure count increments correctly."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self):
        """CircuitBreaker opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_count(self):
        """Success resets failure count."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0

    def test_open_error_type(self):
        """CircuitBreakerOpenError is a proper exception."""
        err = CircuitBreakerOpenError("test")
        assert isinstance(err, Exception)
        assert str(err) == "test"


class TestTimeoutUnit:
    """Unit tests for timeout utility."""

    @pytest.mark.asyncio
    async def test_fast_operation_succeeds(self):
        """Fast operation completes within timeout."""
        async def fast():
            return 42

        result = await with_timeout(fast(), timeout_seconds=1.0)
        assert result == 42

    @pytest.mark.asyncio
    async def test_slow_operation_raises(self):
        """Slow operation raises TimeoutError."""
        async def slow():
            await asyncio.sleep(10)

        with pytest.raises(TimeoutError, match="too slow"):
            await with_timeout(slow(), timeout_seconds=0.05, error_message="too slow")


class TestCircuitBreakerDecorator:
    """Test the decorator usage pattern."""

    @pytest.mark.asyncio
    async def test_wraps_async_function(self):
        """CircuitBreaker works as async decorator."""
        cb = CircuitBreaker(failure_threshold=3)

        @cb
        async def my_call():
            return "result"

        result = await my_call()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_blocks_when_open(self):
        """Open breaker blocks decorated calls."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

        @cb
        async def my_call():
            return "result"

        # Force open
        cb.record_failure()
        cb.record_failure()

        with pytest.raises(CircuitBreakerOpenError):
            await my_call()

    def test_wraps_sync_function(self):
        """CircuitBreaker works as sync decorator."""
        cb = CircuitBreaker(failure_threshold=3)

        @cb
        def my_call():
            return "sync_result"

        result = my_call()
        assert result == "sync_result"
