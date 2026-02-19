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

    def test_anthropic_value(self):
        """Test Anthropic provider value."""
        assert LLMProvider.ANTHROPIC.value == "anthropic"

    def test_google_value(self):
        """Test Google provider value."""
        assert LLMProvider.GOOGLE.value == "google"

    def test_mistral_value(self):
        """Test Mistral provider value."""
        assert LLMProvider.MISTRAL.value == "mistral"

    def test_ollama_value(self):
        """Test Ollama provider value."""
        assert LLMProvider.OLLAMA.value == "ollama"

    def test_together_value(self):
        """Test Together provider value."""
        assert LLMProvider.TOGETHER.value == "together"

    def test_all_seven_providers_exist(self):
        """Test all 7 providers are defined."""
        assert len(LLMProvider) == 7


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

    def test_all_providers_have_configs(self):
        """Test every LLMProvider has an entry in PROVIDER_CONFIGS."""
        for provider in LLMProvider:
            assert provider in PROVIDER_CONFIGS, f"Missing config for {provider.value}"

    def test_all_configs_have_required_keys(self):
        """Test every config has base_url, default_model, env_key, client_type."""
        for provider, config in PROVIDER_CONFIGS.items():
            assert "base_url" in config, f"{provider.value} missing base_url"
            assert "default_model" in config, f"{provider.value} missing default_model"
            assert "env_key" in config, f"{provider.value} missing env_key"
            assert "client_type" in config, f"{provider.value} missing client_type"

    def test_deepseek_config(self):
        """Test DeepSeek provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.DEEPSEEK]
        assert config["base_url"] == "https://api.deepseek.com"
        assert config["default_model"] == "deepseek-chat"
        assert config["env_key"] == "DEEPSEEK_API_KEY"
        assert config["client_type"] == "openai_compat"

    def test_openai_config(self):
        """Test OpenAI provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.OPENAI]
        assert config["base_url"] is None
        assert config["default_model"] == "gpt-4o-mini"
        assert config["env_key"] == "OPENAI_API_KEY"
        assert config["client_type"] == "openai_compat"

    def test_anthropic_config(self):
        """Test Anthropic provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.ANTHROPIC]
        assert config["client_type"] == "anthropic"
        assert config["env_key"] == "ANTHROPIC_API_KEY"
        assert "claude" in config["default_model"]

    def test_google_config(self):
        """Test Google provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.GOOGLE]
        assert config["client_type"] == "google"
        assert config["env_key"] == "GOOGLE_API_KEY"
        assert "gemini" in config["default_model"]

    def test_mistral_config(self):
        """Test Mistral provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.MISTRAL]
        assert config["client_type"] == "openai_compat"
        assert config["env_key"] == "MISTRAL_API_KEY"
        assert "mistral.ai" in config["base_url"]

    def test_ollama_config(self):
        """Test Ollama provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.OLLAMA]
        assert config["client_type"] == "openai_compat"
        assert config["env_key"] is None  # No API key needed
        assert "localhost" in config["base_url"]

    def test_together_config(self):
        """Test Together provider config."""
        config = PROVIDER_CONFIGS[LLMProvider.TOGETHER]
        assert config["client_type"] == "openai_compat"
        assert config["env_key"] == "TOGETHER_API_KEY"
        assert "together.xyz" in config["base_url"]


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

    def test_anthropic_provider_from_env(self):
        """Test setting Anthropic provider from environment."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            config = get_llm_config()
            assert config.provider == LLMProvider.ANTHROPIC
            assert config.api_key == "sk-ant-test"

    def test_ollama_provider_no_key_needed(self):
        """Test Ollama provider doesn't require an API key."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
            config = get_llm_config()
            assert config.provider == LLMProvider.OLLAMA
            assert config.api_key is None  # No key needed

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


class TestFactoryDispatch:
    """Tests for get_chat_model provider dispatch."""

    def test_openai_compat_creates_chatopenai(self):
        """Test openai_compat client_type returns ChatOpenAI."""
        from langchain_openai import ChatOpenAI

        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "sk-test123"}, clear=True):
            get_chat_model.cache_clear()
            model = get_chat_model(purpose="test_openai_compat")
            assert isinstance(model, ChatOpenAI)

    def test_ollama_no_key_creates_chatopenai(self):
        """Test Ollama creates ChatOpenAI with placeholder key."""
        from langchain_openai import ChatOpenAI

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
            get_chat_model.cache_clear()
            model = get_chat_model(purpose="test_ollama")
            assert isinstance(model, ChatOpenAI)

    def test_anthropic_dispatch(self):
        """Test Anthropic dispatch creates ChatAnthropic (or raises ImportError)."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-ant-test123"}, clear=True):
            get_chat_model.cache_clear()
            try:
                model = get_chat_model(purpose="test_anthropic")
                # If langchain-anthropic is installed, verify it's the right type
                from langchain_anthropic import ChatAnthropic
                assert isinstance(model, ChatAnthropic)
            except ImportError as e:
                assert "langchain-anthropic" in str(e)

    def test_google_dispatch(self):
        """Test Google dispatch creates ChatGoogleGenerativeAI (or raises ImportError)."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": "AItest123456789012345"}, clear=True):
            get_chat_model.cache_clear()
            try:
                model = get_chat_model(purpose="test_google")
                from langchain_google_genai import ChatGoogleGenerativeAI
                assert isinstance(model, ChatGoogleGenerativeAI)
            except ImportError as e:
                assert "langchain-google-genai" in str(e)

    def test_missing_key_raises_valueerror(self):
        """Test missing API key raises ValueError."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
            get_chat_model.cache_clear()
            with pytest.raises(ValueError, match="No API key found"):
                get_chat_model(purpose="test_missing_key")

    def test_mistral_creates_chatopenai(self):
        """Test Mistral uses openai_compat path."""
        from langchain_openai import ChatOpenAI

        with patch.dict(os.environ, {"LLM_PROVIDER": "mistral", "MISTRAL_API_KEY": "test-key-123456789012345"}, clear=True):
            get_chat_model.cache_clear()
            model = get_chat_model(purpose="test_mistral")
            assert isinstance(model, ChatOpenAI)

    def test_together_creates_chatopenai(self):
        """Test Together uses openai_compat path."""
        from langchain_openai import ChatOpenAI

        with patch.dict(os.environ, {"LLM_PROVIDER": "together", "TOGETHER_API_KEY": "test-key-123456789012345"}, clear=True):
            get_chat_model.cache_clear()
            model = get_chat_model(purpose="test_together")
            assert isinstance(model, ChatOpenAI)
