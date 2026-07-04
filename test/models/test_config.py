from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from open_webui.models import config as config_module
from open_webui.models.config import Config


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = {row.key: row for row in rows}

    async def get(self, model, key):
        return self.rows.get(key)

    async def execute(self, statement):
        return FakeResult(list(self.rows.values()))


@pytest.fixture(autouse=True)
def restore_config():
    defaults = dict(Config.DEFAULTS)
    persistent_enabled = Config.PERSISTENT_ENABLED
    oauth_persistent_enabled = Config.OAUTH_PERSISTENT_ENABLED
    yield
    Config.configure(
        defaults=defaults,
        enable_persistent=persistent_enabled,
        enable_oauth_persistent=oauth_persistent_enabled,
    )


def patch_db(monkeypatch, rows):
    @asynccontextmanager
    async def fake_get_async_db():
        yield FakeDB(rows)

    monkeypatch.setattr(config_module, 'get_async_db', fake_get_async_db)


def row(key, value):
    return SimpleNamespace(key=key, value=value)


@pytest.mark.asyncio
async def test_get_coerces_string_boolean_for_boolean_config(monkeypatch):
    Config.configure(
        defaults={
            'memories.system_context.enable': True,
            'ui.name': 'Open WebUI',
        },
        enable_persistent=True,
    )
    patch_db(
        monkeypatch,
        [
            row('memories.system_context.enable', 'false'),
            row('ui.name', 'false'),
            row('custom.flag', 'false'),
        ],
    )

    assert await Config.get('memories.system_context.enable') is False
    assert await Config.get('ui.name') == 'false'
    assert await Config.get('custom.flag', False) is False


@pytest.mark.asyncio
async def test_get_many_coerces_boolean_config_values(monkeypatch):
    Config.configure(
        defaults={
            'memories.system_context.enable': True,
            'auth.enable_api_keys': False,
            'ui.name': 'Open WebUI',
        },
        enable_persistent=True,
    )
    patch_db(
        monkeypatch,
        [
            row('memories.system_context.enable', 'false'),
            row('auth.enable_api_keys', 'true'),
            row('ui.name', 'false'),
        ],
    )

    values = await Config.get_many('memories.system_context.enable', 'auth.enable_api_keys', 'ui.name')

    assert values == {
        'memories.system_context.enable': False,
        'auth.enable_api_keys': True,
        'ui.name': 'false',
    }


@pytest.mark.asyncio
async def test_get_namespace_coerces_boolean_config_values(monkeypatch):
    Config.configure(
        defaults={
            'memories.system_context.enable': True,
            'memories.background_review.enable': False,
        },
        enable_persistent=True,
    )
    patch_db(
        monkeypatch,
        [
            row('memories.system_context.enable', 'false'),
            row('memories.background_review.enable', 'true'),
        ],
    )

    values = await Config.get_namespace('memories')

    assert values == {
        'memories.system_context.enable': False,
        'memories.background_review.enable': True,
    }


@pytest.mark.asyncio
async def test_get_all_coerces_boolean_config_values(monkeypatch):
    Config.configure(
        defaults={
            'ui.enable_signup': True,
            'ui.name': 'Open WebUI',
        },
        enable_persistent=True,
    )
    patch_db(
        monkeypatch,
        [
            row('ui.enable_signup', 'false'),
            row('ui.name', 'false'),
        ],
    )

    values = await Config.get_all()

    assert values['ui.enable_signup'] is False
    assert values['ui.name'] == 'false'
