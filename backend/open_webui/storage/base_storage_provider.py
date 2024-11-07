import abc
import os
from typing import AsyncIterator, BinaryIO, Tuple

from typing import BinaryIO, Tuple

class StorageFile(abc.ABC):
    local_path: str

    def __init__(self, local_path: str) -> None:
        self.local_path = local_path

    def get_local_path(self) -> str:
        return self.local_path

    def cleanup_local_file(self) -> None:
        pass

    def __enter__(self):
       return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup_local_file()


class LocalCachedFile(StorageFile):
    def __init__(self, local_path: str) -> None:
        super().__init__(local_path)

    def cleanup_local_file(self) -> None:
        os.remove(self.local_path)
        pass

class LocalFile(StorageFile):
    def __init__(self, local_path: str) -> None:
        super().__init__(local_path)

class StorageProvider(abc.ABC):
    @abc.abstractmethod
    async def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the storage and returns the file content bytes and path."""

    @abc.abstractmethod
    async def get_file(self, file_path: str) -> AsyncIterator[bytes]:
        """Downloads file content"""

    @abc.abstractmethod
    async def as_local_file(self, file_path: str) -> StorageFile:
        """Downloads a file from S3 and returns the file path."""

    @abc.abstractmethod
    async def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""

    @abc.abstractmethod
    async def delete_all_files(self) -> None:
        """Deletes all files from the storage."""
