"""
FastAPI middleware for Clerk shared cookie SSO.

Strategy: when a request has a valid Clerk __session cookie but no OpenWebUI
token cookie, we verify the JWT, create/sync the OpenWebUI user, generate an
OpenWebUI token, and REDIRECT back to the same URL with the token cookie set.
The browser then re-requests with the token cookie, and OpenWebUI's normal
auth flow picks it up seamlessly.

This redirect approach is necessary because OpenWebUI's SvelteKit frontend
checks auth client-side and redirects to /auth before the backend response
for the initial page load arrives.
"""

import logging
import os

from fastapi import Request
from starlette.responses import RedirectResponse, Response

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
    "/api/",
    "/ollama/",
    "/openai/",
    "/oauth/",
)


async def clerk_sso_middleware(request: Request, call_next) -> Response:
    """
    Middleware that enables seamless SSO from Clerk's __session cookie.

    On page loads (HTML requests) with a valid __session cookie but no
    OpenWebUI token: verifies JWT, creates user, sets token cookie, and
    redirects back. The browser then loads with the token cookie set.

    On API requests or when token already exists: passes through.
    """
    # Skip if Clerk is not configured
    if not CLERK_SECRET_KEY:
        return await call_next(request)

    path = request.url.path

    # Skip API routes, static assets, health checks
    if any(path.startswith(p) for p in SKIP_PREFIXES):
        return await call_next(request)

    # Skip if already has an OpenWebUI token
    if request.cookies.get("token"):
        return await call_next(request)

    # Check for Clerk __session cookie
    clerk_session = request.cookies.get("__session")
    if not clerk_session:
        return await call_next(request)

    # Only process HTML page requests (not XHR/fetch)
    accept = request.headers.get("accept", "")
    if "text/html" not in accept:
        return await call_next(request)

    log.info("Clerk SSO: found __session cookie, verifying...")

    # Verify the Clerk JWT
    claims = verify_clerk_session(clerk_session, CLERK_JWKS_URI, CLERK_ISSUER)
    if not claims:
        log.warning("Clerk SSO: __session JWT verification failed")
        return await call_next(request)

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return await call_next(request)

    log.info("Clerk SSO: verified JWT for user %s", clerk_user_id)

    # Fetch user details from Clerk API
    clerk_user = fetch_clerk_user(clerk_user_id, CLERK_SECRET_KEY)
    if not clerk_user:
        log.warning("Clerk SSO: could not fetch user %s from Clerk API", clerk_user_id)
        return await call_next(request)

    # Find or create OpenWebUI user
    user = get_or_create_openwebui_user(clerk_user)
    if not user:
        log.warning("Clerk SSO: could not create OpenWebUI user for %s", clerk_user.get("email"))
        return await call_next(request)

    # Create OpenWebUI session token
    token = create_session_token(user)

    log.info(
        "Clerk SSO: authenticated %s (%s) — setting token cookie and redirecting",
        clerk_user.get("name"),
        clerk_user.get("email"),
    )

    # Redirect back to the same URL with the token cookie set
    # The browser will re-request and OpenWebUI will see the token
    redirect_url = str(request.url)
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=43200,  # 12 hours
    )

    return response
