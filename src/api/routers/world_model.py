# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""World Model, Counterfactual, and Neurosymbolic API endpoints.

Phase 17 — Causal World Models, Counterfactual Reasoning, and
Neurosymbolic Integration inspired by recent research in causal AI,
NeSy AI, and world models.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.api.world_model")
router = APIRouter(prefix="/world-model", tags=["World Model"])


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================


class CounterfactualRequest(BaseModel):
    """Request for counterfactual reasoning."""

    query: str = Field(..., description="Natural language counterfactual question")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    dataset_id: str | None = Field(default=None, description="Optional dataset for data-grounded reasoning")


class CounterfactualResponse(BaseModel):
    """Response from counterfactual reasoning."""

    factual_outcome: str = Field(..., description="What actually happened")
    counterfactual_outcome: str = Field(..., description="What would have happened")
    causal_attribution: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    narrative: str = Field(default="", description="Human-readable explanation")
    reasoning_steps: list[str] = Field(default_factory=list)


class WorldModelSimulationRequest(BaseModel):
    """Request for world model forward simulation."""

    query: str = Field(..., description="What scenario to simulate")
    initial_conditions: dict[str, float] = Field(
        default_factory=dict, description="Starting variable values"
    )
    interventions: dict[str, float] = Field(
        default_factory=dict, description="do(X=x) interventions to apply"
    )
    steps: int = Field(default=5, ge=1, le=50, description="Simulation steps")
    dataset_id: str | None = Field(default=None)
    context: dict[str, Any] = Field(default_factory=dict)


class WorldModelSimulationResponse(BaseModel):
    """Response from world model simulation."""

    trajectory: list[dict[str, float]] = Field(
        default_factory=list, description="State at each timestep"
    )
    variables: list[str] = Field(default_factory=list)
    interventions_applied: dict[str, float] = Field(default_factory=dict)
    model_confidence: float = Field(default=0.0)
    interpretation: str = Field(default="")


class NeurosymbolicReasoningRequest(BaseModel):
    """Request for neurosymbolic reasoning."""

    query: str = Field(..., description="Question to reason about")
    context: dict[str, Any] = Field(default_factory=dict)
    use_knowledge_graph: bool = Field(default=True, description="Ground reasoning in Neo4j KG")
    max_iterations: int = Field(default=3, ge=1, le=10)


class NeurosymbolicReasoningResponse(BaseModel):
    """Response from neurosymbolic reasoning."""

    conclusion: str = Field(..., description="Final reasoned conclusion")
    derived_facts: list[dict[str, Any]] = Field(default_factory=list)
    rule_chain: list[str] = Field(default_factory=list, description="Rules that fired")
    shortcut_warnings: list[str] = Field(
        default_factory=list, description="Detected reasoning shortcuts"
    )
    iterations: int = Field(default=0)
    confidence: float = Field(default=0.0)
    symbolic_grounding: list[dict[str, Any]] = Field(
        default_factory=list, description="Facts from knowledge graph"
    )


class ScenarioComparisonRequest(BaseModel):
    """Request for comparing multiple counterfactual scenarios."""

    base_query: str = Field(..., description="Base scenario description")
    alternative_interventions: list[dict[str, float]] = Field(
        ..., description="List of intervention sets to compare"
    )
    outcome_variable: str = Field(..., description="Variable to compare across scenarios")
    context: dict[str, Any] = Field(default_factory=dict)


class ScenarioComparisonResponse(BaseModel):
    """Response from scenario comparison."""

    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    best_scenario_index: int = Field(default=0)
    ranking_rationale: str = Field(default="")
    outcome_range: tuple[float, float] = Field(default=(0.0, 0.0))


class CausalAttributionRequest(BaseModel):
    """Request for causal attribution analysis."""

    outcome_description: str = Field(..., description="The outcome to attribute causes to")
    context: dict[str, Any] = Field(default_factory=dict)
    dataset_id: str | None = Field(default=None)


