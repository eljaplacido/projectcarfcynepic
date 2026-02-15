"""CSL Tool Guard — wraps LangChain tools with CSL policy enforcement.

Supports two modes:
  - enforce: blocks tool execution on policy violation
  - log-only: logs violations but allows execution (audit mode)

Audit entries use a bounded deque (maxlen=1000) per AP-4 requirements.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable

from src.services.csl_policy_service import CSLEvaluation, get_csl_service

logger = logging.getLogger("carf.csl.toolguard")


class CSLToolGuard:
    """Wraps callable tools with CSL policy enforcement.

    Usage:
        guard = CSLToolGuard(mode="enforce", policies=["chimera_guards", "data_access"])
        wrapped = guard.wrap(original_tool_func)
        result = await wrapped(state)   # raises PolicyViolationError on block
    """

    def __init__(
        self,
        mode: str = "enforce",
        policies: list[str] | None = None,
        max_audit: int = 1000,
    ) -> None:
        """
        Args:
            mode: "enforce" to block on violation, "log-only" to audit only.
            policies: Optional list of policy names to check. None = all.
            max_audit: Maximum audit entries to retain (bounded deque).
        """
        if mode not in ("enforce", "log-only"):
            raise ValueError(f"Invalid mode '{mode}', must be 'enforce' or 'log-only'")
        self.mode = mode
        self.policies = policies
        self.audit_log: deque[dict[str, Any]] = deque(maxlen=max_audit)

    def wrap(self, func: Callable) -> Callable:
        """Wrap a callable (sync or async) with CSL policy checks.

        Returns an async wrapper that evaluates policies before execution.
        """
        import asyncio
        import functools

        @functools.wraps(func)
        async def guarded(*args: Any, **kwargs: Any) -> Any:
            # Extract state from first positional arg or kwargs
            state = args[0] if args else kwargs.get("state")

            start_ms = time.monotonic()
            evaluation = await self._evaluate(state)
            latency_ms = round((time.monotonic() - start_ms) * 1000, 2)

            # Record audit entry
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "tool": func.__name__,
                "mode": self.mode,
                "allow": evaluation.allow,
                "rules_checked": evaluation.rules_checked,
                "rules_failed": evaluation.rules_failed,
                "latency_ms": latency_ms,
                "violations": [
                    {"rule": v.rule_name, "policy": v.policy_name, "message": v.message}
                    for v in evaluation.violations
                ],
            }
            self.audit_log.append(entry)

            if not evaluation.allow:
                violation_summary = "; ".join(v.message for v in evaluation.violations)
                if self.mode == "enforce":
                    logger.warning(
                        f"CSL BLOCKED {func.__name__}: {violation_summary}"
                    )
                    raise PolicyViolationError(
                        f"Policy violation in {func.__name__}: {violation_summary}",
                        evaluation=evaluation,
                    )
                else:
                    logger.info(
                        f"CSL LOG-ONLY {func.__name__}: {violation_summary}"
                    )

            # Execute original function
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return await asyncio.to_thread(func, *args, **kwargs)

        return guarded

    async def _evaluate(self, state: Any) -> CSLEvaluation:
        """Evaluate CSL policies against the given state."""
        service = get_csl_service()

        if not service.is_available:
            return CSLEvaluation(allow=True)

        try:
            context = service.map_state_to_context(state)
        except Exception as exc:
            logger.error(f"CSL context mapping failed: {exc}")
            return CSLEvaluation(allow=True, error=str(exc))

        if self.policies:
            # Evaluate only specified policies
            from src.services.csl_policy_service import CSLRuleResult
            all_results = []
            violations = []
            for policy in service._policies:
                if policy.name in self.policies:
                    results = policy.evaluate(context)
                    all_results.extend(results)
                    violations.extend(r for r in results if not r.passed)

            return CSLEvaluation(
                allow=len(violations) == 0,
                rules_checked=len(all_results),
                rules_passed=len(all_results) - len(violations),
                rules_failed=len(violations),
                violations=violations,
            )
        else:
            return service._evaluate_builtin(context)

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of the audit log."""
        return list(self.audit_log)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics from audit log."""
        total = len(self.audit_log)
        blocked = sum(1 for e in self.audit_log if not e["allow"])
        return {
            "total_checks": total,
            "blocked": blocked,
            "allowed": total - blocked,
            "mode": self.mode,
            "policies": self.policies,
        }


class PolicyViolationError(Exception):
    """Raised when a CSL policy blocks tool execution in enforce mode."""

    def __init__(self, message: str, evaluation: CSLEvaluation | None = None):
        super().__init__(message)
        self.evaluation = evaluation
