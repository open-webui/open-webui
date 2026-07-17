from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.utils.system_prompt import resolve_model_system_prompt


def _make_model(system: str | None = None):
    params_data = {'system': system} if system is not None else {}
    return SimpleNamespace(params=SimpleNamespace(model_dump=lambda: params_data))


@pytest.mark.asyncio
async def test_bypass_returns_empty():
    model = _make_model('You are helpful.')

    result = await resolve_model_system_prompt(model, {}, None, bypass=True)

    assert result == ''


@pytest.mark.asyncio
async def test_model_info_none_returns_empty():
    result = await resolve_model_system_prompt(None, {}, None, bypass=False)

    assert result == ''


@pytest.mark.asyncio
async def test_params_system_resolves_templated_string():
    model = _make_model('Hello {{name}}')
    metadata = {'variables': {'{{name}}': 'World'}}

    with patch(
        'open_webui.utils.system_prompt.resolve_system_prompt',
        new_callable=AsyncMock,
        return_value='Hello World',
    ) as mock_resolve:
        result = await resolve_model_system_prompt(model, metadata, None, bypass=False)

    assert result == 'Hello World'
    mock_resolve.assert_awaited_once_with('Hello {{name}}', metadata, None)


@pytest.mark.asyncio
async def test_params_system_end_to_end_with_metadata_variables():
    model = _make_model('Answer as {{role}}')

    result = await resolve_model_system_prompt(
        model,
        {'variables': {'{{role}}': 'an expert'}},
        None,
        bypass=False,
    )

    assert result == 'Answer as an expert'
