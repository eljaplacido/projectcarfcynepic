"""Transparency and Reliability Service for CARF.

Provides comprehensive transparency, traceability, and reliability metrics for:
- Agent chain-of-thought visibility
- Data quality and reliability scoring
- EU AI Act compliance metrics
- Workflow evaluation and feasibility scoring
- Guardian policy transparency
- Analysis trustworthiness indicators

This service is central to CARF's mission of providing actionable, transparent,
and auditable AI-driven insights.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.transparency")


# =============================================================================
# Enums and Constants
# =============================================================================

class ReliabilityLevel(str, Enum):
    """Reliability levels for analysis results."""
    VERY_HIGH = "very_high"      # >95% confidence, all checks passed
    HIGH = "high"                # >85% confidence, most checks passed
    MEDIUM = "medium"            # >70% confidence, some concerns
    LOW = "low"                  # >50% confidence, significant concerns
    VERY_LOW = "very_low"        # <50% confidence, use with caution
    UNKNOWN = "unknown"          # Cannot assess reliability


class ComplianceStatus(str, Enum):
    """EU AI Act compliance status."""
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class DataQualityLevel(str, Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"      # Complete, no issues
    GOOD = "good"                # Minor issues, usable
    FAIR = "fair"                # Some issues, proceed with caution
    POOR = "poor"                # Significant issues
    UNUSABLE = "unusable"        # Cannot use for analysis


# =============================================================================
# Agent Transparency Models
# =============================================================================

class AgentInfo(BaseModel):
    """Information about an agent used in the analysis pipeline."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_type: str = Field(..., description="Agent type (router, causal, bayesian, guardian)")
    role: str = Field(..., description="Role in the analysis")
    model_used: str | None = Field(None, description="LLM/ML model used")
    version: str = Field("1.0", description="Agent version")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")


class AgentDecision(BaseModel):
    """A decision made by an agent with full transparency."""
    decision_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: AgentInfo
    input_summary: str = Field(..., description="What the agent received")
    output_summary: str = Field(..., description="What the agent produced")
    reasoning: str = Field(..., description="Why the agent made this decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Agent's confidence")
    confidence_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Decomposed confidence factors"
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Other options the agent considered"
    )
    data_sources_used: list[str] = Field(
        default_factory=list,
        description="Data sources informing this decision"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made by the agent"
    )


class AgentChainTrace(BaseModel):
    """Complete trace of agent chain-of-thought."""
    session_id: UUID
    query: str
    total_agents_invoked: int = 0
    decisions: list[AgentDecision] = Field(default_factory=list)
    execution_path: list[str] = Field(default_factory=list, description="Node path taken")
    total_duration_ms: int = 0
    final_confidence: float = 0.0
    reliability_assessment: "ReliabilityAssessment | None" = None


# =============================================================================
# Reliability and Data Quality Models
# =============================================================================

class DataQualityMetric(BaseModel):
    """Individual data quality metric."""
    name: str
    score: float = Field(..., ge=0.0, le=1.0)
    status: DataQualityLevel
    description: str
    recommendation: str | None = None


class DataQualityAssessment(BaseModel):
    """Complete data quality assessment."""
    dataset_id: str | None = None
    overall_score: float = Field(..., ge=0.0, le=1.0)
    overall_status: DataQualityLevel
    metrics: list[DataQualityMetric] = Field(default_factory=list)
    completeness: float = Field(0.0, description="% of non-null values")
    consistency: float = Field(0.0, description="% of values matching expected patterns")
    sample_size: int = 0
    outlier_percentage: float = 0.0
    missing_values_percentage: float = 0.0
    duplicate_percentage: float = 0.0
    data_types_valid: bool = True
    temporal_coverage: str | None = None
    recommendations: list[str] = Field(default_factory=list)


class ReliabilityFactor(BaseModel):
    """Individual factor contributing to reliability."""
    name: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Importance weight")
    score: float = Field(..., ge=0.0, le=1.0, description="Factor score")
    weighted_score: float = Field(..., description="weight * score")
    status: str
    explanation: str
    improvement_actions: list[str] = Field(default_factory=list)


