"""LLM Provider Configuration for CARF.

Supports multiple LLM providers:
- DeepSeek (recommended for cost efficiency)
- OpenAI
- Anthropic (Claude)
- Google (Gemini)
- Mistral
- Ollama (local)
- Together AI (open-source models)

Providers using OpenAI-compatible APIs (DeepSeek, OpenAI, Mistral, Ollama, Together)
use langchain-openai. Anthropic and Google use their dedicated langchain integrations.
"""

import os
import logging
import json
import threading
from enum import Enum
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.llm")


# ---------------------------------------------------------------------------
# Token Usage Tracking (Phase 16 — Governance PRICE pillar)
# ---------------------------------------------------------------------------

_token_usage_local = threading.local()


def reset_token_usage() -> None:
    """Reset accumulated token usage for the current thread."""
    _token_usage_local.input_tokens = 0
    _token_usage_local.output_tokens = 0


def accumulate_token_usage(input_tokens: int, output_tokens: int) -> None:
    """Add token usage from an LLM call to the thread-local accumulator."""
    if not hasattr(_token_usage_local, "input_tokens"):
        reset_token_usage()
    _token_usage_local.input_tokens += input_tokens
    _token_usage_local.output_tokens += output_tokens


def get_accumulated_token_usage() -> dict[str, int]:
    """Get accumulated token usage for the current thread."""
    return {
        "input": getattr(_token_usage_local, "input_tokens", 0),
        "output": getattr(_token_usage_local, "output_tokens", 0),
    }


class _FakeLLMResponse:
    """Minimal response wrapper for test-mode LLM calls."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChatModel:
    """Deterministic, offline LLM stub for tests."""

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose

    async def ainvoke(self, messages):  # type: ignore[no-untyped-def]
        return _FakeLLMResponse(self._build_response(messages))

    def invoke(self, messages):  # type: ignore[no-untyped-def]
        return _FakeLLMResponse(self._build_response(messages))

    def _build_response(self, messages) -> str:  # type: ignore[no-untyped-def]
        # Get full prompt for general use
        prompt = " ".join(getattr(m, "content", "") for m in messages).lower()

        if self.purpose == "router":
            # For router, only check the user's query (last message), not system prompt
            user_query = ""
            for m in messages:
                content = getattr(m, "content", "")
                if "classify this request" in content.lower():
                    # Extract the actual query after "Classify this request:"
                    user_query = content.lower()
                    break
            if not user_query:
                # Fallback to last message if pattern not found
                user_query = getattr(messages[-1], "content", "").lower() if messages else ""

            # Pattern-based domain classification for realistic test behavior
            causal_keywords = ["why", "cause", "effect", "affect", "impact", "increase", "decrease", "drive"]
            complex_keywords = ["predict", "forecast", "will", "might", "could", "market", "future"]
            chaotic_keywords = ["crash", "emergency", "urgent", "critical", "down", "breach"]

            if any(kw in user_query for kw in chaotic_keywords):
                domain, confidence = "Chaotic", 0.90
                reasoning = "Emergency/crisis keywords detected"
                indicators = ["emergency", "crisis"]
            elif any(kw in user_query for kw in causal_keywords):
                domain, confidence = "Complicated", 0.88
                reasoning = "Causal analysis required"
                indicators = ["cause", "effect", "analysis"]
            elif any(kw in user_query for kw in complex_keywords):
                domain, confidence = "Complex", 0.85
                reasoning = "Uncertainty/prediction required"
                indicators = ["uncertainty", "prediction"]
            else:
                domain, confidence = "Clear", 0.95
                reasoning = "Deterministic lookup request"
                indicators = ["lookup", "deterministic"]

            payload = {
                "domain": domain,
                "confidence": confidence,
                "reasoning": reasoning,
                "key_indicators": indicators,
            }
            return json.dumps(payload)

        if self.purpose == "causal_analyst":
            if "analyze this causal hypothesis" in prompt:
                payload = {
                    "interpretation": "Moderate causal effect with manageable risk.",
                    "causal_claim_supported": True,
                    "confidence_level": "medium",
                    "key_limitations": ["limited data", "unobserved confounders"],
                    "recommendations": ["collect more data", "run sensitivity checks"],
                }
                return json.dumps(payload)

            payload = {
                "treatment": "price_increase",
                "outcome": "churn",
                "mechanism": "Higher price reduces retention",
                "confounders": ["competitor_pricing"],
                "variables": [
                    {
                        "name": "price_increase",
                        "role": "treatment",
                        "description": "Pricing change",
                    },
                    {
                        "name": "churn",
                        "role": "outcome",
                        "description": "Customer churn rate",
                    },
                    {
                        "name": "competitor_pricing",
                        "role": "confounder",
                        "description": "Market price pressure",
                    },
                ],
                "edges": [
                    ["price_increase", "churn"],
                    ["competitor_pricing", "churn"],
                ],
                "confidence": 0.7,
                "reasoning": "Pricing changes often affect retention.",
            }
            return json.dumps(payload)

        if self.purpose == "bayesian_explorer":
            if "design probes" in prompt:
                payload = {
                    "probes": [
                        {
                            "probe_id": "probe_1",
                            "description": "Run a small A/B test on pricing",
                            "expected_information_gain": 0.6,
                            "risk_level": "low",
                            "reversible": True,
                            "success_criteria": "Churn decreases in test cohort",
                            "failure_criteria": "No change or higher churn",
                            "estimated_duration": "2 weeks",
                            "resources_needed": ["analytics", "product"],
                        }
                    ],
                    "recommended_probe_id": "probe_1",
                    "recommendation_reasoning": "Low risk, high signal",
                }
                return json.dumps(payload)

            payload = {
                "hypotheses": [
                    {
                        "hypothesis": "Market demand is softening",
                        "prior": 0.6,
                        "reasoning": "Recent demand signals are mixed",
                        "evidence_that_would_increase": ["lower conversion"],
                        "evidence_that_would_decrease": ["higher retention"],
                    }
                ],
                "overall_uncertainty": 0.7,
                "key_unknowns": ["elasticity", "competitor response"],
            }
            return json.dumps(payload)

        return json.dumps({"message": "test-mode stub"})


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    TOGETHER = "together"


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""
    provider: LLMProvider = Field(default=LLMProvider.DEEPSEEK)
    model: str = Field(default="deepseek-chat")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    api_key: str | None = None
    base_url: str | None = None


# Provider configurations
PROVIDER_CONFIGS = {
    LLMProvider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "client_type": "openai_compat",
    },
    LLMProvider.OPENAI: {
        "base_url": None,
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "client_type": "openai_compat",
    },
    LLMProvider.ANTHROPIC: {
        "base_url": None,
        "default_model": "claude-sonnet-4-5-20250929",
        "env_key": "ANTHROPIC_API_KEY",
        "client_type": "anthropic",
    },
    LLMProvider.GOOGLE: {
        "base_url": None,
        "default_model": "gemini-2.0-flash",
        "env_key": "GOOGLE_API_KEY",
        "client_type": "google",
    },
    LLMProvider.MISTRAL: {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "env_key": "MISTRAL_API_KEY",
        "client_type": "openai_compat",
    },
    LLMProvider.OLLAMA: {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.1",
        "env_key": None,
        "client_type": "openai_compat",
    },
    LLMProvider.TOGETHER: {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.1-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "client_type": "openai_compat",
    },
}


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment."""
    provider_str = os.getenv("LLM_PROVIDER", "deepseek").lower()

    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        logger.warning(f"Unknown LLM provider '{provider_str}', defaulting to DeepSeek")
        provider = LLMProvider.DEEPSEEK

    config = PROVIDER_CONFIGS[provider]
    env_key = config["env_key"]
    api_key = os.getenv(env_key) if env_key else None

    if not api_key and provider != LLMProvider.OLLAMA:
        # Fallback to OPENAI_API_KEY for compatibility
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and provider == LLMProvider.DEEPSEEK:
            logger.warning("Using OPENAI_API_KEY for DeepSeek - consider setting DEEPSEEK_API_KEY")

    return LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", config["default_model"]),
        api_key=api_key,
        base_url=config["base_url"],
    )


