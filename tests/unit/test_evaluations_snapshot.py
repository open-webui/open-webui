"""
Unit tests for ENABLE_FEEDBACK_CHAT_SNAPSHOT guard in evaluations router.

Uses importlib to load the router module directly from file path,
bypassing the full open_webui package import chain (which requires a DB).
"""
import sys
import types
import importlib.util
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any


# ---------------------------------------------------------------------------
# Pydantic stubs — must be real BaseModel subclasses so FastAPI can register
# response_model= annotations without crashing.
# ---------------------------------------------------------------------------

class RatingData(BaseModel):
    model_config = ConfigDict(extra='allow', protected_namespaces=())
    rating: Optional[Any] = None
    model_id: Optional[str] = None
    sibling_model_ids: Optional[list] = None
    reason: Optional[str] = None
    comment: Optional[str] = None


class SnapshotData(BaseModel):
    chat: Optional[dict] = None


class FeedbackForm(BaseModel):
    model_config = ConfigDict(extra='ignore')
    type: str = 'rating'
    data: Optional[RatingData] = None
    meta: Optional[dict] = None
    snapshot: Optional[SnapshotData] = None


class FeedbackModel(BaseModel):
    id: str = 'fb-001'
    user_id: str = 'user-001'
    type: str = 'rating'
    data: Optional[dict] = None
    meta: Optional[dict] = None
    snapshot: Optional[dict] = None


class FeedbackIdResponse(BaseModel):
    id: str = ''


class FeedbackResponse(BaseModel):
    id: str = ''


class FeedbackUserResponse(BaseModel):
    id: str = ''


class FeedbackListResponse(BaseModel):
    items: list = []
    count: int = 0


class LeaderboardResponse(BaseModel):
    pass


class ModelHistoryResponse(BaseModel):
    pass


class LeaderboardFeedbackData(BaseModel):
    pass


