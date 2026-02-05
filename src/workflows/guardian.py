"""Guardian Layer - Layer 4 of the CARF Cognitive Stack.

The Guardian is the non-negotiable safety net that checks all actions against
immutable policy constraints before execution.

Responsibilities:
- Policy enforcement (financial limits, data policies, operational constraints)
- Risk assessment with decomposed scoring
- Human escalation triggers for policy overrides
- Audit trail generation
- Context-aware policy application
- Transparent policy explanation

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
    CynefinDomain,
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
    user_overridable: bool = Field(default=False, description="Can user override this policy")
    override_requirements: list[str] = Field(default_factory=list)


class RiskComponent(BaseModel):
    """Individual risk component for decomposed scoring."""

    name: str
    score: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    weighted_score: float = Field(..., ge=0.0, le=1.0)
    status: str
    explanation: str


class GuardianDecision(BaseModel):
    """The Guardian's decision on an action."""

    verdict: GuardianVerdict
    violations: list[PolicyViolation] = Field(default_factory=list)
    risk_level: str = Field(default="low", pattern="^(low|medium|high|critical)$")
    explanation: str
    requires_human_override: bool = False
    modified_action: dict[str, Any] | None = None
    # New transparency fields
    risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Numeric risk score")
    risk_breakdown: list[RiskComponent] = Field(default_factory=list)
    policies_checked: int = 0
    policies_passed: int = 0
    context_adjustments: list[str] = Field(default_factory=list)


class ContextualPolicyConfig(BaseModel):
    """Context-aware policy configuration."""

    # Per-domain confidence thresholds
    confidence_thresholds: dict[str, float] = Field(
        default={
            "Clear": 0.95,
            "Complicated": 0.85,
            "Complex": 0.70,
            "Chaotic": 0.50,
            "Disorder": 0.0,
        },
        description="Minimum confidence required per Cynefin domain"
    )

    # Per-domain financial limits
    financial_limits: dict[str, float] = Field(
        default={
            "Clear": 100000,
            "Complicated": 50000,
            "Complex": 25000,
            "Chaotic": 10000,
            "Disorder": 0,
        },
        description="Auto-approval limit per domain"
    )

    # Risk weights for scoring
    risk_weights: dict[str, float] = Field(
        default={
            "confidence": 0.30,
            "data_quality": 0.25,
            "financial": 0.20,
            "operational": 0.15,
            "compliance": 0.10,
        },
        description="Weights for risk components"
    )

    # User-configurable limits
    user_financial_limit: float | None = Field(
        None, description="User-specified financial limit (overrides domain)"
    )
    user_confidence_threshold: float | None = Field(
        None, description="User-specified confidence threshold"
    )

    # Feature flags
    strict_mode: bool = Field(
        False, description="Reject on any violation (no escalation)"
    )
    audit_all: bool = Field(
        True, description="Log all decisions to audit trail"
    )


