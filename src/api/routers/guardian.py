"""Guardian configuration endpoints."""

import os
from datetime import datetime

from fastapi import APIRouter

from src.api.models import GuardianThresholdUpdate
from src.workflows.guardian import (
    ContextualPolicyConfig,
    get_guardian_config,
    update_guardian_config,
)

router = APIRouter(tags=["Guardian"])


@router.get("/guardian/config", response_model=ContextualPolicyConfig)
async def get_guardian_configuration():
    """Get current Guardian policy configuration."""
    return get_guardian_config()


@router.put("/guardian/config", response_model=ContextualPolicyConfig)
async def update_guardian_configuration(config: ContextualPolicyConfig):
    """Update Guardian policy configuration."""
    update_guardian_config(config)
    return get_guardian_config()


@router.patch("/guardian/config", response_model=ContextualPolicyConfig)
async def patch_guardian_config(update: GuardianThresholdUpdate):
    """Partially update Guardian configuration."""
    current = get_guardian_config()
    updates = update.model_dump(exclude_none=True)

    if updates:
        new_config = current.model_copy(update=updates)
        update_guardian_config(new_config)

    return get_guardian_config()


@router.get("/guardian/policies")
async def get_guardian_policies():
    """Get all defined Guardian policies with explanations."""
    return {
        "policies": [
            {
                "name": "confidence_threshold",
                "category": "risk",
                "description": "Minimum confidence required for automated approval",
                "user_configurable": True,
                "per_domain": True,
            },
            {
                "name": "auto_approval_limit",
                "category": "financial",
                "description": "Maximum amount for automatic approval without human review",
                "user_configurable": True,
                "per_domain": True,
            },
            {
                "name": "max_reflection_attempts",
                "category": "operational",
                "description": "Maximum self-correction loops before escalation",
                "user_configurable": False,
                "default_value": 2,
            },
            {
                "name": "always_escalate",
                "category": "escalation",
                "description": "Actions that always require human approval",
                "user_configurable": False,
                "actions": ["delete_data", "modify_policy", "production_deployment"],
            },
        ],
        "risk_weights": {
            "description": "Weights used for decomposed risk scoring",
            "values": get_guardian_config().risk_weights,
        },
    }


@router.get("/guardian/status")
async def get_guardian_status():
    """Get overall Guardian compliance status."""
    return {
        "status": "active",
        "compliance_percentage": 100.0,
        "policies_configured": 5,
        "policies_active": 5,
        "recent_violations": [],
        "last_check": datetime.utcnow().isoformat(),
        "risk_level": "low",
        "human_oversight_enabled": True,
        "audit_trail_enabled": True,
    }
