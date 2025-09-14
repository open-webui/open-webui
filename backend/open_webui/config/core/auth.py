import os
from authlib.integrations.starlette_client import OAuth
from open_webui.config.core.base import PersistentConfig
from open_webui.env import log

####################################
# WebUI Auth
####################################

ENABLE_API_KEY = PersistentConfig(
    "ENABLE_API_KEY",
    "auth.api_key.enable",
    os.environ.get("ENABLE_API_KEY", "True").lower() == "true",
)

ENABLE_API_KEY_ENDPOINT_RESTRICTIONS = PersistentConfig(
    "ENABLE_API_KEY_ENDPOINT_RESTRICTIONS",
    "auth.api_key.endpoint_restrictions",
    os.environ.get("ENABLE_API_KEY_ENDPOINT_RESTRICTIONS", "False").lower() == "true",
)

API_KEY_ALLOWED_ENDPOINTS = PersistentConfig(
    "API_KEY_ALLOWED_ENDPOINTS",
    "auth.api_key.allowed_endpoints",
    os.environ.get("API_KEY_ALLOWED_ENDPOINTS", ""),
)

JWT_EXPIRES_IN = PersistentConfig(
    "JWT_EXPIRES_IN", "auth.jwt_expiry", os.environ.get("JWT_EXPIRES_IN", "-1")
)

SHOW_ADMIN_DETAILS = PersistentConfig(
    "SHOW_ADMIN_DETAILS",
    "auth.admin.show",
    os.environ.get("SHOW_ADMIN_DETAILS", "true").lower() == "true",
)

ADMIN_EMAIL = PersistentConfig(
    "ADMIN_EMAIL",
    "auth.admin.email",
    os.environ.get("ADMIN_EMAIL", None),
)

####################################
# OAuth config
####################################

ENABLE_OAUTH_PERSISTENT_CONFIG = (
    os.environ.get("ENABLE_OAUTH_PERSISTENT_CONFIG", "False").lower() == "true"
)

ENABLE_OAUTH_SIGNUP = PersistentConfig(
    "ENABLE_OAUTH_SIGNUP",
    "oauth.enable_signup",
    os.environ.get("ENABLE_OAUTH_SIGNUP", "False").lower() == "true",
)

OAUTH_MERGE_ACCOUNTS_BY_EMAIL = PersistentConfig(
    "OAUTH_MERGE_ACCOUNTS_BY_EMAIL",
    "oauth.merge_accounts_by_email",
    os.environ.get("OAUTH_MERGE_ACCOUNTS_BY_EMAIL", "False").lower() == "true",
)

OAUTH_PROVIDERS = {}

####################################
# Google OAuth config
####################################

GOOGLE_CLIENT_ID = PersistentConfig(
    "GOOGLE_CLIENT_ID",
    "oauth.google.client_id",
    os.environ.get("GOOGLE_CLIENT_ID", ""),
)

GOOGLE_CLIENT_SECRET = PersistentConfig(
    "GOOGLE_CLIENT_SECRET",
    "oauth.google.client_secret",
    os.environ.get("GOOGLE_CLIENT_SECRET", ""),
)

GOOGLE_OAUTH_SCOPE = PersistentConfig(
    "GOOGLE_OAUTH_SCOPE",
    "oauth.google.scope",
    os.environ.get("GOOGLE_OAUTH_SCOPE", "openid email profile"),
)

GOOGLE_REDIRECT_URI = PersistentConfig(
    "GOOGLE_REDIRECT_URI",
    "oauth.google.redirect_uri",
    os.environ.get("GOOGLE_REDIRECT_URI", ""),
)

####################################
# Microsoft OAuth config
####################################

MICROSOFT_CLIENT_ID = PersistentConfig(
    "MICROSOFT_CLIENT_ID",
    "oauth.microsoft.client_id",
    os.environ.get("MICROSOFT_CLIENT_ID", ""),
)

MICROSOFT_CLIENT_SECRET = PersistentConfig(
    "MICROSOFT_CLIENT_SECRET",
    "oauth.microsoft.client_secret",
    os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
)

