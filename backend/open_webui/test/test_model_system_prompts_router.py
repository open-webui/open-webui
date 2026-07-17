from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from open_webui.models.models import ModelMeta, ModelModel, ModelParams
from open_webui.routers import model_system_prompts as router_module


def _make_model(model_id: str = 'test-model', user_id: str = 'owner-id') -> ModelModel:
    return ModelModel(
        id=model_id,
        user_id=user_id,
        base_model_id='gpt-4',
        name='Test Model',
        params=ModelParams(system='legacy prompt'),
        meta=ModelMeta(),
        is_active=True,
        updated_at=1,
        created_at=1,
    )


def _make_user(user_id: str = 'owner-id', role: str = 'user'):
    return SimpleNamespace(id=user_id, role=role)


@pytest.mark.asyncio
async def test_has_model_read_access_owner():
    model = _make_model()
    user = _make_user(user_id='owner-id')

    assert await router_module._has_model_read_access(model, user, AsyncMock()) is True


@pytest.mark.asyncio
async def test_has_model_write_access_via_grant():
    model = _make_model(user_id='owner-id')
    user = _make_user(user_id='other-user')

    with patch(
        'open_webui.routers.model_system_prompts.AccessGrants.has_access',
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_has_access:
        result = await router_module._has_model_write_access(model, user, AsyncMock())

    assert result is True
    mock_has_access.assert_awaited_once_with(
        user_id='other-user',
        resource_type='model',
        resource_id='test-model',
        permission='write',
        db=mock_has_access.await_args.kwargs['db'],
    )


@pytest.mark.asyncio
async def test_require_model_read_access_denied():
    model = _make_model(user_id='owner-id')
    user = _make_user(user_id='other-user')

    with patch(
        'open_webui.routers.model_system_prompts.AccessGrants.has_access',
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module._require_model_read_access(model, user, AsyncMock())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_mirror_params_system_updates_model():
    model = _make_model()
    db = AsyncMock()

    with patch(
        'open_webui.routers.model_system_prompts.Models.update_model_by_id',
        new_callable=AsyncMock,
        return_value=model,
    ) as mock_update:
        await router_module._mirror_params_system(model, 'new prompt', db)

    form = mock_update.await_args.args[1]
    assert form.params.model_dump()['system'] == 'new prompt'


@pytest.mark.asyncio
async def test_get_version_for_model_or_404_cross_model():
    with patch(
        'open_webui.routers.model_system_prompts.ModelSystemPromptVersions.get_version_by_id',
        new_callable=AsyncMock,
        return_value=SimpleNamespace(model_id='other-model'),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module._get_version_for_model_or_404('test-model', 'version-1', AsyncMock())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_active_version_returns_400():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=SimpleNamespace(active_version_id='active-version'),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module.delete_model_system_prompt_history_entry(
                version_id='active-version',
                id='test-model',
                user=user,
                db=db,
            )

    assert exc.value.status_code == 400
    assert 'active production version' in exc.value.detail


@pytest.mark.asyncio
async def test_create_version_set_active_updates_binding_and_mirror():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()
    created = SimpleNamespace(
        id='version-1',
        model_id='test-model',
        content='new content',
        commit_message='init',
        user_id='owner-id',
        created_at=123,
        model_dump=lambda: {
            'id': 'version-1',
            'model_id': 'test-model',
            'content': 'new content',
            'commit_message': 'init',
            'user_id': 'owner-id',
            'created_at': 123,
        },
    )
    binding = SimpleNamespace(model_id='test-model', source='local', active_version_id='version-1')

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
            return_value=created,
        ),
        patch(
            'open_webui.routers.model_system_prompts._ensure_local_binding',
            new_callable=AsyncMock,
            return_value=binding,
        ) as mock_ensure,
        patch(
            'open_webui.routers.model_system_prompts._mirror_params_system',
            new_callable=AsyncMock,
        ) as mock_mirror,
        patch(
            'open_webui.routers.model_system_prompts.invalidate_system_prompt_cache',
        ) as mock_invalidate,
    ):
        response = await router_module.create_model_system_prompt_version(
            id='test-model',
            form_data=router_module.CreateSystemPromptVersionForm(
                content='new content',
                commit_message='init',
                set_active=True,
            ),
            user=user,
            db=db,
        )

    assert response.id == 'version-1'
    mock_ensure.assert_awaited_once_with('test-model', 'version-1', db)
    mock_mirror.assert_awaited_once_with(model, 'new content', db)
    mock_invalidate.assert_called_once_with('test-model')


@pytest.mark.asyncio
async def test_set_active_version_invalidates_cache():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()
    version = SimpleNamespace(id='version-1', content='active prompt')
    binding = SimpleNamespace(model_id='test-model', source='local', active_version_id='version-1')

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts._get_version_for_model_or_404',
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch(
            'open_webui.routers.model_system_prompts._ensure_local_binding',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts._mirror_params_system',
            new_callable=AsyncMock,
        ) as mock_mirror,
        patch(
            'open_webui.routers.model_system_prompts.invalidate_system_prompt_cache',
        ) as mock_invalidate,
    ):
        response = await router_module.set_active_model_system_prompt_version(
            id='test-model',
            form_data=router_module.SetActiveSystemPromptVersionForm(version_id='version-1'),
            user=user,
            db=db,
        )

    assert response.active_version_id == 'version-1'
    mock_mirror.assert_awaited_once_with(model, 'active prompt', db)
    mock_invalidate.assert_called_once_with('test-model')


