"""Log-only decision-model shadow for the Cynefin router.

Copyright (c) 2026 Cisuregen
Licensed under the Business Source License 1.1 (BSL).
See LICENSE for details.

Asks a small local decision model (a llama.cpp server exposing ``/v1/systemone``) the
same routing question the router answers, and appends its answer next to what the
router actually decided: one JSON line per model, in the decision-shadow record format
(v1). The shadow never changes routing:

- **Off unless switched on** (``CARF_ROUTER_SHADOW=1``).
- **Log only.** Nothing is written to ``state`` or ``state.context``; the answer is
  never read back by CARF.
- **Fail open.** One bounded attempt per model with a hard timeout. Any failure becomes
  a row with ``error`` set and no ``probs`` (it measures availability) and is swallowed.
- **Off the critical path.** ``classify()`` schedules a background task and returns.
  Batch and benchmark runs set ``CARF_ROUTER_SHADOW_AWAIT=1`` to wait for it instead,
  so a short-lived event loop does not cancel the call. Past ``MAX_IN_FLIGHT`` pending
  calls no model is asked, but an error row is still written.

Exception to the AGENTS.md tenacity rule: the call is deliberately *not* retried. A
retry would only add load for an answer nothing waits on, and a missing answer is
itself the availability measurement.

Privacy: the request text is scrubbed of secrets before it is sent or logged. By
default the log keeps only its sha256; ``CARF_ROUTER_SHADOW_LOG_TEXT=1`` adds a
scrubbed excerpt of at most 200 characters.

Environment (read on every call, no import-time state):

- ``CARF_ROUTER_SHADOW``: ``1`` enables; anything else is off.
- ``CARF_ROUTER_SHADOW_URL``: default ``http://127.0.0.1:18195``.
- ``CARF_ROUTER_SHADOW_MODELS``: default ``vllm-d3``; a comma list asks each model
  (one row per model).
- ``CARF_ROUTER_SHADOW_TIMEOUT_S``: total time per call, default ``1.5`` seconds.
- ``CARF_ROUTER_SHADOW_AWAIT``: ``1`` awaits the shadow inside ``classify()``.
- ``CARF_ROUTER_SHADOW_LOG_TEXT``: ``1`` keeps a scrubbed 200-character excerpt.
- ``CARF_ROUTER_SHADOW_MACHINE``: the calibration key; else ``DECISION_SHADOW_MACHINE``,
  else the hostname.
- ``DECISION_SHADOW_DIR``: the log directory; else ``$CARF_DATA_DIR/decision-shadow``,
  else ``<repo>/var/decision-shadow``. The file is ``carf.jsonl``.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import socket
import threading
import time
from collections.abc import Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.router.shadow")

PROJECT = "carf"
DECISION = "route"
QUESTION_ID = "carf_router.v1"

# Byte-identical to the decision bench's "carf_router" question (decisionbench/tasks.py
# QUESTIONS). Do not reword it or reorder the options: the models' calibration is bound
# to this exact text, and option order changes answers.
SHADOW_QUESTION: dict[str, Any] = {
    "type": "choice",
    "instructions": "Which Cynefin domain does this request belong to, so it can be routed "
    "to the right kind of solver?",
    "criteria": {
        "clear": "a lookup, conversion or rule with one right answer",
        "complicated": "needs expert analysis or a model, but cause and effect are knowable",
        "complex": "emergent, many interacting actors; only probing and learning will tell",
        "chaotic": "an active crisis that needs immediate action to stabilise",
        "disorder": "unclear, garbled, contradictory or not a request at all",
    },
}
LABELS: list[str] = list(SHADOW_QUESTION["criteria"])

DEFAULT_URL = "http://127.0.0.1:18195"
DEFAULT_MODELS = "vllm-d3"
DEFAULT_TIMEOUT_S = 1.5
EXCERPT_CHARS = 200
# Transport bounds, not analytical values: the bench asked about single requests, and
# the in-flight set is capped per AP-4 (a call beyond the cap is dropped, not queued).
MAX_STATE_CHARS = 4000
MAX_IN_FLIGHT = 64

_TASKS: set[asyncio.Task[None]] = set()
_WRITE_LOCK = threading.Lock()

# The project has no shared secret scrubber; these cover the key formats CARF's own
# providers use (.env.example) plus generic key=value secrets, bearer tokens and emails.
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # A key with no END line (pasted in part, or cut at MAX_STATE_CHARS) is redacted to
    # the end of the text rather than left in.
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*)", re.S
        ),
        "[REDACTED]",
    ),
    (re.compile(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"), "[REDACTED]"),
    (re.compile(r"\b(?:sk|pk|rk)-[\w-]{16,}"), "[REDACTED]"),
    (re.compile(r"\b(?:gh[pousr]|github_pat|hf)_\w{20,}"), "[REDACTED]"),
    (re.compile(r"\bxox[abprs]-[\w-]{10,}"), "[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\bAIza[\w-]{35}"), "[REDACTED]"),
    (re.compile(r"\b(?:hl|ls|lsv2)[_-][\w-]{16,}"), "[REDACTED]"),
    (re.compile(r"(?i)\b(authorization\s*[:=]\s*)(?:basic|digest)\s+[\w.~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+[\w.~+/=-]{8,}"), "Bearer [REDACTED]"),
    # The name may carry a prefix (NEO4J_PASSWORD, OPENAI_API_KEY, x-api-key: "_" is a
    # word character, so a plain \b would miss these) and the value may be quoted (JSON,
    # YAML). The lookbehind starts a match only at the start of a name, which keeps the
    # prefix loop linear.
    (
        re.compile(
            r"(?i)(?<![\w-])((?:[a-z0-9]+[_-])*"
            r"(?:api[_-]?key|secret|token|password|passwd|pwd|[a-z0-9]+[_-]key))"
            r"([\"']?\s*[:=]\s*[\"']?)[^\s'\",;&]+"
        ),
        r"\1\2[REDACTED]",
    ),
    # user:password@ in a URL. The scheme is bounded so a long dotted run stays linear.
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]{0,31}://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
    # Bounded local part (RFC 5321: 64) keeps this linear on long runs without an "@".
    (re.compile(r"[\w.%+-]{1,64}@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}"), "[EMAIL]"),
)


class CarfRouteDetails(BaseModel):
    """What the router did, recorded next to each shadow answer."""

    mode: str = Field(..., description="Router mode: llm or distilbert")
    raw_domain: str = Field(..., description="Classifier output before boost, hints and gates")
    raw_confidence: float = Field(..., description="Classifier confidence before post-processing")
    pre_gate_domain: str = Field(..., description="Domain after boost and hints, before the gates")
    final_confidence: float = Field(..., description="Confidence CARF recorded with its decision")
    threshold: float = Field(..., description="The router's global confidence threshold")
    forced_disorder: bool = Field(
        ...,
        description="A gate (threshold or conformal) turned a non-Disorder answer into Disorder",
    )
    chaotic_gate: bool = Field(..., description="The opt-in distribution gate forced Chaotic")
    parse_error: bool = Field(
        ..., description="The LLM reply did not parse, so the raw Disorder is a failure, not a call"
    )
    hinted: bool = Field(..., description="A scenario or data-structure domain hint was present")
    entropy: float = Field(..., description="Lexical signal entropy (state.domain_entropy)")
    distribution_entropy: float = Field(..., description="Entropy of the domain distribution")


class ShadowRecord(BaseModel):
    """One shadow decision in the decision-shadow contract format, version 1.

    Field order follows the contract; ``text_sha256`` and ``carf`` are CARF's own.
    """

    v: int = Field(default=1, description="Contract version")
    ts: str = Field(..., description="UTC time of CARF's decision")
    project: str = Field(default=PROJECT)
    decision: str = Field(default=DECISION)
    machine: str
    calib_key: str = Field(..., description="Conformal threshold key: the machine for CARF")
    subject_id: str = Field(
        ...,
        description="<session_id>:<router pass>; the session id joins the feedback store",
    )
    model: str
    question: str = Field(default=QUESTION_ID)
    order: str = Field(default="fwd", description="Option order as calibrated")
    labels: list[str]
    probs: dict[str, float] | None = Field(..., description="None when the call failed")
    live: str = Field(..., description="CARF's final domain, lowercased")
    excerpt: str | None = Field(..., description="Scrubbed text excerpt, only when opted in")
    latency_ms: int
    error: str | None
    text_sha256: str = Field(..., description="sha256 of the raw request text")
    carf: CarfRouteDetails


def is_enabled() -> bool:
    """Whether the shadow is switched on for this process."""
    return os.getenv("CARF_ROUTER_SHADOW") == "1"


def _flag(name: str) -> bool:
    return os.getenv(name) == "1"


def shadow_dir() -> Path:
    """Where shadow logs go (see the module docstring for the fallbacks)."""
    explicit = os.getenv("DECISION_SHADOW_DIR")
    if explicit:
        return Path(explicit).expanduser()
    data_dir = os.getenv("CARF_DATA_DIR")
    base = Path(data_dir).expanduser() if data_dir else Path(__file__).resolve().parents[2] / "var"
    return base / "decision-shadow"


def log_path() -> Path:
    """The JSONL file this project appends to."""
    return shadow_dir() / f"{PROJECT}.jsonl"


def machine() -> str:
    """Machine name, which is also CARF's calibration key."""
    return (
        os.getenv("CARF_ROUTER_SHADOW_MACHINE")
        or os.getenv("DECISION_SHADOW_MACHINE")
        or socket.gethostname()
    )


