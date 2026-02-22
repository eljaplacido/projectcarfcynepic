"""Cost Intelligence Service for CARF Orchestration Governance.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Implements the PRICE pillar: monetize trade-offs with actual LLM token
tracking and cost intelligence.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from src.core.governance_models import (
    CostAggregate,
    CostBreakdown,
    CostBreakdownItem,
    ROIMetrics,
)

logger = logging.getLogger("carf.governance.cost")


# ---------------------------------------------------------------------------
# LLM Pricing (per 1M tokens, USD)
# ---------------------------------------------------------------------------

DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "deepseek": {"input": 0.14, "output": 0.28},
    "openai": {"input": 3.00, "output": 6.00},
    "anthropic": {"input": 3.00, "output": 15.00},
    "google": {"input": 0.075, "output": 0.30},
    "mistral": {"input": 2.00, "output": 6.00},
    "ollama": {"input": 0.0, "output": 0.0},
    "together": {"input": 0.88, "output": 0.88},
}


class CostIntelligenceService:
    """Service for computing and aggregating AI decision costs.

    Tracks actual LLM token usage and converts to monetary cost using
    provider-specific rates. Also computes risk exposure and opportunity
    cost to give a full picture of decision economics.
    """

    def __init__(self) -> None:
        self._pricing = dict(DEFAULT_PRICING)
        self._session_costs: dict[str, CostBreakdown] = {}
        self._analyst_hourly_rate = float(os.getenv("ANALYST_HOURLY_RATE", "150"))

        # Load custom pricing overrides from env
        for provider in self._pricing:
            env_input = os.getenv(f"LLM_PRICE_{provider.upper()}_INPUT")
            env_output = os.getenv(f"LLM_PRICE_{provider.upper()}_OUTPUT")
            if env_input:
                self._pricing[provider]["input"] = float(env_input)
            if env_output:
                self._pricing[provider]["output"] = float(env_output)

    def get_pricing(self) -> dict[str, dict[str, float]]:
        """Return current pricing configuration."""
        return dict(self._pricing)

    def update_pricing(self, provider: str, input_price: float, output_price: float) -> None:
        """Update pricing for a specific provider."""
        self._pricing[provider.lower()] = {"input": input_price, "output": output_price}

    def compute_llm_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str = "deepseek",
    ) -> float:
        """Compute LLM API cost from actual token counts.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            provider: LLM provider name

        Returns:
            Cost in USD
        """
        rates = self._pricing.get(provider.lower(), self._pricing["deepseek"])
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return round(input_cost + output_cost, 6)

    def compute_risk_exposure(
        self,
        risk_score: float,
        financial_exposure: float = 0.0,
    ) -> float:
        """Compute risk exposure cost.

        Args:
            risk_score: Guardian risk score (0-1)
            financial_exposure: Maximum financial exposure in USD

        Returns:
            Risk-adjusted exposure in USD
        """
        if financial_exposure <= 0:
            return 0.0
        return round(risk_score * financial_exposure, 2)

    def compute_opportunity_cost(
        self,
        decision_time_seconds: float,
    ) -> float:
        """Compute opportunity cost based on analyst time equivalent.

        Args:
            decision_time_seconds: Time taken for AI analysis

        Returns:
            Equivalent human analyst cost in USD
        """
        hours = decision_time_seconds / 3600
        return round(hours * self._analyst_hourly_rate, 2)

    def compute_full_breakdown(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        provider: str = "deepseek",
        compute_time_ms: float = 0.0,
        risk_score: float = 0.0,
        financial_exposure: float = 0.0,
    ) -> CostBreakdown:
        """Compute a complete cost breakdown for a query.

        Args:
            session_id: Session identifier
            input_tokens: LLM input tokens
            output_tokens: LLM output tokens
            provider: LLM provider name
            compute_time_ms: Total pipeline compute time
            risk_score: Guardian risk score (0-1)
            financial_exposure: Max financial exposure

        Returns:
            Complete CostBreakdown
        """
        llm_cost = self.compute_llm_cost(input_tokens, output_tokens, provider)
        risk_exposure = self.compute_risk_exposure(risk_score, financial_exposure)
        opportunity_cost = self.compute_opportunity_cost(compute_time_ms / 1000)

        items = [
            CostBreakdownItem(
                category="llm",
                label="LLM API Token Cost",
                amount=llm_cost,
                details={
                    "provider": provider,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            ),
            CostBreakdownItem(
                category="compute",
                label="Compute Time",
                amount=round(compute_time_ms / 1000 * 0.01, 4),  # $0.01/sec estimate
                details={"compute_time_ms": compute_time_ms},
            ),
            CostBreakdownItem(
                category="risk",
                label="Risk Exposure",
                amount=risk_exposure,
                details={
                    "risk_score": risk_score,
                    "financial_exposure": financial_exposure,
                },
            ),
            CostBreakdownItem(
                category="opportunity",
                label="Opportunity Cost (Time Saved)",
                amount=opportunity_cost,
                details={
                    "analyst_hourly_rate": self._analyst_hourly_rate,
                    "compute_time_seconds": compute_time_ms / 1000,
                },
            ),
        ]

        total = sum(item.amount for item in items)

        breakdown = CostBreakdown(
            session_id=session_id,
            llm_token_cost=llm_cost,
            llm_tokens_used=input_tokens + output_tokens,
            llm_input_tokens=input_tokens,
            llm_output_tokens=output_tokens,
            llm_provider=provider,
            compute_time_ms=compute_time_ms,
            risk_exposure_score=risk_exposure,
            opportunity_cost=opportunity_cost,
            total_cost=round(total, 4),
            breakdown_items=items,
        )

        self._session_costs[session_id] = breakdown
        return breakdown

    def get_session_cost(self, session_id: str) -> CostBreakdown | None:
        """Get stored cost breakdown for a session."""
        return self._session_costs.get(session_id)

    def aggregate_costs(
        self,
        session_ids: list[str] | None = None,
    ) -> CostAggregate:
        """Aggregate costs across sessions.

        Args:
            session_ids: Specific sessions to aggregate. None = all.
        """
        if session_ids:
            costs = [self._session_costs[sid] for sid in session_ids if sid in self._session_costs]
        else:
            costs = list(self._session_costs.values())

        if not costs:
            return CostAggregate()

        total_cost = sum(c.total_cost for c in costs)
        total_tokens = sum(c.llm_tokens_used for c in costs)

        cost_by_category: dict[str, float] = {}
        cost_by_provider: dict[str, float] = {}
        for c in costs:
            for item in c.breakdown_items:
                cost_by_category[item.category] = cost_by_category.get(item.category, 0) + item.amount
            cost_by_provider[c.llm_provider] = cost_by_provider.get(c.llm_provider, 0) + c.llm_token_cost

        return CostAggregate(
            total_sessions=len(costs),
            total_cost=round(total_cost, 4),
            average_cost_per_query=round(total_cost / len(costs), 4) if costs else 0,
            total_tokens=total_tokens,
            cost_by_category=cost_by_category,
            cost_by_provider=cost_by_provider,
        )

    def get_roi_metrics(
        self,
        session_ids: list[str] | None = None,
        manual_hours_estimate: float = 4.0,
    ) -> ROIMetrics:
        """Compute ROI metrics for AI-assisted decisions.

        Args:
            session_ids: Sessions to include
            manual_hours_estimate: Estimated hours for manual equivalent analysis
        """
        aggregate = self.aggregate_costs(session_ids)
        ai_cost = aggregate.total_cost
        manual_cost = manual_hours_estimate * self._analyst_hourly_rate * aggregate.total_sessions

        roi = ((manual_cost - ai_cost) / ai_cost * 100) if ai_cost > 0 else 0

        return ROIMetrics(
            ai_analysis_cost=round(ai_cost, 2),
            manual_analysis_estimate=round(manual_cost, 2),
            time_saved_hours=round(manual_hours_estimate * aggregate.total_sessions, 1),
            roi_percentage=round(roi, 1),
            insights_generated=aggregate.total_sessions,
            decisions_supported=aggregate.total_sessions,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_cost_service: CostIntelligenceService | None = None


def get_cost_service() -> CostIntelligenceService:
    """Get or create the cost intelligence service singleton."""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostIntelligenceService()
    return _cost_service
