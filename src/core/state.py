"""Core state definitions for CARF.

This module defines the Pydantic schemas for the EpistemicState
and related types that flow through the LangGraph workflow.

DO NOT MODIFY without updating AGENTS.md - this is the immutable schema core.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CynefinDomain(str, Enum):
    """The Cynefin framework domains for context classification.

    Used by the Router to determine which cognitive pathway to activate.
    """

    CLEAR = "Clear"  # Cause-effect obvious → Deterministic automation
    COMPLICATED = "Complicated"  # Cause-effect requires analysis → Causal inference
    COMPLEX = "Complex"  # Cause-effect only in retrospect → Bayesian probing
    CHAOTIC = "Chaotic"  # System in crisis → Circuit breaker
    DISORDER = "Disorder"  # Cannot classify → Human escalation


class HumanInteractionStatus(str, Enum):
    """Status of human-in-the-loop interactions via HumanLayer."""

    IDLE = "idle"  # No pending human interaction
    WAITING_APPROVAL = "waiting_approval"  # Awaiting human response
    APPROVED = "approved"  # Human approved the action
    REJECTED = "rejected"  # Human rejected the action
    MODIFIED = "modified"  # Human modified the proposed action
    TIMEOUT = "timeout"  # Human did not respond in time


class GuardianVerdict(str, Enum):
    """Verdict from the Guardian layer policy check."""

    APPROVED = "approved"  # Action passes all policy constraints
    REJECTED = "rejected"  # Action violates policy
    REQUIRES_ESCALATION = "requires_escalation"  # Needs human override


class ConfidenceLevel(str, Enum):
    """Epistemic confidence levels for uncertainty visualization."""

    HIGH = "high"  # Posterior variance < threshold (Green)
    MEDIUM = "medium"  # Gathering data (Yellow)
    LOW = "low"  # High entropy / Disorder (Red)


class CausalEvidence(BaseModel):
    """Evidence from causal inference analysis."""

    effect_size: float = Field(..., description="Estimated causal effect")
    confidence_interval: tuple[float, float] = Field(
        ..., description="95% CI bounds"
    )
    refutation_passed: bool = Field(
        default=False, description="Whether placebo refutation test passed"
    )
    confounders_checked: list[str] = Field(
        default_factory=list, description="List of confounders tested"
    )
    # Full structured result for UIX panels
    p_value: float | None = Field(default=None, description="Statistical p-value")
    refutation_results: dict[str, bool] = Field(
        default_factory=dict, description="Individual refutation test results"
    )
    interpretation: str = Field(default="", description="Human-readable interpretation")
    treatment: str = Field(default="", description="Treatment variable name")
    outcome: str = Field(default="", description="Outcome variable name")
    mechanism: str = Field(default="", description="Causal mechanism description")


class BayesianEvidence(BaseModel):
    """Evidence from Bayesian active inference analysis."""

    posterior_mean: float = Field(..., description="Posterior mean estimate")
    credible_interval: tuple[float, float] = Field(
        ..., description="95% credible interval"
    )
    uncertainty_before: float = Field(default=1.0, description="Initial uncertainty")
    uncertainty_after: float = Field(default=1.0, description="Final uncertainty")
    epistemic_uncertainty: float = Field(default=0.0, description="Reducible uncertainty")
    aleatoric_uncertainty: float = Field(default=0.0, description="Irreducible uncertainty")
    hypothesis: str = Field(default="", description="Primary hypothesis")
    confidence_level: str = Field(default="low", description="Confidence level")
    interpretation: str = Field(default="", description="Human-readable interpretation")
    probes_designed: int = Field(default=0, description="Number of probes designed")
    recommended_probe: str | None = Field(default=None, description="Recommended next action")




class HumanVerificationMetadata(BaseModel):
    """Metadata for human verification events (HumanLayer integration)."""

    requires_approval: bool = False
    human_layer_id: Optional[str] = None
    approver_email: Optional[str] = None
    approval_channel: Optional[str] = None  # "slack", "teams", "email"
    approval_timestamp: Optional[datetime] = None
    human_comment: Optional[str] = None


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain for audit trail."""

    step_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    node_name: str = Field(..., description="LangGraph node that executed")
    action: str = Field(..., description="What the node did")
    input_summary: str = Field(..., description="Summary of inputs")
    output_summary: str = Field(..., description="Summary of outputs")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    duration_ms: int = Field(default=0, description="Execution duration in ms")


