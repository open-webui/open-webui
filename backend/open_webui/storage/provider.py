import abc
from contextlib import AbstractContextManager
import os
import boto3
from botocore.exceptions import ClientError
import shutil


from typing import BinaryIO, Iterator, Tuple, Optional, Union

from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    S3_BUCKET_PREFIX,
    S3_LOCAL_CACHE_DIR,
    STORAGE_PROVIDER,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
    UPLOAD_DIR,
)
from mypy_boto3_s3.client import S3Client
from smart_open import open
import boto3
from typing import BinaryIO, Tuple, Optional

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
        print(f"Remove local cached file: {self.local_path}")
        os.remove(self.local_path)
        pass
    
class LocalFile(StorageFile):
    def __init__(self, local_path: str) -> None:
        super().__init__(local_path)

class StorageProvider(abc.ABC):
    @abc.abstractmethod
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the storage and returns the file content bytes and path."""

    @abc.abstractmethod
    def get_file(self, file_path: str) -> Iterator[bytes]:
        """Downloads file content"""

    @abc.abstractmethod
    def as_local_file(self, file_path: str) -> StorageFile:
        """Downloads a file from S3 and returns the file path."""

    @abc.abstractmethod
    def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""

    @abc.abstractmethod
    def delete_all_files(self) -> None:
        """Deletes all files from the storage."""

class S3StorageProvider(StorageProvider):
    def __init__(self):
        self.s3_client: S3Client = boto3.client(
            "s3",
            region_name=S3_REGION_NAME,
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )
        self.bucket_name: Optional[str] = S3_BUCKET_NAME
        self.bucket_prefix: Optional[str] = S3_BUCKET_PREFIX

    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to S3."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=f"{self.bucket_prefix}/{filename}", Body=contents)
            return contents, f"s3://{self.bucket_name}/{self.bucket_prefix}/{filename}"
        except Exception as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def get_file(self, file_path: str) -> Iterator[bytes]:
        """Downloads a file from S3 and returns the local file path."""
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            # local_file_path = f"{S3_LOCAL_CACHE_DIR}/{key}"
            # os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return response.get("Body").iter_chunks()
        except Exception as e:
            raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")
        
    def as_local_file(self, file_path: str) -> LocalCachedFile:
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            local_file_path = f"{S3_LOCAL_CACHE_DIR}/{key}"
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            self.s3_client.download_file(bucket_name, key, local_file_path)
            return LocalCachedFile(local_file_path)
        except Exception as e:
            raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")

    def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=filename)
        except Exception as e:
            raise RuntimeError(f"Error deleting file {filename} from S3: {e}")

    def delete_all_files(self) -> None:
        """Deletes all files from S3."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.bucket_prefix)
            if "Contents" in response:
                for content in response["Contents"]:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")

class LocalStorageProvider(StorageProvider):
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the local file system."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        file_path = f"{UPLOAD_DIR}/{filename}"
        with open(file_path, "wb") as f:
            f.write(contents)
        return contents, file_path

    def get_file(self, file_path: str) -> Iterator[bytes]:
        chunk_size = 8 * 1024
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def as_local_file(self, file_path: str) -> LocalFile:
        return LocalFile(file_path)
    
    def delete_file(self, filename: str) -> None:
        """Deletes a file from the local file system."""
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            print(f"File {file_path} not found in local storage.")

    def delete_all_files(self) -> None:
        """Deletes all files from the storage."""
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"Directory {UPLOAD_DIR} not found in local storage.")

class LocalStorageProvider(StorageProvider):
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to the local file system."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        file_path = f"{UPLOAD_DIR}/{filename}"
        with open(file_path, "wb") as f:
            f.write(contents)
        return contents, file_path

    def get_file(self, file_path: str) -> Iterator[bytes]:
        chunk_size = 8 * 1024
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def as_local_file(self, file_path: str) -> str:
        return ""
    
    def delete_file(self, filename: str) -> None:
        """Deletes a file from the local file system."""
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            print(f"File {file_path} not found in local storage.")

    def delete_all_files(self) -> None:
        """Deletes all files from the storage."""
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"Directory {UPLOAD_DIR} not found in local storage.")

def get_storage_provider() -> StorageProvider:
    if STORAGE_PROVIDER == "s3":
        return S3StorageProvider()
    elif STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    else:
        raise ValueError(ERROR_MESSAGES.INVALID_STORAGE_PROVIDER)
    
Storage = get_storage_provider()
