import base64
import logging
import mimetypes
import sys
import uuid
import json

import aiohttp
from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
from fastapi import (
    HTTPException,
    status,
)
from starlette.responses import RedirectResponse

from open_webui.models.auths import Auths
from open_webui.models.users import Users
from open_webui.models.groups import Groups, GroupModel, GroupUpdateForm, GroupForm
from open_webui.config import (
    DEFAULT_USER_ROLE,
    ENABLE_OAUTH_SIGNUP,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PROVIDERS,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    ENABLE_OAUTH_GROUP_MANAGEMENT,
    ENABLE_OAUTH_GROUP_CREATION,
    OAUTH_BLOCKED_GROUPS,
    OAUTH_ROLES_CLAIM,
    OAUTH_SUB_CLAIM,
    OAUTH_GROUPS_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    OAUTH_ALLOWED_DOMAINS,
    OAUTH_UPDATE_PICTURE_ON_LOGIN,
    WEBHOOK_URL,
    JWT_EXPIRES_IN,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    WEBUI_NAME,
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
)
from open_webui.utils.misc import parse_duration
from open_webui.utils.auth import get_password_hash, create_token
from open_webui.utils.webhook import post_webhook

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_OAUTH_SIGNUP = ENABLE_OAUTH_SIGNUP
auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL = OAUTH_MERGE_ACCOUNTS_BY_EMAIL
auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT = ENABLE_OAUTH_GROUP_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_CREATION = ENABLE_OAUTH_GROUP_CREATION
auth_manager_config.OAUTH_BLOCKED_GROUPS = OAUTH_BLOCKED_GROUPS
auth_manager_config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
auth_manager_config.OAUTH_SUB_CLAIM = OAUTH_SUB_CLAIM
auth_manager_config.OAUTH_GROUPS_CLAIM = OAUTH_GROUPS_CLAIM
auth_manager_config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM
auth_manager_config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
auth_manager_config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
auth_manager_config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
auth_manager_config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES
auth_manager_config.OAUTH_ALLOWED_DOMAINS = OAUTH_ALLOWED_DOMAINS
auth_manager_config.WEBHOOK_URL = WEBHOOK_URL
auth_manager_config.JWT_EXPIRES_IN = JWT_EXPIRES_IN
auth_manager_config.OAUTH_UPDATE_PICTURE_ON_LOGIN = OAUTH_UPDATE_PICTURE_ON_LOGIN


