"""Dataset registry for small research demo uploads."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("carf.dataset_store")


class DatasetMetadata(BaseModel):
    """Metadata for a stored dataset."""

    dataset_id: str
    name: str
    description: str | None = None
    created_at: str
    row_count: int
    column_names: list[str]
    storage_path: str


class DatasetStore:
    """Lightweight dataset registry backed by SQLite and JSON files."""

    def __init__(
        self,
        base_dir: Path | None = None,
        max_rows: int = 5000,
        storage_mode: str = "disk",
    ) -> None:
        self.base_dir = base_dir or Path(
            os.getenv("CARF_DATA_DIR", Path(__file__).resolve().parents[2] / "var")
        )
        self.data_dir = self.base_dir / "datasets"
        self.db_path = self.base_dir / "carf_datasets.db"
        self.max_rows = max_rows
        self.storage_mode = storage_mode
        self._connection: sqlite3.Connection | None = None
        self._init_storage()

    def _init_storage(self) -> None:
        if self.storage_mode == "memory":
            self._connection = sqlite3.connect(":memory:")
        else:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        with self._open_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    column_names TEXT NOT NULL,
                    storage_path TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_columns (
                    dataset_id TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_payloads (
                    dataset_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dataset_columns_name
                ON dataset_columns(column_name)
                """
            )

    @contextmanager
    def _open_conn(self) -> Any:
        if self.storage_mode == "memory":
            if self._connection is None:
                self._connection = sqlite3.connect(":memory:")
            yield self._connection
        else:
            with sqlite3.connect(self.db_path) as conn:
                yield conn

    def _normalize_data(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            if not all(isinstance(row, dict) for row in data):
                raise ValueError("Dataset rows must be objects")
            rows = data
        elif isinstance(data, dict):
            columns = list(data.keys())
            for values in data.values():
                if not isinstance(values, list):
                    raise ValueError("Dataset columns must be lists")
            lengths = {len(values) for values in data.values()}
            if len(lengths) > 1:
                raise ValueError("Dataset columns must have equal lengths")
            length = lengths.pop() if lengths else 0
            rows = []
            for idx in range(length):
                rows.append({col: data[col][idx] for col in columns})
        else:
            raise ValueError("Dataset data must be list[dict] or dict[str, list]")

        if len(rows) > self.max_rows:
            raise ValueError(f"Dataset exceeds {self.max_rows} rows")

        return rows

    def _column_names(self, rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return []
        columns = set()
        for row in rows:
            columns.update(row.keys())
        return sorted(columns)

    def create_dataset(
        self,
        name: str,
        description: str | None,
        data: Any,
    ) -> DatasetMetadata:
        rows = self._normalize_data(data)
        dataset_id = str(uuid4())
        created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        column_names = self._column_names(rows)
        if self.storage_mode == "memory":
            storage_path = "memory"
        else:
            storage_path = str(self.data_dir / f"{dataset_id}.json")
            with open(storage_path, "w", encoding="utf-8") as handle:
                json.dump(rows, handle, ensure_ascii=True)

        with self._open_conn() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    dataset_id, name, description, created_at, row_count,
                    column_names, storage_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    name,
                    description,
                    created_at,
                    len(rows),
                    json.dumps(column_names, ensure_ascii=True),
                    storage_path,
                ),
            )
            conn.executemany(
                "INSERT INTO dataset_columns (dataset_id, column_name) VALUES (?, ?)",
                [(dataset_id, column) for column in column_names],
            )
            if self.storage_mode == "memory":
                conn.execute(
                    "INSERT INTO dataset_payloads (dataset_id, payload) VALUES (?, ?)",
                    (dataset_id, json.dumps(rows, ensure_ascii=True)),
                )

        logger.info(
            "Stored dataset %s (%s rows, %s columns)",
            dataset_id,
            len(rows),
            len(column_names),
        )

        return DatasetMetadata(
            dataset_id=dataset_id,
            name=name,
            description=description,
            created_at=created_at,
            row_count=len(rows),
            column_names=column_names,
            storage_path=storage_path,
        )

    def list_datasets(self) -> list[DatasetMetadata]:
        with self._open_conn() as conn:
            cursor = conn.execute(
                """
                SELECT dataset_id, name, description, created_at, row_count,
                       column_names, storage_path
                FROM datasets
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()

        datasets = []
        for row in rows:
            datasets.append(
                DatasetMetadata(
                    dataset_id=row[0],
                    name=row[1],
                    description=row[2],
                    created_at=row[3],
                    row_count=row[4],
                    column_names=json.loads(row[5]),
                    storage_path=row[6],
                )
            )
        return datasets

    def get_dataset(self, dataset_id: str) -> DatasetMetadata:
        with self._open_conn() as conn:
            cursor = conn.execute(
                """
                SELECT dataset_id, name, description, created_at, row_count,
                       column_names, storage_path
                FROM datasets
                WHERE dataset_id = ?
                """,
                (dataset_id,),
            )
            row = cursor.fetchone()

        if not row:
            raise KeyError(f"Dataset not found: {dataset_id}")

        return DatasetMetadata(
            dataset_id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            row_count=row[4],
            column_names=json.loads(row[5]),
            storage_path=row[6],
        )

    def load_dataset_data(self, dataset_id: str) -> list[dict[str, Any]]:
        metadata = self.get_dataset(dataset_id)
        if self.storage_mode == "memory":
            with self._open_conn() as conn:
                cursor = conn.execute(
                    "SELECT payload FROM dataset_payloads WHERE dataset_id = ?",
                    (dataset_id,),
                )
                row = cursor.fetchone()
            if not row:
                raise FileNotFoundError("Dataset payload missing in memory")
            return json.loads(row[0])

        path = Path(metadata.storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file missing: {path}")

        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def load_preview(self, dataset_id: str, limit: int = 10) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        rows = self.load_dataset_data(dataset_id)
        return rows[:limit]


_dataset_store: DatasetStore | None = None


def get_dataset_store() -> DatasetStore:
    """Get or create the dataset store singleton."""
    global _dataset_store
    if _dataset_store is None:
        _dataset_store = DatasetStore()
    return _dataset_store
