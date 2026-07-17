from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.utils import model_system_prompt_sync as sync_module


def _make_version(version_id: str = 'ver-1', content: str = 'prompt'):
    return SimpleNamespace(
        id=version_id,
        model_id='model-1',
        content=content,
        commit_message=None,
        user_id='user-1',
        created_at=1,
    )


def _make_binding(source: str = 'local', active_version_id: str | None = 'ver-1'):
    return SimpleNamespace(
        model_id='model-1',
        source=source,
        active_version_id=active_version_id,
    )


@pytest.mark.parametrize(
    ('previous', 'new'),
    [
        (None, None),
        ('', None),
        (None, ''),
        ('', ''),
        ('  ', None),
        ('same', 'same'),
    ],
)
@pytest.mark.asyncio
async def test_skip_unchanged_including_empty_and_none(previous, new):
    with patch(
        'open_webui.utils.model_system_prompt_sync.ModelSystemPromptBindings.get_by_model_id',
        new_callable=AsyncMock,
    ) as mock_binding:
        result = await sync_module.maybe_auto_version_from_params_system(
            'model-1',
            previous,
            new,
            'user-1',
            AsyncMock(),
        )

    assert result is None
    mock_binding.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_when_binding_source_is_langfuse():
    with (
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_binding(source='langfuse'),
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        result = await sync_module.maybe_auto_version_from_params_system(
            'model-1',
            'old',
            'new',
            'user-1',
            AsyncMock(),
        )

    assert result is None
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_when_active_version_content_matches_new():
    binding = _make_binding(active_version_id='ver-active')
    active = _make_version(version_id='ver-active', content='already active')

    with (
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=active,
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        result = await sync_module.maybe_auto_version_from_params_system(
            'model-1',
            'different mirror',
            'already active',
            'user-1',
            AsyncMock(),
        )

    assert result is None
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_creates_version_and_sets_local_binding():
    created = _make_version(version_id='ver-new', content='updated prompt')
    db = AsyncMock()

    with (
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_binding(source='local', active_version_id='ver-old'),
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.get_version_by_id',
            new_callable=AsyncMock,
            return_value=_make_version(version_id='ver-old', content='old prompt'),
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
            return_value=created,
        ) as mock_create,
        patch(
            'open_webui.utils.model_system_prompt_sync._ensure_local_binding',
            new_callable=AsyncMock,
            return_value=_make_binding(active_version_id='ver-new'),
        ) as mock_ensure,
    ):
        result = await sync_module.maybe_auto_version_from_params_system(
            'model-1',
            'old prompt',
            'updated prompt',
            'user-1',
            db,
            commit_message='import',
        )

    assert result is created
    mock_create.assert_awaited_once_with(
        model_id='model-1',
        content='updated prompt',
        user_id='user-1',
        commit_message='import',
        db=db,
    )
    mock_ensure.assert_awaited_once_with('model-1', 'ver-new', db=db)


@pytest.mark.asyncio
async def test_no_binding_creates_first_version():
    created = _make_version(version_id='ver-1', content='first prompt')
    db = AsyncMock()

    with (
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            'open_webui.utils.model_system_prompt_sync.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
            return_value=created,
        ) as mock_create,
        patch(
            'open_webui.utils.model_system_prompt_sync._ensure_local_binding',
            new_callable=AsyncMock,
            return_value=_make_binding(active_version_id='ver-1'),
        ) as mock_ensure,
    ):
        result = await sync_module.maybe_auto_version_from_params_system(
            'model-1',
            None,
            'first prompt',
            'user-1',
            db,
        )

    assert result is created
    mock_create.assert_awaited_once()
    mock_ensure.assert_awaited_once_with('model-1', 'ver-1', db=db)


def test_normalize_system_content_empty_to_none():
    assert sync_module.normalize_system_content('') is None
    assert sync_module.normalize_system_content('   ') is None
    assert sync_module.normalize_system_content(None) is None
    assert sync_module.normalize_system_content('keep me') == 'keep me'


def test_system_content_for_version_stores_empty_string():
    assert sync_module.system_content_for_version(None) == ''
    assert sync_module.system_content_for_version('') == ''
    assert sync_module.system_content_for_version('hello') == 'hello'
