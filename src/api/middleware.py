"""Security Middleware — Profile-aware auth, rate limiting, and request size limits.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).

Behaviour by profile:
  - research:   pass-through (no auth, no rate limits)
  - staging:    API key auth + rate limiting
  - production: full security (same as staging with stricter defaults)

Health, docs, and OpenAPI endpoints are always public.

Usage:
    from src.api.middleware import register_security_middleware
    register_security_middleware(app)
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.deployment_profile import DeploymentMode, get_profile

logger = logging.getLogger("carf.middleware")

# Endpoints that are always public (no auth required)
PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
})


def _is_public(path: str) -> bool:
    """Check if the request path should bypass auth."""
    return path in PUBLIC_PATHS or path.startswith("/health")


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Bearer token auth via CARF_API_KEY env var.

    Only active in staging/production profiles.
    """

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if _is_public(request.url.path):
            return await call_next(request)

        # Allow OPTIONS for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token == self._api_key:
                return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid API key. Use Authorization: Bearer <key>"},
        )


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP rate limiter.

    Uses a sliding window counter. Not suitable for multi-process
    deployments — use Redis-backed rate limiting in production clusters.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst: int = 10,
    ) -> None:
        super().__init__(app)
        self._rpm = requests_per_minute
        self._burst = burst
        self._counters: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if _is_public(request.url.path):
            return await call_next(request)

        client_ip = self._client_ip(request)
        now = time.time()
        window_start = now - 60.0

        # Clean old entries
        timestamps = self._counters[client_ip]
        self._counters[client_ip] = [t for t in timestamps if t > window_start]
        timestamps = self._counters[client_ip]

        if len(timestamps) >= self._rpm:
            retry_after = int(60 - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Request Size Limit
# ---------------------------------------------------------------------------

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than the configured maximum."""

    def __init__(self, app, max_size_bytes: int) -> None:
        super().__init__(app)
        self._max_size = max_size_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self._max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large. Maximum: {self._max_size // (1024 * 1024)}MB"
                },
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_security_middleware(app: FastAPI) -> None:
    """Register profile-aware security middleware on the FastAPI app.

    In research mode this is a no-op.
    """
    profile = get_profile()

    if profile.mode == DeploymentMode.RESEARCH:
        logger.debug("Research mode: security middleware not registered")
        return

    # Request size limit (always in staging/production)
    max_bytes = profile.max_request_size_mb * 1024 * 1024
    app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=max_bytes)
    logger.info("Request size limit: %dMB", profile.max_request_size_mb)

    # Rate limiting
    if profile.rate_limiting_enabled:
        rpm = 120 if profile.mode == DeploymentMode.PRODUCTION else 300
        app.add_middleware(RateLimitMiddleware, requests_per_minute=rpm)
        logger.info("Rate limiting enabled: %d req/min", rpm)

    # Auth: Firebase JWT (cloud) or API key (self-hosted)
    firebase_enabled = (
        profile.firebase_auth_enabled
        or os.environ.get("FIREBASE_AUTH_ENABLED", "").lower() in ("1", "true", "yes")
    )

    if firebase_enabled:
        from src.api.auth import FirebaseAuthMiddleware

        app.add_middleware(FirebaseAuthMiddleware)
        logger.info("Firebase JWT auth enabled (%s mode)", profile.mode.value)
    elif profile.auth_enabled:
        api_key = os.environ.get("CARF_API_KEY", "")
        if not api_key:
            logger.warning(
                "CARF_API_KEY not set — skipping API key auth in %s mode. "
                "Set CARF_API_KEY to enable authentication.",
                profile.mode.value,
            )
        else:
            app.add_middleware(APIKeyAuthMiddleware, api_key=api_key)
            logger.info("API key auth enabled (%s mode)", profile.mode.value)
