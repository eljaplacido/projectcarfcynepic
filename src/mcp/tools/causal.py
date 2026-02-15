"""Causal inference tools for MCP.

Wraps CausalInferenceEngine to expose causal discovery, full analysis
pipeline, and sensitivity testing to any MCP-connected AI agent.
"""

from __future__ import annotations

from typing import Any

from src.mcp.server import mcp
from src.services.causal import get_causal_engine


@mcp.tool()
async def causal_discover(
    query: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Discover causal structure from a problem description.

    Uses LLM-assisted causal discovery to propose a DAG with treatment,
    outcome, confounders, and causal edges.

    Args:
        query: Natural language causal question (e.g. "What causes customer churn?")
        context: Optional additional context (domain knowledge, data description)
    """
    engine = get_causal_engine()
    hypothesis, graph = await engine.discover_causal_structure(query, context)
    return {
        "hypothesis": {
            "treatment": hypothesis.treatment,
            "outcome": hypothesis.outcome,
            "mechanism": hypothesis.mechanism,
            "confounders": hypothesis.confounders,
            "confidence": hypothesis.confidence,
        },
        "graph": {
            "nodes": [
                {
                    "name": n.name,
                    "role": n.role,
                    "description": n.description,
                    "variable_type": n.variable_type,
                }
                for n in graph.nodes
            ],
            "edges": [[e[0], e[1]] for e in graph.edges],
            "adjacency": graph.to_adjacency_list(),
        },
    }


@mcp.tool()
async def causal_analyze(
    query: str,
    context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Full causal analysis pipeline: discover DAG, estimate effects, run refutations.

    This is the primary causal inference tool. It discovers causal structure,
    estimates treatment effects using DoWhy, and validates via refutation tests.

    Args:
        query: The causal question to analyze
        context: Additional context (must include data for estimation)
        session_id: Optional session ID for tracking
    """
    engine = get_causal_engine()
    result, graph = await engine.analyze(query, context, session_id=session_id)
    return {
        "effect": result.effect,
        "p_value": result.p_value,
        "confidence_interval": list(result.confidence_interval) if result.confidence_interval else None,
        "method": result.method,
        "interpretation": result.interpretation,
        "refutations": {
            "passed": result.refutations_passed,
            "total": result.refutations_total,
            "results": [
                {
                    "test": r.get("test_name", "unknown"),
                    "passed": r.get("passed", False),
                    "p_value": r.get("p_value"),
                }
                for r in result.refutation_results
            ],
        },
        "graph_nodes": len(graph.nodes),
        "graph_edges": len(graph.edges),
    }


@mcp.tool()
async def causal_sensitivity(
    treatment: str,
    outcome: str,
    confounders: list[str],
    data_csv_path: str,
) -> dict[str, Any]:
    """Run additional sensitivity/refutation tests on causal estimates.

    Runs placebo treatment, random common cause, and data subset validation
    tests using DoWhy. Requires a CSV file path with the analysis data.

    Args:
        treatment: Name of treatment variable column
        outcome: Name of outcome variable column
        confounders: List of confounder variable column names
        data_csv_path: Path to CSV file containing the data
    """
    import pandas as pd

    engine = get_causal_engine()
    data = pd.read_csv(data_csv_path)
    results = engine.run_sensitivity_analysis(
        data=data,
        treatment=treatment,
        outcome=outcome,
        confounders=confounders,
    )
    return results
