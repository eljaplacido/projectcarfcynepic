"""CARF Benchmarks package.

Provides shared utilities for reproducible benchmark execution.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


def get_benchmark_metadata(seed: int | None = None) -> dict[str, Any]:
    """Return metadata for benchmark reproducibility.

    Includes git hash, python version, platform, LLM provider/model,
    timestamp, and optional random seed.
    """
    # Git hash
    git_hash = "unknown"
    try:
        git_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        pass

    # LLM provider/model from environment
    llm_provider = os.environ.get("LLM_PROVIDER", "unknown")
    llm_model = os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "unknown"

    return {
        "git_hash": git_hash,
        "python_version": sys.version,
        "platform": platform.platform(),
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
    }
