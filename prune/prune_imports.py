"""
Prune Imports Compatibility Layer

This module handles importing Open WebUI backend modules across different
installation scenarios:
1. pip package installation (open_webui.*)
2. Docker container (open_webui.*)
3. Git installation (backend/open_webui/*)

It tries multiple import strategies and exposes a consistent interface.
"""

import sys
import os
from pathlib import Path

# Determine the root directory
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"

# Try different import strategies
_import_strategy = None


def _try_pip_imports():
    """Try importing as if installed via pip (open_webui.*)"""
    try:
        from open_webui.models.users import Users
        return "pip"
    except ImportError:
        return None


def _try_git_imports():
    """Try importing from git structure (backend/open_webui/*)"""
    try:
        # Add repo root to path for git installation
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from backend.open_webui.models.users import Users
        return "git"
    except ImportError as e:
        # Check if it's a missing dependency vs missing backend structure
        if "backend" in str(e) or "No module named 'backend'" in str(e):
            return None  # backend structure doesn't exist
        else:
            # backend exists but dependencies missing
            _last_import_error = e
            return None


def _try_backend_path_imports():
    """Try adding backend/ to path and importing as open_webui.*"""
    try:
        # Add backend directory to path
        if str(BACKEND_DIR) not in sys.path:
            sys.path.insert(0, str(BACKEND_DIR))
        from open_webui.models.users import Users
        return "backend_path"
    except ImportError:
        return None


# Detect import strategy
_import_strategy = _try_pip_imports() or _try_git_imports() or _try_backend_path_imports()

if _import_strategy is None:
    # Check if backend directory exists to give better error message
    if BACKEND_DIR.exists() and (BACKEND_DIR / "open_webui").exists():
        error_msg = (
            "❌ Found backend directory but cannot import Open WebUI modules.\n"
            "   This usually means backend dependencies are not installed.\n"
            "\n"
            "✅ SOLUTION:\n"
            "   Install backend dependencies:\n"
            f"     cd {BACKEND_DIR.parent}\n"
            "     pip install -r backend/requirements.txt\n"
            "\n"
            "   Or activate your virtual environment first if you're using one:\n"
            "     source venv/bin/activate\n"
            "     pip install -r backend/requirements.txt\n"
        )
    else:
        error_msg = (
            "❌ Failed to import Open WebUI modules using any strategy.\n"
            "\n"
            "Tried:\n"
            "  1. pip package (open_webui.*)\n"
            "  2. git installation from repo root (backend.open_webui.*)\n"
            "  3. backend path in PYTHONPATH (open_webui.*)\n"
            "\n"
            "Make sure:\n"
            "  - You're in the correct directory\n"
            "  - Backend dependencies are installed\n"
            "  - For git install: run from repo root with backend/requirements.txt installed\n"
            "  - For pip install: open-webui package is installed\n"
            "  - For docker: script should run inside container\n"
        )
    raise ImportError(error_msg)


# Now import everything using the detected strategy
if _import_strategy == "pip" or _import_strategy == "backend_path":
    # Import from open_webui.* (pip or backend in path)
    from open_webui.models.users import Users
    from open_webui.models.chats import Chat, Chats, ChatFile
    from open_webui.models.messages import Message
    from open_webui.models.files import Files
    from open_webui.models.notes import Notes
    from open_webui.models.prompts import Prompts
    from open_webui.models.models import Models
    from open_webui.models.knowledge import Knowledges
    from open_webui.models.functions import Functions
    from open_webui.models.tools import Tools
    from open_webui.models.folders import Folder, Folders, FolderModel
    from open_webui.internal.db import get_db
    from open_webui.config import CACHE_DIR
    from open_webui.env import SRC_LOG_LEVELS

    try:
        from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT, VECTOR_DB
    except ImportError:
        VECTOR_DB_CLIENT = None
        VECTOR_DB = None

elif _import_strategy == "git":
    # Import from backend.open_webui.* (git installation)
    from backend.open_webui.models.users import Users
    from backend.open_webui.models.chats import Chat, Chats, ChatFile
    from backend.open_webui.models.messages import Message
    from backend.open_webui.models.files import Files
    from backend.open_webui.models.notes import Notes
    from backend.open_webui.models.prompts import Prompts
    from backend.open_webui.models.models import Models
    from backend.open_webui.models.knowledge import Knowledges
    from backend.open_webui.models.functions import Functions
    from backend.open_webui.models.tools import Tools
    from backend.open_webui.models.folders import Folder, Folders, FolderModel
    from backend.open_webui.internal.db import get_db
    from backend.open_webui.config import CACHE_DIR
    from backend.open_webui.env import SRC_LOG_LEVELS

    try:
        from backend.open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT, VECTOR_DB
    except ImportError:
        VECTOR_DB_CLIENT = None
        VECTOR_DB = None


# Export all for easy importing
__all__ = [
    'Users',
    'Chat',
    'Chats',
    'ChatFile',
    'Message',
    'Files',
    'Notes',
    'Prompts',
    'Models',
    'Knowledges',
    'Functions',
    'Tools',
    'Folder',
    'Folders',
    'FolderModel',
    'get_db',
    'CACHE_DIR',
    'SRC_LOG_LEVELS',
    'VECTOR_DB_CLIENT',
    'VECTOR_DB',
    '_import_strategy',
]


# Print debug info if running directly
if __name__ == "__main__":
    print(f"✓ Import strategy: {_import_strategy}")
    print(f"✓ REPO_ROOT: {REPO_ROOT}")
    print(f"✓ BACKEND_DIR: {BACKEND_DIR}")
    print(f"✓ Successfully imported Open WebUI modules")
    print(f"  - Users: {Users}")
    print(f"  - CACHE_DIR: {CACHE_DIR}")
    print(f"  - VECTOR_DB: {VECTOR_DB}")
