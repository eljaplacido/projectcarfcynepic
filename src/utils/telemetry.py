# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""OpenTelemetry observability for CARF.

Provides:
- TracerProvider with Console (dev) and OTLP (prod) exporters
- ``@traced`` decorator for automatic span creation
- ``get_tracer()`` for manual instrumentation
"""

import functools
import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger("carf.telemetry")

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Globals (initialised lazily by ``init_telemetry``)
# ---------------------------------------------------------------------------
_tracer = None
_initialized = False


def init_telemetry() -> None:
    """Initialise the OpenTelemetry TracerProvider.

    - **Dev mode** (default): exports spans to the console logger.
    - **Prod mode** (``OTEL_EXPORTER_OTLP_ENDPOINT`` set): exports via OTLP.
    """
    global _tracer, _initialized
    if _initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
    except ImportError:
        logger.info(
            "opentelemetry-sdk not installed – observability disabled. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk"
        )
        _initialized = True
        return

    resource = Resource.create({"service.name": "carf", "service.version": "0.5.0"})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP exporter configured → %s", otlp_endpoint)
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-grpc not installed; "
                "falling back to console exporter"
            )
            _add_console_exporter(provider)
    else:
        _add_console_exporter(provider)

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("carf")
    _initialized = True
    logger.info("Observability initialized")


def _add_console_exporter(provider: Any) -> None:
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        ConsoleSpanExporter,
    )

    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))


def get_tracer():
    """Return the CARF tracer (or a no-op proxy if OTel is unavailable)."""
    if not _initialized:
        init_telemetry()
    if _tracer is not None:
        return _tracer
    # Fallback: return a no-op tracer so call-sites never crash
    try:
        from opentelemetry import trace

        return trace.get_tracer("carf")
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def traced(
    name: str | None = None,
    attributes: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps a sync or async function in an OTel span.

    Usage::

        @traced()
        async def causal_analyst_node(state): ...

        @traced(name="custom.span", attributes={"layer": "mesh"})
        def my_function(): ...
    """

    def decorator(fn: F) -> F:
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"
        is_async = _is_coroutine_function(fn)

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                if tracer is None:
                    return await fn(*args, **kwargs)
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for k, v in attributes.items():
                            span.set_attribute(k, v)
                    try:
                        result = await fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(exc))
                        raise

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                if tracer is None:
                    return fn(*args, **kwargs)
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for k, v in attributes.items():
                            span.set_attribute(k, v)
                    try:
                        result = fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(exc))
                        raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def traced_node(
    node_name: str | None = None,
    node_type: str = "workflow_node",
    capture_attrs: list[str] | None = None,
) -> Callable[[F], F]:
    """LangGraph-node decorator with automatic state attribute capture.

    In addition to creating an OTel span, this decorator extracts
    router scores, domain classifications, and other EpistemicState
    fields and attaches them as span attributes for observability.

    Usage::

        @traced_node(node_name="router", node_type="routing")
        async def router_node(state: EpistemicState) -> EpistemicState:
            ...
    """

    def decorator(fn: F) -> F:
        span_name = node_name or fn.__name__
        is_async = _is_coroutine_function(fn)

        def _capture_state(span: Any, state: Any) -> None:
            """Extract common state attributes into the span."""
            if not hasattr(state, "__dict__"):
                return

            # Router metadata
            for attr in ("domain", "confidence", "overall_confidence"):
                if hasattr(state, attr):
                    val = getattr(state, attr)
                    if val is not None:
                        span.set_attribute(f"carf.state.{attr}", str(val))

            # User query (truncated)
            if hasattr(state, "user_input") and state.user_input:
                span.set_attribute("carf.state.user_input", str(state.user_input)[:100])

            # Proposed action summary
            if hasattr(state, "proposed_action") and state.proposed_action:
                action_type = state.proposed_action.get("action_type", "unknown")
                span.set_attribute("carf.state.proposed_action_type", action_type)

            # Guardian verdict
            if hasattr(state, "guardian_verdict") and state.guardian_verdict:
                span.set_attribute("carf.state.guardian_verdict", str(state.guardian_verdict))

            # Evaluation scores
            if hasattr(state, "evaluation_scores") and state.evaluation_scores:
                scores = state.evaluation_scores
                if isinstance(scores, dict):
                    for key, val in scores.items():
                        if isinstance(val, dict):
                            for sub_k, sub_v in val.items():
                                if isinstance(sub_v, (int, float)):
                                    span.set_attribute(f"carf.eval.{key}.{sub_k}", sub_v)

            # Explicitly requested attrs
            if capture_attrs:
                for attr in capture_attrs:
                    if hasattr(state, attr):
                        val = getattr(state, attr)
                        if val is not None:
                            span.set_attribute(f"carf.state.{attr}", str(val)[:200])

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                if tracer is None:
                    return await fn(state, *args, **kwargs)
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("carf.node_type", node_type)
                    _capture_state(span, state)
                    try:
                        result = await fn(state, *args, **kwargs)
                        span.set_attribute("carf.node_status", "ok")
                        return result
                    except Exception as exc:
                        span.set_attribute("carf.node_status", "error")
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(exc))
                        raise

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(fn)
            def sync_wrapper(state: Any, *args: Any, **kwargs: Any) -> Any:
                tracer = get_tracer()
                if tracer is None:
                    return fn(state, *args, **kwargs)
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("carf.node_type", node_type)
                    _capture_state(span, state)
                    try:
                        result = fn(state, *args, **kwargs)
                        span.set_attribute("carf.node_status", "ok")
                        return result
                    except Exception as exc:
                        span.set_attribute("carf.node_status", "error")
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(exc))
                        raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def _is_coroutine_function(fn: Any) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(fn)
