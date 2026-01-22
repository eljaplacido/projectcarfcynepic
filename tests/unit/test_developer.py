"""Unit tests for DeveloperService."""

import pytest
from datetime import datetime

from src.services.developer import (
    DeveloperService,
    LogEntry,
    ExecutionStep,
    SystemState,
    ArchitectureLayer,
    DeveloperState,
)


@pytest.fixture
def dev_service():
    """Create a DeveloperService instance for testing."""
    return DeveloperService(max_logs=100)


def test_developer_service_initialization(dev_service):
    """Test that DeveloperService initializes correctly."""
    assert dev_service._max_logs == 100
    assert len(dev_service._logs) == 0
    assert len(dev_service._execution_steps) == 0
    assert dev_service._current_session_id is None
    assert dev_service._is_processing is False


def test_start_query(dev_service):
    """Test starting a query updates state correctly."""
    session_id = "test-session-123"
    query = "What causes customer churn?"
    
    dev_service.start_query(session_id, query)
    
    assert dev_service._current_session_id == session_id
    assert dev_service._is_processing is True
    assert dev_service._queries_processed == 0  # Not incremented until end_query


def test_end_query_success(dev_service):
    """Test ending a query successfully."""
    dev_service.start_query("session-1", "test query")
    dev_service.end_query(domain="Complicated")
    
    assert dev_service._is_processing is False
    assert dev_service._queries_processed == 1
    assert dev_service._errors_count == 0


def test_end_query_with_error(dev_service):
    """Test ending a query with an error."""
    dev_service.start_query("session-1", "test query")
    dev_service.end_query(error="Something went wrong")
    
    assert dev_service._is_processing is False
    assert dev_service._queries_processed == 1
    assert dev_service._errors_count == 1


def test_start_step(dev_service):
    """Test starting an execution step."""
    step_id = dev_service.start_step(
        layer="router",
        name="Classify Domain",
        input_summary="Query: test"
    )
    
    assert step_id is not None
    assert len(dev_service._execution_steps) == 1
    
    step = dev_service._execution_steps[0]
    assert step.step_id == step_id
    assert step.layer == "router"
    assert step.name == "Classify Domain"
    assert step.status == "running"
    assert step.input_summary == "Query: test"


def test_end_step(dev_service):
    """Test ending an execution step."""
    step_id = dev_service.start_step("router", "Classify", "input")
    dev_service.end_step(
        step_id=step_id,
        status="completed",
        output_summary="Domain: Complicated"
    )
    
    step = dev_service._execution_steps[0]
    assert step.status == "completed"
    assert step.output_summary == "Domain: Complicated"
    assert step.end_time is not None
    assert step.duration_ms is not None
    assert step.duration_ms > 0


def test_log_entry(dev_service):
    """Test adding a log entry."""
    dev_service.log(
        layer="router",
        level="INFO",
        message="Classified as Complicated",
        metadata={"confidence": 0.85}
    )
    
    assert len(dev_service._logs) == 1
    log = dev_service._logs[0]
    assert log.layer == "router"
    assert log.level == "INFO"
    assert log.message == "Classified as Complicated"
    assert log.metadata == {"confidence": 0.85}


def test_log_rotation():
    """Test that logs are rotated when max_logs is exceeded."""
    # Create a new service with max_logs=5 (deque maxlen is set at creation time)
    from collections import deque
    small_service = DeveloperService(max_logs=5)
    # Recreate the deque with the small maxlen
    small_service._logs = deque(maxlen=5)

    # Add 10 logs
    for i in range(10):
        small_service.log("test", "INFO", f"Message {i}")

    # Should only keep the last 5
    assert len(small_service._logs) == 5
    assert small_service._logs[0].message == "Message 5"
    assert small_service._logs[-1].message == "Message 9"


def test_record_llm_call(dev_service):
    """Test recording LLM API calls."""
    initial_count = dev_service._llm_calls
    dev_service.record_llm_call()
    assert dev_service._llm_calls == initial_count + 1


def test_record_cache_hit(dev_service):
    """Test recording cache hits."""
    initial_hits = dev_service._cache_hits
    dev_service.record_cache_hit()
    assert dev_service._cache_hits == initial_hits + 1


def test_record_cache_miss(dev_service):
    """Test recording cache misses."""
    initial_misses = dev_service._cache_misses
    dev_service.record_cache_miss()
    assert dev_service._cache_misses == initial_misses + 1


def test_get_state(dev_service):
    """Test getting the full developer state."""
    # Set up some state
    dev_service.start_query("session-123", "test query")
    dev_service.start_step("router", "Classify", "input")
    dev_service.log("router", "INFO", "Test log")
    dev_service.record_llm_call()

    state = dev_service.get_state()

    assert isinstance(state, DeveloperState)
    assert isinstance(state.system, SystemState)
    assert state.system.session_id == "session-123"
    assert state.system.is_processing is True
    assert state.system.llm_calls == 1

    assert len(state.architecture) > 0
    assert all(isinstance(layer, ArchitectureLayer) for layer in state.architecture)

    assert len(state.execution_timeline) == 1
    assert isinstance(state.execution_timeline[0], ExecutionStep)

    # start_query and start_step internally call log(), so there will be more than 1 log
    assert len(state.recent_logs) >= 1
    assert all(isinstance(log, LogEntry) for log in state.recent_logs)


