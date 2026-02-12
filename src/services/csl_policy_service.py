"""CSL-Core policy management service for CARF Guardian.

Provides formal verification via CSL-Core's Z3-based policy evaluation.
Falls back gracefully to OPA/YAML when CSL-Core is not available.

Architecture:
    CSL-Core acts as the PRIMARY policy enforcement layer:
    1. Compile-time: Z3 verifies policy correctness (no contradictions)
    2. Runtime: Pure Python functors evaluate policies (<1ms)
    3. Audit: Every decision generates an audit trail entry

    OPA remains as SECONDARY for complex contextual policies.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.csl")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class CSLConfig(BaseModel):
    """CSL-Core configuration loaded from environment."""

    enabled: bool = Field(default=False)
    policy_dir: str = Field(default="config/policies")
    fail_closed: bool = Field(default=True)
    audit_enabled: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "CSLConfig":
        """Load CSL config from environment variables."""
        enabled_env = os.getenv("CSL_ENABLED")
        enabled = enabled_env.lower() == "true" if enabled_env is not None else False

        fail_closed_env = os.getenv("CSL_FAIL_CLOSED")
        fail_closed = fail_closed_env.lower() != "false" if fail_closed_env is not None else True

        audit_env = os.getenv("CSL_AUDIT_ENABLED")
        audit_enabled = audit_env.lower() != "false" if audit_env is not None else True

        return cls(
            enabled=enabled,
            policy_dir=os.getenv("CSL_POLICY_DIR", "config/policies"),
            fail_closed=fail_closed,
            audit_enabled=audit_enabled,
        )


# ---------------------------------------------------------------------------
# Evaluation result models
# ---------------------------------------------------------------------------

class CSLRuleResult(BaseModel):
    """Result of evaluating a single CSL rule."""

    rule_name: str
    policy_name: str
    passed: bool
    message: str = ""
    context_used: dict[str, Any] = Field(default_factory=dict)


class CSLEvaluation(BaseModel):
    """Aggregate result of CSL policy evaluation."""

    allow: bool
    rules_checked: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    violations: list[CSLRuleResult] = Field(default_factory=list)
    audit_entries: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Policy definitions (built-in fallback when csl-core is not installed)
# ---------------------------------------------------------------------------

class CSLRule:
    """A single policy rule for built-in evaluation."""

    def __init__(
        self,
        name: str,
        policy_name: str,
        condition: dict[str, Any],
        constraint: dict[str, Any],
        message: str = "",
    ):
        self.name = name
        self.policy_name = policy_name
        self.condition = condition
        self.constraint = constraint
        self.message = message

    def evaluate(self, context: dict[str, Any]) -> CSLRuleResult:
        """Evaluate this rule against the given context."""
        # Check if the condition matches
        if not self._matches_condition(context):
            return CSLRuleResult(
                rule_name=self.name,
                policy_name=self.policy_name,
                passed=True,
                message="Condition not matched, rule skipped",
                context_used=context,
            )

        # Check if the constraint is satisfied
        passed = self._check_constraint(context)
        return CSLRuleResult(
            rule_name=self.name,
            policy_name=self.policy_name,
            passed=passed,
            message="" if passed else self.message,
            context_used=context,
        )

    def _matches_condition(self, context: dict[str, Any]) -> bool:
        """Check if rule condition matches the context."""
        for key, expected in self.condition.items():
            actual = self._resolve_path(context, key)
            if actual is None or actual != expected:
                return False
        return True

    def _check_constraint(self, context: dict[str, Any]) -> bool:
        """Check if rule constraint is satisfied."""
        for key, constraint_val in self.constraint.items():
            actual = self._resolve_path(context, key)
            if actual is None:
                return False

            if isinstance(constraint_val, dict):
                # Range check: {"min": x, "max": y}
                if "min" in constraint_val and actual < constraint_val["min"]:
                    return False
                if "max" in constraint_val and actual > constraint_val["max"]:
                    return False
                # Equality check with operator
                if "eq" in constraint_val and actual != constraint_val["eq"]:
                    return False
                if "neq" in constraint_val and actual == constraint_val["neq"]:
                    return False
            elif isinstance(constraint_val, bool):
                if actual != constraint_val:
                    return False
            elif isinstance(constraint_val, (int, float)):
                if actual > constraint_val:
                    return False
            else:
                if actual != constraint_val:
                    return False

        return True

    @staticmethod
    def _resolve_path(context: dict[str, Any], path: str) -> Any:
        """Resolve a dot-separated path in a nested dict."""
        parts = path.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current


class CSLPolicy:
    """A collection of rules forming a policy."""

    def __init__(self, name: str, version: str = "1.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.rules: list[CSLRule] = []

    def add_rule(self, rule: CSLRule) -> None:
        self.rules.append(rule)

    def evaluate(self, context: dict[str, Any]) -> list[CSLRuleResult]:
        """Evaluate all rules in this policy against the context."""
        results = []
        for rule in self.rules:
            results.append(rule.evaluate(context))
        return results


# ---------------------------------------------------------------------------
# Built-in policy loader
# ---------------------------------------------------------------------------

def _build_budget_limits_policy() -> CSLPolicy:
    """Build the budget_limits policy from built-in rules."""
    policy = CSLPolicy("budget_limits", "1.0", "Enforce financial action limits")

    policy.add_rule(CSLRule(
        name="junior_transfer_limit",
        policy_name="budget_limits",
        condition={"user.role": "junior", "action.type": "transfer"},
        constraint={"action.amount": 1000},
        message="Junior users cannot transfer more than $1,000",
    ))

    policy.add_rule(CSLRule(
        name="senior_transfer_limit",
        policy_name="budget_limits",
        condition={"user.role": "senior", "action.type": "transfer"},
        constraint={"action.amount": 50000},
        message="Senior users limited to $50,000 transfers",
    ))

    policy.add_rule(CSLRule(
        name="admin_transfer_limit",
        policy_name="budget_limits",
        condition={"user.role": "admin", "action.type": "transfer"},
        constraint={"action.amount": 500000},
        message="Admin users limited to $500,000 transfers",
    ))

    policy.add_rule(CSLRule(
        name="chimera_prediction_bounds",
        policy_name="budget_limits",
        condition={"prediction.source": "chimera"},
        constraint={"prediction.effect_size": {"min": -1.0, "max": 1.0}},
        message="Chimera predictions must be normalized between -1.0 and 1.0",
    ))

    policy.add_rule(CSLRule(
        name="domain_financial_limit_clear",
        policy_name="budget_limits",
        condition={"domain.type": "Clear"},
        constraint={"action.amount": 100000},
        message="Clear domain auto-approval limit is $100,000",
    ))

    policy.add_rule(CSLRule(
        name="domain_financial_limit_complicated",
        policy_name="budget_limits",
        condition={"domain.type": "Complicated"},
        constraint={"action.amount": 50000},
        message="Complicated domain auto-approval limit is $50,000",
    ))

    policy.add_rule(CSLRule(
        name="domain_financial_limit_complex",
        policy_name="budget_limits",
        condition={"domain.type": "Complex"},
        constraint={"action.amount": 25000},
        message="Complex domain auto-approval limit is $25,000",
    ))

    policy.add_rule(CSLRule(
        name="domain_financial_limit_chaotic",
        policy_name="budget_limits",
        condition={"domain.type": "Chaotic"},
        constraint={"action.amount": 10000},
        message="Chaotic domain auto-approval limit is $10,000",
    ))

    return policy


def _build_action_gates_policy() -> CSLPolicy:
    """Build the action_gates policy from built-in rules."""
    policy = CSLPolicy("action_gates", "1.0", "Require approvals for high-risk actions")

    policy.add_rule(CSLRule(
        name="high_risk_requires_approval",
        policy_name="action_gates",
        condition={"risk.level": "HIGH"},
        constraint={"approval.status": "approved"},
        message="High-risk actions require human approval",
    ))

    policy.add_rule(CSLRule(
        name="critical_risk_blocked",
        policy_name="action_gates",
        condition={"risk.level": "CRITICAL"},
        constraint={"action.type": "halt"},
        message="Critical-risk actions are blocked pending investigation",
    ))

    policy.add_rule(CSLRule(
        name="delete_data_requires_approval",
        policy_name="action_gates",
        condition={"action.type": "delete_data"},
        constraint={"approval.status": "approved"},
        message="Data deletion requires admin approval",
    ))

    policy.add_rule(CSLRule(
        name="modify_policy_requires_approval",
        policy_name="action_gates",
        condition={"action.type": "modify_policy"},
        constraint={"approval.status": "approved"},
        message="Policy modification requires admin approval",
    ))

    policy.add_rule(CSLRule(
        name="production_deployment_gate",
        policy_name="action_gates",
        condition={"action.type": "production_deployment"},
        constraint={"approval.status": "approved"},
        message="Production deployments require approval",
    ))

    policy.add_rule(CSLRule(
        name="external_api_write_gate",
        policy_name="action_gates",
        condition={"action.type": "external_api_write"},
        constraint={"approval.status": "approved"},
        message="External API writes require human approval",
    ))

    return policy


def _build_chimera_guards_policy() -> CSLPolicy:
    """Build the chimera_guards policy from built-in rules."""
    policy = CSLPolicy("chimera_guards", "1.0", "Prediction safety bounds for ChimeraOracle")

    policy.add_rule(CSLRule(
        name="effect_size_bounds",
        policy_name="chimera_guards",
        condition={"prediction.source": "chimera"},
        constraint={"prediction.effect_size": {"min": -2.0, "max": 2.0}},
        message="Chimera effect size must be within [-2.0, 2.0]",
    ))

    policy.add_rule(CSLRule(
        name="confidence_minimum",
        policy_name="chimera_guards",
        condition={"prediction.source": "chimera"},
        constraint={"prediction.confidence": {"min": 0.5}},
        message="Chimera predictions require minimum 50% confidence",
    ))

    policy.add_rule(CSLRule(
        name="drift_detection_gate",
        policy_name="chimera_guards",
        condition={"prediction.drift_detected": True},
        constraint={"approval.escalated": True},
        message="Predictions blocked when drift is detected",
    ))

    policy.add_rule(CSLRule(
        name="refutation_required",
        policy_name="chimera_guards",
        condition={"prediction.source": "causal", "prediction.is_actionable": True},
        constraint={"prediction.refutation_passed": True},
        message="Actionable causal predictions must pass refutation tests",
    ))

    return policy


def _build_data_access_policy() -> CSLPolicy:
    """Build the data_access policy from built-in rules."""
    policy = CSLPolicy("data_access", "1.0", "PII and sensitive data handling rules")

    policy.add_rule(CSLRule(
        name="pii_must_be_masked",
        policy_name="data_access",
        condition={"data.contains_pii": True},
        constraint={"data.is_masked": True},
        message="PII data must be masked before processing",
    ))

    policy.add_rule(CSLRule(
        name="audit_log_immutable",
        policy_name="data_access",
        condition={"data.type": "audit_log"},
        constraint={"action.type": {"neq": "delete"}},
        message="Audit logs are immutable and cannot be deleted",
    ))

    return policy


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class CSLPolicyService:
    """Service for CSL-Core policy evaluation.

    Provides formal verification of policies using CSL-Core when available,
    with graceful fallback to built-in Python evaluation.

    Usage:
        service = get_csl_service()
        evaluation = await service.evaluate(context)
        if not evaluation.allow:
            # Handle violations
    """

    def __init__(self, config: CSLConfig | None = None) -> None:
        self.config = config or CSLConfig.from_env()
        self._policies: list[CSLPolicy] = []
        self._csl_available = False

        if not self.config.enabled:
            logger.info("CSL-Core integration disabled")
            return

        # Try to load csl-core
        try:
            import csl_core  # type: ignore[import-untyped]
            self._csl_available = True
            logger.info("CSL-Core library available, using formal verification")
        except ImportError:
            logger.info(
                "CSL-Core library not installed, using built-in policy evaluation. "
                "Install with: pip install csl-core"
            )

        self._load_policies()

    def _load_policies(self) -> None:
        """Load built-in policy definitions."""
        self._policies = [
            _build_budget_limits_policy(),
            _build_action_gates_policy(),
            _build_chimera_guards_policy(),
            _build_data_access_policy(),
        ]
        logger.info(
            f"Loaded {len(self._policies)} CSL policies with "
            f"{sum(len(p.rules) for p in self._policies)} rules total"
        )

    def map_state_to_context(self, state: Any) -> dict[str, Any]:
        """Map EpistemicState to CSL evaluation context.

        Translates the LangGraph state into the flat namespace expected
        by CSL policy rules.

        Args:
            state: EpistemicState or dict with state data

        Returns:
            Context dict for CSL policy evaluation
        """
        if isinstance(state, dict):
            proposed_action = state.get("proposed_action") or {}
            domain = state.get("cynefin_domain", "Disorder")
            if hasattr(domain, "value"):
                domain = domain.value
            confidence = state.get("domain_confidence", 0.0)
            entropy = state.get("domain_entropy", 1.0)
            context_data = state.get("context", {})
        else:
            proposed_action = state.proposed_action or {}
            domain = state.cynefin_domain.value if hasattr(state.cynefin_domain, "value") else str(state.cynefin_domain)
            confidence = state.domain_confidence
            entropy = state.domain_entropy
            context_data = state.context if hasattr(state, "context") else {}

        # Build CSL context
        return {
            "domain": {
                "type": domain,
                "confidence": confidence,
                "entropy": entropy,
            },
            "action": {
                "type": proposed_action.get("action_type", ""),
                "amount": proposed_action.get("amount")
                    or proposed_action.get("parameters", {}).get("amount", 0),
                "description": proposed_action.get("description", ""),
            },
            "user": {
                "role": context_data.get("user_role", "junior"),
                "id": context_data.get("user_id", ""),
            },
            "risk": {
                "level": context_data.get("risk_level", "LOW"),
            },
            "approval": {
                "status": context_data.get("approval_status", ""),
                "role": context_data.get("approver_role", ""),
                "escalated": context_data.get("escalated", False),
            },
            "prediction": {
                "source": context_data.get("prediction_source", ""),
                "effect_size": context_data.get("prediction_effect_size", 0.0),
                "confidence": confidence,
                "drift_detected": context_data.get("drift_detected", False),
                "is_actionable": context_data.get("is_actionable", False),
                "refutation_passed": context_data.get("refutation_passed", False),
            },
            "data": {
                "contains_pii": context_data.get("contains_pii", False),
                "is_masked": context_data.get("is_masked", False),
                "type": context_data.get("data_type", ""),
            },
            "session": {
                "active_predictions": context_data.get("active_predictions", 0),
            },
        }

    def _evaluate_builtin(self, context: dict[str, Any]) -> CSLEvaluation:
        """Evaluate policies using built-in Python rules."""
        all_results: list[CSLRuleResult] = []
        violations: list[CSLRuleResult] = []

        for policy in self._policies:
            results = policy.evaluate(context)
            all_results.extend(results)
            violations.extend(r for r in results if not r.passed)

        rules_checked = len(all_results)
        rules_passed = rules_checked - len(violations)

        # Determine allow based on fail mode
        allow = len(violations) == 0

        # Generate audit entries
        audit_entries = []
        if self.config.audit_enabled:
            for result in all_results:
                audit_entries.append({
                    "rule": result.rule_name,
                    "policy": result.policy_name,
                    "passed": result.passed,
                    "message": result.message,
                })

        return CSLEvaluation(
            allow=allow,
            rules_checked=rules_checked,
            rules_passed=rules_passed,
            rules_failed=len(violations),
            violations=violations,
            audit_entries=audit_entries,
        )

    async def evaluate(self, state: Any) -> CSLEvaluation:
        """Evaluate all CSL policies against the current state.

        Args:
            state: EpistemicState or dict containing state data

        Returns:
            CSLEvaluation with verdict and violation details
        """
        if not self.config.enabled:
            return CSLEvaluation(allow=True)

        try:
            context = self.map_state_to_context(state)
        except Exception as exc:
            logger.error(f"Failed to map state to CSL context: {exc}")
            if self.config.fail_closed:
                return CSLEvaluation(
                    allow=False,
                    error=f"Context mapping failed: {exc}",
                )
            return CSLEvaluation(allow=True, error=f"Context mapping failed: {exc}")

        try:
            if self._csl_available:
                # Use csl-core native evaluation (runs in thread to avoid blocking)
                return await asyncio.to_thread(self._evaluate_with_csl_core, context)
            else:
                # Use built-in Python evaluation
                return await asyncio.to_thread(self._evaluate_builtin, context)
        except Exception as exc:
            logger.error(f"CSL policy evaluation failed: {exc}")
            if self.config.fail_closed:
                return CSLEvaluation(
                    allow=False,
                    error=f"Evaluation failed: {exc}",
                )
            return CSLEvaluation(allow=True, error=f"Evaluation failed: {exc}")

    def _evaluate_with_csl_core(self, context: dict[str, Any]) -> CSLEvaluation:
        """Evaluate using the csl-core library.

        This method is called when csl-core is installed and available.
        Falls back to built-in evaluation if csl-core evaluation fails.
        """
        try:
            import csl_core  # type: ignore[import-untyped]

            policy_dir = Path(self.config.policy_dir)
            if not policy_dir.is_absolute():
                policy_dir = Path(__file__).parent.parent.parent / policy_dir

            # Load and compile policies
            guard = csl_core.load_guard(str(policy_dir))
            result = guard.evaluate(context)

            violations = []
            for v in result.get("violations", []):
                violations.append(CSLRuleResult(
                    rule_name=v.get("rule", "unknown"),
                    policy_name=v.get("policy", "unknown"),
                    passed=False,
                    message=v.get("message", ""),
                ))

            return CSLEvaluation(
                allow=result.get("allow", False),
                rules_checked=result.get("rules_checked", 0),
                rules_passed=result.get("rules_passed", 0),
                rules_failed=len(violations),
                violations=violations,
                audit_entries=result.get("audit", []),
            )

        except Exception as exc:
            logger.warning(f"CSL-Core evaluation failed, falling back to built-in: {exc}")
            return self._evaluate_builtin(context)

    @property
    def is_available(self) -> bool:
        """Check if CSL-Core is enabled and ready."""
        return self.config.enabled

    @property
    def policy_count(self) -> int:
        """Get the number of loaded policies."""
        return len(self._policies)

    @property
    def rule_count(self) -> int:
        """Get the total number of rules across all policies."""
        return sum(len(p.rules) for p in self._policies)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_csl_service: CSLPolicyService | None = None


def get_csl_service() -> CSLPolicyService:
    """Get or create the CSL policy service singleton."""
    global _csl_service
    if _csl_service is None:
        _csl_service = CSLPolicyService()
    return _csl_service
