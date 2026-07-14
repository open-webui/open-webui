import base64
import datetime as dt
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

module_path = Path(__file__).parents[1] / 'utils' / 'oauth_token.py'
spec = importlib.util.spec_from_file_location('oauth_token', module_path)
oauth_token = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth_token)

_get_id_token_expiry = oauth_token._get_id_token_expiry
_is_oauth_token_refresh_needed = oauth_token._is_oauth_token_refresh_needed


def _make_jwt(payload: dict) -> str:
    def encode(value: dict) -> str:
        data = json.dumps(value, separators=(',', ':')).encode()
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    return f'{encode({"alg": "none"})}.{encode(payload)}.'


class TestOAuthTokenRefresh(unittest.TestCase):
    def test_id_token_near_expiry_requires_refresh(self):
        session = SimpleNamespace(
            expires_at=(dt.datetime.now() + dt.timedelta(hours=1)).timestamp(),
            token={'id_token': _make_jwt({'exp': int((dt.datetime.now() + dt.timedelta(minutes=1)).timestamp())})},
        )

        self.assertTrue(_is_oauth_token_refresh_needed(session))

    def test_valid_id_token_does_not_require_refresh(self):
        expiry = int((dt.datetime.now() + dt.timedelta(hours=1)).timestamp())
        session = SimpleNamespace(
            expires_at=(dt.datetime.now() + dt.timedelta(hours=1)).timestamp(),
            token={'id_token': _make_jwt({'exp': expiry})},
        )

        self.assertEqual(_get_id_token_expiry(session.token), expiry)
        self.assertFalse(_is_oauth_token_refresh_needed(session))

    def test_missing_or_malformed_id_token_keeps_access_token_behavior(self):
        access_expiry = (dt.datetime.now() + dt.timedelta(hours=1)).timestamp()

        for token in ({}, {'id_token': 'not-a-jwt'}, {'id_token': _make_jwt({})}):
            with self.subTest(token=token):
                session = SimpleNamespace(expires_at=access_expiry, token=token)
                self.assertIsNone(_get_id_token_expiry(token))
                self.assertFalse(_is_oauth_token_refresh_needed(session))

        session = SimpleNamespace(
            expires_at=(dt.datetime.now() + dt.timedelta(minutes=1)).timestamp(),
            token={'id_token': 'not-a-jwt'},
        )
        self.assertTrue(_is_oauth_token_refresh_needed(session))


if __name__ == '__main__':
    unittest.main()
