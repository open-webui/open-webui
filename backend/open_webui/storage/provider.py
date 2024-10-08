import os
import boto3
from botocore.exceptions import ClientError
import shutil


from typing import BinaryIO, Tuple, Optional, Union

from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    STORAGE_PROVIDER,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
    UPLOAD_DIR,
)


import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO, Tuple, Optional


class StorageProvider:
    def __init__(self, provider: Optional[str] = None):
        self.storage_provider: str = provider or STORAGE_PROVIDER

        self.s3_client = None
        self.s3_bucket_name: Optional[str] = None

        if self.storage_provider == "s3":
            self._initialize_s3()

    def _initialize_s3(self) -> None:
        """Initializes the S3 client and bucket name if using S3 storage."""
        self.s3_client = boto3.client(
            "s3",
            region_name=S3_REGION_NAME,
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )
        self.bucket_name = S3_BUCKET_NAME

    def _upload_to_s3(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Handles uploading of the file to S3 storage."""
        if not self.s3_client:
            raise RuntimeError("S3 Client is not initialized.")

        try:
            self.s3_client.upload_fileobj(file, self.bucket_name, filename)
            return file.read(), f"s3://{self.bucket_name}/{filename}"
        except ClientError as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def _upload_to_local(self, contents: bytes, filename: str) -> Tuple[bytes, str]:
        """Handles uploading of the file to local storage."""
        file_path = f"{UPLOAD_DIR}/{filename}"
        with open(file_path, "wb") as f:
            f.write(contents)
        return contents, file_path

    def _get_file_from_s3(self, file_path: str) -> str:
        """Handles downloading of the file from S3 storage."""
        if not self.s3_client:
            raise RuntimeError("S3 Client is not initialized.")

        try:
            bucket_name, key = file_path.split("//")[1].split("/")
            local_file_path = f"{UPLOAD_DIR}/{key}"
            self.s3_client.download_file(bucket_name, key, local_file_path)
            return local_file_path
        except ClientError as e:
            raise RuntimeError(f"Error downloading file from S3: {e}")

    def _get_file_from_local(self, file_path: str) -> str:
        """Handles downloading of the file from local storage."""
        return file_path

    def _delete_from_s3(self, filename: str) -> None:
        """Handles deletion of the file from S3 storage."""
        if not self.s3_client:
            raise RuntimeError("S3 Client is not initialized.")

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=filename)
        except ClientError as e:
            raise RuntimeError(f"Error deleting file from S3: {e}")

    def _delete_from_local(self, filename: str) -> None:
        """Handles deletion of the file from local storage."""
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            print(f"File {file_path} not found in local storage.")

    def _delete_all_from_s3(self) -> None:
        """Handles deletion of all files from S3 storage."""
        if not self.s3_client:
            raise RuntimeError("S3 Client is not initialized.")

        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if "Contents" in response:
                for content in response["Contents"]:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except ClientError as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")

    def _delete_all_from_local(self) -> None:
        """Handles deletion of all files from local storage."""
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

    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file either to S3 or the local file system."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        if self.storage_provider == "s3":
            return self._upload_to_s3(file, filename)
        return self._upload_to_local(contents, filename)

    def get_file(self, file_path: str) -> str:
        """Downloads a file either from S3 or the local file system and returns the file path."""
        if self.storage_provider == "s3":
            return self._get_file_from_s3(file_path)
        return self._get_file_from_local(file_path)

    def delete_file(self, filename: str) -> None:
        """Deletes a file either from S3 or the local file system."""
        if self.storage_provider == "s3":
            self._delete_from_s3(filename)

        # Always delete from local storage
        self._delete_from_local(filename)

    def delete_all_files(self) -> None:
        """Deletes all files from the storage."""
        if self.storage_provider == "s3":
            self._delete_all_from_s3()

        # Always delete from local storage
        self._delete_all_from_local()


Storage = StorageProvider(provider=STORAGE_PROVIDER)
