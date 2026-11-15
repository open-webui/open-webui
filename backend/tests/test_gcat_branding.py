"""Dependency-free regression tests for GCAT's public backend identity."""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest


BACKEND = Path(__file__).resolve().parents[1] / 'open_webui'


def load_function(path, name, namespace):
    """Execute a production function without importing the database/ML stack."""
    tree = ast.parse((BACKEND / path).read_text(encoding='utf-8'))
    function = next(
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )
    function.decorator_list = []
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class GcatBrandingTests(unittest.TestCase):
    def test_fixed_public_identity_ignores_legacy_environment(self):
        tree = ast.parse((BACKEND / 'env.py').read_text(encoding='utf-8'))
        expected = {
            'WEBUI_NAME': 'GCAT',
            'WEBUI_FAVICON_URL': '/static/gcat.png',
            'EXTERNAL_PWA_MANIFEST_URL': None,
            'ENABLE_VERSION_UPDATE_CHECK': False,
        }
        for name, value in expected.items():
            assignments = [
                node
                for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            ]
            self.assertEqual(ast.literal_eval(assignments[-1].value), value)

    def test_manifest_uses_local_gcat_identity_even_with_remote_override(self):
        namespace = {
            'WEBUI_NAME': 'GCAT',
            'app': SimpleNamespace(
                state=SimpleNamespace(
                    WEBUI_NAME='Upstream', EXTERNAL_PWA_MANIFEST_URL='https://example.invalid/manifest.json'
                )
            ),
        }
        manifest = asyncio.run(load_function(Path('main.py'), 'get_manifest_json', namespace)())
        self.assertEqual(manifest['name'], 'GCAT')
        self.assertEqual(manifest['short_name'], 'GCAT')
        self.assertTrue(all(icon['src'] == '/static/gcat.svg' for icon in manifest['icons']))
        self.assertEqual(manifest['share_target']['params'], {'text': 'shared'})

    def test_runtime_news_does_not_fetch_or_advertise_upstream_releases(self):
        namespace = {'VERSION': '1.2.3', 'Depends': lambda dependency: None, 'get_verified_user': object()}
        updates = load_function(Path('main.py'), 'get_app_latest_release_version', namespace)
        changelog = load_function(Path('main.py'), 'get_app_changelog', namespace)
        self.assertEqual(asyncio.run(updates()), {'current': '1.2.3', 'latest': '1.2.3'})
        self.assertEqual(asyncio.run(changelog()), {})

    def test_license_entitlements_cannot_replace_name_or_assets(self):
        payload = {
            'resources': {'gcat.png': 'untrusted asset'},
            'name': 'Upstream',
            'count': 42,
            'metadata': {'plan': 'enterprise', 'login_footer': 'Upstream', 'auth_logo_position': 'hidden'},
        }
        namespace = {
            'requests': SimpleNamespace(post=lambda *args, **kwargs: SimpleNamespace(ok=True, json=lambda: payload)),
        }
        app = SimpleNamespace(state=SimpleNamespace(WEBUI_NAME='GCAT'))
        get_license_data = load_function(Path('utils/auth.py'), 'get_license_data', namespace)
        self.assertTrue(get_license_data(app, 'test-key'))
        self.assertEqual(app.state.WEBUI_NAME, 'GCAT')
        self.assertEqual(app.state.USER_COUNT, 42)
        self.assertEqual(app.state.LICENSE_METADATA, {'plan': 'enterprise'})

    def test_legacy_custom_branding_fetch_is_disabled(self):
        tree = ast.parse((BACKEND / 'config.py').read_text(encoding='utf-8'))
        custom_name = next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'CUSTOM_NAME' for target in node.targets)
        )
        self.assertEqual(ast.literal_eval(custom_name.value), '')
        self.assertNotIn('api.openwebui.com/api/v1/custom/', ast.unparse(tree))


if __name__ == '__main__':
    unittest.main()
