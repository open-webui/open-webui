"""
Tests — Session Management Novel Courant (Task 1.2.3)
======================================================

Tests unitaires des endpoints de session :
    - GET  /current            : roman courant, aucun, roman orphelin
    - POST /{id}/select        : sélection OK, 404, 403, DAO failure
    - POST /deselect           : déselection OK, déjà vide (idempotent)

Tests de la dépendance get_current_novel :
    - Retourne le roman si current_novel_id valide
    - Retourne None si pas de current_novel_id
    - Retourne None si roman supprimé/orphelin
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_webui.routers.sw_novels import router, CurrentNovelResponse
from open_webui.utils.sw_dependencies import get_current_novel
from open_webui.models.sw_novels import NovelModel
from open_webui.internal.db import get_session
from open_webui.utils.auth import get_verified_user

# ─── App de test ──────────────────────────────────────────────────────────────

app = FastAPI()
app.include_router(router)

# ─── Helpers ──────────────────────────────────────────────────────────────────

USER_ID = "user-001"
OTHER_USER_ID = "user-999"
NOVEL_ID = "novel-abc"


def _mock_user(
    user_id: str = USER_ID,
    role: str = "user",
    current_novel_id: str | None = None,
):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.current_novel_id = current_novel_id
    return u


def _mock_novel(user_id: str = USER_ID, novel_id: str = NOVEL_ID) -> NovelModel:
    now = int(time.time())
    return NovelModel(
        id=novel_id,
        user_id=user_id,
        title="Mon Roman",
        status="draft",
        created_at=now,
        updated_at=now,
    )


def _mock_updated_user(user_id: str = USER_ID):
    """Simule le retour de Users.update_user_by_id."""
    u = MagicMock()
    u.id = user_id
    return u


def _override_get_session():
    yield MagicMock()


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def override_deps():
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_verified_user] = lambda: _mock_user()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ─── GET /current ──────────────────────────────────────────────────────────────


class TestGetCurrentNovel:
    def test_no_novel_selected_returns_not_selected(self, client):
        # current_novel_id = None par défaut dans _mock_user
        resp = client.get("/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_selected"] is False
        assert data["novel"] is None

    def test_novel_selected_returns_it(self, client):
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(
            current_novel_id=NOVEL_ID
        )
        novel = _mock_novel()
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel):
            resp = client.get("/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_selected"] is True
        assert data["novel"]["id"] == NOVEL_ID

    def test_orphan_novel_resets_and_returns_not_selected(self, client):
        """Le roman référencé a été supprimé → reset silencieux."""
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(
            current_novel_id="deleted-novel"
        )
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=None),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()) as mock_update,
        ):
            resp = client.get("/current")
        assert resp.status_code == 200
        assert resp.json()["is_selected"] is False
        # Vérifie que le reset a bien été déclenché
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args
        assert call_kwargs[1]["updated"]["current_novel_id"] is None

    def test_novel_belonging_to_other_user_resets(self, client):
        """Le roman appartient à un autre user → reset silencieux."""
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(
            current_novel_id=NOVEL_ID
        )
        foreign_novel = _mock_novel(user_id=OTHER_USER_ID)
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=foreign_novel),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()),
        ):
            resp = client.get("/current")
        assert resp.status_code == 200
        assert resp.json()["is_selected"] is False


# ─── POST /{id}/select ─────────────────────────────────────────────────────────


class TestSelectNovel:
    def test_select_ok(self, client):
        novel = _mock_novel()
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()),
        ):
            resp = client.post(f"/{NOVEL_ID}/select")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_selected"] is True
        assert data["novel"]["id"] == NOVEL_ID

    def test_select_persists_current_novel_id(self, client):
        """Vérifie que update_user_by_id est appelé avec le bon novel_id."""
        novel = _mock_novel()
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()) as mock_update,
        ):
            client.post(f"/{NOVEL_ID}/select")
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args
        assert call_kwargs[1]["updated"]["current_novel_id"] == NOVEL_ID

    def test_select_novel_not_found_returns_404(self, client):
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=None):
            resp = client.post(f"/{NOVEL_ID}/select")
        assert resp.status_code == 404

    def test_select_novel_other_user_returns_403(self, client):
        foreign_novel = _mock_novel(user_id=OTHER_USER_ID)
        with patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=foreign_novel):
            resp = client.post(f"/{NOVEL_ID}/select")
        assert resp.status_code == 403

    def test_select_admin_can_select_any_novel(self, client):
        """Un admin peut sélectionner le roman d'un autre utilisateur."""
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(role="admin", user_id="admin-1")
        foreign_novel = _mock_novel(user_id=OTHER_USER_ID)
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=foreign_novel),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user(user_id="admin-1")),
        ):
            resp = client.post(f"/{NOVEL_ID}/select")
        assert resp.status_code == 200

    def test_select_dao_failure_returns_400(self, client):
        novel = _mock_novel()
        with (
            patch("open_webui.routers.sw_novels.Novels.get_novel_by_id", return_value=novel),
            patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=None),
        ):
            resp = client.post(f"/{NOVEL_ID}/select")
        assert resp.status_code == 400


