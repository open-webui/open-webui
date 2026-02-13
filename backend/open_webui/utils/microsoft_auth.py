"""
Microsoft Graph OAuth PKCE Authentication Library

Python implementation for authenticating with Microsoft Graph API
for SharePoint/OneDrive file access.

Features:
- PKCE code verifier/challenge generation
- OAuth authorization URL building
- Token exchange and refresh
- Token management with automatic expiry tracking
"""

import base64
import hashlib
import secrets
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from urllib.parse import urlencode

import aiohttp

log = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Microsoft OAuth endpoints
MS_AUTH_URL_TEMPLATE = (
    "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
)
MS_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# Microsoft Graph API base URL
MS_GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

# Default OAuth scopes for SharePoint/OneDrive file access
DEFAULT_SCOPES = [
    "Files.Read.All",
    "Sites.Read.All",
    "User.Read",
    "offline_access",  # Required for refresh tokens
]

# Access token lifetime (typically 1 hour for MS Graph)
ACCESS_TOKEN_LIFETIME_SECS = 3600

# Minimum length for PKCE code verifier (RFC 7636)
MIN_VERIFIER_LENGTH = 43

# Default length for PKCE code verifier (32 random bytes = 43 base64url chars)
VERIFIER_RANDOM_BYTES = 32


# ============================================================================
# Errors
# ============================================================================


class MSGraphAuthError(Exception):
    """Base exception for Microsoft Graph auth errors."""

    pass


class TokenExchangeError(MSGraphAuthError):
    """Token exchange failed."""

    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"Token exchange failed: {error} - {description}")


class TokenRefreshError(MSGraphAuthError):
    """Token refresh failed."""

    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"Token refresh failed: {error} - {description}")


class TokenExpiredError(MSGraphAuthError):
    """Access token has expired."""

    def __init__(self):
        super().__init__("Access token has expired")


class NoRefreshTokenError(MSGraphAuthError):
    """No refresh token available."""

    def __init__(self):
        super().__init__("No refresh token available")


class PkceVerifierTooShortError(MSGraphAuthError):
    """PKCE verifier is too short."""

    def __init__(self, length: int):
        self.length = length
        super().__init__(
            f"PKCE verifier too short: {length} characters (minimum {MIN_VERIFIER_LENGTH})"
        )


# ============================================================================
# PKCE
# ============================================================================


@dataclass
class PkceChallenge:
    """
    PKCE challenge containing verifier and challenge values.

    The verifier is kept secret and used to prove ownership during token exchange.
    The challenge is derived from the verifier and sent with the authorization request.
    """

    verifier: str
    challenge: str

    @classmethod
    def generate(cls) -> "PkceChallenge":
        """
        Generates a new PKCE challenge with a cryptographically random verifier.

        Returns:
            PkceChallenge with verifier and challenge
        """
        verifier = cls.generate_verifier()
        challenge = cls.compute_challenge(verifier)

        assert len(verifier) >= MIN_VERIFIER_LENGTH, (
            "generated verifier should meet minimum length"
        )

        return cls(verifier=verifier, challenge=challenge)

    @classmethod
    def from_verifier(cls, verifier: str) -> "PkceChallenge":
        """
        Creates a PKCE challenge from an existing verifier.

        Args:
            verifier: The code verifier string (minimum 43 characters)

        Returns:
            PkceChallenge

        Raises:
            PkceVerifierTooShortError: If verifier is too short
        """
        if len(verifier) < MIN_VERIFIER_LENGTH:
            raise PkceVerifierTooShortError(len(verifier))

        challenge = cls.compute_challenge(verifier)
        return cls(verifier=verifier, challenge=challenge)

    @staticmethod
    def generate_verifier() -> str:
        """
        Generates a cryptographically random code verifier.

        The verifier is a base64url-encoded string without padding,
        derived from 32 random bytes.

        Returns:
            Base64url-encoded verifier string
        """
        random_bytes = secrets.token_bytes(VERIFIER_RANDOM_BYTES)
        # Base64url encode without padding
        return base64.urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")

    @staticmethod
    def compute_challenge(verifier: str) -> str:
        """
        Computes the code challenge from a verifier using SHA-256.

        The challenge is: base64url(sha256(verifier))

        Args:
            verifier: The code verifier string

        Returns:
            Base64url-encoded challenge string
        """
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def challenge_method() -> str:
        """Returns the PKCE challenge method used (always 'S256')."""
        return "S256"


# ============================================================================
# Tokens
# ============================================================================


