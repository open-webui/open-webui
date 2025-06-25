import pytest
from open_webui.models.users import User
from open_webui.services.ionos import (
    pseudonymized_user_id,
)
import open_webui.env

def get_mock_user(**kwargs) -> User:
    user_parameters = {
        "id": "47",
        "name": "John Doe",
        "email": "john.doe@openwebui.com",
        "role": "user",
        "profile_image_url": "/user.png",
        "last_active_at": 1627351200,
        "updated_at": 1627351200,
        "created_at": 162735120,
        "oauth_sub": None,
        **kwargs,
    }

    return User(**user_parameters)

class TestIonos:
    @pytest.fixture(autouse=True)
    def around_tests(self, monkeypatch):
        """
        Cleanup environments
        """
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", None, raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", None, raising = True)
        yield
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", None, raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", None, raising = True)

    def test_pseudonymized_user_id_salt_defined(self, monkeypatch):
        """
        echo -n "somesaltprefixSOMEUUIDsomesaltsuffix" | md5sum
        """

        salt_prefix = "somesaltprefix"
        salt_suffix = "somesaltsuffix"
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", salt_prefix, raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", salt_suffix, raising = True)

        oauth_sub = "oidc@SOMEUUID"

        # Note the nice nerdy start of the hex sequence :)
        expected_hash = "f00c899879750f2398c315bf8e89d1a8"

        assert pseudonymized_user_id(get_mock_user(oauth_sub = oauth_sub)) == expected_hash

    def test_pseudonymized_user_id_salt_prefix_and_suffix_undefined(self, monkeypatch):
        assert pseudonymized_user_id(get_mock_user(oauth_sub = "dont-care")) == None

    def test_pseudonymized_user_id_salt_prefix_undefined(self, monkeypatch):
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", "dont-care", raising = True)
        assert pseudonymized_user_id(get_mock_user(oauth_sub = "dont-care")) == None

    def test_pseudonymized_user_id_salt_suffix_undefined(self, monkeypatch):
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", "dont-care", raising = True)
        assert pseudonymized_user_id(get_mock_user(oauth_sub = "dont-care")) == None

    def test_pseudonymized_user_id_oauth_sub_undefined(self, monkeypatch):
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", "dont-care", raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", "dont-care", raising = True)

        assert pseudonymized_user_id(get_mock_user()) == None

    def test_pseudonymized_user_id_oauth_sub_malformed(self, monkeypatch):
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", "dont-care", raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", "dont-care", raising = True)

        with pytest.raises(Exception):
            pseudonymized_user_id(get_mock_user(oauth_sub = 'oidc'))

    def test_pseudonymized_user_id_oauth_sub_missing_sub(self, monkeypatch):
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX", "dont-care", raising = True)
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX", "dont-care", raising = True)

        with pytest.raises(Exception):
            pseudonymized_user_id(get_mock_user(oauth_sub = 'oidc@'))
