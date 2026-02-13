"""
Anthropic/Claude OAuth PKCE Authentication Library

Python port of the anthropic-auth Rust library.
Implements OAuth 2.0 PKCE flow for authenticating with Claude Pro/Max accounts.

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
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp

log = logging.getLogger(__name__)


# ============================================================================
# Constants (matching Rust anthropic-auth/src/lib.rs)
# ============================================================================

# Claude Code CLI's official OAuth client ID (public client)
CLAUDE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

# Claude OAuth authorization endpoint
CLAUDE_AUTH_URL = "https://platform.claude.com/oauth/authorize"

# Anthropic token exchange endpoint
CLAUDE_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"

# Anthropic API base URL
CLAUDE_API_URL = "https://api.anthropic.com/v1"

# Profile URL
CLAUDE_PROFILE_URL = "https://api.anthropic.com/api/oauth/profile"

# Default OAuth scopes (matching opencode-anthropic-auth)
DEFAULT_SCOPES = [
    "user:profile",
    "user:inference",
    "user:sessions:claude_code",
    "user:mcp_servers",
]

# Hosted callback URI (for manual flow)
CLAUDE_HOSTED_CALLBACK_URI = "https://platform.claude.com/oauth/code/callback"

# Access token lifetime in seconds (8 hours)
ACCESS_TOKEN_LIFETIME_SECS = 28800

# User-Agent header for Claude CLI compatibility (fallback version)
USER_AGENT = "claude-cli/2.1.36 (external, cli)"

# Minimum length for PKCE code verifier (RFC 7636)
MIN_VERIFIER_LENGTH = 43

# Default length for PKCE code verifier (32 random bytes = 43 base64url chars)
VERIFIER_RANDOM_BYTES = 32


# ============================================================================
# Errors
# ============================================================================


class AnthropicAuthError(Exception):
    """Base exception for Anthropic auth errors."""

    pass


class TokenExchangeError(AnthropicAuthError):
    """Token exchange failed."""

    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"Token exchange failed: {error} - {description}")


class TokenRefreshError(AnthropicAuthError):
    """Token refresh failed."""

    def __init__(self, error: str, description: str):
        self.error = error
        self.description = description
        super().__init__(f"Token refresh failed: {error} - {description}")


class TokenExpiredError(AnthropicAuthError):
    """Access token has expired."""

    def __init__(self):
        super().__init__("Access token has expired")


class NoRefreshTokenError(AnthropicAuthError):
    """No refresh token available."""

    def __init__(self):
        super().__init__("No refresh token available")


class PkceVerifierTooShortError(AnthropicAuthError):
    """PKCE verifier is too short."""

    def __init__(self, length: int):
        self.length = length
        super().__init__(
            f"PKCE verifier too short: {length} characters (minimum {MIN_VERIFIER_LENGTH})"
        )


# ============================================================================
# PKCE (matching Rust anthropic-auth/src/pkce.rs)
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
# Tokens (matching Rust anthropic-auth/src/tokens.rs)
# ============================================================================


@dataclass
class OrganizationInfo:
    """Organization information from Claude OAuth."""

    uuid: str
    name: str


@dataclass
class AccountInfo:
    """Account information from Claude OAuth."""

    uuid: str
    email_address: str


@dataclass
class ClaudeTokens:
    """
    Managed Claude tokens with expiry tracking.

    This class wraps the raw tokens and provides:
    - Expiry tracking and checking
    - Easy serialization for storage
    - Accessors for common operations
    """

    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    scopes: List[str]
    organization: Optional[OrganizationInfo]
    account: Optional[AccountInfo]
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_response(cls, response: dict) -> "ClaudeTokens":
        """
        Creates new tokens from a token response.

        Args:
            response: The token response dict from the OAuth server

        Returns:
            ClaudeTokens instance
        """
        now = datetime.now(timezone.utc)
        expires_in = response.get("expires_in", ACCESS_TOKEN_LIFETIME_SECS)
        expires_at = now + timedelta(seconds=expires_in)

        # Parse scopes
        scope_str = response.get("scope", "")
        scopes = scope_str.split() if scope_str else []

        # Parse organization
        organization = None
        if org_data := response.get("organization"):
            organization = OrganizationInfo(
                uuid=org_data.get("uuid", ""), name=org_data.get("name", "")
            )

        # Parse account
        account = None
        if acc_data := response.get("account"):
            account = AccountInfo(
                uuid=acc_data.get("uuid", ""),
                email_address=acc_data.get("email_address", ""),
            )

        return cls(
            access_token=response["access_token"],
            refresh_token=response.get("refresh_token"),
            expires_at=expires_at,
            scopes=scopes,
            organization=organization,
            account=account,
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
        return f"Bearer {self.access_token}"

    def to_dict(self) -> dict:
        """Serializes tokens to a dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": int(self.expires_at.timestamp()),
            "scopes": self.scopes,
            "organization": {
                "uuid": self.organization.uuid,
                "name": self.organization.name,
            }
            if self.organization
            else None,
            "account": {
                "uuid": self.account.uuid,
                "email_address": self.account.email_address,
            }
            if self.account
            else None,
            "issued_at": int(self.issued_at.timestamp()),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClaudeTokens":
        """Deserializes tokens from a dictionary."""
        organization = None
        if org_data := data.get("organization"):
            organization = OrganizationInfo(
                uuid=org_data.get("uuid", ""), name=org_data.get("name", "")
            )

        account = None
        if acc_data := data.get("account"):
            account = AccountInfo(
                uuid=acc_data.get("uuid", ""),
                email_address=acc_data.get("email_address", ""),
            )

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromtimestamp(data["expires_at"], tz=timezone.utc),
            scopes=data.get("scopes", []),
            organization=organization,
            account=account,
            issued_at=datetime.fromtimestamp(
                data.get("issued_at", time.time()), tz=timezone.utc
            ),
        )


