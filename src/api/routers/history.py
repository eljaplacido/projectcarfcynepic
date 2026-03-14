# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Per-user analysis history API — cloud-backed via the database abstraction.

Each analysis result is stored with the authenticated user's ID so that
different users see their own isolated history.

When running locally (research profile, no auth) the ``user_id`` defaults to
``"local"`` so the API still works during development.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.core.database import execute, get_connection, is_postgres

logger = logging.getLogger("carf.history")
router = APIRouter(tags=["History"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class HistoryEntry(BaseModel):
    query: str
    domain: str
    confidence: float = 0.0
    result_json: str = "{}"


class HistoryEntryResponse(BaseModel):
    id: str
    user_id: str
    query: str
    domain: str
    confidence: float
    result_json: str
    created_at: str


# ---------------------------------------------------------------------------
# Table init (called once)
# ---------------------------------------------------------------------------

_table_created = False


def _ensure_table() -> None:
    global _table_created
    if _table_created:
        return
    with get_connection(_sqlite_path()) as conn:
        execute(conn, """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                domain TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_history_user
            ON analysis_history(user_id, created_at)
        """)
    _table_created = True


def _sqlite_path() -> str | None:
    """Return the SQLite path for local dev, or None for Postgres."""
    if is_postgres():
        return None
    import os
    from pathlib import Path

    base = Path(os.getenv("CARF_DATA_DIR", Path(__file__).resolve().parents[3] / "var"))
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "carf_history.db")


def _get_user_id(request: Request) -> str:
    """Extract user_id from Firebase auth state, falling back to 'local'."""
    return getattr(request.state, "user_id", "local")


_COLS = ("id", "user_id", "query", "domain", "confidence", "result_json", "created_at")


def _row_to_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "keys"):
        return dict(row)
    return dict(zip(_COLS, row))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/history", response_model=HistoryEntryResponse)
async def save_history(entry: HistoryEntry, request: Request):
    """Save an analysis result to the user's history."""
    _ensure_table()
    user_id = _get_user_id(request)
    entry_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    with get_connection(_sqlite_path()) as conn:
        execute(conn,
            """INSERT INTO analysis_history
               (id, user_id, query, domain, confidence, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, user_id, entry.query, entry.domain,
             entry.confidence, entry.result_json, created_at),
        )

    return HistoryEntryResponse(
        id=entry_id,
        user_id=user_id,
        query=entry.query,
        domain=entry.domain,
        confidence=entry.confidence,
        result_json=entry.result_json,
        created_at=created_at,
    )


@router.get("/history")
async def list_history(request: Request):
    """List the authenticated user's analysis history (newest first)."""
    _ensure_table()
    user_id = _get_user_id(request)

    with get_connection(_sqlite_path()) as conn:
        rows = execute(conn,
            "SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    return {"items": [_row_to_dict(r) for r in rows]}


@router.delete("/history/{entry_id}")
async def delete_history(entry_id: str, request: Request):
    """Delete a single history entry (must belong to the authenticated user)."""
    _ensure_table()
    user_id = _get_user_id(request)

    with get_connection(_sqlite_path()) as conn:
        execute(conn,
            "DELETE FROM analysis_history WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )

    return {"status": "deleted", "id": entry_id}
