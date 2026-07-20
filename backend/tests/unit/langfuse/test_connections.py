import pytest
from open_webui.integrations.langfuse.connections import (
    get_connection_by_id,
    list_enabled_connections,
    merge_langfuse_connection_secrets,
    redact_langfuse_connections_for_response,
)


def test_langfuse_basic_auth_header():
    # Arrange
    from open_webui.integrations.langfuse.connections import langfuse_basic_auth_header

    # Act
    header = langfuse_basic_auth_header('pk-test', 'sk-test')
    # Assert
    assert header['Authorization'] == 'Basic cGstdGVzdDpzay10ZXN0'


def test_merge_langfuse_connection_secrets_preserves_existing():
    # Arrange
    existing = [{'id': 'a', 'secret_key': 'stored-secret'}]
    incoming = [{'id': 'a', 'name': 'Prod', 'secret_key': ''}]

    # Act
    merged = merge_langfuse_connection_secrets(incoming, existing)

    # Assert
    assert merged[0]['secret_key'] == 'stored-secret'
    assert merged[0]['name'] == 'Prod'


def test_merge_langfuse_connection_secrets_keeps_new_secret():
    # Arrange
    existing = [{'id': 'a', 'secret_key': 'stored-secret'}]
    incoming = [{'id': 'a', 'secret_key': 'new-secret'}]

    # Act
    merged = merge_langfuse_connection_secrets(incoming, existing)

    # Assert
    assert merged[0]['secret_key'] == 'new-secret'


def test_redact_langfuse_connections_for_response():
    # Arrange
    connections = [
        {'id': 'a', 'name': 'Prod', 'secret_key': 'hidden'},
        {'id': 'b', 'name': 'Empty', 'secret_key': ''},
    ]

    # Act
    redacted = redact_langfuse_connections_for_response(connections)

    # Assert
    assert redacted[0]['secret_key'] == ''
    assert redacted[0]['secret_key_set'] is True
    assert redacted[1]['secret_key_set'] is False


@pytest.mark.asyncio
async def test_get_connection_by_id(monkeypatch):
    # Arrange
    async def fake_get(_key):
        return [
            {'id': 'a', 'enabled': True},
            {'id': 'b', 'enabled': False},
        ]

    monkeypatch.setattr(
        'open_webui.integrations.langfuse.connections.Config.get',
        fake_get,
    )

    # Act
    found = await get_connection_by_id('a')
    missing = await get_connection_by_id('missing')

    # Assert
    assert found == {'id': 'a', 'enabled': True}
    assert missing is None


@pytest.mark.asyncio
async def test_list_enabled_connections(monkeypatch):
    # Arrange
    async def fake_get(_key):
        return [
            {'id': 'a', 'enabled': True},
            {'id': 'b', 'enabled': False},
            {'id': 'c'},
        ]

    monkeypatch.setattr(
        'open_webui.integrations.langfuse.connections.Config.get',
        fake_get,
    )

    # Act
    enabled = await list_enabled_connections()

    # Assert
    assert [item['id'] for item in enabled] == ['a', 'c']
