"""Governance data models for CARF Orchestration Governance (OG).

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

This module defines all Pydantic models for the OG subsystem implementing
the MAP-PRICE-RESOLVE framework. No imports from state.py to avoid circular deps.

MAP   - Semantic triple knowledge graph for cross-domain impact tracing
PRICE - Cost intelligence with actual LLM token tracking
RESOLVE - Federated policy conflict detection and resolution
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvidenceType(str, Enum):
    """How a semantic triple was derived."""
    LLM_EXTRACTED = "llm_extracted"
    RULE_BASED = "rule_based"
    USER_DEFINED = "user_defined"
    POLICY_DERIVED = "policy_derived"


class ConflictType(str, Enum):
    """Types of cross-domain policy conflicts."""
    CONTRADICTORY = "contradictory"       # Rules directly oppose each other
    OVERLAPPING = "overlapping"           # Rules apply to same context with different outcomes
    RESOURCE_CONTENTION = "resource_contention"  # Rules compete for same resource
    PRIORITY_AMBIGUITY = "priority_ambiguity"    # Unclear which rule takes precedence


class ConflictSeverity(str, Enum):
    """Severity of a policy conflict."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceFramework(str, Enum):
    """Supported regulatory compliance frameworks."""
    EU_AI_ACT = "eu_ai_act"
    CSRD = "csrd"
    GDPR = "gdpr"
    ISO_27001 = "iso_27001"


class GovernanceEventType(str, Enum):
    """Types of governance audit events."""
    TRIPLE_CREATED = "triple_created"
    TRIPLE_UPDATED = "triple_updated"
    POLICY_REGISTERED = "policy_registered"
    POLICY_UPDATED = "policy_updated"
    POLICY_DEACTIVATED = "policy_deactivated"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    COMPLIANCE_ASSESSED = "compliance_assessed"
    DOMAIN_CREATED = "domain_created"
    COST_COMPUTED = "cost_computed"
    GOVERNANCE_NODE_EXECUTED = "governance_node_executed"
    BOARD_CREATED = "board_created"
    BOARD_UPDATED = "board_updated"
    BOARD_DELETED = "board_deleted"
    POLICY_EXTRACTED = "policy_extracted"
    SPEC_EXPORTED = "spec_exported"


# ---------------------------------------------------------------------------
# MAP Models — Semantic Triple Knowledge Graph
# ---------------------------------------------------------------------------

class ContextTriple(BaseModel):
    """A semantic triple representing cross-domain impact.

    subject --[predicate]--> object
    e.g. "procurement_spend" --[increases]--> "carbon_footprint"
    """
    triple_id: UUID = Field(default_factory=uuid4)
    subject: str = Field(..., description="Entity or concept (source)")
    predicate: str = Field(..., description="Relationship type")
    object: str = Field(..., description="Entity or concept (target)")
    domain_source: str = Field(..., description="Originating governance domain")
    domain_target: str = Field(..., description="Impacted governance domain")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in this triple")
    evidence_type: EvidenceType = Field(default=EvidenceType.LLM_EXTRACTED)
    session_id: Optional[str] = Field(default=None, description="Session that produced this triple")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GovernanceDomain(BaseModel):
    """An enterprise governance domain (silo)."""
    domain_id: str = Field(..., description="Unique domain identifier (e.g. 'procurement')")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Domain description")
    owner_email: str = Field(default="", description="Domain owner contact")
    policy_namespace: str = Field(default="", description="Namespace for policies")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    color: str = Field(default="#6B7280", description="UI color for visualization")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImpactPath(BaseModel):
    """A path of cross-domain impacts between two domains."""
    source_domain: str
    target_domain: str
    path: list[ContextTriple] = Field(default_factory=list)
    total_confidence: float = Field(default=0.0)
    hop_count: int = Field(default=0)


# ---------------------------------------------------------------------------
# PRICE Models — Cost Intelligence
# ---------------------------------------------------------------------------

class CostBreakdownItem(BaseModel):
    """A single line item in a cost breakdown."""
    category: str = Field(..., description="Cost category (llm, compute, risk, opportunity)")
    label: str = Field(..., description="Human-readable label")
    amount: float = Field(default=0.0, description="Cost in USD")
    unit: str = Field(default="USD", description="Currency unit")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")


class CostBreakdown(BaseModel):
    """Full cost breakdown for a query or session."""
    session_id: Optional[str] = Field(default=None)
    llm_token_cost: float = Field(default=0.0, description="LLM API token cost in USD")
    llm_tokens_used: int = Field(default=0, description="Total tokens consumed")
    llm_input_tokens: int = Field(default=0, description="Input/prompt tokens")
    llm_output_tokens: int = Field(default=0, description="Output/completion tokens")
    llm_provider: str = Field(default="", description="LLM provider used")
    compute_time_ms: float = Field(default=0.0, description="Total compute time")
    risk_exposure_score: float = Field(default=0.0, description="Financial risk exposure")
    opportunity_cost: float = Field(default=0.0, description="Cost of human time saved/spent")
    total_cost: float = Field(default=0.0, description="Total all-in cost")
    breakdown_items: list[CostBreakdownItem] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class CostAggregate(BaseModel):
    """Aggregated cost metrics across multiple sessions."""
    total_sessions: int = Field(default=0)
    total_cost: float = Field(default=0.0)
    average_cost_per_query: float = Field(default=0.0)
    total_tokens: int = Field(default=0)
    cost_by_category: dict[str, float] = Field(default_factory=dict)
    cost_by_provider: dict[str, float] = Field(default_factory=dict)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ROIMetrics(BaseModel):
    """Return on Investment metrics for AI-assisted decisions."""
    ai_analysis_cost: float = Field(default=0.0, description="Cost of AI analysis")
    manual_analysis_estimate: float = Field(default=0.0, description="Estimated manual analysis cost")
    time_saved_hours: float = Field(default=0.0, description="Hours saved vs manual")
    roi_percentage: float = Field(default=0.0, description="ROI = (manual - ai) / ai * 100")
    insights_generated: int = Field(default=0)
    decisions_supported: int = Field(default=0)


