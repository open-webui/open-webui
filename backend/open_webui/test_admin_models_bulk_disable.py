import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

# Create a temporary directory for clean disposable test data
temp_dir = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = temp_dir.name
os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir.name}/test.db'
os.environ['WEBUI_SECRET_KEY'] = 'test-secret-key-123456789012'

from open_webui.main import get_models
from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
from open_webui.models.users import UserModel


async def run_tests():
    print('=================================================================')
    print('STARTING REGRESSION TEST: Admin Models Bulk Disable & Multi-Provider')
    print('=================================================================')

    admin_user = UserModel(
        id='admin-user-id',
        name='Admin User',
        email='admin@example.com',
        role='admin',
        created_at=0,
        updated_at=0,
        last_active_at=0,
    )

    regular_user = UserModel(
        id='regular-user-id',
        name='Regular User',
        email='user@example.com',
        role='user',
        created_at=0,
        updated_at=0,
        last_active_at=0,
    )

    mock_request = MagicMock()
    mock_request.app.state.MODELS = {}
    mock_request.app.state.BASE_MODELS = []
    mock_request.app.state.redis = None

    # 1. Multiple configured model providers
    provider_models = [
        # Provider 1: NVIDIA NIM
        {'id': 'nvidia/nemotron-4-340b-instruct', 'name': 'NVIDIA Nemotron 340B', 'owned_by': 'openai'},
        {'id': 'meta/llama-3.1-70b-instruct', 'name': 'Meta Llama 3.1 70B', 'owned_by': 'openai'},
        # Provider 2: OpenRouter
        {'id': 'anthropic/claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet', 'owned_by': 'openai'},
        {'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek V2.5', 'owned_by': 'openai'},
        # Provider 3: Google Generative Language API
        {'id': 'google/gemini-1.5-pro', 'name': 'Gemini 1.5 Pro', 'owned_by': 'openai'},
        # Provider 4: GitHub Copilot
        {'id': 'copilot/gpt-4o', 'name': 'Copilot GPT-4o', 'owned_by': 'openai'},
        # Provider 5: Local OpenAI endpoint
        {'id': 'local/mistral-nemo', 'name': 'Local Mistral Nemo', 'owned_by': 'openai'},
    ]

    print(f'\n[TEST 1] Testing baseline: {len(provider_models)} models from 5 providers')
    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=False, user=admin_user)
            active_ids = [m['id'] for m in res['data']]
            assert len(active_ids) == 7, f'Expected 7 models, got {len(active_ids)}'
            print(f'  ✓ Baseline active models returned: {len(active_ids)}')

    # 2. Add custom/preset models
    print('\n[TEST 2] Adding custom/preset model based on one of the provider models')
    custom_form = ModelForm(
        id='wallfire-mcp',
        name='Wallfire MCP',
        base_model_id='nvidia/nemotron-4-340b-instruct',
        meta=ModelMeta(),
        params=ModelParams(),
        is_active=True,
    )
    await Models.insert_new_model(custom_form, admin_user.id)
    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=False, user=admin_user)
            active_ids = [m['id'] for m in res['data']]
            assert 'wallfire-mcp' in active_ids
            assert len(active_ids) == 8
            print(f'  ✓ Total active models including custom model: {len(active_ids)}')

    # 3. Simulate "Disable All Models" action
    print("\n[TEST 3] Simulating 'Disable All Models' from Admin -> Models")
    for m in provider_models:
        form = ModelForm(
            id=m['id'],
            name=m['name'],
            base_model_id=None,
            meta=ModelMeta(),
            params=ModelParams(),
            is_active=False,
        )
        await Models.insert_new_model(form, admin_user.id)

    # Also disable the custom preset model
    await Models.update_model_by_id(
        'wallfire-mcp',
        ModelForm(
            id='wallfire-mcp',
            name='Wallfire MCP',
            base_model_id='nvidia/nemotron-4-340b-instruct',
            meta=ModelMeta(),
            params=ModelParams(),
            is_active=False,
        ),
    )
    print('  ✓ All 7 provider base models and 1 custom preset model marked as is_active=False in DB')

    # 4. Standard chat endpoint check: /api/models (include_inactive=False)
    print('\n[TEST 4] Standard chat endpoint GET /api/models (include_inactive=False)')
    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=False, user=admin_user)
            active_ids = [m['id'] for m in res['data']]
            assert len(active_ids) == 0, f'Expected 0 active models for chat, got {len(active_ids)}: {active_ids}'
            # Verify app.state.MODELS is also empty
            assert len(mock_request.app.state.MODELS) == 0, 'request.app.state.MODELS must not contain inactive models'
            print('  ✓ Normal chat endpoint correctly hides all disabled models (returned 0 models)')
            print('  ✓ request.app.state.MODELS has 0 inactive models')

    # 5. Admin endpoint check: /api/models?include_inactive=true
    print('\n[TEST 5] Admin model management GET /api/models?include_inactive=true')
    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=True, user=admin_user)
            all_ids = [m['id'] for m in res['data']]
            assert len(all_ids) == 8, f'Expected 8 models for Admin, got {len(all_ids)}: {all_ids}'
            for m in res['data']:
                assert m.get('is_active') is False, f'Model {m["id"]} should have is_active=False'
            print(f'  ✓ Admin endpoint returned all {len(all_ids)} models with is_active=False:')
            for m in res['data']:
                print(f'     - {m["id"]}: is_active={m["is_active"]}, preset={m.get("preset", False)}')

    # 6. Non-admin security check: non-admin requesting include_inactive=True
    print('\n[TEST 6] Non-admin security: regular user requesting include_inactive=True')
    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=True, user=regular_user)
            user_ids = [m['id'] for m in res['data']]
            assert len(user_ids) == 0, f'Non-admin should not receive inactive models! Got: {user_ids}'
            print('  ✓ Non-admin request correctly forced include_inactive=False (returned 0 models)')

    # 7. Enable All Models action
    print("\n[TEST 7] Simulating 'Enable All Models' from Admin -> Models")
    for m in provider_models:
        await Models.update_model_by_id(
            m['id'],
            ModelForm(
                id=m['id'],
                name=m['name'],
                base_model_id=None,
                meta=ModelMeta(),
                params=ModelParams(),
                is_active=True,
            ),
        )
    await Models.update_model_by_id(
        'wallfire-mcp',
        ModelForm(
            id='wallfire-mcp',
            name='Wallfire MCP',
            base_model_id='nvidia/nemotron-4-340b-instruct',
            meta=ModelMeta(),
            params=ModelParams(),
            is_active=True,
        ),
    )

    with patch(
        'open_webui.utils.models.get_all_base_models', new=AsyncMock(return_value=[m.copy() for m in provider_models])
    ):
        with patch('open_webui.utils.models.Config.get_many', new=AsyncMock(return_value={})):
            res = await get_models(mock_request, refresh=True, include_inactive=False, user=admin_user)
            restored_ids = [m['id'] for m in res['data']]
            assert len(restored_ids) == 8
            assert len(mock_request.app.state.MODELS) == 8
            print(f'  ✓ Successfully restored all {len(restored_ids)} models to chat endpoint and app.state.MODELS')

    print('\n=================================================================')
    print('ALL REGRESSION TESTS PASSED SUCCESSFULLY! ✓')
    print('=================================================================')


if __name__ == '__main__':
    asyncio.run(run_tests())
