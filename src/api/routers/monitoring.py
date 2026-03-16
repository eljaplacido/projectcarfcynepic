"""Monitoring API Router — Phase 18 operational intelligence endpoints.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Endpoints:
    GET  /monitoring/drift           — Drift detection status
    GET  /monitoring/drift/history   — Recent drift snapshots
    POST /monitoring/drift/reset     — Reset drift baseline
    GET  /monitoring/bias-audit      — Run bias audit on agent memory
    GET  /monitoring/convergence     — Retraining convergence status
    POST /monitoring/convergence/record — Record retraining accuracy
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.api.monitoring")

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ---------------------------------------------------------------------------
# Drift Detection (Phase 18A)
# ---------------------------------------------------------------------------


@router.get("/drift")
async def get_drift_status():
    """Get current drift monitoring status.

    Returns routing distribution, baseline, KL-divergence, and alerts.
    """
    from src.services.drift_detector import get_drift_detector

    detector = get_drift_detector()
    return detector.get_status()


@router.get("/drift/history")
async def get_drift_history(limit: int = 20):
    """Get recent drift detection snapshots."""
    from src.services.drift_detector import get_drift_detector

    detector = get_drift_detector()
    return {"snapshots": detector.get_history(limit=limit)}


@router.post("/drift/reset")
async def reset_drift_baseline():
    """Force recalculate drift baseline from current observations."""
    from src.services.drift_detector import get_drift_detector

    detector = get_drift_detector()
    detector.reset_baseline()
    return {"status": "baseline_reset", "new_status": detector.get_status()}


# ---------------------------------------------------------------------------
# Bias Auditing (Phase 18B)
# ---------------------------------------------------------------------------


@router.get("/bias-audit")
async def run_bias_audit():
    """Run a full bias audit on the agent memory corpus.

    Checks for:
    - Domain representation bias (chi-squared test)
    - Quality score disparity across domains
    - Guardian verdict disparity across domains
    """
    from src.services.bias_auditor import get_bias_auditor

    auditor = get_bias_auditor()
    report = auditor.audit()
    return report.model_dump()


# ---------------------------------------------------------------------------
# Convergence / Plateau Detection (Phase 18C)
# ---------------------------------------------------------------------------


@router.get("/convergence")
async def get_convergence_status():
    """Get retraining convergence monitoring status.

    Shows accuracy history, plateau detection, and recommendations.
    """
    from src.services.router_retraining_service import get_router_retraining_service

    service = get_router_retraining_service()
    return service.get_convergence_status()


class AccuracyRecord(BaseModel):
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy score (0-1)")
    epoch: int | None = Field(None, description="Optional epoch number")


@router.post("/convergence/record")
async def record_accuracy(record: AccuracyRecord):
    """Record a retraining accuracy measurement.

    Used after each retraining epoch to track convergence.
    """
    from src.services.router_retraining_service import get_router_retraining_service

    service = get_router_retraining_service()
    service.record_accuracy(record.accuracy, record.epoch)
    result = service.check_convergence()
    return {
        "status": "recorded",
        "convergence": result.model_dump(),
    }


# ---------------------------------------------------------------------------
# Unified Status
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_monitoring_status():
    """Get unified monitoring status across all Phase 18 components."""
    from src.services.drift_detector import get_drift_detector
    from src.services.bias_auditor import get_bias_auditor
    from src.services.router_retraining_service import get_router_retraining_service

    drift = get_drift_detector()
    auditor = get_bias_auditor()
    retraining = get_router_retraining_service()

    bias_report = auditor.audit()

    return {
        "drift": drift.get_status(),
        "bias": {
            "overall_bias_detected": bias_report.overall_bias_detected,
            "findings_count": len(bias_report.findings),
            "findings": bias_report.findings,
        },
        "convergence": retraining.get_convergence_status(),
    }
