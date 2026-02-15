"""Guardian / CSL Policy tools for MCP.

Wraps CSLPolicyService to expose policy evaluation, listing, rule
management, and engine status to any MCP-connected AI agent.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.csl_policy_service import CSLRule, get_csl_service


@mcp.tool()
async def guardian_evaluate(context: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a context dict against all loaded CSL policies.

    Pass a flat context dict with keys like ``user.role``, ``action.type``,
    ``action.amount``, ``domain.type``, ``domain.confidence``, etc.

    Returns allow/deny verdict, rule counts, and any violations.
    """
    service = get_csl_service()
    evaluation = await service.evaluate(context)
    return {
        "allow": evaluation.allow,
        "rules_checked": evaluation.rules_checked,
        "rules_passed": evaluation.rules_passed,
        "rules_failed": evaluation.rules_failed,
        "violations": [
            {
                "rule": v.rule_name,
                "policy": v.policy_name,
                "message": v.message,
            }
            for v in evaluation.violations
        ],
        "error": evaluation.error,
    }


@mcp.tool()
async def guardian_list_policies() -> list[dict[str, Any]]:
    """List all loaded CSL policies with their rules.

    Returns a list of policies, each with name, version, description,
    and a summary of rules (name, condition, constraint, message).
    """
    service = get_csl_service()
    policies = []
    for policy in service._policies:
        rules = []
        for rule in policy.rules:
            rules.append({
                "name": rule.name,
                "condition": rule.condition,
                "constraint": rule.constraint,
                "message": rule.message,
            })
        policies.append({
            "name": policy.name,
            "version": policy.version,
            "description": policy.description,
            "rule_count": len(policy.rules),
            "rules": rules,
        })
    return policies


@mcp.tool()
async def guardian_add_rule(
    policy_name: str,
    rule_name: str,
    condition: dict[str, Any],
    constraint: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    """Add a new rule to an existing policy.

    Args:
        policy_name: Name of the target policy (e.g. "budget_limits")
        rule_name: Unique name for the new rule
        condition: When-clause as dict (e.g. {"user.role": "junior"})
        constraint: Then-clause as dict (e.g. {"action.amount": {"op": "<=", "value": 1000}})
        message: Human-readable violation message
    """
    service = get_csl_service()
    for policy in service._policies:
        if policy.name == policy_name:
            rule = CSLRule(
                name=rule_name,
                policy_name=policy_name,
                condition=condition,
                constraint=constraint,
                message=message,
            )
            policy.rules.append(rule)
            return {
                "status": "added",
                "policy": policy_name,
                "rule": rule_name,
                "total_rules": len(policy.rules),
            }
    return {"status": "error", "message": f"Policy '{policy_name}' not found"}


@mcp.tool()
async def guardian_status() -> dict[str, Any]:
    """Get CSL policy engine status.

    Returns engine enabled state, engine type (csl-core or builtin),
    and counts of loaded policies and rules.
    """
    service = get_csl_service()
    return {
        "enabled": service.config.enabled,
        "engine": "csl-core" if service._csl_available else "builtin-python",
        "policy_count": service.policy_count,
        "rule_count": service.rule_count,
        "fail_closed": service.config.fail_closed,
        "audit_enabled": service.config.audit_enabled,
    }
