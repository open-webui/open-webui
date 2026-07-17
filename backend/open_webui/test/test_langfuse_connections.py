from open_webui.integrations.langfuse.connections import (
    langfuse_basic_auth_header,
    merge_langfuse_connection_secrets,
    redact_langfuse_connections_for_response,
)


def test_langfuse_basic_auth_header():
    header = langfuse_basic_auth_header('pk-test', 'sk-test')
    assert header['Authorization'] == 'Basic cGstdGVzdDpzay10ZXN0'


def test_merge_langfuse_connection_secrets_preserves_existing():
    existing = [{'id': 'a', 'secret_key': 'stored-secret'}]
    incoming = [{'id': 'a', 'name': 'Prod', 'secret_key': ''}]

    merged = merge_langfuse_connection_secrets(incoming, existing)

    assert merged[0]['secret_key'] == 'stored-secret'
    assert merged[0]['name'] == 'Prod'


def test_merge_langfuse_connection_secrets_keeps_new_secret():
    existing = [{'id': 'a', 'secret_key': 'stored-secret'}]
    incoming = [{'id': 'a', 'secret_key': 'new-secret'}]

    merged = merge_langfuse_connection_secrets(incoming, existing)

    assert merged[0]['secret_key'] == 'new-secret'


def test_redact_langfuse_connections_for_response():
    connections = [
        {'id': 'a', 'name': 'Prod', 'secret_key': 'hidden'},
        {'id': 'b', 'name': 'Empty', 'secret_key': ''},
    ]

    redacted = redact_langfuse_connections_for_response(connections)

    assert redacted[0]['secret_key'] == ''
    assert redacted[0]['secret_key_set'] is True
    assert redacted[1]['secret_key_set'] is False