class CausalAttributionResponse(BaseModel):
    """Response from causal attribution."""

    outcome: str
    attributions: list[dict[str, Any]] = Field(
        default_factory=list, description="Causes ranked by importance"
    )
    but_for_tests: list[dict[str, Any]] = Field(
        default_factory=list, description="But-for causation test results"
    )
    narrative: str = Field(default="")


# =============================================================================
# COUNTERFACTUAL ENDPOINTS
# =============================================================================


@router.post("/counterfactual", response_model=CounterfactualResponse)
async def run_counterfactual(request: CounterfactualRequest):
    """Run counterfactual reasoning: 'What would have happened if...?'

    Uses the three-step process: Abduction → Action → Prediction.
    Falls back to LLM-assisted reasoning when no SCM or data is available.
    """
    try:
        from src.services.counterfactual_engine import get_counterfactual_engine

        engine = get_counterfactual_engine()
        result = await engine.reason_from_text(
            query_text=request.query,
            context=request.context,
        )

        return CounterfactualResponse(
            factual_outcome=result.factual_outcome,
            counterfactual_outcome=result.counterfactual_outcome,
            causal_attribution=[
                attr.model_dump() if hasattr(attr, "model_dump") else attr
                for attr in (result.attributions or [])
            ],
            confidence=result.confidence,
            narrative=result.narrative,
            reasoning_steps=result.reasoning_steps,
        )
    except Exception as e:
        logger.error(f"Counterfactual reasoning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Counterfactual reasoning failed: {str(e)}")


@router.post("/counterfactual/compare", response_model=ScenarioComparisonResponse)
async def compare_counterfactual_scenarios(request: ScenarioComparisonRequest):
    """Compare multiple counterfactual scenarios to find the best intervention."""
    try:
        from src.services.counterfactual_engine import get_counterfactual_engine

        engine = get_counterfactual_engine()
        result = await engine.compare_scenarios(
            base_query=request.base_query,
            interventions=request.alternative_interventions,
            outcome_variable=request.outcome_variable,
            context=request.context,
        )

        return ScenarioComparisonResponse(
            scenarios=result.get("scenarios", []),
            best_scenario_index=result.get("best_index", 0),
            ranking_rationale=result.get("rationale", ""),
            outcome_range=result.get("outcome_range", (0.0, 0.0)),
        )
    except Exception as e:
        logger.error(f"Scenario comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/counterfactual/attribute", response_model=CausalAttributionResponse)
