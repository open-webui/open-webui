"""Validation utilities for user-supplied input."""

import re
from urllib.parse import urlparse

# Matches the OWUI-generated profile image route.  ``[^/?#]+`` accepts
# any user-ID without allowing path-traversal or query/fragment injection,
# and the ``$`` anchor rejects trailing path components.
_USER_PROFILE_IMAGE_RE = re.compile(r'^/api/v1/users/[^/?#]+/profile/image$')

# Validates MIME type and structure of base64 data URIs.  Only the prefix
# is checked — validating the full base64 payload would mean running a
# regex across megabytes of data on every Pydantic instantiation for zero
# security benefit (corrupt base64 simply renders a broken image, same as
# a 404 URL).  SVG is intentionally excluded: it can carry embedded scripts.
_SAFE_DATA_URI_RE = re.compile(r'^data:image/(png|jpeg|gif|webp);base64,', re.IGNORECASE)

# Exact relative paths accepted as profile images.  These are the only
# static-asset paths OWUI itself assigns; no prefix/wildcard matching is
# used so that arbitrary relative paths cannot trigger authenticated GETs
# against internal endpoints when rendered as ``<img>`` sources.
_SAFE_STATIC_PATHS = frozenset(
    {
        '/user.png',
        '/favicon.png',
        '/static/favicon.png',
    }
)


def validate_profile_image_url(url: str) -> str:
    """
    Pydantic-compatible validator for profile image URLs.

    Allowed formats:
    - Empty string (falls back to default avatar)
    - Known static-asset paths assigned by OWUI (exact match)
    - The OWUI profile-image API route ``/api/v1/users/{id}/profile/image``
    - ``http://`` and ``https://`` URLs with a valid hostname
    - ``data:image/{png,jpeg,gif,webp};base64,...`` URIs

    Everything else is rejected, including:
    - Dangerous schemes (javascript:, file:, ftp:, …)
    - SVG data URIs (can contain embedded scripts)
    - Arbitrary relative paths (prevents authenticated GET triggers)
    - Scheme-relative URLs (``//host/path``)
    """
    if not url:
        return url

    # --- Relative paths (exact match + anchored regex only) -----------

    if url in _SAFE_STATIC_PATHS:
        return url

    if _USER_PROFILE_IMAGE_RE.match(url):
        return url

    # --- Absolute URLs -------------------------------------------------

    # urlparse normalises the scheme to lowercase, giving us
    # case-insensitive scheme matching for free.
    parsed = urlparse(url)

    # External images served over HTTP(S), e.g. OAuth provider avatars.
    # Require a non-empty hostname (not just netloc, which can be ":80"
    # for a URL like http://:80/path with no actual host).
    if parsed.scheme in ('http', 'https'):
        if not parsed.hostname:
            raise ValueError('Invalid profile image URL: HTTP(S) URLs must include a host.')
        return url

    # Base64-encoded raster images uploaded via the frontend.
    # The regex enforces the ;base64, boundary and is case-insensitive
    # per the data-URI / MIME-type specs.
    if _SAFE_DATA_URI_RE.match(url):
        return url

    raise ValueError(
        'Invalid profile image URL: must be a known internal path, '
        'an HTTP(S) URL with a host, or a data:image URI (png/jpeg/gif/webp).'
    )
