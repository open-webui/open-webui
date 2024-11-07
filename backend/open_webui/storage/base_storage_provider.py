from abc import abstractmethod, ABC
from typing import BinaryIO, ContextManager, Iterator, Tuple

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the storage and returns the file content bytes and path."""

    @abstractmethod
    def get_file(self, file_path: str) -> Iterator[bytes]:
        """Read the content of a file"""

    @abstractmethod
    def as_local_file(self, file_path: str) -> ContextManager[str]:
        """Get the local file path for a file. Download from remote if not using local fs, e.g. s3"""

    @abstractmethod
    def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""

    @abstractmethod
    def delete_all_files(self, folder: str) -> None:
        """Deletes all files from the storage."""
