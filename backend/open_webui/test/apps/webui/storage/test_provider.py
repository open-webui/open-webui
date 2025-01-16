import pytest
from open_webui.storage import provider


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
