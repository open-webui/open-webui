"""Regression: deleting a model must clear system prompt binding and version history."""

from __future__ import annotations

import pytest
from open_webui.internal.db import Base, _apply_sqlite_pragmas
from open_webui.models.model_system_prompt_binding import ModelSystemPromptBindings
from open_webui.models.model_system_prompt_version import ModelSystemPromptVersions
from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

MODEL_ID = 'reused-model-id'
USER_ID = 'user-1'


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )

    @event.listens_for(engine.sync_engine, 'connect')
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        _apply_sqlite_pragmas(dbapi_connection)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _model_form() -> ModelForm:
    return ModelForm(
        id=MODEL_ID,
        name='Test Model',
        meta=ModelMeta(),
        params=ModelParams(system='legacy prompt'),
        is_active=True,
    )


@pytest.mark.asyncio
async def test_delete_model_clears_system_prompt_history_on_recreate(db_session):
    # Arrange
    created = await Models.insert_new_model(_model_form(), USER_ID, db=db_session)
    assert created is not None

    version = await ModelSystemPromptVersions.create_version(
        model_id=MODEL_ID,
        content='old system prompt v1',
        user_id=USER_ID,
        commit_message='initial',
        db=db_session,
    )
    assert version is not None

    await ModelSystemPromptVersions.create_version(
        model_id=MODEL_ID,
        content='old system prompt v2',
        user_id=USER_ID,
        commit_message='update',
        db=db_session,
    )
    await ModelSystemPromptBindings.upsert(
        model_id=MODEL_ID,
        source='local',
        active_version_id=version.id,
        db=db_session,
    )

    assert await ModelSystemPromptVersions.get_version_count(MODEL_ID, db=db_session) == 2
    assert await ModelSystemPromptBindings.get_by_model_id(MODEL_ID, db=db_session) is not None

    # Act
    deleted = await Models.delete_model_by_id(MODEL_ID, db=db_session)

    # Assert — artifacts gone after delete
    assert deleted is True
    assert await ModelSystemPromptVersions.get_version_count(MODEL_ID, db=db_session) == 0
    assert await ModelSystemPromptBindings.get_by_model_id(MODEL_ID, db=db_session) is None

    # Act — recreate model with the same id
    recreated = await Models.insert_new_model(_model_form(), USER_ID, db=db_session)

    # Assert — fresh model has no inherited history
    assert recreated is not None
    assert recreated.id == MODEL_ID
    assert await ModelSystemPromptVersions.get_version_count(MODEL_ID, db=db_session) == 0
    assert await ModelSystemPromptBindings.get_by_model_id(MODEL_ID, db=db_session) is None