def models() -> list[str]:
    """Decision models to ask, in order."""
    raw = os.getenv("CARF_ROUTER_SHADOW_MODELS") or DEFAULT_MODELS
    names = [m.strip() for m in raw.split(",") if m.strip()]
    return list(dict.fromkeys(names)) or [DEFAULT_MODELS]


def timeout_s() -> float:
    """Total time allowed for one call."""
    try:
        value = float(os.getenv("CARF_ROUTER_SHADOW_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    except ValueError:
        return DEFAULT_TIMEOUT_S
    return value if value > 0 else DEFAULT_TIMEOUT_S


def scrub(text: str) -> str:
    """Replace secrets and email addresses in ``text``."""
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


async def observe(text: str, subject_id: str, live: str, carf: dict[str, Any]) -> None:
    """Hand one routing decision to the shadow.

    Returns at once (unless ``CARF_ROUTER_SHADOW_AWAIT=1``), never raises an ordinary
    exception and never touches the router's state.

    Args:
        text: The request text the router classified.
        subject_id: ``<session_id>:<router pass>``. The graph re-enters the router after
            a Guardian rejection or a human edit, so a session can hold several routing
            decisions; the session id is what the feedback store keys on.
        live: CARF's final domain.
        carf: Router details, validated as ``CarfRouteDetails``.
    """
    try:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if _flag("CARF_ROUTER_SHADOW_AWAIT"):
            await _shadow(ts, text, subject_id, live, carf)
            return
        in_flight = _in_flight()
        if in_flight >= 2 * MAX_IN_FLIGHT:
            logger.debug("Router shadow dropped unlogged: %d tasks pending", in_flight)
            return
        # Past the cap the call is not made, but its rows are still written (no HTTP), so
        # a dropped call counts against availability instead of vanishing from it.
        dropped = (
            f"dropped: over {MAX_IN_FLIGHT} calls in flight" if in_flight >= MAX_IN_FLIGHT else None
        )
        coro: Coroutine[Any, Any, None] = _shadow(ts, text, subject_id, live, carf, dropped)
        task = asyncio.get_running_loop().create_task(coro)
        # Keep a reference so the task is not garbage-collected before it finishes.
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
    except Exception as exc:
        logger.debug("Router shadow not scheduled: %s", exc)


def _in_flight() -> int:
    """Pending shadow tasks, after forgetting those on a closed event loop.

    A caller that runs ``classify()`` on its own loop and closes it without cancelling
    leaves the task pending forever (its done callback never runs). Kept, 64 of them
    would fill the cap and silence the shadow for the life of the process.
    """
    for task in list(_TASKS):  # list() copies in one step; another loop's thread may add
        if task.get_loop().is_closed():
            _TASKS.discard(task)
    return len(_TASKS)


async def drain() -> None:
    """Wait for this event loop's background shadow calls (tests, batch runs, shutdown)."""
    loop = asyncio.get_running_loop()
    pending = [t for t in _TASKS if t.get_loop() is loop and not t.done()]
    while pending:
        await asyncio.gather(*pending, return_exceptions=True)
        pending = [t for t in _TASKS if t.get_loop() is loop and not t.done()]


def _client(timeout: float) -> httpx.AsyncClient:
    """HTTP client for one shadow round (tests swap in a mock transport here)."""
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout))