# ─── POST /deselect ────────────────────────────────────────────────────────────


class TestDeselectNovel:
    def test_deselect_ok(self, client):
        with patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()):
            resp = client.post("/deselect")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_selected"] is False
        assert data["novel"] is None

    def test_deselect_is_idempotent_when_no_novel_selected(self, client):
        """Aucune erreur même si current_novel_id est déjà None."""
        with patch("open_webui.routers.sw_novels.Users.update_user_by_id", return_value=_mock_updated_user()):
            resp = client.post("/deselect")
        assert resp.status_code == 200

    def test_deselect_persists_none(self, client):
        """Vérifie que update_user_by_id est appelé avec current_novel_id=None."""
        with patch(
            "open_webui.routers.sw_novels.Users.update_user_by_id",
            return_value=_mock_updated_user(),
        ) as mock_update:
            client.post("/deselect")
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args
        assert call_kwargs[1]["updated"]["current_novel_id"] is None


# ─── Tests de la dépendance get_current_novel ──────────────────────────────────


import asyncio
import inspect


def _run(coro_or_result):
    """Lance une coroutine ou retourne directement si déjà synchrone."""
    if inspect.iscoroutine(coro_or_result):
        return asyncio.run(coro_or_result)
    return coro_or_result


class TestGetCurrentNovelDependency:
    """Tests unitaires de la dépendance injectable — appels directs sans injection FastAPI."""

    def test_returns_none_when_no_current_novel_id(self):
        user = _mock_user(current_novel_id=None)
        db = MagicMock()

        with patch("open_webui.utils.sw_dependencies.Novels.get_novel_by_id") as mock_get:
            result = _run(get_current_novel(user=user, db=db))

        assert result is None
        mock_get.assert_not_called()

    def test_returns_novel_when_valid(self):
        user = _mock_user(current_novel_id=NOVEL_ID)
        db = MagicMock()
        novel = _mock_novel()

        with patch("open_webui.utils.sw_dependencies.Novels.get_novel_by_id", return_value=novel):
            result = _run(get_current_novel(user=user, db=db))

        assert result is not None
        assert result.id == NOVEL_ID

    def test_returns_none_when_novel_deleted(self):
        user = _mock_user(current_novel_id="deleted-id")
        db = MagicMock()

        with patch("open_webui.utils.sw_dependencies.Novels.get_novel_by_id", return_value=None):
            result = _run(get_current_novel(user=user, db=db))

        assert result is None

    def test_returns_none_when_novel_belongs_to_other_user(self):
        user = _mock_user(current_novel_id=NOVEL_ID)
        db = MagicMock()
        foreign_novel = _mock_novel(user_id=OTHER_USER_ID)

        with patch("open_webui.utils.sw_dependencies.Novels.get_novel_by_id", return_value=foreign_novel):
            result = _run(get_current_novel(user=user, db=db))

        assert result is None

