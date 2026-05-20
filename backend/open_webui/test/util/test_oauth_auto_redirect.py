import os
import subprocess
import sys

import pytest


def _read_persistent_config(env_value):
    """Spawn a fresh interpreter so SQLAlchemy's declarative base is not reloaded.

    Returns a dict with keys: value, env_name, config_path.
    """
    script = (
        'import json, sys; '
        'from open_webui.config import OAUTH_AUTO_REDIRECT as c; '
        "print(json.dumps({'value': c.value, 'env_name': c.env_name, 'config_path': c.config_path}))"
    )
    env = os.environ.copy()
    env.pop('OAUTH_AUTO_REDIRECT', None)
    if env_value is not None:
        env['OAUTH_AUTO_REDIRECT'] = env_value
    # Ensure the backend package is importable regardless of CWD.
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    existing_path = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = backend_dir + (os.pathsep + existing_path if existing_path else '')
    result = subprocess.run(
        [sys.executable, '-c', script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    import json

    return json.loads(result.stdout.strip().splitlines()[-1])


class TestOAuthAutoRedirectConfig:
    """OAUTH_AUTO_REDIRECT env var -> PersistentConfig wiring."""

    def test_defaults_to_false_when_env_unset(self):
        config = _read_persistent_config(None)
        assert config['value'] is False

    @pytest.mark.parametrize('truthy', ['true', 'True', 'TRUE'])
    def test_truthy_env_values_enable_redirect(self, truthy):
        config = _read_persistent_config(truthy)
        assert config['value'] is True

    @pytest.mark.parametrize('falsy', ['false', 'False', '0', '', 'yes', 'no'])
    def test_non_true_env_values_keep_redirect_disabled(self, falsy):
        config = _read_persistent_config(falsy)
        assert config['value'] is False

    def test_persistent_config_key_matches_oauth_namespace(self):
        config = _read_persistent_config(None)
        assert config['env_name'] == 'OAUTH_AUTO_REDIRECT'
        assert config['config_path'] == 'oauth.auto_redirect'
