"""
Pytest fixtures for the Open WebUI backend.

Environment variables are set before ``open_webui`` is imported so the test
process uses an isolated SQLite database under a temp directory.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='owui-pytest-')
os.environ.setdefault('USE_SLIM_DOCKER', 'true')
os.environ.setdefault('WEBUI_SECRET_KEY', 'owui-pytest-secret-key')
os.environ.setdefault('ENABLE_OPENAI_API', 'false')
os.environ.setdefault('OFFLINE_MODE', 'true')

# Import model modules so their tables are registered on Base.metadata.
import open_webui.models.access_grants  # noqa: E402,F401
import open_webui.models.channels  # noqa: E402,F401
import open_webui.models.chats  # noqa: E402,F401
import open_webui.models.config  # noqa: E402,F401
import open_webui.models.folders  # noqa: E402,F401
import open_webui.models.groups  # noqa: E402,F401
import open_webui.models.knowledge  # noqa: E402,F401
import open_webui.models.messages  # noqa: E402,F401
import open_webui.models.models  # noqa: E402,F401
import open_webui.models.notes  # noqa: E402,F401
import open_webui.models.prompts  # noqa: E402,F401
import open_webui.models.shared_chats  # noqa: E402,F401
import open_webui.models.skills  # noqa: E402,F401
import open_webui.models.tools  # noqa: E402,F401
import open_webui.models.users  # noqa: E402,F401
import pytest_asyncio  # noqa: E402
from open_webui.internal.db import Base, async_engine  # noqa: E402


@pytest_asyncio.fixture(scope='session', autouse=True)
async def _create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    yield
    async with async_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
