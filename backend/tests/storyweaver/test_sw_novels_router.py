"""
Tests — Router sw_novels (Task 1.2.1)
========================================

Tests unitaires du router FastAPI /api/sw/novels.
Stratégie : mocks des DAOs et de get_verified_user pour isoler la logique du router.

Couverture:
    - POST /create : création OK, titre vide (validation Pydantic), DAO failure
    - GET /        : liste, liste vide
    - GET /{id}    : trouvé, 404, 403 (autre user)
    - POST /{id}/update : succès partiel, rien à mettre à jour, 404, 403
    - DELETE /{id}/delete : succès, 404, 403
"""

import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# ─── Bootstrap minimal de l'app de test ───────────────────────────────────────

from open_webui.routers.sw_novels import router
from open_webui.models.sw_novels import NovelModel
from open_webui.internal.db import get_session
from open_webui.utils.auth import get_verified_user

app = FastAPI()
app.include_router(router)


def _mock_user(user_id: str = "user-001", role: str = "user"):
    user = MagicMock()
    user.id = user_id
    user.role = role
    return user


def _mock_novel(
    user_id: str = "user-001",
    novel_id: str = "novel-abc",
    title: str = "Mon Roman",
    status: str = "draft",
) -> NovelModel:
    now = int(time.time())
    return NovelModel(
        id=novel_id,
        user_id=user_id,
        title=title,
        description="Une belle histoire.",
        status=status,
        created_at=now,
        updated_at=now,
    )


# Override dépendances FastAPI
def _override_get_session():
    yield MagicMock()


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def override_dependencies():
    """Injecte un user et une session DB mockés pour tous les tests."""
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_verified_user] = lambda: _mock_user()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ─── POST /create ──────────────────────────────────────────────────────────────


class TestCreateNovel:
    def test_create_ok(self, client):
        novel = _mock_novel()
        with patch("open_webui.routers.sw_novels.Novels.insert_new_novel", return_value=novel):
            resp = client.post("/create", json={"title": "Mon Roman", "status": "draft"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Mon Roman"
        assert data["status"] == "draft"

    def test_create_empty_title_returns_422(self, client):
        resp = client.post("/create", json={"title": "", "status": "draft"})
        assert resp.status_code == 422

    def test_create_invalid_status_returns_422(self, client):
        resp = client.post("/create", json={"title": "Test", "status": "invalid-status"})
        assert resp.status_code == 422

    def test_create_dao_failure_returns_400(self, client):
        with patch("open_webui.routers.sw_novels.Novels.insert_new_novel", return_value=None):
            resp = client.post("/create", json={"title": "Mon Roman"})
        assert resp.status_code == 400

    def test_create_with_description(self, client):
        novel = _mock_novel()
        with patch("open_webui.routers.sw_novels.Novels.insert_new_novel", return_value=novel):
            resp = client.post(
                "/create",
                json={"title": "Roman Complet", "description": "Synopsis court.", "status": "in-progress"},
            )
        assert resp.status_code == 200


# ─── GET / ─────────────────────────────────────────────────────────────────────


class TestGetNovels:
    def test_get_returns_list(self, client):
        novels = [_mock_novel(), _mock_novel(novel_id="novel-xyz", title="Autre Roman")]
        with patch("open_webui.routers.sw_novels.Novels.get_novels_by_user", return_value=novels):
            resp = client.get("/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_returns_empty_list(self, client):
        with patch("open_webui.routers.sw_novels.Novels.get_novels_by_user", return_value=[]):
            resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == []


# ─── GET /{id} ─────────────────────────────────────────────────────────────────


class TestGetNovelById:
    def test_get_by_id_ok(self, client):
        novel = _mock_novel()
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.get("/novel-abc")
        assert resp.status_code == 200
        assert resp.json()["id"] == "novel-abc"

    def test_get_by_id_not_found(self, client):
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=None):
            resp = client.get("/novel-does-not-exist")
        assert resp.status_code == 404

    def test_get_by_id_forbidden_other_user(self, client):
        # Novel appartient à user-999, client est user-001
        novel = _mock_novel(user_id="user-999")
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.get("/novel-abc")
        assert resp.status_code == 403

    def test_get_by_id_admin_can_access_any(self, client):
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(user_id="admin-001", role="admin")
        novel = _mock_novel(user_id="user-999")
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.get("/novel-abc")
        assert resp.status_code == 200


# ─── POST /{id}/update ─────────────────────────────────────────────────────────


class TestUpdateNovelById:
    def test_update_ok(self, client):
        original = _mock_novel()
        updated = _mock_novel(title="Titre Modifié")
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=original),
            patch("open_webui.routers.sw_novels.Novels.update_novel_by_id", return_value=updated),
        ):
            resp = client.post("/novel-abc/update", json={"title": "Titre Modifié"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Titre Modifié"

    def test_update_nothing_returns_original(self, client):
        novel = _mock_novel()
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.post("/novel-abc/update", json={})
        assert resp.status_code == 200
        assert resp.json()["id"] == "novel-abc"

    def test_update_not_found(self, client):
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=None):
            resp = client.post("/novel-abc/update", json={"title": "New"})
        assert resp.status_code == 404

    def test_update_forbidden_other_user(self, client):
        novel = _mock_novel(user_id="user-999")
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.post("/novel-abc/update", json={"title": "Tentative"})
        assert resp.status_code == 403

    def test_update_invalid_status_returns_422(self, client):
        resp = client.post("/novel-abc/update", json={"status": "bad-status"})
        assert resp.status_code == 422


# ─── DELETE /{id}/delete ───────────────────────────────────────────────────────


class TestDeleteNovelById:
    def test_delete_ok(self, client):
        novel = _mock_novel()
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel),
            patch("open_webui.routers.sw_novels.Novels.delete_novel_by_id", return_value=True),
        ):
            resp = client.delete("/novel-abc/delete")
        assert resp.status_code == 200
        assert resp.json() is True

    def test_delete_not_found(self, client):
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=None):
            resp = client.delete("/novel-xxx/delete")
        assert resp.status_code == 404

    def test_delete_forbidden_other_user(self, client):
        novel = _mock_novel(user_id="user-999")
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.delete("/novel-abc/delete")
        assert resp.status_code == 403

    def test_delete_dao_failure_returns_400(self, client):
        novel = _mock_novel()
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel),
            patch("open_webui.routers.sw_novels.Novels.delete_novel_by_id", return_value=False),
        ):
            resp = client.delete("/novel-abc/delete")
        assert resp.status_code == 400
