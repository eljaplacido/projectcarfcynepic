"""CSL Policy Management API Router.

Provides CRUD operations for CSL policies and rules,
evaluation endpoints, and engine status.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.csl_policy_service import (
    CSLEvaluation,
    CSLPolicy,
    CSLRule,
    get_csl_service,
)

logger = logging.getLogger("carf.csl")
router = APIRouter(prefix="/csl", tags=["CSL Policy Engine"])


# ── Request / Response Models ────────────────────────────────────────────

class RuleCreateRequest(BaseModel):
    """Request to add a new rule to a policy."""
    name: str = Field(..., description="Unique rule name within the policy")
    condition: dict[str, Any] = Field(default_factory=dict, description="When-condition dict")
    constraint: dict[str, Any] = Field(default_factory=dict, description="Then-constraint dict")
    message: str = Field("", description="Human-readable violation message")
    natural_language: str | None = Field(None, description="Optional NL description to parse")


class RuleUpdateRequest(BaseModel):
    """Request to update an existing rule's constraints."""
    constraint: dict[str, Any] | None = None
    message: str | None = None


class EvaluateRequest(BaseModel):
    """Request to test-evaluate a policy against sample context."""
    policy_name: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class RuleResponse(BaseModel):
    """Serialized rule for API responses."""
    name: str
    policy_name: str
    condition: dict[str, Any]
    constraint: dict[str, Any]
    message: str


class PolicyResponse(BaseModel):
    """Serialized policy for API responses."""
    name: str
    version: str
    description: str
    rules: list[RuleResponse]
    rule_count: int


# ── Helper ───────────────────────────────────────────────────────────────

def _serialize_rule(rule: CSLRule) -> dict[str, Any]:
    return {
        "name": rule.name,
        "policy_name": rule.policy_name,
        "condition": rule.condition,
        "constraint": rule.constraint,
        "message": rule.message,
    }


def _serialize_policy(policy: CSLPolicy) -> dict[str, Any]:
    return {
        "name": policy.name,
        "version": policy.version,
        "description": policy.description,
        "rules": [_serialize_rule(r) for r in policy.rules],
        "rule_count": len(policy.rules),
    }


def _find_policy(name: str) -> CSLPolicy:
    """Find a policy by name or raise 404."""
    service = get_csl_service()
    for p in service._policies:
        if p.name == name:
            return p
    raise HTTPException(status_code=404, detail=f"Policy '{name}' not found")


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/status")
async def get_csl_status():
    """Get CSL engine status, loaded policies count, engine type."""
    service = get_csl_service()
    return {
        "enabled": service.config.enabled,
        "engine": "csl-core" if service._csl_available else "built-in-python",
        "policy_count": service.policy_count,
        "rule_count": service.rule_count,
        "fail_closed": service.config.fail_closed,
        "audit_enabled": service.config.audit_enabled,
        "policies": [p.name for p in service._policies],
    }


@router.get("/policies")
async def list_policies():
    """List all policies with rule summaries."""
    service = get_csl_service()
    return [_serialize_policy(p) for p in service._policies]


@router.get("/policies/{name}")
async def get_policy(name: str):
    """Get full policy with all rules."""
    policy = _find_policy(name)
    return _serialize_policy(policy)


@router.post("/policies/{name}/rules")
async def add_rule(name: str, request: RuleCreateRequest):
    """Add a new rule to a policy."""
    policy = _find_policy(name)

    # Check for duplicate rule name
    for r in policy.rules:
        if r.name == request.name:
            raise HTTPException(
                status_code=409,
                detail=f"Rule '{request.name}' already exists in policy '{name}'",
            )

    # If natural language provided, parse it into structured format
    condition = request.condition
    constraint = request.constraint
    message = request.message

    if request.natural_language and not condition and not constraint:
        parsed = _parse_natural_language_rule(request.natural_language)
        condition = parsed.get("condition", {})
        constraint = parsed.get("constraint", {})
        message = message or parsed.get("message", request.natural_language)

    new_rule = CSLRule(
        name=request.name,
        policy_name=name,
        condition=condition,
        constraint=constraint,
        message=message or f"Rule {request.name} violated",
    )
    policy.add_rule(new_rule)
    logger.info(f"Added rule '{request.name}' to policy '{name}'")

    return {"status": "created", "rule": _serialize_rule(new_rule)}


