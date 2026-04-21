"""
Pytest hooks for WebUI integration tests.

Must set DATABASE_URL before any ``open_webui.internal.db`` import (via test module collection).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure ``import test.util.*`` resolves (``test`` package lives next to ``open_webui``).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def pytest_configure(config):
    if os.environ.get('OPEN_WEBUI_TEST_SKIP_DB_ISOLATION'):
        return
    # Avoid ``import chromadb`` in config.py (optional runtime dep).
    os.environ['VECTOR_DB'] = os.environ.get('VECTOR_DB', 'test')
    # Router tests (api key / permissions) read these at ``open_webui.config`` import time.
    os.environ.setdefault('ENABLE_API_KEYS', 'true')
    os.environ.setdefault('USER_PERMISSIONS_FEATURES_API_KEYS', 'true')
    os.environ.setdefault('USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS', 'true')
    fd, path = tempfile.mkstemp(prefix='owui_pytest_', suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = f'sqlite:///{path}'
    config._open_webui_test_db_path = path  # noqa: SLF001 — test session artifact


def pytest_sessionfinish(session, exitstatus):
    path = getattr(session.config, '_open_webui_test_db_path', None)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
