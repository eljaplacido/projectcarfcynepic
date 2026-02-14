"""Transparency, insights, workflow, agents, and escalation endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

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

@router.get("/transparency/agents", response_model=list[AgentInfo], tags=["Transparency"])
async def list_agents():
    """List all agents used in the CARF analysis pipeline."""
    service = get_transparency_service()
    return service.get_all_agents()


@router.get("/transparency/agents/{agent_id}", response_model=AgentInfo, tags=["Transparency"])
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent."""
    service = get_transparency_service()
    agent = service.get_agent_info(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return agent


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
