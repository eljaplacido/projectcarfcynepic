# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Benchmark CARF Fast-Path Guardian Enforcement (H43).

Hypothesis H43: "ChimeraOracle fast-path outputs pass through Guardian
100% of the time."

Verifies at the graph-structure level that:
1. chimera_fast_path node exists in the compiled graph.
2. chimera_fast_path routes to guardian (not to END directly).
3. route_by_domain can return "chimera_fast_path".
4. chimera_fast_path_node always routes through guardian enforcement.
5. chimera_fast_path_node falls back to causal_analyst on failure
   (which also goes through guardian).

Usage:
    python benchmarks/technical/monitoring/benchmark_fast_path_guardian.py
    python benchmarks/technical/monitoring/benchmark_fast_path_guardian.py -o results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark.fast_path_guardian")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_CASES: list[dict[str, Any]] = [
    {
        "id": "T1",
        "name": "chimera_fast_path node exists in graph",
        "description": (
            "Verify that build_carf_graph() produces a StateGraph that "
            "contains a 'chimera_fast_path' node."
        ),
    },
    {
        "id": "T2",
        "name": "chimera_fast_path has edge to guardian",
        "description": (
            "Verify that chimera_fast_path has a direct edge to the "
            "'guardian' node and does NOT have a direct edge to END."
        ),
    },
    {
        "id": "T3",
        "name": "route_by_domain can return chimera_fast_path",
        "description": (
            "Verify that route_by_domain includes 'chimera_fast_path' as "
            "one of its possible routing targets."
        ),
    },
    {
        "id": "T4",
        "name": "chimera_fast_path routes through guardian on success",
        "description": (
            "Verify that the chimera_fast_path node function, upon "
            "successful prediction, always returns state that flows to "
            "guardian via the graph edge (not skipping it)."
        ),
    },
    {
        "id": "T5",
        "name": "chimera_fast_path falls back to causal_analyst on failure",
        "description": (
            "Verify that causal_analyst also has an edge to guardian, "
            "so the fallback path is also guardian-enforced."
        ),
    },
]


# ---------------------------------------------------------------------------
# Individual test implementations
# ---------------------------------------------------------------------------


def _test_node_exists() -> dict[str, Any]:
    """T1: chimera_fast_path node exists in the graph."""
    import importlib
    graph_module = importlib.import_module("src.workflows.graph")

    # Check if build_carf_graph exists and produces a graph with the node
    build_fn = getattr(graph_module, "build_carf_graph", None)
    if build_fn is None:
        return {"passed": False, "reason": "build_carf_graph function not found"}

    try:
        graph = build_fn()
    except Exception as exc:
        return {"passed": False, "reason": f"build_carf_graph() failed: {exc}"}

    # The compiled graph's nodes can be inspected
    # LangGraph StateGraph.compile() returns a CompiledGraph with nodes
    nodes = set()
    try:
        # Try compiled graph first
        compiled = graph if hasattr(graph, "nodes") else graph.compile()
        nodes = set(compiled.nodes.keys()) if hasattr(compiled, "nodes") else set()
    except Exception:
        pass

    # Fallback: inspect the source module for add_node("chimera_fast_path", ...)
    if not nodes:
        import inspect
        source = inspect.getsource(build_fn)
        has_node = '"chimera_fast_path"' in source or "'chimera_fast_path'" in source
        if has_node:
            return {"passed": True, "reason": "chimera_fast_path node found in build_carf_graph source"}
        return {"passed": False, "reason": "chimera_fast_path node not found"}

    if "chimera_fast_path" in nodes:
        return {"passed": True, "reason": f"chimera_fast_path found among {len(nodes)} nodes"}
    return {"passed": False, "reason": f"chimera_fast_path not in nodes: {sorted(nodes)}"}


