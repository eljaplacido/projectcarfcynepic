"""Governance API Router for CARF Orchestration Governance.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

All endpoints under /governance/ prefix. Only registered when GOVERNANCE_ENABLED=true.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from tenacity import RetryError

from src.core.governance_models import (
    ComplianceFramework,
    ComplianceScore,
    ContextTriple,
    CostBreakdown,
    FederatedPolicy,
    GovernanceBoard,
    GovernanceDomain,
    GovernanceHealth,
    PolicyConflict,
)
from src.utils.resiliency import retry_with_backoff

logger = logging.getLogger("carf.api.governance")

router = APIRouter(prefix="/governance", tags=["governance"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class DomainCreateRequest(BaseModel):
    domain_id: str
    display_name: str
    description: str = ""
    owner_email: str = ""
    policy_namespace: str = ""
    tags: list[str] = Field(default_factory=list)
    color: str = "#6B7280"


class DomainUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    owner_email: Optional[str] = None
    tags: Optional[list[str]] = None


class PolicyCreateRequest(BaseModel):
    name: str
    domain_id: str
    namespace: str
    description: str = ""
    rules: list[dict[str, Any]] = Field(default_factory=list)
    priority: int = 50
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)


class PolicyUpdateRequest(BaseModel):
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    tags: Optional[list[str]] = None


class TripleCreateRequest(BaseModel):
    subject: str
    predicate: str
    object: str
    domain_source: str
    domain_target: str
    confidence: float = 0.8
    session_id: Optional[str] = None


class ConflictResolveRequest(BaseModel):
    resolution: str
    resolved_by: str = "user"


class PricingUpdateRequest(BaseModel):
    provider: str
    input_price: float
    output_price: float


class BoardCreateRequest(BaseModel):
    name: str
    description: str = ""
    domain_ids: list[str] = Field(default_factory=list)
    policy_namespaces: list[str] = Field(default_factory=list)
    compliance_configs: list[dict[str, Any]] = Field(default_factory=list)
    members: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True


class BoardUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain_ids: Optional[list[str]] = None
    policy_namespaces: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


class BoardFromTemplateRequest(BaseModel):
    template_id: str
    name: Optional[str] = None


class SpecExportRequest(BaseModel):
    board_id: str
    format: str = Field(default="json_ld", description="json_ld, yaml, or csl")


class PolicyTextExtractionRequest(BaseModel):
    text: str
    source_name: str = "pasted_text"
    target_domain: Optional[str] = None


class ExtractedPolicyRule(BaseModel):
    """Structured policy rule extracted from free-form governance text."""

    name: str
    condition: dict[str, Any] = Field(default_factory=dict)
    constraint: dict[str, Any] = Field(default_factory=dict)
    message: str
    severity: str
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    rationale: str = ""
    evidence: list[str] = Field(default_factory=list)


class PolicyTextExtractionResponse(BaseModel):
    """Response payload for policy extraction endpoint."""

    source_name: str
    target_domain: Optional[str] = None
    rules_extracted: int
    rules: list[ExtractedPolicyRule] = Field(default_factory=list)
    methodology: str = "llm_structured_extraction_v1"
    extraction_confidence_avg: float = Field(default=0.0, ge=0.0, le=1.0)
    explainability: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class SemanticGraphNode(BaseModel):
    """Node in governance semantic graph."""

    node_id: str
    label: str
    node_type: str = Field(..., description="domain|policy|concept")
    domain_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticGraphEdge(BaseModel):
    """Edge in governance semantic graph."""

    edge_id: str
    source: str
    target: str
    relation: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticGraphResponse(BaseModel):
    """Response payload for governance semantic graph visualization."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    board_id: Optional[str] = None
    session_id: Optional[str] = None
    nodes: list[SemanticGraphNode] = Field(default_factory=list)
    edges: list[SemanticGraphEdge] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    explainability: dict[str, Any] = Field(default_factory=dict)


def _semantic_key(value: str) -> str:
    """Create a stable semantic key for graph node IDs."""
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "unknown"


def _strip_markdown_fences(content: str) -> str:
    """Remove code fences and keep raw JSON if fenced output is returned."""
    payload = content.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        if len(lines) >= 2:
            payload = "\n".join(lines[1:])
        if payload.endswith("```"):
            payload = payload[:-3]
    return payload.strip()


