from __future__ import annotations

import logging
import shutil
from pathlib import Path


def sync_frontend_static(static_dir: Path, frontend_build_dir: Path) -> None:
    """Replace packaged static files with the frontend build's static assets.

    Wipe and copy share the same precondition: a frontend `static/` directory
    must exist. A source checkout without a production build therefore keeps
    the tracked files under ``static_dir`` instead of deleting them.
    """
    frontend_static = frontend_build_dir / 'static'
    if not frontend_static.is_dir():
        return

    try:
        if static_dir.exists():
            for item in static_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    try:
                        item.unlink()
                    except Exception as e:
                        pass
    except Exception as e:
        pass

    for file_path in frontend_static.glob('**/*'):
        if file_path.is_file():
            target_path = static_dir / file_path.relative_to(frontend_static)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(file_path, target_path)
            except Exception as e:
                logging.error(f'An error occurred: {e}')
