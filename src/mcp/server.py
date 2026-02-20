"""CARF MCP Server — exposes cognitive services as MCP tools.

Start with:
    python -m src.mcp
    # or
    carf-mcp
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("carf.mcp")

mcp = FastMCP(
    "CARF CYNEPIC",
    instructions=(
        "Complex-Adaptive Reasoning Fabric v0.1.0 — cognitive services for agentic development. "
        "Provides causal inference, Bayesian active inference, Cynefin domain routing, "
        "ChimeraOracle fast predictions, and CSL policy guardian tools."
    ),
)

# Register tool modules (side-effect imports register @mcp.tool decorators)
from src.mcp.tools import bayesian, causal, guardian, memory, oracle, reflector, router  # noqa: E402, F401


def main() -> None:
    """Entry point for ``carf-mcp`` console script and ``python -m src.mcp``."""
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")
    tool_count = len(mcp._tool_manager._tools) if hasattr(mcp._tool_manager, "_tools") else 0
    logger.info("Starting CARF MCP server with %d tools", tool_count)
    mcp.run()


if __name__ == "__main__":
    main()
