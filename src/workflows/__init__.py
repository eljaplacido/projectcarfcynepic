# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Workflows module: LangGraph definitions.

Contains the StateGraph wiring and node implementations for the CARF cognitive mesh.
"""

try:
    from .graph import build_carf_graph, compile_carf_graph, get_carf_graph, run_carf
except ModuleNotFoundError:
    # Optional dependency boundary: allow importing router/guardian modules
    # in lightweight environments where LangGraph is not installed.
    build_carf_graph = None  # type: ignore[assignment]
    compile_carf_graph = None  # type: ignore[assignment]
    get_carf_graph = None  # type: ignore[assignment]
    run_carf = None  # type: ignore[assignment]
from .guardian import Guardian, guardian_node, get_guardian
from .router import CynefinRouter, cynefin_router_node, get_router

__all__ = [
    "build_carf_graph",
    "compile_carf_graph",
    "get_carf_graph",
    "run_carf",
    "Guardian",
    "guardian_node",
    "get_guardian",
    "CynefinRouter",
    "cynefin_router_node",
    "get_router",
]
