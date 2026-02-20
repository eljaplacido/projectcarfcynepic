"""Smart Reflector Service — hybrid heuristic + LLM repair for policy violations.

Tries fast heuristic repairs first. If heuristic confidence is too low or the
violation type is unrecognized, falls back to LLM-based contextual repair.

Usage:
    reflector = get_smart_reflector()
    result = await reflector.repair(state)
"""

import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.smart_reflector")


class RepairStrategy(str, Enum):
    """Strategy used for repair."""
    HEURISTIC = "heuristic"
    LLM = "llm"
    HYBRID = "hybrid"


class RepairResult(BaseModel):
    """Result of a repair attempt."""
    strategy_used: RepairStrategy
    original_action: dict[str, Any]
    repaired_action: dict[str, Any]
    repair_explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    violations_addressed: list[str] = Field(default_factory=list)
    violations_remaining: list[str] = Field(default_factory=list)


class SmartReflectorService:
    """Hybrid heuristic + LLM repair service for policy violations.

    Strategies:
    - HEURISTIC: Fast rule-based repair (budget → 0.8x, threshold → 0.9x, approval → flag)
    - LLM: Contextual LLM-based repair for unrecognized violations
    - HYBRID (default): Try heuristic first, fall back to LLM if insufficient
    """

    def __init__(self):
        strategy_env = os.getenv("REFLECTOR_STRATEGY", "hybrid").lower()
        self._strategy = RepairStrategy(strategy_env) if strategy_env in ("heuristic", "llm", "hybrid") else RepairStrategy.HYBRID

    @property
    def strategy(self) -> RepairStrategy:
        return self._strategy

    def _try_heuristic_repair(
        self,
        action: dict[str, Any],
        violations: list[str],
    ) -> RepairResult | None:
        """Attempt heuristic-based repair. Returns None if no heuristic matches.

        Extracted from graph.py reflector_node logic:
        - budget/cost → reduce numeric values by 20%
        - threshold/limit → apply 10% safety margin
        - approval/authorization → flag for human review
        """
        repaired = action.copy()
        repair_details: list[str] = []
        addressed: list[str] = []
        remaining: list[str] = []
        any_match = False

        for violation in violations:
            violation_lower = violation.lower()
            matched = False

            # Budget-related repairs
            if "budget" in violation_lower or "cost" in violation_lower:
                self._reduce_numerics(repaired, factor=0.8, details=repair_details, prefix="budget")
                matched = True

            # Threshold-related repairs
            elif "threshold" in violation_lower or "limit" in violation_lower:
                self._reduce_numerics(repaired, factor=0.9, details=repair_details, prefix="threshold")
                matched = True

            # Approval-related — flag for human review
            elif "approval" in violation_lower or "authorization" in violation_lower:
                repaired["requires_human_review"] = True
                repaired["review_reason"] = violation
                repair_details.append("Flagged for targeted human review")
                matched = True

            if matched:
                any_match = True
                addressed.append(violation)
            else:
                remaining.append(violation)

        if not any_match:
            return None

        confidence = 0.85 if not remaining else 0.6
        return RepairResult(
            strategy_used=RepairStrategy.HEURISTIC,
            original_action=action,
            repaired_action=repaired,
            repair_explanation="; ".join(repair_details),
            confidence=confidence,
            violations_addressed=addressed,
            violations_remaining=remaining,
        )

    def _reduce_numerics(
        self,
        action: dict[str, Any],
        factor: float,
        details: list[str],
        prefix: str,
    ) -> None:
        """Reduce all positive numeric values in action by factor."""
        for key in list(action.keys()):
            value = action[key]
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                action[key] = value * factor
                pct = int((1 - factor) * 100)
                details.append(f"Reduced {key} by {pct}% ({prefix})")
            elif isinstance(value, dict):
                for sub_key, sub_val in list(value.items()):
                    if isinstance(sub_val, (int, float)) and not isinstance(sub_val, bool) and sub_val > 0:
                        value[sub_key] = sub_val * factor
                        pct = int((1 - factor) * 100)
                        details.append(f"Reduced {key}.{sub_key} by {pct}% ({prefix})")

    async def _try_llm_repair(
        self,
        state: Any,
        action: dict[str, Any],
        violations: list[str],
    ) -> RepairResult:
        """Use LLM to perform contextual repair.

        In test mode, returns a structured mock repair.
        In production, calls get_chat_model for intelligent repair.
        """
        is_test = os.getenv("CARF_TEST_MODE", "").strip() in ("1", "true", "yes")

        if is_test:
            # Test stub: apply generic 15% reduction + flag
            repaired = action.copy()
            for key in list(repaired.keys()):
                value = repaired[key]
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                    repaired[key] = value * 0.85
            repaired["llm_repair_applied"] = True

            return RepairResult(
                strategy_used=RepairStrategy.LLM,
                original_action=action,
                repaired_action=repaired,
                repair_explanation="[test_stub] LLM-based contextual repair applied",
                confidence=0.7,
                violations_addressed=violations,
                violations_remaining=[],
            )

        # Production LLM path
        try:
            from src.services.chimera_oracle import get_chat_model
            llm = get_chat_model(temperature=0.2, purpose="reflector")

            prompt = (
                f"You are a policy compliance repair assistant. "
                f"The following action was rejected by a policy guardian:\n\n"
                f"Action: {action}\n\n"
                f"Violations:\n" + "\n".join(f"- {v}" for v in violations) + "\n\n"
                f"Domain context: {getattr(state, 'cynefin_domain', 'unknown')}\n\n"
                f"Repair the action to address ALL violations while preserving its intent. "
                f"Return JSON with keys: repaired_action (dict), explanation (str), confidence (float 0-1)."
            )

            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse structured response
            import json
            try:
                parsed = json.loads(content)
                repaired_action = parsed.get("repaired_action", action)
                explanation = parsed.get("explanation", "LLM repair applied")
                confidence = min(max(float(parsed.get("confidence", 0.6)), 0.0), 1.0)
            except (json.JSONDecodeError, ValueError):
                repaired_action = action
                explanation = f"LLM suggested: {content[:200]}"
                confidence = 0.4

            return RepairResult(
                strategy_used=RepairStrategy.LLM,
                original_action=action,
                repaired_action=repaired_action,
                repair_explanation=explanation,
                confidence=confidence,
                violations_addressed=violations,
                violations_remaining=[],
            )

        except Exception as e:
            logger.warning(f"LLM repair failed: {e}")
            return RepairResult(
                strategy_used=RepairStrategy.LLM,
                original_action=action,
                repaired_action=action,
                repair_explanation=f"LLM repair failed: {e}",
                confidence=0.0,
                violations_addressed=[],
                violations_remaining=violations,
            )

    async def repair(self, state: Any) -> RepairResult:
        """Repair a policy-violating action using the configured strategy.

        Args:
            state: EpistemicState with proposed_action and policy_violations

        Returns:
            RepairResult with repaired action and metadata
        """
        action = getattr(state, "proposed_action", None) or {}
        violations = getattr(state, "policy_violations", None) or []
        original_action = action.copy() if isinstance(action, dict) else {}

        if not violations:
            return RepairResult(
                strategy_used=self._strategy,
                original_action=original_action,
                repaired_action=original_action,
                repair_explanation="No violations to address",
                confidence=1.0,
                violations_addressed=[],
                violations_remaining=[],
            )

        if self._strategy == RepairStrategy.HEURISTIC:
            result = self._try_heuristic_repair(original_action, violations)
            if result:
                return result
            return RepairResult(
                strategy_used=RepairStrategy.HEURISTIC,
                original_action=original_action,
                repaired_action=original_action,
                repair_explanation="No heuristic matches for violations",
                confidence=0.0,
                violations_addressed=[],
                violations_remaining=violations,
            )

        if self._strategy == RepairStrategy.LLM:
            return await self._try_llm_repair(state, original_action, violations)

        # HYBRID: heuristic first, LLM fallback
        heuristic_result = self._try_heuristic_repair(original_action, violations)
        if heuristic_result and heuristic_result.confidence >= 0.7 and not heuristic_result.violations_remaining:
            return heuristic_result

        # Fall back to LLM for remaining violations
        if heuristic_result and heuristic_result.violations_remaining:
            llm_result = await self._try_llm_repair(
                state, heuristic_result.repaired_action, heuristic_result.violations_remaining
            )
            # Merge results
            return RepairResult(
                strategy_used=RepairStrategy.HYBRID,
                original_action=original_action,
                repaired_action=llm_result.repaired_action,
                repair_explanation=f"Heuristic: {heuristic_result.repair_explanation}; LLM: {llm_result.repair_explanation}",
                confidence=(heuristic_result.confidence + llm_result.confidence) / 2,
                violations_addressed=heuristic_result.violations_addressed + llm_result.violations_addressed,
                violations_remaining=llm_result.violations_remaining,
            )

        if heuristic_result is None:
            return await self._try_llm_repair(state, original_action, violations)

        return heuristic_result


# Singleton
_smart_reflector: SmartReflectorService | None = None


def get_smart_reflector() -> SmartReflectorService:
    """Get singleton SmartReflectorService instance."""
    global _smart_reflector
    if _smart_reflector is None:
        _smart_reflector = SmartReflectorService()
    return _smart_reflector