MICROSOFT_CLIENT_TENANT_ID = PersistentConfig(
    "MICROSOFT_CLIENT_TENANT_ID",
    "oauth.microsoft.tenant_id",
    os.environ.get("MICROSOFT_CLIENT_TENANT_ID", ""),
)

MICROSOFT_CLIENT_LOGIN_BASE_URL = PersistentConfig(
    "MICROSOFT_CLIENT_LOGIN_BASE_URL",
    "oauth.microsoft.login_base_url",
    os.environ.get(
        "MICROSOFT_CLIENT_LOGIN_BASE_URL", "https://login.microsoftonline.com"
    ),
)

MICROSOFT_CLIENT_PICTURE_URL = PersistentConfig(
    "MICROSOFT_CLIENT_PICTURE_URL",
    "oauth.microsoft.picture_url",
    os.environ.get(
        "MICROSOFT_CLIENT_PICTURE_URL",
        "https://graph.microsoft.com/v1.0/me/photo/$value",
    ),
)

MICROSOFT_OAUTH_SCOPE = PersistentConfig(
    "MICROSOFT_OAUTH_SCOPE",
    "oauth.microsoft.scope",
    os.environ.get("MICROSOFT_OAUTH_SCOPE", "openid email profile"),
)

MICROSOFT_REDIRECT_URI = PersistentConfig(
    "MICROSOFT_REDIRECT_URI",
    "oauth.microsoft.redirect_uri",
    os.environ.get("MICROSOFT_REDIRECT_URI", ""),
)

####################################
# GitHub OAuth config
####################################

GITHUB_CLIENT_ID = PersistentConfig(
    "GITHUB_CLIENT_ID",
    "oauth.github.client_id",
    os.environ.get("GITHUB_CLIENT_ID", ""),
)

GITHUB_CLIENT_SECRET = PersistentConfig(
    "GITHUB_CLIENT_SECRET",
    "oauth.github.client_secret",
    os.environ.get("GITHUB_CLIENT_SECRET", ""),
)

GITHUB_CLIENT_SCOPE = PersistentConfig(
    "GITHUB_CLIENT_SCOPE",
    "oauth.github.scope",
    os.environ.get("GITHUB_CLIENT_SCOPE", "user:email"),
)

GITHUB_CLIENT_REDIRECT_URI = PersistentConfig(
    "GITHUB_CLIENT_REDIRECT_URI",
    "oauth.github.redirect_uri",
    os.environ.get("GITHUB_CLIENT_REDIRECT_URI", ""),
)

####################################
# Feishu OAuth config
####################################

FEISHU_CLIENT_ID = PersistentConfig(
    "FEISHU_CLIENT_ID",
    "oauth.feishu.client_id",
    os.environ.get("FEISHU_CLIENT_ID", ""),
)

FEISHU_CLIENT_SECRET = PersistentConfig(
    "FEISHU_CLIENT_SECRET",
    "oauth.feishu.client_secret",
    os.environ.get("FEISHU_CLIENT_SECRET", ""),
)

FEISHU_OAUTH_SCOPE = PersistentConfig(
    "FEISHU_OAUTH_SCOPE",
    "oauth.feishu.scope",
    os.environ.get("FEISHU_OAUTH_SCOPE", "contact:user.base:readonly"),
)

FEISHU_REDIRECT_URI = PersistentConfig(
    "FEISHU_REDIRECT_URI",
    "oauth.feishu.redirect_uri",
    os.environ.get("FEISHU_REDIRECT_URI", ""),
)

####################################
# Generic OpenID Connect config
####################################

OAUTH_CLIENT_ID = PersistentConfig(
    "OAUTH_CLIENT_ID",
    "oauth.oidc.client_id",
    os.environ.get("OAUTH_CLIENT_ID", ""),
)

OAUTH_CLIENT_SECRET = PersistentConfig(
    "OAUTH_CLIENT_SECRET",
    "oauth.oidc.client_secret",
    os.environ.get("OAUTH_CLIENT_SECRET", ""),
)

OPENID_PROVIDER_URL = PersistentConfig(
    "OPENID_PROVIDER_URL",
    "oauth.oidc.provider_url",
    os.environ.get("OPENID_PROVIDER_URL", ""),
)

