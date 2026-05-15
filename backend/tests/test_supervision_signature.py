"""
Unit tests for the HMAC signature verifier in
backend/open_webui/routers/supervision.py.

Self-contained — runs with just pytest + fastapi installed; no Open WebUI
package import, no database, no dev-env setup required. The helper is
loaded directly from the source file with the package's heavy imports
stubbed in sys.modules, so it tests the real function (not a copy).

Route-level integration tests aren't included here on purpose: they need
the full Open WebUI Python env (peewee_migrate, env vars, etc.) and run
better as a Docker-based smoke test in dev or CI.
"""

import hashlib
import hmac
import importlib.util
import sys
import time
import types
from pathlib import Path


SECRET = 'unit-test-secret'


def _sign(body: bytes, secret: str = SECRET, drift: int = 0) -> tuple[str, str]:
    timestamp = str(int(time.time()) + drift)
    digest = hmac.new(
        secret.encode('utf-8'),
        f'{timestamp}.{body.decode("utf-8")}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return timestamp, f'v1={digest}'


def _load_supervision_module():
    """Import the supervision router with its open_webui deps stubbed.

    The unit tests only exercise `_verify_signature`, a pure function
    that touches none of these — but the module's top-level imports
    still have to resolve. Stubs let us bypass the full package init.
    """
    stub_db = types.ModuleType('open_webui.internal.db')

    async def _stub_get_async_session():
        yield None

    stub_db.get_async_session = _stub_get_async_session
    stub_db.Base = type('Base', (), {})

    # SupervisionCallbackModel is referenced as response_model on the route
    # decorator, so FastAPI validates it at module-load time — it must be a
    # real Pydantic model, not a placeholder.
    from pydantic import BaseModel

    class _StubSupervisionCallbackModel(BaseModel):
        id: str = ''

    stub_models = types.ModuleType('open_webui.models.supervision_callbacks')
    stub_models.SupervisionCallback = type('SupervisionCallback', (), {})
    stub_models.SupervisionCallbackModel = _StubSupervisionCallbackModel
    stub_models.now_seconds = lambda: int(time.time())

    sys.modules.setdefault('open_webui', types.ModuleType('open_webui'))
    sys.modules.setdefault('open_webui.internal', types.ModuleType('open_webui.internal'))
    sys.modules.setdefault('open_webui.models', types.ModuleType('open_webui.models'))
    sys.modules['open_webui.internal.db'] = stub_db
    sys.modules['open_webui.models.supervision_callbacks'] = stub_models

    path = Path(__file__).resolve().parents[1] / 'open_webui' / 'routers' / 'supervision.py'
    spec = importlib.util.spec_from_file_location('open_webui.routers.supervision', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


supervision = _load_supervision_module()


class TestVerifySignature:
    def test_returns_false_when_secret_blank(self):
        ts = str(int(time.time()))
        assert supervision._verify_signature('', ts, b'{}', 'v1=abc') is False

    def test_returns_false_when_header_missing(self):
        ts = str(int(time.time()))
        assert supervision._verify_signature(SECRET, ts, b'{}', None) is False

    def test_returns_false_when_version_unknown(self):
        body = b'{}'
        ts, sig_v1 = _sign(body)
        sig_v2 = sig_v1.replace('v1=', 'v2=')
        assert supervision._verify_signature(SECRET, ts, body, sig_v2) is False

    def test_returns_false_when_timestamp_stale(self):
        body = b'{}'
        ts, sig = _sign(body, drift=-10_000)
        assert supervision._verify_signature(SECRET, ts, body, sig) is False

    def test_returns_false_when_timestamp_not_numeric(self):
        assert supervision._verify_signature(SECRET, 'not-a-number', b'{}', 'v1=abc') is False

    def test_returns_false_when_signature_wrong(self):
        body = b'{"k": "v"}'
        ts, _ = _sign(body)
        assert supervision._verify_signature(SECRET, ts, body, 'v1=deadbeef') is False

    def test_returns_true_on_correct_signature(self):
        body = b'{"k": "v"}'
        ts, sig = _sign(body)
        assert supervision._verify_signature(SECRET, ts, body, sig) is True

    def test_returns_false_when_body_mutated(self):
        original = b'{"k": "v"}'
        tampered = b'{"k": "evil"}'
        ts, sig = _sign(original)
        assert supervision._verify_signature(SECRET, ts, tampered, sig) is False

    def test_returns_false_when_signature_header_malformed(self):
        body = b'{}'
        ts, _ = _sign(body)
        assert supervision._verify_signature(SECRET, ts, body, 'no-equals-sign') is False

    def test_handles_non_utf8_body_without_raising(self):
        # A bit-flipped or malformed body that isn't valid UTF-8 should NOT
        # raise UnicodeDecodeError out of the verifier — it should just fail
        # signature comparison and return False.
        body = b'\xc3\x28'  # invalid UTF-8 byte sequence
        ts = str(int(time.time()))
        # Construct a signature over the bytes the sender would have used
        # (we just need any signature; the goal is to confirm no exception).
        digest = hmac.new(SECRET.encode(), f'{ts}.'.encode() + body, hashlib.sha256).hexdigest()
        assert supervision._verify_signature(SECRET, ts, body, f'v1={digest}') is True
        assert supervision._verify_signature(SECRET, ts, body, 'v1=deadbeef') is False