async def _shadow(
    ts: str,
    text: str,
    subject_id: str,
    live: str,
    carf: dict[str, Any],
    dropped: str | None = None,
) -> None:
    """Ask every configured model once and append one row per model.

    With ``dropped`` set no model is asked; each row carries it as the error.
    """
    try:
        details = CarfRouteDetails(**carf)
        # Cut before scrubbing so the regexes stay cheap on the event loop; the margin
        # keeps a secret that straddles the cut whole long enough to be matched.
        scrubbed = scrub(text[: MAX_STATE_CHARS + 256])[:MAX_STATE_CHARS]
        excerpt = scrubbed[:EXCERPT_CHARS] if _flag("CARF_ROUTER_SHADOW_LOG_TEXT") else None
        text_sha256 = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
        host = machine()
        url = os.getenv("CARF_ROUTER_SHADOW_URL", DEFAULT_URL).rstrip("/") + "/v1/systemone"
        timeout = timeout_s()
        names = models()

        answers: list[tuple[dict[str, float] | None, int, str | None]]
        if dropped:
            answers = [(None, 0, dropped)] * len(names)
        else:
            async with _client(timeout) as client:
                answers = await asyncio.gather(
                    *(_ask(client, url, name, scrubbed, timeout) for name in names)
                )

        rows = [
            ShadowRecord(
                ts=ts,
                machine=host,
                calib_key=host,
                subject_id=subject_id,
                model=name,
                labels=LABELS,
                probs=probs,
                live=live.lower(),
                excerpt=excerpt,
                latency_ms=latency_ms,
                error=error,
                text_sha256=text_sha256,
                carf=details,
            ).model_dump_json()
            for name, (probs, latency_ms, error) in zip(names, answers, strict=True)
        ]
        await asyncio.to_thread(_append, log_path(), rows)
    except Exception as exc:
        logger.debug("Router shadow failed: %s", exc)


