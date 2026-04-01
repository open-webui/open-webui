import importlib.util
from typing import Any


def _value(value: Any) -> Any:
    return getattr(value, 'value', value)


def _enabled(value: Any) -> bool:
    return bool(_value(value))


def _missing(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is None


def validate_optional_dependencies(config: Any) -> None:
    errors: list[str] = []

    try:
        from open_webui.config import STORAGE_PROVIDER as DEFAULT_STORAGE_PROVIDER
    except Exception:
        DEFAULT_STORAGE_PROVIDER = 'local'

    storage_provider = (_value(getattr(config, 'STORAGE_PROVIDER', DEFAULT_STORAGE_PROVIDER)) or 'local').lower()
    if storage_provider == 'gcs' and _missing('google.cloud.storage'):
        errors.append("STORAGE_PROVIDER=gcs requires 'google-cloud-storage'")
    if storage_provider == 'azure':
        if _missing('azure.identity'):
            errors.append("STORAGE_PROVIDER=azure requires 'azure-identity'")
        if _missing('azure.storage.blob'):
            errors.append("STORAGE_PROVIDER=azure requires 'azure-storage-blob'")

    if _enabled(getattr(config, 'ENABLE_LDAP', False)) and _missing('ldap3'):
        errors.append("ENABLE_LDAP=true requires 'ldap3'")

    if _enabled(getattr(config, 'ENABLE_WEB_SEARCH', False)):
        web_search_engine = (_value(getattr(config, 'WEB_SEARCH_ENGINE', '')) or '').lower()
        if web_search_engine in {'duckduckgo', 'ddgs'} and _missing('ddgs'):
            errors.append("WEB_SEARCH_ENGINE=duckduckgo requires 'ddgs'")

    if _enabled(getattr(config, 'ENABLE_IMAGE_GENERATION', False)):
        image_engine = (_value(getattr(config, 'IMAGE_GENERATION_ENGINE', '')) or '').lower()
        if image_engine == 'comfyui' and _missing('websocket'):
            errors.append("IMAGE_GENERATION_ENGINE=comfyui requires 'websocket-client'")

    edit_engine = (_value(getattr(config, 'IMAGE_EDIT_ENGINE', '')) or '').lower()
    if edit_engine == 'comfyui' and _missing('websocket'):
        errors.append("IMAGE_EDIT_ENGINE=comfyui requires 'websocket-client'")

    if errors:
        raise RuntimeError('Startup dependency validation failed:\n- ' + '\n- '.join(errors))