# ============================================================================
# Auth Client (matching Rust anthropic-auth/src/client.rs)
# ============================================================================


class ClaudeAuth:
    """
    Claude OAuth authentication client.

    This client handles the OAuth PKCE flow for authenticating with Claude/Anthropic.
    It's designed to be used in server-side applications where the redirect callback
    can be handled.

    Example:
        auth = ClaudeAuth("https://your-app.com/callback")

        # Step 1: Generate PKCE challenge and build auth URL
        pkce = PkceChallenge.generate()
        auth_url, state = auth.build_authorization_url(pkce)

        # Step 2: Redirect user to auth_url, they authenticate with Claude
        # Step 3: User is redirected back to your callback with `code` and `state`

        # Step 4: Exchange code for tokens
        tokens = await auth.exchange_code(code, pkce.verifier, state)
    """

    def __init__(self, redirect_uri: str, scopes: Optional[List[str]] = None):
        """
        Creates a new Claude authentication client.

        Args:
            redirect_uri: The URI where users will be redirected after authentication
            scopes: OAuth scopes to request (defaults to DEFAULT_SCOPES)
        """
        self.redirect_uri = redirect_uri
        self.scopes = scopes if scopes is not None else list(DEFAULT_SCOPES)

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

        Note: Claude requires state = verifier for the PKCE flow.

        Args:
            pkce: The PKCE challenge to use for this authorization request

        Returns:
            Tuple of (authorization_url, state)
        """
        params = {
            "code": "true",
            "client_id": CLAUDE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "code_challenge": pkce.challenge,
            "code_challenge_method": PkceChallenge.challenge_method(),
            "state": pkce.verifier,  # Claude requires state = verifier
        }

        url = f"{CLAUDE_AUTH_URL}?{urlencode(params)}"
        log.debug(f"Built authorization URL: {url[:100]}...")

        return url, pkce.verifier

    async def exchange_code(
        self, code: str, code_verifier: str, state: str
    ) -> ClaudeTokens:
        """
        Exchanges an authorization code for tokens.

        This should be called when the user is redirected back to your application
        with an authorization code.

        Args:
            code: The authorization code from the callback
            code_verifier: The PKCE code verifier (from the original PKCE challenge)
            state: The state parameter from the callback

        Returns:
            ClaudeTokens with access and refresh tokens

        Raises:
            TokenExchangeError: If the exchange fails
        """
        assert code, "authorization code must not be empty"
        assert code_verifier, "code verifier must not be empty"
        assert state, "state must not be empty"

        log.info("[EXCHANGE] Exchanging authorization code for tokens")
        log.info(
            f"[EXCHANGE] Code length: {len(code)}, verifier length: {len(code_verifier)}, state: {state[:20]}..."
        )
        log.info(f"[EXCHANGE] Redirect URI: {self.redirect_uri}")

        body = {
            "code": code,
            "state": state,
            "grant_type": "authorization_code",
            "client_id": CLAUDE_CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        log.info(f"[EXCHANGE] Token URL: {CLAUDE_TOKEN_URL}")
        log.info(
            f"[EXCHANGE] Request body (without code): grant_type={body['grant_type']}, client_id={body['client_id']}, redirect_uri={body['redirect_uri']}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                CLAUDE_TOKEN_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                response_text = await response.text()
                log.info(
                    f"[EXCHANGE] Token response status: {response.status}, body preview: {response_text[:200]}..."
                )

                if not response.ok:
                    log.error(
                        f"[EXCHANGE] Token exchange failed: {response.status} - {response_text}"
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

        tokens = ClaudeTokens.from_response(token_response)
        log.info("Successfully obtained tokens")
        log.debug(
            f"Token details: expires_at={tokens.expires_at}, scopes={tokens.scopes}"
        )

        return tokens

    async def refresh_token(self, refresh_token: str) -> ClaudeTokens:
        """
        Refreshes an access token using a refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            New ClaudeTokens with fresh access token

        Raises:
            TokenRefreshError: If the refresh fails
        """
        assert refresh_token, "refresh token must not be empty"

        log.info("Refreshing access token")

        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLAUDE_CLIENT_ID,
            "scope": " ".join(self.scopes),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                CLAUDE_TOKEN_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
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

        tokens = ClaudeTokens.from_response(token_response)
        log.info("Successfully refreshed tokens")

        return tokens

    async def refresh_from_tokens(self, tokens: ClaudeTokens) -> ClaudeTokens:
        """
        Refreshes tokens from existing ClaudeTokens.

        This is a convenience method that extracts the refresh token from
        existing tokens and calls refresh_token.

        Args:
            tokens: Existing tokens with refresh token

        Returns:
            New ClaudeTokens

        Raises:
            NoRefreshTokenError: If tokens don't have a refresh token
            TokenRefreshError: If the refresh fails
        """
        if not tokens.refresh_token:
            raise NoRefreshTokenError()

        return await self.refresh_token(tokens.refresh_token)
