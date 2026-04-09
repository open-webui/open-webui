"""
Tests — Router sw_kb (Task 1.2.2)
=====================================

Tests unitaires du router FastAPI /api/sw/novels/{novel_id}/kb.
Stratégie : mocks des DAOs (Novels, KnowledgeBases) et de get_verified_user.

Couverture:
    - GET /                        : KB existante, lazy init (KB absente)
    - GET /{section}               : section existante, section vide, section invalide (422)
    - POST /{section}/add          : ajout OK, UUID auto-généré, ownership KO
    - POST /{section}/{id}/update  : update OK (merge), item non trouvé (404)
    - DELETE /{section}/{id}/delete: suppression OK, item non trouvé (404)
    - PUT /{section}/replace       : remplacement complet, auto-UUID sur items sans id
    - Ownership : novel inexistant (404), novel autre user (403), admin bypass
"""

import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_webui.routers.sw_kb import router
from open_webui.models.sw_novels import KnowledgeBaseModel, NovelModel
from open_webui.internal.db import get_session
from open_webui.utils.auth import get_verified_user

# ─── App de test ──────────────────────────────────────────────────────────────

app = FastAPI()
# Le router est monté avec le path param novel_id dans le préfixe
app.include_router(router, prefix="/{novel_id}/kb")


# ─── Helpers ──────────────────────────────────────────────────────────────────

NOVEL_ID = "novel-001"
USER_ID = "user-001"
OTHER_USER_ID = "user-999"
ITEM_ID = "item-aaa"


def _mock_user(user_id: str = USER_ID, role: str = "user"):
    u = MagicMock()
    u.id = user_id
    u.role = role
    return u


def _mock_novel(user_id: str = USER_ID) -> NovelModel:
    now = int(time.time())
    return NovelModel(
        id=NOVEL_ID,
        user_id=user_id,
        title="Test Novel",
        status="draft",
        created_at=now,
        updated_at=now,
    )


def _mock_kb(
    characters: list | None = None,
    locations: list | None = None,
    universe_docs: list | None = None,
    objects: list | None = None,
    timeline: list | None = None,
) -> KnowledgeBaseModel:
    return KnowledgeBaseModel(
        id="kb-001",
        novel_id=NOVEL_ID,
        universe_docs=universe_docs or [],
        characters=characters or [],
        locations=locations or [],
        objects=objects or [],
        timeline=timeline or [],
        updated_at=int(time.time()),
    )


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


def url(path: str = "") -> str:
    """Construit l'URL complète avec le novel_id."""
    return f"/{NOVEL_ID}/kb{path}"


# ─── GET / ─────────────────────────────────────────────────────────────────────


