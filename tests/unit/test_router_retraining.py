"""Tests for Router retraining pipeline."""

import json
import sqlite3
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.retrain_router_from_feedback import (
    extract_training_data,
    validate_training_data,
    export_training_jsonl,
)


@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as d:
        yield Path(d)


def _create_test_db(db_path: Path, overrides: list[dict]) -> None:
    """Create a test SQLite database with domain_overrides."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE domain_overrides (
            feedback_id TEXT PRIMARY KEY,
            session_id TEXT,
            original_domain TEXT,
            correct_domain TEXT,
            query TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    for i, override in enumerate(overrides):
        conn.execute(
            "INSERT INTO domain_overrides VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"fb-{i}",
                override.get("session_id", "sess-1"),
                override.get("original_domain", "clear"),
                override["correct_domain"],
                override["query"],
                override.get("timestamp", "2026-01-01T00:00:00Z"),
            ),
        )
    conn.commit()
    conn.close()


class TestExtractTrainingData:
    """Tests for extract_training_data."""

    def test_extract_from_empty_db(self, temp_dir):
        """Empty database returns empty list."""
        db_path = temp_dir / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE domain_overrides (
                feedback_id TEXT, session_id TEXT, original_domain TEXT,
                correct_domain TEXT, query TEXT, timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

        data = extract_training_data(db_path)
        assert data == []

    def test_extract_with_overrides(self, temp_dir):
        """Populated database returns formatted training data."""
        db_path = temp_dir / "feedback.db"
        _create_test_db(db_path, [
            {"query": "What causes churn?", "correct_domain": "complicated"},
            {"query": "URGENT: system down", "correct_domain": "chaotic"},
            {"query": "Should we expand?", "correct_domain": "complex"},
        ])

        data = extract_training_data(db_path)
        assert len(data) == 3
        assert data[0]["query"] == "What causes churn?"
        assert data[0]["correct_domain"] == "complicated"

    def test_extract_skips_invalid_domains(self, temp_dir):
        """Invalid domain labels should be skipped."""
        db_path = temp_dir / "feedback.db"
        _create_test_db(db_path, [
            {"query": "Valid", "correct_domain": "complicated"},
            {"query": "Invalid", "correct_domain": "not_a_domain"},
        ])

        data = extract_training_data(db_path)
        assert len(data) == 1

    def test_extract_missing_db(self, temp_dir):
        """Missing database returns empty list."""
        data = extract_training_data(temp_dir / "nonexistent.db")
        assert data == []


class TestValidateTrainingData:
    """Tests for validate_training_data."""

    def test_validate_insufficient(self):
        """Too few samples per domain should be flagged."""
        data = [
            {"query": "q1", "correct_domain": "complicated"},
            {"query": "q2", "correct_domain": "complicated"},
        ]
        report = validate_training_data(data, min_samples_per_domain=3)
        assert "complicated" in report["insufficient_domains"]
        assert not report["ready_for_retraining"]

    def test_validate_contradictions(self):
        """Same query with different labels should be detected."""
        data = [
            {"query": "Ambiguous question", "correct_domain": "complicated"},
            {"query": "Ambiguous question", "correct_domain": "complex"},
            {"query": "Another query", "correct_domain": "clear"},
        ]
        report = validate_training_data(data, min_samples_per_domain=1)
        assert "Ambiguous question" in report["contradictions"]
        assert len(report["issues"]) > 0

    def test_validate_clean_data(self):
        """Clean data with enough samples should pass."""
        data = [
            {"query": f"Query {i}", "correct_domain": "complicated"}
            for i in range(10)
        ]
        report = validate_training_data(data, min_samples_per_domain=3)
        assert report["ready_for_retraining"] is True
        assert report["issues"] == []


class TestExportJsonl:
    """Tests for export_training_jsonl."""

    def test_export_jsonl_format(self, temp_dir):
        """Exported JSONL should have valid format."""
        data = [
            {"query": "What causes churn?", "correct_domain": "complicated"},
            {"query": "URGENT: system down", "correct_domain": "chaotic"},
        ]
        output = temp_dir / "train.jsonl"
        count = export_training_jsonl(data, output)

        assert count == 2
        assert output.exists()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2

        record = json.loads(lines[0])
        assert "text" in record
        assert "label" in record
        assert record["text"] == "What causes churn?"
        assert record["label"] == "complicated"


class TestRetrainingReadinessEndpoint:
    """Tests for the /feedback/retraining-readiness endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self):
        """API should return correct readiness status."""
        from httpx import AsyncClient, ASGITransport
        from src.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/feedback/retraining-readiness")

        assert response.status_code == 200
        body = response.json()
        assert "total_overrides" in body
        assert "domain_distribution" in body
        assert "ready_for_retraining" in body
        assert "recommendation" in body