class EpistemicState(BaseModel):
    """The core state object that flows through the CARF workflow.

    This is the 'single source of truth' for the agent's epistemic awareness.
    It tracks what the system knows, infers, and does not know.
    """

    # --- Session Identification ---
    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Cynefin Context Classification ---
    cynefin_domain: CynefinDomain = Field(
        default=CynefinDomain.DISORDER,
        description="Current domain classification from the Router",
    )
    domain_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Router's confidence in domain classification",
    )
    domain_entropy: float = Field(
        default=1.0,
        ge=0.0,
        description="Entropy measure from signal analysis",
    )
    router_key_indicators: list[str] = Field(
        default_factory=list,
        description="Key indicators that led to domain classification",
    )
    domain_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each Cynefin domain",
    )
    triggered_method: str = Field(
        default="",
        description="Analysis method triggered by classification (causal/bayesian/circuit_breaker)",
    )

    # --- Input & Task ---
    user_input: str = Field(default="", description="Original user request")
    task_description: str = Field(default="", description="Parsed task intent")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context data"
    )

    # --- Evaluation Scores (DeepEval Quality Metrics) ---
    evaluation_scores: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="DeepEval quality scores by node (relevancy, hallucination_risk, reasoning_depth, uix_compliance)",
    )

    # --- Reasoning Chain ---
    reasoning_chain: list[ReasoningStep] = Field(
        default_factory=list,
        description="Audit trail of reasoning steps",
    )
    current_hypothesis: Optional[str] = Field(
        default=None, description="Current working hypothesis"
    )
    causal_evidence: Optional[CausalEvidence] = Field(
        default=None, description="Evidence from causal analysis"
    )
    bayesian_evidence: Optional[BayesianEvidence] = Field(
        default=None, description="Evidence from Bayesian active inference"
    )

    # --- Uncertainty Tracking ---
    epistemic_uncertainty: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How much we don't know (reducible uncertainty)",
    )
    aleatoric_uncertainty: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Inherent randomness (irreducible uncertainty)",
    )
    overall_confidence: ConfidenceLevel = Field(default=ConfidenceLevel.LOW)

    # --- Guardian Layer ---
    proposed_action: Optional[dict[str, Any]] = Field(
        default=None, description="Action proposed by the cognitive mesh"
    )
    guardian_verdict: Optional[GuardianVerdict] = Field(
        default=None, description="Guardian's policy verdict"
    )
    policy_violations: list[str] = Field(
        default_factory=list, description="List of violated policies"
    )

    # --- Self-Correction ---
    reflection_count: int = Field(
        default=0, ge=0, description="Number of self-correction attempts"
    )
    max_reflections: int = Field(
        default=2, description="Max reflections before human escalation"
    )

    # --- Human-in-the-Loop (HumanLayer) ---
    human_interaction_status: HumanInteractionStatus = Field(
        default=HumanInteractionStatus.IDLE
    )
    human_verification: Optional[HumanVerificationMetadata] = Field(
        default=None, description="HumanLayer verification metadata"
    )
    last_human_feedback: Optional[str] = Field(
        default=None, description="Last feedback from human"
    )
    human_override_instructions: Optional[str] = Field(
        default=None, description="Human-provided override instructions"
    )

    # --- Output ---
    final_response: Optional[str] = Field(
        default=None, description="Final response to user"
    )
    final_action: Optional[dict[str, Any]] = Field(
        default=None, description="Final executed action"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")

    def add_reasoning_step(
        self,
        node_name: str,
        action: str,
        input_summary: str,
        output_summary: str,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        duration_ms: int = 0,
    ) -> None:
        """Add a step to the reasoning chain for audit trail."""
        step = ReasoningStep(
            node_name=node_name,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            confidence=confidence,
            duration_ms=duration_ms,
        )
        self.reasoning_chain.append(step)
        self.updated_at = datetime.utcnow()

    def should_escalate_to_human(self) -> bool:
        """Determine if the state warrants human escalation."""
        return (
            self.cynefin_domain == CynefinDomain.DISORDER
            or self.cynefin_domain == CynefinDomain.CHAOTIC
            or self.reflection_count >= self.max_reflections
            or self.guardian_verdict == GuardianVerdict.REQUIRES_ESCALATION
            or self.domain_confidence < 0.85
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "cynefin_domain": "Complicated",
                "domain_confidence": 0.92,
                "user_input": "Analyze why supplier costs increased 15%",
                "human_interaction_status": "idle",
            }
        }
    }


# Type alias for LangGraph compatibility
AgentState = EpistemicState
