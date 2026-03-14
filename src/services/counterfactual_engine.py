# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Counterfactual Reasoning Engine — Phase 17.

Implements Level-3 counterfactual reasoning (Pearl's Ladder of Causation):
- "What would Y have been if X had been x' instead of x?"
- Three-step process: Abduction → Action → Prediction
- Scenario comparison and causal attribution
- LLM-assisted fallback when no SCM/data available

Research basis: Causal Cartographer [14], Beyond Generative AI [5],
Physical Grounding [6], Think Before You Simulate [34], CausalARC [10].
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.counterfactual")


# =============================================================================
# DATA MODELS
# =============================================================================


class CounterfactualQuery(BaseModel):
    """A structured counterfactual question."""

    factual_description: str = Field(default="", description="What actually happened")
    intervention_variable: str = Field(default="", description="What variable to change")
    intervention_value: str = Field(default="", description="What value to set it to")
    target_variable: str = Field(default="", description="What outcome to predict")
    context: dict[str, Any] = Field(default_factory=dict)


class CausalAttributionItem(BaseModel):
    """A single causal attribution."""

    cause: str
    importance: float = Field(default=0.0, ge=0.0, le=1.0)
    but_for_result: bool = Field(
        default=False, description="Would outcome change without this cause?"
    )
    description: str = Field(default="")


class CounterfactualResult(BaseModel):
    """Result of counterfactual reasoning."""

    query_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    factual_outcome: str = Field(default="")
    counterfactual_outcome: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    narrative: str = Field(default="")
    reasoning_steps: list[str] = Field(default_factory=list)
    attributions: list[CausalAttributionItem] = Field(default_factory=list)
    method: str = Field(default="llm_assisted", description="scm or llm_assisted")


# =============================================================================
# COUNTERFACTUAL ENGINE
# =============================================================================


class CounterfactualEngine:
    """Counterfactual reasoning engine.

    Supports both SCM-based (when data/model available) and LLM-assisted
    (always available) counterfactual reasoning.
    """

    def __init__(self):
        self._cache: dict[str, CounterfactualResult] = {}

    async def reason_from_text(
        self,
        query_text: str,
        context: dict[str, Any] | None = None,
    ) -> CounterfactualResult:
        """Run counterfactual reasoning from a natural language question.

        1. Parse the question into a structured CounterfactualQuery
        2. Try SCM-based reasoning if data/model available
        3. Fall back to LLM-assisted reasoning
        """
        context = context or {}
        steps: list[str] = []

        # Step 1: Parse the counterfactual question
        steps.append("Parsing counterfactual question")
        cf_query = await self._parse_query(query_text, context)
        steps.append(f"Identified intervention on '{cf_query.intervention_variable}' "
                      f"targeting '{cf_query.target_variable}'")

        # Step 2: Try SCM-based counterfactual
        data = context.get("data") or context.get("benchmark_data")
        if data and isinstance(data, list) and len(data) > 5:
            try:
                result = await self._scm_counterfactual(cf_query, data, steps)
                if result.confidence > 0.3:
                    self._cache[result.query_id] = result
                    return result
            except Exception as e:
                steps.append(f"SCM counterfactual failed: {e}, falling back to LLM")
                logger.debug("SCM counterfactual failed: %s", e)

        # Step 3: LLM-assisted counterfactual
        steps.append("Using LLM-assisted counterfactual reasoning")
        result = await self._llm_counterfactual(query_text, cf_query, context, steps)
        self._cache[result.query_id] = result
        return result

    async def _parse_query(
        self, query_text: str, context: dict[str, Any]
    ) -> CounterfactualQuery:
        """Parse a natural language counterfactual into structured form."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()
        prompt = f"""Parse this counterfactual question into structured components.

Question: {query_text}

Return a JSON object with:
- "factual_description": what actually happened (string)
- "intervention_variable": what variable the user wants to change (string)
- "intervention_value": what value they want to set it to (string)
- "target_variable": what outcome they want to predict (string)

Return ONLY valid JSON, no markdown fencing."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)
            return CounterfactualQuery(
                factual_description=parsed.get("factual_description", query_text),
                intervention_variable=parsed.get("intervention_variable", "unknown"),
                intervention_value=parsed.get("intervention_value", "unknown"),
                target_variable=parsed.get("target_variable", "unknown"),
                context=context,
            )
        except Exception as e:
            logger.warning("Failed to parse counterfactual query: %s", e)
            return CounterfactualQuery(
                factual_description=query_text,
                context=context,
            )

    async def _scm_counterfactual(
        self,
        cf_query: CounterfactualQuery,
        data: list[dict],
        steps: list[str],
    ) -> CounterfactualResult:
        """Run counterfactual reasoning using a Structural Causal Model."""
        from src.services.causal import get_causal_engine
        from src.services.causal_world_model import CausalWorldModel

        steps.append("Building SCM from data and causal graph")

        # Discover causal structure
        engine = get_causal_engine()
        hypothesis, graph = await engine.discover_causal_structure(
            cf_query.factual_description, cf_query.context
        )

        # Learn world model
        model = CausalWorldModel.learn_from_data(data, graph)
        steps.append(f"Learned SCM with {len(model.equations)} equations")

        # Compute average factual state from data
        factual_state: dict[str, float] = {}
        for var in model.variables:
            values = [obs.get(var, 0.0) for obs in data if var in obs]
            if values:
                factual_state[var] = sum(values) / len(values)

        # Parse intervention value
        try:
            intervention_val = float(cf_query.intervention_value)
        except (ValueError, TypeError):
            intervention_val = factual_state.get(cf_query.intervention_variable, 0.0) * 0.8

        # Run counterfactual
        intervention = {cf_query.intervention_variable: intervention_val}
        cf_result = model.counterfactual(factual_state, intervention)
        steps.append("Completed Abduction → Action → Prediction")

        # Extract target outcome
        target = cf_query.target_variable
        factual_val = cf_result.factual_state.get(target, 0.0)
        cf_val = cf_result.counterfactual_state.get(target, 0.0)
        diff = cf_val - factual_val

        # Compute attributions
        attributions = []
        for var, d in cf_result.differences.items():
            if var != target and abs(d) > 0.001:
                attributions.append(CausalAttributionItem(
                    cause=var,
                    importance=min(abs(d) / (abs(diff) + 1e-9), 1.0),
                    but_for_result=abs(d) > 0.01,
                    description=f"{var} changed by {d:+.3f}",
                ))

        attributions.sort(key=lambda a: a.importance, reverse=True)

        return CounterfactualResult(
            factual_outcome=f"{target} = {factual_val:.3f}",
            counterfactual_outcome=f"{target} = {cf_val:.3f} (change: {diff:+.3f})",
            confidence=0.7,
            narrative=(
                f"If {cf_query.intervention_variable} had been {intervention_val} "
                f"instead of {factual_state.get(cf_query.intervention_variable, '?')}, "
                f"then {target} would have been {cf_val:.3f} instead of {factual_val:.3f} "
                f"(a change of {diff:+.3f})."
            ),
            reasoning_steps=steps,
            attributions=attributions,
            method="scm",
        )

    async def _llm_counterfactual(
        self,
        query_text: str,
        cf_query: CounterfactualQuery,
        context: dict[str, Any],
        steps: list[str],
    ) -> CounterfactualResult:
        """LLM-assisted counterfactual reasoning when no SCM available."""
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        prompt = f"""You are a causal reasoning expert performing counterfactual analysis.

Question: {query_text}

Structured query:
- Factual: {cf_query.factual_description}
- Intervention: Change {cf_query.intervention_variable} to {cf_query.intervention_value}
- Target: Predict {cf_query.target_variable}

Perform Pearl's three-step counterfactual reasoning:
1. ABDUCTION: What are the background conditions that led to the factual outcome?
2. ACTION: What changes when we apply the intervention?
3. PREDICTION: What would the outcome be under the modified model?

Return a JSON object with:
- "factual_outcome": string describing what actually happened
- "counterfactual_outcome": string describing what would have happened
- "reasoning_steps": list of strings (one per reasoning step)
- "attributions": list of objects with "cause", "importance" (0-1), "but_for_result" (bool), "description"
- "narrative": 2-3 sentence explanation
- "confidence": float 0-1

Return ONLY valid JSON, no markdown fencing."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)

            llm_steps = parsed.get("reasoning_steps", [])
            steps.extend(llm_steps)

            attributions = [
                CausalAttributionItem(**attr)
                for attr in parsed.get("attributions", [])
            ]

            return CounterfactualResult(
                factual_outcome=parsed.get("factual_outcome", "Unknown"),
                counterfactual_outcome=parsed.get("counterfactual_outcome", "Unknown"),
                confidence=min(parsed.get("confidence", 0.5), 0.6),  # Cap LLM confidence
                narrative=parsed.get("narrative", ""),
                reasoning_steps=steps,
                attributions=attributions,
                method="llm_assisted",
            )
        except Exception as e:
            logger.error("LLM counterfactual failed: %s", e)
            return CounterfactualResult(
                factual_outcome="Analysis failed",
                counterfactual_outcome="Could not determine",
                confidence=0.0,
                narrative=f"Counterfactual reasoning failed: {str(e)}",
                reasoning_steps=steps,
                method="llm_assisted",
            )

    async def compare_scenarios(
        self,
        base_query: str,
        interventions: list[dict[str, float]],
        outcome_variable: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compare multiple counterfactual scenarios.

        Evaluates each intervention set and ranks by outcome.
        """
        context = context or {}
        scenarios: list[dict[str, Any]] = []

        for i, intervention in enumerate(interventions):
            intervention_desc = ", ".join(f"{k}={v}" for k, v in intervention.items())
            query = (
                f"{base_query} What would happen to {outcome_variable} "
                f"if we set {intervention_desc}?"
            )

            try:
                result = await self.reason_from_text(query, context)
                scenarios.append({
                    "index": i,
                    "intervention": intervention,
                    "factual": result.factual_outcome,
                    "counterfactual": result.counterfactual_outcome,
                    "confidence": result.confidence,
                    "narrative": result.narrative,
                })
            except Exception as e:
                scenarios.append({
                    "index": i,
                    "intervention": intervention,
                    "error": str(e),
                    "confidence": 0.0,
                })

        # Rank by confidence (higher is better scenario analysis)
        best_idx = max(range(len(scenarios)), key=lambda i: scenarios[i].get("confidence", 0))

        return {
            "scenarios": scenarios,
            "best_index": best_idx,
            "rationale": (
                f"Scenario {best_idx} has the highest analysis confidence "
                f"({scenarios[best_idx].get('confidence', 0):.0%})."
            ),
            "outcome_range": (0.0, 1.0),  # Placeholder
        }

    async def attribute_causes(
        self,
        outcome_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Causal attribution: identify contributing causes for an outcome.

        Uses but-for causation test: would the outcome have occurred
        but for this cause?
        """
        context = context or {}
        from langchain_core.messages import HumanMessage
        from src.core.llm import get_llm

        llm = get_llm()

        prompt = f"""You are a causal reasoning expert. Analyze the causes of this outcome.

Outcome: {outcome_description}

For each cause:
1. Identify it
2. Rate its importance (0-1)
3. Apply the but-for test: would the outcome have occurred WITHOUT this cause?
4. Describe the causal mechanism

Return a JSON object with:
- "attributions": list of {{"cause": str, "importance": float, "but_for_result": bool, "description": str}}
- "but_for_tests": list of {{"cause": str, "without_cause": str, "outcome_changes": bool}}
- "narrative": 2-3 sentence causal explanation

Return ONLY valid JSON, no markdown fencing."""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception as e:
            logger.error("Causal attribution failed: %s", e)
            return {
                "attributions": [],
                "but_for_tests": [],
                "narrative": f"Attribution analysis failed: {str(e)}",
            }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: CounterfactualEngine | None = None


def get_counterfactual_engine() -> CounterfactualEngine:
    """Get the singleton CounterfactualEngine."""
    global _engine
    if _engine is None:
        _engine = CounterfactualEngine()
    return _engine
