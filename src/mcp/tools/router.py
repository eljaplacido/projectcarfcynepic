"""Cynefin Router tools for MCP.

Wraps CynefinRouter to expose domain classification and configuration
to any MCP-connected AI agent.
"""

from __future__ import annotations

from typing import Any

from src.core.state import EpistemicState
from src.mcp.server import mcp
from src.workflows.router import get_router, get_router_config


@mcp.tool()
async def cynefin_classify(
    query: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a query into a Cynefin domain.

    Routes the input into one of: Clear, Complicated, Complex, Chaotic,
    or Disorder. Uses LLM-based semantic classification combined with
    signal entropy analysis.

    Args:
        query: The input text to classify
        context: Optional additional context for classification
    """
    router = get_router()
    state = EpistemicState(
        user_input=query,
        context=context or {},
    )
    result = await router.classify(state)
    return {
        "domain": result.cynefin_domain.value if hasattr(result.cynefin_domain, "value") else str(result.cynefin_domain),
        "confidence": result.domain_confidence,
        "entropy": result.domain_entropy,
        "requires_human": result.requires_human,
    }


@mcp.tool()
async def cynefin_config() -> dict[str, Any]:
    """Get current Cynefin router configuration and thresholds.

    Returns the router mode (llm or distilbert), confidence threshold,
    entropy threshold, and domain-specific settings.
    """
    config = get_router_config()
    return config.model_dump()
