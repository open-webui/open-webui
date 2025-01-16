import io

import pytest
from open_webui.storage import provider


def mock_upload_dir(monkeypatch, tmp_path):
    """Fixture to monkey-patch the UPLOAD_DIR and create a temporary directory."""
    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr(provider, "UPLOAD_DIR", str(directory))
    return directory


def test_imports():
    provider.StorageProvider
    provider.LocalStorageProvider
    provider.S3StorageProvider
    provider.Storage


def test_get_storage_provider():
    Storage = provider.get_storage_provider("local")
    assert isinstance(Storage, provider.LocalStorageProvider)
    Storage = provider.get_storage_provider("s3")
    assert isinstance(Storage, provider.S3StorageProvider)
    with pytest.raises(RuntimeError):
        provider.get_storage_provider("invalid")


def test_class_instantiation():
    with pytest.raises(TypeError):
        provider.StorageProvider()
    with pytest.raises(TypeError):

        class Test(provider.StorageProvider):
            pass

        Test()
    provider.LocalStorageProvider()
    provider.S3StorageProvider()


class TestLocalStorageProvider(provider.LocalStorageProvider):
    file_content = b"test content"
    file_bytesio = io.BytesIO(file_content)
    filename = "test.txt"
    filename_extra = "test_exyta.txt"
    file_bytesio_empty = io.BytesIO()

    def test_upload_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        contents, file_path = self.upload_file(self.file_bytesio, self.filename)
        assert (upload_dir / self.filename).exists()
        assert (upload_dir / self.filename).read_bytes() == self.file_content
        assert contents == self.file_content
        assert file_path == str(upload_dir / self.filename)
        with pytest.raises(ValueError):
            self.upload_file(self.file_bytesio_empty, self.filename)

    def test_get_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        file_path = str(upload_dir / self.filename)
        file_path_return = self.get_file(file_path)
        assert file_path == file_path_return

    def test_delete_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        (upload_dir / self.filename).write_bytes(self.file_content)
        assert (upload_dir / self.filename).exists()
        file_path = str(upload_dir / self.filename)
        self.delete_file(file_path)
        assert not (upload_dir / self.filename).exists()

    def test_delete_all_files(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        (upload_dir / self.filename).write_bytes(self.file_content)
        (upload_dir / self.filename_extra).write_bytes(self.file_content)
        self.delete_all_files()
        assert not (upload_dir / self.filename).exists()
        assert not (upload_dir / self.filename_extra).exists()


class TestS3StorageProvider(provider.S3StorageProvider):
    file_content = b"test content"
    file_bytesio = io.BytesIO(file_content)
    filename = "test.txt"
    filename_extra = "test_extra.txt"
    file_bytesio_empty = io.BytesIO()
    bucket_name = "my-bucket"

    def test_upload_file(self, monkeypatch, tmp_path):
        upload_dir = mock_upload_dir(monkeypatch, tmp_path)
        contents, file_path = self.upload_file(self.file_bytesio, self.filename)
        assert (upload_dir / self.filename).exists()
        assert (upload_dir / self.filename).read_bytes() == self.file_content
        assert contents == self.file_content
        assert file_path == str(upload_dir / self.filename)
        with pytest.raises(ValueError):
            self.upload_file(self.file_bytesio_empty, self.filename)

    def test_get_file(self):
        pass

    def test_delete_file(self):
        pass

    def test_delete_all_files(self):
        pass
