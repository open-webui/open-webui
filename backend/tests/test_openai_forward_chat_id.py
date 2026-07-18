"""Tests for the ``ENABLE_FORWARD_CHAT_ID`` feature.

The forwarding logic lives in ``_inject_chat_id_as_user()`` in
``backend/open_webui/routers/openai.py``.  Because the flag is a module-level
constant imported from ``env.py``, tests toggle it via ``monkeypatch.setattr``
on the imported name rather than ``os.environ``.
"""

from __future__ import annotations

import pytest

import open_webui.routers.openai as openai_router

inject = openai_router._inject_chat_id_as_user


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_injects_chat_id_when_enabled_and_present():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    metadata = {"chat_id": "chat-abc-123"}

    inject(payload, metadata)
    assert payload["user"] == "chat-abc-123"


def test_injects_chat_id_when_payload_has_other_keys():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload = {"model": "gpt-4", "messages": []}
    metadata = {"chat_id": "chat-def-456"}

    inject(payload, metadata)
    assert payload["user"] == "chat-def-456"
    assert payload["model"] == "gpt-4"  # other keys preserved


# ---------------------------------------------------------------------------
# Feature flag off
# ---------------------------------------------------------------------------


def test_does_nothing_when_flag_off():
    openai_router.ENABLE_FORWARD_CHAT_ID = False

    payload: dict = {}
    metadata = {"chat_id": "chat-abc-123"}

    inject(payload, metadata)
    assert "user" not in payload


# ---------------------------------------------------------------------------
# Missing / empty metadata
# ---------------------------------------------------------------------------


def test_does_nothing_when_metadata_is_none():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    inject(payload, None)
    assert "user" not in payload


def test_does_nothing_when_metadata_lacks_chat_id():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    metadata = {"some_other_key": "value"}
    inject(payload, metadata)
    assert "user" not in payload


def test_does_nothing_when_chat_id_is_none():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    metadata = {"chat_id": None}
    inject(payload, metadata)
    assert "user" not in payload


def test_does_nothing_when_chat_id_is_empty_string():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    metadata = {"chat_id": ""}
    inject(payload, metadata)
    assert "user" not in payload


# ---------------------------------------------------------------------------
# Respect explicit caller-provided ``user``
# ---------------------------------------------------------------------------


def test_does_not_overwrite_existing_user():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload = {"user": "explicit-caller-id"}
    metadata = {"chat_id": "chat-ghi-789"}

    inject(payload, metadata)
    assert payload["user"] == "explicit-caller-id"


def test_does_not_overwrite_empty_user():
    """Even an empty string user is an explicit choice."""
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload = {"user": ""}
    metadata = {"chat_id": "chat-jkl-012"}

    inject(payload, metadata)
    assert payload["user"] == ""


# ---------------------------------------------------------------------------
# Idempotency — calling twice shouldn't change the result
# ---------------------------------------------------------------------------


def test_idempotent():
    openai_router.ENABLE_FORWARD_CHAT_ID = True

    payload: dict = {}
    metadata = {"chat_id": "chat-mno-345"}

    inject(payload, metadata)
    assert payload["user"] == "chat-mno-345"

    inject(payload, metadata)
    assert payload["user"] == "chat-mno-345"


if __name__ == "__main__":
    pytest.main([__file__])
