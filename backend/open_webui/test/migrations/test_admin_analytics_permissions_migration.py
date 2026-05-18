import importlib.util
import json
from pathlib import Path

LEGACY_STORED_PERMISSIONS = {
    'workspace': {'models': True},
    'sharing': {'public_chats': False},
    'access_grants': {'allow_users': True},
    'chat': {'controls': True},
    'features': {'notes': True},
    'settings': {'interface': True},
}


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[2]
        / 'migrations'
        / 'versions'
        / 'f8a9b0c1d2e3_add_admin_analytics_permissions.py'
    )
    spec = importlib.util.spec_from_file_location('admin_analytics_migration', migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_migration = _load_migration_module()
_normalize_permissions = _migration._normalize_permissions
_ensure_admin_permissions = _migration._ensure_admin_permissions


def test_normalize_permissions_adds_admin_section():
    result = _normalize_permissions(LEGACY_STORED_PERMISSIONS.copy())
    assert result is not None
    assert 'admin' in result
    assert result['admin']['analytics'] is False


def test_normalize_permissions_idempotent():
    first = _normalize_permissions(LEGACY_STORED_PERMISSIONS.copy())
    second = _normalize_permissions(first)
    assert first == second


def test_normalize_permissions_none():
    assert _normalize_permissions(None) is None


def test_ensure_admin_preserves_existing_true_flag():
    perms = {**LEGACY_STORED_PERMISSIONS, 'admin': {'analytics': True}}
    result = _ensure_admin_permissions(perms)
    assert result['admin']['analytics'] is True


def test_config_payload_shape_after_upgrade():
    """Simulate pre-upgrade config JSON stored in the database."""
    data = {
        'version': 0,
        'user': {
            'permissions': LEGACY_STORED_PERMISSIONS.copy(),
        },
    }
    permissions = data['user']['permissions']
    data['user']['permissions'] = _normalize_permissions(permissions)

    assert data['user']['permissions']['admin']['analytics'] is False
    assert json.dumps(data['user']['permissions'])
