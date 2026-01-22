"""Tests for src/core/llm.py."""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.core.llm import (
    _FakeLLMResponse,
    _FakeChatModel,
    LLMProvider,
    LLMConfig,
    get_llm_config,
    get_chat_model,
    get_router_model,
    get_analyst_model,
    get_explorer_model,
    PROVIDER_CONFIGS,
)


class TestFakeLLMResponse:
    """Tests for _FakeLLMResponse class."""

    def test_stores_content(self):
        """Test response stores content."""
        response = _FakeLLMResponse("Test content")
        assert response.content == "Test content"

    def test_empty_content(self):
        """Test response with empty content."""
        response = _FakeLLMResponse("")
        assert response.content == ""


class TestFakeChatModel:
    """Tests for _FakeChatModel class."""

    def test_initialization(self):
        """Test model initialization with purpose."""
        model = _FakeChatModel(purpose="router")
        assert model.purpose == "router"

    def test_router_purpose_response(self):
        """Test router purpose generates domain classification."""
        model = _FakeChatModel(purpose="router")

        class FakeMessage:
            content = "What domain is this?"

        response = model.invoke([FakeMessage()])

        assert "domain" in response.content.lower()
        assert "Clear" in response.content

    def test_causal_analyst_discovery_response(self):
        """Test causal analyst generates discovery response."""
        model = _FakeChatModel(purpose="causal_analyst")

        class FakeMessage:
            content = "Discover causal structure for pricing"

        response = model.invoke([FakeMessage()])

        assert "treatment" in response.content
        assert "outcome" in response.content

    def test_causal_analyst_hypothesis_response(self):
        """Test causal analyst generates hypothesis analysis response."""
        model = _FakeChatModel(purpose="causal_analyst")

        class FakeMessage:
            content = "Analyze this causal hypothesis"

        response = model.invoke([FakeMessage()])

        assert "interpretation" in response.content
        assert "causal_claim_supported" in response.content

    def test_bayesian_explorer_prior_response(self):
        """Test bayesian explorer generates prior response."""
        model = _FakeChatModel(purpose="bayesian_explorer")

        class FakeMessage:
            content = "Establish priors for market analysis"

        response = model.invoke([FakeMessage()])

        assert "hypotheses" in response.content
        assert "overall_uncertainty" in response.content

    def test_bayesian_explorer_probe_response(self):
        """Test bayesian explorer generates probe design response."""
        model = _FakeChatModel(purpose="bayesian_explorer")

        class FakeMessage:
            content = "Design probes for uncertainty reduction"

        response = model.invoke([FakeMessage()])

        assert "probes" in response.content
        assert "probe_id" in response.content

    def test_general_purpose_response(self):
        """Test general purpose generates default response."""
        model = _FakeChatModel(purpose="general")

        class FakeMessage:
            content = "Generic query"

        response = model.invoke([FakeMessage()])

        assert "test-mode stub" in response.content

    @pytest.mark.asyncio
    async def test_async_invoke(self):
        """Test async invoke method."""
        model = _FakeChatModel(purpose="router")

        class FakeMessage:
            content = "Test async"

        response = await model.ainvoke([FakeMessage()])

        assert response.content is not None
        assert "domain" in response.content.lower()


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_deepseek_value(self):
        """Test DeepSeek provider value."""
        assert LLMProvider.DEEPSEEK.value == "deepseek"

    def test_openai_value(self):
        """Test OpenAI provider value."""
        assert LLMProvider.OPENAI.value == "openai"


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LLMConfig()
        assert config.provider == LLMProvider.DEEPSEEK
        assert config.model == "deepseek-chat"
        assert config.temperature == 0.1
        assert config.max_tokens == 4096

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.7,
            max_tokens=2048,
            api_key="test-key",
        )
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.api_key == "test-key"

    def test_temperature_bounds(self):
        """Test temperature validation bounds."""
        # Valid temperatures
        LLMConfig(temperature=0.0)
        LLMConfig(temperature=2.0)

        # Invalid temperatures
        with pytest.raises(ValueError):
            LLMConfig(temperature=-0.1)
        with pytest.raises(ValueError):
            LLMConfig(temperature=2.1)


class TestProviderConfigs:
    """Tests for PROVIDER_CONFIGS."""

    def test_deepseek_config(self):
        """Test DeepSeek provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.DEEPSEEK]
        assert config["base_url"] == "https://api.deepseek.com"
        assert config["default_model"] == "deepseek-chat"
        assert config["env_key"] == "DEEPSEEK_API_KEY"

    def test_openai_config(self):
        """Test OpenAI provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.OPENAI]
        assert config["base_url"] is None
        assert config["default_model"] == "gpt-4o-mini"
        assert config["env_key"] == "OPENAI_API_KEY"


class TestGetLLMConfig:
    """Tests for get_llm_config function."""

    def test_default_provider(self):
        """Test default provider is DeepSeek."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_llm_config()
            assert config.provider == LLMProvider.DEEPSEEK

    def test_openai_provider_from_env(self):
        """Test setting OpenAI provider from environment."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
            config = get_llm_config()
            assert config.provider == LLMProvider.OPENAI

    def test_invalid_provider_defaults_to_deepseek(self):
        """Test invalid provider defaults to DeepSeek."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "invalid"}, clear=True):
            config = get_llm_config()
            assert config.provider == LLMProvider.DEEPSEEK

    def test_custom_model_from_env(self):
        """Test custom model from environment."""
        with patch.dict(os.environ, {"LLM_MODEL": "custom-model"}, clear=True):
            config = get_llm_config()
            assert config.model == "custom-model"


class TestGetChatModel:
    """Tests for get_chat_model function."""

    def test_returns_fake_model_in_test_mode(self):
        """Test returns fake model in test mode."""
        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            # Clear cache
            get_chat_model.cache_clear()
            model = get_chat_model(purpose="router")
            assert isinstance(model, _FakeChatModel)

    def test_different_purposes_same_temperature(self):
        """Test same model returned for same purpose and temperature."""
        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            get_chat_model.cache_clear()
            model1 = get_chat_model(temperature=0.1, purpose="test1")
            model2 = get_chat_model(temperature=0.1, purpose="test1")
            assert model1 is model2


class TestGetRouterModel:
    """Tests for get_router_model function."""

    def test_returns_low_temperature_model(self):
        """Test router model has low temperature."""
        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            get_chat_model.cache_clear()
            model = get_router_model()
            assert isinstance(model, _FakeChatModel)
            assert model.purpose == "router"


class TestGetAnalystModel:
    """Tests for get_analyst_model function."""

    def test_returns_analyst_model(self):
        """Test analyst model returned."""
        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            get_chat_model.cache_clear()
            model = get_analyst_model()
            assert isinstance(model, _FakeChatModel)
            assert model.purpose == "causal_analyst"


class TestGetExplorerModel:
    """Tests for get_explorer_model function."""

    def test_returns_explorer_model(self):
        """Test explorer model returned."""
        with patch.dict(os.environ, {"CARF_TEST_MODE": "1"}):
            get_chat_model.cache_clear()
            model = get_explorer_model()
            assert isinstance(model, _FakeChatModel)
            assert model.purpose == "bayesian_explorer"
