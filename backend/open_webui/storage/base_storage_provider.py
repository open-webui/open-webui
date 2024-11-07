import abc
import os
from typing import BinaryIO, ContextManager, Iterator, Tuple

from typing import BinaryIO, Tuple

class StorageProvider(abc.ABC):
    @abc.abstractmethod
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the storage and returns the file content bytes and path."""

    @abc.abstractmethod
    def get_file(self, file_path: str) -> Iterator[bytes]:
        """Read the content of a file"""

    @abc.abstractmethod
    def as_local_file(self, file_path: str) -> ContextManager[str]:
        """Get the local file path for a file. Download from remote if not using local fs, e.g. s3"""

    @abc.abstractmethod
    def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""

    @abc.abstractmethod
    def delete_all_files(self, folder: str) -> None:
        """Deletes all files from the storage."""
