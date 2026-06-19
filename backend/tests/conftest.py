"""
Stub out open_webui modules that require a live database or heavy system
dependencies, so unit tests can import and exercise pure logic without a
running database or full dependency installation.

This file is loaded by pytest before any test collection begins.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _stub(name: str) -> ModuleType:
    """Register a fresh stub module under the given dotted name."""
    m = ModuleType(name)
    sys.modules[name] = m
    return m


# ── open_webui.models.users ───────────────────────────────────────────────────
users_mod = _stub("open_webui.models.users")
users_mod.Users = MagicMock()
users_mod.UserModel = MagicMock()

# ── open_webui.models.groups ──────────────────────────────────────────────────
groups_mod = _stub("open_webui.models.groups")
groups_mod.Groups = MagicMock()
groups_mod.GroupMember = MagicMock()
groups_mod.GroupUpdateForm = MagicMock()

# ── open_webui.models.chat_messages ──────────────────────────────────────────
chat_messages_mod = _stub("open_webui.models.chat_messages")
chat_messages_mod.ChatMessages = MagicMock()
