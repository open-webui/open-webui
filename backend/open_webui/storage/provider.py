from urllib.parse import urlparse
from open_webui.config import USER_DATA_DIR
from open_webui.storage.base_storage_provider import StorageProvider
from open_webui.storage.local_storage_provider import LocalStorageProvider
from open_webui.storage.s3_storage_provider import S3StorageProvider

def get_storage_provider() -> StorageProvider:
    if USER_DATA_DIR.lower().startswith("s3://"):
        parsed_url = urlparse(USER_DATA_DIR)
        bucket_name = parsed_url.netloc
        prefix = parsed_url.path.lstrip('/')
        return S3StorageProvider(bucket_name, prefix)
    else:
        return LocalStorageProvider(USER_DATA_DIR)

Storage = get_storage_provider()
