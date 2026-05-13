"""OpenTelemetry / OpenInference tracing for CARF LangGraph workflow.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Provides lightweight span instrumentation for workflow nodes with graceful
degradation to structured logging when OpenTelemetry is not installed.

Phase 18E+ — Production Observability.
"""

from __future__ import annotations

import contextlib
import functools
import inspect
import logging
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger("carf.tracing")

# ---------------------------------------------------------------------------
# Optional OpenTelemetry import
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import Status, StatusCode

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    otel_trace = None  # type: ignore
    Status = None  # type: ignore
    StatusCode = None  # type: ignore


# ---------------------------------------------------------------------------
# Trace context helpers
# ---------------------------------------------------------------------------

class _TraceContext:
    """Thread-local trace context (simplified for single-threaded async)."""

    def __init__(self) -> None:
        self.trace_id: str | None = None
        self.span_stack: list[str] = []

    def start_trace(self) -> str:
        self.trace_id = str(uuid.uuid4())
        self.span_stack = []
        return self.trace_id

    def push_span(self, span_id: str) -> None:
        self.span_stack.append(span_id)

    def pop_span(self) -> str | None:
        return self.span_stack.pop() if self.span_stack else None

    @property
    def current_span_id(self) -> str | None:
        return self.span_stack[-1] if self.span_stack else None


_trace_ctx = _TraceContext()


def get_current_trace_id() -> str | None:
    return _trace_ctx.trace_id


def get_current_span_id() -> str | None:
    return _trace_ctx.current_span_id


# ---------------------------------------------------------------------------
# Span abstraction
# ---------------------------------------------------------------------------

class WorkflowSpan:
    """A span representing a single LangGraph node execution.

    Wraps either an OpenTelemetry span or a lightweight log-based span.
    """

    def __init__(
        self,
        name: str,
        node_type: str = "workflow_node",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.node_type = node_type
        self.attributes = attributes or {}
        self.start_time = time.perf_counter()
        self._otel_span: Any = None
        self._ended = False

        # Start OpenTelemetry span if available
        if _OTEL_AVAILABLE and otel_trace is not None:
            tracer = otel_trace.get_tracer("carf.langgraph")
            self._otel_span = tracer.start_span(name)
            for key, value in self.attributes.items():
                self._otel_span.set_attribute(key, value)

        # Push to trace context
        self._span_id = str(uuid.uuid4())
        _trace_ctx.push_span(self._span_id)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value
        if self._otel_span is not None:
            self._otel_span.set_attribute(key, value)

    def set_status(self, status: str, description: str | None = None) -> None:
        if self._otel_span is not None and Status is not None and StatusCode is not None:
            code = StatusCode.OK if status == "ok" else StatusCode.ERROR
            self._otel_span.set_status(Status(code, description))

    def record_exception(self, exception: BaseException) -> None:
        if self._otel_span is not None:
            self._otel_span.record_exception(exception)
        logger.exception("Exception in span %s", self.name, exc_info=exception)

    def end(self) -> None:
        if self._ended:
            return
        self._ended = True
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        self.attributes["duration_ms"] = round(duration_ms, 2)

        if self._otel_span is not None:
            self._otel_span.end()

        # Pop from trace context
        _trace_ctx.pop_span()

        # Structured log record
        log_record = {
            "trace_id": _trace_ctx.trace_id,
            "span_id": self._span_id,
            "parent_span_id": _trace_ctx.current_span_id,
            "span_name": self.name,
            "node_type": self.node_type,
            "duration_ms": round(duration_ms, 2),
            "attributes": self.attributes,
        }
        logger.info("Workflow span: %s", log_record)

    def __enter__(self) -> "WorkflowSpan":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val is not None:
            self.record_exception(exc_val)
            self.set_status("error", str(exc_val))
        else:
            self.set_status("ok")
        self.end()


# ---------------------------------------------------------------------------
# Decorator for node instrumentation
# ---------------------------------------------------------------------------

def traced_node(
    node_name: str | None = None,
    node_type: str = "workflow_node",
    capture_attrs: list[str] | None = None,
) -> Callable:
    """Decorator that wraps a LangGraph node with span instrumentation.

    Args:
        node_name: Name for the span (defaults to function name)
        node_type: Semantic type (workflow_node, guardian_node, etc.)
        capture_attrs: State attribute keys to capture as span attributes
    """

    def decorator(func: Callable) -> Callable:
        span_name = node_name or func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                with WorkflowSpan(span_name, node_type) as span:
                    # Capture requested state attributes
                    if capture_attrs and hasattr(state, "__dict__"):
                        for attr in capture_attrs:
                            if hasattr(state, attr):
                                val = getattr(state, attr)
                                # Serialize safely
                                try:
                                    if isinstance(val, (str, int, float, bool)):
                                        span.set_attribute(f"state.{attr}", val)
                                    elif val is not None:
                                        span.set_attribute(f"state.{attr}", str(val)[:200])
                                except Exception:
                                    pass

                    # Capture router-specific metrics if present
                    if hasattr(state, "domain") and state.domain is not None:
                        span.set_attribute("router.domain", str(state.domain))
                    if hasattr(state, "confidence") and state.confidence is not None:
                        span.set_attribute("router.confidence", round(state.confidence, 4))
                    if hasattr(state, "overall_confidence") and state.overall_confidence is not None:
                        span.set_attribute("router.overall_confidence", str(state.overall_confidence))

                    try:
                        result = await func(state, *args, **kwargs)
                        span.set_status("ok")
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status("error", str(exc))
                        raise

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                with WorkflowSpan(span_name, node_type) as span:
                    if capture_attrs and hasattr(state, "__dict__"):
                        for attr in capture_attrs:
                            if hasattr(state, attr):
                                val = getattr(state, attr)
                                try:
                                    if isinstance(val, (str, int, float, bool)):
                                        span.set_attribute(f"state.{attr}", val)
                                    elif val is not None:
                                        span.set_attribute(f"state.{attr}", str(val)[:200])
                                except Exception:
                                    pass

                    if hasattr(state, "domain") and state.domain is not None:
                        span.set_attribute("router.domain", str(state.domain))
                    if hasattr(state, "confidence") and state.confidence is not None:
                        span.set_attribute("router.confidence", round(state.confidence, 4))

                    try:
                        result = func(state, *args, **kwargs)
                        span.set_status("ok")
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status("error", str(exc))
                        raise

            return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# Trace initialization
# ---------------------------------------------------------------------------

def init_tracing(
    service_name: str = "carf",
    service_version: str = "0.5.0",
    exporter_endpoint: str | None = None,
) -> None:
    """Initialize OpenTelemetry tracing if available.

    Args:
        service_name: Service name for trace resource
        service_version: Service version
        exporter_endpoint: Optional OTLP endpoint (e.g., http://localhost:4317)
    """
    if not _OTEL_AVAILABLE:
        logger.info("OpenTelemetry not installed; using log-based tracing")
        return

    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {"service.name": service_name, "service.version": service_version}
        )
        provider = TracerProvider(resource=resource)

        # Console exporter as fallback
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # OTLP exporter if endpoint provided
        if exporter_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                otlp_exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            except ImportError:
                logger.warning("OTLP exporter not available; using console exporter only")

        otel_trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing initialized (service=%s)", service_name)
    except Exception as exc:
        logger.warning("Failed to initialize OpenTelemetry: %s", exc)
