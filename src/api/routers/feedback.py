"""Feedback API router — closed-loop learning from user input.

Implements the feedback loop identified in platform evaluation §2.6:
- User feedback on analysis quality (correct/wrong/refine)
- Domain override corrections for Router retraining
- Issue reports and improvement suggestions
- Feedback persisted for downstream learning pipelines
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.feedback")
router = APIRouter(tags=["Feedback"])


# ============================================================================
# Models
# ============================================================================

class FeedbackItem(BaseModel):
    """A single feedback item from the user."""
    type: str = Field(
        ...,
        description="Feedback type: 'issue', 'improvement', 'domain_override', 'quality_rating'",
    )
    description: str = Field(..., min_length=1, description="Feedback text")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Session context (sessionId, domain, confidence, etc.)",
    )
    rating: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Quality rating 1-5 (for quality_rating type)",
    )
    correct_domain: str | None = Field(
        None,
        description="User-corrected domain (for domain_override type)",
    )


class FeedbackResponse(BaseModel):
    """Response after feedback submission."""
    feedback_id: str
    status: str
    message: str
    received_at: str


class FeedbackSummary(BaseModel):
    """Aggregated feedback summary."""
    total_items: int
    by_type: dict[str, int]
    avg_rating: float | None
    domain_overrides: list[dict[str, Any]]
    recent_items: list[dict[str, Any]]


# ============================================================================
# In-memory feedback store (production: persist to DB/LightRAG)
# ============================================================================

class FeedbackStore:
    """Thread-safe feedback storage with bounded capacity."""

    def __init__(self, max_items: int = 5000):
        from collections import deque
        self._items: deque[dict[str, Any]] = deque(maxlen=max_items)
        self._domain_overrides: deque[dict[str, Any]] = deque(maxlen=1000)

    def add(self, item: dict[str, Any]) -> str:
        feedback_id = str(uuid4())[:12]
        record = {
            "feedback_id": feedback_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            **item,
        }
        self._items.append(record)

        # Track domain overrides separately for Router retraining
        if item.get("type") == "domain_override" and item.get("correct_domain"):
            self._domain_overrides.append({
                "feedback_id": feedback_id,
                "session_id": item.get("context", {}).get("sessionId"),
                "original_domain": item.get("context", {}).get("domain"),
                "correct_domain": item["correct_domain"],
                "query": item.get("context", {}).get("query"),
                "timestamp": record["received_at"],
            })

        return feedback_id

    def get_summary(self) -> dict[str, Any]:
        items = list(self._items)
        by_type: dict[str, int] = {}
        ratings: list[int] = []

        for item in items:
            t = item.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            if item.get("rating") is not None:
                ratings.append(item["rating"])

        return {
            "total_items": len(items),
            "by_type": by_type,
            "avg_rating": sum(ratings) / len(ratings) if ratings else None,
            "domain_overrides": list(self._domain_overrides),
            "recent_items": items[-20:],
        }

    def get_domain_overrides(self) -> list[dict[str, Any]]:
        """Get domain overrides for Router retraining pipeline."""
        return list(self._domain_overrides)

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._items)


_feedback_store: FeedbackStore | None = None


def get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(item: FeedbackItem):
    """Submit user feedback on analysis quality.

    Feedback types:
    - **issue**: Report a problem with analysis results
    - **improvement**: Suggest an improvement
    - **domain_override**: Correct a Cynefin domain classification
    - **quality_rating**: Rate analysis quality (1-5)
    """
    store = get_feedback_store()
    feedback_id = store.add(item.model_dump())

    logger.info(
        f"Feedback received: type={item.type} id={feedback_id} "
        f"session={item.context.get('sessionId', 'unknown')}"
    )

    return FeedbackResponse(
        feedback_id=feedback_id,
        status="received",
        message="Feedback recorded. Thank you for helping improve the platform.",
        received_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/feedback/summary", response_model=FeedbackSummary)
async def get_feedback_summary():
    """Get aggregated feedback summary for monitoring and learning."""
    store = get_feedback_store()
    return store.get_summary()


@router.get("/feedback/domain-overrides")
async def get_domain_overrides():
    """Get domain override feedback for Router retraining pipeline.

    Returns user-corrected domain classifications that can be used to:
    1. Fine-tune the DistilBERT classifier
    2. Adjust confidence thresholds
    3. Update DATA_STRUCTURE_HINTS
    """
    store = get_feedback_store()
    overrides = store.get_domain_overrides()
    return {
        "count": len(overrides),
        "overrides": overrides,
        "usage": "Feed these into the Router retraining pipeline (see docs/ROUTER_TRAINING.md)",
    }


@router.get("/feedback/export")
async def export_feedback():
    """Export all feedback as JSON for analysis."""
    store = get_feedback_store()
    items = store.get_all()
    return {
        "count": len(items),
        "items": items,
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
    }
