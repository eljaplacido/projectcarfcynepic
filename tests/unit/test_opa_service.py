"""Unit tests for OPA config parsing."""

from src.services.opa_service import OPAConfig


def test_opa_config_defaults(monkeypatch):
    monkeypatch.delenv("OPA_ENABLED", raising=False)
    monkeypatch.delenv("OPA_URL", raising=False)
    monkeypatch.delenv("OPA_POLICY_PATH", raising=False)
    monkeypatch.delenv("OPA_TIMEOUT_SECONDS", raising=False)

    config = OPAConfig.from_env()

    assert config.enabled is False
    assert config.base_url == ""
    assert config.policy_path == "/v1/data/carf/guardian/allow"


def test_opa_config_overrides(monkeypatch):
    monkeypatch.setenv("OPA_ENABLED", "true")
    monkeypatch.setenv("OPA_URL", "http://localhost:8181")
    monkeypatch.setenv("OPA_POLICY_PATH", "/v1/data/custom/allow")
    monkeypatch.setenv("OPA_TIMEOUT_SECONDS", "3")

    config = OPAConfig.from_env()

    assert config.enabled is True
    assert config.base_url == "http://localhost:8181"
    assert config.policy_path == "/v1/data/custom/allow"
    assert config.timeout_seconds == 3.0
