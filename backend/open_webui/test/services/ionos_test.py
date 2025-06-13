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
        **kwargs,
    }

    return User(**user_parameters)

class TestIonos:
    @pytest.fixture(autouse=True)
    def around_tests(self, monkeypatch):
        """
        Cleanup environments
        """
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT", None, raising = True)
        yield
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT", None, raising = True)

    def test_pseudonymized_user_id_salt_defined(self, monkeypatch):
        """
        echo -n "SOMEUUIDsomesalt" | md5sum
        """

        salt = "somesalt"
        monkeypatch.setattr(open_webui.services.ionos, "IONOS_USER_ID_PSEUDONYMIZATION_SALT", salt, raising = True)

        user_id = "SOMEUUID"

        expected_hash = "3c810acae41ee75abfae48d53abbcee5"

        assert pseudonymized_user_id(get_mock_user(id = user_id)) == expected_hash

    def test_pseudonymized_user_id_salt_undefined(self, monkeypatch):
        assert pseudonymized_user_id(get_mock_user(id = "dont-care")) == None
