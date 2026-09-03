import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('WEBUI_SECRET_KEY', 'unit-test-secret-key-not-used-for-auth')

# Importing open_webui.config prepares STATIC_DIR. Keep that side effect out of
# the checkout while collecting backend tests.
_scratch = Path(tempfile.mkdtemp(prefix='open-webui-tests-'))
atexit.register(shutil.rmtree, _scratch, True)
os.environ.setdefault('DATA_DIR', str(_scratch / 'data'))
os.environ.setdefault('STATIC_DIR', str(_scratch / 'static'))
os.environ.setdefault('FRONTEND_BUILD_DIR', str(_scratch / 'frontend-build'))
os.environ.setdefault('ENABLE_DB_MIGRATIONS', 'false')
(_scratch / 'data').mkdir(parents=True)
(_scratch / 'static').mkdir(parents=True)
