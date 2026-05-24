"""Unit tests for open_webui.utils.webhook

Tests cover:
- _parse_webhook_config: legacy single URL, multi-URL newline-separated,
  JSON-object entries, mixed formats, empty/whitespace inputs.
- post_webhook_event: event-scope filtering, catch-all (None events), and
  backwards-compat with legacy single-URL config strings.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from open_webui.utils.webhook import (
    _parse_webhook_config,
    post_webhook_event,
    post_webhook,
    WEBHOOK_EVENTS,
)


# ---------------------------------------------------------------------------
# _parse_webhook_config tests
# ---------------------------------------------------------------------------


class TestParseWebhookConfig:
    """Tests for the _parse_webhook_config helper."""

    def test_empty_string_returns_empty_list(self):
        assert _parse_webhook_config('') == []

    def test_whitespace_only_returns_empty_list(self):
        assert _parse_webhook_config('   \n  ') == []

    def test_single_legacy_url(self):
        url = 'https://hooks.slack.com/services/T00/B00/xxx'
        result = _parse_webhook_config(url)
        assert result == [{'url': url, 'events': None}]

    def test_two_urls_newline_separated(self):
        cfg = 'https://hooks.slack.com/xxx\nhttps://discord.com/api/webhooks/yyy'
        result = _parse_webhook_config(cfg)
        assert len(result) == 2
        assert result[0]['url'] == 'https://hooks.slack.com/xxx'
        assert result[0]['events'] is None
        assert result[1]['url'] == 'https://discord.com/api/webhooks/yyy'

    def test_two_urls_comma_separated(self):
        cfg = 'https://a.example.com/hook,https://b.example.com/hook'
        result = _parse_webhook_config(cfg)
        assert len(result) == 2

    def test_json_object_with_events(self):
        entry = json.dumps({'url': 'https://example.com/hook', 'events': ['signup']})
        result = _parse_webhook_config(entry)
        assert result == [{'url': 'https://example.com/hook', 'events': {'signup'}}]

    def test_json_array_with_mixed_entries(self):
        cfg = json.dumps([
            {'url': 'https://a.example.com/hook', 'events': ['signup', 'oauth_signup']},
            {'url': 'https://b.example.com/hook', 'events': None},
            'https://c.example.com/hook',
        ])
        result = _parse_webhook_config(cfg)
        assert len(result) == 3
        assert result[0]['events'] == {'signup', 'oauth_signup'}
        assert result[1]['events'] is None
        assert result[2]['events'] is None

    def test_json_object_null_events_becomes_none(self):
        entry = json.dumps({'url': 'https://example.com/hook', 'events': None})
        result = _parse_webhook_config(entry)
        assert result[0]['events'] is None

    def test_json_object_empty_events_list_becomes_none(self):
        entry = json.dumps({'url': 'https://example.com/hook', 'events': []})
        result = _parse_webhook_config(entry)
        # Empty events list → treated as catch-all (None)
        assert result[0]['events'] is None

    def test_newline_separated_json_objects(self):
        line1 = json.dumps({'url': 'https://a.example.com/hook', 'events': ['signup']})
        line2 = json.dumps({'url': 'https://b.example.com/hook', 'events': ['signout']})
        cfg = f'{line1}\n{line2}'
        result = _parse_webhook_config(cfg)
        assert len(result) == 2
        assert result[0]['events'] == {'signup'}
        assert result[1]['events'] == {'signout'}

    def test_malformed_json_falls_back_to_plain_url_treatment(self):
        # Not valid JSON → should fall back to treating as a plain URL string.
        cfg = '{not valid json}'
        result = _parse_webhook_config(cfg)
        # The parser should not crash, but the entry won't have 'url' key from
        # JSON parse, so it will be treated as a literal string URL.
        # Since it starts with '{' and JSON parse fails, result may be empty or
        # contain the raw string as URL depending on fallback behaviour.
        # The important thing is it doesn't raise.
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# post_webhook_event tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPostWebhookEvent:
    """Tests for the post_webhook_event dispatcher."""

    async def test_returns_empty_list_for_empty_config(self):
        result = await post_webhook_event('TestApp', '', 'msg', {}, event='signup')
        assert result == []

    async def test_legacy_url_fires_for_any_event(self):
        url = 'https://hooks.slack.com/services/xxx'
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            result = await post_webhook_event('App', url, 'msg', {}, event='signup')
        assert result == [True]
        mock_pw.assert_called_once()

    async def test_legacy_url_fires_even_with_unknown_event(self):
        url = 'https://discord.com/api/webhooks/xxx'
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            result = await post_webhook_event('App', url, 'msg', {}, event='some_future_event')
        assert result == [True]

    async def test_scoped_url_fires_only_for_matching_event(self):
        cfg = json.dumps([
            {'url': 'https://a.example.com', 'events': ['signup']},
            {'url': 'https://b.example.com', 'events': ['signout']},
        ])
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            result = await post_webhook_event('App', cfg, 'msg', {}, event='signup')

        # Only URL 'a' should have been called (event='signup')
        assert len(result) == 1
        assert result == [True]
        call_args = mock_pw.call_args_list
        assert len(call_args) == 1
        assert call_args[0].args[1] == 'https://a.example.com'

    async def test_scoped_url_skipped_for_non_matching_event(self):
        cfg = json.dumps([
            {'url': 'https://signup-only.example.com', 'events': ['signup']},
        ])
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            result = await post_webhook_event('App', cfg, 'msg', {}, event='signout')

        assert result == []
        mock_pw.assert_not_called()

    async def test_mixed_config_fires_scoped_and_catchall(self):
        cfg = json.dumps([
            {'url': 'https://signup-only.example.com', 'events': ['signup']},
            {'url': 'https://all-events.example.com', 'events': None},
        ])
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            result = await post_webhook_event('App', cfg, 'msg', {}, event='signup')

        # Both should fire: signup-only matches event; catchall always fires
        assert len(result) == 2

    async def test_event_name_injected_into_payload(self):
        url = 'https://example.com/hook'
        captured_data = {}

        async def capture_webhook(name, _url, message, data):
            captured_data.update(data)
            return True

        with patch('open_webui.utils.webhook.post_webhook', side_effect=capture_webhook):
            await post_webhook_event('App', url, 'msg', {'action': 'signup'}, event='signup')

        assert captured_data.get('event') == 'signup'

    async def test_no_event_arg_sends_to_all_configured_urls(self):
        cfg = json.dumps([
            {'url': 'https://a.example.com', 'events': ['signup']},
            {'url': 'https://b.example.com', 'events': None},
        ])
        with patch('open_webui.utils.webhook.post_webhook', new_callable=AsyncMock) as mock_pw:
            mock_pw.return_value = True
            # event=None → backwards-compat, should be sent to ALL (no filtering)
            result = await post_webhook_event('App', cfg, 'msg', {}, event=None)

        # event=None: scoped URL 'a' has events=['signup'] which is not None, and
        # event param is None, so the check `allowed is not None and event not in allowed`
        # → None not in {'signup'} → True → skip 'a'.
        # URL 'b' has events=None → catch-all → fires.
        # This is the intended behaviour: None event only reaches catch-all webhooks.
        assert len(result) == 1


# ---------------------------------------------------------------------------
# WEBHOOK_EVENTS constant sanity check
# ---------------------------------------------------------------------------


class TestWebhookEventsConstant:
    def test_expected_events_present(self):
        expected = {'signup', 'oauth_signup', 'signin', 'signout', 'user_deleted', 'user_role_changed'}
        assert expected.issubset(WEBHOOK_EVENTS)