class TestGetKB:
    def test_get_existing_kb(self, client):
        kb = _mock_kb(characters=[{"id": ITEM_ID, "name": "Aela"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.get(url("/"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["novel_id"] == NOVEL_ID
        assert len(data["characters"]) == 1

    def test_get_lazily_creates_kb_if_missing(self, client):
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=None),
            patch("open_webui.routers.sw_kb.KnowledgeBases.insert_new_kb", return_value=kb) as mock_create,
        ):
            resp = client.get(url("/"))
        assert resp.status_code == 200
        mock_create.assert_called_once()

    def test_get_novel_not_found_returns_404(self, client):
        with patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=None):
            resp = client.get(url("/"))
        assert resp.status_code == 404

    def test_get_novel_other_user_returns_403(self, client):
        with patch(
            "open_webui.routers.sw_kb.Novels.get_novel_by_id",
            return_value=_mock_novel(user_id=OTHER_USER_ID),
        ):
            resp = client.get(url("/"))
        assert resp.status_code == 403

    def test_admin_can_access_any_novel_kb(self, client):
        app.dependency_overrides[get_verified_user] = lambda: _mock_user(role="admin", user_id="admin-1")
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel(user_id=OTHER_USER_ID)),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.get(url("/"))
        assert resp.status_code == 200


# ─── GET /{section} ────────────────────────────────────────────────────────────


class TestGetKBSection:
    def test_get_characters_section(self, client):
        items = [{"id": ITEM_ID, "name": "Aela"}, {"id": "item-bbb", "name": "Bran"}]
        kb = _mock_kb(characters=items)
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.get(url("/characters"))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_empty_section_returns_empty_list(self, client):
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.get(url("/locations"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_section_returns_422(self, client):
        resp = client.get(url("/invalid_section"))
        assert resp.status_code == 422

    def test_get_all_valid_sections(self, client):
        kb = _mock_kb()
        for section in ["universe_docs", "characters", "locations", "objects", "timeline"]:
            with (
                patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
                patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            ):
                resp = client.get(url(f"/{section}"))
            assert resp.status_code == 200, f"Section {section} should return 200"


# ─── POST /{section}/add ───────────────────────────────────────────────────────


class TestAddKBItem:
    def test_add_character_ok(self, client):
        kb = _mock_kb()
        new_kb = _mock_kb(characters=[{"id": "generated-uuid", "name": "Aela", "role": "hero"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=new_kb),
        ):
            resp = client.post(
                url("/characters/add"),
                json={"data": {"name": "Aela", "role": "hero"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Aela"
        assert "id" in data  # UUID auto-généré

    def test_add_item_generates_uuid(self, client):
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=_mock_kb()),
        ):
            resp = client.post(url("/locations/add"), json={"data": {"name": "Forêt d'Elen"}})
        assert resp.status_code == 200
        item_id = resp.json().get("id")
        # Vérifier que c'est bien un UUID valide
        uuid.UUID(item_id)  # lève ValueError si invalide

    def test_add_to_all_sections(self, client):
        kb = _mock_kb()
        for section in ["universe_docs", "characters", "locations", "objects", "timeline"]:
            with (
                patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
                patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
                patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=kb),
            ):
                resp = client.post(url(f"/{section}/add"), json={"data": {"label": "test"}})
            assert resp.status_code == 200, f"POST /{section}/add should return 200"

    def test_add_novel_not_found_returns_404(self, client):
        with patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=None):
            resp = client.post(url("/characters/add"), json={"data": {"name": "X"}})
        assert resp.status_code == 404

    def test_add_forbidden_other_user_returns_403(self, client):
        with patch(
            "open_webui.routers.sw_kb.Novels.get_novel_by_id",
            return_value=_mock_novel(user_id=OTHER_USER_ID),
        ):
            resp = client.post(url("/characters/add"), json={"data": {"name": "X"}})
        assert resp.status_code == 403

    def test_add_dao_failure_returns_400(self, client):
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=None),
        ):
            resp = client.post(url("/characters/add"), json={"data": {"name": "X"}})
        assert resp.status_code == 400


# ─── POST /{section}/{item_id}/update ──────────────────────────────────────────


class TestUpdateKBItem:
    def test_update_item_ok(self, client):
        existing = [{"id": ITEM_ID, "name": "Aela", "role": "hero"}]
        kb = _mock_kb(characters=existing)
        updated_kb = _mock_kb(characters=[{"id": ITEM_ID, "name": "Aela", "role": "mentor"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=updated_kb),
        ):
            resp = client.post(
                url(f"/characters/{ITEM_ID}/update"),
                json={"data": {"role": "mentor"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == ITEM_ID
        assert data["role"] == "mentor"
        assert data["name"] == "Aela"  # Champ préservé par le merge

    def test_update_preserves_item_id(self, client):
        existing = [{"id": ITEM_ID, "name": "Aela"}]
        kb = _mock_kb(characters=existing)
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=kb),
        ):
            resp = client.post(
                url(f"/characters/{ITEM_ID}/update"),
                json={"data": {"id": "attempt-to-change-id", "name": "Aela Renamed"}},
            )
        assert resp.status_code == 200
        # L'id doit être préservé, pas remplacé
        assert resp.json()["id"] == ITEM_ID

    def test_update_item_not_found_returns_404(self, client):
        kb = _mock_kb(characters=[{"id": "other-item", "name": "Bran"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.post(url(f"/characters/{ITEM_ID}/update"), json={"data": {"name": "X"}})
        assert resp.status_code == 404

    def test_update_novel_not_found_returns_404(self, client):
        with patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=None):
            resp = client.post(url(f"/characters/{ITEM_ID}/update"), json={"data": {}})
        assert resp.status_code == 404


# ─── DELETE /{section}/{item_id}/delete ────────────────────────────────────────


class TestDeleteKBItem:
    def test_delete_item_ok(self, client):
        existing = [{"id": ITEM_ID, "name": "Aela"}, {"id": "item-bbb", "name": "Bran"}]
        kb = _mock_kb(characters=existing)
        updated_kb = _mock_kb(characters=[{"id": "item-bbb", "name": "Bran"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=updated_kb),
        ):
            resp = client.delete(url(f"/characters/{ITEM_ID}/delete"))
        assert resp.status_code == 200
        assert resp.json() is True

    def test_delete_item_not_found_returns_404(self, client):
        kb = _mock_kb(characters=[{"id": "item-bbb", "name": "Bran"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
        ):
            resp = client.delete(url(f"/characters/{ITEM_ID}/delete"))
        assert resp.status_code == 404

    def test_delete_forbidden_other_user(self, client):
        with patch(
            "open_webui.routers.sw_kb.Novels.get_novel_by_id",
            return_value=_mock_novel(user_id=OTHER_USER_ID),
        ):
            resp = client.delete(url(f"/characters/{ITEM_ID}/delete"))
        assert resp.status_code == 403

    def test_delete_dao_failure_returns_400(self, client):
        kb = _mock_kb(characters=[{"id": ITEM_ID, "name": "Aela"}])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=None),
        ):
            resp = client.delete(url(f"/characters/{ITEM_ID}/delete"))
        assert resp.status_code == 400


# ─── PUT /{section}/replace ────────────────────────────────────────────────────


class TestReplaceKBSection:
    def test_replace_section_ok(self, client):
        kb = _mock_kb()
        new_items = [{"name": "Aela"}, {"id": "existing-id", "name": "Bran"}]
        replaced_kb = _mock_kb(characters=[
            {"id": "new-uuid", "name": "Aela"},
            {"id": "existing-id", "name": "Bran"},
        ])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=replaced_kb),
        ):
            resp = client.put(url("/characters/replace"), json={"items": new_items})
        assert resp.status_code == 200

    def test_replace_with_empty_list_clears_section(self, client):
        kb = _mock_kb(characters=[{"id": ITEM_ID, "name": "Aela"}])
        empty_kb = _mock_kb(characters=[])
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=empty_kb),
        ):
            resp = client.put(url("/characters/replace"), json={"items": []})
        assert resp.status_code == 200

    def test_replace_auto_generates_uuid_for_items_without_id(self, client):
        """Vérifie que les items sans `id` reçoivent un UUID dans l'appel DAO."""
        kb = _mock_kb()
        captured: list[dict] = []

        def mock_update(novel_id, updated, db=None):
            captured.append(updated)
            return _mock_kb()

        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", side_effect=mock_update),
        ):
            resp = client.put(
                url("/characters/replace"),
                json={"items": [{"name": "Aela"}, {"name": "Bran"}]},
            )
        assert resp.status_code == 200
        items_sent = captured[0]["characters"]
        for item in items_sent:
            assert "id" in item
            uuid.UUID(item["id"])  # Valide que c'est bien un UUID

    def test_replace_preserves_existing_id(self, client):
        """Un item qui a déjà un `id` doit le conserver."""
        kb = _mock_kb()
        captured: list[dict] = []

        def mock_update(novel_id, updated, db=None):
            captured.append(updated)
            return _mock_kb()

        existing_id = "my-fixed-id-123"
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", side_effect=mock_update),
        ):
            resp = client.put(
                url("/characters/replace"),
                json={"items": [{"id": existing_id, "name": "Aela"}]},
            )
        assert resp.status_code == 200
        items_sent = captured[0]["characters"]
        assert items_sent[0]["id"] == existing_id

    def test_replace_novel_not_found_returns_404(self, client):
        with patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=None):
            resp = client.put(url("/characters/replace"), json={"items": []})
        assert resp.status_code == 404

    def test_replace_dao_failure_returns_400(self, client):
        kb = _mock_kb()
        with (
            patch("open_webui.routers.sw_kb.Novels.get_novel_by_id", return_value=_mock_novel()),
            patch("open_webui.routers.sw_kb.KnowledgeBases.get_kb_by_novel_id", return_value=kb),
            patch("open_webui.routers.sw_kb.KnowledgeBases.update_kb_by_novel_id", return_value=None),
        ):
            resp = client.put(url("/characters/replace"), json={"items": [{"name": "X"}]})
        assert resp.status_code == 400
