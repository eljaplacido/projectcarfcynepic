"""Unit tests for GovernanceExportService — JSON-LD, YAML, and CSL export.

Tests export_json_ld, export_yaml, and export_csl using a board created
from the scope_emissions template.
"""

import os
import pytest
import yaml

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"

from src.services.governance_board_service import GovernanceBoardService
from src.services.governance_export_service import GovernanceExportService


@pytest.fixture
def board_and_services(monkeypatch):
    """Create fresh services, build a scope_emissions board, and return both."""
    import src.services.federated_policy_service as fps
    import src.services.governance_service as gs

    monkeypatch.setattr(fps, "_federated_service", None)
    monkeypatch.setattr(gs, "_governance_service", None)

    board_service = GovernanceBoardService()
    export_service = GovernanceExportService()

    board = board_service.create_from_template("scope_emissions")
    assert board is not None, "scope_emissions template must produce a board"
    return board, export_service


# ---------------------------------------------------------------------------
# JSON-LD Export
# ---------------------------------------------------------------------------

class TestExportJsonLd:
    """Test JSON-LD export of a governance board."""

    def test_export_json_ld(self, board_and_services):
        board, export_service = board_and_services
        result = export_service.export_json_ld(board)

        assert "@context" in result
        assert "@type" in result
        assert result["@type"] == "carf:GovernanceBoard"
        assert "odrl" in result["@context"]
        assert "carf" in result["@context"]

        # Policies should be present
        policies = result.get("odrl:policy", [])
        assert len(policies) > 0, "Board should have exported policies"
        for policy in policies:
            assert policy["@type"] == "odrl:Policy"
            assert "dcterms:title" in policy
            assert "carf:namespace" in policy


# ---------------------------------------------------------------------------
# YAML Export
# ---------------------------------------------------------------------------

class TestExportYaml:
    """Test YAML export of a governance board."""

    def test_export_yaml(self, board_and_services):
        board, export_service = board_and_services
        result = export_service.export_yaml(board)

        assert isinstance(result, str)
        assert "board:" in result

        # Verify it is valid YAML
        parsed = yaml.safe_load(result)
        assert parsed is not None
        assert "board" in parsed
        assert "domains" in parsed

        # Verify domain names appear
        for domain_id in board.domain_ids:
            assert domain_id in result, f"Domain '{domain_id}' should appear in YAML output"


# ---------------------------------------------------------------------------
# CSL Export
# ---------------------------------------------------------------------------

class TestExportCsl:
    """Test CSL policy format export of a governance board."""

    def test_export_csl(self, board_and_services):
        board, export_service = board_and_services
        result = export_service.export_csl(board)

        assert isinstance(result, list)
        assert len(result) > 0, "Board should export at least one CSL policy"
        for policy in result:
            assert isinstance(policy, dict)
            assert "name" in policy
            assert "rules" in policy
            assert isinstance(policy["rules"], list)