class DeepEvalScores(BaseModel):
    """DeepEval quality metrics for LLM outputs.

    These scores provide quantitative measures of LLM response quality
    based on the DeepEval framework for LLM evaluation.
    """
    relevancy_score: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How relevant the response is to the input query"
    )
    hallucination_risk: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Risk of hallucinated content (0=no risk, 1=high risk)"
    )
    reasoning_depth: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Quality and depth of reasoning in response"
    )
    uix_compliance: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Compliance with CARF UIX standards (Why? How confident? Based on what?)"
    )
    task_completion: bool = Field(
        False,
        description="Whether the response adequately addresses the query"
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when evaluation was performed"
    )


class ReliabilityAssessment(BaseModel):
    """Comprehensive reliability assessment of an analysis."""
    assessment_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Overall scores
    overall_score: float = Field(..., ge=0.0, le=1.0)
    overall_level: ReliabilityLevel

    # Decomposed factors
    factors: list[ReliabilityFactor] = Field(default_factory=list)

    # Component scores
    data_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    model_confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    refutation_score: float = Field(0.0, ge=0.0, le=1.0)
    sample_size_score: float = Field(0.0, ge=0.0, le=1.0)
    domain_expertise_score: float = Field(0.0, ge=0.0, le=1.0)

    # DeepEval LLM quality scores (optional, populated when evaluation enabled)
    deepeval_scores: DeepEvalScores | None = Field(
        None,
        description="LLM quality metrics from DeepEval evaluation"
    )

    # Recommendations
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)

    # Metadata
    methodology_used: str = ""
    confidence_interval_coverage: str | None = None


# =============================================================================
# EU AI Act Compliance Models
# =============================================================================

class ComplianceRequirement(BaseModel):
    """Individual EU AI Act compliance requirement."""
    requirement_id: str
    article: str = Field(..., description="EU AI Act article reference")
    title: str
    description: str
    status: ComplianceStatus
    evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    remediation_steps: list[str] = Field(default_factory=list)


class EUAIActComplianceReport(BaseModel):
    """EU AI Act compliance assessment report."""
    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    ai_system_name: str = "CARF - Complex-Adaptive Reasoning Fabric"
    risk_category: str = "limited"  # minimal, limited, high, unacceptable

    # Overall compliance
    overall_status: ComplianceStatus
    compliance_score: float = Field(..., ge=0.0, le=1.0)

    # Individual requirements
    requirements: list[ComplianceRequirement] = Field(default_factory=list)

    # Key compliance areas
    transparency_score: float = Field(0.0, ge=0.0, le=1.0)
    documentation_score: float = Field(0.0, ge=0.0, le=1.0)
    human_oversight_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_management_score: float = Field(0.0, ge=0.0, le=1.0)
    data_governance_score: float = Field(0.0, ge=0.0, le=1.0)

    # Recommendations
    priority_actions: list[str] = Field(default_factory=list)


# =============================================================================
# Workflow Evaluation Models
# =============================================================================

class WorkflowEvaluationCriteria(BaseModel):
    """Criteria for evaluating a workflow or analysis approach."""
    criterion: str
    weight: float = Field(..., ge=0.0, le=1.0)
    score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    improvement_potential: str | None = None


class WorkflowEvaluation(BaseModel):
    """Evaluation of an agentic workflow's feasibility and reliability."""
    evaluation_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Input description
    workflow_name: str
    use_case: str
    data_types: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)

    # Scores
    feasibility_score: float = Field(..., ge=0.0, le=1.0)
    reliability_score: float = Field(..., ge=0.0, le=1.0)
    transparency_score: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)

    # Detailed criteria
    criteria: list[WorkflowEvaluationCriteria] = Field(default_factory=list)

    # Recommendations
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # EU AI Act alignment
    eu_ai_act_alignment: float = Field(0.0, ge=0.0, le=1.0)
    compliance_gaps: list[str] = Field(default_factory=list)


