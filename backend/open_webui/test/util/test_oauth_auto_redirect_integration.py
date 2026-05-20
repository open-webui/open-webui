"""Integration test for OAUTH_AUTO_REDIRECT through the real FastAPI app.

Boots ``open_webui.main`` with an OIDC provider pointed at an in-process mock
identity provider, then asserts at the HTTP layer that:

  1. GET /api/config        exposes ``oauth.auto_redirect`` and the ``oidc``
                            provider — i.e. the frontend can see the feature.
  2. GET /oauth/oidc/login  redirects (302) to the IdP's authorize endpoint —
                            i.e. the configured SSO entry point actually works.

It runs in a subprocess so the OAuth/OIDC environment is set *before*
``open_webui.config`` is imported — ``OAUTH_PROVIDERS`` is built at import time.

The mock IdP only needs to serve the OpenID discovery document; ``handle_login``
fetches that and builds the redirect without ever calling /authorize or /token.
"""

import os
import subprocess
import sys


def _probe() -> None:
    """Runs in the subprocess: boot the app against a mock IdP and assert."""
    import json
    import shutil
    import tempfile
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    issuer: dict = {}

    class _DiscoveryHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence
            return

        def do_GET(self):
            if self.path == '/.well-known/openid-configuration':
                doc = json.dumps(
                    {
                        'issuer': issuer['url'],
                        'authorization_endpoint': f'{issuer["url"]}/authorize',
                        'token_endpoint': f'{issuer["url"]}/token',
                        'jwks_uri': f'{issuer["url"]}/jwks',
                        'userinfo_endpoint': f'{issuer["url"]}/userinfo',
                        'response_types_supported': ['code'],
                        'id_token_signing_alg_values_supported': ['RS256'],
                        'scopes_supported': ['openid', 'email', 'profile'],
                    }
                ).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(doc)))
                self.end_headers()
                self.wfile.write(doc)
            else:
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()

    server = ThreadingHTTPServer(('127.0.0.1', 0), _DiscoveryHandler)
    issuer['url'] = f'http://127.0.0.1:{server.server_address[1]}'
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Environment must be in place before open_webui.config is imported.
    data_dir = tempfile.mkdtemp(prefix='owui-oidc-it-')
    os.environ.update(
        {
            'DATA_DIR': data_dir,
            'WEBUI_AUTH': 'true',
            'WEBUI_SECRET_KEY': 'integration-test-secret',
            'ENABLE_PERSISTENT_CONFIG': 'false',
            'OAUTH_AUTO_REDIRECT': 'true',
            'OAUTH_CLIENT_ID': 'integration-test',
            'OAUTH_CLIENT_SECRET': 'integration-secret',
            'OAUTH_PROVIDER_NAME': 'SSO',
            'OPENID_PROVIDER_URL': f'{issuer["url"]}/.well-known/openid-configuration',
            # Keep app boot offline/fast — irrelevant to the auth flow.
            'RAG_EMBEDDING_ENGINE': 'ollama',
            'HF_HUB_OFFLINE': '1',
        }
    )

    from fastapi.testclient import TestClient
    from open_webui.main import app

    try:
        with TestClient(app) as client:
            config = client.get('/api/config').json()
            oauth = config.get('oauth', {})
            assert oauth.get('auto_redirect') is True, f'/api/config oauth.auto_redirect: {oauth}'
            assert 'oidc' in oauth.get('providers', {}), f'/api/config oauth.providers: {oauth}'

            resp = client.get('/oauth/oidc/login', follow_redirects=False)
            assert resp.status_code in (302, 307), f'/oauth/oidc/login status: {resp.status_code}'
            location = resp.headers.get('location', '')
            assert location.startswith(f'{issuer["url"]}/authorize'), f'/oauth/oidc/login Location: {location}'
    finally:
        server.shutdown()
        shutil.rmtree(data_dir, ignore_errors=True)

    print('OAUTH_AUTO_REDIRECT integration probe: OK')


def test_oauth_auto_redirect_integration():
    """Boot the app with a mock OIDC provider; verify config exposure + login redirect."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    env = {**os.environ, 'PYTHONPATH': backend_dir + os.pathsep + os.environ.get('PYTHONPATH', '')}
    result = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    assert result.returncode == 0, f'integration probe failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}'
    assert 'integration probe: OK' in result.stdout


if __name__ == '__main__':
    _probe()
