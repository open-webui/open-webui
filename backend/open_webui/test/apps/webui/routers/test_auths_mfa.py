from test.util.abstract_integration_test import AbstractPostgresTest
from test.util.mock_user import mock_webui_user
import pyotp
import json  # For backup codes handling


class TestAuthsMFA(AbstractPostgresTest):
    BASE_PATH = "/api/v1/auths/mfa"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.auths import Auths
        from open_webui.models.users import Users
        from open_webui.utils.auth import get_password_hash

        cls.users = Users
        cls.auths = Auths
        # We'll need this for password handling in our tests
        cls.get_password_hash = get_password_hash

    def test_mfa_setup(self):
        """Test MFA setup initialization"""
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )

        with mock_webui_user(id=user.id):
            response = self.fast_api_client.post(self.create_url("/setup"))
        
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code" in data
        assert data["secret"] is not None
        assert len(data["secret"]) > 0
        assert data["qr_code"].startswith("data:image/png;base64,")

        # Verify the secret is stored in the database but MFA is not yet enabled
        auth = self.auths.get_auth_by_id(user.id)
        assert auth.mfa_secret is not None
        assert auth.mfa_enabled is False

    def test_mfa_enable(self):
        """Test enabling MFA with a valid TOTP code"""
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # First set up MFA
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        
        # Generate a valid TOTP code using the secret
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Enable MFA with the valid code
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        assert enable_response.status_code == 200
        data = enable_response.json()
        assert data["enabled"] is True
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        
        # Verify MFA is now enabled in the database
        auth = self.auths.get_auth_by_id(user.id)
        assert auth.mfa_enabled is True
        assert auth.backup_codes is not None
        
        # Handle backup codes which may be stored as a JSON string
        backup_codes = auth.backup_codes
        if isinstance(backup_codes, str):
            backup_codes = json.loads(backup_codes)
            
        assert len(backup_codes) > 0

    def test_mfa_enable_invalid_code(self):
        """Test enabling MFA with an invalid TOTP code fails"""
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # First set up MFA
        with mock_webui_user(id=user.id):
            self.fast_api_client.post(self.create_url("/setup"))
        
        # Try to enable MFA with an invalid code
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": "123456"}  # Invalid code
            )
        
        assert enable_response.status_code == 400
        
        # Verify MFA is still not enabled
        auth = self.auths.get_auth_by_id(user.id)
        assert auth.mfa_enabled is False

    def test_signin_with_mfa(self):
        """Test signin process with MFA enabled"""
        # Create a user with MFA enabled
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up and enable MFA for this user
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        # Now try to sign in - this should return a partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "john.doe@openwebui.com", "password": "password"}
        )
        
        assert signin_response.status_code == 200
        signin_data = signin_response.json()
        assert "mfa_required" in signin_data
        assert signin_data["mfa_required"] is True
        assert "email" in signin_data
        assert "token" not in signin_data
        
        # Get the partial token from cookies
        cookies = signin_response.cookies
        assert "partial_token" in cookies
        
        # Now complete authentication with a valid MFA code
        new_valid_code = totp.now()  # Get a fresh code
        mfa_verify_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": new_valid_code},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert mfa_verify_response.status_code == 200
        verify_data = mfa_verify_response.json()
        assert "token" in verify_data
        assert verify_data["token"] is not None
        assert len(verify_data["token"]) > 0
        assert verify_data["token_type"] == "bearer"
        assert verify_data["id"] == user.id

    def test_signin_with_mfa_invalid_code(self):
        """Test signin with an invalid MFA code fails"""
        # Create a user with MFA enabled
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up and enable MFA for this user
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "john.doe@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Try to complete authentication with an invalid MFA code
        mfa_verify_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": "111111"},  # Invalid code
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert mfa_verify_response.status_code == 400
        
    def test_verify_backup_code(self):
        """Test signin with a backup code"""
        # Create a user with MFA enabled
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up and enable MFA for this user
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        # Get a backup code
        backup_codes = enable_response.json()["backup_codes"]
        backup_code = backup_codes[0]
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "john.doe@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Complete authentication with the backup code
        mfa_verify_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": backup_code},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert mfa_verify_response.status_code == 200
        verify_data = mfa_verify_response.json()
        assert "token" in verify_data
        assert verify_data["is_backup_code_used"] is True
        
        # Verify the backup code can't be used again
        signin_response2 = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "john.doe@openwebui.com", "password": "password"}
        )
        
        cookies2 = signin_response2.cookies
        
        mfa_verify_response2 = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": backup_code},
            cookies={"partial_token": cookies2["partial_token"]}
        )
        
        assert mfa_verify_response2.status_code == 400

    def test_disable_mfa(self):
        """Test disabling MFA"""
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up and enable MFA for this user
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        # Test disabling MFA with missing verification code
        with mock_webui_user(id=user.id):
            missing_code_response = self.fast_api_client.post(
                self.create_url("/disable"),
                json={"password": "password"}
            )
        
        assert missing_code_response.status_code == 400
        assert "code" in missing_code_response.json().get("detail", "").lower()
        
        # Test disabling MFA with invalid verification code
        with mock_webui_user(id=user.id):
            invalid_code_response = self.fast_api_client.post(
                self.create_url("/disable"),
                json={"password": "password", "code": "123456"}
            )
        
        assert invalid_code_response.status_code == 400
        
        # Now disable MFA with both valid verification code and password
        totp = pyotp.TOTP(secret)
        new_valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            disable_response = self.fast_api_client.post(
                self.create_url("/disable"),
                json={"password": "password", "code": new_valid_code}
            )
        
        assert disable_response.status_code == 200
        assert disable_response.json()["disabled"] is True
        
        # Verify MFA is now disabled in the database
        auth = self.auths.get_auth_by_id(user.id)
        assert auth.mfa_enabled is False
        assert auth.mfa_secret is None
        assert auth.backup_codes is None
        
    def test_regenerate_backup_codes(self):
        """Test regenerating backup codes"""
        user = self.auths.insert_new_auth(
            email="john.doe@openwebui.com",
            password=self.get_password_hash("password"),
            name="John Doe",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up and enable MFA for this user
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        original_backup_codes = enable_response.json()["backup_codes"]
        
        # Regenerate backup codes
        with mock_webui_user(id=user.id):
            regen_response = self.fast_api_client.post(
                self.create_url("/backup-codes"),
                json={"password": "password"}
            )
        
        assert regen_response.status_code == 200
        new_backup_codes = regen_response.json()["backup_codes"]
        assert len(new_backup_codes) > 0
        assert new_backup_codes != original_backup_codes