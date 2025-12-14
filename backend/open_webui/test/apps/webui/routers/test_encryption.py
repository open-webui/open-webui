from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user


class TestEncryption(AbstractPostgresTest):
    BASE_PATH = "/api/v1/encryption"

    def test_policy_requires_auth(self):
        response = self.fast_api_client.get(self.create_url("/policy"))
        assert response.status_code == 401

    def test_policy(self):
        from open_webui.env import (
            WEBUI_CHAT_ENCRYPTION_ALLOW_LEGACY_READ,
            WEBUI_CHAT_ENCRYPTION_DEFAULT,
            WEBUI_CHAT_ENCRYPTION_REQUIRED,
        )

        with mock_webui_user():
            response = self.fast_api_client.get(self.create_url("/policy"))

        assert response.status_code == 200
        assert response.json() == {
            "required": WEBUI_CHAT_ENCRYPTION_REQUIRED,
            "default": WEBUI_CHAT_ENCRYPTION_DEFAULT,
            "allow_legacy_read": WEBUI_CHAT_ENCRYPTION_ALLOW_LEGACY_READ,
        }