@router.put("/policies/{name}/rules/{rule_name}")
async def update_rule(name: str, rule_name: str, request: RuleUpdateRequest):
    """Update rule constraints (threshold values, limits)."""
    policy = _find_policy(name)

    for rule in policy.rules:
        if rule.name == rule_name:
            if request.constraint is not None:
                rule.constraint = request.constraint
            if request.message is not None:
                rule.message = request.message
            logger.info(f"Updated rule '{rule_name}' in policy '{name}'")
            return {"status": "updated", "rule": _serialize_rule(rule)}

    raise HTTPException(
        status_code=404,
        detail=f"Rule '{rule_name}' not found in policy '{name}'",
    )


@router.delete("/policies/{name}/rules/{rule_name}")
async def delete_rule(name: str, rule_name: str):
    """Remove a rule from a policy."""
    policy = _find_policy(name)

    for i, rule in enumerate(policy.rules):
        if rule.name == rule_name:
            policy.rules.pop(i)
            logger.info(f"Deleted rule '{rule_name}' from policy '{name}'")
            return {"status": "deleted", "rule_name": rule_name}

    raise HTTPException(
        status_code=404,
        detail=f"Rule '{rule_name}' not found in policy '{name}'",
    )


@router.post("/evaluate")
async def evaluate_policy(request: EvaluateRequest):
    """Test-evaluate policies against sample context."""
    service = get_csl_service()

    if request.policy_name:
        policy = _find_policy(request.policy_name)
        results = policy.evaluate(request.context)
        violations = [r for r in results if not r.passed]
        return {
            "allow": len(violations) == 0,
            "rules_checked": len(results),
            "rules_passed": len(results) - len(violations),
            "rules_failed": len(violations),
            "violations": [
                {
                    "rule_name": v.rule_name,
                    "policy_name": v.policy_name,
                    "message": v.message,
                }
                for v in violations
            ],
        }
    else:
        # Evaluate all policies
        evaluation = service._evaluate_builtin(request.context)
        return {
            "allow": evaluation.allow,
            "rules_checked": evaluation.rules_checked,
            "rules_passed": evaluation.rules_passed,
            "rules_failed": evaluation.rules_failed,
            "violations": [
                {
                    "rule_name": v.rule_name,
                    "policy_name": v.policy_name,
                    "message": v.message,
                }
                for v in evaluation.violations
            ],
        }


@router.post("/reload")
async def reload_policies():
    """Reload all policies without restart."""
    service = get_csl_service()
    service._load_policies()
    return {
        "status": "reloaded",
        "message": f"Loaded {service.policy_count} policies with {service.rule_count} rules",
    }


# ── NL Rule Parsing ─────────────────────────────────────────────────────

def _parse_natural_language_rule(text: str) -> dict[str, Any]:
    """Basic natural language rule parsing.

    Handles common patterns like:
    - "Block transfers over $5000 for junior users"
    - "Require approval for high risk actions"
    - "Limit daily spend to $100000"
    """
    text_lower = text.lower()
    condition: dict[str, Any] = {}
    constraint: dict[str, Any] = {}
    message = text

    # Extract amount limits
    import re
    amount_match = re.search(r'\$?([\d,]+)', text)
    amount = None
    if amount_match:
        amount = float(amount_match.group(1).replace(',', ''))

    # Role detection
    for role in ("junior", "senior", "admin"):
        if role in text_lower:
            condition["user.role"] = role
            break

    # Action type detection
    if "transfer" in text_lower:
        condition["action.type"] = "transfer"
        if amount is not None:
            constraint["action.amount"] = amount
    elif "export" in text_lower:
        condition["action.type"] = "export"
        if amount is not None:
            constraint["action.amount"] = amount
    elif "delete" in text_lower:
        condition["action.type"] = "delete_data"
        constraint["approval.status"] = "approved"
    elif "daily spend" in text_lower or "daily_spend" in text_lower:
        if amount is not None:
            constraint["action.daily_total"] = amount

    # Risk level detection
    if "high risk" in text_lower or "high-risk" in text_lower:
        condition["risk.level"] = "HIGH"
        constraint["approval.status"] = "approved"
    elif "critical" in text_lower:
        condition["risk.level"] = "CRITICAL"
        constraint["action.type"] = "halt"

    # Approval requirement
    if "require approval" in text_lower or "requires approval" in text_lower:
        constraint["approval.status"] = "approved"

    # Block pattern
    if "block" in text_lower and amount is not None and not constraint:
        constraint["action.amount"] = amount

    return {"condition": condition, "constraint": constraint, "message": message}
