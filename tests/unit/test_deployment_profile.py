# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Tests for the deployment profile system."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.core.deployment_profile import (
    DeploymentMode,
    ProfileConfig,
    resolve_profile,
    get_profile,
    governance_enabled,
    _infer_mode,
)


# ---------------------------------------------------------------------------
# Mode inference
# ---------------------------------------------------------------------------

class TestInferMode:
    def test_default_is_research(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _infer_mode() == DeploymentMode.RESEARCH

    def test_explicit_carf_profile_research(self):
        with patch.dict(os.environ, {"CARF_PROFILE": "research"}, clear=True):
            assert _infer_mode() == DeploymentMode.RESEARCH

    def test_explicit_carf_profile_staging(self):
        with patch.dict(os.environ, {"CARF_PROFILE": "staging"}, clear=True):
            assert _infer_mode() == DeploymentMode.STAGING

    def test_explicit_carf_profile_production(self):
        with patch.dict(os.environ, {"CARF_PROFILE": "production"}, clear=True):
            assert _infer_mode() == DeploymentMode.PRODUCTION

    def test_invalid_carf_profile_falls_back(self):
        with patch.dict(os.environ, {"CARF_PROFILE": "banana"}, clear=True):
            assert _infer_mode() == DeploymentMode.RESEARCH

    def test_prod_mode_infers_production(self):
        with patch.dict(os.environ, {"PROD_MODE": "true"}, clear=True):
            assert _infer_mode() == DeploymentMode.PRODUCTION

    def test_governance_enabled_infers_staging(self):
        with patch.dict(os.environ, {"GOVERNANCE_ENABLED": "true"}, clear=True):
            assert _infer_mode() == DeploymentMode.STAGING

    def test_carf_profile_overrides_prod_mode(self):
        with patch.dict(os.environ, {"CARF_PROFILE": "research", "PROD_MODE": "true"}, clear=True):
            assert _infer_mode() == DeploymentMode.RESEARCH


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------

class TestResolveProfile:
    def test_research_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            profile = resolve_profile(DeploymentMode.RESEARCH)
            assert profile.mode == DeploymentMode.RESEARCH
            assert profile.cors_origins == ["*"]
            assert profile.require_neo4j is False
            assert profile.auth_enabled is False
            assert profile.governance_enabled is False

    def test_staging_defaults(self):
        profile = resolve_profile(DeploymentMode.STAGING)
        assert profile.mode == DeploymentMode.STAGING
        assert profile.auth_enabled is True
        assert profile.rate_limiting_enabled is True
        assert profile.governance_enabled is True

    def test_production_defaults(self):
        profile = resolve_profile(DeploymentMode.PRODUCTION)
        assert profile.mode == DeploymentMode.PRODUCTION
        assert profile.require_neo4j is True
        assert profile.auth_enabled is True

    def test_cors_origins_env_override(self):
        with patch.dict(os.environ, {"CARF_CORS_ORIGINS": "https://app.example.com, https://admin.example.com"}):
            profile = resolve_profile(DeploymentMode.PRODUCTION)
            assert "https://app.example.com" in profile.cors_origins
            assert "https://admin.example.com" in profile.cors_origins

    def test_governance_force_enabled(self):
        with patch.dict(os.environ, {"GOVERNANCE_ENABLED": "true"}):
            profile = resolve_profile(DeploymentMode.RESEARCH)
            assert profile.governance_enabled is True


# ---------------------------------------------------------------------------
# Singleton and convenience
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_profile_returns_same_instance(self):
        import src.core.deployment_profile as mod
        mod._profile = None
        with patch.dict(os.environ, {}, clear=True):
            a = get_profile()
            b = get_profile()
            assert a is b
        mod._profile = None  # cleanup

    def test_governance_enabled_convenience(self):
        import src.core.deployment_profile as mod
        mod._profile = None
        with patch.dict(os.environ, {"GOVERNANCE_ENABLED": "true"}, clear=True):
            assert governance_enabled() is True
        mod._profile = None  # cleanup


# ---------------------------------------------------------------------------
# ProfileConfig model
# ---------------------------------------------------------------------------

class TestProfileConfig:
    def test_profile_config_serializable(self):
        config = ProfileConfig(mode=DeploymentMode.RESEARCH)
        data = config.model_dump()
        assert data["mode"] == "research"
        assert isinstance(data["cors_origins"], list)