OPENID_REDIRECT_URI = PersistentConfig(
    "OPENID_REDIRECT_URI",
    "oauth.oidc.redirect_uri",
    os.environ.get("OPENID_REDIRECT_URI", ""),
)

OAUTH_SCOPES = PersistentConfig(
    "OAUTH_SCOPES",
    "oauth.oidc.scopes",
    os.environ.get("OAUTH_SCOPES", "openid email profile"),
)

OAUTH_TIMEOUT = PersistentConfig(
    "OAUTH_TIMEOUT",
    "oauth.oidc.oauth_timeout",
    os.environ.get("OAUTH_TIMEOUT", ""),
)

OAUTH_TOKEN_ENDPOINT_AUTH_METHOD = PersistentConfig(
    "OAUTH_TOKEN_ENDPOINT_AUTH_METHOD",
    "oauth.oidc.token_endpoint_auth_method",
    os.environ.get("OAUTH_TOKEN_ENDPOINT_AUTH_METHOD", None),
)

OAUTH_CODE_CHALLENGE_METHOD = PersistentConfig(
    "OAUTH_CODE_CHALLENGE_METHOD",
    "oauth.oidc.code_challenge_method",
    os.environ.get("OAUTH_CODE_CHALLENGE_METHOD", None),
)

OAUTH_PROVIDER_NAME = PersistentConfig(
    "OAUTH_PROVIDER_NAME",
    "oauth.oidc.provider_name",
    os.environ.get("OAUTH_PROVIDER_NAME", "SSO"),
)

OAUTH_SUB_CLAIM = PersistentConfig(
    "OAUTH_SUB_CLAIM",
    "oauth.oidc.sub_claim",
    os.environ.get("OAUTH_SUB_CLAIM", None),
)

OAUTH_USERNAME_CLAIM = PersistentConfig(
    "OAUTH_USERNAME_CLAIM",
    "oauth.oidc.username_claim",
    os.environ.get("OAUTH_USERNAME_CLAIM", "name"),
)

OAUTH_PICTURE_CLAIM = PersistentConfig(
    "OAUTH_PICTURE_CLAIM",
    "oauth.oidc.avatar_claim",
    os.environ.get("OAUTH_PICTURE_CLAIM", "picture"),
)

OAUTH_EMAIL_CLAIM = PersistentConfig(
    "OAUTH_EMAIL_CLAIM",
    "oauth.oidc.email_claim",
    os.environ.get("OAUTH_EMAIL_CLAIM", "email"),
)

OAUTH_GROUPS_CLAIM = PersistentConfig(
    "OAUTH_GROUPS_CLAIM",
    "oauth.oidc.group_claim",
    os.environ.get("OAUTH_GROUPS_CLAIM", os.environ.get("OAUTH_GROUP_CLAIM", "groups")),
)

####################################
# OAuth role and group management
####################################

ENABLE_OAUTH_ROLE_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_ROLE_MANAGEMENT",
    "oauth.enable_role_mapping",
    os.environ.get("ENABLE_OAUTH_ROLE_MANAGEMENT", "False").lower() == "true",
)

ENABLE_OAUTH_GROUP_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_GROUP_MANAGEMENT",
    "oauth.enable_group_mapping",
    os.environ.get("ENABLE_OAUTH_GROUP_MANAGEMENT", "False").lower() == "true",
)

ENABLE_OAUTH_GROUP_CREATION = PersistentConfig(
    "ENABLE_OAUTH_GROUP_CREATION",
    "oauth.enable_group_creation",
    os.environ.get("ENABLE_OAUTH_GROUP_CREATION", "False").lower() == "true",
)

OAUTH_BLOCKED_GROUPS = PersistentConfig(
    "OAUTH_BLOCKED_GROUPS",
    "oauth.blocked_groups",
    os.environ.get("OAUTH_BLOCKED_GROUPS", "[]"),
)

OAUTH_ROLES_CLAIM = PersistentConfig(
    "OAUTH_ROLES_CLAIM",
    "oauth.roles_claim",
    os.environ.get("OAUTH_ROLES_CLAIM", "roles"),
)

