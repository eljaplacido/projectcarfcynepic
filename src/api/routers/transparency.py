"""Transparency, insights, workflow, agents, and escalation endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.models import (
    ComplianceRequest,
    CompleteWorkflowRequest,
    DataQualityRequest,
    EscalationResolveRequest,
    GuardianTransparencyRequest,
    InsightsRequest,
    InsightsResponseModel,
    ReliabilityRequest,
    StartWorkflowRequest,
    StartWorkflowResponse,
    WorkflowEvaluationRequest,
)
from src.services.human_layer import (
    Escalation,
    get_all_escalations,
    get_escalation,
    get_pending_escalations,
    resolve_escalation,
)
from src.services.transparency import (
    AgentInfo,
    DataQualityAssessment,
    EUAIActComplianceReport,
    GuardianTransparencyReport,
    ReliabilityAssessment,
    WorkflowEvaluation,
    get_transparency_service,
)
from src.services.insights_service import (
    AnalysisContext,
    InsightPriority,
    InsightType,
    get_insights_service,
)
from src.services.agent_tracker import (
    get_agent_tracker,
)

logger = logging.getLogger("carf")
router = APIRouter()


# ── Escalations ───────────────────────────────────────────────────────────

@router.get("/escalations", tags=["Human-in-the-Loop"])
async def list_escalations(pending_only: bool = True) -> list[Escalation]:
    """List escalations requiring human review."""
    if pending_only:
        return get_pending_escalations()
    return get_all_escalations()


@router.get("/escalations/{escalation_id}", tags=["Human-in-the-Loop"])
async def get_escalation_by_id(escalation_id: str) -> Escalation:
    """Get details of a specific escalation."""
    escalation = get_escalation(escalation_id)
    if not escalation:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation {escalation_id} not found"
        )
    return escalation


@router.post("/escalations/{escalation_id}/resolve", tags=["Human-in-the-Loop"])
async def resolve_escalation_endpoint(
    escalation_id: str,
    request: EscalationResolveRequest,
) -> Escalation:
    """Resolve an escalation with a human decision."""
    escalation = resolve_escalation(
        escalation_id=escalation_id,
        resolution=request.resolution,
        notes=request.notes,
        resolver_email=request.resolver_email,
    )
    if not escalation:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation {escalation_id} not found"
        )
    logger.info(f"Escalation {escalation_id} resolved: {request.resolution}")
    return escalation


# ── Transparency ──────────────────────────────────────────────────────────

def _map_agent_to_frontend(agent: AgentInfo) -> dict:
    """Map backend AgentInfo fields to frontend-expected field names.

    Frontend expects: name, description, category, dependencies, reliability_score
    Backend has:      agent_name, role, agent_type, limitations, reliability_score
    """
    return {
        "agent_id": agent.agent_id,
        "name": agent.agent_name,
        "description": agent.role,
        "category": agent.agent_type,
        "capabilities": agent.capabilities,
        "dependencies": agent.limitations,  # Map limitations as dependencies for frontend
        "reliability_score": agent.reliability_score,
        "version": agent.version,
        "status": agent.status,
    }


@router.get("/transparency/agents", tags=["Transparency"])
async def list_agents():
    """List all agents used in the CARF analysis pipeline.

    Returns agent data with field names mapped for the frontend:
    agent_name -> name, role -> description, agent_type -> category.
    """
    service = get_transparency_service()
    agents = service.get_all_agents()
    return [_map_agent_to_frontend(a) for a in agents]


@router.get("/transparency/agents/{agent_id}", tags=["Transparency"])
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent."""
    service = get_transparency_service()
    agent = service.get_agent_info(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return _map_agent_to_frontend(agent)


@router.post("/transparency/data-quality", response_model=DataQualityAssessment, tags=["Transparency"])
async def assess_data_quality(request: DataQualityRequest):
    """Assess data quality for transparency and reliability."""
    service = get_transparency_service()
    return service.assess_data_quality(request.data, request.dataset_id)


@router.post("/transparency/reliability", response_model=ReliabilityAssessment, tags=["Transparency"])
async def assess_reliability(request: ReliabilityRequest):
    """Assess overall reliability of an analysis."""
    service = get_transparency_service()

    data_quality = None
    if request.data:
        data_quality = service.assess_data_quality(request.data)

    return service.assess_reliability(
        confidence=request.confidence,
        data_quality=data_quality,
        refutation_passed=request.refutation_passed,
        refutation_tests_run=request.refutation_tests_run,
        refutation_tests_passed=request.refutation_tests_passed,
        sample_size=request.sample_size,
        methodology=request.methodology,
    )


@router.post("/transparency/compliance", response_model=EUAIActComplianceReport, tags=["Transparency"])
async def assess_compliance(request: ComplianceRequest):
    """Assess EU AI Act compliance status."""
    service = get_transparency_service()
    return service.assess_eu_ai_act_compliance(
        session_id=UUID(request.session_id) if request.session_id else None,
        has_explanation=request.has_explanation,
        has_audit_trail=request.has_audit_trail,
        has_human_oversight=request.has_human_oversight,
        data_governance_score=request.data_governance_score,
    )


@router.post("/transparency/evaluate-workflow", response_model=WorkflowEvaluation, tags=["Transparency"])
async def evaluate_workflow(request: WorkflowEvaluationRequest):
    """Evaluate an agentic workflow's feasibility, reliability, and transparency."""
    service = get_transparency_service()
    return service.evaluate_workflow(
        workflow_name=request.workflow_name,
        use_case=request.use_case,
        data_types=request.data_types,
        models_used=request.models_used,
        has_validation=request.has_validation,
        has_human_review=request.has_human_review,
        sample_size=request.sample_size,
        domain=request.domain,
    )


@router.post("/transparency/guardian", response_model=GuardianTransparencyReport, tags=["Transparency"])
async def get_guardian_transparency(request: GuardianTransparencyRequest):
    """Get transparent view of Guardian policy decisions."""
    service = get_transparency_service()
    return service.get_guardian_transparency(
        session_id=UUID(request.session_id),
        verdict=request.verdict,
        policies_passed=request.policies_passed,
        policies_violated=request.policies_violated,
    )


# ── Insights ──────────────────────────────────────────────────────────────

@router.post("/insights/generate", response_model=InsightsResponseModel, tags=["Insights"])
async def generate_insights(request: InsightsRequest):
    """Generate contextual insights for the specified persona."""
    service = get_insights_service()
    context = AnalysisContext(
        domain=request.domain,
        domain_confidence=request.domain_confidence,
        domain_entropy=request.domain_entropy,
        has_causal_result=request.has_causal_result,
        causal_effect=request.causal_effect,
        refutation_pass_rate=request.refutation_pass_rate,
        has_bayesian_result=request.has_bayesian_result,
        epistemic_uncertainty=request.epistemic_uncertainty,
        aleatoric_uncertainty=request.aleatoric_uncertainty,
        guardian_verdict=request.guardian_verdict,
        policies_passed=request.policies_passed,
        policies_total=request.policies_total,
        sample_size=request.sample_size,
        processing_time_ms=request.processing_time_ms,
    )

    response = service.generate_insights(context, request.persona)

    return InsightsResponseModel(
        persona=response.persona,
        insights=[
            {
                "id": i.id,
                "type": i.type.value,
                "priority": i.priority.value,
                "title": i.title,
                "description": i.description,
                "action": i.action,
                "related_component": i.related_component,
            }
            for i in response.insights
        ],
        total_count=response.total_count,
        generated_at=response.generated_at.isoformat(),
    )


@router.get("/insights/types", tags=["Insights"])
async def get_insight_types():
    """Get available insight types and priorities."""
    return {
        "types": [t.value for t in InsightType],
        "priorities": [p.value for p in InsightPriority],
        "personas": ["analyst", "developer", "executive"],
    }


# ── Workflow Tracking ─────────────────────────────────────────────────────

@router.post("/workflow/start", response_model=StartWorkflowResponse, tags=["Workflow Tracking"])
async def start_workflow_tracking(request: StartWorkflowRequest):
    """Start tracking a new workflow execution."""
    tracker = get_agent_tracker()
    trace = tracker.start_workflow(
        session_id=UUID(request.session_id),
        query=request.query,
        workflow_name=request.workflow_name,
    )

    return StartWorkflowResponse(
        trace_id=str(trace.trace_id),
        session_id=str(trace.session_id),
        started_at=trace.started_at.isoformat(),
    )


@router.post("/workflow/complete", tags=["Workflow Tracking"])
async def complete_workflow_tracking(request: CompleteWorkflowRequest):
    """Mark a workflow as complete and aggregate metrics."""
    tracker = get_agent_tracker()
    trace = tracker.complete_workflow(
        trace_id=UUID(request.trace_id),
        domain=request.domain,
        quality_score=request.quality_score,
    )

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return {
        "trace_id": str(trace.trace_id),
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        "total_latency_ms": trace.total_latency_ms,
        "total_tokens": trace.total_tokens,
        "total_cost_usd": trace.total_cost_usd,
        "executions_count": len(trace.executions),
    }


@router.get("/workflow/trace/{trace_id}", tags=["Workflow Tracking"])
async def get_workflow_trace(trace_id: str):
    """Get full execution trace for a workflow."""
    tracker = get_agent_tracker()
    trace = tracker.get_trace(UUID(trace_id))

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return {
        "trace_id": str(trace.trace_id),
        "session_id": str(trace.session_id),
        "workflow_name": trace.workflow_name,
        "domain": trace.domain,
        "query": trace.query,
        "started_at": trace.started_at.isoformat(),
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        "total_latency_ms": trace.total_latency_ms,
        "total_tokens": trace.total_tokens,
        "total_cost_usd": trace.total_cost_usd,
        "overall_quality_score": trace.overall_quality_score,
        "executions": [
            {
                "execution_id": str(ex.execution_id),
                "agent_id": ex.agent_id,
                "agent_name": ex.agent_name,
                "status": ex.status.value,
                "started_at": ex.started_at.isoformat(),
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                "latency_ms": ex.latency_ms,
                "input_summary": ex.input_summary,
                "output_summary": ex.output_summary,
                "quality_score": ex.quality_score,
                "confidence_score": ex.confidence_score,
                "error_message": ex.error_message,
                "llm_usage": {
                    "model": ex.llm_usage.model,
                    "provider": ex.llm_usage.provider,
                    "prompt_tokens": ex.llm_usage.prompt_tokens,
                    "completion_tokens": ex.llm_usage.completion_tokens,
                    "total_tokens": ex.llm_usage.total_tokens,
                    "cost_usd": ex.llm_usage.cost_usd,
                } if ex.llm_usage else None,
            }
            for ex in trace.executions
        ],
    }


@router.get("/workflow/session/{session_id}", tags=["Workflow Tracking"])
async def get_session_trace(session_id: str):
    """Get the most recent workflow trace for a session."""
    tracker = get_agent_tracker()
    trace = tracker.get_session_trace(UUID(session_id))

    if not trace:
        raise HTTPException(status_code=404, detail="No trace found for session")

    return {"trace_id": str(trace.trace_id)}


@router.get("/workflow/recent", tags=["Workflow Tracking"])
async def get_recent_traces(limit: int = 10):
    """Get the most recent workflow traces."""
    tracker = get_agent_tracker()
    traces = tracker.get_recent_traces(limit)

    return {
        "traces": [
            {
                "trace_id": str(t.trace_id),
                "session_id": str(t.session_id),
                "workflow_name": t.workflow_name,
                "domain": t.domain,
                "started_at": t.started_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "total_latency_ms": t.total_latency_ms,
                "executions_count": len(t.executions),
            }
            for t in traces
        ],
        "count": len(traces),
    }


@router.get("/agents/stats", tags=["Workflow Tracking"])
async def get_agent_statistics(agent_id: str | None = None):
    """Get performance statistics for agents."""
    tracker = get_agent_tracker()
    stats = tracker.get_agent_stats(agent_id)

    return {
        "agents": [
            {
                "agent_id": s.agent_id,
                "agent_name": s.agent_name,
                "total_executions": s.total_executions,
                "successful_executions": s.successful_executions,
                "failed_executions": s.failed_executions,
                "success_rate": s.successful_executions / s.total_executions if s.total_executions > 0 else 0,
                "average_latency_ms": s.average_latency_ms,
                "average_quality_score": s.average_quality_score,
                "total_tokens_used": s.total_tokens_used,
                "total_cost_usd": s.total_cost_usd,
                "last_execution": s.last_execution.isoformat() if s.last_execution else None,
            }
            for s in stats
        ],
        "count": len(stats),
    }


@router.get("/agents/comparison", tags=["Workflow Tracking"])
async def get_agent_comparison():
    """Get comparison data for all agents."""
    tracker = get_agent_tracker()
    return tracker.get_agent_comparison()


# ── Executive Summary ────────────────────────────────────────────────────

class ExecutiveSummaryRequest(BaseModel):
    """Request for executive summary generation."""
    domain: str = "unknown"
    domain_confidence: float = 0.0
    causal_effect: float | None = None
    refutation_pass_rate: float | None = None
    bayesian_uncertainty: float | None = None
    guardian_verdict: str = "unknown"
    treatment: str | None = None
    outcome: str | None = None
    sample_size: int | None = None
    p_value: float | None = None


@router.post("/summary/executive", tags=["Executive Summary"])
async def generate_executive_summary(request: ExecutiveSummaryRequest):
    """Generate a structured executive summary for decision-makers.

    Translates technical metrics into plain-English findings,
    confidence assessments, and recommended actions.
    """
    # Derive confidence level description
    if request.domain_confidence >= 0.85:
        confidence_level = "High confidence"
        confidence_desc = "The analysis results are highly reliable."
    elif request.domain_confidence >= 0.70:
        confidence_level = "Moderate confidence"
        confidence_desc = "Results are reasonably reliable but should be validated."
    elif request.domain_confidence >= 0.50:
        confidence_level = "Low confidence"
        confidence_desc = "Results have significant uncertainty — use with caution."
    else:
        confidence_level = "Very low confidence"
        confidence_desc = "Results are unreliable and should not drive decisions alone."

    # Derive key finding
    key_finding = _derive_key_finding(
        request.causal_effect, request.treatment, request.outcome,
        request.p_value, request.domain,
    )

    # Derive recommended action
    recommended_action = _derive_recommended_action(
        request.guardian_verdict, request.domain_confidence,
        request.refutation_pass_rate, request.domain,
    )

    # Derive risk assessment
    risk_assessment = _derive_risk_assessment(
        request.guardian_verdict, request.refutation_pass_rate,
        request.bayesian_uncertainty, request.domain,
    )

    # Build plain explanation narrative
    plain_explanation = _build_narrative(
        key_finding, confidence_desc, recommended_action,
        risk_assessment, request.domain,
    )

    from datetime import datetime
    return {
        "key_finding": key_finding,
        "confidence_level": confidence_level,
        "recommended_action": recommended_action,
        "risk_assessment": risk_assessment,
        "plain_explanation": plain_explanation,
        "domain": request.domain,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _derive_key_finding(
    effect: float | None, treatment: str | None, outcome: str | None,
    p_value: float | None, domain: str,
) -> str:
    """Convert causal effect into decision-maker-friendly language."""
    if effect is None:
        if domain in ("Complex", "complex"):
            return "The situation involves high uncertainty — no definitive causal relationship identified yet."
        return "No causal effect was measured in this analysis."

    treatment_name = treatment or "the intervention"
    outcome_name = outcome or "the outcome"
    abs_effect = abs(effect)

    if abs_effect < 0.01:
        magnitude = "negligible"
    elif abs_effect < 1.0:
        magnitude = "small"
    elif abs_effect < 10.0:
        magnitude = "moderate"
    elif abs_effect < 50.0:
        magnitude = "substantial"
    else:
        magnitude = "very large"

    direction = "positive" if effect > 0 else "negative"
    impact_word = "increases" if effect > 0 else "decreases"

    finding = f"{treatment_name.capitalize()} has a {magnitude} {direction} impact — it {impact_word} {outcome_name} by {abs_effect:.2f} units."

    if p_value is not None:
        if p_value < 0.01:
            finding += " This finding is statistically significant (p < 0.01)."
        elif p_value < 0.05:
            finding += " This finding is statistically significant (p < 0.05)."
        elif p_value < 0.10:
            finding += " This finding is marginally significant (p < 0.10)."
        else:
            finding += f" However, the statistical significance is weak (p = {p_value:.3f})."

    return finding


def _derive_recommended_action(
    verdict: str, confidence: float,
    refutation_rate: float | None, domain: str,
) -> str:
    """Generate action recommendation based on analysis results."""
    if verdict in ("fail", "rejected", "blocked"):
        return "DO NOT proceed — the Guardian policy engine has flagged safety concerns. Escalate to compliance team for review."

    if confidence < 0.50:
        return "Gather more data before making a decision. Current analysis confidence is too low for reliable action."

    if refutation_rate is not None and refutation_rate < 0.5:
        return "Exercise caution — less than half of robustness checks passed. Consider additional validation before acting."

    if domain in ("Chaotic", "chaotic"):
        return "Stabilize the situation first. In chaotic conditions, act to establish order before optimizing."

    if domain in ("Complex", "complex"):
        return "Design safe-to-fail experiments to test the hypothesis before full implementation."

    if confidence >= 0.85 and (refutation_rate is None or refutation_rate >= 0.75):
        return "Evidence supports proceeding. Implement with standard monitoring and review cycles."

    return "Proceed with caution. Monitor key metrics closely and be prepared to adjust."


def _derive_risk_assessment(
    verdict: str, refutation_rate: float | None,
    bayesian_uncertainty: float | None, domain: str,
) -> str:
    """Assess risk level for decision-makers."""
    risks = []

    if verdict in ("fail", "rejected"):
        risks.append("Policy violations detected — regulatory or safety risk present")

    if refutation_rate is not None and refutation_rate < 0.5:
        risks.append("Causal analysis failed multiple robustness checks")
    elif refutation_rate is not None and refutation_rate < 0.75:
        risks.append("Some robustness checks did not pass — moderate analytical risk")

    if bayesian_uncertainty is not None and bayesian_uncertainty > 0.7:
        risks.append("High epistemic uncertainty — the model lacks sufficient knowledge")
    elif bayesian_uncertainty is not None and bayesian_uncertainty > 0.5:
        risks.append("Moderate uncertainty in Bayesian estimates")

    if domain in ("Chaotic", "chaotic"):
        risks.append("Operating in chaotic domain — situation is volatile and unpredictable")
    elif domain in ("Disorder", "disorder"):
        risks.append("Cannot classify the domain — fundamental ambiguity in the situation")

    if not risks:
        return "Low risk — analysis passed all checks and confidence is adequate."

    return "Identified risks: " + "; ".join(risks) + "."


def _build_narrative(
    finding: str, confidence_desc: str,
    action: str, risk: str, domain: str,
) -> str:
    """Build a coherent narrative paragraph for executive consumption."""
    domain_context = {
        "Clear": "a straightforward situation with clear cause-and-effect",
        "Complicated": "a complicated situation requiring expert analysis",
        "Complex": "a complex adaptive situation with emergent behavior",
        "Chaotic": "a chaotic situation requiring immediate stabilization",
        "Disorder": "an ambiguous situation that defies classification",
    }
    context = domain_context.get(domain, "an analytical scenario")

    return (
        f"This analysis examined {context}. "
        f"{finding} {confidence_desc} "
        f"{risk} "
        f"Recommendation: {action}"
    )