def _extract_json_fragment(content: str) -> str:
    """Extract first JSON object/array fragment from a model response."""
    cleaned = _strip_markdown_fences(content)
    if cleaned.startswith("[") or cleaned.startswith("{"):
        return cleaned

    first_array = cleaned.find("[")
    first_obj = cleaned.find("{")
    starts = [idx for idx in (first_array, first_obj) if idx >= 0]
    if not starts:
        return cleaned
    start = min(starts)

    last_array = cleaned.rfind("]")
    last_obj = cleaned.rfind("}")
    end = max(last_array, last_obj)
    if end < start:
        return cleaned
    return cleaned[start : end + 1]


@retry_with_backoff(max_attempts=3, min_wait=1.0, max_wait=8.0, exceptions=(Exception,))
def _invoke_extraction_model(prompt: str) -> str:
    """Invoke extraction LLM with retry/backoff for transient provider failures."""
    from src.core.llm import get_chat_model

    llm = get_chat_model(purpose="governance_extraction")
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


# ---------------------------------------------------------------------------
# Domain Endpoints
# ---------------------------------------------------------------------------

@router.get("/domains", response_model=list[GovernanceDomain])
async def list_domains():
    """List all governance domains."""
    from src.services.federated_policy_service import get_federated_service
    return get_federated_service().list_domains()


@router.post("/domains", response_model=GovernanceDomain, status_code=201)
async def create_domain(req: DomainCreateRequest):
    """Create a new governance domain."""
    from src.services.federated_policy_service import get_federated_service
    domain = GovernanceDomain(**req.model_dump())
    return get_federated_service().register_domain(domain)


@router.get("/domains/{domain_id}", response_model=GovernanceDomain)
async def get_domain(domain_id: str):
    """Get a specific governance domain."""
    from src.services.federated_policy_service import get_federated_service
    domain = get_federated_service().get_domain(domain_id)
    if domain is None:
        raise HTTPException(404, f"Domain '{domain_id}' not found")
    return domain


@router.put("/domains/{domain_id}", response_model=GovernanceDomain)
async def update_domain(domain_id: str, req: DomainUpdateRequest):
    """Update a governance domain."""
    from src.services.federated_policy_service import get_federated_service
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    domain = get_federated_service().update_domain(domain_id, updates)
    if domain is None:
        raise HTTPException(404, f"Domain '{domain_id}' not found")
    return domain


# ---------------------------------------------------------------------------
# Triple Endpoints
# ---------------------------------------------------------------------------

@router.get("/triples")
async def list_triples(session_id: Optional[str] = None, limit: int = 100):
    """List context triples, optionally filtered by session."""
    from src.services.governance_graph_service import get_governance_graph_service
    graph = get_governance_graph_service()
    if graph.is_available:
        return await graph.get_all_triples(session_id=session_id, limit=limit)
    return []


@router.post("/triples", response_model=ContextTriple, status_code=201)
async def create_triple(req: TripleCreateRequest):
    """Create a new context triple."""
    from src.services.governance_graph_service import get_governance_graph_service
    from src.core.governance_models import EvidenceType
    triple = ContextTriple(
        subject=req.subject,
        predicate=req.predicate,
        object=req.object,
        domain_source=req.domain_source,
        domain_target=req.domain_target,
        confidence=req.confidence,
        evidence_type=EvidenceType.USER_DEFINED,
        session_id=req.session_id,
    )
    graph = get_governance_graph_service()
    if graph.is_available:
        await graph.save_triple(triple)
    return triple


@router.get("/triples/impact/{domain_id}")
async def get_impact_graph(domain_id: str):
    """Get cross-domain impact graph for a domain."""
    from src.services.governance_graph_service import get_governance_graph_service
    graph = get_governance_graph_service()
    if graph.is_available:
        return await graph.find_cross_domain_impacts(domain_id)
    # Fallback: return static domain graph
    from src.services.governance_service import get_governance_service
    return get_governance_service().get_impact_graph(domain_id)


@router.get("/triples/path/{source}/{target}")
async def get_impact_path(source: str, target: str):
    """Get impact path between two domains."""
    from src.services.governance_graph_service import get_governance_graph_service
    graph = get_governance_graph_service()
    if graph.is_available:
        return await graph.get_impact_path(source, target)
    return []


@router.get("/semantic-graph", response_model=SemanticGraphResponse)
async def get_semantic_graph(
    board_id: Optional[str] = None,
    session_id: Optional[str] = None,
    unresolved_only: bool = True,
    triple_limit: int = 80,
):
    """Return a purpose-built governance semantic graph for visualization."""
    try:
        return await _build_semantic_graph(board_id, session_id, unresolved_only, triple_limit)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Semantic graph generation failed, returning empty graph: %s", exc)
        return SemanticGraphResponse(
            board_id=board_id,
            session_id=session_id,
            nodes=[],
            edges=[],
            stats={"error": str(exc), "domains": 0, "policies": 0, "concepts": 0},
            explainability={
                "why_this": "Graph generation failed; returning empty graph as fallback.",
                "how_confident": 0.0,
                "based_on": [f"error:{type(exc).__name__}"],
            },
        )


