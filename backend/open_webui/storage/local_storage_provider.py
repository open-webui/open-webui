import os
import shutil

from contextlib import contextmanager
from open_webui.constants import ERROR_MESSAGES
from open_webui.storage.base_storage_provider import StorageProvider
from pathlib import Path
from typing import BinaryIO, Iterator, Tuple

class LocalStorageProvider(StorageProvider):
    def __init__(self, storage_home: str):
        self.storage_home: str = storage_home

    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the local file system."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        file_path = Path(self.storage_home) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(contents)
        return contents, file_path.as_posix()

    def get_file(self, file_path: str) -> Iterator[bytes]:
        chunk_size = 8 * 1024
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    @contextmanager
    def as_local_file(self, file_path: str) -> Iterator[str]:
        yield file_path
    
    def delete_file(self, filename: str) -> None:
        """Deletes a file from the local file system."""
        file_path = f"{self.storage_home}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            print(f"File {file_path} not found in local storage.")

    def delete_all_files(self, folder) -> None:
        """Deletes all files from the storage."""
        folder_to_delete = f"{self.storage_home}/{folder}"
        if os.path.exists(folder_to_delete):
            for filename in os.listdir(folder_to_delete):
                file_path = os.path.join(folder_to_delete, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"Directory {folder_to_delete} not found in local storage.")
