import base64
import mimetypes
import uuid

import aiohttp
import logging
from fastapi import (
    HTTPException,
    Request,
    status,
)
from starlette.responses import RedirectResponse, Response, StreamingResponse
from authlib.oidc.core import UserInfo

from open_webui.apps.webui.models.auths import Auths
from open_webui.apps.webui.models.users import Users, UserModel
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
    OAUTH_ADMIN_ROLES, WEBHOOK_URL, JWT_EXPIRES_IN,
)

from authlib.integrations.starlette_client import OAuth

from open_webui.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from open_webui.utils.misc import parse_duration
from open_webui.utils.utils import get_password_hash, create_token
from open_webui.utils.webhook import post_webhook

log = logging.getLogger(__name__)

oauth_manager = {}
oauth_manager.oauth = OAuth()

for provider_name, provider_config in OAUTH_PROVIDERS.items():
    oauth_manager.oauth.register(
        name=provider_name,
        client_id=provider_config["client_id"],
        client_secret=provider_config["client_secret"],
        server_metadata_url=provider_config["server_metadata_url"],
        client_kwargs={
            "scope": provider_config["scope"],
        },
        redirect_uri=provider_config["redirect_uri"],
    )

oauth_manager.get_client = oauth_manager.oauth.create_client

def get_user_role(user: UserModel, user_data: UserInfo) -> str:
    if user and Users.get_num_users() == 1:
        # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
        return "admin"
    if not user and Users.get_num_users() == 0:
        # If there are no users, assign the role "admin", as the first user will be an admin
        return "admin"

    if ENABLE_OAUTH_ROLE_MANAGEMENT:
        oauth_claim = OAUTH_ROLES_CLAIM
        oauth_allowed_roles = OAUTH_ALLOWED_ROLES
        oauth_admin_roles = OAUTH_ADMIN_ROLES
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
            role = DEFAULT_USER_ROLE
        else:
            # If role management is disabled, use the existing role for existing users
            role = user.role

    return role

oauth_manager.get_user_role = get_user_role

async def handle_login(provider: str, request: Request):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404)
    # If the provider has a custom redirect URL, use that, otherwise automatically generate one
    redirect_uri = OAUTH_PROVIDERS[provider].get("redirect_uri") or request.url_for(
        "oauth_callback", provider=provider
    )
    client = oauth_manager.get_client(provider)
    if client is None:
        raise HTTPException(404)
    return await client.authorize_redirect(request, redirect_uri)

oauth_manager.handle_login = handle_login

async def handle_callback(provider: str, request: Request, response: Response):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404)
    client = oauth_manager.get_client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        log.warning(f"OAuth callback error: {e}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
    user_data: UserInfo = token["userinfo"]

    sub = user_data.get("sub")
    if not sub:
        log.warning(f"OAuth callback failed, sub is missing: {user_data}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
    provider_sub = f"{provider}@{sub}"
    email_claim = OAUTH_EMAIL_CLAIM
    email = user_data.get(email_claim, "").lower()
    # We currently mandate that email addresses are provided
    if not email:
        log.warning(f"OAuth callback failed, email is missing: {user_data}")
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    # Check if the user exists
    user = Users.get_user_by_oauth_sub(provider_sub)

    if not user:
        # If the user does not exist, check if merging is enabled
        if OAUTH_MERGE_ACCOUNTS_BY_EMAIL.value:
            # Check if the user exists by email
            user = Users.get_user_by_email(email)
            if user:
                # Update the user with the new oauth sub
                Users.update_user_oauth_sub_by_id(user.id, provider_sub)

    if user:
        determined_role = get_user_role(user, user_data)
        if user.role != determined_role:
            Users.update_user_role_by_id(user.id, determined_role)

    if not user:
        # If the user does not exist, check if signups are enabled
        if ENABLE_OAUTH_SIGNUP.value:
            # Check if an existing user with the same email already exists
            existing_user = Users.get_user_by_email(user_data.get("email", "").lower())
            if existing_user:
                raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

            picture_claim = OAUTH_PICTURE_CLAIM
            picture_url = user_data.get(picture_claim, "")
            if picture_url:
                # Download the profile image into a base64 string
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(picture_url) as resp:
                            picture = await resp.read()
                            base64_encoded_picture = base64.b64encode(picture).decode(
                                "utf-8"
                            )
                            guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                            if guessed_mime_type is None:
                                # assume JPG, browsers are tolerant enough of image formats
                                guessed_mime_type = "image/jpeg"
                            picture_url = f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                except Exception as e:
                    log.error(f"Error downloading profile image '{picture_url}': {e}")
                    picture_url = ""
            if not picture_url:
                picture_url = "/user.png"
            username_claim = OAUTH_USERNAME_CLAIM

            role = get_user_role(None, user_data)

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

            if WEBHOOK_URL:
                post_webhook(
                    WEBHOOK_URL,
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
        expires_delta=parse_duration(JWT_EXPIRES_IN),
    )

    # Set the cookie token
    response.set_cookie(
        key="token",
        value=jwt_token,
        httponly=True,  # Ensures the cookie is not accessible via JavaScript
    )

    # Redirect back to the frontend with the JWT token
    redirect_url = f"{request.base_url}auth#token={jwt_token}"
    return RedirectResponse(url=redirect_url)

oauth_manager.handle_callback = handle_callback