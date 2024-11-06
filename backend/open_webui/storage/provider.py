from open_webui.constants import ERROR_MESSAGES
from open_webui.config import STORAGE_PROVIDER

from openwebui.backend.open_webui.storage.base_storage_provider import StorageProvider
from openwebui.backend.open_webui.storage.local_storage_provider import LocalStorageProvider
from openwebui.backend.open_webui.storage.s3_storage_provider import S3StorageProvider

def get_storage_provider() -> StorageProvider:
    if STORAGE_PROVIDER == "s3":
        return S3StorageProvider()
    elif STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    else:
        raise ValueError(ERROR_MESSAGES.INVALID_STORAGE_PROVIDER)

Storage = get_storage_provider()