# =============================================================================
# Guardian Transparency Models
# =============================================================================

class PolicyDefinition(BaseModel):
    """Detailed policy definition for transparency."""
    policy_id: str
    name: str
    category: str
    description: str
    rationale: str = Field(..., description="Why this policy exists")
    threshold_value: Any | None = None
    threshold_unit: str | None = None
    severity: str = Field("medium", description="low, medium, high, critical")
    user_configurable: bool = False
    configuration_range: dict[str, Any] | None = None


class GuardianTransparencyReport(BaseModel):
    """Transparency report for Guardian layer decisions."""
    session_id: UUID
    verdict: str
    policies_evaluated: list[PolicyDefinition] = Field(default_factory=list)
    policies_passed: list[str] = Field(default_factory=list)
    policies_violated: list[str] = Field(default_factory=list)
    risk_breakdown: dict[str, float] = Field(default_factory=dict)
    escalation_reason: str | None = None
    user_override_available: bool = False
    override_requirements: list[str] = Field(default_factory=list)


# =============================================================================
# Transparency Service Implementation
# =============================================================================

class TransparencyService:
    """Service for providing transparency, traceability, and reliability metrics."""

    def __init__(self):
        self._agent_registry: dict[str, AgentInfo] = self._init_agent_registry()

    def _init_agent_registry(self) -> dict[str, AgentInfo]:
        """Initialize registry of known agents."""
        return {
            "cynefin_router": AgentInfo(
                agent_id="cynefin_router",
                agent_name="Cynefin Router",
                agent_type="router",
                role="Classifies queries into Cynefin domains to determine analysis approach",
                model_used="LLM (configurable: OpenAI/DeepSeek/Anthropic)",
                capabilities=[
                    "Domain classification (Clear, Complicated, Complex, Chaotic, Disorder)",
                    "Entropy calculation for uncertainty assessment",
                    "Pattern recognition for domain hints",
                    "Confidence scoring"
                ],
                limitations=[
                    "Relies on LLM interpretation which may vary",
                    "Domain boundaries can be ambiguous",
                    "May misclassify novel query types"
                ]
            ),
            "causal_analyst": AgentInfo(
                agent_id="causal_analyst",
                agent_name="Causal Inference Agent",
                agent_type="causal",
                role="Performs causal analysis using DoWhy/EconML for Complicated domain queries",
                model_used="DoWhy + EconML (CausalForestDML)",
                capabilities=[
                    "Average Treatment Effect (ATE) estimation",
                    "Conditional Average Treatment Effect (CATE)",
                    "Refutation testing (placebo, random cause, subset)",
                    "Confounder identification",
                    "Causal graph construction"
                ],
                limitations=[
                    "Assumes correct causal graph structure",
                    "Sensitive to unmeasured confounders",
                    "Requires sufficient sample size",
                    "Cannot prove causation, only estimate effects"
                ]
            ),
            "bayesian_explorer": AgentInfo(
                agent_id="bayesian_explorer",
                agent_name="Bayesian Inference Agent",
                agent_type="bayesian",
                role="Performs Bayesian analysis for Complex domain queries with high uncertainty",
                model_used="PyMC (MCMC sampling)",
                capabilities=[
                    "Posterior distribution estimation",
                    "Uncertainty quantification (epistemic vs aleatoric)",
                    "Probe design for information gathering",
                    "Hypothesis updating with new evidence"
                ],
                limitations=[
                    "Prior specification affects results",
                    "Computationally intensive for large models",
                    "MCMC convergence not guaranteed",
                    "Interpretability of posteriors requires expertise"
                ]
            ),
            "guardian": AgentInfo(
                agent_id="guardian",
                agent_name="Guardian Policy Engine",
                agent_type="guardian",
                role="Enforces safety policies and determines action approval",
                model_used="Rule-based engine + OPA (optional)",
                capabilities=[
                    "Policy evaluation (financial, operational, risk)",
                    "Risk level assessment",
                    "Human escalation triggering",
                    "Audit trail generation"
                ],
                limitations=[
                    "Policies must be pre-defined",
                    "Cannot handle novel policy scenarios",
                    "Binary decisions may not capture nuance"
                ]
            ),
            "chimera_oracle": AgentInfo(
                agent_id="chimera_oracle",
                agent_name="Chimera Fast Oracle",
                agent_type="oracle",
                role="Fast causal predictions using pre-trained models",
                model_used="CausalForestDML (pre-trained)",
                capabilities=[
                    "Sub-100ms causal effect predictions",
                    "Feature importance ranking",
                    "Confidence interval estimation"
                ],
                limitations=[
                    "Requires pre-training on scenario data",
                    "Cannot handle out-of-distribution queries",
                    "No refutation testing (use full DoWhy for validation)",
                    "Point estimates may not capture uncertainty"
                ]
            ),
        }

    def get_agent_info(self, agent_id: str) -> AgentInfo | None:
        """Get information about a specific agent."""
        return self._agent_registry.get(agent_id)

    def get_all_agents(self) -> list[AgentInfo]:
        """Get information about all registered agents."""
        return list(self._agent_registry.values())

    def create_agent_decision(
        self,
        agent_id: str,
        input_summary: str,
        output_summary: str,
        reasoning: str,
        confidence: float,
        confidence_breakdown: dict[str, float] | None = None,
        alternatives: list[str] | None = None,
        data_sources: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> AgentDecision:
        """Create a transparent agent decision record."""
        agent = self._agent_registry.get(agent_id)
        if not agent:
            agent = AgentInfo(
                agent_id=agent_id,
                agent_name=agent_id,
                agent_type="unknown",
                role="Unknown agent",
            )

        return AgentDecision(
            agent=agent,
            input_summary=input_summary,
            output_summary=output_summary,
            reasoning=reasoning,
            confidence=confidence,
            confidence_breakdown=confidence_breakdown or {},
            alternatives_considered=alternatives or [],
            data_sources_used=data_sources or [],
            assumptions=assumptions or [],
        )

    def assess_data_quality(
        self,
        data: Any,
        dataset_id: str | None = None,
    ) -> DataQualityAssessment:
        """Assess data quality for transparency."""
        try:
            import pandas as pd
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                return DataQualityAssessment(
                    dataset_id=dataset_id,
                    overall_score=0.0,
                    overall_status=DataQualityLevel.UNUSABLE,
                    recommendations=["Provide data as DataFrame, dict, or list"]
                )
        except Exception as e:
            return DataQualityAssessment(
                dataset_id=dataset_id,
                overall_score=0.0,
                overall_status=DataQualityLevel.UNUSABLE,
                recommendations=[f"Data parsing error: {e}"]
            )

        metrics = []
        sample_size = len(df)

        # Completeness
        completeness = 1 - (df.isnull().sum().sum() / (df.shape[0] * df.shape[1]))
        completeness_status = (
            DataQualityLevel.EXCELLENT if completeness > 0.98
            else DataQualityLevel.GOOD if completeness > 0.95
            else DataQualityLevel.FAIR if completeness > 0.85
            else DataQualityLevel.POOR
        )
        metrics.append(DataQualityMetric(
            name="completeness",
            score=completeness,
            status=completeness_status,
            description=f"{completeness:.1%} of values are non-null",
            recommendation="Impute or handle missing values" if completeness < 0.95 else None
        ))

        # Duplicates
        duplicate_pct = df.duplicated().sum() / len(df) if len(df) > 0 else 0
        dup_score = 1 - duplicate_pct
        dup_status = (
            DataQualityLevel.EXCELLENT if duplicate_pct < 0.01
            else DataQualityLevel.GOOD if duplicate_pct < 0.05
            else DataQualityLevel.FAIR if duplicate_pct < 0.10
            else DataQualityLevel.POOR
        )
        metrics.append(DataQualityMetric(
            name="uniqueness",
            score=dup_score,
            status=dup_status,
            description=f"{duplicate_pct:.1%} duplicate rows",
            recommendation="Review and deduplicate data" if duplicate_pct > 0.05 else None
        ))

        # Sample size adequacy
        size_score = min(1.0, sample_size / 500)  # 500 samples = full score
        size_status = (
            DataQualityLevel.EXCELLENT if sample_size >= 1000
            else DataQualityLevel.GOOD if sample_size >= 500
            else DataQualityLevel.FAIR if sample_size >= 100
            else DataQualityLevel.POOR
        )
        metrics.append(DataQualityMetric(
            name="sample_size",
            score=size_score,
            status=size_status,
            description=f"{sample_size} samples",
            recommendation="Collect more data for robust analysis" if sample_size < 500 else None
        ))

        # Overall score
        overall_score = sum(m.score for m in metrics) / len(metrics)
        overall_status = (
            DataQualityLevel.EXCELLENT if overall_score > 0.95
            else DataQualityLevel.GOOD if overall_score > 0.85
            else DataQualityLevel.FAIR if overall_score > 0.70
            else DataQualityLevel.POOR if overall_score > 0.50
            else DataQualityLevel.UNUSABLE
        )

        recommendations = [m.recommendation for m in metrics if m.recommendation]

        return DataQualityAssessment(
            dataset_id=dataset_id,
            overall_score=overall_score,
            overall_status=overall_status,
            metrics=metrics,
            completeness=completeness,
            sample_size=sample_size,
            missing_values_percentage=(1 - completeness) * 100,
            duplicate_percentage=duplicate_pct * 100,
            recommendations=recommendations,
        )

    def assess_reliability(
        self,
        confidence: float,
        data_quality: DataQualityAssessment | None = None,
        refutation_passed: bool | None = None,
        refutation_tests_run: int = 0,
        refutation_tests_passed: int = 0,
        sample_size: int = 0,
        methodology: str = "unknown",
    ) -> ReliabilityAssessment:
        """Assess overall reliability of an analysis."""
        factors = []

        # Model confidence factor
        conf_score = confidence
        factors.append(ReliabilityFactor(
            name="Model Confidence",
            weight=0.30,
            score=conf_score,
            weighted_score=0.30 * conf_score,
            status="good" if conf_score > 0.85 else "medium" if conf_score > 0.70 else "low",
            explanation=f"Analysis confidence: {conf_score:.1%}",
            improvement_actions=(
                ["Provide more context or data"] if conf_score < 0.85 else []
            )
        ))

        # Data quality factor
        dq_score = data_quality.overall_score if data_quality else 0.5
        factors.append(ReliabilityFactor(
            name="Data Quality",
            weight=0.25,
            score=dq_score,
            weighted_score=0.25 * dq_score,
            status="good" if dq_score > 0.85 else "medium" if dq_score > 0.70 else "low",
            explanation=f"Data quality: {dq_score:.1%}",
            improvement_actions=data_quality.recommendations if data_quality else []
        ))

        # Refutation factor (for causal analysis)
        if refutation_tests_run > 0:
            ref_score = refutation_tests_passed / refutation_tests_run
        elif refutation_passed is not None:
            ref_score = 1.0 if refutation_passed else 0.0
        else:
            ref_score = 0.5  # Unknown
        factors.append(ReliabilityFactor(
            name="Refutation Tests",
            weight=0.25,
            score=ref_score,
            weighted_score=0.25 * ref_score,
            status="good" if ref_score > 0.80 else "medium" if ref_score > 0.50 else "low",
            explanation=f"Refutation tests: {refutation_tests_passed}/{refutation_tests_run} passed",
            improvement_actions=(
                ["Review failed refutation tests", "Check for confounders"]
                if ref_score < 0.80 else []
            )
        ))

        # Sample size factor
        size_score = min(1.0, sample_size / 500) if sample_size > 0 else 0.5
        factors.append(ReliabilityFactor(
            name="Sample Size",
            weight=0.20,
            score=size_score,
            weighted_score=0.20 * size_score,
            status="good" if size_score > 0.80 else "medium" if size_score > 0.50 else "low",
            explanation=f"Sample size: {sample_size}",
            improvement_actions=(
                ["Increase sample size for more robust results"]
                if size_score < 0.80 else []
            )
        ))

        # Calculate overall
        overall_score = sum(f.weighted_score for f in factors)
        overall_level = (
            ReliabilityLevel.VERY_HIGH if overall_score > 0.90
            else ReliabilityLevel.HIGH if overall_score > 0.80
            else ReliabilityLevel.MEDIUM if overall_score > 0.65
            else ReliabilityLevel.LOW if overall_score > 0.50
            else ReliabilityLevel.VERY_LOW
        )

        # Generate strengths and weaknesses
        strengths = [f.explanation for f in factors if f.score > 0.80]
        weaknesses = [f.explanation for f in factors if f.score < 0.70]
        suggestions = []
        for f in factors:
            suggestions.extend(f.improvement_actions)

        return ReliabilityAssessment(
            overall_score=overall_score,
            overall_level=overall_level,
            factors=factors,
            data_quality_score=dq_score,
            model_confidence_score=conf_score,
            refutation_score=ref_score,
            sample_size_score=size_score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=list(set(suggestions)),
            methodology_used=methodology,
        )

    def assess_eu_ai_act_compliance(
        self,
        session_id: UUID | None = None,
        has_explanation: bool = True,
        has_audit_trail: bool = True,
        has_human_oversight: bool = True,
        data_governance_score: float = 0.8,
    ) -> EUAIActComplianceReport:
        """Generate EU AI Act compliance report."""
        requirements = []

        # Art. 13 - Transparency
        requirements.append(ComplianceRequirement(
            requirement_id="art13_transparency",
            article="Article 13",
            title="Transparency",
            description="AI systems must be designed to enable users to interpret outputs",
            status=ComplianceStatus.COMPLIANT if has_explanation else ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=[
                "Explanation service provides component explanations",
                "Confidence scores decomposed",
                "Reasoning chain visible in developer view"
            ] if has_explanation else [],
            gaps=[] if has_explanation else ["Need enhanced explanation API"],
            remediation_steps=[] if has_explanation else ["Implement decomposable confidence scores"]
        ))

        # Art. 12 - Record-keeping
        requirements.append(ComplianceRequirement(
            requirement_id="art12_records",
            article="Article 12",
            title="Record-keeping (Audit Trail)",
            description="AI systems must enable logging of events for traceability",
            status=ComplianceStatus.COMPLIANT if has_audit_trail else ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=[
                "Kafka audit trail logs agent decisions",
                "Session IDs track analysis lineage",
                "Reasoning chain preserved in state"
            ] if has_audit_trail else [],
            gaps=[] if has_audit_trail else ["Enable Kafka audit service"],
            remediation_steps=[] if has_audit_trail else ["Configure KAFKA_ENABLED=true"]
        ))

        # Art. 14 - Human Oversight
        requirements.append(ComplianceRequirement(
            requirement_id="art14_oversight",
            article="Article 14",
            title="Human Oversight",
            description="AI systems must allow human oversight and intervention",
            status=ComplianceStatus.COMPLIANT if has_human_oversight else ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=[
                "HumanLayer integration for escalation",
                "Guardian triggers human review on policy violations",
                "Escalation endpoints for manual resolution"
            ] if has_human_oversight else [],
            gaps=[] if has_human_oversight else ["Implement mandatory human review"],
            remediation_steps=[] if has_human_oversight else ["Configure HumanLayer API key"]
        ))

        # Art. 10 - Data Governance
        dg_status = (
            ComplianceStatus.COMPLIANT if data_governance_score > 0.85
            else ComplianceStatus.PARTIALLY_COMPLIANT if data_governance_score > 0.60
            else ComplianceStatus.NON_COMPLIANT
        )
        requirements.append(ComplianceRequirement(
            requirement_id="art10_data",
            article="Article 10",
            title="Data Governance",
            description="Training and test data must meet quality criteria",
            status=dg_status,
            evidence=[
                "Schema detection validates data structure",
                "Data quality assessment available",
                "Recommendations for data improvement"
            ],
            gaps=["Automated bias detection not implemented"] if data_governance_score < 0.85 else [],
            remediation_steps=["Add fairness metrics", "Implement bias detection"] if data_governance_score < 0.85 else []
        ))

        # Calculate scores
        transparency_score = 0.9 if has_explanation else 0.6
        documentation_score = 0.85  # Docs exist
        human_oversight_score = 0.95 if has_human_oversight else 0.5
        risk_management_score = 0.8  # Guardian provides risk assessment

        compliant_count = sum(1 for r in requirements if r.status == ComplianceStatus.COMPLIANT)
        compliance_score = compliant_count / len(requirements)

        overall_status = (
            ComplianceStatus.COMPLIANT if compliance_score > 0.90
            else ComplianceStatus.PARTIALLY_COMPLIANT if compliance_score > 0.60
            else ComplianceStatus.NON_COMPLIANT
        )

        priority_actions = []
        for r in requirements:
            priority_actions.extend(r.remediation_steps)

        return EUAIActComplianceReport(
            overall_status=overall_status,
            compliance_score=compliance_score,
            requirements=requirements,
            transparency_score=transparency_score,
            documentation_score=documentation_score,
            human_oversight_score=human_oversight_score,
            risk_management_score=risk_management_score,
            data_governance_score=data_governance_score,
            priority_actions=list(set(priority_actions)),
        )

    def evaluate_workflow(
        self,
        workflow_name: str,
        use_case: str,
        data_types: list[str],
        models_used: list[str],
        has_validation: bool = False,
        has_human_review: bool = False,
        sample_size: int = 0,
        domain: str = "Complicated",
    ) -> WorkflowEvaluation:
        """Evaluate a workflow's feasibility, reliability, and transparency."""
        criteria = []

        # Data appropriateness
        data_score = 0.7
        if "csv" in data_types or "tabular" in data_types:
            data_score = 0.9
        if sample_size > 500:
            data_score = min(1.0, data_score + 0.1)
        criteria.append(WorkflowEvaluationCriteria(
            criterion="Data Appropriateness",
            weight=0.25,
            score=data_score,
            explanation=f"Data types: {data_types}, sample size: {sample_size}",
            improvement_potential="Ensure tabular data with sufficient samples" if data_score < 0.8 else None
        ))

        # Model suitability
        model_score = 0.8
        if "DoWhy" in models_used or "causal" in str(models_used).lower():
            model_score = 0.9 if domain == "Complicated" else 0.7
        if "PyMC" in models_used or "bayesian" in str(models_used).lower():
            model_score = 0.9 if domain == "Complex" else 0.7
        criteria.append(WorkflowEvaluationCriteria(
            criterion="Model Suitability",
            weight=0.25,
            score=model_score,
            explanation=f"Models: {models_used} for domain: {domain}",
            improvement_potential="Match model to Cynefin domain" if model_score < 0.8 else None
        ))

        # Validation rigor
        val_score = 0.9 if has_validation else 0.5
        criteria.append(WorkflowEvaluationCriteria(
            criterion="Validation Rigor",
            weight=0.25,
            score=val_score,
            explanation="Refutation tests included" if has_validation else "No validation tests",
            improvement_potential="Add refutation tests" if not has_validation else None
        ))

        # Human oversight
        oversight_score = 0.95 if has_human_review else 0.6
        criteria.append(WorkflowEvaluationCriteria(
            criterion="Human Oversight",
            weight=0.25,
            score=oversight_score,
            explanation="Human review enabled" if has_human_review else "Automated only",
            improvement_potential="Enable human review for critical decisions" if not has_human_review else None
        ))

        # Calculate scores
        feasibility_score = sum(c.score * c.weight for c in criteria)
        reliability_score = (data_score * 0.4 + model_score * 0.3 + val_score * 0.3)
        transparency_score = 0.85  # CARF provides transparency by default
        overall_score = (feasibility_score + reliability_score + transparency_score) / 3

        # EU AI Act alignment
        eu_alignment = (transparency_score + oversight_score + val_score) / 3

        strengths = [c.explanation for c in criteria if c.score > 0.8]
        weaknesses = [c.explanation for c in criteria if c.score < 0.7]
        recommendations = [c.improvement_potential for c in criteria if c.improvement_potential]

        compliance_gaps = []
        if not has_human_review:
            compliance_gaps.append("Art. 14 Human Oversight: Enable human review")
        if not has_validation:
            compliance_gaps.append("Art. 10 Data Quality: Add validation tests")

        return WorkflowEvaluation(
            workflow_name=workflow_name,
            use_case=use_case,
            data_types=data_types,
            models_used=models_used,
            feasibility_score=feasibility_score,
            reliability_score=reliability_score,
            transparency_score=transparency_score,
            overall_score=overall_score,
            criteria=criteria,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            eu_ai_act_alignment=eu_alignment,
            compliance_gaps=compliance_gaps,
        )

    def get_guardian_transparency(
        self,
        session_id: UUID,
        verdict: str,
        policies_passed: list[str],
        policies_violated: list[str],
    ) -> GuardianTransparencyReport:
        """Generate Guardian transparency report."""
        # Define standard policies
        policy_definitions = [
            PolicyDefinition(
                policy_id="financial_limit",
                name="Financial Auto-Approval Limit",
                category="financial",
                description="Maximum amount for automatic approval",
                rationale="Prevents unauthorized high-value transactions",
                threshold_value=100000,
                threshold_unit="USD",
                severity="high",
                user_configurable=True,
                configuration_range={"min": 1000, "max": 1000000}
            ),
            PolicyDefinition(
                policy_id="confidence_threshold",
                name="Confidence Threshold",
                category="risk",
                description="Minimum confidence required for automated decisions",
                rationale="Ensures decisions have sufficient certainty",
                threshold_value=0.85,
                threshold_unit="probability",
                severity="medium",
                user_configurable=True,
                configuration_range={"min": 0.5, "max": 0.99}
            ),
            PolicyDefinition(
                policy_id="max_reflections",
                name="Maximum Reflection Attempts",
                category="operational",
                description="Maximum self-correction loops before escalation",
                rationale="Prevents infinite loops and ensures human review",
                threshold_value=2,
                threshold_unit="count",
                severity="medium",
                user_configurable=True,
                configuration_range={"min": 1, "max": 5}
            ),
            PolicyDefinition(
                policy_id="always_escalate",
                name="Mandatory Escalation Actions",
                category="escalation",
                description="Actions that always require human approval",
                rationale="High-impact actions need human oversight",
                threshold_value=["delete_data", "modify_policy", "production_deployment"],
                severity="critical",
                user_configurable=False
            ),
        ]

        return GuardianTransparencyReport(
            session_id=session_id,
            verdict=verdict,
            policies_evaluated=policy_definitions,
            policies_passed=policies_passed,
            policies_violated=policies_violated,
            risk_breakdown={
                "financial_risk": 0.2 if "financial" not in str(policies_violated) else 0.8,
                "operational_risk": 0.3 if "operational" not in str(policies_violated) else 0.7,
                "confidence_risk": 0.2 if "confidence" not in str(policies_violated) else 0.6,
            },
            escalation_reason=(
                f"Policy violations: {policies_violated}" if policies_violated else None
            ),
            user_override_available=bool(policies_violated),
            override_requirements=(
                ["Provide justification", "Manager approval required"]
                if policies_violated else []
            ),
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_transparency_service: TransparencyService | None = None


def get_transparency_service() -> TransparencyService:
    """Get singleton TransparencyService instance."""
    global _transparency_service
    if _transparency_service is None:
        _transparency_service = TransparencyService()
    return _transparency_service
