# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Database connection factory — SQLite locally, PostgreSQL in cloud.

Reads ``DATABASE_URL`` env var:
  - Starts with ``postgresql://`` → psycopg2 connection
  - Otherwise → SQLite at the given path (or default ``var/`` directory)

Both backends use ``?`` parameter style so existing SQL stays unchanged.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger("carf.database")

_database_url: str | None = None


def _get_database_url() -> str | None:
    global _database_url
    if _database_url is None:
        _database_url = os.environ.get("DATABASE_URL", "")
    return _database_url or None


def is_postgres() -> bool:
    """Return True if the configured database is PostgreSQL."""
    url = _get_database_url()
    return bool(url and url.startswith("postgresql://"))


@contextmanager
def get_connection(
    sqlite_path: Path | str | None = None,
) -> Generator[Any, None, None]:
    """Yield a DB-API 2.0 connection.

    - If ``DATABASE_URL`` starts with ``postgresql://``, returns a psycopg2 connection.
    - Otherwise, returns a sqlite3 connection to *sqlite_path*.

    The caller is responsible for calling ``conn.commit()`` when needed.
    The connection is closed when the context manager exits.
    """
    if is_postgres():
        import psycopg2
        import psycopg2.extensions

        conn = psycopg2.connect(_get_database_url())
        # Use pyformat paramstyle by default; we'll adapt SQL at call sites
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        path = str(sqlite_path) if sqlite_path else ":memory:"
        conn = sqlite3.connect(path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def execute(conn: Any, sql: str, params: tuple = ()) -> Any:
    """Execute a SQL statement, adapting ``?`` placeholders for PostgreSQL.

    SQLite uses ``?`` for parameter markers, PostgreSQL (psycopg2) uses ``%s``.
    This helper transparently rewrites ``?`` → ``%s`` when running on Postgres
    so that all SQL in the codebase can use ``?`` style consistently.
    """
    if is_postgres():
        sql = sql.replace("?", "%s")
    cursor = conn.execute(sql, params)
    return cursor


def executemany(conn: Any, sql: str, params_seq: list[tuple]) -> None:
    """Execute a SQL statement with multiple parameter sets."""
    if is_postgres():
        sql = sql.replace("?", "%s")
    conn.executemany(sql, params_seq)
