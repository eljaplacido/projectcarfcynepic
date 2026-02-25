# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""CARF Benchmarks package.

Provides shared utilities for reproducible benchmark execution.
"""

from __future__ import annotations

import datetime
import os
import platform
import subprocess
import sys
from pathlib import Path
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
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "seed": seed,
    }


def finalize_benchmark_report(
    report: dict[str, Any],
    benchmark_id: str,
    source_reference: str | None = None,
    dataset_context: dict[str, Any] | None = None,
    sample_context: dict[str, Any] | None = None,
    benchmark_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach standardized provenance metadata to benchmark results.

    Required evidence dimensions for realism validation:
    - timestamp metadata
    - run configuration
    - dataset context
    - sample context
    - provenance/source reference
    """
    payload = dict(report)
    meta = get_benchmark_metadata()

    # Timestamp + identity
    payload.setdefault("generated_at", meta["timestamp"])
    payload.setdefault("benchmark_id", benchmark_id)
    payload.setdefault("methodology", "scripted_benchmark_v1")

    # Config context (provider/model/git/platform)
    existing_cfg = payload.get("benchmark_config")
    combined_cfg: dict[str, Any] = {}
    if isinstance(existing_cfg, dict):
        combined_cfg.update(existing_cfg)
    if isinstance(benchmark_config, dict):
        combined_cfg.update(benchmark_config)
    combined_cfg.setdefault("llm_provider", meta.get("llm_provider"))
    combined_cfg.setdefault("llm_model", meta.get("llm_model"))
    combined_cfg.setdefault("git_hash", meta.get("git_hash"))
    combined_cfg.setdefault("platform", meta.get("platform"))
    combined_cfg.setdefault("python_version", meta.get("python_version"))
    payload["benchmark_config"] = combined_cfg

    # Dataset context (allow benchmark-local overrides)
    existing_dataset = payload.get("dataset_context")
    ds_ctx: dict[str, Any] = {}
    if isinstance(existing_dataset, dict):
        ds_ctx.update(existing_dataset)
    if isinstance(dataset_context, dict):
        ds_ctx.update(dataset_context)
    ds_ctx.setdefault("dataset_profile", payload.get("dataset_profile", "unknown"))
    ds_ctx.setdefault("data_source", payload.get("data_source", "benchmark_dataset"))
    payload["dataset_context"] = ds_ctx

    # Sample context from common counters if not provided
    existing_sample = payload.get("sample_context")
    sm_ctx: dict[str, Any] = {}
    if isinstance(existing_sample, dict):
        sm_ctx.update(existing_sample)
    if isinstance(sample_context, dict):
        sm_ctx.update(sample_context)
    for key in (
        "total_scenarios",
        "total_queries",
        "total_cases",
        "queries_processed",
        "n_queries",
        "total_data_rows",
        "rows",
        "samples",
    ):
        if key in payload and key not in sm_ctx:
            sm_ctx[key] = payload[key]
    payload["sample_context"] = sm_ctx

    # Provenance
    src_ref = (
        source_reference
        or payload.get("source_reference")
        or f"benchmark:{benchmark_id}"
    )
    payload["source_reference"] = src_ref
    provenance = payload.get("provenance")
    provenance_dict: dict[str, Any] = provenance if isinstance(provenance, dict) else {}
    provenance_dict.setdefault("source_reference", src_ref)
    provenance_dict.setdefault("generated_by", "carf_benchmark_runner")
    provenance_dict.setdefault("result_schema", "benchmark_result_v2")
    provenance_dict.setdefault("script", str(Path(__file__).resolve()))
    payload["provenance"] = provenance_dict

    return payload
