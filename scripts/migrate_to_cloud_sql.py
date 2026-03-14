#!/usr/bin/env python3
# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""One-time migration: copy local SQLite data into Cloud SQL (PostgreSQL).

Usage:
    # Set DATABASE_URL to your Cloud SQL connection string first
    export DATABASE_URL="postgresql://carf_app:<password>@/<dbname>?host=/cloudsql/<INSTANCE_CONNECTION_NAME>"
    python scripts/migrate_to_cloud_sql.py

This reads from the local var/ SQLite databases and inserts into PostgreSQL.
Both DBs are tiny (~48KB combined), so this runs in seconds.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def migrate_datasets(pg_conn, sqlite_path: Path) -> int:
    """Migrate carf_datasets.db → Cloud SQL."""
    if not sqlite_path.exists():
        print(f"  Skipping {sqlite_path} (not found)")
        return 0

    lite = sqlite3.connect(str(sqlite_path))
    cur = lite.execute("SELECT * FROM datasets")
    rows = cur.fetchall()
    lite.close()

    if not rows:
        print("  No dataset rows to migrate")
        return 0

    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            column_names TEXT NOT NULL,
            storage_path TEXT NOT NULL
        )
    """)
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS dataset_columns (
            dataset_id TEXT NOT NULL,
            column_name TEXT NOT NULL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
        )
    """)
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS dataset_payloads (
            dataset_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
        )
    """)

    for row in rows:
        pg_cur.execute(
            "INSERT INTO datasets VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            row,
        )

    pg_conn.commit()
    print(f"  Migrated {len(rows)} dataset rows")
    return len(rows)


def migrate_feedback(pg_conn, sqlite_path: Path) -> int:
    """Migrate carf_feedback.db → Cloud SQL."""
    if not sqlite_path.exists():
        print(f"  Skipping {sqlite_path} (not found)")
        return 0

    lite = sqlite3.connect(str(sqlite_path))

    # Feedback table
    cur = lite.execute("SELECT * FROM feedback")
    feedback_rows = cur.fetchall()

    # Domain overrides table
    cur = lite.execute("SELECT * FROM domain_overrides")
    override_rows = cur.fetchall()

    lite.close()

    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
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
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS domain_overrides (
            feedback_id TEXT PRIMARY KEY,
            session_id TEXT,
            original_domain TEXT,
            correct_domain TEXT,
            query TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    for row in feedback_rows:
        pg_cur.execute(
            "INSERT INTO feedback VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            row,
        )
    for row in override_rows:
        pg_cur.execute(
            "INSERT INTO domain_overrides VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            row,
        )

    pg_conn.commit()
    print(f"  Migrated {len(feedback_rows)} feedback + {len(override_rows)} override rows")
    return len(feedback_rows) + len(override_rows)


def main():
    import os

    db_url = os.environ.get("DATABASE_URL")
    if not db_url or not db_url.startswith("postgresql://"):
        print("ERROR: Set DATABASE_URL to a postgresql:// connection string")
        sys.exit(1)

    import psycopg2

    print(f"Connecting to Cloud SQL...")
    pg_conn = psycopg2.connect(db_url)

    var_dir = PROJECT_ROOT / "var"

    print("\n[1/2] Migrating datasets...")
    migrate_datasets(pg_conn, var_dir / "carf_datasets.db")

    print("\n[2/2] Migrating feedback...")
    migrate_feedback(pg_conn, var_dir / "carf_feedback.db")

    # Also create the history table (empty, but ready)
    print("\n[bonus] Creating analysis_history table...")
    cur = pg_conn.cursor()
    cur.execute("""
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
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_user
        ON analysis_history(user_id, created_at)
    """)
    pg_conn.commit()

    pg_conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    main()