async def _build_semantic_graph(
    board_id: Optional[str],
    session_id: Optional[str],
    unresolved_only: bool,
    triple_limit: int,
) -> SemanticGraphResponse:
    """Internal builder for the semantic graph — extracted for error isolation."""
    from src.services.federated_policy_service import get_federated_service
    from src.services.governance_graph_service import get_governance_graph_service

    scope_note = "all governance domains"
    federated = get_federated_service()
    domains = federated.list_domains()
    policies = federated.list_policies()
    conflicts = (
        federated.get_unresolved_conflicts()
        if unresolved_only
        else federated.get_all_conflicts()
    )

    scoped_domain_ids = {domain.domain_id for domain in domains}

    if board_id:
        from src.services.governance_board_service import get_board_service

        board = get_board_service().get_board(board_id)
        if board is None:
            raise HTTPException(404, f"Board '{board_id}' not found")

        if board.domain_ids:
            scoped_domain_ids = set(board.domain_ids)
            domains = [domain for domain in domains if domain.domain_id in scoped_domain_ids]
            policies = [
                policy for policy in policies
                if policy.domain_id in scoped_domain_ids
            ]
        if board.policy_namespaces:
            board_namespaces = set(board.policy_namespaces)
            policies = [
                policy for policy in policies
                if policy.namespace in board_namespaces
            ]

        conflicts = [
            conflict
            for conflict in conflicts
            if (
                conflict.policy_a_domain in scoped_domain_ids
                or conflict.policy_b_domain in scoped_domain_ids
            )
        ]
        scope_note = f"governance board {board_id}"

    graph_service = get_governance_graph_service()
    triples: list[dict[str, Any]] = []
    limit = max(1, min(triple_limit, 500))
    if graph_service.is_available:
        triples = await graph_service.get_all_triples(session_id=session_id, limit=limit)

    if scoped_domain_ids:
        triples = [
            triple
            for triple in triples
            if (
                str(triple.get("domain_source", "")) in scoped_domain_ids
                or str(triple.get("domain_target", "")) in scoped_domain_ids
            )
        ]

    node_map: dict[str, SemanticGraphNode] = {}
    edges: list[SemanticGraphEdge] = []
    edge_counter = 0

    def add_node(node: SemanticGraphNode) -> None:
        node_map.setdefault(node.node_id, node)

    def add_edge(
        source: str,
        target: str,
        relation: str,
        confidence: float = 1.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        nonlocal edge_counter
        edge_counter += 1
        edges.append(
            SemanticGraphEdge(
                edge_id=f"e_{edge_counter}",
                source=source,
                target=target,
                relation=relation,
                confidence=max(0.0, min(float(confidence), 1.0)),
                metadata=metadata or {},
            )
        )

    for domain in domains:
        add_node(
            SemanticGraphNode(
                node_id=f"domain:{domain.domain_id}",
                label=domain.display_name,
                node_type="domain",
                domain_id=domain.domain_id,
                metadata={
                    "owner_email": domain.owner_email,
                    "tags": domain.tags,
                    "color": domain.color,
                },
            )
        )

    policy_id_to_node: dict[str, str] = {}
    for policy in policies:
        policy_node_id = f"policy:{_semantic_key(policy.namespace)}"
        policy_id_to_node[str(policy.policy_id)] = policy_node_id
        add_node(
            SemanticGraphNode(
                node_id=policy_node_id,
                label=policy.name,
                node_type="policy",
                domain_id=policy.domain_id,
                metadata={
                    "namespace": policy.namespace,
                    "priority": policy.priority,
                    "active": policy.is_active,
                    "rule_count": len(policy.rules),
                },
            )
        )
        domain_node_id = f"domain:{policy.domain_id}"
        if domain_node_id in node_map:
            add_edge(
                source=domain_node_id,
                target=policy_node_id,
                relation="owns_policy",
                confidence=1.0,
                metadata={"namespace": policy.namespace},
            )

    severity_confidence = {
        "critical": 1.0,
        "high": 0.9,
        "medium": 0.75,
        "low": 0.6,
    }
    for conflict in conflicts:
        severity = conflict.severity.value if hasattr(conflict.severity, "value") else str(conflict.severity)
        conflict_type = (
            conflict.conflict_type.value if hasattr(conflict.conflict_type, "value") else str(conflict.conflict_type)
        )
        source = policy_id_to_node.get(
            str(conflict.policy_a_id), f"policy:{_semantic_key(conflict.policy_a_name or conflict.policy_a_id)}"
        )
        target = policy_id_to_node.get(
            str(conflict.policy_b_id), f"policy:{_semantic_key(conflict.policy_b_name or conflict.policy_b_id)}"
        )
        if source not in node_map:
            add_node(
                SemanticGraphNode(
                    node_id=source,
                    label=conflict.policy_a_name or str(conflict.policy_a_id),
                    node_type="policy",
                    domain_id=conflict.policy_a_domain,
                    metadata={"inferred_from_conflict": True},
                )
            )
        if target not in node_map:
            add_node(
                SemanticGraphNode(
                    node_id=target,
                    label=conflict.policy_b_name or str(conflict.policy_b_id),
                    node_type="policy",
                    domain_id=conflict.policy_b_domain,
                    metadata={"inferred_from_conflict": True},
                )
            )
        add_edge(
            source=source,
            target=target,
            relation="conflicts_with",
            confidence=severity_confidence.get(severity, 0.7),
            metadata={
                "severity": severity,
                "conflict_type": conflict_type,
                "description": conflict.description,
                "resolved": conflict.resolution is not None,
            },
        )

    for triple in triples:
        subject = str(triple.get("subject", "")).strip()
        obj = str(triple.get("object", "")).strip()
        predicate = str(triple.get("predicate", "related_to")).strip() or "related_to"
        source_domain = str(triple.get("domain_source", "")).strip()
        target_domain = str(triple.get("domain_target", "")).strip()
        confidence = float(triple.get("confidence", 0.6) or 0.6)
        triple_id = str(triple.get("triple_id", f"{source_domain}_{predicate}_{target_domain}"))

        if not subject or not obj:
            continue
        if scoped_domain_ids and source_domain and source_domain not in scoped_domain_ids and target_domain not in scoped_domain_ids:
            continue

        subject_node = f"concept:{_semantic_key(subject)}"
        object_node = f"concept:{_semantic_key(obj)}"
        add_node(
            SemanticGraphNode(
                node_id=subject_node,
                label=subject,
                node_type="concept",
                metadata={"role": "subject"},
            )
        )
        add_node(
            SemanticGraphNode(
                node_id=object_node,
                label=obj,
                node_type="concept",
                metadata={"role": "object"},
            )
        )

        if source_domain and f"domain:{source_domain}" in node_map:
            add_edge(
                source=f"domain:{source_domain}",
                target=subject_node,
                relation="domain_mentions",
                confidence=min(confidence + 0.1, 1.0),
                metadata={"triple_id": triple_id},
            )
        add_edge(
            source=subject_node,
            target=object_node,
            relation=predicate,
            confidence=confidence,
            metadata={
                "triple_id": triple_id,
                "domain_source": source_domain,
                "domain_target": target_domain,
            },
        )
        if target_domain and f"domain:{target_domain}" in node_map:
            add_edge(
                source=object_node,
                target=f"domain:{target_domain}",
                relation="impacts_domain",
                confidence=min(confidence + 0.1, 1.0),
                metadata={"triple_id": triple_id},
            )

    avg_confidence = (
        round(sum(edge.confidence for edge in edges) / max(len(edges), 1), 3)
        if edges
        else 0.0
    )
    explainability = {
        "why_this": (
            "This graph combines MAP semantic triples, policy ownership, and RESOLVE conflicts "
            "to make governance interactions explicit."
        ),
        "how_confident": avg_confidence,
        "based_on": [
            f"scope:{scope_note}",
            f"domains:{len([n for n in node_map.values() if n.node_type == 'domain'])}",
            f"policies:{len([n for n in node_map.values() if n.node_type == 'policy'])}",
            f"triples:{len(triples)}",
            f"conflicts:{len(conflicts)}",
            f"graph_backend:{'neo4j' if graph_service.is_available else 'degraded_in_memory'}",
        ],
    }

    return SemanticGraphResponse(
        board_id=board_id,
        session_id=session_id,
        nodes=list(node_map.values()),
        edges=edges,
        stats={
            "domains": len([n for n in node_map.values() if n.node_type == "domain"]),
            "policies": len([n for n in node_map.values() if n.node_type == "policy"]),
            "concepts": len([n for n in node_map.values() if n.node_type == "concept"]),
            "triples_loaded": len(triples),
            "conflicts_loaded": len(conflicts),
            "edge_count": len(edges),
        },
        explainability=explainability,
    )


# ---------------------------------------------------------------------------
# Policy Endpoints
# ---------------------------------------------------------------------------

@router.get("/policies", response_model=list[FederatedPolicy])
async def list_policies(domain_id: Optional[str] = None):
    """List federated policies, optionally filtered by domain."""
    from src.services.federated_policy_service import get_federated_service
    return get_federated_service().list_policies(domain_id=domain_id)


@router.post("/policies", response_model=FederatedPolicy, status_code=201)
async def create_policy(req: PolicyCreateRequest):
    """Register a new federated policy."""
    from src.services.federated_policy_service import get_federated_service
    from src.core.governance_models import FederatedPolicyRule
    rules = [FederatedPolicyRule(**r) for r in req.rules]
    policy = FederatedPolicy(
        name=req.name,
        domain_id=req.domain_id,
        namespace=req.namespace,
        description=req.description,
        rules=rules,
        priority=req.priority,
        is_active=req.is_active,
        tags=req.tags,
    )
    result = get_federated_service().add_policy(policy)
    # Incremental RAG re-ingestion (non-blocking)
    try:
        from src.services.rag_service import get_rag_service
        get_rag_service().ingest_policies()
    except Exception:
        pass
    return result


@router.get("/policies/{namespace}")
async def get_policy(namespace: str):
    """Get a specific policy by namespace."""
    from src.services.federated_policy_service import get_federated_service
    policy = get_federated_service().get_policy(namespace)
    if policy is None:
        raise HTTPException(404, f"Policy '{namespace}' not found")
    return policy


@router.put("/policies/{namespace}")
async def update_policy(namespace: str, req: PolicyUpdateRequest):
    """Update a federated policy."""
    from src.services.federated_policy_service import get_federated_service
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    policy = get_federated_service().update_policy(namespace, updates)
    if policy is None:
        raise HTTPException(404, f"Policy '{namespace}' not found")
    # Incremental RAG re-ingestion (non-blocking)
    try:
        from src.services.rag_service import get_rag_service
        get_rag_service().ingest_policies()
    except Exception:
        pass
    return policy


@router.delete("/policies/{namespace}", status_code=204)
async def delete_policy(namespace: str):
    """Remove a federated policy."""
    from src.services.federated_policy_service import get_federated_service
    if not get_federated_service().remove_policy(namespace):
        raise HTTPException(404, f"Policy '{namespace}' not found")
    # Incremental RAG re-ingestion (non-blocking)
    try:
        from src.services.rag_service import get_rag_service
        get_rag_service().ingest_policies()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Conflict Endpoints
# ---------------------------------------------------------------------------

@router.get("/conflicts", response_model=list[PolicyConflict])
async def list_conflicts(unresolved_only: bool = True):
    """List policy conflicts."""
    from src.services.federated_policy_service import get_federated_service
    service = get_federated_service()
    if unresolved_only:
        return service.get_unresolved_conflicts()
    return service.get_all_conflicts()


@router.post("/conflicts/{conflict_id}/resolve", response_model=PolicyConflict)
async def resolve_conflict(conflict_id: str, req: ConflictResolveRequest):
    """Resolve a policy conflict."""
    from src.services.federated_policy_service import get_federated_service
    conflict = get_federated_service().resolve_conflict(
        conflict_id, req.resolution, req.resolved_by
    )
    if conflict is None:
        raise HTTPException(404, f"Conflict '{conflict_id}' not found")
    return conflict


# ---------------------------------------------------------------------------
# Cost Endpoints
# ---------------------------------------------------------------------------

@router.get("/cost/breakdown/{session_id}", response_model=CostBreakdown)
async def get_cost_breakdown(session_id: str):
    """Get cost breakdown for a specific session."""
    from src.services.cost_intelligence_service import get_cost_service
    cost = get_cost_service().get_session_cost(session_id)
    if cost is None:
        raise HTTPException(404, f"No cost data for session '{session_id}'")
    return cost


@router.get("/cost/aggregate")
async def get_cost_aggregate():
    """Get aggregate cost metrics."""
    from src.services.cost_intelligence_service import get_cost_service
    return get_cost_service().aggregate_costs().model_dump()


@router.get("/cost/roi")
async def get_cost_roi():
    """Get ROI dashboard data."""
    from src.services.cost_intelligence_service import get_cost_service
    return get_cost_service().get_roi_metrics().model_dump()


@router.get("/cost/pricing")
async def get_pricing():
    """Get current LLM pricing configuration."""
    from src.services.cost_intelligence_service import get_cost_service
    return get_cost_service().get_pricing()


@router.put("/cost/pricing")
async def update_pricing(req: PricingUpdateRequest):
    """Update LLM pricing for a provider."""
    from src.services.cost_intelligence_service import get_cost_service
    get_cost_service().update_pricing(req.provider, req.input_price, req.output_price)
    return {"status": "updated", "provider": req.provider}


# ---------------------------------------------------------------------------
# Audit & Compliance Endpoints
# ---------------------------------------------------------------------------

@router.get("/audit")
async def get_audit_timeline(
    limit: int = 100,
    domain_id: Optional[str] = None,
    event_type: Optional[str] = None,
):
    """Get governance audit timeline with filters."""
    from src.services.governance_service import get_governance_service
    entries = get_governance_service().get_audit_timeline(
        limit=limit, domain_id=domain_id, event_type=event_type
    )
    return [e.model_dump(mode="json") for e in entries]


@router.get("/compliance/{framework}", response_model=ComplianceScore)
async def get_compliance(framework: str):
    """Get compliance score for a specific framework."""
    from src.services.governance_service import get_governance_service
    try:
        fw = ComplianceFramework(framework)
    except ValueError:
        raise HTTPException(400, f"Unknown framework: {framework}. Valid: {[f.value for f in ComplianceFramework]}")
    return get_governance_service().compute_compliance(fw)


# ---------------------------------------------------------------------------
# Board Endpoints
# ---------------------------------------------------------------------------

@router.get("/boards")
async def list_boards():
    """List all governance boards."""
    from src.services.governance_board_service import get_board_service
    boards = get_board_service().list_boards()
    return [b.model_dump(mode="json") for b in boards]


@router.post("/boards", status_code=201)
async def create_board(req: BoardCreateRequest):
    """Create a new governance board."""
    from src.services.governance_board_service import get_board_service
    from src.core.governance_models import (
        BoardMember,
        ComplianceFrameworkConfig,
        ComplianceFramework as CF,
    )
    compliance_configs = []
    for cc in req.compliance_configs:
        try:
            fw = CF(cc.get("framework", ""))
            compliance_configs.append(ComplianceFrameworkConfig(
                framework=fw,
                enabled=cc.get("enabled", True),
                target_score=cc.get("target_score", 0.8),
            ))
        except ValueError:
            pass
    members = [BoardMember(**m) for m in req.members]
    board = GovernanceBoard(
        name=req.name,
        description=req.description,
        domain_ids=req.domain_ids,
        policy_namespaces=req.policy_namespaces,
        compliance_configs=compliance_configs,
        members=members,
        tags=req.tags,
        is_active=req.is_active,
    )
    result = get_board_service().create_board(board)
    return result.model_dump(mode="json")


@router.get("/boards/templates")
async def list_board_templates():
    """List available board preset templates."""
    from src.services.governance_board_service import get_board_service
    return get_board_service().list_templates()


@router.post("/boards/from-template", status_code=201)
async def create_board_from_template(req: BoardFromTemplateRequest):
    """Create a board from a preset template."""
    from src.services.governance_board_service import get_board_service
    board = get_board_service().create_from_template(req.template_id, req.name)
    if board is None:
        raise HTTPException(404, f"Template '{req.template_id}' not found")
    return board.model_dump(mode="json")


@router.get("/boards/{board_id}")
async def get_board(board_id: str):
    """Get a specific governance board."""
    from src.services.governance_board_service import get_board_service
    board = get_board_service().get_board(board_id)
    if board is None:
        raise HTTPException(404, f"Board '{board_id}' not found")
    return board.model_dump(mode="json")


@router.put("/boards/{board_id}")
async def update_board(board_id: str, req: BoardUpdateRequest):
    """Update a governance board."""
    from src.services.governance_board_service import get_board_service
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    board = get_board_service().update_board(board_id, updates)
    if board is None:
        raise HTTPException(404, f"Board '{board_id}' not found")
    return board.model_dump(mode="json")


@router.delete("/boards/{board_id}", status_code=204)
async def delete_board(board_id: str):
    """Delete a governance board."""
    from src.services.governance_board_service import get_board_service
    if not get_board_service().delete_board(board_id):
        raise HTTPException(404, f"Board '{board_id}' not found")


@router.get("/boards/{board_id}/compliance")
async def get_board_compliance(board_id: str):
    """Get compliance scores for a board's configured frameworks."""
    from src.services.governance_board_service import get_board_service
    scores = get_board_service().compute_board_compliance(board_id)
    return [s.model_dump(mode="json") for s in scores]


# ---------------------------------------------------------------------------
# Export Endpoints
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_spec(req: SpecExportRequest):
    """Export governance board specification in various formats."""
    from src.services.governance_board_service import get_board_service
    from src.services.governance_export_service import get_export_service

    board = get_board_service().get_board(req.board_id)
    if board is None:
        raise HTTPException(404, f"Board '{req.board_id}' not found")

    export_service = get_export_service()

    if req.format == "json_ld":
        return export_service.export_json_ld(board)
    elif req.format == "yaml":
        yaml_content = export_service.export_yaml(board)
        return {"format": "yaml", "content": yaml_content}
    elif req.format == "csl":
        return {"format": "csl", "policies": export_service.export_csl(board)}
    else:
        raise HTTPException(400, f"Unknown format: {req.format}. Valid: json_ld, yaml, csl")


# ---------------------------------------------------------------------------
# Policy Text Extraction Endpoints
# ---------------------------------------------------------------------------

@router.post("/policies/extract", response_model=PolicyTextExtractionResponse)
async def extract_policies_from_text(req: PolicyTextExtractionRequest):
    """Extract governance rules from unstructured text via LLM."""
    try:
        prompt = f"""You are a governance policy extraction engine. Extract structured governance rules from the following text.

For each rule found, return a JSON array of objects with these fields:
- name: short snake_case rule name
- condition: dict of key-value conditions that trigger this rule
- constraint: dict of key-value constraints the rule enforces
- message: human-readable description of the rule
- severity: one of "critical", "high", "medium", "low"
- confidence: number in [0,1] indicating extraction confidence for this rule
- rationale: one sentence on why this rule applies
- evidence: list of 1-3 short quotes/snippets from the input text supporting this rule

Text to analyze:
---
{req.text}
---

Return ONLY a valid JSON array. No markdown, no explanation."""

        # LLM invoke is sync in current provider adapters; run off-thread from async endpoint.
        content = await asyncio.to_thread(_invoke_extraction_model, prompt)
        payload = _extract_json_fragment(content)

        # Parse the LLM response
        extracted_rules = json.loads(payload)
        if not isinstance(extracted_rules, list):
            extracted_rules = [extracted_rules]

        # Convert to FederatedPolicyRule format
        from src.core.governance_models import ConflictSeverity

        rules: list[ExtractedPolicyRule] = []
        for item in extracted_rules:
            rule_data = item if isinstance(item, dict) else {}
            try:
                severity = ConflictSeverity(rule_data.get("severity", "medium"))
            except ValueError:
                severity = ConflictSeverity.MEDIUM
            confidence_raw = rule_data.get("confidence", 0.6)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.6
            confidence = max(0.0, min(confidence, 1.0))

            evidence = rule_data.get("evidence", [])
            if not isinstance(evidence, list):
                evidence = []
            evidence = [str(item).strip() for item in evidence if str(item).strip()][:3]

            condition = rule_data.get("condition", {})
            if not isinstance(condition, dict):
                condition = {}
            constraint = rule_data.get("constraint", {})
            if not isinstance(constraint, dict):
                constraint = {}

            rules.append(
                ExtractedPolicyRule(
                    name=str(rule_data.get("name", "unnamed_rule")),
                    condition=condition,
                    constraint=constraint,
                    message=str(rule_data.get("message", "")),
                    severity=severity.value,
                    confidence=confidence,
                    rationale=str(rule_data.get("rationale", "")),
                    evidence=evidence,
                )
            )

        avg_confidence = round(
            sum(rule.confidence for rule in rules) / max(len(rules), 1),
            3,
        )

        return PolicyTextExtractionResponse(
            source_name=req.source_name,
            target_domain=req.target_domain,
            rules_extracted=len(rules),
            rules=rules,
            extraction_confidence_avg=avg_confidence,
            explainability={
                "why_this": "Rules were extracted from unstructured governance text using a structured schema.",
                "how_confident": avg_confidence,
                "based_on": [
                    f"source:{req.source_name}",
                    f"text_characters:{len(req.text)}",
                    f"rules_detected:{len(rules)}",
                ],
            },
        )

    except RetryError as exc:
        logger.warning("Policy extraction retry attempts exhausted: %s", exc)
        return PolicyTextExtractionResponse(
            source_name=req.source_name,
            target_domain=req.target_domain,
            rules_extracted=0,
            rules=[],
            explainability={
                "why_this": "Extraction failed due to repeated model invocation failures.",
                "how_confident": 0.0,
                "based_on": [f"source:{req.source_name}"],
            },
            error="LLM extraction failed after retries.",
        )
    except Exception as exc:
        logger.warning("Policy extraction failed: %s", exc)
        return PolicyTextExtractionResponse(
            source_name=req.source_name,
            target_domain=req.target_domain,
            rules_extracted=0,
            rules=[],
            explainability={
                "why_this": "Extraction could not parse or validate model output.",
                "how_confident": 0.0,
                "based_on": [f"source:{req.source_name}"],
            },
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Seed Demo Data Endpoint
# ---------------------------------------------------------------------------

@router.post("/seed/{template_id}")
async def seed_demo_data(template_id: str):
    """Seed demo data for a governance board template."""
    from src.services.governance_board_service import get_board_service
    board = get_board_service().seed_demo_data(template_id)
    if board is None:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return {
        "status": "seeded",
        "board_id": board.board_id,
        "board_name": board.name,
        "domains": board.domain_ids,
        "policies": board.policy_namespaces,
    }


# ---------------------------------------------------------------------------
# RAG / Knowledge Base Endpoints
# ---------------------------------------------------------------------------

@router.get("/rag/status")
async def rag_status():
    """Get RAG service status."""
    from src.services.rag_service import get_rag_service
    return get_rag_service().get_status()


@router.post("/rag/ingest-policies")
async def rag_ingest_policies():
    """Ingest all federated policies into the RAG knowledge base."""
    from src.services.rag_service import get_rag_service
    count = get_rag_service().ingest_policies()
    return {"status": "ingested", "chunks": count}


class RAGQueryRequest(BaseModel):
    query: str
    domain_id: Optional[str] = None
    top_k: int = 5


@router.post("/rag/query")
async def rag_query(req: RAGQueryRequest):
    """Query the RAG knowledge base."""
    from src.services.rag_service import get_rag_service
    result = get_rag_service().retrieve(req.query, top_k=req.top_k, domain_id=req.domain_id)
    return result.model_dump(mode="json")


@router.post("/rag/ingest-text")
async def rag_ingest_text(req: PolicyTextExtractionRequest):
    """Ingest arbitrary text into the RAG knowledge base."""
    from src.services.rag_service import get_rag_service
    count = get_rag_service().ingest_text(
        req.text,
        source=req.source_name,
        domain_id=req.target_domain,
    )
    return {"status": "ingested", "source": req.source_name, "chunks": count}


# ---------------------------------------------------------------------------
# Document Upload Endpoints
# ---------------------------------------------------------------------------

@router.post("/documents/upload")
async def upload_document(
    domain_id: Optional[str] = None,
    source_name: Optional[str] = None,
):
    """Upload a document for RAG ingestion.

    Accepts multipart/form-data with a 'file' field.
    Supported formats: PDF, DOCX, CSV, JSON, TXT, MD, YAML.
    """
    from fastapi import UploadFile, File as FastAPIFile

    # This endpoint is registered but the actual file handling requires
    # the FastAPI File() dependency — implemented via a separate route below.
    return {"error": "Use /governance/documents/upload-file instead"}


@router.post("/documents/upload-file")
async def upload_document_file(
    domain_id: Optional[str] = None,
    source_name: Optional[str] = None,
):
    """Placeholder for file upload — actual implementation uses Form dependency.

    The frontend should POST multipart/form-data to this endpoint.
    See the main app router for the actual file-accepting version.
    """
    return {"status": "ready", "supported_types": ["pdf", "docx", "csv", "json", "txt", "md", "yaml"]}


@router.get("/documents/status")
async def document_processor_status():
    """Get document processor status."""
    from src.services.document_processor import get_document_processor
    return get_document_processor().get_status()


# ---------------------------------------------------------------------------
# Agent Memory Endpoints
# ---------------------------------------------------------------------------

@router.get("/memory/status")
async def memory_status():
    """Get agent memory status."""
    from src.services.agent_memory import get_agent_memory
    return get_agent_memory().get_status()


@router.post("/memory/compact")
async def memory_compact():
    """Compact the agent memory file."""
    from src.services.agent_memory import get_agent_memory
    count = get_agent_memory().compact()
    return {"status": "compacted", "entries": count}


class MemoryRecallRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/memory/recall")
async def memory_recall(req: MemoryRecallRequest):
    """Recall similar past analyses from persistent memory."""
    from src.services.agent_memory import get_agent_memory
    results = get_agent_memory().recall(req.query, top_k=req.top_k)
    return [r.model_dump(mode="json") for r in results]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=GovernanceHealth)
async def governance_health():
    """Get governance subsystem health."""
    from src.services.governance_service import get_governance_service
    return get_governance_service().get_health()
