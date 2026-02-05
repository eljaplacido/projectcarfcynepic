"""Tests for the AgentTrackerService."""

import pytest
from uuid import uuid4
from src.services.agent_tracker import (
    AgentTrackerService,
    AgentExecutionStatus,
    LLMUsage,
    get_agent_tracker,
)


@pytest.fixture
def tracker():
    """Create a fresh AgentTrackerService for testing."""
    return AgentTrackerService(max_traces=100)


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return uuid4()


class TestAgentTrackerService:
    """Tests for AgentTrackerService class."""

    def test_get_agent_tracker_singleton(self):
        """Test that get_agent_tracker returns same instance."""
        tracker1 = get_agent_tracker()
        tracker2 = get_agent_tracker()
        assert tracker1 is tracker2

    def test_start_workflow(self, tracker, session_id):
        """Test starting a workflow trace."""
        trace = tracker.start_workflow(
            session_id=session_id,
            query="What causes high churn?",
            workflow_name="test_workflow",
        )

        assert trace.session_id == session_id
        assert trace.query == "What causes high churn?"
        assert trace.workflow_name == "test_workflow"
        assert trace.completed_at is None
        assert len(trace.executions) == 0

    def test_complete_workflow(self, tracker, session_id):
        """Test completing a workflow trace."""
        trace = tracker.start_workflow(session_id, "Test query")

        completed = tracker.complete_workflow(
            trace_id=trace.trace_id,
            domain="complicated",
            quality_score=0.85,
        )

        assert completed is not None
        assert completed.completed_at is not None
        assert completed.domain == "complicated"
        assert completed.overall_quality_score == 0.85

    def test_complete_workflow_not_found(self, tracker):
        """Test completing a non-existent workflow."""
        result = tracker.complete_workflow(
            trace_id=uuid4(),
            domain="clear",
        )
        assert result is None

    def test_start_agent_execution(self, tracker, session_id):
        """Test starting an agent execution."""
        trace = tracker.start_workflow(session_id, "Test query")

        execution = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="causal_analyst",
            agent_name="Causal Analyst",
            input_summary="Analyzing causal effects...",
        )

        assert execution is not None
        assert execution.agent_id == "causal_analyst"
        assert execution.agent_name == "Causal Analyst"
        assert execution.status == AgentExecutionStatus.RUNNING
        assert len(trace.executions) == 1

    def test_start_agent_execution_trace_not_found(self, tracker):
        """Test starting execution for non-existent trace."""
        result = tracker.start_agent_execution(
            trace_id=uuid4(),
            agent_id="test",
            agent_name="Test Agent",
        )
        assert result is None

    def test_complete_agent_execution(self, tracker, session_id):
        """Test completing an agent execution."""
        trace = tracker.start_workflow(session_id, "Test query")
        execution = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="causal_analyst",
            agent_name="Causal Analyst",
        )

        llm_usage = LLMUsage(
            model="deepseek-chat",
            provider="deepseek",
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
            cost_usd=0.001,
            latency_ms=1500,
        )

        completed = tracker.complete_agent_execution(
            execution_id=execution.execution_id,
            output_summary="Effect: 0.15",
            llm_usage=llm_usage,
            quality_score=0.87,
            confidence_score=0.9,
            status=AgentExecutionStatus.COMPLETED,
        )

        assert completed is not None
        assert completed.status == AgentExecutionStatus.COMPLETED
        assert completed.output_summary == "Effect: 0.15"
        assert completed.llm_usage.total_tokens == 700
        assert completed.quality_score == 0.87

    def test_complete_agent_execution_not_found(self, tracker):
        """Test completing a non-existent execution."""
        result = tracker.complete_agent_execution(
            execution_id=uuid4(),
            output_summary="Test",
        )
        assert result is None

    def test_workflow_aggregates_metrics(self, tracker, session_id):
        """Test that workflow aggregates execution metrics."""
        trace = tracker.start_workflow(session_id, "Test query")

        # Add first agent execution
        exec1 = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="router",
            agent_name="Router",
        )
        tracker.complete_agent_execution(
            execution_id=exec1.execution_id,
            llm_usage=LLMUsage(
                model="deepseek-chat",
                provider="deepseek",
                total_tokens=100,
                cost_usd=0.0001,
            ),
        )

        # Add second agent execution
        exec2 = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="analyst",
            agent_name="Analyst",
        )
        tracker.complete_agent_execution(
            execution_id=exec2.execution_id,
            llm_usage=LLMUsage(
                model="deepseek-chat",
                provider="deepseek",
                total_tokens=500,
                cost_usd=0.0005,
            ),
        )

        # Complete workflow
        completed = tracker.complete_workflow(trace.trace_id)

        assert completed.total_tokens == 600
        assert completed.total_cost_usd == pytest.approx(0.0006, rel=1e-6)
        assert len(completed.executions) == 2

    def test_agent_stats_tracking(self, tracker, session_id):
        """Test that agent statistics are tracked."""
        trace = tracker.start_workflow(session_id, "Test query")

        # Execute agent multiple times
        for i in range(3):
            exec_i = tracker.start_agent_execution(
                trace_id=trace.trace_id,
                agent_id="test_agent",
                agent_name="Test Agent",
            )
            tracker.complete_agent_execution(
                execution_id=exec_i.execution_id,
                llm_usage=LLMUsage(
                    model="deepseek-chat",
                    provider="deepseek",
                    total_tokens=100,
                    cost_usd=0.0001,
                ),
                quality_score=0.8 + i * 0.05,
                status=AgentExecutionStatus.COMPLETED,
            )

        stats = tracker.get_agent_stats("test_agent")
        assert len(stats) == 1
        assert stats[0].total_executions == 3
        assert stats[0].successful_executions == 3
        assert stats[0].total_tokens_used == 300

    def test_agent_stats_failed_execution(self, tracker, session_id):
        """Test that failed executions are tracked."""
        trace = tracker.start_workflow(session_id, "Test query")

        # Successful execution
        exec1 = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="test_agent",
            agent_name="Test Agent",
        )
        tracker.complete_agent_execution(
            execution_id=exec1.execution_id,
            status=AgentExecutionStatus.COMPLETED,
        )

        # Failed execution
        exec2 = tracker.start_agent_execution(
            trace_id=trace.trace_id,
            agent_id="test_agent",
            agent_name="Test Agent",
        )
        tracker.complete_agent_execution(
            execution_id=exec2.execution_id,
            status=AgentExecutionStatus.FAILED,
            error_message="LLM API error",
        )

        stats = tracker.get_agent_stats("test_agent")
        assert stats[0].total_executions == 2
        assert stats[0].successful_executions == 1
        assert stats[0].failed_executions == 1

    def test_get_trace(self, tracker, session_id):
        """Test retrieving a trace by ID."""
        trace = tracker.start_workflow(session_id, "Test query")

        retrieved = tracker.get_trace(trace.trace_id)
        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id

    def test_get_session_trace(self, tracker, session_id):
        """Test retrieving the most recent trace for a session."""
        # Create multiple traces for same session
        trace1 = tracker.start_workflow(session_id, "Query 1")
        trace2 = tracker.start_workflow(session_id, "Query 2")

        latest = tracker.get_session_trace(session_id)
        assert latest is not None
        assert latest.trace_id == trace2.trace_id

    def test_get_recent_traces(self, tracker):
        """Test retrieving recent traces."""
        # Create multiple traces
        for i in range(5):
            tracker.start_workflow(uuid4(), f"Query {i}")

        recent = tracker.get_recent_traces(limit=3)
        assert len(recent) == 3

    def test_get_agent_comparison(self, tracker, session_id):
        """Test getting agent comparison data."""
        trace = tracker.start_workflow(session_id, "Test query")

        # Add executions for different agents
        for agent in ["router", "causal_analyst", "guardian"]:
            execution = tracker.start_agent_execution(
                trace_id=trace.trace_id,
                agent_id=agent,
                agent_name=agent.replace("_", " ").title(),
            )
            tracker.complete_agent_execution(
                execution_id=execution.execution_id,
                llm_usage=LLMUsage(
                    model="deepseek-chat",
                    provider="deepseek",
                    total_tokens=100,
                ),
            )

        comparison = tracker.get_agent_comparison()
        assert "agents" in comparison
        assert len(comparison["agents"]) == 3
        assert "generated_at" in comparison

    def test_max_traces_cleanup(self, tracker):
        """Test that old traces are cleaned up when max is reached."""
        small_tracker = AgentTrackerService(max_traces=3)

        # Add more traces than max
        trace_ids = []
        for i in range(5):
            trace = small_tracker.start_workflow(uuid4(), f"Query {i}")
            trace_ids.append(trace.trace_id)

        # First traces should be gone
        assert small_tracker.get_trace(trace_ids[0]) is None
        assert small_tracker.get_trace(trace_ids[1]) is None
        # Last traces should still exist
        assert small_tracker.get_trace(trace_ids[4]) is not None

    def test_query_truncation(self, tracker, session_id):
        """Test that long queries are truncated."""
        long_query = "x" * 1000
        trace = tracker.start_workflow(session_id, long_query)

        assert len(trace.query) == 500  # Truncated to 500 chars
