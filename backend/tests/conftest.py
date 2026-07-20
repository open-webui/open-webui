"""Shared pytest configuration for backend tests."""

from __future__ import annotations

import os

# open_webui.env requires WEBUI_SECRET_KEY when WEBUI_AUTH is enabled (default).
# Set a stable test-only value before any test module imports application code.
os.environ.setdefault(
    'WEBUI_SECRET_KEY',
    'test-webui-secret-key-for-pytest-only-not-for-production-use',
)

# Unit tests inject AsyncSession via get_async_db_context(db=...); without this flag
# the helper opens the process default DB and ignores the injected session.
os.environ['DATABASE_ENABLE_SESSION_SHARING'] = 'true'