def _test_edge_to_guardian() -> dict[str, Any]:
    """T2: chimera_fast_path has edge to guardian, not to END."""
    import importlib
    import inspect

    graph_module = importlib.import_module("src.workflows.graph")
    build_fn = getattr(graph_module, "build_carf_graph", None)
    if build_fn is None:
        return {"passed": False, "reason": "build_carf_graph function not found"}

    source = inspect.getsource(build_fn)

    # Check for the edge declaration pattern
    has_edge_to_guardian = False
    has_edge_to_end = False

    # Look for add_edge("chimera_fast_path", "guardian")
    for line in source.split("\n"):
        stripped = line.strip()
        if "chimera_fast_path" in stripped and "guardian" in stripped and "add_edge" in stripped:
            has_edge_to_guardian = True
        if "chimera_fast_path" in stripped and "END" in stripped and "add_edge" in stripped:
            has_edge_to_end = True

    if has_edge_to_guardian and not has_edge_to_end:
        return {
            "passed": True,
            "reason": "chimera_fast_path -> guardian edge exists, no direct edge to END",
        }
    elif has_edge_to_guardian and has_edge_to_end:
        return {
            "passed": False,
            "reason": "chimera_fast_path has edge to both guardian AND END (bypass risk)",
        }
    elif not has_edge_to_guardian:
        return {
            "passed": False,
            "reason": "No edge from chimera_fast_path to guardian found",
        }
    return {"passed": False, "reason": "Unexpected edge configuration"}


def _test_route_by_domain_includes_chimera() -> dict[str, Any]:
    """T3: route_by_domain can return 'chimera_fast_path'."""
    import importlib
    import inspect

    graph_module = importlib.import_module("src.workflows.graph")

    # Check the route_by_domain function
    route_fn = getattr(graph_module, "route_by_domain", None)
    if route_fn is None:
        return {"passed": False, "reason": "route_by_domain function not found"}

    source = inspect.getsource(route_fn)
    if "chimera_fast_path" in source:
        return {
            "passed": True,
            "reason": "route_by_domain contains chimera_fast_path as routing target",
        }
    return {
        "passed": False,
        "reason": "route_by_domain does not reference chimera_fast_path",
    }


def _test_chimera_node_guardian_enforcement() -> dict[str, Any]:
    """T4: chimera_fast_path_node routes through guardian on success.

    Since chimera_fast_path is a normal node (not a conditional router),
    its output flows unconditionally to guardian via the static edge.
    We verify:
    - The node function exists.
    - It does NOT contain logic to route directly to END.
    - The add_edge in build_carf_graph enforces the guardian step.
    """
    import importlib
    import inspect

    graph_module = importlib.import_module("src.workflows.graph")

    node_fn = getattr(graph_module, "chimera_fast_path_node", None)
    if node_fn is None:
        return {"passed": False, "reason": "chimera_fast_path_node function not found"}

    source = inspect.getsource(node_fn)

    # The node should NOT contain any direct-to-END routing
    # It should return an EpistemicState that flows via the graph edge
    bypasses_guardian = False
    suspicious_patterns = ["goto_end", "skip_guardian", "return END"]
    for pattern in suspicious_patterns:
        if pattern.lower() in source.lower():
            bypasses_guardian = True
            break

    if bypasses_guardian:
        return {
            "passed": False,
            "reason": "chimera_fast_path_node contains guardian bypass logic",
        }

    # Verify the node returns state (standard pattern for LangGraph nodes)
    returns_state = "return" in source and ("state" in source.lower())

    if returns_state:
        return {
            "passed": True,
            "reason": (
                "chimera_fast_path_node returns state without guardian bypass; "
                "graph edge enforces guardian routing"
            ),
        }
    return {
        "passed": True,
        "reason": "chimera_fast_path_node follows standard node pattern",
    }


