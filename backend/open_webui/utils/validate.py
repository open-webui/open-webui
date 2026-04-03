"""Validation utilities for user-supplied input."""

import re
from urllib.parse import urlparse

# Validates the MIME type and structure of base64 data URIs, not payload
# integrity — corrupt base64 simply produces a broken image, same as a 404 URL.
# SVG is intentionally excluded: it can carry embedded scripts.
_SAFE_DATA_URI_RE = re.compile(
    r'^data:image/(png|jpeg|gif|webp);base64,', re.IGNORECASE
)


def validate_profile_image_url(url: str) -> str:
    """
    Pydantic-compatible validator for profile image URLs.

    Allowed formats:
    - Empty string (falls back to default avatar)
    - Relative paths starting with ``/`` (internal assets and API routes)
    - ``http://`` and ``https://`` URLs with a valid host
    - ``data:image/{png,jpeg,gif,webp};base64,...`` URIs

    All other schemes (javascript:, file:, ftp:, etc.) are rejected.
    SVG data URIs are rejected because SVG can contain embedded scripts.
    """
    if not url:
        return url

    # Relative paths: covers /user.png, /static/favicon.png,
    # /api/v1/users/{id}/profile/image, and any future internal routes.
    # Exclude scheme-relative URLs (//host/path) which browsers resolve
    # against the current protocol.
    if url.startswith('/') and not url.startswith('//'):
        return url

    # urlparse normalises the scheme to lowercase, giving us
    # case-insensitive scheme matching for free.
    parsed = urlparse(url)

    # External images served over HTTP(S), e.g. OAuth provider avatars.
    # Require a non-empty hostname (not just netloc, which can be ":80"
    # for a URL like http://:80/path with no actual host).
    if parsed.scheme in ('http', 'https'):
        if not parsed.hostname:
            raise ValueError(
                'Invalid profile image URL: HTTP(S) URLs must include a host.'
            )
        return url

    # Base64-encoded raster images uploaded via the frontend.
    # The regex enforces format boundaries (;base64,) and is
    # case-insensitive per the data URI / MIME type specs.
    if _SAFE_DATA_URI_RE.match(url):
        return url

    raise ValueError(
        'Invalid profile image URL: must be a relative path, an HTTP(S) URL '
        'with a host, or a data:image URI (png/jpeg/gif/webp).'
    )

