# Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
"""Unit tests for the log-only router shadow (src/services/router_shadow.py).

The shadow must never change routing: these tests run the test-mode router stub with
the shadow off and on (against a mock decision-model server, a dead port, a slow
server and a failing one) and require identical routing output every time.
"""

import asyncio
import copy
import gc
import hashlib
import json
import re
import socket
from typing import Any

import httpx
import pytest

from src.core.state import CynefinDomain, EpistemicState
from src.services import router_shadow
from src.workflows.router import CynefinRouter

QUERIES = [
    "Look up customer ID 12345 in the CRM.",  # stub: Clear
    "Why did our costs increase 15% last quarter?",  # stub: Complicated
    "Predict how the market will react to our launch.",  # stub: Complex
    "Production database is down, customers cannot log in!",  # stub: Chaotic
]

CONTRACT_KEYS = [
    "v",
    "ts",
    "project",
    "decision",
    "machine",
    "calib_key",
    "subject_id",
    "model",
    "question",
    "order",
    "labels",
    "probs",
    "live",
    "excerpt",
    "latency_ms",
    "error",
]

# sha256 of json.dumps(QUESTIONS["carf_router"]) in the decision bench (decisionbench/tasks.py).
# Insertion order is part of the hash, so this also pins the option order.
BENCH_QUESTION_SHA256 = "20ea7796e45c862466a9e41f1b1df5f1e2cc69faaf13c5264eaae946a26918a0"


@pytest.fixture
def shadow_log(monkeypatch, tmp_path):
    """Isolate the shadow's environment; return the log file path it would write."""
    for name in (
        "CARF_ROUTER_SHADOW",
        "CARF_ROUTER_SHADOW_URL",
        "CARF_ROUTER_SHADOW_MODELS",
        "CARF_ROUTER_SHADOW_TIMEOUT_S",
        "CARF_ROUTER_SHADOW_AWAIT",
        "CARF_ROUTER_SHADOW_LOG_TEXT",
        "DECISION_SHADOW_MACHINE",
        "CARF_DATA_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DECISION_SHADOW_DIR", str(tmp_path / "decision-shadow"))
    monkeypatch.setenv("CARF_ROUTER_SHADOW_MACHINE", "test-box")
    return tmp_path / "decision-shadow" / "carf.jsonl"


def _reply(probs: dict[str, float]) -> httpx.Response:
    choice = max(probs, key=probs.get)
    return httpx.Response(
        200,
        json={
            "answers": {
                "q": {
                    "type": "choice",
                    "choice": choice,
                    "probabilities": probs,
                    "confidence": probs[choice],
                }
            }
        },
    )


# The mock always disagrees with the stub, so a leak into routing would show.
CHAOTIC = {"clear": 0.01, "complicated": 0.02, "complex": 0.03, "chaotic": 0.9, "disorder": 0.04}


def _serve(monkeypatch, handler) -> list[httpx.Request]:
    """Route the shadow's HTTP calls to ``handler``; return the requests it saw."""
    seen: list[httpx.Request] = []

    async def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        result = handler(request)
        return await result if asyncio.iscoroutine(result) else result

    def client(timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(recording), timeout=timeout)

    monkeypatch.setattr(router_shadow, "_client", client)
    return seen


def _snapshot(state: EpistemicState) -> dict[str, Any]:
    """Everything the router decides or records, minus per-run ids and timestamps."""
    return {
        "cynefin_domain": state.cynefin_domain,
        "domain_confidence": state.domain_confidence,
        "overall_confidence": state.overall_confidence,
        "triggered_method": state.triggered_method,
        "domain_scores": dict(state.domain_scores),
        "domain_entropy": state.domain_entropy,
        "current_hypothesis": state.current_hypothesis,
        "router_key_indicators": list(state.router_key_indicators),
        "context": copy.deepcopy(state.context),
        "reasoning": [(s.node_name, s.action, s.output_summary) for s in state.reasoning_chain],
    }


async def _route_all(queries: list[str], threshold: float = 0.70) -> list[dict[str, Any]]:
    """Classify each query with a fresh router (its rolling window is per instance)."""
    router = CynefinRouter(mode="llm", confidence_threshold=threshold)
    out = []
    for query in queries:
        state = await router.classify(EpistemicState(user_input=query))
        await router_shadow.drain()
        out.append(_snapshot(state))
    return out


