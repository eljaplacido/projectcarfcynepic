"""LLM Provider Configuration for CARF.

Supports multiple LLM providers with OpenAI-compatible APIs:
- DeepSeek (recommended for cost efficiency)
- OpenAI

DeepSeek offers significantly lower costs while maintaining strong reasoning capabilities,
making it ideal for the CARF cognitive pipeline.
"""

import os
import logging
import json
from enum import Enum
from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.llm")


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
        prompt = " ".join(getattr(m, "content", "") for m in messages).lower()

        if self.purpose == "router":
            payload = {
                "domain": "Clear",
                "confidence": 0.95,
                "reasoning": "Deterministic lookup request",
                "key_indicators": ["lookup", "deterministic"],
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
        "default_model": "deepseek-chat",  # DeepSeek-V3, excellent for reasoning
        "env_key": "DEEPSEEK_API_KEY",
    },
    LLMProvider.OPENAI: {
        "base_url": None,  # Uses default OpenAI URL
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
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
    api_key = os.getenv(config["env_key"])

    if not api_key:
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
) -> ChatOpenAI:
    """Get a configured ChatOpenAI instance.

    Uses DeepSeek by default for cost efficiency. DeepSeek's API is OpenAI-compatible.

    Args:
        model: Override model name (optional)
        temperature: LLM temperature (0.0-2.0)
        purpose: Usage context for logging ("router", "causal", "bayesian", etc.)

    Returns:
        Configured ChatOpenAI instance

    Usage:
        # Default (uses env config)
        llm = get_chat_model()

        # For classification (low temperature)
        llm = get_chat_model(temperature=0.1, purpose="router")

        # For creative exploration (higher temperature)
        llm = get_chat_model(temperature=0.7, purpose="bayesian")
    """
    if os.getenv("CARF_TEST_MODE") == "1":
        logger.info(f"Using test-mode LLM stub for purpose={purpose}")
        return _FakeChatModel(purpose=purpose)  # type: ignore[return-value]

    config = get_llm_config()

    model_name = model or config.model
    api_key = config.api_key

    if not api_key:
        raise ValueError(
            f"No API key found for {config.provider.value}. "
            f"Set {PROVIDER_CONFIGS[config.provider]['env_key']} environment variable."
        )

    logger.info(
        f"Initializing LLM: provider={config.provider.value}, "
        f"model={model_name}, temperature={temperature}, purpose={purpose}"
    )

    # Create ChatOpenAI with provider-specific config
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=config.base_url,
        max_tokens=config.max_tokens,
    )

    return llm


def get_router_model() -> ChatOpenAI:
    """Get LLM configured for Cynefin routing (low temperature, fast)."""
    return get_chat_model(temperature=0.1, purpose="router")


def get_analyst_model() -> ChatOpenAI:
    """Get LLM configured for causal analysis (moderate temperature)."""
    return get_chat_model(temperature=0.3, purpose="causal_analyst")


def get_explorer_model() -> ChatOpenAI:
    """Get LLM configured for Bayesian exploration (higher temperature)."""
    return get_chat_model(temperature=0.7, purpose="bayesian_explorer")
