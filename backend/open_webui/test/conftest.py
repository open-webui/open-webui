import os
import sys
import tempfile
from pathlib import Path

# Ensure `open_webui` and `test` packages are importable when running pytest from repo root or backend/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Isolated data directory and database for tests (before open_webui.config is imported)
_TEST_DATA_DIR = tempfile.mkdtemp(prefix='open-webui-test-')
os.environ.setdefault('DATA_DIR', _TEST_DATA_DIR)
os.environ.setdefault('DATABASE_URL', f'sqlite:///{_TEST_DATA_DIR}/test.db')
os.environ.setdefault('ENABLE_PERSISTENT_CONFIG', 'False')
