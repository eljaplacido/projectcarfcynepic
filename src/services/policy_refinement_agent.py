"""Policy refinement agent for generating and validating CSL policies.

This agent enables user-driven and automated policy refinement:
1. Generate new CSL rules from natural language descriptions
2. Validate generated rules for consistency (Z3 when available)
3. Update policy scaffolds with refined rules

Architecture:
    User/Agent → PolicyRefinementAgent → Generate CSL Rule → Validate → Store
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.policy_refinement")


class PolicyRefinementRequest(BaseModel):
    """Request to refine or generate a policy rule."""

    description: str = Field(..., description="Natural language description of the policy")
    base_scaffold: str = Field(default="", description="Base scaffold to extend")
    domain: str = Field(default="", description="Target domain (financial, safety, etc.)")
    rule_type: str = Field(
        default="constraint",
        description="Rule type: constraint, approval, threshold, rate_limit",
    )
    parameters: dict[str, Any] = Field(default_factory=dict)


class PolicyRefinementResult(BaseModel):
    """Result of policy refinement."""

    success: bool
    rule_name: str = ""
    policy_name: str = ""
    generated_rule: dict[str, Any] = Field(default_factory=dict)
    validation_passed: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    csl_representation: str = ""


class PolicyRefinementAgent:
    """Agent for generating and refining CSL policy rules.

    Translates natural language policy descriptions into structured
    CSL rules, validates them for consistency, and integrates them
    into the policy scaffold system.

    Usage:
        agent = PolicyRefinementAgent()
        result = agent.refine(PolicyRefinementRequest(
            description="Limit enterprise customer discounts to 25%",
            domain="operational",
            rule_type="threshold",
        ))
    """

    def __init__(self) -> None:
        self._rule_templates = self._load_rule_templates()

    def _load_rule_templates(self) -> dict[str, dict[str, Any]]:
        """Load rule generation templates."""
        return {
            "constraint": {
                "structure": {
                    "condition": {},
                    "constraint": {},
                    "message": "",
                },
                "description": "Value must satisfy a constraint",
            },
            "approval": {
                "structure": {
                    "condition": {},
                    "constraint": {"approval.status": "approved"},
                    "message": "",
                },
                "description": "Action requires approval",
            },
            "threshold": {
                "structure": {
                    "condition": {},
                    "constraint": {},
                    "message": "",
                },
                "description": "Value must be within threshold bounds",
            },
            "rate_limit": {
                "structure": {
                    "condition": {},
                    "constraint": {},
                    "message": "",
                },
                "description": "Action frequency must not exceed limit",
            },
        }

    def refine(self, request: PolicyRefinementRequest) -> PolicyRefinementResult:
        """Generate a refined policy rule from a request.

        Args:
            request: Policy refinement request with description and parameters

        Returns:
            PolicyRefinementResult with generated rule and validation status
        """
        logger.info(f"Refining policy: {request.description}")

        try:
            # Generate rule structure
            rule = self._generate_rule(request)

            # Validate the rule
            validation_errors = self._validate_rule(rule)
            validation_passed = len(validation_errors) == 0

            # Generate CSL representation
            csl_repr = self._to_csl_string(rule, request)

            return PolicyRefinementResult(
                success=True,
                rule_name=rule.get("name", ""),
                policy_name=request.base_scaffold or request.domain,
                generated_rule=rule,
                validation_passed=validation_passed,
                validation_errors=validation_errors,
                csl_representation=csl_repr,
            )

        except Exception as e:
            logger.error(f"Policy refinement failed: {e}")
            return PolicyRefinementResult(
                success=False,
                validation_errors=[str(e)],
            )

    def _generate_rule(self, request: PolicyRefinementRequest) -> dict[str, Any]:
        """Generate a rule structure from the request."""
        template = self._rule_templates.get(request.rule_type, self._rule_templates["constraint"])
        rule = dict(template["structure"])

        # Build rule name from description
        rule_name = (
            request.description.lower()
            .replace(" ", "_")
            .replace("-", "_")[:50]
        )
        # Clean non-alphanumeric chars
        rule_name = "".join(c for c in rule_name if c.isalnum() or c == "_")
        rule["name"] = rule_name

        # Apply parameters
        params = request.parameters

        if request.rule_type == "threshold":
            field = params.get("field", "value")
            min_val = params.get("min")
            max_val = params.get("max")
            condition_field = params.get("condition_field", "")
            condition_value = params.get("condition_value", "")

            if condition_field and condition_value:
                rule["condition"] = {condition_field: condition_value}

            constraint: dict[str, Any] = {}
            if min_val is not None and max_val is not None:
                constraint[field] = {"min": min_val, "max": max_val}
            elif max_val is not None:
                constraint[field] = max_val
            elif min_val is not None:
                constraint[field] = {"min": min_val}
            rule["constraint"] = constraint

        elif request.rule_type == "approval":
            condition_field = params.get("condition_field", "action.type")
            condition_value = params.get("condition_value", "")
            if condition_value:
                rule["condition"] = {condition_field: condition_value}
            rule["constraint"] = {"approval.status": "approved"}
            if params.get("required_role"):
                rule["constraint"]["approval.role"] = params["required_role"]

        elif request.rule_type == "rate_limit":
            field = params.get("field", "action.count")
            max_val = params.get("max", 10)
            period = params.get("period", "minute")
            rule["condition"] = params.get("condition", {})
            rule["constraint"] = {field: max_val}
            rule["period"] = period

        elif request.rule_type == "constraint":
            rule["condition"] = params.get("condition", {})
            rule["constraint"] = params.get("constraint", {})

        rule["message"] = request.description

        return rule

    def _validate_rule(self, rule: dict[str, Any]) -> list[str]:
        """Validate a generated rule for consistency."""
        errors: list[str] = []

        if not rule.get("name"):
            errors.append("Rule must have a name")

        if not rule.get("constraint"):
            errors.append("Rule must have at least one constraint")

        if not rule.get("message"):
            errors.append("Rule must have a descriptive message")

        # Try Z3 validation if available
        try:
            import z3  # type: ignore[import-untyped]
            z3_errors = self._validate_with_z3(rule)
            errors.extend(z3_errors)
        except ImportError:
            pass  # Z3 not available, skip formal verification

        return errors

    def _validate_with_z3(self, rule: dict[str, Any]) -> list[str]:
        """Validate rule consistency using Z3 theorem prover."""
        errors: list[str] = []

        try:
            import z3  # type: ignore[import-untyped]

            solver = z3.Solver()

            # Check for contradictory constraints
            constraints = rule.get("constraint", {})
            for field, value in constraints.items():
                if isinstance(value, dict):
                    min_val = value.get("min")
                    max_val = value.get("max")
                    if min_val is not None and max_val is not None:
                        var = z3.Real(field)
                        solver.add(var >= min_val)
                        solver.add(var <= max_val)

            if solver.check() == z3.unsat:
                errors.append(f"Rule '{rule.get('name')}' has contradictory constraints")

        except Exception as e:
            logger.warning(f"Z3 validation skipped: {e}")

        return errors

    def _to_csl_string(self, rule: dict[str, Any], request: PolicyRefinementRequest) -> str:
        """Convert a rule to CSL string representation."""
        lines = []
        name = rule.get("name", "unnamed_rule")
        policy_name = request.base_scaffold or request.domain or "custom"

        lines.append(f"policy {policy_name} {{")
        lines.append(f'    version = "user-refined-v1"')
        lines.append(f'    generated_by = "policy_refinement_agent"')
        if request.base_scaffold:
            lines.append(f'    base_scaffold = "{request.base_scaffold}"')
        lines.append("")
        lines.append(f"    rule {name} {{")

        # Condition
        conditions = rule.get("condition", {})
        if conditions:
            condition_parts = [f"{k} == {_format_value(v)}" for k, v in conditions.items()]
            lines.append(f"        when {' and '.join(condition_parts)}")

        # Constraint
        constraints = rule.get("constraint", {})
        if constraints:
            constraint_parts = []
            for k, v in constraints.items():
                if isinstance(v, dict):
                    if "min" in v:
                        constraint_parts.append(f"{k} >= {v['min']}")
                    if "max" in v:
                        constraint_parts.append(f"{k} <= {v['max']}")
                else:
                    constraint_parts.append(f"{k} <= {v}" if isinstance(v, (int, float)) else f"{k} == {_format_value(v)}")
            lines.append(f"        then {' and '.join(constraint_parts)}")

        # Message
        message = rule.get("message", "")
        if message:
            lines.append(f'        message = "{message}"')

        lines.append("    }")
        lines.append("}")

        return "\n".join(lines)


def _format_value(value: Any) -> str:
    """Format a value for CSL string representation."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_refinement_agent: PolicyRefinementAgent | None = None


def get_refinement_agent() -> PolicyRefinementAgent:
    """Get or create the policy refinement agent singleton."""
    global _refinement_agent
    if _refinement_agent is None:
        _refinement_agent = PolicyRefinementAgent()
    return _refinement_agent