class OAuthManager:
    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app
        for _, provider_config in OAUTH_PROVIDERS.items():
            provider_config["register"](self.oauth)

    def get_client(self, provider_name):
        return self.oauth.create_client(provider_name)

    def get_user_role(self, user, user_data):
        user_count = Users.get_num_users()
        if user and user_count == 1:
            # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
            log.debug("Assigning the only user the admin role")
            return "admin"
        if not user and user_count == 0:
            # If there are no users, assign the role "admin", as the first user will be an admin
            log.debug("Assigning the first user the admin role")
            return "admin"

        if auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT:
            log.debug("Running OAUTH Role management")
            oauth_claim = auth_manager_config.OAUTH_ROLES_CLAIM
            oauth_allowed_roles = auth_manager_config.OAUTH_ALLOWED_ROLES
            oauth_admin_roles = auth_manager_config.OAUTH_ADMIN_ROLES
            oauth_roles = []
            # Default/fallback role if no matching roles are found
            role = auth_manager_config.DEFAULT_USER_ROLE

            # Next block extracts the roles from the user data, accepting nested claims of any depth
            if oauth_claim and oauth_allowed_roles and oauth_admin_roles:
                claim_data = user_data
                nested_claims = oauth_claim.split(".")
                for nested_claim in nested_claims:
                    claim_data = claim_data.get(nested_claim, {})
                oauth_roles = claim_data if isinstance(claim_data, list) else []

            log.debug(f"Oauth Roles claim: {oauth_claim}")
            log.debug(f"User roles from oauth: {oauth_roles}")
            log.debug(f"Accepted user roles: {oauth_allowed_roles}")
            log.debug(f"Accepted admin roles: {oauth_admin_roles}")

            # If any roles are found, check if they match the allowed or admin roles
            if oauth_roles:
                # If role management is enabled, and matching roles are provided, use the roles
                for allowed_role in oauth_allowed_roles:
                    # If the user has any of the allowed roles, assign the role "user"
                    if allowed_role in oauth_roles:
                        log.debug("Assigned user the user role")
                        role = "user"
                        break
                for admin_role in oauth_admin_roles:
                    # If the user has any of the admin roles, assign the role "admin"
                    if admin_role in oauth_roles:
                        log.debug("Assigned user the admin role")
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

    def update_user_groups(self, user, user_data, default_permissions):
        log.debug("Running OAUTH Group management")
        oauth_claim = auth_manager_config.OAUTH_GROUPS_CLAIM

        try:
            blocked_groups = json.loads(auth_manager_config.OAUTH_BLOCKED_GROUPS)
        except Exception as e:
            log.exception(f"Error loading OAUTH_BLOCKED_GROUPS: {e}")
            blocked_groups = []

        user_oauth_groups = []
        # Nested claim search for groups claim
        if oauth_claim:
            claim_data = user_data
            nested_claims = oauth_claim.split(".")
            for nested_claim in nested_claims:
                claim_data = claim_data.get(nested_claim, {})

            if isinstance(claim_data, list):
                user_oauth_groups = claim_data
            elif isinstance(claim_data, str):
                user_oauth_groups = [claim_data]
            else:
                user_oauth_groups = []

        user_current_groups: list[GroupModel] = Groups.get_groups_by_member_id(user.id)
        all_available_groups: list[GroupModel] = Groups.get_groups()

        # Create groups if they don't exist and creation is enabled
        if auth_manager_config.ENABLE_OAUTH_GROUP_CREATION:
            log.debug("Checking for missing groups to create...")
            all_group_names = {g.name for g in all_available_groups}
            groups_created = False
            # Determine creator ID: Prefer admin, fallback to current user if no admin exists
            admin_user = Users.get_super_admin_user()
            creator_id = admin_user.id if admin_user else user.id
            log.debug(f"Using creator ID {creator_id} for potential group creation.")

            for group_name in user_oauth_groups:
                if group_name not in all_group_names:
                    log.info(
                        f"Group '{group_name}' not found via OAuth claim. Creating group..."
                    )
                    try:
                        new_group_form = GroupForm(
                            name=group_name,
                            description=f"Group '{group_name}' created automatically via OAuth.",
                            permissions=default_permissions,  # Use default permissions from function args
                            user_ids=[],  # Start with no users, user will be added later by subsequent logic
                        )
                        # Use determined creator ID (admin or fallback to current user)
                        created_group = Groups.insert_new_group(
                            creator_id, new_group_form
                        )
                        if created_group:
                            log.info(
                                f"Successfully created group '{group_name}' with ID {created_group.id} using creator ID {creator_id}"
                            )
                            groups_created = True
                            # Add to local set to prevent duplicate creation attempts in this run
                            all_group_names.add(group_name)
                        else:
                            log.error(
                                f"Failed to create group '{group_name}' via OAuth."
                            )
                    except Exception as e:
                        log.error(f"Error creating group '{group_name}' via OAuth: {e}")

            # Refresh the list of all available groups if any were created
            if groups_created:
                all_available_groups = Groups.get_groups()
                log.debug("Refreshed list of all available groups after creation.")

        log.debug(f"Oauth Groups claim: {oauth_claim}")
        log.debug(f"User oauth groups: {user_oauth_groups}")
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(
            f"All groups available in OpenWebUI: {[g.name for g in all_available_groups]}"
        )

        # Remove groups that user is no longer a part of
        for group_model in user_current_groups:
            if (
                user_oauth_groups
                and group_model.name not in user_oauth_groups
                and group_model.name not in blocked_groups
            ):
                # Remove group from user
                log.debug(
                    f"Removing user from group {group_model.name} as it is no longer in their oauth groups"
                )

                user_ids = group_model.user_ids
                user_ids = [i for i in user_ids if i != user.id]

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                update_form = GroupUpdateForm(
                    name=group_model.name,
                    description=group_model.description,
                    permissions=group_permissions,
                    user_ids=user_ids,
                )
                Groups.update_group_by_id(
                    id=group_model.id, form_data=update_form, overwrite=False
                )

        # Add user to new groups
        for group_model in all_available_groups:
            if (
                user_oauth_groups
                and group_model.name in user_oauth_groups
                and not any(gm.name == group_model.name for gm in user_current_groups)
                and group_model.name not in blocked_groups
            ):
                # Add user to group
                log.debug(
                    f"Adding user to group {group_model.name} as it was found in their oauth groups"
                )

                user_ids = group_model.user_ids
                user_ids.append(user.id)

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                update_form = GroupUpdateForm(
                    name=group_model.name,
                    description=group_model.description,
                    permissions=group_permissions,
                    user_ids=user_ids,
                )
                Groups.update_group_by_id(
                    id=group_model.id, form_data=update_form, overwrite=False
                )

    async def _process_picture_url(
        self, picture_url: str, access_token: str = None
    ) -> str:
        """Process a picture URL and return a base64 encoded data URL.

        Args:
            picture_url: The URL of the picture to process
            access_token: Optional OAuth access token for authenticated requests

        Returns:
            A data URL containing the base64 encoded picture, or "/user.png" if processing fails
        """
        if not picture_url:
            return "/user.png"

        try:
            get_kwargs = {}
            if access_token:
                get_kwargs["headers"] = {
                    "Authorization": f"Bearer {access_token}",
                }
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(
                    picture_url, **get_kwargs, ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as resp:
                    if resp.ok:
                        picture = await resp.read()
                        base64_encoded_picture = base64.b64encode(picture).decode(
                            "utf-8"
                        )
                        guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                        if guessed_mime_type is None:
                            guessed_mime_type = "image/jpeg"
                        return (
                            f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                        )
                    else:
                        log.warning(
                            f"Failed to fetch profile picture from {picture_url}"
                        )
                        return "/user.png"
        except Exception as e:
            log.error(f"Error processing profile picture '{picture_url}': {e}")
            return "/user.png"

    async def handle_login(self, request, provider):
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

    async def handle_callback(self, request, provider, response):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        client = self.get_client(provider)
        try:
            token = await client.authorize_access_token(request)
        except Exception as e:
            log.warning(f"OAuth callback error: {e}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        user_data: UserInfo = token.get("userinfo")
        if not user_data or auth_manager_config.OAUTH_EMAIL_CLAIM not in user_data:
            user_data: UserInfo = await client.userinfo(token=token)
        if not user_data:
            log.warning(f"OAuth callback failed, user data is missing: {token}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        if auth_manager_config.OAUTH_SUB_CLAIM:
            sub = user_data.get(auth_manager_config.OAUTH_SUB_CLAIM)
        else:
            # Fallback to the default sub claim if not configured
            sub = user_data.get(OAUTH_PROVIDERS[provider].get("sub_claim", "sub"))

        if not sub:
            log.warning(f"OAuth callback failed, sub is missing: {user_data}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        provider_sub = f"{provider}@{sub}"

        email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
        email = user_data.get(email_claim, "")
        # We currently mandate that email addresses are provided
        if not email:
            # If the provider is GitHub,and public email is not provided, we can use the access token to fetch the user's email
            if provider == "github":
                try:
                    access_token = token.get("access_token")
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with aiohttp.ClientSession(trust_env=True) as session:
                        async with session.get(
                            "https://api.github.com/user/emails",
                            headers=headers,
                            ssl=AIOHTTP_CLIENT_SESSION_SSL,
                        ) as resp:
                            if resp.ok:
                                emails = await resp.json()
                                # use the primary email as the user's email
                                primary_email = next(
                                    (e["email"] for e in emails if e.get("primary")),
                                    None,
                                )
                                if primary_email:
                                    email = primary_email
                                else:
                                    log.warning(
                                        "No primary email found in GitHub response"
                                    )
                                    raise HTTPException(
                                        400, detail=ERROR_MESSAGES.INVALID_CRED
                                    )
                            else:
                                log.warning("Failed to fetch GitHub email")
                                raise HTTPException(
                                    400, detail=ERROR_MESSAGES.INVALID_CRED
                                )
                except Exception as e:
                    log.warning(f"Error fetching GitHub email: {e}")
                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
            else:
                log.warning(f"OAuth callback failed, email is missing: {user_data}")
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        email = email.lower()
        if (
            "*" not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
            and email.split("@")[-1] not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
        ):
            log.warning(
                f"OAuth callback failed, e-mail domain is not in the list of allowed domains: {user_data}"
            )
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

            # Update profile picture if enabled and different from current
            if auth_manager_config.OAUTH_UPDATE_PICTURE_ON_LOGIN:
                picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                if picture_claim:
                    new_picture_url = user_data.get(
                        picture_claim, OAUTH_PROVIDERS[provider].get("picture_url", "")
                    )
                    processed_picture_url = await self._process_picture_url(
                        new_picture_url, token.get("access_token")
                    )
                    if processed_picture_url != user.profile_image_url:
                        Users.update_user_profile_image_url_by_id(
                            user.id, processed_picture_url
                        )
                        log.debug(f"Updated profile picture for user {user.email}")

        if not user:
            # If the user does not exist, check if signups are enabled
            if auth_manager_config.ENABLE_OAUTH_SIGNUP:
                # Check if an existing user with the same email already exists
                existing_user = Users.get_user_by_email(email)
                if existing_user:
                    raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

                picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                if picture_claim:
                    picture_url = user_data.get(
                        picture_claim, OAUTH_PROVIDERS[provider].get("picture_url", "")
                    )
                    picture_url = await self._process_picture_url(
                        picture_url, token.get("access_token")
                    )
                else:
                    picture_url = "/user.png"

                username_claim = auth_manager_config.OAUTH_USERNAME_CLAIM

                name = user_data.get(username_claim)
                if not name:
                    log.warning("Username claim is missing, using email as name")
                    name = email

                role = self.get_user_role(None, user_data)

                user = Auths.insert_new_auth(
                    email=email,
                    password=get_password_hash(
                        str(uuid.uuid4())
                    ),  # Random password, not used
                    name=name,
                    profile_image_url=picture_url,
                    role=role,
                    oauth_sub=provider_sub,
                )

                if auth_manager_config.WEBHOOK_URL:
                    post_webhook(
                        WEBUI_NAME,
                        auth_manager_config.WEBHOOK_URL,
                        WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        {
                            "action": "signup",
                            "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
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

        if auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT and user.role != "admin":
            self.update_user_groups(
                user=user,
                user_data=user_data,
                default_permissions=request.app.state.config.USER_PERMISSIONS,
            )

        # Set the cookie token
        response.set_cookie(
            key="token",
            value=jwt_token,
            httponly=False,  # Required for frontend access
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )

        if ENABLE_OAUTH_SIGNUP.value:
            oauth_id_token = token.get("id_token")
            response.set_cookie(
                key="oauth_id_token",
                value=oauth_id_token,
                httponly=True,
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
            )
        # Redirect back to the frontend with the JWT token

        redirect_base_url = str(request.app.state.config.WEBUI_URL or request.base_url)
        if redirect_base_url.endswith("/"):
            redirect_base_url = redirect_base_url[:-1]
        redirect_url = f"{redirect_base_url}/auth"

        return RedirectResponse(url=redirect_url, headers=response.headers)