@pytest.mark.asyncio
async def test_patch_binding_requires_write_access():
    model = _make_model()
    user = _make_user(user_id='other-user')
    db = AsyncMock()

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=401, detail='denied'),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module.patch_model_system_prompt_binding(
                id='test-model',
                form_data=router_module.PatchSystemPromptBindingForm(source='langfuse'),
                user=user,
                db=db,
            )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_sync_langfuse_requires_write_access():
    model = _make_model()
    user = _make_user(user_id='other-user')
    db = AsyncMock()

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=401, detail='denied'),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module.sync_langfuse_system_prompt(
                id='test-model',
                user=user,
                db=db,
            )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_detach_creates_local_version_and_mirrors():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()
    binding = SimpleNamespace(
        source='langfuse',
        cached_content='cached lf prompt',
    )
    version = SimpleNamespace(
        id='version-1',
        model_id='test-model',
        content='cached lf prompt',
        commit_message='Detached from Langfuse',
        user_id='owner-id',
        created_at=123,
        model_dump=lambda: {
            'id': 'version-1',
            'model_id': 'test-model',
            'content': 'cached lf prompt',
            'commit_message': 'Detached from Langfuse',
            'user_id': 'owner-id',
            'created_at': 123,
        },
    )
    updated_binding = SimpleNamespace(
        model_id='test-model',
        source='local',
        active_version_id='version-1',
    )

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptVersions.create_version',
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.upsert',
            new_callable=AsyncMock,
            return_value=updated_binding,
        ) as mock_upsert,
        patch(
            'open_webui.routers.model_system_prompts._mirror_params_system',
            new_callable=AsyncMock,
        ) as mock_mirror,
        patch(
            'open_webui.routers.model_system_prompts.invalidate_system_prompt_cache',
        ) as mock_invalidate,
    ):
        response = await router_module.detach_langfuse_system_prompt(
            id='test-model',
            user=user,
            db=db,
        )

    assert response.binding.source == 'local'
    assert response.version.id == 'version-1'
    mock_upsert.assert_awaited_once()
    mock_mirror.assert_awaited_once_with(model, 'cached lf prompt', db)
    mock_invalidate.assert_called_once_with('test-model')


@pytest.mark.asyncio
async def test_authorize_langfuse_connection_read_only_bound():
    model = _make_model()
    user = _make_user(user_id='reader-id')
    binding = SimpleNamespace(connection_id='bound-conn')

    with patch(
        'open_webui.routers.model_system_prompts.AccessGrants.has_access',
        new_callable=AsyncMock,
        return_value=True,
    ):
        await router_module._authorize_langfuse_connection_for_model(
            model,
            user,
            AsyncMock(),
            'bound-conn',
            binding,
            configure=False,
        )


@pytest.mark.asyncio
async def test_authorize_langfuse_connection_read_only_rejects_arbitrary():
    model = _make_model()
    user = _make_user(user_id='reader-id')
    binding = SimpleNamespace(connection_id='bound-conn')

    with patch(
        'open_webui.routers.model_system_prompts.AccessGrants.has_access',
        new_callable=AsyncMock,
        return_value=True,
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module._authorize_langfuse_connection_for_model(
                model,
                user,
                AsyncMock(),
                'other-conn',
                binding,
                configure=False,
            )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authorize_langfuse_connection_write_can_configure():
    model = _make_model()
    user = _make_user(user_id='editor-id')

    with patch(
        'open_webui.routers.model_system_prompts.AccessGrants.has_access',
        new_callable=AsyncMock,
        side_effect=lambda **kwargs: kwargs['permission'] == 'write',
    ):
        await router_module._authorize_langfuse_connection_for_model(
            model,
            user,
            AsyncMock(),
            'new-conn',
            None,
            configure=True,
        )


@pytest.mark.asyncio
async def test_preview_rejects_arbitrary_connection_for_read_only():
    model = _make_model()
    user = _make_user(user_id='reader-id')
    db = AsyncMock()
    binding = SimpleNamespace(
        connection_id='bound-conn',
        external_name='bound-prompt',
        external_label=None,
        external_version=None,
    )

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_read_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts._has_model_write_access',
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module.preview_langfuse_system_prompt(
                id='test-model',
                form_data=router_module.LangfusePromptPreviewForm(
                    connection_id='other-conn',
                    external_name='secret-prompt',
                ),
                user=user,
                db=db,
            )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_preview_allows_bound_connection_for_read_only():
    model = _make_model()
    user = _make_user(user_id='reader-id')
    db = AsyncMock()
    binding = SimpleNamespace(
        connection_id='bound-conn',
        external_name='bound-prompt',
        external_label=None,
        external_version=None,
    )
    preview = router_module.LangfusePromptActionResponse(
        content='cached prompt',
        prompt_name='bound-prompt',
        prompt_version='1',
    )

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_read_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts._preview_langfuse_prompt',
            new_callable=AsyncMock,
            return_value=preview,
        ) as mock_preview,
    ):
        result = await router_module.preview_langfuse_system_prompt(
            id='test-model',
            form_data=router_module.LangfusePromptPreviewForm(
                connection_id='bound-conn',
                external_name='bound-prompt',
            ),
            user=user,
            db=db,
        )

    assert result.content == 'cached prompt'
    mock_preview.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_local_binding_clears_langfuse_fields():
    db = AsyncMock()
    binding = SimpleNamespace(model_id='test-model', source='local', active_version_id='version-1')

    with patch(
        'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.upsert',
        new_callable=AsyncMock,
        return_value=binding,
    ) as mock_upsert:
        result = await router_module._ensure_local_binding('test-model', 'version-1', db)

    assert result.source == 'local'
    kwargs = mock_upsert.await_args.kwargs
    assert kwargs['source'] == 'local'
    assert kwargs['active_version_id'] == 'version-1'
    assert kwargs['connection_id'] is None
    assert kwargs['external_name'] is None
    assert kwargs['cached_content'] is None
    assert kwargs['cached_at'] is None