@dataclass
class MSGraphTokens:
    """
    Managed Microsoft Graph tokens with expiry tracking.

    This class wraps the raw tokens and provides:
    - Expiry tracking and checking
    - Easy serialization for storage
    - Accessors for common operations
    """

    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    scopes: List[str]
    token_type: str = "Bearer"
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_response(cls, response: dict) -> "MSGraphTokens":
        """
        Creates new tokens from a token response.

        Args:
            response: The token response dict from the OAuth server

        Returns:
            MSGraphTokens instance
        """
        now = datetime.now(timezone.utc)
        expires_in = response.get("expires_in", ACCESS_TOKEN_LIFETIME_SECS)
        expires_at = now + timedelta(seconds=expires_in)

        # Parse scopes
        scope_str = response.get("scope", "")
        scopes = scope_str.split() if scope_str else []

        return cls(
            access_token=response["access_token"],
            refresh_token=response.get("refresh_token"),
            expires_at=expires_at,
            scopes=scopes,
            token_type=response.get("token_type", "Bearer"),
            issued_at=now,
        )

    def is_expired(self) -> bool:
        """Checks if the access token has expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def expires_within(self, seconds: int) -> bool:
        """
        Checks if the access token will expire within the given duration.

        This is useful for proactively refreshing tokens before they expire.

        Args:
            seconds: Number of seconds to check

        Returns:
            True if token expires within the given duration
        """
        threshold = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        return threshold >= self.expires_at

    def time_remaining(self) -> Optional[timedelta]:
        """
        Returns the time remaining until the token expires.

        Returns:
            timedelta if token is valid, None if expired
        """
        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return None
        return self.expires_at - now

    def validate(self) -> None:
        """
        Validates that the tokens are usable.

        Raises:
            TokenExpiredError: If access token has expired
        """
        if self.is_expired():
            raise TokenExpiredError()

    def authorization_header(self) -> str:
        """Returns the Authorization header value for API requests."""
        return f"{self.token_type} {self.access_token}"

    def to_dict(self) -> dict:
        """Serializes tokens to a dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": int(self.expires_at.timestamp()),
            "scopes": self.scopes,
            "token_type": self.token_type,
            "issued_at": int(self.issued_at.timestamp()),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MSGraphTokens":
        """Deserializes tokens from a dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromtimestamp(data["expires_at"], tz=timezone.utc),
            scopes=data.get("scopes", []),
            token_type=data.get("token_type", "Bearer"),
            issued_at=datetime.fromtimestamp(
                data.get("issued_at", time.time()), tz=timezone.utc
            ),
        )


# ============================================================================
# Auth Client
# ============================================================================


class MSGraphAuth:
    """
    Microsoft Graph OAuth authentication client.

    This client handles the OAuth PKCE flow for authenticating with Microsoft Graph API.
    It's designed to be used in server-side applications where the redirect callback
    can be handled.

    Example:
        auth = MSGraphAuth(
            client_id="your-app-id",
            client_secret="your-secret",
            tenant_id="your-tenant-id",
            redirect_uri="https://your-app.com/sharepoint/auth/callback"
        )

        # Step 1: Generate PKCE challenge and build auth URL
        pkce = PkceChallenge.generate()
        auth_url, state = auth.build_authorization_url(pkce)

        # Step 2: Redirect user to auth_url, they authenticate with Microsoft
        # Step 3: User is redirected back to your callback with `code` and `state`

        # Step 4: Exchange code for tokens
        tokens = await auth.exchange_code(code, pkce.verifier, state)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
    ):
        """
        Creates a new Microsoft Graph authentication client.

        Args:
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            tenant_id: Azure AD tenant ID
            redirect_uri: The URI where users will be redirected after authentication
            scopes: OAuth scopes to request (defaults to DEFAULT_SCOPES)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.redirect_uri = redirect_uri
        self.scopes = scopes if scopes is not None else list(DEFAULT_SCOPES)

        # Build endpoint URLs
        self.auth_url = MS_AUTH_URL_TEMPLATE.format(tenant=tenant_id)
        self.token_url = MS_TOKEN_URL_TEMPLATE.format(tenant=tenant_id)

    @staticmethod
    def generate_state() -> str:
        """
        Generates a cryptographically random state parameter.

        The state parameter is used to prevent CSRF attacks by verifying that
        the authorization response matches the request.

        Returns:
            Base64url-encoded random string
        """
        random_bytes = secrets.token_bytes(16)
        return base64.urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")

    def build_authorization_url(self, pkce: PkceChallenge) -> tuple[str, str]:
        """
        Builds the OAuth authorization URL.

        Returns the URL that users should be redirected to for authentication,
        along with the state parameter that should be stored for verification.

        Args:
            pkce: The PKCE challenge to use for this authorization request

        Returns:
            Tuple of (authorization_url, state)
        """
        state = self.generate_state()

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "code_challenge": pkce.challenge,
            "code_challenge_method": PkceChallenge.challenge_method(),
            "state": state,
            "response_mode": "query",
        }

        url = f"{self.auth_url}?{urlencode(params)}"
        log.debug(f"Built authorization URL: {url[:100]}...")

        return url, state

    async def exchange_code(
        self, code: str, code_verifier: str, state: str
    ) -> MSGraphTokens:
        """
        Exchanges an authorization code for tokens.

        This should be called when the user is redirected back to your application
        with an authorization code.

        Args:
            code: The authorization code from the callback
            code_verifier: The PKCE code verifier (from the original PKCE challenge)
            state: The state parameter from the callback (for logging only)

        Returns:
            MSGraphTokens with access and refresh tokens

        Raises:
            TokenExchangeError: If the exchange fails
        """
        assert code, "authorization code must not be empty"
        assert code_verifier, "code verifier must not be empty"

        log.info("Exchanging authorization code for tokens")

        # Microsoft uses form-encoded body, not JSON
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }

        log.debug(f"Token exchange request to {self.token_url}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.token_url,
                data=body,  # form-encoded, not JSON
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as response:
                response_text = await response.text()
                log.debug(
                    f"Token response status: {response.status}, body: {response_text[:500]}"
                )

                if not response.ok:
                    log.error(
                        f"Token exchange failed: {response.status} - {response_text}"
                    )
                    try:
                        error_data = await response.json()
                        raise TokenExchangeError(
                            error_data.get("error", str(response.status)),
                            error_data.get("error_description", response_text),
                        )
                    except Exception:
                        raise TokenExchangeError(str(response.status), response_text)

                token_response = await response.json()

        tokens = MSGraphTokens.from_response(token_response)
        log.info("Successfully obtained tokens")
        log.debug(
            f"Token details: expires_at={tokens.expires_at}, scopes={tokens.scopes}"
        )

        return tokens

    async def refresh_token(self, refresh_token: str) -> MSGraphTokens:
        """
        Refreshes an access token using a refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            New MSGraphTokens with fresh access token

        Raises:
            TokenRefreshError: If the refresh fails
        """
        assert refresh_token, "refresh token must not be empty"

        log.info("Refreshing access token")

        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.scopes),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.token_url,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as response:
                response_text = await response.text()
                log.debug(f"Refresh response status: {response.status}")

                if not response.ok:
                    log.error(
                        f"Token refresh failed: {response.status} - {response_text}"
                    )
                    try:
                        error_data = await response.json()
                        raise TokenRefreshError(
                            error_data.get("error", str(response.status)),
                            error_data.get("error_description", response_text),
                        )
                    except Exception:
                        raise TokenRefreshError(str(response.status), response_text)

                token_response = await response.json()

        tokens = MSGraphTokens.from_response(token_response)
        log.info("Successfully refreshed tokens")

        return tokens

    async def refresh_from_tokens(self, tokens: MSGraphTokens) -> MSGraphTokens:
        """
        Refreshes tokens from existing MSGraphTokens.

        This is a convenience method that extracts the refresh token from
        existing tokens and calls refresh_token.

        Args:
            tokens: Existing tokens with refresh token

        Returns:
            New MSGraphTokens

        Raises:
            NoRefreshTokenError: If tokens don't have a refresh token
            TokenRefreshError: If the refresh fails
        """
        if not tokens.refresh_token:
            raise NoRefreshTokenError()

        return await self.refresh_token(tokens.refresh_token)

    async def get_client_credentials_token(self) -> MSGraphTokens:
        """
        Gets an access token using client credentials flow (app-only authentication).

        This flow doesn't require user interaction - the app authenticates as itself.
        Requires the app to have Application permissions (not Delegated) in Azure AD.

        Returns:
            MSGraphTokens with access token (no refresh token in this flow)

        Raises:
            TokenExchangeError: If the token request fails
        """
        log.info("DEBUG: Starting client credentials flow")
        log.info(f"DEBUG: client_id={self.client_id[:8]}...")
        log.info(f"DEBUG: tenant_id={self.tenant_id}")
        log.info(f"DEBUG: token_url={self.token_url}")

        # Client credentials flow uses .default scope for application permissions
        # This requests all pre-configured application permissions
        scope = "https://graph.microsoft.com/.default"

        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": scope,
        }

        log.info(f"DEBUG: Requesting token with scope={scope}")

        async with aiohttp.ClientSession() as session:
            log.info(f"DEBUG: POSTing to {self.token_url}")
            async with session.post(
                self.token_url,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as response:
                response_text = await response.text()
                log.info(f"DEBUG: Response status: {response.status}")
                log.info(f"DEBUG: Response body: {response_text[:500]}")

                if not response.ok:
                    log.error(
                        f"Client credentials token request failed: {response.status} - {response_text}"
                    )
                    try:
                        error_data = await response.json()
                        raise TokenExchangeError(
                            error_data.get("error", str(response.status)),
                            error_data.get("error_description", response_text),
                        )
                    except TokenExchangeError:
                        raise
                    except Exception:
                        raise TokenExchangeError(str(response.status), response_text)

                token_response = await response.json()

        tokens = MSGraphTokens.from_response(token_response)
        log.info(
            f"DEBUG: Successfully got client credentials token, expires_at={tokens.expires_at}"
        )

        return tokens
