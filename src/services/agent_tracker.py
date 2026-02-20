"""Agent Tracker Service for CARF.

Provides comprehensive tracking of agent execution including:
- Which LLM was used per node
- Token usage per call
- Latency per agent
- Quality scores per output
- Historical performance trends

This service is central to CARF's mission of providing transparent,
auditable AI-driven insights.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.agent_tracker")


class AgentExecutionStatus(str, Enum):
    """Status of an agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class LLMUsage(BaseModel):
    """LLM usage statistics for a single call."""
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class AgentExecution(BaseModel):
    """Record of a single agent execution."""
    execution_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    agent_id: str
    agent_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: AgentExecutionStatus = AgentExecutionStatus.PENDING

    # Input/Output
    input_summary: str = ""
    output_summary: str = ""

    # LLM Usage
    llm_usage: LLMUsage | None = None

    # Performance Metrics
    latency_ms: int = 0

    # Quality Scores (0-1)
    quality_score: float | None = None
    confidence_score: float | None = None

    # Error handling
    error_message: str | None = None
    retry_count: int = 0


class WorkflowTrace(BaseModel):
    """Complete trace of a workflow execution."""
    trace_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Workflow info
    workflow_name: str = "carf_analysis"
    domain: str | None = None
    query: str = ""

    # Executions
    executions: list[AgentExecution] = Field(default_factory=list)

    # Aggregated metrics
    total_latency_ms: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Quality
    overall_quality_score: float | None = None


class AgentPerformanceSummary(BaseModel):
    """Summary of agent performance over time."""
    agent_id: str
    agent_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_latency_ms: float = 0.0
    average_quality_score: float | None = None
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    last_execution: datetime | None = None