@pytest.mark.asyncio
async def test_patch_binding_clears_cache_when_identity_changes():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()
    binding = SimpleNamespace(
        source='langfuse',
        active_version_id=None,
        connection_id='conn-1',
        external_name='old-prompt',
        external_label='production',
        external_version=None,
        cached_content='stale content',
        cached_version='3',
        cached_at=123,
        cache_ttl_seconds=300,
    )
    updated = SimpleNamespace(model_id='test-model', source='langfuse', cached_content=None)

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts._authorize_langfuse_connection_for_model',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.upsert',
            new_callable=AsyncMock,
            return_value=updated,
        ) as mock_upsert,
        patch(
            'open_webui.routers.model_system_prompts.invalidate_system_prompt_cache',
        ),
    ):
        await router_module.patch_model_system_prompt_binding(
            id='test-model',
            form_data=router_module.PatchSystemPromptBindingForm(
                external_name='new-prompt',
            ),
            user=user,
            db=db,
        )

    kwargs = mock_upsert.await_args.kwargs
    assert kwargs['external_name'] == 'new-prompt'
    assert kwargs['cached_content'] is None
    assert kwargs['cached_version'] is None
    assert kwargs['cached_at'] is None


@pytest.mark.asyncio
async def test_patch_binding_to_local_clears_langfuse_fields():
    model = _make_model()
    user = _make_user()
    db = AsyncMock()
    binding = SimpleNamespace(
        source='langfuse',
        active_version_id='version-1',
        connection_id='conn-1',
        external_name='lf-prompt',
        external_label=None,
        external_version=None,
        cached_content='cached',
        cached_version='1',
        cached_at=123,
        cache_ttl_seconds=300,
    )
    updated = SimpleNamespace(model_id='test-model', source='local')

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_write_access',
            new_callable=AsyncMock,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            'open_webui.routers.model_system_prompts.ModelSystemPromptBindings.upsert',
            new_callable=AsyncMock,
            return_value=updated,
        ) as mock_upsert,
        patch(
            'open_webui.routers.model_system_prompts.invalidate_system_prompt_cache',
        ),
    ):
        await router_module.patch_model_system_prompt_binding(
            id='test-model',
            form_data=router_module.PatchSystemPromptBindingForm(source='local'),
            user=user,
            db=db,
        )

    kwargs = mock_upsert.await_args.kwargs
    assert kwargs['source'] == 'local'
    assert kwargs['connection_id'] is None
    assert kwargs['external_name'] is None
    assert kwargs['cached_content'] is None


@pytest.mark.asyncio
async def test_list_model_langfuse_prompts_requires_model_read():
    model = _make_model()
    user = _make_user(user_id='other-user')
    db = AsyncMock()

    with (
        patch(
            'open_webui.routers.model_system_prompts._get_model_or_404',
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            'open_webui.routers.model_system_prompts._require_model_read_access',
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=401, detail='denied'),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await router_module.list_model_langfuse_prompts(
                id='test-model',
                connection_id='conn-1',
                user=user,
                db=db,
            )

    assert exc.value.status_code == 401


def test_router_paths_and_no_collision_with_model_update():
    paths = {route.path for route in router_module.router.routes if hasattr(route, 'path')}

    assert paths == {
        '/system-prompt/binding',
        '/system-prompt/history',
        '/system-prompt/history/{version_id}',
        '/system-prompt/versions',
        '/system-prompt/active',
        '/system-prompt/langfuse/sync',
        '/system-prompt/langfuse/preview',
        '/system-prompt/langfuse/connections',
        '/system-prompt/langfuse/prompts',
        '/system-prompt/langfuse/prompts/{prompt_name:path}',
        '/system-prompt/detach',
    }
    assert '/model/update' not in paths


def test_router_import_smoke():
    from open_webui.routers import model_system_prompts

    assert model_system_prompts.router is not None
    assert model_system_prompts.PAGE_SIZE == 20
