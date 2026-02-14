"""Router configuration endpoints."""

from fastapi import APIRouter

from src.api.models import RouterThresholdUpdate
from src.workflows.router import (
    DATA_STRUCTURE_HINTS,
    RouterConfig,
    get_router_config,
    update_router_config,
)

router = APIRouter(tags=["Router"])


@router.get("/router/config", response_model=RouterConfig)
async def get_router_configuration():
    """Get current Cynefin Router configuration."""
    return get_router_config()


@router.put("/router/config", response_model=RouterConfig)
async def update_router_configuration(config: RouterConfig):
    """Update Cynefin Router configuration."""
    update_router_config(config)
    return get_router_config()


@router.patch("/router/config", response_model=RouterConfig)
async def patch_router_thresholds(update: RouterThresholdUpdate):
    """Partially update router thresholds."""
    current = get_router_config()
    updates = update.model_dump(exclude_none=True)

    if updates:
        new_config = current.model_copy(update=updates)
        update_router_config(new_config)

    return get_router_config()


@router.get("/router/hints")
async def get_router_hints():
    """Get data structure and query patterns used for domain hints."""
    return {
        "data_structure_hints": DATA_STRUCTURE_HINTS,
        "description": "Patterns used to detect domain from data structure and query text"
    }
