"""Tests for the CARF Library API."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def test_mode():
    """Ensure CARF_TEST_MODE is set."""
    with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
        yield


class TestClassifyQuery:
    """Tests for classify_query."""

    @pytest.mark.asyncio
    async def test_classify_query_returns_dict(self):
        """classify_query should return dict with domain and confidence."""
        from src.api.library import classify_query

        result = await classify_query("What is the current USD exchange rate?")
        assert isinstance(result, dict)
        assert "domain" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)


class TestRunCausal:
    """Tests for run_causal."""

    @pytest.mark.asyncio
    async def test_run_causal_returns_dict(self):
        """run_causal should return dict with effect estimate."""
        from src.api.library import run_causal

        result = await run_causal(
            query="Does training improve productivity?",
            context={"causal_estimation": {
                "treatment": "treatment",
                "outcome": "outcome",
                "covariates": ["X1"],
                "data": [
                    {"treatment": 1, "outcome": 50, "X1": 0.5},
                    {"treatment": 0, "outcome": 40, "X1": 0.3},
                ] * 50,
            }},
        )
        assert isinstance(result, dict)
        assert "effect_estimate" in result or "error" in result
        assert "response" in result


class TestCheckGuardian:
    """Tests for check_guardian."""

    @pytest.mark.asyncio
    async def test_check_guardian_returns_dict(self):
        """check_guardian should return dict with verdict."""
        from src.api.library import check_guardian

        result = await check_guardian(
            proposed_action={"action_type": "lookup", "description": "Simple lookup"},
            context={},
        )
        assert isinstance(result, dict)
        assert "verdict" in result


class TestRunPipeline:
    """Tests for run_pipeline."""

    @pytest.mark.asyncio
    async def test_run_pipeline_returns_dict(self):
        """run_pipeline should return complete result dict."""
        from src.api.library import run_pipeline

        result = await run_pipeline("What is 2 + 2?")
        assert isinstance(result, dict)
        assert "domain" in result
        assert "domain_confidence" in result
        assert "response" in result
        assert "session_id" in result
        assert "reasoning_steps" in result


class TestQueryMemory:
    """Tests for query_memory."""

    @pytest.mark.asyncio
    async def test_query_memory_returns_dict(self):
        """query_memory should return dict with matches."""
        from src.api.library import query_memory
        from src.services.experience_buffer import get_experience_buffer

        # Ensure a clean buffer state
        buffer = get_experience_buffer()
        buffer.clear()

        result = await query_memory("test query")
        assert isinstance(result, dict)
        assert "matches" in result
        assert "buffer_size" in result
        assert isinstance(result["matches"], list)