class PolicyEngine:
    """Engine for loading and evaluating policies from YAML configuration.

    Policies are organized into categories:
    - financial: Transaction limits, approved vendors
    - data: PII handling, data residency
    - operational: Timeouts, rate limits, reflection caps
    - risk: Confidence thresholds, entropy alerts
    - escalation: Actions that always require human approval

    Supports context-aware policy application based on Cynefin domain.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        contextual_config: ContextualPolicyConfig | None = None,
    ):
        """Initialize the policy engine.

        Args:
            config_path: Path to policies.yaml. If None, uses default location.
            contextual_config: Optional context-aware policy configuration.
        """
        self.policies: dict[str, Any] = {}
        self.contextual_config = contextual_config or ContextualPolicyConfig()
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
                "daily_limit": {"value": 500000, "currency": "USD"},
            },
            "operational": {
                "max_reflection_attempts": {"value": 2},
                "timeout": {"value_seconds": 300},
            },
            "risk": {
                "confidence_threshold": {"value": 0.85},
                "entropy_alert_threshold": {"value": 0.9},
            },
            "data": {
                "pii_handling": {"require_encryption": True},
                "data_residency": {"allowed_regions": ["EU", "US"]},
            },
            "escalation": {
                "always_escalate": {
                    "actions": ["delete_data", "modify_policy", "production_deployment"]
                }
            },
        }

    def get_context_aware_threshold(
        self,
        domain: CynefinDomain,
        threshold_type: str = "confidence",
    ) -> float:
        """Get threshold adjusted for Cynefin domain.

        Args:
            domain: Current Cynefin domain
            threshold_type: Type of threshold (confidence, financial)

        Returns:
            Adjusted threshold value
        """
        domain_name = domain.value

        if threshold_type == "confidence":
            # Check user override first
            if self.contextual_config.user_confidence_threshold is not None:
                return self.contextual_config.user_confidence_threshold
            return self.contextual_config.confidence_thresholds.get(domain_name, 0.85)

        elif threshold_type == "financial":
            # Check user override first
            if self.contextual_config.user_financial_limit is not None:
                return self.contextual_config.user_financial_limit
            return self.contextual_config.financial_limits.get(domain_name, 100000)

        return 0.85  # Default

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

    def check_confidence_threshold(
        self,
        confidence: float,
        domain: CynefinDomain | None = None,
    ) -> PolicyViolation | None:
        """Check if confidence is below required threshold.

        Uses context-aware threshold based on Cynefin domain.
        """
        # Get context-aware threshold
        if domain:
            threshold = self.get_context_aware_threshold(domain, "confidence")
        else:
            policy = self.get_policy("risk", "confidence_threshold")
            threshold = policy.get("value", 0.85) if policy else 0.85

        if confidence < threshold:
            return PolicyViolation(
                policy_name="confidence_threshold",
                policy_category="risk",
                description=f"Confidence ({confidence:.2f}) below threshold ({threshold:.2f}) for domain {domain.value if domain else 'default'}",
                severity="medium",
                suggested_fix="Gather more information or escalate to human",
                user_overridable=True,
                override_requirements=["Provide justification for low-confidence action"],
            )
        return None

    def check_financial_limit_contextual(
        self,
        amount: float,
        currency: str = "USD",
        domain: CynefinDomain | None = None,
    ) -> list[PolicyViolation]:
        """Check financial limit with context-aware threshold."""
        violations: list[PolicyViolation] = []

        # Get context-aware limit
        if domain:
            limit = self.get_context_aware_threshold(domain, "financial")
        else:
            policy = self.get_policy("financial", "auto_approval_limit")
            limit = policy.get("value", float("inf")) if policy else float("inf")

        if amount > limit:
            violations.append(PolicyViolation(
                policy_name="auto_approval_limit",
                policy_category="financial",
                description=f"Amount {amount:,.2f} {currency} exceeds limit of {limit:,.2f} for domain {domain.value if domain else 'default'}",
                severity="high",
                suggested_fix=f"Reduce amount to {limit:,.2f} {currency} or request human approval",
                user_overridable=True,
                override_requirements=["Manager approval", "Business justification"],
            ))

        return violations


class Guardian:
    """The Guardian layer that enforces safety policies.

    Checks all proposed actions against policy constraints and returns
    a verdict: approved, rejected, or requires_escalation.

    Features:
    - Context-aware policy application based on Cynefin domain
    - Decomposed risk scoring for transparency
    - User-configurable policy overrides
    - Detailed audit trail
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        contextual_config: ContextualPolicyConfig | None = None,
    ):
        """Initialize the Guardian.

        Args:
            config_path: Path to policies.yaml
            contextual_config: Optional context-aware configuration
        """
        self.contextual_config = contextual_config or ContextualPolicyConfig()
        self.policy_engine = PolicyEngine(config_path, self.contextual_config)

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

    def _compute_risk_breakdown(
        self,
        state: EpistemicState,
        violations: list[PolicyViolation],
    ) -> tuple[float, list[RiskComponent]]:
        """Compute decomposed risk score with transparency."""
        weights = self.contextual_config.risk_weights
        components = []

        # Confidence risk
        conf_score = 1.0 - state.domain_confidence  # Low confidence = high risk
        components.append(RiskComponent(
            name="Confidence Risk",
            score=conf_score,
            weight=weights.get("confidence", 0.30),
            weighted_score=conf_score * weights.get("confidence", 0.30),
            status="low" if conf_score < 0.3 else "medium" if conf_score < 0.6 else "high",
            explanation=f"Confidence: {state.domain_confidence:.1%}"
        ))

        # Financial risk (from violations)
        financial_violations = [v for v in violations if v.policy_category == "financial"]
        fin_score = min(1.0, len(financial_violations) * 0.5)
        components.append(RiskComponent(
            name="Financial Risk",
            score=fin_score,
            weight=weights.get("financial", 0.20),
            weighted_score=fin_score * weights.get("financial", 0.20),
            status="low" if fin_score < 0.3 else "medium" if fin_score < 0.6 else "high",
            explanation=f"{len(financial_violations)} financial violations"
        ))

        # Operational risk
        operational_violations = [v for v in violations if v.policy_category == "operational"]
        op_score = min(1.0, len(operational_violations) * 0.3)
        components.append(RiskComponent(
            name="Operational Risk",
            score=op_score,
            weight=weights.get("operational", 0.15),
            weighted_score=op_score * weights.get("operational", 0.15),
            status="low" if op_score < 0.3 else "medium" if op_score < 0.6 else "high",
            explanation=f"{len(operational_violations)} operational violations"
        ))

        # Data quality risk (from entropy)
        dq_score = state.domain_entropy  # High entropy = high risk
        components.append(RiskComponent(
            name="Data Quality Risk",
            score=dq_score,
            weight=weights.get("data_quality", 0.25),
            weighted_score=dq_score * weights.get("data_quality", 0.25),
            status="low" if dq_score < 0.3 else "medium" if dq_score < 0.6 else "high",
            explanation=f"Signal entropy: {state.domain_entropy:.2f}"
        ))

        # Compliance risk (escalation violations)
        escalation_violations = [v for v in violations if v.policy_category == "escalation"]
        comp_score = 1.0 if escalation_violations else 0.0
        components.append(RiskComponent(
            name="Compliance Risk",
            score=comp_score,
            weight=weights.get("compliance", 0.10),
            weighted_score=comp_score * weights.get("compliance", 0.10),
            status="low" if comp_score < 0.3 else "critical" if comp_score > 0.8 else "high",
            explanation=f"Mandatory escalation required" if escalation_violations else "No compliance issues"
        ))

        total_risk = sum(c.weighted_score for c in components)
        return total_risk, components

    async def evaluate(self, state: EpistemicState) -> GuardianDecision:
        """Evaluate the current state against all policies.

        Args:
            state: Current epistemic state with proposed action

        Returns:
            GuardianDecision with verdict, risk breakdown, and details
        """
        violations: list[PolicyViolation] = []
        context_adjustments: list[str] = []
        policies_checked = 0

        # Check 1: Context-aware confidence threshold
        policies_checked += 1
        confidence_violation = self.policy_engine.check_confidence_threshold(
            state.domain_confidence,
            domain=state.cynefin_domain,
        )
        if confidence_violation:
            violations.append(confidence_violation)
            context_adjustments.append(
                f"Confidence threshold adjusted for {state.cynefin_domain.value} domain"
            )

        # Check 2: Reflection limit
        policies_checked += 1
        reflection_violation = self.policy_engine.check_reflection_limit(
            state.reflection_count
        )
        if reflection_violation:
            violations.append(reflection_violation)

        # Check 3: Proposed action checks
        if state.proposed_action:
            action = state.proposed_action

            # Check action type for mandatory escalation
            policies_checked += 1
            action_type = action.get("action_type", "")
            escalation_violation = self.policy_engine.check_always_escalate(action_type)
            if escalation_violation:
                violations.append(escalation_violation)

            # Check context-aware financial limits
            amount = action.get("amount") or action.get("parameters", {}).get("amount")
            if amount is not None:
                policies_checked += 1
                financial_violations = self.policy_engine.check_financial_limit_contextual(
                    float(amount),
                    action.get("currency", "USD"),
                    domain=state.cynefin_domain,
                )
                violations.extend(financial_violations)
                if financial_violations:
                    context_adjustments.append(
                        f"Financial limit adjusted for {state.cynefin_domain.value} domain"
                    )

        # Compute risk breakdown
        risk_score, risk_breakdown = self._compute_risk_breakdown(state, violations)

        # Assess overall risk level
        risk_level = (
            "critical" if risk_score > 0.8
            else "high" if risk_score > 0.6
            else "medium" if risk_score > 0.3
            else "low"
        )

        # Determine verdict
        if self.contextual_config.strict_mode and violations:
            verdict = GuardianVerdict.REJECTED
        else:
            verdict = self._determine_verdict(violations, risk_level)

        # Build explanation
        policies_passed = policies_checked - len(violations)
        if not violations:
            explanation = f"All {policies_checked} policy checks passed. Action approved."
        else:
            violation_summaries = [v.description for v in violations]
            explanation = f"Policy violations ({len(violations)}/{policies_checked}): {'; '.join(violation_summaries)}"

        decision = GuardianDecision(
            verdict=verdict,
            violations=violations,
            risk_level=risk_level,
            explanation=explanation,
            requires_human_override=(verdict == GuardianVerdict.REQUIRES_ESCALATION),
            risk_score=risk_score,
            risk_breakdown=risk_breakdown,
            policies_checked=policies_checked,
            policies_passed=policies_passed,
            context_adjustments=context_adjustments,
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
_guardian_config: ContextualPolicyConfig | None = None


def get_guardian() -> Guardian:
    """Get or create the Guardian singleton."""
    global _guardian_instance, _guardian_config
    if _guardian_instance is None:
        _guardian_instance = Guardian(contextual_config=_guardian_config)
    return _guardian_instance


def get_guardian_config() -> ContextualPolicyConfig:
    """Get current Guardian policy configuration."""
    guardian = get_guardian()
    return guardian.contextual_config


def update_guardian_config(config: ContextualPolicyConfig) -> Guardian:
    """Update Guardian configuration and recreate instance."""
    global _guardian_instance, _guardian_config
    _guardian_config = config
    _guardian_instance = Guardian(contextual_config=config)
    logger.info(f"Guardian configuration updated")
    return _guardian_instance


async def guardian_node(state: EpistemicState) -> EpistemicState:
    """LangGraph node for the Guardian layer.

    Usage in LangGraph:
        workflow.add_node("guardian", guardian_node)
    """
    guardian = get_guardian()
    return await guardian.check(state)
