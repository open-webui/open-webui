"""Focused regressions for private arena-model access (#30013).

These tests stub Open WebUI imports so they can run with the Python stdlib.
They cover listing (`get_filtered_models`) and chat-time (`check_model_access`)
when `BYPASS_ADMIN_ACCESS_CONTROL` and `BYPASS_MODEL_ACCESS_CONTROL` are false.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[2]
ACCESS_CONTROL_PATH = BACKEND_DIR / 'open_webui' / 'utils' / 'access_control' / '__init__.py'
MODELS_UTIL_PATH = BACKEND_DIR / 'open_webui' / 'utils' / 'models.py'

PUBLIC_READ_GRANT = {'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}
GROUP_READ_GRANT = {'principal_type': 'group', 'principal_id': 'group-1', 'permission': 'read'}


def _module(name: str, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    module.__path__ = []  # mark as a package when needed
    sys.modules[name] = module
    return module


def _ensure_parent_packages(*names: str):
    for name in names:
        if name not in sys.modules:
            _module(name)


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_stubs(*, bypass_admin: bool = False):
    """Install lightweight stand-ins for the access-control and models imports."""
    _ensure_parent_packages(
        'open_webui',
        'open_webui.models',
        'open_webui.utils',
        'open_webui.utils.access_control',
        'open_webui.routers',
        'open_webui.socket',
        'sqlalchemy',
        'sqlalchemy.ext',
        'fastapi',
    )

    config = _module(
        'open_webui.config',
        DEFAULT_USER_PERMISSIONS={},
        BYPASS_ADMIN_ACCESS_CONTROL=bypass_admin,
        DEFAULT_ARENA_MODEL={'id': 'arena-model', 'name': 'Arena Model', 'meta': {}},
    )
    _module(
        'open_webui.env',
        BYPASS_MODEL_ACCESS_CONTROL=False,
        ENABLE_PLUGINS=False,
        GLOBAL_LOG_LEVEL='WARNING',
        REDIS_KEY_PREFIX='owui',
    )
    _module(
        'open_webui.models.access_grants',
        AccessGrants=SimpleNamespace(
            has_access=AsyncMock(return_value=False),
            get_accessible_resource_ids=AsyncMock(return_value=set()),
        ),
        has_anyone_read_access_grant=lambda grants: False,
        has_public_read_access_grant=lambda grants: False,
        has_public_write_access_grant=lambda grants: False,
        has_user_access_grant=lambda grants: False,
        strip_anyone_access_grants=lambda grants: grants,
        strip_user_access_grants=lambda grants: grants,
    )
    groups = _module('open_webui.models.groups')
    groups.Groups = SimpleNamespace(get_groups_by_member_id=AsyncMock(return_value=[]))
    _module('open_webui.models.users', UserModel=object)
    _module('open_webui.models.config', Config=SimpleNamespace())
    _module('open_webui.models.functions', Functions=SimpleNamespace())
    _module('open_webui.models.models', Models=SimpleNamespace())
    _module('open_webui.utils.json_codec', JSONCodec=SimpleNamespace())
    _module('open_webui.utils.chat_variables', get_chat_variables_schema=lambda system: None)
    _module(
        'open_webui.utils.plugin',
        get_functions_cache=lambda request: {},
        get_function_module_from_cache=AsyncMock(return_value=None),
    )
    _module('open_webui.functions', get_function_models=AsyncMock(return_value=[]))
    _module('open_webui.routers.ollama')
    _module('open_webui.routers.openai')
    _module('open_webui.socket.utils', RedisDict=object)
    _module('sqlalchemy.ext.asyncio', AsyncSession=object)
    _module('fastapi', Request=object)
    return config, groups


def _user(role: str, user_id: str = 'user-1'):
    return SimpleNamespace(id=user_id, role=role)


def _arena_model(model_id: str = 'arena-private', access_grants=None):
    grants = [] if access_grants is None else access_grants
    return {
        'id': model_id,
        'name': 'Private Arena',
        'arena': True,
        'owned_by': 'arena',
        'info': {'meta': {'access_grants': grants}},
    }


class ArenaModelAccessTests(unittest.TestCase):
    def setUp(self):
        self._saved_modules = {name: sys.modules.get(name) for name in list(sys.modules)}
        self.config, self.groups = _install_stubs(bypass_admin=False)
        self.access_control = _load_module('open_webui.utils.access_control', ACCESS_CONTROL_PATH)
        sys.modules['open_webui.utils.access_control'] = self.access_control
        self.models_util = _load_module('open_webui.utils.models', MODELS_UTIL_PATH)

    def tearDown(self):
        for name in list(sys.modules):
            if name not in self._saved_modules:
                sys.modules.pop(name, None)
        for name, module in self._saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def _run(self, coro):
        return asyncio.run(coro)

    def test_empty_grants_are_visible_to_admin_when_bypass_is_off(self):
        admin = _user('admin', 'admin-1')
        model = _arena_model()

        self.assertTrue(self._run(self.access_control.has_arena_model_access(admin, model)))
        filtered = self._run(self.models_util.get_filtered_models([model], admin))
        self.assertEqual([item['id'] for item in filtered], ['arena-private'])
        self._run(self.models_util.check_model_access(admin, model))

    def test_empty_grants_stay_hidden_from_regular_users(self):
        user = _user('user', 'user-1')
        model = _arena_model()

        self.assertFalse(self._run(self.access_control.has_arena_model_access(user, model)))
        filtered = self._run(self.models_util.get_filtered_models([model], user))
        self.assertEqual(filtered, [])
        with self.assertRaises(Exception) as raised:
            self._run(self.models_util.check_model_access(user, model))
        self.assertEqual(str(raised.exception), 'Model not found')

    def test_public_grants_remain_visible_to_users_and_admins(self):
        model = _arena_model(access_grants=[PUBLIC_READ_GRANT])
        admin = _user('admin', 'admin-1')
        user = _user('user', 'user-1')

        self.assertTrue(self._run(self.access_control.has_arena_model_access(admin, model)))
        self.assertTrue(self._run(self.access_control.has_arena_model_access(user, model)))
        self.assertEqual(
            [item['id'] for item in self._run(self.models_util.get_filtered_models([model], user))],
            ['arena-private'],
        )
        self._run(self.models_util.check_model_access(user, model))

    def test_group_grants_require_membership(self):
        model = _arena_model(access_grants=[GROUP_READ_GRANT])
        user = _user('user', 'user-1')

        self.assertFalse(self._run(self.access_control.has_arena_model_access(user, model, user_group_ids=set())))
        self.assertTrue(self._run(self.access_control.has_arena_model_access(user, model, user_group_ids={'group-1'})))

    def test_second_admin_also_sees_private_arena_with_empty_grants(self):
        creator = _user('admin', 'admin-creator')
        other_admin = _user('admin', 'admin-2')
        model = _arena_model()

        self.assertTrue(self._run(self.access_control.has_arena_model_access(creator, model)))
        self.assertTrue(self._run(self.access_control.has_arena_model_access(other_admin, model)))
        self.assertEqual(
            [item['id'] for item in self._run(self.models_util.get_filtered_models([model], other_admin))],
            ['arena-private'],
        )
        self._run(self.models_util.check_model_access(other_admin, model))

    def test_explicit_group_grants_do_not_fall_back_to_admin_when_bypass_is_off(self):
        admin = _user('admin', 'admin-1')
        model = _arena_model(access_grants=[GROUP_READ_GRANT])

        self.assertFalse(self._run(self.access_control.has_arena_model_access(admin, model, user_group_ids=set())))
        self.assertEqual(self._run(self.models_util.get_filtered_models([model], admin)), [])

    def test_admin_bypass_still_allows_arena_models_with_unrelated_grants(self):
        admin = _user('admin', 'admin-1')
        model = _arena_model(access_grants=[GROUP_READ_GRANT])

        with patch.object(self.config, 'BYPASS_ADMIN_ACCESS_CONTROL', True):
            self.assertTrue(self._run(self.access_control.has_arena_model_access(admin, model)))


if __name__ == '__main__':
    unittest.main()
