"""Unit tests for dataset registry."""

from __future__ import annotations

import pytest

from src.services.dataset_store import DatasetStore


def test_create_and_list_dataset() -> None:
    store = DatasetStore(max_rows=10, storage_mode="memory")
    metadata = store.create_dataset(
        name="demo",
        description="test",
        data=[{"a": 1, "b": 2}, {"a": 3, "b": 4}],
    )

    assert metadata.row_count == 2
    assert metadata.column_names == ["a", "b"]

    datasets = store.list_datasets()
    assert len(datasets) == 1
    assert datasets[0].dataset_id == metadata.dataset_id

    preview = store.load_preview(metadata.dataset_id, limit=1)
    assert preview == [{"a": 1, "b": 2}]

    data = store.load_dataset_data(metadata.dataset_id)
    assert data == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


def test_create_dataset_from_columns() -> None:
    store = DatasetStore(max_rows=10, storage_mode="memory")
    metadata = store.create_dataset(
        name="columns",
        description=None,
        data={"x": [1, 2], "y": [3, 4]},
    )

    assert metadata.row_count == 2
    assert metadata.column_names == ["x", "y"]


def test_dataset_row_limit() -> None:
    store = DatasetStore(max_rows=2, storage_mode="memory")
    with pytest.raises(ValueError, match="exceeds"):
        store.create_dataset(
            name="too_big",
            description=None,
            data=[{"a": 1}, {"a": 2}, {"a": 3}],
        )
