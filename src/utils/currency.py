# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Currency normalization utilities for financial policy enforcement.

Rates are configured via `CARF_FX_RATES_JSON` as JSON mapping:
    {"USD": 1.0, "EUR": 1.08, "JPY": 0.0067}
where each value is USD per one unit of the currency.

If only USD is configured, non-USD conversions are treated as unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("carf.currency")

_DEFAULT_RATES_USD_PER_UNIT = {"USD": 1.0}


@dataclass
class CurrencyNormalizationResult:
    """Result of currency amount normalization."""

    success: bool
    amount: float
    source_currency: str
    target_currency: str
    normalized_amount: float | None = None
    reason: str | None = None
    rate_source: str = "default_usd_only"



def _load_fx_rates_from_env() -> tuple[dict[str, float], str]:
    """Load FX rates from env, fallback to USD-only if absent/invalid."""
    raw = os.getenv("CARF_FX_RATES_JSON", "").strip()
    if not raw:
        return dict(_DEFAULT_RATES_USD_PER_UNIT), "default_usd_only"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid CARF_FX_RATES_JSON; using USD-only currency conversion")
        return dict(_DEFAULT_RATES_USD_PER_UNIT), "default_usd_only"

    if not isinstance(parsed, dict):
        logger.warning("CARF_FX_RATES_JSON must be a JSON object; using USD-only")
        return dict(_DEFAULT_RATES_USD_PER_UNIT), "default_usd_only"

    rates: dict[str, float] = {}
    for key, value in parsed.items():
        code = str(key).strip().upper()
        try:
            rate_val = float(value)
        except (TypeError, ValueError):
            continue
        if code and rate_val > 0:
            rates[code] = rate_val

    if "USD" not in rates:
        rates["USD"] = 1.0

    if len(rates) == 1:
        return rates, "default_usd_only"
    return rates, "env_json"



def normalize_currency_amount(
    amount: float,
    source_currency: str,
    target_currency: str,
) -> CurrencyNormalizationResult:
    """Normalize amount from source_currency into target_currency.

    Returns a structured result with success/failure reason rather than raising.
    """
    src = (source_currency or "USD").strip().upper()
    target = (target_currency or "USD").strip().upper()

    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return CurrencyNormalizationResult(
            success=False,
            amount=0.0,
            source_currency=src,
            target_currency=target,
            reason="invalid_amount",
        )

    if src == target:
        return CurrencyNormalizationResult(
            success=True,
            amount=amt,
            source_currency=src,
            target_currency=target,
            normalized_amount=amt,
            rate_source="identity",
        )

    rates, rate_source = _load_fx_rates_from_env()
    src_rate = rates.get(src)
    target_rate = rates.get(target)

    if src_rate is None or target_rate is None:
        missing = src if src_rate is None else target
        return CurrencyNormalizationResult(
            success=False,
            amount=amt,
            source_currency=src,
            target_currency=target,
            reason=f"missing_fx_rate:{missing}",
            rate_source=rate_source,
        )

    usd_amount = amt * src_rate
    normalized = usd_amount / target_rate
    return CurrencyNormalizationResult(
        success=True,
        amount=amt,
        source_currency=src,
        target_currency=target,
        normalized_amount=normalized,
        rate_source=rate_source,
    )



def get_currency_config_hint() -> dict[str, Any]:
    """Return active currency config metadata for explainability."""
    rates, source = _load_fx_rates_from_env()
    return {
        "rate_source": source,
        "configured_currencies": sorted(list(rates.keys())),
    }