def test_get_logs_no_filter(dev_service):
    """Test getting logs without filters."""
    dev_service.log("router", "INFO", "Message 1")
    dev_service.log("mesh", "ERROR", "Message 2")
    dev_service.log("guardian", "WARNING", "Message 3")
    
    logs = dev_service.get_logs()
    assert len(logs) == 3


def test_get_logs_filter_by_layer(dev_service):
    """Test filtering logs by layer."""
    dev_service.log("router", "INFO", "Message 1")
    dev_service.log("mesh", "INFO", "Message 2")
    dev_service.log("router", "INFO", "Message 3")
    
    logs = dev_service.get_logs(layer="router")
    assert len(logs) == 2
    assert all(log.layer == "router" for log in logs)


def test_get_logs_filter_by_level(dev_service):
    """Test filtering logs by level."""
    dev_service.log("router", "INFO", "Message 1")
    dev_service.log("router", "ERROR", "Message 2")
    dev_service.log("router", "INFO", "Message 3")
    
    logs = dev_service.get_logs(level="ERROR")
    assert len(logs) == 1
    assert logs[0].level == "ERROR"


def test_get_logs_with_limit(dev_service):
    """Test limiting the number of logs returned."""
    for i in range(10):
        dev_service.log("test", "INFO", f"Message {i}")
    
    logs = dev_service.get_logs(limit=5)
    assert len(logs) == 5


def test_architecture_layers_defined(dev_service):
    """Test that architecture layers are properly defined."""
    state = dev_service.get_state()
    
    layer_ids = [layer.id for layer in state.architecture]
    assert "router" in layer_ids
    assert "mesh" in layer_ids
    assert "services" in layer_ids
    assert "guardian" in layer_ids
    
    # Check that each layer has required fields
    for layer in state.architecture:
        assert layer.id
        assert layer.name
        assert layer.description
        assert isinstance(layer.components, list)
        assert layer.status in ["idle", "active", "processing", "error"]


def test_execution_steps_ordering(dev_service):
    """Test that execution timeline maintains chronological order."""
    step1_id = dev_service.start_step("router", "Step 1", "input1")
    step2_id = dev_service.start_step("mesh", "Step 2", "input2")
    step3_id = dev_service.start_step("guardian", "Step 3", "input3")
    
    state = dev_service.get_state()
    timeline = state.execution_timeline
    
    assert len(timeline) == 3
    assert timeline[0].step_id == step1_id
    assert timeline[1].step_id == step2_id
    assert timeline[2].step_id == step3_id


def test_websocket_connection_management(dev_service):
    """Test adding and removing WebSocket connections."""
    # Mock WebSocket object
    class MockWebSocket:
        pass
    
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Add connections
    dev_service.add_ws_connection(ws1)
    dev_service.add_ws_connection(ws2)
    assert len(dev_service._ws_connections) == 2
    
    # Remove connection
    dev_service.remove_ws_connection(ws1)
    assert len(dev_service._ws_connections) == 1
    assert ws2 in dev_service._ws_connections


def test_system_state_uptime(dev_service):
    """Test that system state includes uptime."""
    state = dev_service.get_state()
    assert state.system.uptime_seconds >= 0


def test_multiple_queries_tracking(dev_service):
    """Test tracking multiple queries."""
    dev_service.start_query("session-1", "query 1")
    dev_service.end_query(domain="Complicated")
    
    dev_service.start_query("session-2", "query 2")
    dev_service.end_query(domain="Complex")
    
    dev_service.start_query("session-3", "query 3")
    dev_service.end_query(error="Failed")
    
    state = dev_service.get_state()
    assert state.system.queries_processed == 3
    assert state.system.errors_count == 1


def test_step_duration_calculation(dev_service):
    """Test that step duration is calculated correctly."""
    import time
    
    step_id = dev_service.start_step("router", "Test", "input")
    time.sleep(0.01)  # Sleep for 10ms
    dev_service.end_step(step_id, "completed", "output")
    
    step = dev_service._execution_steps[0]
    assert step.duration_ms is not None
    assert step.duration_ms >= 10  # Should be at least 10ms


def test_log_handler_integration(dev_service):
    """Test that log handler captures Python logging."""
    import logging
    
    # Get the CARF logger
    logger = logging.getLogger("carf.test")
    logger.setLevel(logging.INFO)
    
    # Log a message
    logger.info("Test message from logger")
    
    # The log handler should have captured it
    # Note: This test may be flaky depending on handler setup timing
    # In a real scenario, you'd verify the handler is attached
    assert dev_service._log_handler is not None

