# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Firebase JWT authentication middleware for Cloud Run deployment.

When ``FIREBASE_AUTH_ENABLED=true`` the middleware verifies every request's
``Authorization: Bearer <token>`` header using the Firebase Admin SDK and
sets ``request.state.user_id`` / ``request.state.user_email`` for downstream
handlers.

Health, docs, and CORS preflight requests bypass auth.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("carf.auth")

# Endpoints that bypass auth
PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
})

_firebase_app_initialized = False


def _ensure_firebase() -> None:
    """Lazily initialize the Firebase Admin SDK (once)."""
    global _firebase_app_initialized
    if _firebase_app_initialized:
        return

    import firebase_admin
    from firebase_admin import credentials

    # In Cloud Run, Application Default Credentials are available automatically.
    # GOOGLE_APPLICATION_CREDENTIALS can also point to a service account JSON.
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()

    _firebase_app_initialized = True
    logger.info("Firebase Admin SDK initialized")


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/health")


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """Verify Firebase ID tokens on every non-public request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if _is_public(request.url.path):
            return await call_next(request)

        # Allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization: Bearer <token> header"},
            )

        token = auth_header[7:].strip()

        try:
            _ensure_firebase()
            from firebase_admin import auth

            decoded = auth.verify_id_token(token)
            request.state.user_id = decoded["uid"]
            request.state.user_email = decoded.get("email", "")
        except Exception as exc:
            logger.warning("Firebase token verification failed: %s", exc)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired Firebase token"},
            )

        return await call_next(request)
