import io
from unittest.mock import MagicMock

import pytest

from open_webui.storage import provider


def mock_upload_dir(monkeypatch, tmp_path):
    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr(provider, "UPLOAD_DIR", str(directory))
    return directory


def test_imports():
    provider.StorageProvider
    provider.LocalStorageProvider
    provider.S3StorageProvider
    provider.GCSStorageProvider
    provider.AzureStorageProvider
    provider.Storage


def test_get_storage_provider_local():
    storage = provider.get_storage_provider("local")
    assert isinstance(storage, provider.LocalStorageProvider)
    with pytest.raises(RuntimeError):
        provider.get_storage_provider("invalid")


class TestLocalStorageProvider:
    file_content = b"test content"
    filename = "test.txt"
    filename_extra = "test_extra.txt"

    def test_upload_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        storage = provider.LocalStorageProvider()

        contents, file_path = storage.upload_file(
            io.BytesIO(self.file_content), self.filename, {}
        )
        assert (upload_dir / self.filename).exists()
        assert (upload_dir / self.filename).read_bytes() == self.file_content
        assert contents == self.file_content
        assert file_path == str(upload_dir / self.filename)

        with pytest.raises(ValueError):
            storage.upload_file(io.BytesIO(), self.filename, {})

    def test_get_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        storage = provider.LocalStorageProvider()

        file_path = str(upload_dir / self.filename)
        assert storage.get_file(file_path) == file_path

    def test_delete_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        storage = provider.LocalStorageProvider()

        path = upload_dir / self.filename
        path.write_bytes(self.file_content)
        assert path.exists()

        storage.delete_file(str(path))
        assert not path.exists()

    def test_delete_all_files(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        storage = provider.LocalStorageProvider()

        (upload_dir / self.filename).write_bytes(self.file_content)
        (upload_dir / self.filename_extra).write_bytes(self.file_content)
        storage.delete_all_files()
        assert not (upload_dir / self.filename).exists()
        assert not (upload_dir / self.filename_extra).exists()


@pytest.fixture
def s3_provider(monkeypatch, tmp_path):
    upload_dir = mock_upload_dir(monkeypatch, tmp_path)

    s3_client = MagicMock()
    monkeypatch.setattr(provider.boto3, "client", MagicMock(return_value=s3_client))
    monkeypatch.setattr(provider, "S3_BUCKET_NAME", "my-bucket")
    monkeypatch.setattr(provider, "S3_KEY_PREFIX", "prefix")
    monkeypatch.setattr(provider, "S3_REGION_NAME", "us-east-1")
    monkeypatch.setattr(provider, "S3_ENDPOINT_URL", None)
    monkeypatch.setattr(provider, "S3_USE_ACCELERATE_ENDPOINT", False)
    monkeypatch.setattr(provider, "S3_ADDRESSING_STYLE", None)
    monkeypatch.setattr(provider, "S3_ENABLE_TAGGING", True)
    monkeypatch.setattr(provider, "S3_ACCESS_KEY_ID", None)
    monkeypatch.setattr(provider, "S3_SECRET_ACCESS_KEY", None)

    storage = provider.S3StorageProvider()
    return storage, upload_dir, s3_client


class TestS3StorageProvider:
    file_content = b"test content"
    filename = "test.txt"
    filename_extra = "test_extra.txt"

    def test_upload_file(self, s3_provider):
        storage, upload_dir, s3_client = s3_provider

        contents, s3_file_path = storage.upload_file(
            io.BytesIO(self.file_content), self.filename, {"tag": "value"}
        )

        assert contents == self.file_content
        assert (upload_dir / self.filename).exists()
        assert (upload_dir / self.filename).read_bytes() == self.file_content
        assert s3_file_path == "s3://my-bucket/prefix/test.txt"

        s3_client.upload_file.assert_called_once()
        s3_client.put_object_tagging.assert_called_once()

    def test_get_file(self, s3_provider):
        storage, upload_dir, s3_client = s3_provider

        def _download_file(_bucket, _key, dest):
            with open(dest, "wb") as f:
                f.write(self.file_content)

        s3_client.download_file.side_effect = _download_file
        file_path = storage.get_file("s3://my-bucket/prefix/test.txt")

        assert file_path == str(upload_dir / self.filename)
        assert (upload_dir / self.filename).read_bytes() == self.file_content

    def test_delete_file(self, s3_provider):
        storage, upload_dir, s3_client = s3_provider
        (upload_dir / self.filename).write_bytes(self.file_content)

        storage.delete_file("s3://my-bucket/prefix/test.txt")
        s3_client.delete_object.assert_called_once_with(Bucket="my-bucket", Key="prefix/test.txt")
        assert not (upload_dir / self.filename).exists()

    def test_delete_all_files(self, s3_provider):
        storage, upload_dir, s3_client = s3_provider
        (upload_dir / self.filename).write_bytes(self.file_content)
        (upload_dir / self.filename_extra).write_bytes(self.file_content)

        s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/test.txt"},
                {"Key": "other/skip.txt"},
                {"Key": "prefix/test_extra.txt"},
            ]
        }

        storage.delete_all_files()
        assert s3_client.delete_object.call_count == 2
        assert not (upload_dir / self.filename).exists()
        assert not (upload_dir / self.filename_extra).exists()


@pytest.fixture
def gcs_provider(monkeypatch, tmp_path):
    upload_dir = mock_upload_dir(monkeypatch, tmp_path)

    bucket = MagicMock()
    client = MagicMock()
    client.bucket.return_value = bucket
    monkeypatch.setattr(provider.storage, "Client", MagicMock(return_value=client))
    monkeypatch.setattr(provider, "GCS_BUCKET_NAME", "my-bucket")
    monkeypatch.setattr(provider, "GOOGLE_APPLICATION_CREDENTIALS_JSON", None)

    storage = provider.GCSStorageProvider()
    return storage, upload_dir, bucket


