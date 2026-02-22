"""Unit tests for GovernanceBoardService — Board CRUD, Templates, and Compliance.

Tests create_board, list_boards, get_board, update_board, delete_board,
create_from_template, list_templates, and compute_board_compliance.
"""

import os
import pytest

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"

from src.core.governance_models import (
    ComplianceFramework,
    ComplianceFrameworkConfig,
    ComplianceScore,
    GovernanceBoard,
)
from src.services.governance_board_service import (
    BOARD_TEMPLATES,
    GovernanceBoardService,
)


@pytest.fixture
def board_service(monkeypatch):
    """Create a fresh GovernanceBoardService and reset federated singleton."""
    import src.services.federated_policy_service as fps
    import src.services.governance_service as gs

    monkeypatch.setattr(fps, "_federated_service", None)
    monkeypatch.setattr(gs, "_governance_service", None)
    return GovernanceBoardService()


# ---------------------------------------------------------------------------
# Board CRUD
# ---------------------------------------------------------------------------

class TestCreateBoard:
    """Test creating a governance board."""

    def test_create_board(self, board_service):
        board = GovernanceBoard(name="Test Board")
        result = board_service.create_board(board)
        assert result.name == "Test Board"
        assert board_service.get_board(result.board_id) is not None


class TestListBoards:
    """Test listing governance boards."""

    def test_list_boards(self, board_service):
        board_service.create_board(GovernanceBoard(name="Board A"))
        board_service.create_board(GovernanceBoard(name="Board B"))
        boards = board_service.list_boards()
        assert len(boards) == 2
        names = {b.name for b in boards}
        assert "Board A" in names
        assert "Board B" in names


class TestGetBoard:
    """Test retrieving a board by ID."""

    def test_get_board(self, board_service):
        board = GovernanceBoard(name="Retrieve Me")
        created = board_service.create_board(board)
        fetched = board_service.get_board(created.board_id)
        assert fetched is not None
        assert fetched.name == "Retrieve Me"
        assert fetched.board_id == created.board_id


class TestUpdateBoard:
    """Test updating a board's attributes."""

    def test_update_board(self, board_service):
        board = GovernanceBoard(name="Original Name")
        created = board_service.create_board(board)
        updated = board_service.update_board(created.board_id, {"name": "Updated Name"})
        assert updated is not None
        assert updated.name == "Updated Name"
        # Verify persistence
        fetched = board_service.get_board(created.board_id)
        assert fetched.name == "Updated Name"


class TestDeleteBoard:
    """Test deleting a board."""

    def test_delete_board(self, board_service):
        board = GovernanceBoard(name="Delete Me")
        created = board_service.create_board(board)
        assert board_service.delete_board(created.board_id) is True
        assert board_service.get_board(created.board_id) is None


# ---------------------------------------------------------------------------
# Template-Based Board Creation
# ---------------------------------------------------------------------------

class TestCreateFromTemplate:
    """Test board creation from predefined templates."""

    def test_create_from_template_scope_emissions(self, board_service):
        board = board_service.create_from_template("scope_emissions")
        assert board is not None
        assert board.template_id == "scope_emissions"
        assert "sustainability" in board.domain_ids
        assert "procurement" in board.domain_ids
        assert "finance" in board.domain_ids
        # Verify policies were registered via the federated service
        from src.services.federated_policy_service import get_federated_service
        fed = get_federated_service()
        assert len(board.policy_namespaces) > 0
        for ns in board.policy_namespaces:
            policy = fed.get_policy(ns)
            assert policy is not None, f"Policy {ns} should exist in federated service"
        # Verify domains were registered
        for domain_id in board.domain_ids:
            domain = fed.get_domain(domain_id)
            assert domain is not None, f"Domain {domain_id} should exist in federated service"

    def test_create_from_template_unknown(self, board_service):
        result = board_service.create_from_template("nonexistent_template")
        assert result is None


class TestListTemplates:
    """Test listing available board templates."""

    def test_list_templates(self, board_service):
        templates = board_service.list_templates()
        assert len(templates) >= 4
        template_ids = {t["template_id"] for t in templates}
        assert "scope_emissions" in template_ids
        assert "csrd_esrs" in template_ids
        assert "eu_ai_act" in template_ids
        assert "supply_chain" in template_ids


# ---------------------------------------------------------------------------
# Board Compliance Aggregation
# ---------------------------------------------------------------------------

class TestComputeBoardCompliance:
    """Test compliance score aggregation for a board."""

    def test_compute_board_compliance(self, board_service):
        board = board_service.create_from_template("scope_emissions")
        assert board is not None
        scores = board_service.compute_board_compliance(board.board_id)
        assert isinstance(scores, list)
        assert len(scores) > 0
        for score in scores:
            assert isinstance(score, ComplianceScore)
            assert 0 <= score.overall_score <= 1
            assert len(score.articles) > 0
