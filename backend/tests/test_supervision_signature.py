"""
Unit tests for the HMAC signature verifier in
backend/open_webui/routers/supervision.py.

Mostly self-contained — runs with pytest + fastapi + pydantic + sqlalchemy
installed. (sqlalchemy is needed because the router module imports it at
load time; the verifier itself doesn't touch it.) No Open WebUI package
import, no database, no dev-env setup beyond those four pip packages. The
helper is loaded directly from the source file with the package's heavy
imports stubbed in sys.modules, so it tests the real function (not a copy).

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


_STUBBED_MODULE_NAMES = (
    'open_webui',
    'open_webui.internal',
    'open_webui.internal.db',
    'open_webui.models',
    'open_webui.models.supervision_callbacks',
    'open_webui.routers.supervision',
)


def _load_supervision_module():
    """Import the supervision router with its open_webui deps stubbed.

    The unit tests only exercise `_verify_signature` / `_skew_seconds`,
    pure functions that touch none of these — but the module's top-level
    imports still have to resolve. Stubs let us bypass the full package init.

    Critical: we restore the original `sys.modules` state *immediately*
    after the import completes (in `finally`), not at test teardown. The
    loaded `supervision` module already holds references to the stub
    objects via its closures, so the tests still work — but `sys.modules`
    is clean before pytest moves on to collect or import any other test
    file. This prevents the order-dependent contamination Copilot has
    flagged across rounds: even during pytest's collection phase, no
    sibling import sees our stubs.
    """
    saved = {name: sys.modules.get(name) for name in _STUBBED_MODULE_NAMES}

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

    try:
        sys.modules['open_webui'] = types.ModuleType('open_webui')
        sys.modules['open_webui.internal'] = types.ModuleType('open_webui.internal')
        sys.modules['open_webui.models'] = types.ModuleType('open_webui.models')
        sys.modules['open_webui.internal.db'] = stub_db
        sys.modules['open_webui.models.supervision_callbacks'] = stub_models

        # Lives at backend/tests/this_file.py → parents[1] is backend/,
        # so the router path is open_webui/routers/supervision.py.
        # We keep this file out of backend/open_webui/test/ on purpose:
        # that directory is part of the open_webui package, so pytest
        # collection there triggers `import open_webui`, which pulls in
        # the full app (typer, fastapi, peewee_migrate, etc.). Living
        # under backend/tests/ keeps this suite stub-driven and runnable
        # with just pytest + fastapi + pydantic + sqlalchemy.
        path = Path(__file__).resolve().parents[1] / 'open_webui' / 'routers' / 'supervision.py'
        spec = importlib.util.spec_from_file_location('open_webui.routers.supervision', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


supervision = _load_supervision_module()


def test_sys_modules_is_not_polluted_by_stubs():
    """Guard against regression: after _load_supervision_module returns,
    sys.modules must not still contain our stub modules. Without this,
    any pytest collection that imports the real open_webui.* after this
    file would pick up our placeholders and fail in confusing ways."""
    for name in _STUBBED_MODULE_NAMES:
        mod = sys.modules.get(name)
        if mod is None:
            continue
        # If the real package was already imported before us, the real
        # module is still in sys.modules — that's fine. What we must NOT
        # see is the bare types.ModuleType('open_webui*') placeholders
        # we planted, which have neither the real package's __file__ nor
        # any of its attributes.
        assert hasattr(mod, '__file__') or name == 'open_webui.routers.supervision', (
            f'sys.modules[{name!r}] is still a test stub; stubs leaked out of _load_supervision_module'
        )


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


class TestSkewSeconds:
    """Guards _skew_seconds against malformed env values raising at request time."""

    def test_returns_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv('WORKBENCH_CALLBACK_SKEW_SEC', raising=False)
        assert supervision._skew_seconds() == supervision.DEFAULT_SKEW_SECONDS

    def test_returns_int_when_env_valid(self, monkeypatch):
        monkeypatch.setenv('WORKBENCH_CALLBACK_SKEW_SEC', '42')
        assert supervision._skew_seconds() == 42

    def test_falls_back_to_default_on_garbage(self, monkeypatch):
        monkeypatch.setenv('WORKBENCH_CALLBACK_SKEW_SEC', 'not-an-int')
        assert supervision._skew_seconds() == supervision.DEFAULT_SKEW_SECONDS

    def test_falls_back_to_default_on_negative(self, monkeypatch):
        monkeypatch.setenv('WORKBENCH_CALLBACK_SKEW_SEC', '-5')
        # A negative skew would make abs(now - ts) > skew always true and
        # reject every callback. Misconfiguration should silently fall
        # back to the default, not nuke the receiver.
        assert supervision._skew_seconds() == supervision.DEFAULT_SKEW_SECONDS

    def test_verify_signature_does_not_500_on_garbage_skew(self, monkeypatch):
        monkeypatch.setenv('WORKBENCH_CALLBACK_SKEW_SEC', 'banana')
        ts = str(int(time.time()))
        body = b'{}'
        digest = hmac.new(SECRET.encode(), f'{ts}.'.encode() + body, hashlib.sha256).hexdigest()
        # Should evaluate cleanly and return True; previously raised ValueError
        # inside _verify_signature when the env var was non-int.
        assert supervision._verify_signature(SECRET, ts, body, f'v1={digest}') is True
