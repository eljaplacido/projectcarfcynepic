"""OPA policy evaluation service for CARF Guardian."""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import request

from pydantic import BaseModel, Field

from src.utils.resiliency import retry_with_backoff

logger = logging.getLogger("carf.opa")


class OPAConfig(BaseModel):
    """OPA configuration loaded from environment."""

    enabled: bool = Field(default=False)
    base_url: str = Field(default="")
    policy_path: str = Field(default="/v1/data/carf/guardian/allow")
    timeout_seconds: float = Field(default=5.0, ge=1.0)

    @classmethod
    def from_env(cls) -> "OPAConfig":
        """Load OPA config from environment variables."""
        enabled_env = os.getenv("OPA_ENABLED")
        enabled = enabled_env.lower() == "true" if enabled_env is not None else False

        return cls(
            enabled=enabled,
            base_url=os.getenv("OPA_URL", ""),
            policy_path=os.getenv("OPA_POLICY_PATH", "/v1/data/carf/guardian/allow"),
            timeout_seconds=float(os.getenv("OPA_TIMEOUT_SECONDS", "5")),
        )


class OPAEvaluation(BaseModel):
    """Result of an OPA policy evaluation."""

    allow: bool
    raw_result: dict[str, Any]


class OPAService:
    """Service for evaluating policies against OPA."""

    def __init__(self, config: OPAConfig | None = None) -> None:
        self.config = config or OPAConfig.from_env()
        if not self.config.enabled:
            logger.info("OPA integration disabled")

    def _build_url(self) -> str:
        if not self.config.base_url:
            raise RuntimeError("OPA_URL is not configured")
        return self.config.base_url.rstrip("/") + self.config.policy_path

    def _parse_allow(self, data: dict[str, Any]) -> bool:
        result = data.get("result")
        if isinstance(result, bool):
            return result
        if isinstance(result, dict) and isinstance(result.get("allow"), bool):
            return bool(result["allow"])
        return False

    @retry_with_backoff(max_attempts=3, exceptions=(Exception,))
    def evaluate(self, input_data: dict[str, Any]) -> OPAEvaluation:
        """Evaluate a policy decision against OPA."""
        if not self.config.enabled:
            return OPAEvaluation(allow=True, raw_result={})

        url = self._build_url()
        payload = json.dumps({"input": input_data}).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        logger.info("Evaluating Guardian policy via OPA")
        with request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)

        allow = self._parse_allow(data)
        return OPAEvaluation(allow=allow, raw_result=data)


_opa_service: OPAService | None = None


def get_opa_service() -> OPAService:
    """Get or create the OPA service singleton."""
    global _opa_service
    if _opa_service is None:
        _opa_service = OPAService()
    return _opa_service