def _rows(path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestShadowQuestion:
    def test_question_is_the_bench_question(self):
        """Wording and option order must match the calibrated bench question."""
        digest = hashlib.sha256(json.dumps(router_shadow.SHADOW_QUESTION).encode()).hexdigest()
        assert digest == BENCH_QUESTION_SHA256
        assert router_shadow.LABELS == ["clear", "complicated", "complex", "chaotic", "disorder"]


class TestFlagOff:
    async def test_no_http_and_no_file(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))

        await _route_all(QUERIES)

        assert seen == []
        assert not shadow_log.exists()
        assert not shadow_log.parent.exists()

    async def test_other_values_do_not_enable(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "true")

        await _route_all(QUERIES[:1])

        assert seen == []
        assert not shadow_log.exists()


class TestRoutingUnchanged:
    async def test_flag_on_matches_flag_off(self, monkeypatch, shadow_log):
        off = await _route_all(QUERIES)

        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        on = await _route_all(QUERIES)

        assert on == off
        assert [s["cynefin_domain"] for s in on] == [
            CynefinDomain.CLEAR,
            CynefinDomain.COMPLICATED,
            CynefinDomain.COMPLEX,
            CynefinDomain.CHAOTIC,
        ]
        assert len(seen) == len(QUERIES)
        assert not any("shadow" in key for s in on for key in s["context"])
        assert [r["live"] for r in _rows(shadow_log)] == [
            "clear",
            "complicated",
            "complex",
            "chaotic",
        ]

    async def test_await_mode_matches_flag_off(self, monkeypatch, shadow_log):
        off = await _route_all(QUERIES)

        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        on = await _route_all(QUERIES)

        assert on == off
        assert len(_rows(shadow_log)) == len(QUERIES)