@lru_cache(maxsize=4)
def get_chat_model(
    model: str | None = None,
    temperature: float = 0.1,
    purpose: str = "general",
) -> BaseChatModel:
    """Get a configured LLM instance for any supported provider.

    Dispatches to the correct LangChain chat model class based on provider's
    client_type: openai_compat uses ChatOpenAI, anthropic uses ChatAnthropic,
    google uses ChatGoogleGenerativeAI.

    Args:
        model: Override model name (optional)
        temperature: LLM temperature (0.0-2.0)
        purpose: Usage context for logging ("router", "causal", "bayesian", etc.)

    Returns:
        Configured BaseChatModel instance
    """
    if os.getenv("CARF_TEST_MODE") == "1":
        logger.info(f"Using test-mode LLM stub for purpose={purpose}")
        return _FakeChatModel(purpose=purpose)  # type: ignore[return-value]

    config = get_llm_config()
    provider_config = PROVIDER_CONFIGS[config.provider]
    client_type = provider_config["client_type"]

    model_name = model or config.model
    api_key = config.api_key

    # Ollama doesn't need an API key
    if config.provider == LLMProvider.OLLAMA:
        api_key = "ollama"  # placeholder for ChatOpenAI requirement
    elif not api_key:
        env_key = provider_config["env_key"]
        raise ValueError(
            f"No API key found for {config.provider.value}. "
            f"Set {env_key} environment variable."
        )

    logger.info(
        f"Initializing LLM: provider={config.provider.value}, "
        f"model={model_name}, temperature={temperature}, purpose={purpose}"
    )

    if client_type == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for Anthropic provider. "
                "Install it with: pip install 'carf[providers]' or pip install langchain-anthropic"
            )
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            max_tokens=config.max_tokens,
        )

    if client_type == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for Google provider. "
                "Install it with: pip install 'carf[providers]' or pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
            max_output_tokens=config.max_tokens,
        )

    # client_type == "openai_compat" (DeepSeek, OpenAI, Mistral, Ollama, Together)
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=config.base_url,
        max_tokens=config.max_tokens,
    )


def get_router_model() -> BaseChatModel:
    """Get LLM configured for Cynefin routing (low temperature, fast)."""
    return get_chat_model(temperature=0.1, purpose="router")


def get_analyst_model() -> BaseChatModel:
    """Get LLM configured for causal analysis (moderate temperature)."""
    return get_chat_model(temperature=0.3, purpose="causal_analyst")


def get_explorer_model() -> BaseChatModel:
    """Get LLM configured for Bayesian exploration (higher temperature)."""
    return get_chat_model(temperature=0.7, purpose="bayesian_explorer")