# ---------------------------------------------------------------------------
# RESOLVE Models — Federated Policy Conflict Detection
# ---------------------------------------------------------------------------

class FederatedPolicyRule(BaseModel):
    """A single rule within a federated policy."""
    rule_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    condition: dict[str, Any] = Field(default_factory=dict)
    constraint: dict[str, Any] = Field(default_factory=dict)
    message: str = Field(default="")
    severity: ConflictSeverity = Field(default=ConflictSeverity.MEDIUM)


class FederatedPolicy(BaseModel):
    """A domain-owner contributed policy for federated governance."""
    policy_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Policy name")
    domain_id: str = Field(..., description="Owning domain")
    namespace: str = Field(..., description="Policy namespace (e.g. 'procurement.spend')")
    description: str = Field(default="")
    rules: list[FederatedPolicyRule] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100, description="Priority (0=lowest, 100=highest)")
    is_active: bool = Field(default=True)
    version: str = Field(default="1.0")
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyConflict(BaseModel):
    """A detected conflict between two federated policies."""
    conflict_id: UUID = Field(default_factory=uuid4)
    policy_a_id: str = Field(..., description="First policy ID")
    policy_a_name: str = Field(default="")
    policy_a_domain: str = Field(default="")
    policy_b_id: str = Field(..., description="Second policy ID")
    policy_b_name: str = Field(default="")
    policy_b_domain: str = Field(default="")
    conflict_type: ConflictType = Field(default=ConflictType.OVERLAPPING)
    severity: ConflictSeverity = Field(default=ConflictSeverity.MEDIUM)
    description: str = Field(default="", description="Human-readable conflict description")
    resolution: Optional[str] = Field(default=None, description="Resolution if resolved")
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by: Optional[str] = Field(default=None)
    detected_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Audit & Compliance Models
# ---------------------------------------------------------------------------

class GovernanceAuditEntry(BaseModel):
    """An entry in the governance audit timeline."""
    entry_id: UUID = Field(default_factory=uuid4)
    event_type: GovernanceEventType
    actor: str = Field(default="system", description="Who/what triggered this event")
    affected_domains: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComplianceArticle(BaseModel):
    """Assessment of a single compliance article/requirement."""
    article_id: str = Field(..., description="Article identifier (e.g. 'Art.9')")
    title: str = Field(default="")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Compliance score 0-1")
    status: str = Field(default="unknown", description="compliant/partial/non_compliant/unknown")
    evidence: list[str] = Field(default_factory=list, description="Evidence supporting score")
    gaps: list[str] = Field(default_factory=list, description="Identified gaps")


class ComplianceScore(BaseModel):
    """Regulatory compliance assessment for a specific framework."""
    framework: ComplianceFramework
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    articles: list[ComplianceArticle] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="All identified gaps")
    recommendations: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Board Models — Governance Board Abstraction
# ---------------------------------------------------------------------------

class BoardMember(BaseModel):
    """A member of a governance board."""
    user_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    email: str = Field(default="")
    role: str = Field(default="member", description="owner/approver/member/observer")


class ComplianceFrameworkConfig(BaseModel):
    """Configuration for a compliance framework within a board."""
    framework: ComplianceFramework
    enabled: bool = Field(default=True)
    target_score: float = Field(default=0.8, ge=0.0, le=1.0)
    custom_articles: list[ComplianceArticle] = Field(default_factory=list)
    custom_weights: dict[str, float] = Field(default_factory=dict)


class GovernanceBoard(BaseModel):
    """A governance board grouping domains, policies, and compliance configs."""
    board_id: str = Field(default_factory=lambda: str(uuid4())[:12])
    name: str
    description: str = Field(default="")
    template_id: Optional[str] = Field(default=None)
    domain_ids: list[str] = Field(default_factory=list)
    policy_namespaces: list[str] = Field(default_factory=list)
    compliance_configs: list[ComplianceFrameworkConfig] = Field(default_factory=list)
    members: list[BoardMember] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Governance Health
# ---------------------------------------------------------------------------

class GovernanceHealth(BaseModel):
    """Health status of the governance subsystem."""
    enabled: bool = Field(default=False)
    neo4j_available: bool = Field(default=False)
    domains_count: int = Field(default=0)
    policies_count: int = Field(default=0)
    active_conflicts: int = Field(default=0)
    triples_count: int = Field(default=0)
    status: str = Field(default="disabled")