class TestFailOpen:
    @pytest.fixture(params=["down", "timeout", "http500", "bad_reply"])
    def failing(self, request, monkeypatch, shadow_log):
        """Each way the server can fail, plus the error text it should leave behind."""
        kind = request.param
        if kind == "down":
            monkeypatch.setenv("CARF_ROUTER_SHADOW_URL", f"http://127.0.0.1:{_free_port()}")
            return kind, r"^ConnectError"
        if kind == "timeout":
            monkeypatch.setenv("CARF_ROUTER_SHADOW_TIMEOUT_S", "0.05")

            async def slow(request):
                await asyncio.sleep(2)
                return _reply(CHAOTIC)

            _serve(monkeypatch, slow)
            return kind, r"^timeout after 50ms$"
        if kind == "http500":
            _serve(monkeypatch, lambda request: httpx.Response(500, text="boom"))
            return kind, r"^RuntimeError: http 500$"
        _serve(
            monkeypatch,
            lambda request: httpx.Response(
                200, json={"answers": {"q": {"probabilities": {"clear": 1.0}}}}
            ),
        )
        return kind, r"^ValueError: reply lacks labels"

    @pytest.mark.parametrize("wait", ["0", "1"])
    async def test_failure_leaves_routing_alone_and_logs_an_error_row(
        self, monkeypatch, shadow_log, failing, wait
    ):
        kind, error_pattern = failing
        off = await _route_all(QUERIES[:2])

        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", wait)
        on = await _route_all(QUERIES[:2])

        assert on == off
        rows = _rows(shadow_log)
        assert len(rows) == 2
        for row in rows:
            assert row["probs"] is None
            assert re.match(error_pattern, row["error"]), (kind, row["error"])
            assert row["latency_ms"] >= 0
            if kind == "timeout":
                assert row["latency_ms"] < 1000

    async def test_background_call_does_not_hold_up_classify(self, monkeypatch, shadow_log):
        release = asyncio.Event()

        async def held(request):
            await release.wait()
            return _reply(CHAOTIC)

        _serve(monkeypatch, held)
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_TIMEOUT_S", "5")
        router = CynefinRouter(mode="llm")

        state = await asyncio.wait_for(router.classify(EpistemicState(user_input=QUERIES[0])), 2)

        assert state.cynefin_domain == CynefinDomain.CLEAR
        assert not shadow_log.exists()
        release.set()
        await router_shadow.drain()
        assert _rows(shadow_log)[0]["probs"]["chaotic"] == 0.9

    async def test_unwritable_log_dir_is_swallowed(self, monkeypatch, shadow_log, tmp_path):
        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("")
        monkeypatch.setenv("DECISION_SHADOW_DIR", str(blocker / "sub"))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")

        on = await _route_all(QUERIES[:1])

        assert on[0]["cynefin_domain"] == CynefinDomain.CLEAR

    @pytest.mark.parametrize(
        "content",
        [
            b'{"answers":{"q":{"probabilities":'
            b'{"clear":NaN,"complicated":0.2,"complex":0.2,"chaotic":0.2,"disorder":0.2}}}}',
            b'{"answers":{"q":{"probabilities":'
            b'{"clear":-3,"complicated":7,"complex":0,"chaotic":0,"disorder":0}}}}',
        ],
    )
    async def test_probabilities_outside_0_1_are_an_error_row(
        self, monkeypatch, shadow_log, content
    ):
        """Logged as is, the readout would reject the line instead of counting the call."""
        _serve(monkeypatch, lambda request: httpx.Response(200, content=content))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")

        await _route_all(QUERIES[:1])

        (row,) = _rows(shadow_log)
        assert row["probs"] is None
        assert row["error"] == "ValueError: probabilities are not all in [0, 1]"

    async def test_error_text_is_scrubbed(self, monkeypatch, shadow_log):
        def refuse(request):
            raise httpx.ConnectError("refused, token=hunter2hunter2")

        _serve(monkeypatch, refuse)
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")

        await _route_all(QUERIES[:1])

        (row,) = _rows(shadow_log)
        assert row["error"] == "ConnectError: refused, token=[REDACTED]"

    async def test_call_past_the_cap_is_dropped_but_still_logged(self, monkeypatch, shadow_log):
        release = asyncio.Event()

        async def held(request):
            await release.wait()
            return _reply(CHAOTIC)

        seen = _serve(monkeypatch, held)
        monkeypatch.setattr(router_shadow, "MAX_IN_FLIGHT", 1)
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        router = CynefinRouter(mode="llm")

        first = await router.classify(EpistemicState(user_input=QUERIES[0]))
        second = await router.classify(EpistemicState(user_input=QUERIES[1]))
        release.set()
        await router_shadow.drain()

        assert [first.cynefin_domain, second.cynefin_domain] == [
            CynefinDomain.CLEAR,
            CynefinDomain.COMPLICATED,
        ]
        assert len(seen) == 1
        # Both rows are written once the held call is released, in either order.
        rows = {r["live"]: r for r in _rows(shadow_log)}
        assert sorted(rows) == ["clear", "complicated"]
        assert rows["clear"]["error"] is None
        assert rows["complicated"]["error"] == "dropped: over 1 calls in flight"
        assert rows["complicated"]["probs"] is None

    # The forgotten tasks never ran their calls; collecting them warns, as it should.
    @pytest.mark.filterwarnings("ignore:coroutine '_ask' was never awaited:RuntimeWarning")
    def test_tasks_left_on_closed_loops_do_not_fill_the_cap(self, monkeypatch, shadow_log):
        """A caller that closes its own loop must not silence the shadow for good."""

        async def never(request):
            await asyncio.Event().wait()

        _serve(monkeypatch, never)
        monkeypatch.setattr(router_shadow, "MAX_IN_FLIGHT", 2)
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        router = CynefinRouter(mode="llm")
        for _ in range(5):
            loop = asyncio.new_event_loop()
            loop.run_until_complete(router.classify(EpistemicState(user_input=QUERIES[0])))
            loop.close()

        _serve(monkeypatch, lambda request: _reply(CHAOTIC))

        async def healthy() -> None:
            await router.classify(EpistemicState(user_input=QUERIES[1]))
            await router_shadow.drain()

        asyncio.run(healthy())
        gc.collect()  # the forgotten tasks go here, not in a later test

        (row,) = _rows(shadow_log)
        assert row["live"] == "complicated"
        assert row["probs"]["chaotic"] == 0.9

    async def test_torn_last_line_is_not_glued_to_the_next_row(self, monkeypatch, shadow_log):
        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        shadow_log.parent.mkdir(parents=True)
        shadow_log.write_text('{"v": 1, "ts": "2026-10-31T12:00:00Z", "proj')

        await _route_all(QUERIES[:1])

        torn, line = shadow_log.read_text().splitlines()
        assert torn.endswith('"proj')
        assert json.loads(line)["live"] == "clear"


