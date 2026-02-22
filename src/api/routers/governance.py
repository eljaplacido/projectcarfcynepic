"""Governance API Router for CARF Orchestration Governance.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

All endpoints under /governance/ prefix. Only registered when GOVERNANCE_ENABLED=true.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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
    return get_federated_service().add_policy(policy)


@router.get("/policies/{namespace:path}")
async def get_policy(namespace: str):
    """Get a specific policy by namespace."""
    from src.services.federated_policy_service import get_federated_service
    policy = get_federated_service().get_policy(namespace)
    if policy is None:
        raise HTTPException(404, f"Policy '{namespace}' not found")
    return policy


@router.put("/policies/{namespace:path}")
async def update_policy(namespace: str, req: PolicyUpdateRequest):
    """Update a federated policy."""
    from src.services.federated_policy_service import get_federated_service
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    policy = get_federated_service().update_policy(namespace, updates)
    if policy is None:
        raise HTTPException(404, f"Policy '{namespace}' not found")
    return policy


@router.delete("/policies/{namespace:path}", status_code=204)
async def delete_policy(namespace: str):
    """Remove a federated policy."""
    from src.services.federated_policy_service import get_federated_service
    if not get_federated_service().remove_policy(namespace):
        raise HTTPException(404, f"Policy '{namespace}' not found")


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

@router.post("/policies/extract")
async def extract_policies_from_text(req: PolicyTextExtractionRequest):
    """Extract governance rules from unstructured text via LLM."""
    import json as _json

    try:
        from src.core.llm import get_chat_model
        llm = get_chat_model(purpose="governance_extraction")

        prompt = f"""You are a governance policy extraction engine. Extract structured governance rules from the following text.

For each rule found, return a JSON array of objects with these fields:
- name: short snake_case rule name
- condition: dict of key-value conditions that trigger this rule
- constraint: dict of key-value constraints the rule enforces
- message: human-readable description of the rule
- severity: one of "critical", "high", "medium", "low"

Text to analyze:
---
{req.text}
---

Return ONLY a valid JSON array. No markdown, no explanation."""

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse the LLM response
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.endswith("```"):
                content = content[:-3].strip()

        extracted_rules = _json.loads(content)
        if not isinstance(extracted_rules, list):
            extracted_rules = [extracted_rules]

        # Convert to FederatedPolicyRule format
        from src.core.governance_models import FederatedPolicyRule, ConflictSeverity
        rules = []
        for rule_data in extracted_rules:
            try:
                severity = ConflictSeverity(rule_data.get("severity", "medium"))
            except ValueError:
                severity = ConflictSeverity.MEDIUM
            rules.append({
                "name": rule_data.get("name", "unnamed_rule"),
                "condition": rule_data.get("condition", {}),
                "constraint": rule_data.get("constraint", {}),
                "message": rule_data.get("message", ""),
                "severity": severity.value,
            })

        return {
            "source_name": req.source_name,
            "target_domain": req.target_domain,
            "rules_extracted": len(rules),
            "rules": rules,
            "error": None,
        }

    except Exception as exc:
        logger.warning(f"Policy extraction failed: {exc}")
        return {
            "source_name": req.source_name,
            "target_domain": req.target_domain,
            "rules_extracted": 0,
            "rules": [],
            "error": str(exc),
        }


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
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=GovernanceHealth)
async def governance_health():
    """Get governance subsystem health."""
    from src.services.governance_service import get_governance_service
    return get_governance_service().get_health()
