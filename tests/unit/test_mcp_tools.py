"""Unit tests for MCP tool wrappers.

Tests tool function signatures, guardian evaluation, and oracle/router tools
using mocks to avoid requiring LLM or model dependencies.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPToolImports:
    """Verify all MCP tool modules import successfully."""

    def test_import_guardian_tools(self):
        from src.mcp.tools import guardian

        assert callable(guardian.guardian_evaluate)
        assert callable(guardian.guardian_list_policies)
        assert callable(guardian.guardian_add_rule)
        assert callable(guardian.guardian_status)

    def test_import_causal_tools(self):
        from src.mcp.tools import causal

        assert callable(causal.causal_discover)
        assert callable(causal.causal_analyze)
        assert callable(causal.causal_sensitivity)

    def test_import_bayesian_tools(self):
        from src.mcp.tools import bayesian

        assert callable(bayesian.bayesian_explore)
        assert callable(bayesian.bayesian_run_inference)

    def test_import_oracle_tools(self):
        from src.mcp.tools import oracle

        assert callable(oracle.oracle_predict)
        assert callable(oracle.oracle_train)
        assert callable(oracle.oracle_list_models)
        assert callable(oracle.oracle_model_info)

    def test_import_router_tools(self):
        from src.mcp.tools import router

        assert callable(router.cynefin_classify)
        assert callable(router.cynefin_config)

    def test_total_tool_count(self):
        """Verify we have exactly 15 tools registered in the MCP server."""
        from src.mcp.server import mcp

        tools = mcp._tool_manager._tools
        assert len(tools) == 15, f"Expected 15 tools, got {len(tools)}: {list(tools.keys())}"


class TestMCPServerModule:
    """Verify the MCP server module loads correctly."""

    def test_server_import(self):
        from src.mcp.server import mcp

        assert mcp.name == "CARF CYNEPIC"

    def test_server_has_main(self):
        from src.mcp.server import main

        assert callable(main)


class TestGuardianTools:
    """Test Guardian MCP tools with live CSL service."""

    @pytest.fixture(autouse=True)
    def _reset_csl_singleton(self, monkeypatch):
        """Ensure CSL service is freshly initialized for each test."""
        monkeypatch.setenv("CSL_ENABLED", "true")
        import src.services.csl_policy_service as csl_mod
        csl_mod._csl_service = None
        yield
        csl_mod._csl_service = None

    @pytest.mark.asyncio
    async def test_guardian_status(self):
        from src.mcp.tools.guardian import guardian_status

        result = await guardian_status()
        assert "enabled" in result
        assert "engine" in result
        assert "policy_count" in result
        assert "rule_count" in result
        assert result["policy_count"] >= 4

    @pytest.mark.asyncio
    async def test_guardian_list_policies(self):
        from src.mcp.tools.guardian import guardian_list_policies

        policies = await guardian_list_policies()
        assert isinstance(policies, list)
        assert len(policies) >= 4
        names = {p["name"] for p in policies}
        assert "budget_limits" in names
        assert "action_gates" in names
        for policy in policies:
            assert "name" in policy
            assert "rules" in policy
            assert "rule_count" in policy

    @pytest.mark.asyncio
    async def test_guardian_evaluate_allow(self):
        from src.mcp.tools.guardian import guardian_evaluate

        # Low-risk context should be allowed
        result = await guardian_evaluate({
            "user": {"role": "senior"},
            "action": {"type": "view", "amount": 10},
            "domain": {"type": "Clear", "confidence": 0.95},
        })
        assert "allow" in result
        assert "rules_checked" in result
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_guardian_add_rule(self):
        from src.mcp.tools.guardian import guardian_add_rule

        result = await guardian_add_rule(
            policy_name="budget_limits",
            rule_name="test_mcp_rule",
            condition={"user.role": "intern"},
            constraint={"action.amount": {"op": "<=", "value": 50}},
            message="Test MCP rule",
        )
        assert result["status"] == "added"
        assert result["policy"] == "budget_limits"

    @pytest.mark.asyncio
    async def test_guardian_add_rule_missing_policy(self):
        from src.mcp.tools.guardian import guardian_add_rule

        result = await guardian_add_rule(
            policy_name="nonexistent_policy",
            rule_name="test_rule",
            condition={},
            constraint={},
            message="test",
        )
        assert result["status"] == "error"


class TestOracleTools:
    """Test Oracle MCP tools."""

    @pytest.mark.asyncio
    async def test_oracle_list_models_empty(self):
        from src.mcp.tools.oracle import oracle_list_models

        models = await oracle_list_models()
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_oracle_model_info_missing(self):
        from src.mcp.tools.oracle import oracle_model_info

        result = await oracle_model_info("nonexistent_scenario")
        assert "error" in result


class TestRouterTools:
    """Test Router MCP tools."""

    @pytest.mark.asyncio
    async def test_cynefin_config(self):
        from src.mcp.tools.router import cynefin_config

        config = await cynefin_config()
        assert isinstance(config, dict)
        assert "confidence_threshold" in config

    @pytest.mark.asyncio
    async def test_cynefin_classify_signature(self):
        """Verify classify tool has expected parameters."""
        from src.mcp.tools.router import cynefin_classify

        sig = inspect.signature(cynefin_classify)
        params = list(sig.parameters.keys())
        assert "query" in params
        assert "context" in params
