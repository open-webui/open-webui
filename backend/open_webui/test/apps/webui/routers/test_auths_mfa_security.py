from open_webui.test.util.abstract_integration_test import AbstractPostgresTest
from open_webui.test.util.mock_user import mock_webui_user
import pyotp
import json
import time
import re


class TestAuthsMFASecurity(AbstractPostgresTest):
    BASE_PATH = "/api/v1/auths/mfa"

    def setup_class(cls):
        super().setup_class()
        from open_webui.models.auths import Auths
        from open_webui.models.users import Users
        from open_webui.utils.auth import get_password_hash
        from open_webui.utils.auth_mfa import generate_backup_codes, hash_backup_code

        cls.users = Users
        cls.auths = Auths
        cls.get_password_hash = get_password_hash
        cls.generate_backup_codes = generate_backup_codes
        cls.hash_backup_code = hash_backup_code

    def _create_user_with_mfa(self):
        """Create a test user with MFA enabled and return the user, secret and first backup code"""
        user = self.auths.insert_new_auth(
            email="security.test@openwebui.com",
            password=self.get_password_hash("password"),
            name="Security Test",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up MFA
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Enable MFA
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code}
            )
        
        backup_codes = enable_response.json()["backup_codes"]
        first_backup_code = backup_codes[0]
        
        return user, secret, first_backup_code

    def test_standardized_error_message_invalid_totp(self):
        """Test consistent error messages for invalid TOTP codes to prevent enumeration attacks"""
        user, secret, _ = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Try with various invalid codes
        test_codes = ["000000", "111111", "invalid", "12345", "abcdef", "000001"]
        error_messages = set()
        
        for code in test_codes:
            mfa_verify_response = self.fast_api_client.post(
                self.create_url("/verify"),
                json={"code": code},
                cookies={"partial_token": cookies["partial_token"]}
            )
            
            assert mfa_verify_response.status_code == 400
            error_messages.add(mfa_verify_response.json().get("message", ""))
        
        # All error messages should be the same, regardless of why the code was invalid
        assert len(error_messages) == 1, "Error messages are not standardized"
        
    def test_standardized_error_message_invalid_backup(self):
        """Test consistent error messages for invalid backup codes to prevent enumeration attacks"""
        user, secret, _ = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Try with various invalid backup codes
        test_codes = ["ABCD-1234", "1111-2222", "AAAA-BBBB", "XXXX-YYYY", "AB12-CD34"]
        error_messages = set()
        
        for code in test_codes:
            mfa_verify_response = self.fast_api_client.post(
                self.create_url("/verify"),
                json={"code": code},
                cookies={"partial_token": cookies["partial_token"]}
            )
            
            assert mfa_verify_response.status_code == 400
            error_messages.add(mfa_verify_response.json().get("message", ""))
        
        # All error messages should be the same, regardless of whether the backup code format was valid
        assert len(error_messages) == 1, "Error messages are not standardized"

    def test_prevent_token_reuse(self):
        """Test that partial tokens cannot be reused after a successful verification"""
        user, secret, backup_code = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        partial_token = cookies["partial_token"]
        
        # First verification attempt - should succeed
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        mfa_verify_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_code},
            cookies={"partial_token": partial_token}
        )
        
        assert mfa_verify_response.status_code == 200
        
        # Try to reuse the same partial token - should fail
        time.sleep(1)  # Ensure we're not hitting rate limits
        totp = pyotp.TOTP(secret)
        new_valid_code = totp.now()
        
        reuse_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": new_valid_code},
            cookies={"partial_token": partial_token}
        )
        
        assert reuse_response.status_code == 401, "Partial token reuse should be prevented"

    def test_code_time_window(self):
        """Test that TOTP codes expire within the expected time window"""
        user = self.auths.insert_new_auth(
            email="security.test@openwebui.com",
            password=self.get_password_hash("password"),
            name="Security Test",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up MFA
        with mock_webui_user(id=user.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret = setup_response.json()["secret"]
        
        # Create a TOTP object
        totp = pyotp.TOTP(secret)
        
        # Get current time
        now = int(time.time())
        
        # Generate a TOTP code for 30 seconds ago (should still be valid within the default window)
        time_30_sec_ago = now - 30
        valid_code_30_sec_ago = totp.at(time_30_sec_ago)
        
        # Generate a TOTP code for 60 seconds ago (should be invalid)
        time_60_sec_ago = now - 60
        invalid_code_60_sec_ago = totp.at(time_60_sec_ago)
        
        # Enable MFA with the code from 30 seconds ago (should work)
        with mock_webui_user(id=user.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code_30_sec_ago}
            )
        
        assert enable_response.status_code == 200
        
        # Now use the other user to test the 60 second code
        user2 = self.auths.insert_new_auth(
            email="security.test2@openwebui.com",
            password=self.get_password_hash("password"),
            name="Security Test 2",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up MFA for the second user
        with mock_webui_user(id=user2.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret2 = setup_response.json()["secret"]
        totp2 = pyotp.TOTP(secret2)
        
        # Try to enable MFA with the code from 60 seconds ago (should fail)
        with mock_webui_user(id=user2.id):
            enable_response = self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": totp2.at(time_60_sec_ago)}
            )
        
        assert enable_response.status_code == 400

    def test_backup_code_format_validation(self):
        """Test validation of backup code format"""
        user, secret, valid_backup_code = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Test with wrong formats
        invalid_formats = [
            "ABCD1234",         # No hyphen
            "ABCD-12345",       # Too long second part
            "ABC-DEFG",         # Too short first part, correct second part
            "ABCDE-FGHI",       # Too long both parts
            "AB-CD",            # Too short both parts
            valid_backup_code.lower(),  # Lowercase should still work because of normalization
        ]
        
        # The lowercase valid code should work
        lowercase_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_backup_code.lower()},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert lowercase_response.status_code == 200
        
        # Now test the invalid formats with a new signin
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        for invalid_format in invalid_formats[:4]:  # Skip the lowercase valid code
            response = self.fast_api_client.post(
                self.create_url("/verify"),
                json={"code": invalid_format},
                cookies={"partial_token": cookies["partial_token"]}
            )
            
            assert response.status_code == 400, f"Code {invalid_format} should be rejected"

    def test_missing_or_empty_backup_codes(self):
        """Test handling of missing or empty backup codes"""
        # This test verifies that the API properly handles the case when backup codes are missing/empty
        user = self.auths.insert_new_auth(
            email="security.test@openwebui.com",
            password=self.get_password_hash("password"),
            name="Security Test",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Let's manually enable MFA but set backup_codes to None to simulate missing backup codes
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
        
        # Now manually update the database to remove backup codes
        auth = self.auths.get_auth_by_id(user.id)
        auth.backup_codes = None
        from open_webui.internal.db import Session
        Session.commit()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Try to verify with a made-up backup code
        backup_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": "ABCD-1234"},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert backup_response.status_code == 400
        
        # Now try with a valid TOTP code, which should still work
        valid_totp = totp.now()
        totp_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_totp},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert totp_response.status_code == 200

    def test_token_contains_required_user_data(self):
        """Test that the generated token contains the required user data"""
        user, secret, _ = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Verify with valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        mfa_verify_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_code},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        assert mfa_verify_response.status_code == 200
        verify_data = mfa_verify_response.json()
        
        # Check that the response contains the required fields
        assert "token" in verify_data
        assert "id" in verify_data
        assert "token_type" in verify_data
        assert verify_data["token_type"] == "bearer"
        assert verify_data["id"] == user.id
        
        # Check JWT format (simple validation)
        token = verify_data["token"]
        assert len(token.split(".")) == 3, "Token should be in JWT format with 3 parts"
        
        # Verify token is also set in cookies
        response_cookies = mfa_verify_response.cookies
        assert "token" in response_cookies

    def test_multiple_failed_verifications(self):
        """Test behavior after multiple failed verification attempts"""
        user, secret, _ = self._create_user_with_mfa()
        
        # Sign in to get the partial token
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        cookies = signin_response.cookies
        
        # Try multiple invalid codes to see if any rate limiting or lockout occurs
        # (Note: This is testing current behavior, not necessarily ideal behavior)
        error_messages = []
        
        for i in range(10):
            invalid_code = f"{i:06d}"  # Format as 6 digits
            response = self.fast_api_client.post(
                self.create_url("/verify"),
                json={"code": invalid_code},
                cookies={"partial_token": cookies["partial_token"]}
            )
            
            assert response.status_code == 400
            error_messages.append(response.json().get("message", ""))
            time.sleep(0.1)  # Small delay to prevent overwhelming the server
        
        # A valid TOTP code should still work after failed attempts
        # (Ideally, the system should have some rate limiting, but we're testing current behavior)
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        success_response = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_code},
            cookies={"partial_token": cookies["partial_token"]}
        )
        
        # Current behavior should allow this to succeed
        # In an enhanced version, there might be rate limiting or account lockout after multiple failures
        assert success_response.status_code == 200

    def test_concurrency_different_users(self):
        """Test concurrent MFA operations with different users"""
        # Set up two users with MFA
        user1, secret1, _ = self._create_user_with_mfa()
        
        user2 = self.auths.insert_new_auth(
            email="security.test2@openwebui.com",
            password=self.get_password_hash("password"),
            name="Security Test 2",
            profile_image_url="/user.png",
            role="user",
        )
        
        # Set up MFA for second user
        with mock_webui_user(id=user2.id):
            setup_response = self.fast_api_client.post(self.create_url("/setup"))
        
        secret2 = setup_response.json()["secret"]
        totp2 = pyotp.TOTP(secret2)
        valid_code2 = totp2.now()
        
        with mock_webui_user(id=user2.id):
            self.fast_api_client.post(
                self.create_url("/enable"),
                json={"code": valid_code2}
            )
        
        # Sign in with both users to get partial tokens
        signin_response1 = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        signin_response2 = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test2@openwebui.com", "password": "password"}
        )
        
        cookies1 = signin_response1.cookies
        cookies2 = signin_response2.cookies
        
        # Verify both users can complete MFA verification
        totp1 = pyotp.TOTP(secret1)
        valid_code1 = totp1.now()
        
        valid_code2 = totp2.now()
        
        verify_response1 = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_code1},
            cookies={"partial_token": cookies1["partial_token"]}
        )
        
        verify_response2 = self.fast_api_client.post(
            self.create_url("/verify"),
            json={"code": valid_code2},
            cookies={"partial_token": cookies2["partial_token"]}
        )
        
        assert verify_response1.status_code == 200
        assert verify_response2.status_code == 200
        
        # Verify each user got their own token with correct ID
        assert verify_response1.json()["id"] == user1.id
        assert verify_response2.json()["id"] == user2.id
        
    def test_admin_disable_mfa(self):
        """Test that an admin can disable MFA for another user"""
        # Create a regular user with MFA enabled
        user, secret, _ = self._create_user_with_mfa()
        
        # Create an admin user
        admin_user = self.auths.insert_new_auth(
            email="admin@openwebui.com",
            password=self.get_password_hash("admin_password"),
            name="Admin User",
            profile_image_url="/user.png",
            role="admin",
        )
        
        # Verify user has MFA enabled
        with self.fast_api_client.app.dependency_overrides.get(mock_webui_user)(id=user.id):
            user_auth = self.auths.get_auth_by_id(user.id)
            assert user_auth.mfa_enabled is True
        
        # Admin disables MFA for the user
        with mock_webui_user(id=admin_user.id, role="admin"):
            response = self.fast_api_client.post(
                self.create_url("/admin/disable"),
                json={"user_id": user.id}
            )
            
            assert response.status_code == 200
            assert response.json()["disabled"] is True
        
        # Verify MFA is now disabled for the user
        with self.fast_api_client.app.dependency_overrides.get(mock_webui_user)(id=user.id):
            user_auth = self.auths.get_auth_by_id(user.id)
            assert user_auth.mfa_enabled is False
            
        # Regular user should no longer be able to use MFA
        signin_response = self.fast_api_client.post(
            "/api/v1/auths/signin",
            json={"email": "security.test@openwebui.com", "password": "password"}
        )
        
        # Login should complete normally without MFA verification
        assert signin_response.status_code == 200
        assert "partial_token" not in signin_response.cookies
        assert "mfa_required" not in signin_response.json() or not signin_response.json()["mfa_required"]

    def test_invalid_partial_token(self):
        """Test verification with invalid or malformed partial tokens"""
        # Create a user with MFA
        user, secret, _ = self._create_user_with_mfa()
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Test with various invalid tokens
        test_cases = [
            {"token": "invalid-token", "description": "random string"},
            {"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", "description": "valid JWT but wrong signature"},
            {"token": None, "description": "missing token"},
            {"token": "", "description": "empty token"},
            {"token": "partial_", "description": "malformed token prefix"},
        ]
        
        for test_case in test_cases:
            if test_case["token"] is None:
                cookies = {}
            else:
                cookies = {"partial_token": test_case["token"]}
                
            response = self.fast_api_client.post(
                self.create_url("/verify"),
                json={"code": valid_code},
                cookies=cookies
            )
            
            assert response.status_code in [400, 401], f"Failed with {test_case['description']}"