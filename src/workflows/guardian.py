"""Guardian Layer - Layer 4 of the CARF Cognitive Stack.

The Guardian is the non-negotiable safety net that checks all actions against
immutable policy constraints before execution.

Responsibilities:
- Policy enforcement (financial limits, data policies, operational constraints)
- Risk assessment
- Human escalation triggers for policy overrides
- Audit trail generation

In Phase 3, this will integrate with Open Policy Agent (OPA) for enterprise-grade
policy enforcement. For MVP, we use YAML-based policy definitions.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.core.state import (
    ConfidenceLevel,
    EpistemicState,
    GuardianVerdict,
)
from src.services.opa_service import get_opa_service

logger = logging.getLogger("carf.guardian")


class PolicyViolation(BaseModel):
    """Details of a policy violation."""

    policy_name: str
    policy_category: str
    description: str
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    suggested_fix: str | None = None


class GuardianDecision(BaseModel):
    """The Guardian's decision on an action."""

    verdict: GuardianVerdict
    violations: list[PolicyViolation] = Field(default_factory=list)
    risk_level: str = Field(default="low", pattern="^(low|medium|high|critical)$")
    explanation: str
    requires_human_override: bool = False
    modified_action: dict[str, Any] | None = None


class PolicyEngine:
    """Engine for loading and evaluating policies from YAML configuration.

    Policies are organized into categories:
    - financial: Transaction limits, approved vendors
    - data: PII handling, data residency
    - operational: Timeouts, rate limits, reflection caps
    - risk: Confidence thresholds, entropy alerts
    - escalation: Actions that always require human approval
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize the policy engine.

        Args:
            config_path: Path to policies.yaml. If None, uses default location.
        """
        self.policies: dict[str, Any] = {}
        self._load_policies(config_path)

    def _load_policies(self, config_path: str | Path | None) -> None:
        """Load policies from YAML configuration."""
        if config_path is None:
            # Default path relative to project root
            config_path = Path(__file__).parent.parent.parent / "config" / "policies.yaml"

        try:
            with open(config_path) as f:
                self.policies = yaml.safe_load(f) or {}
            logger.info(f"Loaded policies from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Policy file not found: {config_path}. Using defaults.")
            self._set_default_policies()
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse policies: {e}. Using defaults.")
            self._set_default_policies()

    def _set_default_policies(self) -> None:
        """Set minimal default policies for MVP."""
        self.policies = {
            "financial": {
                "auto_approval_limit": {"value": 100000, "currency": "USD"},
            },
            "operational": {
                "max_reflection_attempts": {"value": 2},
                "timeout": {"value_seconds": 300},
            },
            "risk": {
                "confidence_threshold": {"value": 0.85},
            },
            "escalation": {
                "always_escalate": {
                    "actions": ["delete_data", "modify_policy", "production_deployment"]
                }
            },
        }

    def get_policy(self, category: str, name: str) -> dict[str, Any] | None:
        """Get a specific policy by category and name."""
        return self.policies.get(category, {}).get(name)

    def check_financial_limit(
        self,
        amount: float,
        currency: str = "USD",
    ) -> list[PolicyViolation]:
        """Check if amount exceeds financial auto-approval limit."""
        policy = self.get_policy("financial", "auto_approval_limit")
        if not policy:
            return []

        violations: list[PolicyViolation] = []
        limit = policy.get("value", float("inf"))
        policy_currency = policy.get("currency", "USD")

        if currency != policy_currency:
            violations.append(PolicyViolation(
                policy_name="currency_mismatch",
                policy_category="financial",
                description=(
                    f"Currency mismatch: action uses {currency} "
                    f"but policy limit is in {policy_currency}"
                ),
                severity="medium",
                suggested_fix=(
                    f"Convert amount to {policy_currency} or "
                    f"specify the amount in {policy_currency}"
                ),
            ))

        if amount > limit:
            violations.append(PolicyViolation(
                policy_name="auto_approval_limit",
                policy_category="financial",
                description=f"Amount {amount:,.2f} {currency} exceeds auto-approval limit of {limit:,.2f} {policy_currency}",
                severity="high",
                suggested_fix=f"Reduce amount to {limit:,.2f} {policy_currency} or request human approval",
            ))

        return violations

    def check_always_escalate(self, action_type: str) -> PolicyViolation | None:
        """Check if action type requires mandatory human escalation."""
        policy = self.get_policy("escalation", "always_escalate")
        if not policy:
            return None

        always_escalate_actions = policy.get("actions", [])
        if action_type in always_escalate_actions:
            return PolicyViolation(
                policy_name="always_escalate",
                policy_category="escalation",
                description=f"Action '{action_type}' requires mandatory human approval",
                severity="high",
            )
        return None

    def check_reflection_limit(self, count: int) -> PolicyViolation | None:
        """Check if reflection attempts exceed limit."""
        policy = self.get_policy("operational", "max_reflection_attempts")
        if not policy:
            return None

        limit = policy.get("value", 3)
        if count >= limit:
            return PolicyViolation(
                policy_name="max_reflection_attempts",
                policy_category="operational",
                description=f"Reflection count ({count}) has reached limit ({limit})",
                severity="medium",
                suggested_fix="Escalate to human for resolution",
            )
        return None

    def check_confidence_threshold(self, confidence: float) -> PolicyViolation | None:
        """Check if confidence is below required threshold."""
        policy = self.get_policy("risk", "confidence_threshold")
        if not policy:
            return None

        threshold = policy.get("value", 0.85)
        if confidence < threshold:
            return PolicyViolation(
                policy_name="confidence_threshold",
                policy_category="risk",
                description=f"Confidence ({confidence:.2f}) below threshold ({threshold})",
                severity="medium",
                suggested_fix="Gather more information or escalate to human",
            )
        return None


