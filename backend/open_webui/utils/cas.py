import logging
from fastapi import HTTPException, Request, status
from starlette.responses import RedirectResponse
from cas import CASClient
from open_webui.apps.webui.models.auths import Auths
from open_webui.apps.webui.models.users import Users
from open_webui.config import (
    DEFAULT_USER_ROLE,
    ENABLE_CAS_SIGNUP,
    CAS_PROVIDER,
    CAS_USERNAME_CLAIM,
    CAS_EMAIL_CLAIM,
    JWT_EXPIRES_IN,
    AppConfig,
)
from open_webui.env import WEBUI_URL
from starlette.responses import Response
import uuid
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import WEBUI_SESSION_COOKIE_SAME_SITE, WEBUI_SESSION_COOKIE_SECURE
from open_webui.utils.misc import parse_duration
from open_webui.utils.utils import get_password_hash, create_token
from urllib.parse import urljoin

log = logging.getLogger(__name__)

auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_CAS_SIGNUP = ENABLE_CAS_SIGNUP
auth_manager_config.CAS_USERNAME_CLAIM = CAS_USERNAME_CLAIM
auth_manager_config.CAS_EMAIL_CLAIM = CAS_EMAIL_CLAIM
auth_manager_config.JWT_EXPIRES_IN = JWT_EXPIRES_IN


class CASManager:
    def __init__(self):
        self.cas_client = None

    def get_or_create_client(self, base_url="http://localhost:8080"):
        """Get the CAS client."""
        if not CAS_PROVIDER:
            raise HTTPException(400, detail="CAS is not configured")

        if not self.cas_client:
            self.cas_client = CASClient(
                version=CAS_PROVIDER.get("version"),
                server_url=CAS_PROVIDER.get("server_url"),
                service_url=urljoin(base_url, "/cas/callback"),
            )

        return self.cas_client

    def get_user_role(self, user):
        """Get the user role."""
        if user and Users.get_num_users() == 1:
            # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
            return "admin"
        if not user and Users.get_num_users() == 0:
            # If there are no users, assign the role "admin", as the first user will be an admin
            return "admin"
        if not user:
            # use the default role for new users
            role = auth_manager_config.DEFAULT_USER_ROLE
        else:
            # If role management is disabled, use the existing role for existing users
            role = user.role
        return role

    def handle_login(self, request: Request) -> RedirectResponse:
        """Redirect the user to the CAS login page."""
        login_url = self.get_or_create_client(str(request.base_url)).get_login_url()
        return RedirectResponse(url=login_url)

    async def handle_callback(self, request: Request, response: Response):
        """Validate the CAS ticket and create a JWT token for the user."""
        ticket = request.query_params.get("ticket")
        if not ticket:
            raise HTTPException(400, detail="Missing CAS ticket")

        cas_user, cas_attributes, _ = self.get_or_create_client().verify_ticket(ticket)
        if not cas_user:
            raise HTTPException(403, detail="CAS authentication failed")

        # Check if the user exists
        user = Users.get_user_by_email(cas_attributes.get("mail"))

        if user:
            Users.update_user_by_id(
                user.id,
                {
                    "name": cas_attributes.get(auth_manager_config.CAS_USERNAME_CLAIM),
                    "email": cas_attributes.get(auth_manager_config.CAS_EMAIL_CLAIM),
                },
            )

        if user:
            determined_role = self.get_user_role(user)
            if user.role != determined_role:
                Users.update_user_role_by_id(user.id, determined_role)

        if not user:
            # If the user does not exist, check if signups are enabled
            if auth_manager_config.ENABLE_CAS_SIGNUP:
                role = self.get_user_role(None)
                user = Auths.insert_new_auth(
                    email=cas_attributes.get(auth_manager_config.CAS_EMAIL_CLAIM),
                    password=get_password_hash(
                        str(uuid.uuid4())
                    ),  # Random password, not used
                    name=cas_attributes.get(auth_manager_config.CAS_USERNAME_CLAIM),
                    role=role,
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
        redirect_url = f"{WEBUI_URL}/auth#token={jwt_token}"
        return RedirectResponse(url=redirect_url)

    def get_logout_url(self, base_url="http://localhost:8080"):
        """Generate the CAS logout URL."""
        if not CAS_PROVIDER:
            raise HTTPException(400, detail="CAS is not configured")

        cas_logout_url = urljoin(CAS_PROVIDER.get("server_url"), "./logout")
        service_url = urljoin(base_url, "/auth")

        return f"{cas_logout_url}?service={service_url}"

    def handle_logout(self, request: Request, response: Response) -> RedirectResponse:
        """Log out the user by clearing the session and redirecting to CAS logout."""

        response.delete_cookie("token", samesite=WEBUI_SESSION_COOKIE_SAME_SITE)
        logout_url = self.get_logout_url(str(request.base_url))
        return RedirectResponse(url=logout_url)


cas_manager = CASManager()
