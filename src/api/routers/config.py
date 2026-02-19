"""Configuration endpoints."""

import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.api.models import (
    ConfigValidateRequest,
    ConfigValidateResponse,
    LLMConfigStatus,
    LLMConfigUpdateRequest,
    LLMConfigValidateRequest,
)
from src.services.visualization_engine import get_visualization_config, ContextualVisualization, get_cynefin_viz_config

logger = logging.getLogger("carf")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
router = APIRouter(tags=["Configuration"])


@router.get("/config/visualization")
async def get_viz_config(context: str = "general") -> ContextualVisualization:
    """Get context-aware visualization configuration."""
    return get_visualization_config(context)


@router.get("/api/visualization-config")
async def visualization_config(context: str = "general", domain: str = "disorder"):
    """Return combined visualization configuration for context + domain."""
    context_config = get_visualization_config(context)
    domain_config = get_cynefin_viz_config(domain)
    return {
        "context": context_config.model_dump(),
        "domain": domain_config.model_dump(),
    }


@router.get("/config/status")
async def get_config_status() -> LLMConfigStatus:
    """Check current LLM configuration status.

    Returns whether the system has a valid LLM configuration.
    Respects the LLM_PROVIDER environment variable if set.
    """
    from src.core.llm import PROVIDER_CONFIGS, LLMProvider

    configured_provider = os.getenv("LLM_PROVIDER", "").lower()

    # Provider detection table: (provider_name, env_key, default_model, display_name)
    provider_table = [
        ("deepseek", "DEEPSEEK_API_KEY", "deepseek-chat", "DeepSeek"),
        ("openai", "OPENAI_API_KEY", "gpt-4o-mini", "OpenAI"),
        ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-5-20250929", "Anthropic"),
        ("google", "GOOGLE_API_KEY", "gemini-2.0-flash", "Google Gemini"),
        ("mistral", "MISTRAL_API_KEY", "mistral-large-latest", "Mistral"),
        ("together", "TOGETHER_API_KEY", "meta-llama/Llama-3.1-70B-Instruct-Turbo", "Together AI"),
    ]

    # Ollama is special: no API key needed, just check if provider is set
    if configured_provider == "ollama":
        return LLMConfigStatus(
            is_configured=True,
            provider="ollama",
            model=os.getenv("LLM_MODEL", "llama3.1"),
            message="Ollama (local) configured",
        )

    # Check explicitly configured provider first
    for name, env_key, default_model, display_name in provider_table:
        if configured_provider == name and os.getenv(env_key):
            return LLMConfigStatus(
                is_configured=True,
                provider=name,
                model=os.getenv("LLM_MODEL", default_model),
                message=f"{display_name} API configured",
            )

    # Auto-detect from available keys (priority order)
    for name, env_key, default_model, display_name in provider_table:
        if os.getenv(env_key):
            return LLMConfigStatus(
                is_configured=True,
                provider=name,
                model=os.getenv("LLM_MODEL", default_model),
                message=f"{display_name} API configured",
            )

    return LLMConfigStatus(
        is_configured=False,
        provider=None,
        model=None,
        message="No LLM API key configured. Please set up your API key.",
    )


@router.post("/config/validate")
async def validate_config(request: ConfigValidateRequest) -> ConfigValidateResponse:
    """Validate LLM provider configuration.

    Tests the API key by making a minimal request to the provider.
    For local providers, checks if the endpoint is reachable.
    """
    provider = request.provider.lower()

    # Ollama: no key needed, check server reachability
    if provider in ("local", "ollama"):
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{request.base_url or 'http://localhost:11434'}/api/tags")
                if response.status_code == 200:
                    return ConfigValidateResponse(
                        valid=True,
                        provider=provider,
                        message="Local Ollama server is reachable",
                    )
        except Exception:
            pass

        return ConfigValidateResponse(
            valid=False,
            provider=provider,
            message="Cannot reach local Ollama server",
        )

    if not request.api_key:
        return ConfigValidateResponse(
            valid=False,
            provider=provider,
            message="API key is required for this provider",
        )

    key = request.api_key.strip()
    valid = False
    message = "Invalid API key format"

    # Validation patterns per provider
    validation_rules: dict[str, tuple[str, str]] = {
        "deepseek": ("sk-", "DeepSeek key should start with 'sk-'"),
        "openai": ("sk-", "OpenAI key should start with 'sk-'"),
        "anthropic": ("sk-ant-", "Anthropic key should start with 'sk-ant-'"),
        "google": ("AI", "Google key should start with 'AI'"),
        "mistral": ("", "Mistral API key format not recognized"),
        "together": ("", "Together API key format not recognized"),
    }

    if provider in validation_rules:
        prefix, error_msg = validation_rules[provider]
        if prefix:
            valid = key.startswith(prefix) and len(key) > 20
        else:
            # For providers without a known prefix, accept any key > 20 chars
            valid = len(key) > 20
        display_name = provider.capitalize()
        message = f"{display_name} API key validated" if valid else error_msg
    else:
        # Unknown provider: accept if key is long enough
        valid = len(key) > 10
        message = "API key accepted" if valid else "API key too short"

    return ConfigValidateResponse(
        valid=valid,
        provider=provider,
        message=message,
    )


@router.post("/config/update")
async def update_config(request: LLMConfigUpdateRequest) -> LLMConfigStatus:
    """Update LLM configuration and persist to .env."""
    validation = await validate_config(
        ConfigValidateRequest(
            provider=request.provider,
            api_key=request.api_key,
            base_url=request.base_url,
        )
    )
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.message)

    provider = request.provider.lower()
    from src.core.llm import get_chat_model

    # Map provider to its env key
    env_key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "together": "TOGETHER_API_KEY",
        "ollama": None,
        "local": None,
    }
    all_api_keys = [v for v in env_key_map.values() if v]
    env_key = env_key_map.get(provider)

    os.environ["LLM_PROVIDER"] = provider
    if env_key and request.api_key:
        os.environ[env_key] = request.api_key
        # Clean up other provider keys from env
        for k in all_api_keys:
            if k != env_key and k in os.environ:
                del os.environ[k]

    get_chat_model.cache_clear()
    logger.info(f"Updated LLM config to {provider} and cleared cache")

    env_path = PROJECT_ROOT / ".env"
    try:
        current_env = {}
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        current_env[k] = v

        current_env["LLM_PROVIDER"] = provider
        if env_key and request.api_key:
            current_env[env_key] = request.api_key
            for k in all_api_keys:
                if k != env_key and k in current_env:
                    del current_env[k]

        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in current_env.items():
                f.write(f"{k}={v}\n")
            if not current_env:
                f.write(f"LLM_PROVIDER={provider}\n")
                if env_key and request.api_key:
                    f.write(f"{env_key}={request.api_key}\n")

    except Exception as e:
        logger.error(f"Failed to write .env: {e}")

    return await get_config_status()
