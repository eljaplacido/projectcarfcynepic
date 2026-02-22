"""Tests for Governance Board API endpoints.

Uses httpx.AsyncClient with ASGITransport to test FastAPI board endpoints
at /governance/boards, /governance/boards/templates, /governance/boards/from-template,
and /governance/seed.
"""

import os
import pytest

os.environ["CARF_TEST_MODE"] = "1"
os.environ["GOVERNANCE_ENABLED"] = "true"

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from src.api.routers.governance import router


@pytest.fixture
def app():
    """Build a minimal FastAPI app with the governance router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all governance singletons between tests."""
    import src.services.federated_policy_service as fps
    import src.services.governance_service as gs
    import src.services.governance_board_service as gbs
    import src.services.governance_export_service as ges
    import src.services.cost_intelligence_service as cis
    import src.services.governance_graph_service as ggs

    fps._federated_service = None
    gs._governance_service = None
    gbs._board_service = None
    ges._export_service = None
    cis._cost_service = None
    ggs._governance_graph_instance = None
    yield
    fps._federated_service = None
    gs._governance_service = None
    gbs._board_service = None
    ges._export_service = None
    cis._cost_service = None
    ggs._governance_graph_instance = None


@pytest.fixture
async def client(app):
    """Create async test client via ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Board CRUD via API
# ---------------------------------------------------------------------------

class TestListBoardsEmpty:
    @pytest.mark.asyncio
    async def test_list_boards_empty(self, client):
        resp = await client.get("/governance/boards")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateBoard:
    @pytest.mark.asyncio
    async def test_create_board(self, client):
        resp = await client.post("/governance/boards", json={
            "name": "Test Board",
            "description": "A board created via API",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "board_id" in data
        assert data["name"] == "Test Board"


class TestListBoardTemplates:
    @pytest.mark.asyncio
    async def test_list_board_templates(self, client):
        resp = await client.get("/governance/boards/templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert isinstance(templates, list)
        assert len(templates) >= 4
        template_ids = {t["template_id"] for t in templates}
        assert "scope_emissions" in template_ids


class TestCreateFromTemplate:
    @pytest.mark.asyncio
    async def test_create_from_template(self, client):
        resp = await client.post("/governance/boards/from-template", json={
            "template_id": "scope_emissions",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "board_id" in data
        assert data["template_id"] == "scope_emissions"
        assert "sustainability" in data["domain_ids"]


class TestGetBoardNotFound:
    @pytest.mark.asyncio
    async def test_get_board_not_found(self, client):
        resp = await client.get("/governance/boards/nonexistent")
        assert resp.status_code == 404


class TestDeleteBoard:
    @pytest.mark.asyncio
    async def test_delete_board(self, client):
        # Create a board first
        create_resp = await client.post("/governance/boards", json={
            "name": "Board To Delete",
        })
        assert create_resp.status_code == 201
        board_id = create_resp.json()["board_id"]

        # Delete it
        delete_resp = await client.delete(f"/governance/boards/{board_id}")
        assert delete_resp.status_code == 204

        # Verify it is gone
        get_resp = await client.get(f"/governance/boards/{board_id}")
        assert get_resp.status_code == 404


class TestSeedDemoData:
    @pytest.mark.asyncio
    async def test_seed_demo_data(self, client):
        resp = await client.post("/governance/seed/scope_emissions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "seeded"
        assert "board_id" in data
        assert "sustainability" in data["domains"]