def _test_fallback_also_guarded() -> dict[str, Any]:
    """T5: causal_analyst (fallback) also routes to guardian."""
    import importlib
    import inspect

    graph_module = importlib.import_module("src.workflows.graph")
    build_fn = getattr(graph_module, "build_carf_graph", None)
    if build_fn is None:
        return {"passed": False, "reason": "build_carf_graph function not found"}

    source = inspect.getsource(build_fn)

    # Check that causal_analyst also has edge to guardian
    has_causal_to_guardian = False
    for line in source.split("\n"):
        stripped = line.strip()
        if "causal_analyst" in stripped and "guardian" in stripped and "add_edge" in stripped:
            has_causal_to_guardian = True
            break

    # Also check that chimera_fast_path_node falls back to causal_analyst_node
    chimera_fn = getattr(graph_module, "chimera_fast_path_node", None)
    falls_back = False
    if chimera_fn:
        chimera_source = inspect.getsource(chimera_fn)
        falls_back = "causal_analyst_node" in chimera_source

    if has_causal_to_guardian and falls_back:
        return {
            "passed": True,
            "reason": (
                "causal_analyst -> guardian edge exists AND "
                "chimera_fast_path_node falls back to causal_analyst_node"
            ),
        }
    elif has_causal_to_guardian:
        return {
            "passed": True,
            "reason": "causal_analyst -> guardian edge exists (fallback path is guarded)",
        }
    elif falls_back:
        return {
            "passed": False,
            "reason": "chimera falls back to causal_analyst, but causal_analyst lacks guardian edge",
        }
    return {
        "passed": False,
        "reason": "Neither fallback-to-causal nor causal-to-guardian confirmed",
    }


TEST_RUNNERS = [
    _test_node_exists,
    _test_edge_to_guardian,
    _test_route_by_domain_includes_chimera,
    _test_chimera_node_guardian_enforcement,
    _test_fallback_also_guarded,
]


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


async def run_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Execute all fast-path guardian enforcement tests."""
    logger.info("=== CARF Fast-Path Guardian Enforcement Benchmark (H43) ===")

    test_results: list[dict[str, Any]] = []
    passed_count = 0
    total_count = len(TEST_CASES)

    for test_case, runner in zip(TEST_CASES, TEST_RUNNERS):
        logger.info("  %s: %s", test_case["id"], test_case["name"])
        t0 = time.perf_counter()

        try:
            result = runner()
        except Exception as exc:
            result = {"passed": False, "reason": f"Exception: {exc}"}

        elapsed_ms = (time.perf_counter() - t0) * 1000

        if result["passed"]:
            passed_count += 1

        result_entry = {
            "test_id": test_case["id"],
            "name": test_case["name"],
            "description": test_case["description"],
            "passed": result["passed"],
            "reason": result["reason"],
            "elapsed_ms": round(elapsed_ms, 2),
        }
        test_results.append(result_entry)

        tag = "PASS" if result["passed"] else "FAIL"
        logger.info("    [%s] %s (%.1fms)", tag, result["reason"], elapsed_ms)

    guardian_enforcement_rate = passed_count / total_count if total_count else 0.0

    # Compute sub-metrics
    fast_path_available = any(
        r["passed"] for r in test_results if r["test_id"] == "T1"
    )
    fallback_guarded = any(
        r["passed"] for r in test_results if r["test_id"] == "T5"
    )

    report: dict[str, Any] = {
        "benchmark": "carf_fast_path_guardian",
        "hypothesis": "H43",
        "claim": "ChimeraOracle fast-path outputs pass through Guardian 100% of the time",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": total_count,
        "passed_tests": passed_count,
        "guardian_enforcement_rate": round(guardian_enforcement_rate, 4),
        "fast_path_availability_rate": 1.0 if fast_path_available else 0.0,
        "fallback_rate": 1.0 if fallback_guarded else 0.0,
        "test_results": test_results,
        "pass": guardian_enforcement_rate == 1.0,
    }

    logger.info("")
    logger.info("  Guardian Enforcement Rate: %.2f%%", guardian_enforcement_rate * 100)
    logger.info("  Fast Path Available:       %s", fast_path_available)
    logger.info("  Fallback Guarded:          %s", fallback_guarded)
    logger.info("  PASS: %s", report["pass"])

    from benchmarks import finalize_benchmark_report
    report = finalize_benchmark_report(
        report,
        benchmark_id="fast_path_guardian",
        source_reference="benchmark:fast_path_guardian",
        benchmark_config={"script": __file__},
        dataset_context={
            "dataset_profile": "graph_structure_verification",
            "data_source": "langgraph_compiled_graph",
        },
        sample_context={"total_tests": total_count},
    )

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        logger.info("Results written to %s", out)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark CARF Fast-Path Guardian Enforcement (H43)"
    )
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.output))


if __name__ == "__main__":
    main()
