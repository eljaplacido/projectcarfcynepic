"""Tests for the security middleware."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import (
    APIKeyAuthMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    register_security_middleware,
    _is_public,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "secret"}

    @app.post("/api/data")
    async def post_data():
        return {"status": "created"}

    return app


# ---------------------------------------------------------------------------
# Public path detection
# ---------------------------------------------------------------------------

class TestIsPublic:
    def test_health_is_public(self):
        assert _is_public("/health") is True

    def test_docs_is_public(self):
        assert _is_public("/docs") is True

    def test_api_is_not_public(self):
        assert _is_public("/api/test") is False

    def test_governance_is_not_public(self):
        assert _is_public("/governance/policies") is False


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------

class TestAPIKeyAuth:
    def test_rejects_without_auth(self):
        app = _make_app()
        app.add_middleware(APIKeyAuthMiddleware, api_key="test-key-123")
        client = TestClient(app)
        resp = client.get("/api/test")
        assert resp.status_code == 401

    def test_accepts_valid_bearer_token(self):
        app = _make_app()
        app.add_middleware(APIKeyAuthMiddleware, api_key="test-key-123")
        client = TestClient(app)
        resp = client.get("/api/test", headers={"Authorization": "Bearer test-key-123"})
        assert resp.status_code == 200

    def test_rejects_invalid_token(self):
        app = _make_app()
        app.add_middleware(APIKeyAuthMiddleware, api_key="test-key-123")
        client = TestClient(app)
        resp = client.get("/api/test", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 401

    def test_health_bypasses_auth(self):
        app = _make_app()
        app.add_middleware(APIKeyAuthMiddleware, api_key="test-key-123")
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_allows_within_limit(self):
        app = _make_app()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=10)
        client = TestClient(app)
        for _ in range(5):
            resp = client.get("/api/test")
            assert resp.status_code == 200

    def test_rejects_over_limit(self):
        app = _make_app()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=3)
        client = TestClient(app)
        for _ in range(3):
            resp = client.get("/api/test")
            assert resp.status_code == 200
        resp = client.get("/api/test")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_health_bypasses_rate_limit(self):
        app = _make_app()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=1)
        client = TestClient(app)
        # First request to /api/test
        client.get("/api/test")
        # Health should still work even if limit reached
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Request Size Limit
# ---------------------------------------------------------------------------

class TestRequestSizeLimit:
    def test_rejects_large_request(self):
        app = _make_app()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=100)
        client = TestClient(app)
        resp = client.post(
            "/api/data",
            content="x" * 200,
            headers={"Content-Length": "200"},
        )
        assert resp.status_code == 413

    def test_allows_small_request(self):
        app = _make_app()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=1000)
        client = TestClient(app)
        resp = client.post("/api/data", content="small")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_research_mode_skips_middleware(self):
        """In research mode, no middleware should be registered."""
        app = _make_app()
        with patch.dict(os.environ, {}, clear=True):
            import src.core.deployment_profile as dp
            dp._profile = None
            register_security_middleware(app)
            dp._profile = None

        client = TestClient(app)
        # No auth required in research mode
        resp = client.get("/api/test")
        assert resp.status_code == 200

    def test_staging_mode_registers_middleware(self):
        """In staging mode, auth and rate limiting should be active."""
        app = _make_app()
        with patch.dict(os.environ, {"CARF_PROFILE": "staging", "CARF_API_KEY": "staging-key"}, clear=True):
            import src.core.deployment_profile as dp
            dp._profile = None
            register_security_middleware(app)
            dp._profile = None

        client = TestClient(app)
        # Without auth header → 401
        resp = client.get("/api/test")
        assert resp.status_code == 401
        # With auth header → 200
        resp = client.get("/api/test", headers={"Authorization": "Bearer staging-key"})
        assert resp.status_code == 200