async def run_causal_attribution(request: CausalAttributionRequest):
    """Trace causes of an outcome via but-for causation tests."""
    try:
        from src.services.counterfactual_engine import get_counterfactual_engine

        engine = get_counterfactual_engine()
        result = await engine.attribute_causes(
            outcome_description=request.outcome_description,
            context=request.context,
        )

        return CausalAttributionResponse(
            outcome=request.outcome_description,
            attributions=result.get("attributions", []),
            but_for_tests=result.get("but_for_tests", []),
            narrative=result.get("narrative", ""),
        )
    except Exception as e:
        logger.error(f"Causal attribution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WORLD MODEL SIMULATION ENDPOINTS
# =============================================================================


@router.post("/simulate", response_model=WorldModelSimulationResponse)
async def simulate_world_model(request: WorldModelSimulationRequest):
    """Forward-simulate a causal world model with optional interventions.

    Given initial conditions and a causal graph, simulates how the system
    evolves over time. Supports do-calculus interventions (do(X=x)).
    """
    try:
        from src.services.causal_world_model import get_causal_world_model

        wm = get_causal_world_model()
        result = await wm.simulate_from_text(
            query=request.query,
            initial_conditions=request.initial_conditions,
            interventions=request.interventions,
            steps=request.steps,
            context=request.context,
        )

        return WorldModelSimulationResponse(
            trajectory=result.get("trajectory", []),
            variables=result.get("variables", []),
            interventions_applied=request.interventions,
            model_confidence=result.get("confidence", 0.0),
            interpretation=result.get("interpretation", ""),
        )
    except Exception as e:
        logger.error(f"World model simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEUROSYMBOLIC REASONING ENDPOINTS
# =============================================================================


@router.post("/neurosymbolic/reason", response_model=NeurosymbolicReasoningResponse)
async def neurosymbolic_reasoning(request: NeurosymbolicReasoningRequest):
    """Run neurosymbolic reasoning: tightly-coupled neural + symbolic loop.

    1. LLM extracts facts from query
    2. Forward-chaining derives new facts from rules
    3. Derived facts + gaps fed back to LLM
    4. LLM output validated against symbolic constraints
    5. Shortcut reasoning detection
    """
    try:
        from src.services.neurosymbolic_engine import get_neurosymbolic_engine

        engine = get_neurosymbolic_engine()
        result = await engine.reason(
            query=request.query,
            context=request.context,
            use_knowledge_graph=request.use_knowledge_graph,
            max_iterations=request.max_iterations,
        )

        return NeurosymbolicReasoningResponse(
            conclusion=result.conclusion,
            derived_facts=[
                f.model_dump() if hasattr(f, "model_dump") else f
                for f in (result.derived_facts or [])
            ],
            rule_chain=result.rule_chain or [],
            shortcut_warnings=result.shortcut_warnings or [],
            iterations=result.iterations,
            confidence=result.confidence,
            symbolic_grounding=[
                f.model_dump() if hasattr(f, "model_dump") else f
                for f in (result.grounding_facts or [])
            ],
        )
    except Exception as e:
        logger.error(f"Neurosymbolic reasoning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/neurosymbolic/validate")
async def validate_reasoning(
    claim: str,
    evidence: list[str] | None = None,
    context: dict[str, Any] | None = None,
):
    """Validate a claim against the symbolic knowledge base.

    Checks if a claim is logically derivable from known facts and rules.
    Detects reasoning shortcuts where conclusions skip required causal steps.
    """
    try:
        from src.services.neurosymbolic_engine import get_neurosymbolic_engine

        engine = get_neurosymbolic_engine()
        result = await engine.validate_claim(
            claim=claim,
            evidence=evidence or [],
            context=context or {},
        )

        return {
            "claim": claim,
            "is_valid": result.get("is_valid", False),
            "violations": result.get("violations", []),
            "shortcut_warnings": result.get("shortcut_warnings", []),
            "supporting_rules": result.get("supporting_rules", []),
            "confidence": result.get("confidence", 0.0),
        }
    except Exception as e:
        logger.error(f"Reasoning validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMBINED ENDPOINT — Full NeSy-Causal Pipeline
# =============================================================================


@router.get("/h-neuron/status")
async def h_neuron_status():
    """Get H-Neuron Sentinel status and configuration.

    Returns whether the mechanistic hallucination detection sentinel is
    enabled, its mode (proxy/mechanistic), thresholds, and active domains.
    """
    try:
        from src.services.h_neuron_interceptor import get_h_neuron_sentinel

        sentinel = get_h_neuron_sentinel()
        return sentinel.get_status()
    except Exception as e:
        return {
            "enabled": False,
            "mode": "unavailable",
            "error": str(e),
        }


@router.post("/h-neuron/assess")
async def h_neuron_assess(
    response_text: str = "",
    deepeval_hallucination_risk: float | None = None,
    domain_confidence: float | None = None,
    epistemic_uncertainty: float | None = None,
    reflection_count: int = 0,
):
    """Run H-Neuron hallucination risk assessment on given signals.

    In proxy mode, fuses available CARF signals (DeepEval scores,
    domain confidence, uncertainty) into a unified hallucination risk score.
    """
    try:
        from src.services.h_neuron_interceptor import get_h_neuron_sentinel

        sentinel = get_h_neuron_sentinel()
        result = sentinel.assess_hallucination_risk(
            response_text=response_text,
            deepeval_hallucination_risk=deepeval_hallucination_risk,
            domain_confidence=domain_confidence,
            epistemic_uncertainty=epistemic_uncertainty,
            reflection_count=reflection_count,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"H-Neuron assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/neurosymbolic")
async def retrieve_neurosymbolic_augmented(
    query: str,
    top_k: int = 5,
    domain_id: str | None = None,
    include_causal_context: bool = True,
    include_symbolic_facts: bool = True,
):
    """Neurosymbolic-augmented retrieval — highest contextual reliability.

    Combines vector similarity, graph-structural traversal, and symbolic
    knowledge base grounding for maximum epistemic context.
    """
    try:
        from src.services.rag_service import get_rag_service

        rag = get_rag_service()
        result = await rag.retrieve_neurosymbolic_augmented(
            query=query,
            top_k=top_k,
            domain_id=domain_id,
            include_causal_context=include_causal_context,
            include_symbolic_facts=include_symbolic_facts,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"NeSy-augmented retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-deep")
async def deep_analysis(
    query: str,
    context: dict[str, Any] | None = None,
    include_counterfactual: bool = True,
    include_neurosymbolic: bool = True,
    include_simulation: bool = False,
):
    """Run the full neurosymbolic-causal analysis pipeline.

    Combines:
    1. Standard CARF causal/bayesian analysis
    2. Counterfactual reasoning (what-if)
    3. Neurosymbolic validation (shortcut detection)
    4. Optional world model simulation

    Returns a unified deep analysis result.
    """
    results: dict[str, Any] = {"query": query}

    # 1. Run standard CARF pipeline
    try:
        from src.workflows.graph import run_carf

        carf_result = await run_carf(query, context)
        results["carf"] = {
            "domain": carf_result.cynefin_domain.value,
            "domain_confidence": carf_result.domain_confidence,
            "response": carf_result.final_response,
            "verdict": carf_result.guardian_verdict.value if carf_result.guardian_verdict else None,
            "confidence": carf_result.overall_confidence.value,
        }
        if carf_result.causal_evidence:
            results["carf"]["causal_evidence"] = carf_result.causal_evidence.model_dump()
        if carf_result.bayesian_evidence:
            results["carf"]["bayesian_evidence"] = carf_result.bayesian_evidence.model_dump()
    except Exception as e:
        logger.error(f"CARF pipeline failed: {e}", exc_info=True)
        results["carf"] = {"error": str(e)}

    # 2. Counterfactual reasoning
    if include_counterfactual:
        try:
            from src.services.counterfactual_engine import get_counterfactual_engine

            cf_engine = get_counterfactual_engine()
            cf_result = await cf_engine.reason_from_text(query, context or {})
            results["counterfactual"] = {
                "factual": cf_result.factual_outcome,
                "counterfactual": cf_result.counterfactual_outcome,
                "confidence": cf_result.confidence,
                "narrative": cf_result.narrative,
            }
        except Exception as e:
            logger.warning(f"Counterfactual reasoning failed: {e}")
            results["counterfactual"] = {"error": str(e)}

    # 3. Neurosymbolic validation
    if include_neurosymbolic:
        try:
            from src.services.neurosymbolic_engine import get_neurosymbolic_engine

            nesy_engine = get_neurosymbolic_engine()
            nesy_result = await nesy_engine.reason(query, context or {})
            results["neurosymbolic"] = {
                "conclusion": nesy_result.conclusion,
                "derived_facts_count": len(nesy_result.derived_facts or []),
                "shortcut_warnings": nesy_result.shortcut_warnings or [],
                "iterations": nesy_result.iterations,
                "confidence": nesy_result.confidence,
            }
        except Exception as e:
            logger.warning(f"Neurosymbolic reasoning failed: {e}")
            results["neurosymbolic"] = {"error": str(e)}

    # 4. World model simulation (optional)
    if include_simulation:
        try:
            from src.services.causal_world_model import get_causal_world_model

            wm = get_causal_world_model()
            sim_result = await wm.simulate_from_text(query, context=context or {})
            results["simulation"] = {
                "trajectory_length": len(sim_result.get("trajectory", [])),
                "variables": sim_result.get("variables", []),
                "confidence": sim_result.get("confidence", 0.0),
                "interpretation": sim_result.get("interpretation", ""),
            }
        except Exception as e:
            logger.warning(f"World model simulation failed: {e}")
            results["simulation"] = {"error": str(e)}

    return results
