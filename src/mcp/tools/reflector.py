"""Smart Reflector tool for MCP.

Exposes the SmartReflectorService's repair capability to any MCP-connected
AI agent, allowing them to attempt policy-violation repair.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.smart_reflector import get_smart_reflector, RepairStrategy


@mcp.tool()
async def reflector_repair(
    proposed_action: dict[str, Any],
    violations: list[str],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attempt to repair a policy-violating action using CARF's smart reflector.

    Uses a hybrid heuristic + LLM approach:
    1. Fast heuristic rules for known violation types (budget, threshold, approval)
    2. LLM fallback for unrecognized violations

    Args:
        proposed_action: The action that was rejected by the Guardian
        violations: List of policy violation descriptions
        context: Optional context (domain, session metadata, etc.)
    """
    from src.core.state import EpistemicState

    # Build a minimal state for the repair
    state = EpistemicState(
        user_input=context.get("query", "MCP repair request") if context else "MCP repair request",
        proposed_action=proposed_action,
        policy_violations=violations,
        context=context or {},
    )

    reflector = get_smart_reflector()
    result = await reflector.repair(state)

    return {
        "strategy_used": result.strategy_used.value,
        "repaired_action": result.repaired_action,
        "repair_explanation": result.repair_explanation,
        "confidence": result.confidence,
        "violations_addressed": result.violations_addressed,
        "violations_remaining": result.violations_remaining,
    }