class TestGCSStorageProvider:
    file_content = b"test content"
    filename = "test.txt"
    filename_extra = "test_extra.txt"

    def test_upload_file(self, gcs_provider):
        storage, upload_dir, bucket = gcs_provider
        blob = MagicMock()
        bucket.blob.return_value = blob

        contents, gcs_file_path = storage.upload_file(
            io.BytesIO(self.file_content), self.filename, {}
        )

        assert contents == self.file_content
        assert gcs_file_path == "gs://my-bucket/test.txt"
        assert (upload_dir / self.filename).exists()
        blob.upload_from_filename.assert_called_once()

        with pytest.raises(ValueError):
            storage.upload_file(io.BytesIO(), self.filename, {})

    def test_get_file(self, gcs_provider):
        storage, upload_dir, bucket = gcs_provider
        blob = MagicMock()

        def _download_to_filename(dest):
            with open(dest, "wb") as f:
                f.write(self.file_content)

        blob.download_to_filename.side_effect = _download_to_filename
        bucket.get_blob.return_value = blob

        file_path = storage.get_file("gs://my-bucket/test.txt")
        assert file_path == str(upload_dir / self.filename)
        assert (upload_dir / self.filename).read_bytes() == self.file_content

    def test_delete_file(self, gcs_provider):
        storage, upload_dir, bucket = gcs_provider
        (upload_dir / self.filename).write_bytes(self.file_content)
        blob = MagicMock()
        bucket.get_blob.return_value = blob

        storage.delete_file("gs://my-bucket/test.txt")
        blob.delete.assert_called_once()
        assert not (upload_dir / self.filename).exists()

    def test_delete_all_files(self, gcs_provider):
        storage, upload_dir, bucket = gcs_provider
        (upload_dir / self.filename).write_bytes(self.file_content)
        (upload_dir / self.filename_extra).write_bytes(self.file_content)

        blob1 = MagicMock()
        blob2 = MagicMock()
        bucket.list_blobs.return_value = [blob1, blob2]

        storage.delete_all_files()
        blob1.delete.assert_called_once()
        blob2.delete.assert_called_once()
        assert not (upload_dir / self.filename).exists()
        assert not (upload_dir / self.filename_extra).exists()


@pytest.fixture
def azure_provider(monkeypatch, tmp_path):
    upload_dir = mock_upload_dir(monkeypatch, tmp_path)

    container_client = MagicMock()
    blob_client = MagicMock()
    container_client.get_blob_client.return_value = blob_client

    blob_service_client = MagicMock()
    blob_service_client.get_container_client.return_value = container_client

    monkeypatch.setattr(
        provider, "BlobServiceClient", MagicMock(return_value=blob_service_client)
    )
    monkeypatch.setattr(provider, "AZURE_STORAGE_ENDPOINT", "https://myaccount.blob.core.windows.net")
    monkeypatch.setattr(provider, "AZURE_STORAGE_CONTAINER_NAME", "my-container")
    monkeypatch.setattr(provider, "AZURE_STORAGE_KEY", "dummy-key")

    storage = provider.AzureStorageProvider()
    return storage, upload_dir, container_client, blob_client


class TestAzureStorageProvider:
    file_content = b"test content"
    filename = "test.txt"
    filename_extra = "test_extra.txt"

    def test_upload_file(self, azure_provider):
        storage, upload_dir, _container_client, blob_client = azure_provider

        contents, azure_file_path = storage.upload_file(
            io.BytesIO(self.file_content), self.filename, {}
        )

        blob_client.upload_blob.assert_called_once_with(self.file_content, overwrite=True)
        assert contents == self.file_content
        assert azure_file_path == "https://myaccount.blob.core.windows.net/my-container/test.txt"
        assert (upload_dir / self.filename).exists()

        with pytest.raises(ValueError):
            storage.upload_file(io.BytesIO(), self.filename, {})

    def test_get_file(self, azure_provider):
        storage, upload_dir, _container_client, blob_client = azure_provider
        download = MagicMock()
        download.readall.return_value = self.file_content
        blob_client.download_blob.return_value = download

        file_url = "https://myaccount.blob.core.windows.net/my-container/test.txt"
        file_path = storage.get_file(file_url)

        assert file_path == str(upload_dir / self.filename)
        assert (upload_dir / self.filename).read_bytes() == self.file_content

    def test_delete_file(self, azure_provider):
        storage, upload_dir, _container_client, blob_client = azure_provider
        (upload_dir / self.filename).write_bytes(self.file_content)

        file_url = "https://myaccount.blob.core.windows.net/my-container/test.txt"
        storage.delete_file(file_url)

        blob_client.delete_blob.assert_called_once()
        assert not (upload_dir / self.filename).exists()

    def test_delete_all_files(self, azure_provider):
        storage, upload_dir, container_client, _blob_client = azure_provider
        (upload_dir / self.filename).write_bytes(self.file_content)
        (upload_dir / self.filename_extra).write_bytes(self.file_content)

        blob1 = MagicMock()
        blob1.name = self.filename
        blob2 = MagicMock()
        blob2.name = self.filename_extra
        container_client.list_blobs.return_value = [blob1, blob2]

        storage.delete_all_files()
        container_client.delete_blob.assert_any_call(self.filename)
        container_client.delete_blob.assert_any_call(self.filename_extra)
        assert not (upload_dir / self.filename).exists()
        assert not (upload_dir / self.filename_extra).exists()