OAUTH_ALLOWED_ROLES = PersistentConfig(
    "OAUTH_ALLOWED_ROLES",
    "oauth.allowed_roles",
    [
        role.strip()
        for role in os.environ.get("OAUTH_ALLOWED_ROLES", "user,admin").split(",")
    ],
)

OAUTH_ADMIN_ROLES = PersistentConfig(
    "OAUTH_ADMIN_ROLES",
    "oauth.admin_roles",
    [role.strip() for role in os.environ.get("OAUTH_ADMIN_ROLES", "admin").split(",")],
)

OAUTH_ALLOWED_DOMAINS = PersistentConfig(
    "OAUTH_ALLOWED_DOMAINS",
    "oauth.allowed_domains",
    [
        domain.strip()
        for domain in os.environ.get("OAUTH_ALLOWED_DOMAINS", "*").split(",")
    ],
)

OAUTH_UPDATE_PICTURE_ON_LOGIN = PersistentConfig(
    "OAUTH_UPDATE_PICTURE_ON_LOGIN",
    "oauth.update_picture_on_login",
    os.environ.get("OAUTH_UPDATE_PICTURE_ON_LOGIN", "False").lower() == "true",
)


def load_oauth_providers():
    OAUTH_PROVIDERS.clear()
    if GOOGLE_CLIENT_ID.value and GOOGLE_CLIENT_SECRET.value:

        def google_oauth_register(client: OAuth):
            client.register(
                name="google",
                client_id=GOOGLE_CLIENT_ID.value,
                client_secret=GOOGLE_CLIENT_SECRET.value,
                access_token_url="https://accounts.google.com/o/oauth2/token",
                authorize_url="https://accounts.google.com/o/oauth2/auth",
                api_base_url="https://www.googleapis.com/oauth2/v1/",
                userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
                client_kwargs={
                    "scope": GOOGLE_OAUTH_SCOPE.value,
                    **(
                        {"timeout": int(OAUTH_TIMEOUT.value)}
                        if OAUTH_TIMEOUT.value
                        else {}
                    ),
                },
                redirect_uri=GOOGLE_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["google"] = {
            "redirect_uri": GOOGLE_REDIRECT_URI.value,
            "register": google_oauth_register,
        }

    if (
        MICROSOFT_CLIENT_ID.value
        and MICROSOFT_CLIENT_SECRET.value
        and MICROSOFT_CLIENT_TENANT_ID.value
    ):

        def microsoft_oauth_register(client: OAuth):
            client.register(
                name="microsoft",
                client_id=MICROSOFT_CLIENT_ID.value,
                client_secret=MICROSOFT_CLIENT_SECRET.value,
                access_token_url=f"{MICROSOFT_CLIENT_LOGIN_BASE_URL.value}/{MICROSOFT_CLIENT_TENANT_ID.value}/oauth2/v2.0/token",
                authorize_url=f"{MICROSOFT_CLIENT_LOGIN_BASE_URL.value}/{MICROSOFT_CLIENT_TENANT_ID.value}/oauth2/v2.0/authorize",
                api_base_url="https://graph.microsoft.com/v1.0/",
                userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
                client_kwargs={
                    "scope": MICROSOFT_OAUTH_SCOPE.value,
                    **(
                        {"timeout": int(OAUTH_TIMEOUT.value)}
                        if OAUTH_TIMEOUT.value
                        else {}
                    ),
                },
                redirect_uri=MICROSOFT_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["microsoft"] = {
            "redirect_uri": MICROSOFT_REDIRECT_URI.value,
            "picture_url": MICROSOFT_CLIENT_PICTURE_URL.value,
            "register": microsoft_oauth_register,
        }

    if GITHUB_CLIENT_ID.value and GITHUB_CLIENT_SECRET.value:

        def github_oauth_register(client: OAuth):
            client.register(
                name="github",
                client_id=GITHUB_CLIENT_ID.value,
                client_secret=GITHUB_CLIENT_SECRET.value,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com/",
                userinfo_endpoint="https://api.github.com/user",
                client_kwargs={
                    "scope": GITHUB_CLIENT_SCOPE.value,
                    **(
                        {"timeout": int(OAUTH_TIMEOUT.value)}
                        if OAUTH_TIMEOUT.value
                        else {}
                    ),
                },
                redirect_uri=GITHUB_CLIENT_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["github"] = {
            "redirect_uri": GITHUB_CLIENT_REDIRECT_URI.value,
            "register": github_oauth_register,
            "sub_claim": "id",
        }

    if (
        OAUTH_CLIENT_ID.value
        and (OAUTH_CLIENT_SECRET.value or OAUTH_CODE_CHALLENGE_METHOD.value)
        and OPENID_PROVIDER_URL.value
    ):

        def oidc_oauth_register(client: OAuth):
            client_kwargs = {
                "scope": OAUTH_SCOPES.value,
                **(
                    {
                        "token_endpoint_auth_method": OAUTH_TOKEN_ENDPOINT_AUTH_METHOD.value
                    }
                    if OAUTH_TOKEN_ENDPOINT_AUTH_METHOD.value
                    else {}
                ),
                **(
                    {"timeout": int(OAUTH_TIMEOUT.value)} if OAUTH_TIMEOUT.value else {}
                ),
            }

            if (
                OAUTH_CODE_CHALLENGE_METHOD.value
                and OAUTH_CODE_CHALLENGE_METHOD.value == "S256"
            ):
                client_kwargs["code_challenge_method"] = "S256"
            elif OAUTH_CODE_CHALLENGE_METHOD.value:
                log.warning(
                    f"Unsupported OAUTH_CODE_CHALLENGE_METHOD: {OAUTH_CODE_CHALLENGE_METHOD.value}. Supported methods: S256"
                )

            client.register(
                name="oidc",
                client_id=OAUTH_CLIENT_ID.value,
                client_secret=OAUTH_CLIENT_SECRET.value,
                server_metadata_url=OPENID_PROVIDER_URL.value,
                client_kwargs=client_kwargs,
                redirect_uri=OPENID_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["oidc"] = {
            "name": OAUTH_PROVIDER_NAME.value,
            "redirect_uri": OPENID_REDIRECT_URI.value,
            "register": oidc_oauth_register,
        }

    if FEISHU_CLIENT_ID.value and FEISHU_CLIENT_SECRET.value:

        def feishu_oauth_register(client: OAuth):
            client.register(
                name="feishu",
                client_id=FEISHU_CLIENT_ID.value,
                client_secret=FEISHU_CLIENT_SECRET.value,
                access_token_url="https://open.feishu.cn/open-apis/authen/v2/oauth/token",
                authorize_url="https://accounts.feishu.cn/open-apis/authen/v1/authorize",
                api_base_url="https://open.feishu.cn/open-apis",
                userinfo_endpoint="https://open.feishu.cn/open-apis/authen/v1/user_info",
                client_kwargs={
                    "scope": FEISHU_OAUTH_SCOPE.value,
                    **(
                        {"timeout": int(OAUTH_TIMEOUT.value)}
                        if OAUTH_TIMEOUT.value
                        else {}
                    ),
                },
                redirect_uri=FEISHU_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["feishu"] = {
            "register": feishu_oauth_register,
            "sub_claim": "user_id",
        }

    configured_providers = []
    if GOOGLE_CLIENT_ID.value:
        configured_providers.append("Google")
    if MICROSOFT_CLIENT_ID.value:
        configured_providers.append("Microsoft")
    if GITHUB_CLIENT_ID.value:
        configured_providers.append("GitHub")
    if FEISHU_CLIENT_ID.value:
        configured_providers.append("Feishu")

    if configured_providers and not OPENID_PROVIDER_URL.value:
        provider_list = ", ".join(configured_providers)
        log.warning(
            f"⚠️  OAuth providers configured ({provider_list}) but OPENID_PROVIDER_URL not set - logout will not work!"
        )
        log.warning(
            f"Set OPENID_PROVIDER_URL to your OAuth provider's OpenID Connect discovery endpoint to fix logout functionality."
        )


load_oauth_providers()


####################################
# LDAP
####################################

ENABLE_LDAP = PersistentConfig(
    "ENABLE_LDAP",
    "ldap.enable",
    os.environ.get("ENABLE_LDAP", "false").lower() == "true",
)

LDAP_SERVER_LABEL = PersistentConfig(
    "LDAP_SERVER_LABEL",
    "ldap.server.label",
    os.environ.get("LDAP_SERVER_LABEL", "LDAP Server"),
)

LDAP_SERVER_HOST = PersistentConfig(
    "LDAP_SERVER_HOST",
    "ldap.server.host",
    os.environ.get("LDAP_SERVER_HOST", "localhost"),
)

LDAP_SERVER_PORT = PersistentConfig(
    "LDAP_SERVER_PORT",
    "ldap.server.port",
    int(os.environ.get("LDAP_SERVER_PORT", "389")),
)

LDAP_ATTRIBUTE_FOR_MAIL = PersistentConfig(
    "LDAP_ATTRIBUTE_FOR_MAIL",
    "ldap.server.attribute_for_mail",
    os.environ.get("LDAP_ATTRIBUTE_FOR_MAIL", "mail"),
)

LDAP_ATTRIBUTE_FOR_USERNAME = PersistentConfig(
    "LDAP_ATTRIBUTE_FOR_USERNAME",
    "ldap.server.attribute_for_username",
    os.environ.get("LDAP_ATTRIBUTE_FOR_USERNAME", "uid"),
)

LDAP_APP_DN = PersistentConfig(
    "LDAP_APP_DN", "ldap.server.app_dn", os.environ.get("LDAP_APP_DN", "")
)

LDAP_APP_PASSWORD = PersistentConfig(
    "LDAP_APP_PASSWORD",
    "ldap.server.app_password",
    os.environ.get("LDAP_APP_PASSWORD", ""),
)

LDAP_SEARCH_BASE = PersistentConfig(
    "LDAP_SEARCH_BASE", "ldap.server.users_dn", os.environ.get("LDAP_SEARCH_BASE", "")
)

LDAP_SEARCH_FILTERS = PersistentConfig(
    "LDAP_SEARCH_FILTER",
    "ldap.server.search_filter",
    os.environ.get("LDAP_SEARCH_FILTER", os.environ.get("LDAP_SEARCH_FILTERS", "")),
)

LDAP_USE_TLS = PersistentConfig(
    "LDAP_USE_TLS",
    "ldap.server.use_tls",
    os.environ.get("LDAP_USE_TLS", "True").lower() == "true",
)

LDAP_CA_CERT_FILE = PersistentConfig(
    "LDAP_CA_CERT_FILE",
    "ldap.server.ca_cert_file",
    os.environ.get("LDAP_CA_CERT_FILE", ""),
)

LDAP_VALIDATE_CERT = PersistentConfig(
    "LDAP_VALIDATE_CERT",
    "ldap.server.validate_cert",
    os.environ.get("LDAP_VALIDATE_CERT", "True").lower() == "true",
)

LDAP_CIPHERS = PersistentConfig(
    "LDAP_CIPHERS", "ldap.server.ciphers", os.environ.get("LDAP_CIPHERS", "ALL")
)

# For LDAP Group Management
ENABLE_LDAP_GROUP_MANAGEMENT = PersistentConfig(
    "ENABLE_LDAP_GROUP_MANAGEMENT",
    "ldap.group.enable_management",
    os.environ.get("ENABLE_LDAP_GROUP_MANAGEMENT", "False").lower() == "true",
)

ENABLE_LDAP_GROUP_CREATION = PersistentConfig(
    "ENABLE_LDAP_GROUP_CREATION",
    "ldap.group.enable_creation",
    os.environ.get("ENABLE_LDAP_GROUP_CREATION", "False").lower() == "true",
)

LDAP_ATTRIBUTE_FOR_GROUPS = PersistentConfig(
    "LDAP_ATTRIBUTE_FOR_GROUPS",
    "ldap.server.attribute_for_groups",
    os.environ.get("LDAP_ATTRIBUTE_FOR_GROUPS", "memberOf"),
)
