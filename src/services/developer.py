"""Developer Service for CARF.

Provides real-time debugging and monitoring capabilities:
- System state inspection
- Log streaming
- Execution timeline
- Architecture visualization data
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.developer")


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: str = Field(..., description="ISO timestamp")
    level: str = Field(..., description="Log level")
    layer: str = Field(..., description="CARF layer (router, mesh, services, guardian)")
    message: str = Field(..., description="Log message")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ExecutionStep(BaseModel):
    """A step in the execution timeline."""

    step_id: str = Field(..., description="Unique step ID")
    layer: str = Field(..., description="CARF layer")
    name: str = Field(..., description="Step name")
    start_time: float = Field(..., description="Start timestamp (epoch)")
    end_time: float | None = Field(None, description="End timestamp (epoch)")
    duration_ms: float | None = Field(None, description="Duration in milliseconds")
    status: str = Field("pending", description="pending, running, completed, failed")
    input_summary: str | None = Field(None, description="Summary of input")
    output_summary: str | None = Field(None, description="Summary of output")


class SystemState(BaseModel):
    """Current system state for developer view."""

    session_id: str | None = Field(None, description="Current session ID")
    is_processing: bool = Field(False, description="Whether a query is being processed")
    current_layer: str | None = Field(None, description="Currently active layer")
    last_query: str | None = Field(None, description="Last processed query")
    last_domain: str | None = Field(None, description="Last classified domain")
    uptime_seconds: float = Field(0, description="System uptime")
    queries_processed: int = Field(0, description="Total queries processed")
    errors_count: int = Field(0, description="Total errors")
    llm_calls: int = Field(0, description="Total LLM API calls")
    cache_hits: int = Field(0, description="Cache hits")
    cache_misses: int = Field(0, description="Cache misses")


class ArchitectureLayer(BaseModel):
    """Architecture layer visualization data."""

    id: str = Field(..., description="Layer ID")
    name: str = Field(..., description="Layer name")
    description: str = Field(..., description="Layer description")
    components: list[str] = Field(..., description="Components in this layer")
    status: str = Field("idle", description="idle, active, processing, error")
    last_activity: str | None = Field(None, description="Last activity timestamp")


class DeveloperState(BaseModel):
    """Complete developer state response."""

    system: SystemState
    architecture: list[ArchitectureLayer]
    execution_timeline: list[ExecutionStep]
    recent_logs: list[LogEntry]


class DeveloperService:
    """Service for developer debugging and monitoring."""

    # Architecture layers
    LAYERS = [
        ArchitectureLayer(
            id="router",
            name="Cynefin Router",
            description="Classifies queries into Cynefin domains",
            components=["Domain Classifier", "Entropy Calculator", "Solver Selector"],
            status="idle",
        ),
        ArchitectureLayer(
            id="mesh",
            name="Agent Mesh",
            description="Orchestrates domain-specific agents",
            components=["Causal Analyst", "Bayesian Explorer", "Circuit Breaker", "Human Escalation"],
            status="idle",
        ),
        ArchitectureLayer(
            id="services",
            name="Analysis Services",
            description="Core analytical capabilities",
            components=["DoWhy Causal", "PyMC Bayesian", "LLM Integration", "Dataset Store"],
            status="idle",
        ),
        ArchitectureLayer(
            id="guardian",
            name="Guardian Layer",
            description="Policy enforcement and safety checks",
            components=["Policy Engine", "Human Layer", "Audit Trail"],
            status="idle",
        ),
    ]

    def __init__(self, max_logs: int = 500):
        self._start_time = time.time()
        self._max_logs = max_logs  # Store for testing
        self._logs: deque[LogEntry] = deque(maxlen=max_logs)
        self._execution_steps: list[ExecutionStep] = []
        self._current_session_id: str | None = None
        self._is_processing = False
        self._current_layer: str | None = None
        self._last_query: str | None = None
        self._last_domain: str | None = None
        self._queries_processed = 0
        self._errors_count = 0
        self._llm_calls = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._layer_states: dict[str, str] = {layer.id: "idle" for layer in self.LAYERS}
        self._layer_last_activity: dict[str, str | None] = {layer.id: None for layer in self.LAYERS}

        # WebSocket connections for live streaming
        self._ws_connections: list[Any] = []

        # Set up logging handler to capture logs
        self._log_handler = None  # Will be set by _setup_log_handler
        self._setup_log_handler()

    def _setup_log_handler(self):
        """Set up a custom log handler to capture CARF logs."""

        class DevServiceHandler(logging.Handler):
            def __init__(self, service: "DeveloperService"):
                super().__init__()
                self.service = service

            def emit(self, record: logging.LogRecord):
                # Determine layer from logger name
                layer = "services"
                if "router" in record.name:
                    layer = "router"
                elif "guardian" in record.name:
                    layer = "guardian"
                elif "mesh" in record.name or "agent" in record.name:
                    layer = "mesh"

                entry = LogEntry(
                    timestamp=datetime.now().isoformat(),
                    level=record.levelname,
                    layer=layer,
                    message=record.getMessage(),
                    metadata={"logger": record.name},
                )
                self.service._logs.append(entry)

                # Broadcast to WebSocket connections (best effort, ignore errors)
                try:
                    asyncio.create_task(self.service._broadcast_log(entry))
                except RuntimeError:
                    # No event loop running (e.g., in tests) - skip broadcast
                    pass

        self._log_handler = DevServiceHandler(self)
        self._log_handler.setLevel(logging.DEBUG)

        # Add to root CARF logger
        carf_logger = logging.getLogger("carf")
        carf_logger.addHandler(self._log_handler)

    async def _broadcast_log(self, entry: LogEntry):
        """Broadcast log entry to all WebSocket connections."""
        if not self._ws_connections:
            return

        message = entry.model_dump_json()
        disconnected = []

        for ws in self._ws_connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            self._ws_connections.remove(ws)

    def add_ws_connection(self, ws: Any):
        """Add a WebSocket connection for log streaming."""
        self._ws_connections.append(ws)
        logger.info(f"WebSocket connected. Total connections: {len(self._ws_connections)}")

    def remove_ws_connection(self, ws: Any):
        """Remove a WebSocket connection."""
        if ws in self._ws_connections:
            self._ws_connections.remove(ws)
        logger.info(f"WebSocket disconnected. Total connections: {len(self._ws_connections)}")

    def start_query(self, session_id: str, query: str):
        """Record start of query processing."""
        self._current_session_id = session_id
        self._is_processing = True
        self._last_query = query
        self._execution_steps = []

        self.log("router", "info", f"Starting query processing: {query[:100]}...")

    def end_query(self, domain: str | None = None, error: str | None = None):
        """Record end of query processing."""
        self._is_processing = False
        self._current_layer = None
        self._queries_processed += 1

        if domain:
            self._last_domain = domain

        if error:
            self._errors_count += 1
            self.log("services", "error", f"Query failed: {error}")
        else:
            self.log("guardian", "info", "Query processing completed")

        # Reset layer states
        for layer_id in self._layer_states:
            self._layer_states[layer_id] = "idle"

    def start_step(
        self,
        layer: str,
        name: str,
        input_summary: str | None = None,
    ) -> str:
        """Start an execution step."""
        step_id = f"step_{len(self._execution_steps)}_{int(time.time() * 1000)}"

        step = ExecutionStep(
            step_id=step_id,
            layer=layer,
            name=name,
            start_time=time.time(),
            status="running",
            input_summary=input_summary,
        )
        self._execution_steps.append(step)

        self._current_layer = layer
        self._layer_states[layer] = "processing"
        self._layer_last_activity[layer] = datetime.now().isoformat()

        self.log(layer, "debug", f"Starting: {name}")

        return step_id

    def end_step(
        self,
        step_id: str,
        status: str = "completed",
        output_summary: str | None = None,
    ):
        """End an execution step."""
        for step in self._execution_steps:
            if step.step_id == step_id:
                step.end_time = time.time()
                step.duration_ms = (step.end_time - step.start_time) * 1000
                step.status = status
                step.output_summary = output_summary

                self._layer_states[step.layer] = "idle" if status == "completed" else "error"
                self.log(step.layer, "debug", f"Completed: {step.name} ({step.duration_ms:.1f}ms)")
                break

    def log(self, layer: str, level: str, message: str, metadata: dict[str, Any] | None = None):
        """Add a log entry."""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.upper(),
            layer=layer,
            message=message,
            metadata=metadata,
        )
        self._logs.append(entry)

    def record_llm_call(self):
        """Record an LLM API call."""
        self._llm_calls += 1

    def record_cache_hit(self):
        """Record a cache hit."""
        self._cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self._cache_misses += 1

    def get_state(self) -> DeveloperState:
        """Get current developer state."""
        # Update architecture layers with current states
        architecture = []
        for layer in self.LAYERS:
            updated_layer = layer.model_copy()
            updated_layer.status = self._layer_states.get(layer.id, "idle")
            updated_layer.last_activity = self._layer_last_activity.get(layer.id)
            architecture.append(updated_layer)

        return DeveloperState(
            system=SystemState(
                session_id=self._current_session_id,
                is_processing=self._is_processing,
                current_layer=self._current_layer,
                last_query=self._last_query,
                last_domain=self._last_domain,
                uptime_seconds=time.time() - self._start_time,
                queries_processed=self._queries_processed,
                errors_count=self._errors_count,
                llm_calls=self._llm_calls,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
            ),
            architecture=architecture,
            execution_timeline=self._execution_steps[-50:],  # Last 50 steps
            recent_logs=list(self._logs)[-100:],  # Last 100 logs
        )

    def get_logs(
        self,
        layer: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get filtered log entries."""
        logs = list(self._logs)

        if layer:
            logs = [log for log in logs if log.layer == layer]

        if level:
            logs = [log for log in logs if log.level == level.upper()]

        return logs[-limit:]


# Singleton instance
_developer_service: DeveloperService | None = None


def get_developer_service() -> DeveloperService:
    """Get singleton DeveloperService instance."""
    global _developer_service
    if _developer_service is None:
        _developer_service = DeveloperService()
    return _developer_service
