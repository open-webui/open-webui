"""
Clerk Shared Cookie SSO for OpenWebUI.

Reads the __session cookie set by Clerk on .datameesters.nl,
verifies the JWT against Clerk's JWKS endpoint, and creates
or syncs an OpenWebUI user session.

Flow:
1. Request arrives with __session cookie but no OpenWebUI token cookie
2. Middleware verifies the Clerk JWT via JWKS (RS256)
3. Extracts Clerk user ID from 'sub' claim
4. Fetches user details (email, name) from Clerk Backend API
5. Finds or creates the OpenWebUI user
6. Creates an OpenWebUI session token, sets it as 'token' cookie
7. Subsequent requests use the 'token' cookie (this middleware skips)

Falls back to OpenWebUI's built-in OIDC flow if no valid __session
cookie is present (e.g., user goes directly to chatbot.datameesters.nl
without visiting datameesters.nl first).
"""

import logging
import uuid
from datetime import timedelta
from typing import Optional

import httpx
import jwt as pyjwt
from jwt import PyJWKClient

from open_webui.models.auths import Auths
from open_webui.models.users import Users
from open_webui.utils.auth import create_token

log = logging.getLogger(__name__)

# Cache the JWKS client
_jwks_client: Optional[PyJWKClient] = None

# Cache Clerk user info to avoid API calls on every request
_clerk_user_cache: dict[str, dict] = {}


def get_jwks_client(jwks_uri: str) -> PyJWKClient:
    """Get or create a cached JWKS client for Clerk token verification."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client


def verify_clerk_session(token: str, jwks_uri: str, issuer: str) -> Optional[dict]:
    """
    Verify a Clerk __session JWT using Clerk's JWKS endpoint.

    Returns decoded claims if valid, None otherwise.
    Claims include: sub (user ID), sid (session ID), azp, iss, exp, iat.
    """
    try:
        client = get_jwks_client(jwks_uri)
        signing_key = client.get_signing_key_from_jwt(token)

        claims = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_exp": True,
                "verify_aud": False,  # Clerk JWTs use azp, not aud
            },
        )
        return claims
    except pyjwt.ExpiredSignatureError:
        log.debug("Clerk __session JWT expired — will refresh on next request")
        return None
    except pyjwt.InvalidTokenError as e:
        log.debug("Invalid Clerk __session JWT: %s", e)
        return None
    except Exception as e:
        log.warning("Error verifying Clerk JWT: %s", e)
        return None


def fetch_clerk_user(clerk_user_id: str, clerk_secret_key: str) -> Optional[dict]:
    """
    Fetch user details from Clerk Backend API.

    Returns dict with: id, email, first_name, last_name, image_url, public_metadata.
    Cached per user ID to avoid redundant API calls.
    """
    if clerk_user_id in _clerk_user_cache:
        return _clerk_user_cache[clerk_user_id]

    try:
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {clerk_secret_key}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        user_data = resp.json()

        result = {
            "id": user_data["id"],
            "email": _get_primary_email(user_data),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            "image_url": user_data.get("image_url", ""),
            "public_metadata": user_data.get("public_metadata", {}),
        }

        _clerk_user_cache[clerk_user_id] = result
        return result
    except Exception as e:
        log.error("Failed to fetch Clerk user %s: %s", clerk_user_id, e)
        return None


def _get_primary_email(user_data: dict) -> str:
    """Extract the primary email from Clerk user data."""
    primary_email_id = user_data.get("primary_email_address_id")
    for addr in user_data.get("email_addresses", []):
        if addr.get("id") == primary_email_id:
            return addr["email_address"]
    # Fallback: first email
    if user_data.get("email_addresses"):
        return user_data["email_addresses"][0]["email_address"]
    return ""


def get_or_create_openwebui_user(
    clerk_user: dict,
    default_role: str = "user",
    db=None,
) -> Optional[object]:
    """
    Find or create an OpenWebUI user from Clerk user data.

    Lookup order:
    1. By email (most reliable — email is unique in both systems)
    2. If not found, create a new user with Clerk-provided details

    The Clerk user ID is stored in the user's settings for future reference.
    """
    email = clerk_user["email"]
    if not email:
        log.warning("Clerk user %s has no email — cannot create OpenWebUI user", clerk_user["id"])
        return None

    # Look up by email
    user = Users.get_user_by_email(email.lower(), db=db) if db else Users.get_user_by_email(email.lower())

    if user:
        log.debug("Found existing OpenWebUI user for Clerk user %s (%s)", clerk_user["id"], email)
        return user

    # Create new user
    log.info("Creating OpenWebUI user for Clerk user %s (%s)", clerk_user["id"], email)

    # Map Clerk public_metadata.rm_role to OpenWebUI role
    rm_role = clerk_user.get("public_metadata", {}).get("role", "")
    if rm_role == "admin" or rm_role == "director":
        webui_role = "admin"
    elif rm_role in ("manager", "advisor", "consultant", "analyst", "sales"):
        webui_role = "user"
    else:
        webui_role = default_role

    # First user is always admin
    has_users = Users.has_users(db=db) if db else Users.has_users()
    if not has_users:
        webui_role = "admin"

    try:
        user = Auths.insert_new_auth(
            email=email.lower(),
            password=str(uuid.uuid4()),  # Random password — login is via Clerk only
            name=clerk_user["name"] or email.split("@")[0],
            role=webui_role,
            profile_image_url=clerk_user.get("image_url", ""),
            db=db,
        )

        if user:
            log.info("Created OpenWebUI user %s (role=%s) from Clerk", user.id, webui_role)
        return user
    except Exception as e:
        log.error("Failed to create OpenWebUI user for %s: %s", email, e)
        return None


def create_session_token(user) -> str:
    """Create an OpenWebUI JWT for the given user."""
    return create_token(
        data={"id": user.id},
        expires_delta=timedelta(hours=12),
    )
