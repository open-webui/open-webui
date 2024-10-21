import os
import boto3
from botocore.exceptions import ClientError
from open_webui.config import (
    STORAGE_PROVIDER,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_REGION_NAME,
    S3_ENDPOINT_URL,
    UPLOAD_DIR,
    AppConfig,
)


class StorageProvider:
    def __init__(self):
        self.storage_provider = None
        self.client = None
        self.bucket_name = None

        if STORAGE_PROVIDER == "s3":
            self.storage_provider = "s3"
            self.client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            )
            self.bucket_name = S3_BUCKET_NAME
        else:
            self.storage_provider = "local"

    def get_storage_provider(self):
        return self.storage_provider

    def upload_file(self, file, filename):
        if self.storage_provider == "s3":
            try:
                bucket = self.bucket_name
                self.client.upload_fileobj(file, bucket, filename)
                return filename
            except ClientError as e:
                raise RuntimeError(f"Error uploading file: {e}")
        else:
            file_path = os.path.join(UPLOAD_DIR, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file.read())
            return filename

    def list_files(self):
        if self.storage_provider == "s3":
            try:
                bucket = self.bucket_name
                response = self.client.list_objects_v2(Bucket=bucket)
                if "Contents" in response:
                    return [content["Key"] for content in response["Contents"]]
                return []
            except ClientError as e:
                raise RuntimeError(f"Error listing files: {e}")
        else:
            return [
                f
                for f in os.listdir(UPLOAD_DIR)
                if os.path.isfile(os.path.join(UPLOAD_DIR, f))
            ]

    def get_file(self, filename):
        if self.storage_provider == "s3":
            try:
                bucket = self.bucket_name
                file_path = f"/tmp/{filename}"
                self.client.download_file(bucket, filename, file_path)
                return file_path
            except ClientError as e:
                raise RuntimeError(f"Error downloading file: {e}")
        else:
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                return file_path
            else:
                raise FileNotFoundError(f"File {filename} not found in local storage.")

    def delete_file(self, filename):
        if self.storage_provider == "s3":
            try:
                bucket = self.bucket_name
                self.client.delete_object(Bucket=bucket, Key=filename)
            except ClientError as e:
                raise RuntimeError(f"Error deleting file: {e}")
        else:
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                raise FileNotFoundError(f"File {filename} not found in local storage.")

    def delete_all_files(self):
        if self.storage_provider == "s3":
            try:
                bucket = self.bucket_name
                response = self.client.list_objects_v2(Bucket=bucket)
                if "Contents" in response:
                    for content in response["Contents"]:
                        self.client.delete_object(Bucket=bucket, Key=content["Key"])
            except ClientError as e:
                raise RuntimeError(f"Error deleting all files: {e}")
        else:
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)


Storage = StorageProvider()
