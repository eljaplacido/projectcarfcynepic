"""Unit tests for dashboard utility helpers."""

from __future__ import annotations

import io
import sys
import types

import pytest


@pytest.fixture
def dashboard_app(monkeypatch):
    """Import dashboard module with a lightweight Streamlit stub."""
    st_stub = types.ModuleType("streamlit")
    st_stub.session_state = {}
    monkeypatch.setitem(sys.modules, "streamlit", st_stub)

    from src.dashboard import app as dashboard_app

    return dashboard_app


def test_generate_session_id_format(dashboard_app):
    session_id = dashboard_app._generate_session_id()
    assert session_id.startswith("sess_demo_")
    assert session_id.endswith("...")
    middle = session_id.replace("sess_demo_", "").replace("...", "")
    assert len(middle) == 2
    assert middle.isdigit()


def test_get_confidence_color_levels(dashboard_app):
    assert (
        dashboard_app._get_confidence_color("high")
        == dashboard_app.COLORS["confidence_high"]
    )
    assert (
        dashboard_app._get_confidence_color("medium")
        == dashboard_app.COLORS["confidence_medium"]
    )
    assert (
        dashboard_app._get_confidence_color("low")
        == dashboard_app.COLORS["confidence_low"]
    )
    assert (
        dashboard_app._get_confidence_color("unknown")
        == dashboard_app.COLORS["text_muted"]
    )


def test_call_api_http_error(dashboard_app, monkeypatch):
    def fake_urlopen(req, timeout=30):
        body = io.BytesIO(b'{"detail":"boom"}')
        raise dashboard_app.error.HTTPError(
            req.full_url,
            500,
            "error",
            hdrs=None,
            fp=body,
        )

    monkeypatch.setattr(dashboard_app.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as exc:
        dashboard_app._call_api("http://example.com", payload={"ping": "pong"})
    assert "HTTP 500" in str(exc.value)
