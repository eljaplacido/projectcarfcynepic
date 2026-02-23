"""Deployment Profiles — Environment-aware configuration presets for CARF.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Unifies ``CARF_PROFILE`` (research / staging / production) into a single
``ProfileConfig`` that controls CORS, auth requirements, Neo4j strictness,
and governance defaults.

Backward-compatible: when ``CARF_PROFILE`` is unset, infers from existing
``PROD_MODE`` / ``GOVERNANCE_ENABLED`` environment variables.

Usage:
    from src.core.deployment_profile import get_profile
    profile = get_profile()
    if profile.require_neo4j:
        ...
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.deployment_profile")


class DeploymentMode(str, Enum):
    RESEARCH = "research"
    STAGING = "staging"
    PRODUCTION = "production"


class ProfileConfig(BaseModel):
    """Resolved deployment profile with concrete settings."""

    mode: DeploymentMode = DeploymentMode.RESEARCH

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False

    # Neo4j
    require_neo4j: bool = False

    # Governance
    governance_enabled: bool = False

    # Auth / Security
    auth_enabled: bool = False
    rate_limiting_enabled: bool = False
    max_request_size_mb: int = 10

    # Observability
    structured_logging: bool = False


# ---------------------------------------------------------------------------
# Profile presets
# ---------------------------------------------------------------------------

_PROFILE_PRESETS: dict[DeploymentMode, dict[str, Any]] = {
    DeploymentMode.RESEARCH: {
        "cors_origins": ["*"],
        "cors_allow_credentials": False,
        "require_neo4j": False,
        "governance_enabled": False,
        "auth_enabled": False,
        "rate_limiting_enabled": False,
        "structured_logging": False,
    },
    DeploymentMode.STAGING: {
        "cors_origins": ["*"],
        "cors_allow_credentials": True,
        "require_neo4j": False,
        "governance_enabled": True,
        "auth_enabled": True,
        "rate_limiting_enabled": True,
        "structured_logging": True,
    },
    DeploymentMode.PRODUCTION: {
        "cors_origins": [],  # Must be set via CARF_CORS_ORIGINS
        "cors_allow_credentials": True,
        "require_neo4j": True,
        "governance_enabled": True,
        "auth_enabled": True,
        "rate_limiting_enabled": True,
        "max_request_size_mb": 50,
        "structured_logging": True,
    },
}


def _infer_mode() -> DeploymentMode:
    """Infer deployment mode from environment variables.

    Priority:
      1. ``CARF_PROFILE`` (explicit)
      2. ``PROD_MODE=true`` → production
      3. ``GOVERNANCE_ENABLED=true`` (without PROD_MODE) → staging
      4. Default → research
    """
    explicit = os.environ.get("CARF_PROFILE", "").strip().lower()
    if explicit:
        try:
            return DeploymentMode(explicit)
        except ValueError:
            logger.warning(
                "Unknown CARF_PROFILE '%s'; falling back to research. "
                "Valid: research, staging, production",
                explicit,
            )
            return DeploymentMode.RESEARCH

    # Backward-compatible inference
    if os.getenv("PROD_MODE", "").lower() in ("1", "true", "yes"):
        return DeploymentMode.PRODUCTION

    if os.getenv("GOVERNANCE_ENABLED", "").lower() == "true":
        return DeploymentMode.STAGING

    return DeploymentMode.RESEARCH


def resolve_profile(mode: DeploymentMode | None = None) -> ProfileConfig:
    """Resolve a full ``ProfileConfig`` for the given (or inferred) mode.

    The preset values can be overridden by specific env vars:
      - ``CARF_CORS_ORIGINS`` (comma-separated)
      - ``GOVERNANCE_ENABLED``
    """
    if mode is None:
        mode = _infer_mode()

    preset = _PROFILE_PRESETS[mode]
    config = ProfileConfig(mode=mode, **preset)

    # Allow env-var overrides on top of the preset
    cors_env = os.environ.get("CARF_CORS_ORIGINS")
    if cors_env:
        config.cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

    # Allow governance to be force-enabled even in research
    gov_env = os.environ.get("GOVERNANCE_ENABLED", "").lower()
    if gov_env == "true":
        config.governance_enabled = True

    return config


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_profile: ProfileConfig | None = None


def get_profile() -> ProfileConfig:
    """Get the singleton deployment profile (resolved once at first access)."""
    global _profile
    if _profile is None:
        _profile = resolve_profile()
        logger.info("Deployment profile: %s", _profile.mode.value)
    return _profile


def governance_enabled() -> bool:
    """Convenience: check whether governance is enabled via the profile."""
    return get_profile().governance_enabled
