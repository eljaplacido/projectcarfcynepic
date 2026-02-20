"""Router Retraining from Feedback — extract domain override feedback for DistilBERT fine-tuning.

Reads domain_overrides from the CARF feedback SQLite database and exports
training data in JSONL format suitable for DistilBERT fine-tuning.

Usage:
    python scripts/retrain_router_from_feedback.py --dry-run
    python scripts/retrain_router_from_feedback.py --output training_data.jsonl
    python scripts/retrain_router_from_feedback.py --db-path var/carf_feedback.db --min-samples 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("carf.retrain")

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


VALID_DOMAINS = {"clear", "complicated", "complex", "chaotic", "disorder"}


def extract_training_data(db_path: Path) -> list[dict]:
    """Read domain_overrides from SQLite and return formatted training data.

    Each record maps a query to the user-corrected domain label.
    """
    if not db_path.exists():
        logger.warning(f"Database not found: {db_path}")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT query, original_domain, correct_domain, timestamp FROM domain_overrides ORDER BY timestamp"
        ).fetchall()
    except sqlite3.OperationalError:
        logger.warning("domain_overrides table not found")
        return []
    finally:
        conn.close()

    data = []
    for row in rows:
        query = row["query"]
        correct_domain = (row["correct_domain"] or "").lower()

        if not query or correct_domain not in VALID_DOMAINS:
            continue

        data.append({
            "query": query,
            "original_domain": (row["original_domain"] or "").lower(),
            "correct_domain": correct_domain,
            "timestamp": row["timestamp"],
        })

    return data


def validate_training_data(
    data: list[dict],
    min_samples_per_domain: int = 3,
) -> dict:
    """Validate training data quality.

    Checks:
    - Minimum samples per domain
    - Contradiction detection (same query, different labels)

    Returns:
        Validation report with issues and statistics.
    """
    domain_counts = Counter(d["correct_domain"] for d in data)
    total = len(data)

    # Check min samples
    insufficient_domains = {
        domain: count
        for domain, count in domain_counts.items()
        if count < min_samples_per_domain
    }

    # Detect contradictions: same query mapped to different domains
    query_labels: dict[str, set[str]] = {}
    for item in data:
        query_labels.setdefault(item["query"], set()).add(item["correct_domain"])

    contradictions = {
        query: list(labels)
        for query, labels in query_labels.items()
        if len(labels) > 1
    }

    issues = []
    if insufficient_domains:
        issues.append(f"Insufficient samples: {insufficient_domains}")
    if contradictions:
        issues.append(f"Contradictions found: {len(contradictions)} queries with conflicting labels")

    return {
        "total_samples": total,
        "domain_distribution": dict(domain_counts),
        "insufficient_domains": insufficient_domains,
        "contradictions": contradictions,
        "issues": issues,
        "ready_for_retraining": len(issues) == 0 and total >= min_samples_per_domain,
    }


def export_training_jsonl(data: list[dict], output_path: Path) -> int:
    """Export training data as JSONL for DistilBERT fine-tuning.

    Format: {"text": "<query>", "label": "<domain>"}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "w") as f:
        for item in data:
            record = {
                "text": item["query"],
                "label": item["correct_domain"],
            }
            f.write(json.dumps(record) + "\n")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Extract Router retraining data from feedback")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=_PROJECT_ROOT / "var" / "carf_feedback.db",
        help="Path to feedback SQLite database",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_PROJECT_ROOT / "var" / "router_training_data.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--min-samples", type=int, default=3, help="Min samples per domain")
    parser.add_argument("--dry-run", action="store_true", help="Only validate, don't export")
    args = parser.parse_args()

    logger.info(f"Extracting training data from {args.db_path}")
    data = extract_training_data(args.db_path)

    if not data:
        logger.info("No domain overrides found. Nothing to export.")
        return

    logger.info(f"Found {len(data)} domain override records")

    # Validate
    report = validate_training_data(data, min_samples_per_domain=args.min_samples)
    logger.info(f"Validation: {json.dumps(report, indent=2, default=str)}")

    if report["issues"]:
        for issue in report["issues"]:
            logger.warning(f"  Issue: {issue}")

    if args.dry_run:
        logger.info("Dry run complete. No files written.")
        return

    # Export
    count = export_training_jsonl(data, args.output)
    logger.info(f"Exported {count} records to {args.output}")


if __name__ == "__main__":
    main()
