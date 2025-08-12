import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def oauth_manager():
    from open_webui.utils.oauth import OAuthManager
    return OAuthManager(Mock())


@pytest.fixture
def mock_dependencies():
    with patch('open_webui.utils.oauth.log') as mock_log, \
         patch('open_webui.utils.oauth.Users') as mock_users, \
         patch('open_webui.utils.oauth.auth_manager_config') as mock_config:
        
        mock_users.get_num_users.return_value = 5
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = True
        mock_config.OAUTH_ROLES_CLAIM = "roles"
        mock_config.OAUTH_ALLOWED_ROLES = ["user", "member", "viewer"]
        mock_config.OAUTH_ADMIN_ROLES = ["admin", "administrator", "owner"]
        mock_config.DEFAULT_USER_ROLE = "pending"
        
        yield mock_config, mock_users, mock_log


class TestOAuthClaimTypeConversion:
    """Test OAuth claim type conversion for str and int support"""
    
    def test_claim_as_string_converts_to_list(self, oauth_manager, mock_dependencies):
        mock_config, mock_users, mock_log = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": "member"})
        
        assert role == "user"
        mock_log.debug.assert_any_call("User roles from oauth: ['member']")
    
    def test_claim_as_integer_converts_to_string_list(self, oauth_manager, mock_dependencies):
        mock_config, mock_users, mock_log = mock_dependencies
        mock_config.OAUTH_ALLOWED_ROLES = ["1", "2", "3"]
        
        role = oauth_manager.get_user_role(None, {"roles": 2})
        
        assert role == "user"
        mock_log.debug.assert_any_call("User roles from oauth: ['2']")
    
    def test_claim_as_list_unchanged(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": ["viewer", "member"]})
        
        assert role == "user"
    
    @pytest.mark.parametrize("invalid_value", [
        {"nested": "value"},
        None,
        True,
        False,
        3.14,
        [],
    ])
    def test_invalid_claim_types_return_default(self, oauth_manager, mock_dependencies, invalid_value):
        mock_config, _, _ = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": invalid_value})
        
        assert role == "pending"


class TestOAuthRoleAssignment:
    
    def test_admin_role_takes_precedence(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": ["member", "administrator", "viewer"]})
        
        assert role == "admin"
    
    def test_integer_admin_role(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        mock_config.OAUTH_ADMIN_ROLES = ["1", "99", "100"]
        
        role = oauth_manager.get_user_role(None, {"roles": 99})
        
        assert role == "admin"
    
    def test_string_admin_role(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": "administrator"})
        
        assert role == "admin"
    
    def test_no_matching_roles_returns_default(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        
        role = oauth_manager.get_user_role(None, {"roles": ["unknown", "random"]})
        
        assert role == "pending"


class TestOAuthNestedClaims:
    
    def test_nested_string_claim(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        mock_config.OAUTH_ROLES_CLAIM = "auth.role"
        
        role = oauth_manager.get_user_role(None, {"auth": {"role": "member"}})
        
        assert role == "user"
    
    def test_nested_integer_claim(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        mock_config.OAUTH_ROLES_CLAIM = "auth.level"
        mock_config.OAUTH_ADMIN_ROLES = ["100", "99"]
        
        role = oauth_manager.get_user_role(None, {"auth": {"level": 100}})
        
        assert role == "admin"
    
    def test_deeply_nested_list_claim(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        mock_config.OAUTH_ROLES_CLAIM = "user.permissions.roles"
        
        user_data = {"user": {"permissions": {"roles": ["admin", "member"]}}}
        role = oauth_manager.get_user_role(None, user_data)
        
        assert role == "admin"
    
    def test_missing_nested_path_returns_default(self, oauth_manager, mock_dependencies):
        mock_config, _, _ = mock_dependencies
        mock_config.OAUTH_ROLES_CLAIM = "missing.path.roles"
        
        role = oauth_manager.get_user_role(None, {"other": {"data": "value"}})
        
        assert role == "pending"


class TestSpecialCases:
    
    @patch('open_webui.utils.oauth.log')
    @patch('open_webui.utils.oauth.Users')
    @patch('open_webui.utils.oauth.auth_manager_config')
    def test_single_user_becomes_admin(self, mock_config, mock_users, mock_log, oauth_manager):
        mock_users.get_num_users.return_value = 1
        user = Mock(role="user")
        
        role = oauth_manager.get_user_role(user, {})
        
        assert role == "admin"
    
    @patch('open_webui.utils.oauth.log')
    @patch('open_webui.utils.oauth.Users')
    @patch('open_webui.utils.oauth.auth_manager_config')
    def test_first_user_becomes_admin(self, mock_config, mock_users, mock_log, oauth_manager):
        mock_users.get_num_users.return_value = 0
        
        role = oauth_manager.get_user_role(None, {})
        
        assert role == "admin"
    
    @patch('open_webui.utils.oauth.log')
    @patch('open_webui.utils.oauth.Users')
    @patch('open_webui.utils.oauth.auth_manager_config')
    def test_oauth_disabled_preserves_existing_role(self, mock_config, mock_users, mock_log, oauth_manager):
        mock_users.get_num_users.return_value = 5
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = False
        user = Mock(role="custom_role")
        
        role = oauth_manager.get_user_role(user, {})
        
        assert role == "custom_role"
    
    @patch('open_webui.utils.oauth.log')
    @patch('open_webui.utils.oauth.Users')
    @patch('open_webui.utils.oauth.auth_manager_config')
    def test_oauth_disabled_new_user_gets_default(self, mock_config, mock_users, mock_log, oauth_manager):
        mock_users.get_num_users.return_value = 5
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = False
        mock_config.DEFAULT_USER_ROLE = "pending"
        
        role = oauth_manager.get_user_role(None, {})
        
        assert role == "pending"


@pytest.mark.parametrize("claim_value,allowed_roles,admin_roles,expected_role", [
    ("member", ["user", "member"], ["admin"], "user"),
    ("admin", ["user"], ["admin"], "admin"),
    (1, ["1", "2"], ["99"], "user"),
    (99, ["1", "2"], ["99"], "admin"),
    (["viewer", "admin"], ["viewer"], ["admin"], "admin"),
    ("unknown", ["user"], ["admin"], "pending"),
])
def test_role_mapping(oauth_manager, claim_value, allowed_roles, admin_roles, expected_role):
    with patch('open_webui.utils.oauth.log'), \
         patch('open_webui.utils.oauth.Users') as mock_users, \
         patch('open_webui.utils.oauth.auth_manager_config') as mock_config:
        
        mock_users.get_num_users.return_value = 5
        mock_config.ENABLE_OAUTH_ROLE_MANAGEMENT = True
        mock_config.OAUTH_ROLES_CLAIM = "roles"
        mock_config.OAUTH_ALLOWED_ROLES = allowed_roles
        mock_config.OAUTH_ADMIN_ROLES = admin_roles
        mock_config.DEFAULT_USER_ROLE = "pending"
        
        role = oauth_manager.get_user_role(None, {"roles": claim_value})
        
        assert role == expected_role