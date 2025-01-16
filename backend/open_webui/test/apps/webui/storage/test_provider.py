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
    def test_upload_file(self):
        pass
    def test_get_file(self):
        pass
    def test_delete_file(self):
        pass
    def test_delete_all_files(self):
        pass


class TestLocalStorageProvider(provider.S3StorageProvider):
    def test_upload_file(self):
        pass
    def test_get_file(self):
        pass
    def test_delete_file(self):
        pass
    def test_delete_all_files(self):
        pass

)