class ModelHistoryEntry(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Stub sys.modules
# ---------------------------------------------------------------------------

def _build_stubs():
    feedbacks_mod = types.ModuleType('open_webui.models.feedbacks')
    feedbacks_mod.FeedbackForm = FeedbackForm
    feedbacks_mod.SnapshotData = SnapshotData
    feedbacks_mod.RatingData = RatingData
    feedbacks_mod.FeedbackModel = FeedbackModel
    feedbacks_mod.FeedbackIdResponse = FeedbackIdResponse
    feedbacks_mod.FeedbackResponse = FeedbackResponse
    feedbacks_mod.FeedbackUserResponse = FeedbackUserResponse
    feedbacks_mod.FeedbackListResponse = FeedbackListResponse
    feedbacks_mod.LeaderboardFeedbackData = LeaderboardFeedbackData
    feedbacks_mod.ModelHistoryEntry = ModelHistoryEntry
    feedbacks_mod.ModelHistoryResponse = ModelHistoryResponse
    feedbacks_mod.Feedbacks = MagicMock()

    db_mod = types.ModuleType('open_webui.internal.db')
    db_mod.Base = MagicMock()
    db_mod.JSONField = MagicMock()
    db_mod.get_async_db_context = MagicMock()
    db_mod.get_async_session = MagicMock()

    auth_mod = types.ModuleType('open_webui.utils.auth')
    auth_mod.get_verified_user = MagicMock()
    auth_mod.get_admin_user = MagicMock()

    misc_mod = types.ModuleType('open_webui.utils.misc')
    misc_mod.get_gravatar_url = MagicMock()

    constants_mod = types.ModuleType('open_webui.constants')
    error_msgs = MagicMock()
    error_msgs.DEFAULT = lambda: 'error'
    error_msgs.NOT_FOUND = 'not found'
    constants_mod.ERROR_MESSAGES = error_msgs

    users_mod = types.ModuleType('open_webui.models.users')
    users_mod.Users = MagicMock()
    users_mod.UserModel = MagicMock()

    config_mod = types.ModuleType('open_webui.config')

    owui_pkg = types.ModuleType('open_webui')
    owui_pkg.__path__ = []
    owui_pkg.__package__ = 'open_webui'

    models_pkg = types.ModuleType('open_webui.models')
    models_pkg.__path__ = []

    internal_pkg = types.ModuleType('open_webui.internal')
    internal_pkg.__path__ = []

    utils_pkg = types.ModuleType('open_webui.utils')
    utils_pkg.__path__ = []

    routers_pkg = types.ModuleType('open_webui.routers')
    routers_pkg.__path__ = []
    routers_pkg.__package__ = 'open_webui.routers'

    for name, mod in [
        ('open_webui', owui_pkg),
        ('open_webui.models', models_pkg),
        ('open_webui.models.feedbacks', feedbacks_mod),
        ('open_webui.models.users', users_mod),
        ('open_webui.internal', internal_pkg),
        ('open_webui.internal.db', db_mod),
        ('open_webui.utils', utils_pkg),
        ('open_webui.utils.auth', auth_mod),
        ('open_webui.utils.misc', misc_mod),
        ('open_webui.constants', constants_mod),
        ('open_webui.config', config_mod),
        ('open_webui.routers', routers_pkg),
    ]:
        sys.modules[name] = mod

    return feedbacks_mod.Feedbacks


_Feedbacks_mock = _build_stubs()


def _load_evaluations_router():
    """Load open_webui/routers/evaluations.py directly from filesystem."""
    router_path = Path(__file__).parents[2] / 'backend' / 'open_webui' / 'routers' / 'evaluations.py'
    spec = importlib.util.spec_from_file_location('open_webui.routers.evaluations', router_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['open_webui.routers.evaluations'] = mod
    spec.loader.exec_module(mod)
    return mod


_evaluations = _load_evaluations_router()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_form_data(with_snapshot: bool) -> FeedbackForm:
    snapshot = SnapshotData(chat={"messages": [{"role": "user", "content": "hello"}]}) if with_snapshot else None
    return FeedbackForm(
        type="rating",
        data=RatingData(rating=1, model_id="gpt-4"),
        meta={"chat_id": "chat-123", "message_id": "msg-456"},
        snapshot=snapshot,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_feedback_snapshot_stripped_when_disabled():
    """When ENABLE_FEEDBACK_CHAT_SNAPSHOT=False, snapshot is set to None before ORM call."""
    form_data = make_form_data(with_snapshot=True)
    assert form_data.snapshot is not None  # sanity

    request = MagicMock()
    request.app.state.config.ENABLE_FEEDBACK_CHAT_SNAPSHOT = False

    user = MagicMock()
    user.id = "user-001"

    captured = {}

    async def fake_insert(user_id, form_data, db):
        captured["snapshot"] = form_data.snapshot
        return FeedbackModel()

    _evaluations.Feedbacks.insert_new_feedback = fake_insert
    await _evaluations.create_feedback(request=request, form_data=form_data, user=user, db=MagicMock())

    assert captured["snapshot"] is None, "snapshot should be None when ENABLE_FEEDBACK_CHAT_SNAPSHOT=False"


@pytest.mark.asyncio
async def test_create_feedback_snapshot_preserved_when_enabled():
    """When ENABLE_FEEDBACK_CHAT_SNAPSHOT=True, snapshot passes through unchanged."""
    form_data = make_form_data(with_snapshot=True)
    original_snapshot = form_data.snapshot

    request = MagicMock()
    request.app.state.config.ENABLE_FEEDBACK_CHAT_SNAPSHOT = True

    user = MagicMock()
    user.id = "user-001"

    captured = {}

    async def fake_insert(user_id, form_data, db):
        captured["snapshot"] = form_data.snapshot
        return FeedbackModel()

    _evaluations.Feedbacks.insert_new_feedback = fake_insert
    await _evaluations.create_feedback(request=request, form_data=form_data, user=user, db=MagicMock())

    assert captured["snapshot"] == original_snapshot, "snapshot should be unchanged when ENABLE_FEEDBACK_CHAT_SNAPSHOT=True"


@pytest.mark.asyncio
async def test_update_feedback_snapshot_stripped_when_disabled():
    """When ENABLE_FEEDBACK_CHAT_SNAPSHOT=False, snapshot is set to None in update path (regular user)."""
    form_data = make_form_data(with_snapshot=True)

    request = MagicMock()
    request.app.state.config.ENABLE_FEEDBACK_CHAT_SNAPSHOT = False

    user = MagicMock()
    user.role = "user"
    user.id = "user-001"

    captured = {}

    async def fake_update(id, user_id, form_data, db):
        captured["snapshot"] = form_data.snapshot
        return FeedbackModel()

    _evaluations.Feedbacks.update_feedback_by_id_and_user_id = fake_update
    await _evaluations.update_feedback_by_id(id="fb-001", request=request, form_data=form_data, user=user, db=MagicMock())

    assert captured["snapshot"] is None, "snapshot should be None in update when ENABLE_FEEDBACK_CHAT_SNAPSHOT=False"


@pytest.mark.asyncio
async def test_update_feedback_snapshot_preserved_when_enabled():
    """When ENABLE_FEEDBACK_CHAT_SNAPSHOT=True, snapshot passes through in update path."""
    form_data = make_form_data(with_snapshot=True)
    original_snapshot = form_data.snapshot

    request = MagicMock()
    request.app.state.config.ENABLE_FEEDBACK_CHAT_SNAPSHOT = True

    user = MagicMock()
    user.role = "user"
    user.id = "user-001"

    captured = {}

    async def fake_update(id, user_id, form_data, db):
        captured["snapshot"] = form_data.snapshot
        return FeedbackModel()

    _evaluations.Feedbacks.update_feedback_by_id_and_user_id = fake_update
    await _evaluations.update_feedback_by_id(id="fb-001", request=request, form_data=form_data, user=user, db=MagicMock())

    assert captured["snapshot"] == original_snapshot, "snapshot should be unchanged when enabled"
