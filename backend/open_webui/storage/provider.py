import os
import shutil
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple, Dict

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from open_webui.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_KEY_PREFIX,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
    S3_ENABLE_TAGGING,
    GCS_BUCKET_NAME,
    GOOGLE_APPLICATION_CREDENTIALS_JSON,
    AZURE_STORAGE_ENDPOINT,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_KEY,
    STORAGE_PROVIDER,
    UPLOAD_DIR,
)
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
from open_webui.constants import ERROR_MESSAGES
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

log = logging.getLogger(__name__)


class StorageProvider(ABC):
    @abstractmethod
    def get_file(self, file_path: str) -> str:
        pass

    @abstractmethod
    def upload_file(self, file: BinaryIO, filename: str, tags: Dict[str, str]) -> Tuple[bytes, str]:
        pass

    @abstractmethod
    def delete_all_files(self) -> None:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        pass

    def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a time-limited signed URL for direct browser access (streaming).

        This enables HTTP Range Request streaming for video/audio without backend proxying.
        Default implementation falls back to local file path.

        Args:
            file_path: Cloud storage path (e.g., "gs://bucket/file.mp4")
            expiration: URL validity in seconds (default: 1 hour)

        Returns:
            Signed URL for direct browser access (supports Range Requests)
        """
        # Default: return local file path (for local storage provider)
        return self.get_file(file_path)


class LocalStorageProvider(StorageProvider):
    @staticmethod
    def upload_file(file: BinaryIO, filename: str, tags: Dict[str, str]) -> Tuple[bytes, str]:
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, 'wb') as f:
            f.write(contents)
        return contents, file_path

    @staticmethod
    def get_file(file_path: str) -> str:
        """Handles downloading of the file from local storage."""
        return file_path

    @staticmethod
    def delete_file(file_path: str) -> None:
        """Handles deletion of the file from local storage."""
        filename = os.path.basename(file_path)
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            log.warning(f'File {file_path} not found in local storage.')

    @staticmethod
    def delete_all_files() -> None:
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
                    log.exception(f'Failed to delete {file_path}. Reason: {e}')
        else:
            log.warning(f'Directory {UPLOAD_DIR} not found in local storage.')

    @staticmethod
    def get_signed_url(file_path: str, expiration: int = 3600) -> str:
        """For local storage there is no signed URL — the backend serves the
        file directly via FileResponse, so we just return the path."""
        return file_path


class S3StorageProvider(StorageProvider):
    def __init__(self):
        config = Config(
            s3={
                'use_accelerate_endpoint': S3_USE_ACCELERATE_ENDPOINT,
                'addressing_style': S3_ADDRESSING_STYLE,
            },
            # KIT change - see https://github.com/boto/boto3/issues/4400#issuecomment-2600742103∆
            request_checksum_calculation='when_required',
            response_checksum_validation='when_required',
        )

        # If access key and secret are provided, use them for authentication
        if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
                config=config,
            )
        else:
            # If no explicit credentials are provided, fall back to default AWS credentials
            # This supports workload identity (IAM roles for EC2, EKS, etc.)
            self.s3_client = boto3.client(
                's3',
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                config=config,
            )

        self.bucket_name = S3_BUCKET_NAME
        self.key_prefix = S3_KEY_PREFIX if S3_KEY_PREFIX else ''

    @staticmethod
    def sanitize_tag_value(s: str) -> str:
        """Only include S3 allowed characters."""
        return re.sub(r'[^a-zA-Z0-9 äöüÄÖÜß\+\-=\._:/@]', '', s)

    def upload_file(self, file: BinaryIO, filename: str, tags: Dict[str, str]) -> Tuple[bytes, str]:
        """Handles uploading of the file to S3 storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        s3_key = os.path.join(self.key_prefix, filename)
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            if S3_ENABLE_TAGGING and tags:
                sanitized_tags = {self.sanitize_tag_value(k): self.sanitize_tag_value(v) for k, v in tags.items()}
                tagging = {'TagSet': [{'Key': k, 'Value': v} for k, v in sanitized_tags.items()]}
                self.s3_client.put_object_tagging(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Tagging=tagging,
                )
            return (
                contents,
                f's3://{self.bucket_name}/{s3_key}',
            )
        except ClientError as e:
            raise RuntimeError(f'Error uploading file to S3: {e}')

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from S3 storage with local caching."""
        try:
            s3_key = self._extract_s3_key(file_path)
            local_file_path = self._get_local_file_path(s3_key)

            # **PERFORMANCE OPTIMIZATION**: Check if file already exists locally
            # This prevents re-downloading large video/audio files for every segment request
            if os.path.exists(local_file_path) and os.path.getsize(local_file_path) > 0:
                log.debug(f"Using cached local copy of {s3_key} (avoiding S3 download)")
                return local_file_path

            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            log.info(f"Successfully downloaded {s3_key} from S3")
            return local_file_path
        except ClientError as e:
            raise RuntimeError(f'Error downloading file from S3: {e}')

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except ClientError as e:
            raise RuntimeError(f'Error deleting file from S3: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from S3 storage."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in response:
                for content in response['Contents']:
                    # Skip objects that were not uploaded from open-webui in the first place
                    if not content['Key'].startswith(self.key_prefix):
                        continue

                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=content['Key'])
        except ClientError as e:
            raise RuntimeError(f'Error deleting all files from S3: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for direct browser streaming from S3.

        Enables HTTP Range Request support for video/audio playback without backend proxying.

        Args:
            file_path: S3 file path (e.g., "s3://bucket/prefix/file.mp4")
            expiration: URL validity in seconds (default: 1 hour)

        Returns:
            Time-limited presigned URL with Range Request support
        """
        try:
            s3_key = self._extract_s3_key(file_path)

            # Generate presigned URL that supports HTTP Range Requests
            # This allows browser to seek in video/audio and stream efficiently
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': self.bucket_name, 'Key': s3_key}, ExpiresIn=expiration
            )

            log.debug(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return presigned_url

        except ClientError as e:
            log.warning(f"Failed to generate presigned URL for {file_path}: {e}")
            # Fallback to downloading file locally
            return self.get_file(file_path)

    # The s3 key is the name assigned to an object. It excludes the bucket name, but includes the internal path and the file name.
    def _extract_s3_key(self, full_file_path: str) -> str:
        return '/'.join(full_file_path.split('//')[1].split('/')[1:])

    def _get_local_file_path(self, s3_key: str) -> str:
        return os.path.join(UPLOAD_DIR, s3_key.split('/')[-1])


class GCSStorageProvider(StorageProvider):
    def __init__(self):
        self.bucket_name = GCS_BUCKET_NAME

        if GOOGLE_APPLICATION_CREDENTIALS_JSON:
            self.gcs_client = storage.Client.from_service_account_info(
                info=json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
            )
        else:
            # if no credentials json is provided, credentials will be picked up from the environment
            # if running on local environment, credentials would be user credentials
            # if running on a Compute Engine instance, credentials would be from Google Metadata server
            self.gcs_client = storage.Client()
        self.bucket = self.gcs_client.bucket(GCS_BUCKET_NAME)

    def upload_file(self, file: BinaryIO, filename: str, tags: Dict[str, str]) -> Tuple[bytes, str]:
        """Handles uploading of the file to GCS storage with retry logic."""
        import time
        from requests.exceptions import ConnectionError, Timeout
        from open_webui.config import (
            GCS_UPLOAD_TIMEOUT_SECONDS,
            GCS_MAX_RETRY_ATTEMPTS,
            GCS_RETRY_BASE_DELAY_SECONDS,
        )

        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)

        max_retries = GCS_MAX_RETRY_ATTEMPTS
        base_delay = GCS_RETRY_BASE_DELAY_SECONDS
        upload_timeout = GCS_UPLOAD_TIMEOUT_SECONDS

        for attempt in range(max_retries):
            try:
                blob = self.bucket.blob(filename)
                blob.upload_from_filename(file_path, timeout=upload_timeout)

                log.info(f'Successfully uploaded {filename} to GCS')
                return contents, 'gs://' + self.bucket_name + '/' + filename

            except (ConnectionError, Timeout, Exception) as e:
                is_retryable = (
                    isinstance(e, (ConnectionError, Timeout))
                    or 'RemoteDisconnected' in str(e)
                    or 'Connection aborted' in str(e)
                    or 'timed out' in str(e).lower()
                )

                if is_retryable and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + (time.time() % 1)
                    log.warning(
                        f'GCS upload attempt {attempt + 1}/{max_retries} failed for {filename}: {e}. '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)
                    continue
                else:
                    if isinstance(e, GoogleCloudError):
                        raise RuntimeError(f'Error uploading file to GCS: {e}')
                    else:
                        raise RuntimeError(f'Error uploading file to GCS after {max_retries} attempts: {e}')

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from GCS storage with retry logic and local caching."""
        import time
        from requests.exceptions import ConnectionError, Timeout
        from open_webui.config import (
            GCS_DOWNLOAD_TIMEOUT_SECONDS,
            GCS_MAX_RETRY_ATTEMPTS,
            GCS_RETRY_BASE_DELAY_SECONDS,
        )

        filename = file_path.removeprefix('gs://').split('/')[1]
        local_file_path = os.path.join(UPLOAD_DIR, filename)

        # Performance: skip re-downloading if a usable local copy already exists.
        # Critical for serving video/audio segment requests cheaply.
        if os.path.exists(local_file_path) and os.path.getsize(local_file_path) > 0:
            log.debug(f'Using cached local copy of {filename} (avoiding GCS download)')
            return local_file_path

        # Get configurable retry settings
        max_retries = GCS_MAX_RETRY_ATTEMPTS
        base_delay = GCS_RETRY_BASE_DELAY_SECONDS
        download_timeout = GCS_DOWNLOAD_TIMEOUT_SECONDS

        for attempt in range(max_retries):
            try:
                blob = self.bucket.get_blob(filename)
                if not blob:
                    raise RuntimeError(f"File not found in GCS: {filename}")

                # Set timeout for download (configurable, default 5 minutes)
                blob.download_to_filename(local_file_path, timeout=download_timeout)
                log.info(f"Successfully downloaded {filename} from GCS")
                return local_file_path

            except NotFound as e:
                # File doesn't exist - don't retry
                raise RuntimeError(f"File not found in GCS: {filename}")

            except (ConnectionError, Timeout, Exception) as e:
                is_retryable = (
                    isinstance(e, (ConnectionError, Timeout))
                    or "RemoteDisconnected" in str(e)
                    or "Connection aborted" in str(e)
                    or "timed out" in str(e).lower()
                )

                if is_retryable and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + (time.time() % 1)
                    log.warning(
                        f"GCS download attempt {attempt + 1}/{max_retries} failed for {filename}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Error downloading file from GCS after {max_retries} attempts: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from GCS storage with retry logic."""
        import time
        from requests.exceptions import ConnectionError, Timeout
        from open_webui.config import (
            GCS_MAX_RETRY_ATTEMPTS,
            GCS_RETRY_BASE_DELAY_SECONDS,
        )

        filename = file_path.removeprefix("gs://").split("/")[1]

        # Get configurable retry settings
        max_retries = GCS_MAX_RETRY_ATTEMPTS
        base_delay = GCS_RETRY_BASE_DELAY_SECONDS

        for attempt in range(max_retries):
            try:
                blob = self.bucket.get_blob(filename)
                if blob:
                    blob.delete(timeout=60)
                    log.info(f"Successfully deleted {filename} from GCS")
                else:
                    log.warning(f"File not found in GCS (already deleted?): {filename}")
                break  # Success or file doesn't exist - exit retry loop

            except NotFound:
                # File doesn't exist - not an error
                log.info(f"File not found in GCS (already deleted): {filename}")
                break

            except (ConnectionError, Timeout, Exception) as e:
                is_retryable = (
                    isinstance(e, (ConnectionError, Timeout))
                    or "RemoteDisconnected" in str(e)
                    or "Connection aborted" in str(e)
                    or "timed out" in str(e).lower()
                )

                if is_retryable and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt) + (time.time() % 1)
                    log.warning(
                        f'GCS delete attempt {attempt + 1}/{max_retries} failed for {filename}: {e}. '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f'Error deleting file from GCS after {max_retries} attempts: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from GCS storage."""
        try:
            blobs = self.bucket.list_blobs()

            for blob in blobs:
                blob.delete()

        except NotFound as e:
            raise RuntimeError(f'Error deleting all files from GCS: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a signed URL for direct browser streaming from GCS.

        Enables HTTP Range Request support for video/audio playback without backend proxying.

        Args:
            file_path: GCS file path (e.g., "gs://bucket/file.mp4")
            expiration: URL validity in seconds (default: 1 hour)

        Returns:
            Time-limited signed URL with Range Request support
        """
        try:
            from datetime import timedelta

            filename = file_path.removeprefix("gs://").split("/")[1]
            blob = self.bucket.blob(filename)

            # Generate signed URL that supports HTTP Range Requests
            # This allows browser to seek in video/audio and stream efficiently
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET",
            )

            log.debug(f"Generated signed URL for {filename} (expires in {expiration}s)")
            return signed_url

        except Exception as e:
            log.warning(f"Failed to generate signed URL for {file_path}: {e}")
            # Fallback to downloading file locally
            return self.get_file(file_path)


class AzureStorageProvider(StorageProvider):
    def __init__(self):
        self.endpoint = AZURE_STORAGE_ENDPOINT
        self.container_name = AZURE_STORAGE_CONTAINER_NAME
        storage_key = AZURE_STORAGE_KEY

        if storage_key:
            # Configure using the Azure Storage Account Endpoint and Key
            self.blob_service_client = BlobServiceClient(account_url=self.endpoint, credential=storage_key)
        else:
            # Configure using the Azure Storage Account Endpoint and DefaultAzureCredential
            # If the key is not configured, then the DefaultAzureCredential will be used to support Managed Identity authentication
            self.blob_service_client = BlobServiceClient(account_url=self.endpoint, credential=DefaultAzureCredential())
        self.container_client = self.blob_service_client.get_container_client(self.container_name)

    def upload_file(self, file: BinaryIO, filename: str, tags: Dict[str, str]) -> Tuple[bytes, str]:
        """Handles uploading of the file to Azure Blob Storage."""
        contents, file_path = LocalStorageProvider.upload_file(file, filename, tags)
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(contents, overwrite=True)
            return contents, f'{self.endpoint}/{self.container_name}/{filename}'
        except Exception as e:
            raise RuntimeError(f'Error uploading file to Azure Blob Storage: {e}')

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from Azure Blob Storage with local caching."""
        try:
            filename = file_path.split('/')[-1]
            local_file_path = os.path.join(UPLOAD_DIR, filename)

            # Performance: skip re-downloading if a usable local copy already exists.
            if os.path.exists(local_file_path) and os.path.getsize(local_file_path) > 0:
                log.debug(f'Using cached local copy of {filename} (avoiding Azure download)')
                return local_file_path

            blob_client = self.container_client.get_blob_client(filename)
            with open(local_file_path, 'wb') as download_file:
                download_file.write(blob_client.download_blob().readall())
            log.info(f"Successfully downloaded {filename} from Azure Blob Storage")
            return local_file_path
        except ResourceNotFoundError as e:
            raise RuntimeError(f'Error downloading file from Azure Blob Storage: {e}')

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from Azure Blob Storage."""
        try:
            filename = file_path.split('/')[-1]
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.delete_blob()
        except ResourceNotFoundError as e:
            raise RuntimeError(f'Error deleting file from Azure Blob Storage: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from Azure Blob Storage."""
        try:
            blobs = self.container_client.list_blobs()
            for blob in blobs:
                self.container_client.delete_blob(blob.name)
        except Exception as e:
            raise RuntimeError(f'Error deleting all files from Azure Blob Storage: {e}')

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    def get_signed_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a SAS URL for direct browser streaming from Azure Blob Storage.

        Enables HTTP Range Request support for video/audio playback without backend proxying.

        Args:
            file_path: Azure file path
            expiration: URL validity in seconds (default: 1 hour)

        Returns:
            Time-limited SAS URL with Range Request support
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import datetime, timedelta

            filename = file_path.split("/")[-1]
            blob_client = self.container_client.get_blob_client(filename)

            # Generate SAS token for blob access
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=self.container_name,
                blob_name=filename,
                account_key=AZURE_STORAGE_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expiration),
            )

            # Construct full URL with SAS token
            sas_url = f"{blob_client.url}?{sas_token}"

            log.debug(f"Generated SAS URL for {filename} (expires in {expiration}s)")
            return sas_url

        except Exception as e:
            log.warning(f"Failed to generate SAS URL for {file_path}: {e}")
            # Fallback to downloading file locally
            return self.get_file(file_path)


def get_storage_provider(storage_provider: str):
    if storage_provider == 'local':
        Storage = LocalStorageProvider()
    elif storage_provider == 's3':
        Storage = S3StorageProvider()
    elif storage_provider == 'gcs':
        Storage = GCSStorageProvider()
    elif storage_provider == 'azure':
        Storage = AzureStorageProvider()
    else:
        raise RuntimeError(f'Unsupported storage provider: {storage_provider}')
    return Storage


Storage = get_storage_provider(STORAGE_PROVIDER)
