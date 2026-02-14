"""Query and domain endpoints — core CARF pipeline."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import (
    _load_scenario_payload,
    _load_scenarios,
    _validate_payload_limits,
)
from src.api.models import (
    BayesianResult,
    CausalResult,
    EnhancedQueryResponse,
    FastQueryRequest,
    FastQueryResponse,
    GuardianResult,
    QueryRequest,
    QueryResponse,
    ReasoningStep,
)
from src.services.bayesian import BayesianInferenceConfig
from src.services.causal import CausalEstimationConfig
from src.services.dataset_store import get_dataset_store
from src.services.transparency import get_transparency_service
from src.workflows.graph import run_carf

logger = logging.getLogger("carf")
router = APIRouter()


@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """Process a query through the CARF cognitive pipeline."""
    try:
        _validate_payload_limits(request)

        context = dict(request.context or {})
        if request.dataset_selection:
            store = get_dataset_store()
            try:
                store.get_dataset(request.dataset_selection.dataset_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

            context["dataset_selection"] = request.dataset_selection.model_dump()
            context["causal_estimation"] = CausalEstimationConfig(
                dataset_id=request.dataset_selection.dataset_id,
                treatment=request.dataset_selection.treatment,
                outcome=request.dataset_selection.outcome,
                covariates=request.dataset_selection.covariates,
                effect_modifiers=request.dataset_selection.effect_modifiers,
            ).model_dump()
        elif request.causal_estimation:
            context["causal_estimation"] = request.causal_estimation.model_dump()

        # Auto-load scenario configuration if ID provided but config missing
        scenario_id = context.get("scenario_id")
        if scenario_id:
            try:
                scenarios = _load_scenarios()
                scenario = next((s for s in scenarios if s.id == scenario_id), None)
                if scenario:
                    payload = _load_scenario_payload(scenario.payload_path)

                    if "context" in payload and isinstance(payload["context"], dict):
                        for key, value in payload["context"].items():
                            if key not in context:
                                context[key] = value

                    if "causal_estimation" in payload and "causal_estimation" not in context:
                        ce_config = CausalEstimationConfig(**payload["causal_estimation"])
                        context["causal_estimation"] = ce_config.model_dump()

                    if "bayesian_inference" in payload and "bayesian_inference" not in context:
                        bi_config = BayesianInferenceConfig(**payload["bayesian_inference"])
                        context["bayesian_inference"] = bi_config.model_dump()

                    logger.info(f"Auto-loaded scenario config: {scenario_id}, domain_hint={context.get('domain_hint')}")
            except Exception as e:
                logger.warning(f"Failed to auto-load scenario {scenario_id}: {e}")

        if request.bayesian_inference:
            context["bayesian_inference"] = request.bayesian_inference.model_dump()

        # Run the full CARF pipeline
        final_state = await run_carf(
            user_input=request.query,
            context=context,
        )

        # Build reasoning chain for response
        reasoning_chain = [
            ReasoningStep(
                node=step.node_name,
                action=step.action,
                confidence=step.confidence.value,
                timestamp=step.timestamp,
                duration_ms=step.duration_ms,
            )
            for step in final_state.reasoning_chain
        ]

        # Build causal result if available
        causal_result = None
        if final_state.causal_evidence:
            ce = final_state.causal_evidence
            refutations_passed = sum(1 for v in ce.refutation_results.values() if v)
            causal_result = CausalResult(
                effect=ce.effect_size,
                unit="units",
                p_value=ce.p_value,
                ci_low=ce.confidence_interval[0],
                ci_high=ce.confidence_interval[1],
                description=ce.interpretation or f"Effect of {ce.treatment} on {ce.outcome}",
                refutations_passed=refutations_passed,
                refutations_total=len(ce.refutation_results),
                confounders_controlled=len([c for c in ce.confounders_checked]),
                confounders_total=len(ce.confounders_checked),
                treatment=ce.treatment,
                outcome=ce.outcome,
            )

        # Build bayesian result if available
        bayesian_result = None
        if final_state.bayesian_evidence:
            be = final_state.bayesian_evidence
            bayesian_result = BayesianResult(
                posterior_mean=be.posterior_mean,
                ci_low=be.credible_interval[0],
                ci_high=be.credible_interval[1],
                uncertainty_before=be.uncertainty_before,
                uncertainty_after=be.uncertainty_after,
                epistemic_uncertainty=be.epistemic_uncertainty,
                aleatoric_uncertainty=be.aleatoric_uncertainty,
                hypothesis=be.hypothesis,
                confidence_level=be.confidence_level,
                probes_designed=be.probes_designed,
                recommended_probe=be.recommended_probe,
            )

        # Build guardian result
        guardian_result = GuardianResult(
            verdict=final_state.guardian_verdict,
            policies_passed=0 if final_state.policy_violations else 1,
            policies_total=1,
            risk_level="high" if final_state.policy_violations else "low",
            violations=final_state.policy_violations or [],
        )

        return QueryResponse(
            session_id=str(final_state.session_id),
            domain=final_state.cynefin_domain,
            domain_confidence=final_state.domain_confidence,
            domain_entropy=final_state.domain_entropy,
            guardian_verdict=final_state.guardian_verdict,
            response=final_state.final_response,
            requires_human=final_state.should_escalate_to_human(),
            reasoning_chain=reasoning_chain,
            causal_result=causal_result,
            bayesian_result=bayesian_result,
            guardian_result=guardian_result,
            error=final_state.error,
            router_reasoning=final_state.current_hypothesis,
            router_key_indicators=final_state.router_key_indicators,
            domain_scores=final_state.domain_scores,
            triggered_method=final_state.triggered_method,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"CARF pipeline validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"CARF pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"CARF processing failed: {str(e)}",
        )


@router.post("/query/stream", tags=["Query"])
async def process_query_stream(request: QueryRequest):
    """Process a query with real-time chain-of-thought streaming."""

    async def generate_progress():
        try:
            _validate_payload_limits(request)

            yield f"data: {json.dumps({'step': 'init', 'status': 'started', 'message': 'Initializing analysis', 'progress_percent': 5, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            context = dict(request.context or {})
            scenario_id = context.get("scenario_id")

            if scenario_id:
                try:
                    scenarios = _load_scenarios()
                    scenario = next((s for s in scenarios if s.id == scenario_id), None)
                    if scenario:
                        payload = _load_scenario_payload(scenario.payload_path)
                        if "context" in payload and isinstance(payload["context"], dict):
                            for key, value in payload["context"].items():
                                if key not in context:
                                    context[key] = value
                        if "causal_estimation" in payload and "causal_estimation" not in context:
                            ce_config = CausalEstimationConfig(**payload["causal_estimation"])
                            context["causal_estimation"] = ce_config.model_dump()
                        if "bayesian_inference" in payload and "bayesian_inference" not in context:
                            bi_config = BayesianInferenceConfig(**payload["bayesian_inference"])
                            context["bayesian_inference"] = bi_config.model_dump()
                except Exception as e:
                    logger.warning(f"Failed to auto-load scenario {scenario_id}: {e}")

            if request.causal_estimation:
                context["causal_estimation"] = request.causal_estimation.model_dump()
            if request.bayesian_inference:
                context["bayesian_inference"] = request.bayesian_inference.model_dump()

            yield f"data: {json.dumps({'step': 'context', 'status': 'completed', 'message': 'Context prepared', 'progress_percent': 10, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            yield f"data: {json.dumps({'step': 'router', 'status': 'started', 'message': 'Classifying query into Cynefin domain...', 'progress_percent': 15, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            from src.core.state import EpistemicState
            from src.workflows.router import cynefin_router_node

            initial_state = EpistemicState(user_input=request.query, context=context)

            state = await cynefin_router_node(initial_state)
            domain = state.cynefin_domain.value
            confidence = state.domain_confidence

            yield f"data: {json.dumps({'step': 'router', 'status': 'completed', 'message': f'Classified as {domain} (confidence: {confidence:.0%})', 'progress_percent': 30, 'timestamp': datetime.now().isoformat(), 'details': {'domain': domain, 'confidence': confidence, 'entropy': state.domain_entropy}})}\n\n"
            await asyncio.sleep(0.1)

            triggered_method = state.triggered_method or "unknown"
            yield f"data: {json.dumps({'step': 'domain_agent', 'status': 'started', 'message': f'Running {triggered_method} analysis...', 'progress_percent': 35, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            final_state = await run_carf(user_input=request.query, context=context)

            yield f"data: {json.dumps({'step': 'domain_agent', 'status': 'completed', 'message': 'Analysis complete', 'progress_percent': 70, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            guardian_status = final_state.guardian_verdict.value if final_state.guardian_verdict else "passed"
            yield f"data: {json.dumps({'step': 'guardian', 'status': 'completed', 'message': f'Policy check: {guardian_status}', 'progress_percent': 90, 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            reasoning_chain = [
                {
                    "node": step.node_name,
                    "action": step.action,
                    "confidence": step.confidence.value,
                    "timestamp": step.timestamp.isoformat(),
                    "durationMs": step.duration_ms,
                }
                for step in final_state.reasoning_chain
            ]

            causal_result = None
            if final_state.causal_evidence:
                ce = final_state.causal_evidence
                causal_result = {
                    "effect": ce.effect_size,
                    "confidenceInterval": ce.confidence_interval,
                    "refutationsPassed": sum(1 for v in ce.refutation_results.values() if v),
                    "treatment": ce.treatment,
                    "outcome": ce.outcome,
                }

            final_response = {
                "step": "complete",
                "status": "completed",
                "message": "Analysis complete",
                "progress_percent": 100,
                "timestamp": datetime.now().isoformat(),
                "result": {
                    "sessionId": str(final_state.session_id),
                    "domain": final_state.cynefin_domain.value,
                    "domainConfidence": final_state.domain_confidence,
                    "response": final_state.final_response,
                    "reasoningChain": reasoning_chain,
                    "causalResult": causal_result,
                    "guardianVerdict": final_state.guardian_verdict.value if final_state.guardian_verdict else None,
                },
            }
            yield f"data: {json.dumps(final_response)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e), 'progress_percent': 0, 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/query/fast", response_model=FastQueryResponse, tags=["Query"])
async def process_fast_query(request: FastQueryRequest):
    """Fast causal effect query using pre-trained ChimeraOracle."""
    from src.services.chimera_oracle import get_oracle_engine

    engine = get_oracle_engine()

    if not engine.has_model(request.scenario_id):
        raise HTTPException(
            status_code=404,
            detail=f"No trained Oracle model for scenario '{request.scenario_id}'. "
            f"Train first with POST /oracle/train. Available: {engine.get_available_scenarios()}",
        )

    try:
        prediction = engine.predict_effect(request.scenario_id, request.context)
        model_stats = engine.get_average_treatment_effect(request.scenario_id)

        effect = prediction.effect_estimate
        direction = "reduces" if effect < 0 else "increases"
        magnitude = abs(effect)

        interpretation = (
            f"The {request.treatment} {direction} {request.outcome} by approximately "
            f"{magnitude:.2f} units (95% CI: [{prediction.confidence_interval[0]:.2f}, "
            f"{prediction.confidence_interval[1]:.2f}]). "
            f"Based on {model_stats['n_samples']} samples."
        )

        return FastQueryResponse(
            effect_estimate=prediction.effect_estimate,
            confidence_interval=prediction.confidence_interval,
            interpretation=interpretation,
            prediction_time_ms=prediction.prediction_time_ms,
            model_info={
                "scenario_id": request.scenario_id,
                "average_treatment_effect": model_stats["ate"],
                "effect_std": model_stats["std"],
                "n_samples": model_stats["n_samples"],
                "feature_importance": prediction.feature_importance,
            },
            domain="Complicated",
        )
    except Exception as e:
        logger.error(f"Fast query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/transparent", response_model=EnhancedQueryResponse, tags=["Query"])
async def process_query_with_transparency(request: QueryRequest):
    """Process a query with full transparency and reliability metrics."""
    try:
        _validate_payload_limits(request)

        context = dict(request.context or {})
        if request.causal_estimation:
            context["causal_estimation"] = request.causal_estimation.model_dump()
        if request.bayesian_inference:
            context["bayesian_inference"] = request.bayesian_inference.model_dump()

        final_state = await run_carf(
            user_input=request.query,
            context=context,
        )

        reasoning_chain = [
            ReasoningStep(
                node=step.node_name,
                action=step.action,
                confidence=step.confidence.value,
                timestamp=step.timestamp,
                duration_ms=step.duration_ms,
            )
            for step in final_state.reasoning_chain
        ]

        causal_result = None
        if final_state.causal_evidence:
            ce = final_state.causal_evidence
            refutations_passed = sum(1 for v in ce.refutation_results.values() if v)
            causal_result = CausalResult(
                effect=ce.effect_size,
                unit="units",
                p_value=ce.p_value,
                ci_low=ce.confidence_interval[0],
                ci_high=ce.confidence_interval[1],
                description=ce.interpretation or f"Effect of {ce.treatment} on {ce.outcome}",
                refutations_passed=refutations_passed,
                refutations_total=len(ce.refutation_results),
                confounders_controlled=len([c for c in ce.confounders_checked]),
                confounders_total=len(ce.confounders_checked),
                treatment=ce.treatment,
                outcome=ce.outcome,
            )

        bayesian_result = None
        if final_state.bayesian_evidence:
            be = final_state.bayesian_evidence
            bayesian_result = BayesianResult(
                posterior_mean=be.posterior_mean,
                ci_low=be.credible_interval[0],
                ci_high=be.credible_interval[1],
                uncertainty_before=be.uncertainty_before,
                uncertainty_after=be.uncertainty_after,
                epistemic_uncertainty=be.epistemic_uncertainty,
                aleatoric_uncertainty=be.aleatoric_uncertainty,
                hypothesis=be.hypothesis,
                confidence_level=be.confidence_level,
                probes_designed=be.probes_designed,
                recommended_probe=be.recommended_probe,
            )

        guardian_result = GuardianResult(
            verdict=final_state.guardian_verdict,
            policies_passed=0 if final_state.policy_violations else 1,
            policies_total=1,
            risk_level="high" if final_state.policy_violations else "low",
            violations=final_state.policy_violations or [],
        )

        transparency_service = get_transparency_service()

        agents_used = []
        for step in final_state.reasoning_chain:
            agent = transparency_service.get_agent_info(step.node_name)
            if agent and agent not in agents_used:
                agents_used.append(agent)

        refutation_passed = None
        refutation_count = 0
        refutation_passed_count = 0
        if final_state.causal_evidence:
            refutation_count = len(final_state.causal_evidence.refutation_results)
            refutation_passed_count = sum(
                1 for v in final_state.causal_evidence.refutation_results.values() if v
            )
            refutation_passed = refutation_passed_count == refutation_count

        reliability = transparency_service.assess_reliability(
            confidence=final_state.domain_confidence,
            refutation_passed=refutation_passed,
            refutation_tests_run=refutation_count,
            refutation_tests_passed=refutation_passed_count,
            methodology=final_state.triggered_method or "unknown",
        )

        return EnhancedQueryResponse(
            session_id=str(final_state.session_id),
            domain=final_state.cynefin_domain,
            domain_confidence=final_state.domain_confidence,
            domain_entropy=final_state.domain_entropy,
            guardian_verdict=final_state.guardian_verdict,
            response=final_state.final_response,
            requires_human=final_state.should_escalate_to_human(),
            reasoning_chain=reasoning_chain,
            causal_result=causal_result,
            bayesian_result=bayesian_result,
            guardian_result=guardian_result,
            error=final_state.error,
            router_reasoning=final_state.current_hypothesis,
            router_key_indicators=final_state.router_key_indicators,
            domain_scores=final_state.domain_scores,
            triggered_method=final_state.triggered_method,
            reliability_assessment=reliability,
            agents_used=agents_used,
            eu_compliance_status="compliant",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transparent query error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}",
        )


@router.get("/domains", tags=["Query"])
async def list_domains():
    """List all Cynefin domains and their descriptions."""
    return {
        "domains": [
            {
                "name": "Clear",
                "description": "Cause-effect obvious. Deterministic automation.",
                "route": "deterministic_runner",
            },
            {
                "name": "Complicated",
                "description": "Requires expert analysis. Causal inference.",
                "route": "causal_analyst",
            },
            {
                "name": "Complex",
                "description": "Emergent causality. Bayesian probing.",
                "route": "bayesian_explorer",
            },
            {
                "name": "Chaotic",
                "description": "Crisis mode. Circuit breaker.",
                "route": "circuit_breaker",
            },
            {
                "name": "Disorder",
                "description": "Cannot classify. Human escalation.",
                "route": "human_escalation",
            },
        ]
    }
