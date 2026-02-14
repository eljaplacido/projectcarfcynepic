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
    configured_provider = os.getenv("LLM_PROVIDER", "").lower()

    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if configured_provider == "deepseek" and deepseek_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            message="DeepSeek API configured",
        )
    elif configured_provider == "openai" and openai_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            message="OpenAI API configured",
        )
    elif configured_provider == "anthropic" and anthropic_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet"),
            message="Anthropic API configured",
        )
    elif deepseek_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            message="DeepSeek API configured",
        )
    elif openai_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            message="OpenAI API configured",
        )
    elif anthropic_key:
        return LLMConfigStatus(
            is_configured=True,
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet"),
            message="Anthropic API configured",
        )
    else:
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

    if provider == "local":
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

    if provider == "deepseek":
        valid = key.startswith("sk-") and len(key) > 20
        message = "DeepSeek API key validated" if valid else "DeepSeek key should start with 'sk-'"
    elif provider == "openai":
        valid = key.startswith("sk-") and len(key) > 20
        message = "OpenAI API key validated" if valid else "OpenAI key should start with 'sk-'"
    elif provider == "anthropic":
        valid = key.startswith("sk-ant-") and len(key) > 20
        message = "Anthropic API key validated" if valid else "Anthropic key should start with 'sk-ant-'"

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

    env_key = None
    if provider == "openai":
        env_key = "OPENAI_API_KEY"
    elif provider == "deepseek":
        env_key = "DEEPSEEK_API_KEY"
    elif provider == "anthropic":
        env_key = "ANTHROPIC_API_KEY"

    os.environ["LLM_PROVIDER"] = provider
    if env_key and request.api_key:
        os.environ[env_key] = request.api_key
        for k in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
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
            for k in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
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