async def _ask(
    client: httpx.AsyncClient, url: str, model: str, state: str, timeout: float
) -> tuple[dict[str, float] | None, int, str | None]:
    """One bounded call: ``(probs, latency_ms, error)``; exactly one of probs/error is set."""
    body = {"model": model, "state": state, "questions": {"q": SHADOW_QUESTION}}
    started = time.perf_counter()
    try:
        resp = await asyncio.wait_for(client.post(url, json=body), timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"http {resp.status_code}")
        probs = _parse(resp.json())
        return probs, _ms(started), None
    except (TimeoutError, httpx.TimeoutException):
        # Milliseconds, as the other hooks write it, so the readout groups it as "timeout".
        return None, _ms(started), f"timeout after {round(timeout * 1000)}ms"
    except Exception as exc:
        return None, _ms(started), scrub(f"{type(exc).__name__}: {exc}")[:EXCERPT_CHARS]


def _parse(payload: Any) -> dict[str, float]:
    """Read the label probabilities from a ``/v1/systemone`` reply, in question order."""
    raw = payload["answers"]["q"]["probabilities"]
    probs = {str(k).lower(): float(v) for k, v in raw.items()}
    missing = [label for label in LABELS if label not in probs]
    if missing:
        raise ValueError(f"reply lacks labels {missing}")
    # NaN fails this too. Logged as is, a NaN would serialise as null and an
    # out-of-range value would make the readout reject the whole line; as an error row
    # it counts against availability instead.
    if not all(0.0 <= probs[label] <= 1.0 for label in LABELS):
        raise ValueError("probabilities are not all in [0, 1]")
    return {label: round(probs[label], 6) for label in LABELS}


def _ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def _append(path: Path, rows: list[str]) -> None:
    data = "".join(row + "\n" for row in rows).encode("utf-8")
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as fh:
            end = fh.seek(0, os.SEEK_END)
            if end:
                fh.seek(end - 1)
                if fh.read(1) != b"\n":
                    # A writer killed mid-line left a torn row; start a new line so this
                    # batch is not glued onto it (append mode still writes at the end).
                    data = b"\n" + data
            fh.write(data)
