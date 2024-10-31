import base64
import logging
import mimetypes
import uuid

import aiohttp
from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
from fastapi import (
    HTTPException,
    status,
)
from starlette.responses import RedirectResponse

from open_webui.apps.webui.models.auths import Auths
from open_webui.apps.webui.models.users import Users
from open_webui.config import (
    DEFAULT_USER_ROLE,
    ENABLE_OAUTH_SIGNUP,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PROVIDERS,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    OAUTH_ROLES_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    WEBHOOK_URL,
    JWT_EXPIRES_IN,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import WEBUI_SESSION_COOKIE_SAME_SITE, WEBUI_SESSION_COOKIE_SECURE
from open_webui.utils.misc import parse_duration
from open_webui.utils.utils import get_password_hash, create_token
from open_webui.utils.webhook import post_webhook

log = logging.getLogger(__name__)

auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_OAUTH_SIGNUP = ENABLE_OAUTH_SIGNUP
auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL = OAUTH_MERGE_ACCOUNTS_BY_EMAIL
auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
auth_manager_config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
auth_manager_config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM
auth_manager_config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
auth_manager_config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
auth_manager_config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
auth_manager_config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES
auth_manager_config.WEBHOOK_URL = WEBHOOK_URL
auth_manager_config.JWT_EXPIRES_IN = JWT_EXPIRES_IN


class OAuthManager:
    def __init__(self):
        self.oauth = OAuth()
        for provider_name, provider_config in OAUTH_PROVIDERS.items():
            self.oauth.register(
                name=provider_name,
                client_id=provider_config["client_id"],
                client_secret=provider_config["client_secret"],
                server_metadata_url=provider_config["server_metadata_url"],
                client_kwargs={
                    "scope": provider_config["scope"],
                },
                redirect_uri=provider_config["redirect_uri"],
            )

    def get_client(self, provider_name):
        return self.oauth.create_client(provider_name)

    def get_user_role(self, user, user_data):
        if user and Users.get_num_users() == 1:
            # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
            return "admin"
        if not user and Users.get_num_users() == 0:
            # If there are no users, assign the role "admin", as the first user will be an admin
            return "admin"

        if auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT:
            oauth_claim = auth_manager_config.OAUTH_ROLES_CLAIM
            oauth_allowed_roles = auth_manager_config.OAUTH_ALLOWED_ROLES
            oauth_admin_roles = auth_manager_config.OAUTH_ADMIN_ROLES
            oauth_roles = None
            role = "pending"  # Default/fallback role if no matching roles are found

            # Next block extracts the roles from the user data, accepting nested claims of any depth
            if oauth_claim and oauth_allowed_roles and oauth_admin_roles:
                claim_data = user_data
                nested_claims = oauth_claim.split(".")
                for nested_claim in nested_claims:
                    claim_data = claim_data.get(nested_claim, {})
                oauth_roles = claim_data if isinstance(claim_data, list) else None

            # If any roles are found, check if they match the allowed or admin roles
            if oauth_roles:
                # If role management is enabled, and matching roles are provided, use the roles
                for allowed_role in oauth_allowed_roles:
                    # If the user has any of the allowed roles, assign the role "user"
                    if allowed_role in oauth_roles:
                        role = "user"
                        break
                for admin_role in oauth_admin_roles:
                    # If the user has any of the admin roles, assign the role "admin"
                    if admin_role in oauth_roles:
                        role = "admin"
                        break
        else:
            if not user:
                # If role management is disabled, use the default role for new users
                role = auth_manager_config.DEFAULT_USER_ROLE
            else:
                # If role management is disabled, use the existing role for existing users
                role = user.role

        return role

    async def handle_login(self, provider, request):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        # If the provider has a custom redirect URL, use that, otherwise automatically generate one
        redirect_uri = OAUTH_PROVIDERS[provider].get("redirect_uri") or request.url_for(
            "oauth_callback", provider=provider
        )
        client = self.get_client(provider)
        if client is None:
            raise HTTPException(404)
        return await client.authorize_redirect(request, redirect_uri)

    async def handle_callback(self, provider, request, response):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        client = self.get_client(provider)
        try:
            token = await client.authorize_access_token(request)
        except Exception as e:
            log.warning(f"OAuth callback error: {e}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        user_data: UserInfo = token["userinfo"]
        if not user_data:
            user_data: UserInfo = await client.userinfo(token=token)
        if not user_data:
            log.warning(f"OAuth callback failed, user data is missing: {token}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        sub = user_data.get("sub")
        if not sub:
            log.warning(f"OAuth callback failed, sub is missing: {user_data}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        provider_sub = f"{provider}@{sub}"
        email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
        email = user_data.get(email_claim, "").lower()
        # We currently mandate that email addresses are provided
        if not email:
            log.warning(f"OAuth callback failed, email is missing: {user_data}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        # Check if the user exists
        user = Users.get_user_by_oauth_sub(provider_sub)

        if not user:
            # If the user does not exist, check if merging is enabled
            if auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL:
                # Check if the user exists by email
                user = Users.get_user_by_email(email)
                if user:
                    # Update the user with the new oauth sub
                    Users.update_user_oauth_sub_by_id(user.id, provider_sub)

        if user:
            determined_role = self.get_user_role(user, user_data)
            if user.role != determined_role:
                Users.update_user_role_by_id(user.id, determined_role)

        if not user:
            # If the user does not exist, check if signups are enabled
            if auth_manager_config.ENABLE_OAUTH_SIGNUP:
                # Check if an existing user with the same email already exists
                existing_user = Users.get_user_by_email(
                    user_data.get("email", "").lower()
                )
                if existing_user:
                    raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

                picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                picture_url = user_data.get(picture_claim, "")
                if picture_url:
                    # Download the profile image into a base64 string
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(picture_url) as resp:
                                picture = await resp.read()
                                base64_encoded_picture = base64.b64encode(
                                    picture
                                ).decode("utf-8")
                                guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                                if guessed_mime_type is None:
                                    # assume JPG, browsers are tolerant enough of image formats
                                    guessed_mime_type = "image/jpeg"
                                picture_url = f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                    except Exception as e:
                        log.error(
                            f"Error downloading profile image '{picture_url}': {e}"
                        )
                        picture_url = ""
                if not picture_url:
                    picture_url = "/user.png"
                username_claim = auth_manager_config.OAUTH_USERNAME_CLAIM

                role = self.get_user_role(None, user_data)

                user = Auths.insert_new_auth(
                    email=email,
                    password=get_password_hash(
                        str(uuid.uuid4())
                    ),  # Random password, not used
                    name=user_data.get(username_claim, "User"),
                    profile_image_url=picture_url,
                    role=role,
                    oauth_sub=provider_sub,
                )

                if auth_manager_config.WEBHOOK_URL:
                    post_webhook(
                        auth_manager_config.WEBHOOK_URL,
                        auth_manager_config.WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        {
                            "action": "signup",
                            "message": auth_manager_config.WEBHOOK_MESSAGES.USER_SIGNUP(
                                user.name
                            ),
                            "user": user.model_dump_json(exclude_none=True),
                        },
                    )
            else:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
                )

        jwt_token = create_token(
            data={"id": user.id},
            expires_delta=parse_duration(auth_manager_config.JWT_EXPIRES_IN),
        )

        # Set the cookie token
        response.set_cookie(
            key="token",
            value=jwt_token,
            httponly=True,  # Ensures the cookie is not accessible via JavaScript
            samesite=WEBUI_SESSION_COOKIE_SAME_SITE,
            secure=WEBUI_SESSION_COOKIE_SECURE,
        )

        # Redirect back to the frontend with the JWT token
        redirect_url = f"{request.base_url}auth#token={jwt_token}"
        return RedirectResponse(url=redirect_url)


oauth_manager = OAuthManager()
