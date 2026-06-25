from types import SimpleNamespace

import pytest

from open_webui import events


class DummyRequest:
    def __init__(self):
        self.app = SimpleNamespace(state=SimpleNamespace(instance_id='instance-1', WEBUI_NAME='Test WebUI'))


@pytest.mark.asyncio
async def test_build_event_derives_resource_operation_and_sanitizes():
    request = DummyRequest()

    event = events.build_event(
        request,
        events.EVENTS.KNOWLEDGE_FILE_ADDED,
        actor={
            'id': 'user-1',
            'name': 'Ada',
            'email': 'ada@example.com',
            'role': 'admin',
            'api_key': 'secret',
        },
        subject_id='file-1',
        data={
            'safe': 'value',
            'token': 'hidden',
            'nested': {'refresh_token': 'hidden', 'name': 'visible'},
            'content': 'x' * (events.MAX_STRING_LENGTH + 10),
        },
    )

    payload = event.model_dump()

    assert payload['schema'] == events.EVENT_VERSION
    assert payload['event'] == 'knowledge.file.added'
    assert payload['resource'] == 'knowledge.file'
    assert payload['operation'] == 'added'
    assert payload['instance_id'] == 'instance-1'
    assert payload['actor'] == {
        'id': 'user-1',
        'name': 'Ada',
        'email': 'ada@example.com',
        'role': 'admin',
        'type': 'user',
    }
    assert 'token' not in payload['data']
    assert 'refresh_token' not in payload['data']['nested']
    assert payload['data']['nested']['name'] == 'visible'
    assert payload['data']['content'].endswith('...')


def test_build_event_accepts_events_enum():
    request = DummyRequest()

    event = events.build_event(
        request,
        events.EVENTS.MESSAGE_CREATED,
        actor={'id': 'user-1'},
        subject_id='message-1',
    )

    payload = event.model_dump()
    assert payload['event'] == 'message.created'
    assert payload['resource'] == 'message'
    assert payload['operation'] == 'created'
    assert events.EVENTS.MESSAGE_CREATED.value in events.EVENT_CATALOG


@pytest.mark.asyncio
async def test_webhook_sink_sends_canonical_json(monkeypatch):
    request = DummyRequest()
    sent = {}

    async def fake_config_get(key, default=None):
        assert key == 'webhook_url'
        return 'https://example.com/events'

    async def fake_post_webhook(name, url, message, event_data):
        sent.update({'name': name, 'url': url, 'message': message, 'event_data': event_data})
        return True

    monkeypatch.setattr(events.Config, 'get', fake_config_get)
    monkeypatch.setattr(events, 'post_webhook', fake_post_webhook)

    event = events.build_event(
        request,
        events.EVENTS.USER_CREATED,
        actor={'id': 'admin-1', 'name': 'Admin', 'role': 'admin'},
        subject_id='user-1',
    )

    await events.WebhookEventSink().handle_event(request.app, event)

    assert sent['name'] == 'Test WebUI'
    assert sent['url'] == 'https://example.com/events'
    assert sent['event_data'] == event.model_dump()
    assert sent['event_data']['event'] == 'user.created'


@pytest.mark.asyncio
async def test_publish_event_swallows_sink_failure(monkeypatch):
    request = DummyRequest()

    class FailingSink:
        async def handle_event(self, app, event):
            raise RuntimeError('boom')

    monkeypatch.setattr(events, 'EVENT_SINKS', [FailingSink()])

    await events.publish_event(
        request,
        events.EVENTS.USER_CREATED,
        actor={'id': 'admin-1'},
        subject_id='user-1',
    )
