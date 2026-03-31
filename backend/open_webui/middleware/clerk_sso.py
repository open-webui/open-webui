"""
FastAPI middleware for Clerk shared cookie SSO.

Intercepts requests that have a Clerk __session cookie but no OpenWebUI
token cookie. Verifies the Clerk JWT, finds/creates the OpenWebUI user,
and sets both request.state.token (for immediate auth) and the 'token'
cookie (for subsequent requests).

Add to main.py BEFORE the check_url middleware:

    from open_webui.middleware.clerk_sso import clerk_sso_middleware
    # Add as @app.middleware('http') — see main.py integration
"""

import logging
import os

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.responses import Response

from open_webui.utils.clerk_sso import (
    verify_clerk_session,
    fetch_clerk_user,
    get_or_create_openwebui_user,
    create_session_token,
)

log = logging.getLogger(__name__)

# Clerk configuration
CLERK_JWKS_URI = os.environ.get(
    "CLERK_JWKS_URI",
    "https://clerk.datameesters.nl/.well-known/jwks.json",
)
CLERK_ISSUER = os.environ.get(
    "CLERK_ISSUER",
    "https://clerk.datameesters.nl",
)
CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY", "")

# Paths to skip
SKIP_PREFIXES = (
    "/static/",
    "/brand-assets/",
    "/assets/",
    "/_app/",
    "/health",
    "/ws/",
)


async def clerk_sso_middleware(request: Request, call_next) -> Response:
    """
    Middleware that enables seamless SSO from Clerk's __session cookie.

    If a request has a valid __session cookie but no OpenWebUI token,
    this middleware authenticates the user and sets both request.state.token
    (for immediate use) and the token cookie (for subsequent requests).
    """
    # Skip if Clerk is not configured
    if not CLERK_SECRET_KEY:
        return await call_next(request)

    # Skip static assets
    path = request.url.path
    if any(path.startswith(p) for p in SKIP_PREFIXES):
        return await call_next(request)

    # Skip if already has an OpenWebUI token (cookie or header)
    if request.cookies.get("token"):
        return await call_next(request)
    if request.headers.get("Authorization"):
        return await call_next(request)

    # Check for Clerk __session cookie
    clerk_session = request.cookies.get("__session")
    if not clerk_session:
        return await call_next(request)

    # Verify the Clerk JWT
    claims = verify_clerk_session(clerk_session, CLERK_JWKS_URI, CLERK_ISSUER)
    if not claims:
        return await call_next(request)

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return await call_next(request)

    # Fetch user details from Clerk API
    clerk_user = fetch_clerk_user(clerk_user_id, CLERK_SECRET_KEY)
    if not clerk_user:
        return await call_next(request)

    # Find or create OpenWebUI user
    user = get_or_create_openwebui_user(clerk_user)
    if not user:
        return await call_next(request)

    # Create OpenWebUI session token
    token = create_session_token(user)

    # Set request.state.token so the existing check_url middleware
    # and get_current_user see the token immediately on this request
    request.state.token = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    # Process the request
    response = await call_next(request)

    # Set the token cookie so subsequent requests don't need this middleware
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=43200,  # 12 hours
    )

    log.info(
        "Clerk SSO: authenticated %s (%s) via __session cookie",
        clerk_user.get("name"),
        clerk_user.get("email"),
    )

    return response
