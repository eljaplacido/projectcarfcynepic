# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Feedback API router — closed-loop learning from user input.

Implements the feedback loop identified in platform evaluation §2.6:
- User feedback on analysis quality (correct/wrong/refine)
- Domain override corrections for Router retraining
- Issue reports and improvement suggestions
- Feedback persisted to SQLite for downstream learning pipelines
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.database import execute, get_connection, is_postgres

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
# SQLite-backed feedback store
# ============================================================================

class FeedbackStore:
    """Persistent feedback storage backed by SQLite."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or Path(
            os.getenv("CARF_DATA_DIR", Path(__file__).resolve().parents[3] / "var")
        ) / "carf_feedback.db"
        if not is_postgres():
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        if is_postgres():
            with get_connection() as conn:
                yield conn
        else:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            execute(conn, """
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    context TEXT DEFAULT '{}',
                    rating INTEGER,
                    correct_domain TEXT,
                    received_at TEXT NOT NULL
                )
            """)
            execute(conn, """
                CREATE TABLE IF NOT EXISTS domain_overrides (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    original_domain TEXT,
                    correct_domain TEXT,
                    query TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

    def add(self, item: dict[str, Any]) -> str:
        feedback_id = str(uuid4())[:12]
        received_at = datetime.now(UTC).isoformat()

        with self._conn() as conn:
            execute(conn,
                "INSERT INTO feedback (feedback_id, type, description, context, rating, correct_domain, received_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    feedback_id,
                    item.get("type", "unknown"),
                    item.get("description", ""),
                    json.dumps(item.get("context", {})),
                    item.get("rating"),
                    item.get("correct_domain"),
                    received_at,
                ),
            )

            # Track domain overrides separately for Router retraining
            if item.get("type") == "domain_override" and item.get("correct_domain"):
                execute(conn,
                    "INSERT INTO domain_overrides (feedback_id, session_id, original_domain, correct_domain, query, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        feedback_id,
                        item.get("context", {}).get("sessionId"),
                        item.get("context", {}).get("domain"),
                        item["correct_domain"],
                        item.get("context", {}).get("query"),
                        received_at,
                    ),
                )

        return feedback_id

    _FEEDBACK_COLS = ("feedback_id", "type", "description", "context", "rating", "correct_domain", "received_at")
    _OVERRIDE_COLS = ("feedback_id", "session_id", "original_domain", "correct_domain", "query", "timestamp")

    def _row_to_dict(self, row: Any, columns: tuple[str, ...] = _FEEDBACK_COLS) -> dict[str, Any]:
        if isinstance(row, dict):
            d = row
        elif hasattr(row, "keys"):
            # sqlite3.Row
            d = dict(row)
        else:
            # tuple from psycopg2
            d = dict(zip(columns, row))
        if "context" in d and isinstance(d["context"], str):
            d["context"] = json.loads(d["context"])
        return d

    def get_summary(self) -> dict[str, Any]:
        with self._conn() as conn:
            rows = execute(conn, "SELECT * FROM feedback ORDER BY received_at DESC").fetchall()
            items = [self._row_to_dict(r, self._FEEDBACK_COLS) for r in rows]

            by_type: dict[str, int] = {}
            ratings: list[int] = []
            for item in items:
                t = item.get("type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
                if item.get("rating") is not None:
                    ratings.append(item["rating"])

            overrides = [
                self._row_to_dict(r, self._OVERRIDE_COLS)
                for r in execute(conn, "SELECT * FROM domain_overrides ORDER BY timestamp DESC").fetchall()
            ]

        return {
            "total_items": len(items),
            "by_type": by_type,
            "avg_rating": sum(ratings) / len(ratings) if ratings else None,
            "domain_overrides": overrides,
            "recent_items": items[:20],
        }

    def get_domain_overrides(self) -> list[dict[str, Any]]:
        """Get domain overrides for Router retraining pipeline."""
        with self._conn() as conn:
            rows = execute(conn, "SELECT * FROM domain_overrides ORDER BY timestamp DESC").fetchall()
            return [self._row_to_dict(r, self._OVERRIDE_COLS) for r in rows]

    def get_all(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = execute(conn, "SELECT * FROM feedback ORDER BY received_at DESC").fetchall()
            return [self._row_to_dict(r, self._FEEDBACK_COLS) for r in rows]


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
        received_at=datetime.now(UTC).isoformat(),
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


@router.get("/feedback/retraining-readiness")
async def check_retraining_readiness():
    """Check if there's enough domain override feedback for Router retraining.

    Returns total overrides, distribution across domains, and a recommendation.
    """
    store = get_feedback_store()
    overrides = store.get_domain_overrides()

    domain_distribution: dict[str, int] = {}
    for override in overrides:
        domain = (override.get("correct_domain") or "unknown").lower()
        domain_distribution[domain] = domain_distribution.get(domain, 0) + 1

    total = len(overrides)
    min_per_domain = 3
    has_enough = total >= 10 and all(
        count >= min_per_domain
        for count in domain_distribution.values()
    )

    if total == 0:
        recommendation = "No domain overrides collected yet. Encourage users to correct misclassifications."
    elif total < 10:
        recommendation = f"Only {total} overrides collected. Need at least 10 for meaningful retraining."
    elif not has_enough:
        under_represented = [d for d, c in domain_distribution.items() if c < min_per_domain]
        recommendation = f"Some domains under-represented ({under_represented}). Collect more samples for these."
    else:
        recommendation = "Ready for retraining. Run: python scripts/retrain_router_from_feedback.py"

    return {
        "total_overrides": total,
        "domain_distribution": domain_distribution,
        "ready_for_retraining": has_enough,
        "recommendation": recommendation,
    }


@router.post("/feedback/retrain-router")
async def retrain_router():
    """Trigger keyword hint extraction from domain override feedback.

    Reads domain overrides, extracts frequent terms per corrected domain,
    and returns new keyword hints. Non-destructive: does not modify the
    running router directly.
    """
    from src.services.router_retraining_service import get_router_retraining_service

    service = get_router_retraining_service()

    if not service.should_retrain(min_samples=5):
        overrides = service.get_training_data()
        return {
            "status": "insufficient_data",
            "total_overrides": len(overrides),
            "min_required": 5,
            "message": "Not enough domain overrides for meaningful retraining.",
        }

    hints = service.retrain_keyword_hints()

    return {
        "status": "hints_extracted",
        "keyword_hints": hints,
        "total_domains": len(hints),
        "message": (
            "Keyword hints extracted from domain overrides. "
            "Apply these to DATA_STRUCTURE_HINTS in the router configuration."
        ),
    }


@router.get("/feedback/export")
async def export_feedback():
    """Export all feedback as JSON for analysis."""
    store = get_feedback_store()
    items = store.get_all()
    return {
        "count": len(items),
        "items": items,
        "export_timestamp": datetime.now(UTC).isoformat(),
    }
