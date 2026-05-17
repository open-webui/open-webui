import os
import logging
from pathlib import Path
from typing import Optional

from .config import LOCAL_STORAGE_ENABLED, LOCAL_STORAGE_PATH

log = logging.getLogger(__name__)


class LocalStorage:
    def __init__(self, enabled: bool = LOCAL_STORAGE_ENABLED, base_path: str = LOCAL_STORAGE_PATH):
        self.enabled = enabled
        self.base_path = Path(base_path)

    def ensure_project_dir(self, project_id: str) -> Path:
        project_dir = self.base_path / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def save_file(self, project_id: str, file_path: str, content: str) -> Optional[Path]:
        if not self.enabled:
            return None
        try:
            dest = self.base_path / str(project_id) / file_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding='utf-8')
            log.debug(f'Saved file: {dest}')
            return dest
        except Exception as e:
            log.error(f'Failed to save file {file_path}: {e}')
            return None

    def file_exists(self, project_id: str, file_path: str) -> bool:
        if not self.enabled:
            return False
        return (self.base_path / str(project_id) / file_path).exists()

    def get_local_path(self, project_id: str, file_path: str) -> Optional[Path]:
        if not self.enabled:
            return None
        p = self.base_path / str(project_id) / file_path
        return p if p.exists() else None

    def get_project_size(self, project_id: str) -> int:
        project_dir = self.base_path / str(project_id)
        if not project_dir.exists():
            return 0
        total = 0
        for f in project_dir.rglob('*'):
            if f.is_file():
                total += f.stat().st_size
        return total

    def list_project_files(self, project_id: str) -> list[str]:
        project_dir = self.base_path / str(project_id)
        if not project_dir.exists():
            return []
        return [str(f.relative_to(project_dir)) for f in project_dir.rglob('*') if f.is_file()]

    def remove_project(self, project_id: str) -> None:
        project_dir = self.base_path / str(project_id)
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
            log.info(f'Removed local storage for project {project_id}')


local_storage = LocalStorage()
