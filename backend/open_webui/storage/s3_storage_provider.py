import boto3

from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from fastapi import HTTPException, status
from typing import BinaryIO, Iterator, Tuple, Optional
from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
)
from open_webui.storage.base_storage_provider import StorageProvider

class S3StorageProvider(StorageProvider):
    def __init__(self, bucket_name: str, prefix: str):
        self.client = boto3.client(
            "s3",
            region_name=S3_REGION_NAME,
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )
        self.bucket_name: Optional[str] = bucket_name
        self.bucket_prefix: Optional[str] = prefix

    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Uploads a file to S3."""
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

        try:
            self.client.put_object(Bucket=self.bucket_name, Key=f"{self.bucket_prefix}/{filename}", Body=contents)
            return contents, f"s3://{self.bucket_name}/{self.bucket_prefix}/{filename}"
        except Exception as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def get_file(self, file_path: str) -> Iterator[bytes]:
        """Downloads a file from S3 and returns the local file path."""
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            response = self.client.get_object(Bucket=bucket_name, Key=key)
            return response.get("Body").iter_chunks()
        except Exception as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            else:
                raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")
        
    @contextmanager
    def as_local_file(self, file_path: str) -> Iterator[str]:
        try:
            bucket_name, key = file_path.split("//")[1].split("/", 1)
            with NamedTemporaryFile() as f:
                self.client.download_file(bucket_name, key, f.name)
                yield f.name
        except Exception as e:
            raise RuntimeError(f"Error downloading file {file_path} from S3: {e}")

    def delete_file(self, filename: str) -> None:
        """Deletes a file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=filename)
        except Exception as e:
            raise RuntimeError(f"Error deleting file {filename} from S3: {e}")

    def delete_all_files(self, folder: str) -> None:
        """Deletes all files from S3."""
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=f"{self.bucket_prefix}/{folder}")
            for page in pages:
                if "Contents" in page:
                    objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                    self.client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={
                            'Objects': objects_to_delete,
                            'Quiet': True
                        }
                    )
        except Exception as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")