class TestRecord:
    async def test_contract_v1_schema(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        router = CynefinRouter(mode="llm")
        state = EpistemicState(user_input=QUERIES[1])

        await router.classify(state)

        (row,) = _rows(shadow_log)
        assert list(row) == CONTRACT_KEYS + ["text_sha256", "carf"]
        assert row["v"] == 1
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", row["ts"])
        assert row["project"] == "carf"
        assert row["decision"] == "route"
        assert row["machine"] == row["calib_key"] == "test-box"
        assert row["subject_id"] == f"{state.session_id}:1"
        assert row["model"] == "vllm-d3"
        assert row["question"] == "carf_router.v1"
        assert row["order"] == "fwd"
        assert row["labels"] == router_shadow.LABELS
        assert list(row["probs"]) == router_shadow.LABELS
        assert row["probs"]["chaotic"] == 0.9
        assert row["live"] == "complicated"
        assert row["excerpt"] is None
        assert isinstance(row["latency_ms"], int)
        assert row["error"] is None
        assert row["text_sha256"] == hashlib.sha256(QUERIES[1].encode()).hexdigest()
        assert row["carf"] == {
            "mode": "llm",
            "raw_domain": "Complicated",
            "raw_confidence": 0.88,
            "pre_gate_domain": "Complicated",
            "final_confidence": 0.88,
            "threshold": 0.70,
            "forced_disorder": False,
            "chaotic_gate": False,
            "parse_error": False,
            "hinted": False,
            "entropy": state.domain_entropy,
            "distribution_entropy": row["carf"]["distribution_entropy"],
        }

        (request,) = seen
        assert request.url == "http://127.0.0.1:18195/v1/systemone"
        body = json.loads(request.content)
        assert body == {
            "model": "vllm-d3",
            "state": QUERIES[1],
            "questions": {"q": router_shadow.SHADOW_QUESTION},
        }
        assert list(body["questions"]["q"]["criteria"]) == router_shadow.LABELS

    async def test_threshold_override_is_recorded(self, monkeypatch, shadow_log):
        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")

        # The stub answers Complicated at 0.88; a 0.90 threshold forces Disorder.
        (snap,) = await _route_all(QUERIES[1:2], threshold=0.90)

        assert snap["cynefin_domain"] == CynefinDomain.DISORDER
        (row,) = _rows(shadow_log)
        assert row["live"] == "disorder"
        assert row["carf"]["raw_domain"] == "Complicated"
        assert row["carf"]["forced_disorder"] is True

    async def test_one_row_per_model(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_MODELS", " vllm-d3 , kev-4b ,")

        await _route_all(QUERIES[:1])

        rows = _rows(shadow_log)
        assert [r["model"] for r in rows] == ["vllm-d3", "kev-4b"]
        assert len({r["subject_id"] for r in rows}) == 1
        assert sorted(json.loads(r.content)["model"] for r in seen) == ["kev-4b", "vllm-d3"]

    async def test_text_is_opt_in_and_scrubbed(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_LOG_TEXT", "1")
        secret = "sk-" + "a1B2" * 8
        query = f"Look up account ops@example.com with api_key={secret} " + "x" * 300

        await _route_all([query])

        (row,) = _rows(shadow_log)
        assert len(row["excerpt"]) == 200
        assert secret not in row["excerpt"]
        assert "ops@example.com" not in row["excerpt"]
        assert "api_key=[REDACTED]" in row["excerpt"]
        assert row["text_sha256"] == hashlib.sha256(query.encode()).hexdigest()
        sent = json.loads(seen[0].content)["state"]
        assert secret not in sent and "ops@example.com" not in sent

    async def test_long_text_is_cut_before_it_is_sent(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        query = "x" * 200_000  # a long run with no "@" is the scrubber's worst case

        await _route_all([query])

        assert len(json.loads(seen[0].content)["state"]) == router_shadow.MAX_STATE_CHARS
        assert _rows(shadow_log)[0]["text_sha256"] == hashlib.sha256(query.encode()).hexdigest()

    async def test_each_router_pass_has_its_own_subject_id(self, monkeypatch, shadow_log):
        """The graph re-enters the router (reflector, human edit) with the same session."""
        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        router = CynefinRouter(mode="llm")
        state = EpistemicState(user_input=QUERIES[1])

        state = await router.classify(state)
        state = await router.classify(state)

        assert [r["subject_id"] for r in _rows(shadow_log)] == [
            f"{state.session_id}:1",
            f"{state.session_id}:2",
        ]

    async def test_parse_error_is_recorded(self, monkeypatch, shadow_log):
        """A reply CARF cannot parse becomes Disorder; the row must say it was a failure."""

        class Garbled:
            async def ainvoke(self, messages):
                return type("Reply", (), {"content": "not json"})()

        _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        router = CynefinRouter(mode="llm")
        router.model = Garbled()

        state = await router.classify(EpistemicState(user_input=QUERIES[0]))

        assert state.cynefin_domain == CynefinDomain.DISORDER
        (row,) = _rows(shadow_log)
        assert row["live"] == "disorder"
        assert row["carf"]["parse_error"] is True
        assert row["carf"]["forced_disorder"] is False

    async def test_private_key_cut_at_the_limit_is_not_sent(self, monkeypatch, shadow_log):
        seen = _serve(monkeypatch, lambda request: _reply(CHAOTIC))
        monkeypatch.setenv("CARF_ROUTER_SHADOW", "1")
        monkeypatch.setenv("CARF_ROUTER_SHADOW_AWAIT", "1")
        body = "MIIEpAIBAAKCAQEA" * 40
        key = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----"
        query = "Why did the deploy fail? " + "x" * 3880 + " " + key

        await _route_all([query])

        sent = json.loads(seen[0].content)["state"]
        assert "MIIEpAIBAAKCAQEA" not in sent
        assert sent.endswith("[REDACTED]")


class TestConfig:
    def test_default_log_dir_is_in_the_repo_data_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DECISION_SHADOW_DIR", raising=False)
        monkeypatch.delenv("CARF_DATA_DIR", raising=False)
        assert router_shadow.log_path().parts[-3:] == ("var", "decision-shadow", "carf.jsonl")

        monkeypatch.setenv("CARF_DATA_DIR", str(tmp_path))
        assert router_shadow.log_path() == tmp_path / "decision-shadow" / "carf.jsonl"

    def test_bad_timeout_falls_back(self, monkeypatch):
        monkeypatch.setenv("CARF_ROUTER_SHADOW_TIMEOUT_S", "soon")
        assert router_shadow.timeout_s() == router_shadow.DEFAULT_TIMEOUT_S
        monkeypatch.setenv("CARF_ROUTER_SHADOW_TIMEOUT_S", "-1")
        assert router_shadow.timeout_s() == router_shadow.DEFAULT_TIMEOUT_S

    @pytest.mark.parametrize(
        "text",
        [
            "Bearer abcdefghijklmnop.qrstuv",
            "token: hunter2hunter2",
            "AKIAABCDEFGHIJKLMNOP",
            "ghp_" + "x" * 36,
            "eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2QT4",
        ],
    )
    def test_scrub_removes_secrets(self, text):
        assert "[REDACTED]" in router_shadow.scrub(f"please check {text} now")

    @pytest.mark.parametrize(
        ("text", "secret"),
        [
            ("NEO4J_PASSWORD=hunter2hunter2", "hunter2"),
            ("OPENAI_API_KEY=0123456789abcdef0123456789abcdef", "0123456789abcdef"),
            ("AZURE_OPENAI_KEY=0123456789abcdef0123456789abcdef", "0123456789abcdef"),
            ('{"password": "hunter2hunter2"}', "hunter2"),
            ("client_secret: 'hunter2hunter2'", "hunter2"),
            ("x-api-key: hunter2hunter2", "hunter2"),
            ("HF_TOKEN=hf_abcdefghijklmnopqrstuvwxyz0123", "abcdefghijklmnop"),
            ("Authorization: Basic dXNlcjpodW50ZXIy", "dXNlcjpodW50ZXIy"),
            ("postgres://carf:hunter2hunter2@db.internal:5432/carf", "hunter2"),
        ],
    )
    def test_scrub_removes_prefixed_and_quoted_secrets(self, text, secret):
        """Env-style names (_ is a word character) and quoted values were missed before."""
        assert secret not in router_shadow.scrub(f"please check {text} now")

    def test_scrub_leaves_ordinary_requests_alone(self):
        for query in QUERIES:
            assert router_shadow.scrub(query) == query