class AgentTrackerService:
    """Service for tracking agent execution and performance."""

    def __init__(self, max_traces: int = 100):
        self._traces: dict[UUID, WorkflowTrace] = {}
        self._agent_stats: dict[str, AgentPerformanceSummary] = {}
        self._max_traces = max_traces
        self._execution_times: dict[UUID, float] = {}  # For tracking start times

    def start_workflow(
        self,
        session_id: UUID,
        query: str,
        workflow_name: str = "carf_analysis"
    ) -> WorkflowTrace:
        """Start tracking a new workflow."""
        trace = WorkflowTrace(
            session_id=session_id,
            workflow_name=workflow_name,
            query=query[:500]  # Truncate long queries
        )
        self._traces[trace.trace_id] = trace

        # Batch eviction: remove oldest 20% when limit exceeded
        if len(self._traces) > self._max_traces:
            n_evict = max(1, self._max_traces // 5)
            sorted_ids = sorted(self._traces.keys(), key=lambda k: self._traces[k].started_at)
            for evict_id in sorted_ids[:n_evict]:
                del self._traces[evict_id]
                self._execution_times.pop(evict_id, None)

        logger.info(f"Started workflow trace {trace.trace_id} for session {session_id}")
        return trace

    def complete_workflow(
        self,
        trace_id: UUID,
        domain: str | None = None,
        quality_score: float | None = None
    ) -> WorkflowTrace | None:
        """Mark a workflow as complete and aggregate metrics."""
        trace = self._traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace {trace_id} not found")
            return None

        trace.completed_at = datetime.utcnow()
        trace.domain = domain
        trace.overall_quality_score = quality_score

        # Aggregate metrics
        trace.total_latency_ms = sum(e.latency_ms for e in trace.executions)
        trace.total_tokens = sum(
            e.llm_usage.total_tokens if e.llm_usage else 0
            for e in trace.executions
        )
        trace.total_cost_usd = sum(
            e.llm_usage.cost_usd if e.llm_usage else 0
            for e in trace.executions
        )

        logger.info(
            f"Completed workflow {trace_id}: "
            f"{len(trace.executions)} agents, "
            f"{trace.total_latency_ms}ms, "
            f"{trace.total_tokens} tokens"
        )

        return trace

    def start_agent_execution(
        self,
        trace_id: UUID,
        agent_id: str,
        agent_name: str,
        input_summary: str = ""
    ) -> AgentExecution | None:
        """Start tracking an agent execution."""
        trace = self._traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace {trace_id} not found")
            return None

        execution = AgentExecution(
            session_id=trace.session_id,
            agent_id=agent_id,
            agent_name=agent_name,
            input_summary=input_summary[:500],
            status=AgentExecutionStatus.RUNNING
        )

        trace.executions.append(execution)
        self._execution_times[execution.execution_id] = time.perf_counter()

        logger.debug(f"Started agent {agent_name} execution {execution.execution_id}")
        return execution

    def complete_agent_execution(
        self,
        execution_id: UUID,
        output_summary: str = "",
        llm_usage: LLMUsage | None = None,
        quality_score: float | None = None,
        confidence_score: float | None = None,
        status: AgentExecutionStatus = AgentExecutionStatus.COMPLETED,
        error_message: str | None = None
    ) -> AgentExecution | None:
        """Complete an agent execution and record metrics."""
        # Find the execution
        execution = None
        for trace in self._traces.values():
            for ex in trace.executions:
                if ex.execution_id == execution_id:
                    execution = ex
                    break
            if execution:
                break

        if not execution:
            logger.warning(f"Execution {execution_id} not found")
            return None

        # Calculate latency
        start_time = self._execution_times.pop(execution_id, None)
        if start_time:
            execution.latency_ms = int((time.perf_counter() - start_time) * 1000)

        execution.completed_at = datetime.utcnow()
        execution.status = status
        execution.output_summary = output_summary[:500]
        execution.llm_usage = llm_usage
        execution.quality_score = quality_score
        execution.confidence_score = confidence_score
        execution.error_message = error_message

        # Update agent stats
        self._update_agent_stats(execution)

        logger.debug(
            f"Completed agent {execution.agent_name}: "
            f"{execution.latency_ms}ms, "
            f"status={status.value}"
        )

        return execution

    def _update_agent_stats(self, execution: AgentExecution) -> None:
        """Update aggregated agent statistics."""
        agent_id = execution.agent_id

        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = AgentPerformanceSummary(
                agent_id=agent_id,
                agent_name=execution.agent_name
            )

        stats = self._agent_stats[agent_id]
        stats.total_executions += 1

        if execution.status == AgentExecutionStatus.COMPLETED:
            stats.successful_executions += 1
        elif execution.status == AgentExecutionStatus.FAILED:
            stats.failed_executions += 1

        # Update running averages
        n = stats.total_executions
        stats.average_latency_ms = (
            (stats.average_latency_ms * (n - 1) + execution.latency_ms) / n
        )

        if execution.quality_score is not None:
            if stats.average_quality_score is None:
                stats.average_quality_score = execution.quality_score
            else:
                stats.average_quality_score = (
                    (stats.average_quality_score * (n - 1) + execution.quality_score) / n
                )

        if execution.llm_usage:
            stats.total_tokens_used += execution.llm_usage.total_tokens
            stats.total_cost_usd += execution.llm_usage.cost_usd

        stats.last_execution = execution.completed_at

    def clear_traces(self) -> None:
        """Clear traces and execution times, preserving agent stats."""
        self._traces.clear()
        self._execution_times.clear()

    def get_trace(self, trace_id: UUID) -> WorkflowTrace | None:
        """Get a workflow trace by ID."""
        return self._traces.get(trace_id)

    def get_session_trace(self, session_id: UUID) -> WorkflowTrace | None:
        """Get the most recent trace for a session."""
        matching = [
            t for t in self._traces.values()
            if t.session_id == session_id
        ]
        if not matching:
            return None
        return max(matching, key=lambda t: t.started_at)

    def get_agent_stats(self, agent_id: str | None = None) -> list[AgentPerformanceSummary]:
        """Get performance statistics for agents."""
        if agent_id:
            stats = self._agent_stats.get(agent_id)
            return [stats] if stats else []
        return list(self._agent_stats.values())

    def get_recent_traces(self, limit: int = 10) -> list[WorkflowTrace]:
        """Get the most recent workflow traces."""
        traces = sorted(
            self._traces.values(),
            key=lambda t: t.started_at,
            reverse=True
        )
        return traces[:limit]

    def get_agent_comparison(self) -> dict[str, Any]:
        """Get comparison data for all agents."""
        return {
            "agents": [
                {
                    "agent_id": stats.agent_id,
                    "agent_name": stats.agent_name,
                    "executions": stats.total_executions,
                    "success_rate": (
                        stats.successful_executions / stats.total_executions
                        if stats.total_executions > 0 else 0
                    ),
                    "avg_latency_ms": stats.average_latency_ms,
                    "avg_quality": stats.average_quality_score,
                    "total_tokens": stats.total_tokens_used,
                    "total_cost": stats.total_cost_usd
                }
                for stats in self._agent_stats.values()
            ],
            "generated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_tracker_service: AgentTrackerService | None = None


def get_agent_tracker() -> AgentTrackerService:
    """Get singleton AgentTrackerService instance."""
    global _tracker_service
    if _tracker_service is None:
        _tracker_service = AgentTrackerService()
    return _tracker_service