class Guardian:
    """The Guardian layer that enforces safety policies.

    Checks all proposed actions against policy constraints and returns
    a verdict: approved, rejected, or requires_escalation.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize the Guardian.

        Args:
            config_path: Path to policies.yaml
        """
        self.policy_engine = PolicyEngine(config_path)

    def _assess_risk_level(self, violations: list[PolicyViolation]) -> str:
        """Determine overall risk level from violations."""
        if not violations:
            return "low"

        severities = [v.severity for v in violations]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _determine_verdict(
        self,
        violations: list[PolicyViolation],
        risk_level: str,
    ) -> GuardianVerdict:
        """Determine verdict based on violations and risk."""
        if not violations:
            return GuardianVerdict.APPROVED

        # Critical violations → reject
        if risk_level == "critical":
            return GuardianVerdict.REJECTED

        # High-severity violations that can be overridden → escalate
        high_violations = [v for v in violations if v.severity in ("high", "critical")]
        if high_violations:
            return GuardianVerdict.REQUIRES_ESCALATION

        # Medium/low violations might still pass with warning
        return GuardianVerdict.REQUIRES_ESCALATION

    async def _apply_opa(
        self,
        state: EpistemicState,
        decision: GuardianDecision,
    ) -> GuardianDecision:
        """Apply optional OPA policy checks to an existing decision."""
        service = get_opa_service()
        if not service.config.enabled:
            return decision

        input_data = {
            "session_id": str(state.session_id),
            "cynefin_domain": state.cynefin_domain.value,
            "domain_confidence": state.domain_confidence,
            "domain_entropy": state.domain_entropy,
            "proposed_action": state.proposed_action,
            "guardian_verdict": decision.verdict.value,
            "policy_violations": [v.description for v in decision.violations],
        }

        try:
            evaluation = await service.evaluate(input_data)
        except Exception as exc:
            violations = list(decision.violations)
            violations.append(
                PolicyViolation(
                    policy_name="opa_unavailable",
                    policy_category="opa",
                    description=f"OPA evaluation failed: {exc}",
                    severity="high",
                    suggested_fix="Verify OPA endpoint and policy bundle",
                )
            )
            risk_level = self._assess_risk_level(violations)
            return GuardianDecision(
                verdict=GuardianVerdict.REQUIRES_ESCALATION,
                violations=violations,
                risk_level=risk_level,
                explanation="OPA evaluation failed; human escalation required.",
                requires_human_override=True,
            )

        if evaluation.allow:
            return decision

        violations = list(decision.violations)
        violations.append(
            PolicyViolation(
                policy_name="opa_denied",
                policy_category="opa",
                description="OPA policy denied the proposed action",
                severity="high",
                suggested_fix="Review OPA policy decision and adjust action",
            )
        )
        risk_level = self._assess_risk_level(violations)
        return GuardianDecision(
            verdict=GuardianVerdict.REJECTED,
            violations=violations,
            risk_level=risk_level,
            explanation="OPA policy denied the proposed action.",
            requires_human_override=False,
        )

    async def evaluate(self, state: EpistemicState) -> GuardianDecision:
        """Evaluate the current state against all policies.

        Args:
            state: Current epistemic state with proposed action

        Returns:
            GuardianDecision with verdict and details
        """
        violations: list[PolicyViolation] = []

        # Check 1: Confidence threshold
        confidence_violation = self.policy_engine.check_confidence_threshold(
            state.domain_confidence
        )
        if confidence_violation:
            violations.append(confidence_violation)

        # Check 2: Reflection limit
        reflection_violation = self.policy_engine.check_reflection_limit(
            state.reflection_count
        )
        if reflection_violation:
            violations.append(reflection_violation)

        # Check 3: Proposed action checks
        if state.proposed_action:
            action = state.proposed_action

            # Check action type for mandatory escalation
            action_type = action.get("action_type", "")
            escalation_violation = self.policy_engine.check_always_escalate(action_type)
            if escalation_violation:
                violations.append(escalation_violation)

            # Check financial limits
            amount = action.get("amount") or action.get("parameters", {}).get("amount")
            if amount is not None:
                financial_violations = self.policy_engine.check_financial_limit(
                    float(amount),
                    action.get("currency", "USD"),
                )
                violations.extend(financial_violations)

        # Assess overall risk
        risk_level = self._assess_risk_level(violations)

        # Determine verdict
        verdict = self._determine_verdict(violations, risk_level)

        # Build explanation
        if not violations:
            explanation = "All policy checks passed. Action approved."
        else:
            violation_summaries = [v.description for v in violations]
            explanation = f"Policy violations detected: {'; '.join(violation_summaries)}"

        decision = GuardianDecision(
            verdict=verdict,
            violations=violations,
            risk_level=risk_level,
            explanation=explanation,
            requires_human_override=(verdict == GuardianVerdict.REQUIRES_ESCALATION),
        )

        return await self._apply_opa(state, decision)

    async def check(self, state: EpistemicState) -> EpistemicState:
        """Check the state against policies and update it.

        This is the main entry point, designed to be used as a LangGraph node.

        Args:
            state: Current epistemic state

        Returns:
            Updated epistemic state with guardian verdict
        """
        logger.info(f"Guardian evaluating session {state.session_id}")

        decision = await self.evaluate(state)

        # Update state
        state.guardian_verdict = decision.verdict
        state.policy_violations = [v.description for v in decision.violations]

        # Record reasoning step
        state.add_reasoning_step(
            node_name="guardian",
            action=f"Policy check: {decision.verdict.value}",
            input_summary=f"Proposed action: {state.proposed_action}",
            output_summary=decision.explanation,
            confidence=(
                ConfidenceLevel.HIGH
                if decision.verdict == GuardianVerdict.APPROVED
                else ConfidenceLevel.MEDIUM
            ),
        )

        logger.info(
            f"Guardian verdict: {decision.verdict.value} "
            f"(risk: {decision.risk_level}, violations: {len(decision.violations)})"
        )

        return state


# Singleton instance
_guardian_instance: Guardian | None = None


def get_guardian() -> Guardian:
    """Get or create the Guardian singleton."""
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = Guardian()
    return _guardian_instance


async def guardian_node(state: EpistemicState) -> EpistemicState:
    """LangGraph node for the Guardian layer.

    Usage in LangGraph:
        workflow.add_node("guardian", guardian_node)
    """
    guardian = get_guardian()
    return await guardian.check(state)
